"""
s19: Permission System — 先划边界，再给自由

Hermes 的权限审批管线: 判断操作能不能做、要不要问用户。
四层检查: 硬阻止 → 需审批 → 安全操作 → 自由执行。

Usage:
    python s19_permission/code.py
"""

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()


# ── Permission Levels ──────────────────────────────────

class PermissionLevel(Enum):
    DENY = "deny"            # 硬阻止 — 绝不执行
    ASK_USER = "ask_user"    # 需要用户确认
    ALLOW_ONCE = "allow_once"  # 本次允许，下次再问
    ALLOW_ALWAYS = "allow_always"  # 永远允许
    SANDBOX = "sandbox"      # 在沙箱中执行


# ── Permission Rule ────────────────────────────────────

@dataclass
class PermissionRule:
    """一条权限规则"""
    pattern: str              # 匹配命令的正则
    level: PermissionLevel    # 匹配后的权限级别
    reason: str = ""          # 为什么这样设置
    scope: str = "global"     # global | project | session


class PermissionPolicy:
    """权限策略 — 有序规则列表，先匹配先生效"""

    def __init__(self):
        self.rules: list[PermissionRule] = [
            # 硬阻止 — 危险操作
            PermissionRule(r"rm\s+-rf\s+/", PermissionLevel.DENY, "防止误删根目录"),
            PermissionRule(r"sudo\s+", PermissionLevel.DENY, "禁止提权操作"),
            PermissionRule(r"chmod\s+777", PermissionLevel.DENY, "禁止开放所有权限"),
            PermissionRule(r">\s*/dev/sda", PermissionLevel.DENY, "禁止直接写磁盘"),

            # 需审批 — 破坏性操作
            PermissionRule(r"git\s+push\s+--force", PermissionLevel.ASK_USER, "强制推送需确认"),
            PermissionRule(r"rm\s+-rf\s+(?!~)", PermissionLevel.ASK_USER, "递归删除需确认"),
            PermissionRule(r"pip\s+(uninstall|install)", PermissionLevel.ASK_USER, "修改包需确认"),
            PermissionRule(r"npm\s+(uninstall|install)\s+-g", PermissionLevel.ASK_USER, "全局安装需确认"),

            # 沙箱执行 — 可能有副作用的操作
            PermissionRule(r"curl\s+", PermissionLevel.SANDBOX, "网络请求在沙箱中执行"),
            PermissionRule(r"wget\s+", PermissionLevel.SANDBOX, "下载操作在沙箱中执行"),

            # 安全操作 — 不需要审批
            PermissionRule(r"ls\s+", PermissionLevel.ALLOW_ALWAYS, "列出文件总是安全的"),
            PermissionRule(r"cat\s+", PermissionLevel.ALLOW_ALWAYS, "读取文件总是安全的"),
            PermissionRule(r"git\s+(status|diff|log|branch)", PermissionLevel.ALLOW_ALWAYS, "git 只读操作安全"),
            PermissionRule(r"echo\s+", PermissionLevel.ALLOW_ALWAYS, "echo 是安全的"),
        ]
        self.default_level = PermissionLevel.ASK_USER  # 未知命令默认需审批
        self.approved_this_session: set = set()  # 本 session 已批准的操作

    def check(self, command: str) -> tuple[PermissionLevel, str]:
        """检查一条命令的权限级别"""
        # 检查是否本 session 已批准
        cmd_hash = hash(command)
        if cmd_hash in self.approved_this_session:
            return PermissionLevel.ALLOW_ONCE, "session-approved"

        for rule in self.rules:
            if re.search(rule.pattern, command):
                return rule.level, rule.reason

        return self.default_level, "未知命令，默认需审批"

    def approve(self, command: str):
        """批准一条命令（本 session 有效）"""
        self.approved_this_session.add(hash(command))

    def deny(self, command: str):
        """拒绝一条命令（本 session 记住拒绝）"""
        pass  # 可以扩展为记住拒绝列表


# ── Approval Pipeline ──────────────────────────────────

class ApprovalPipeline:
    """权限审批管线 — 检查 → 审批 → 执行"""

    def __init__(self, policy: PermissionPolicy):
        self.policy = policy
        self.stats = {"denied": 0, "approved": 0, "asked": 0}

    def execute(self, command: str, auto_approve: bool = False) -> dict:
        """执行一条命令，经过权限检查"""
        level, reason = self.policy.check(command)

        result = {
            "command": command,
            "level": level.value,
            "reason": reason,
            "executed": False,
            "output": "",
        }

        if level == PermissionLevel.DENY:
            self.stats["denied"] += 1
            result["output"] = f"❌ DENIED: {reason}"
            return result

        if level == PermissionLevel.ASK_USER and not auto_approve:
            self.stats["asked"] += 1
            result["output"] = f"⚠️ 需确认: {command}\n原因: {reason}\n输入 'approve' 批准, 'deny' 拒绝"
            return result

        # 批准执行
        self.stats["approved"] += 1
        return self._do_execute(command, result)

    def _do_execute(self, command: str, result: dict) -> dict:
        """实际执行命令"""
        import subprocess
        try:
            r = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=10, cwd=os.getcwd(),
            )
            result["executed"] = True
            result["output"] = r.stdout or "(no output)"
            if r.stderr:
                result["output"] += f"\n[stderr] {r.stderr}"
        except subprocess.TimeoutExpired:
            result["output"] = "⏱️ 命令超时"
        except Exception as e:
            result["output"] = f"❌ 执行错误: {e}"
        return result


# ── Main ──────────────────────────────────────────────

def main():
    policy = PermissionPolicy()
    pipeline = ApprovalPipeline(policy)

    print("=" * 60)
    print("s19: Permission System — 权限审批管线")
    print("=" * 60)
    print(f"已加载 {len(policy.rules)} 条权限规则")
    print()
    print("权限级别:")
    print("  🚫 DENY       — 硬阻止，绝不执行")
    print("  ⚠️  ASK_USER  — 需要用户确认")
    print("  🏖️  SANDBOX   — 沙箱执行")
    print("  ✅ ALLOW      — 自由执行")
    print()

    # 演示: 各种命令的权限检查
    test_commands = [
        "ls -la",
        "cat README.md",
        "rm -rf /tmp/cache",
        "sudo rm -rf /",
        "curl https://example.com",
        "git push --force origin main",
    ]

    print("━━━ 权限检查演示 ━━━")
    for cmd in test_commands:
        level, reason = policy.check(cmd)
        emoji = {"deny": "🚫", "ask_user": "⚠️", "allow_once": "🔓",
                  "allow_always": "✅", "sandbox": "🏖️"}
        print(f"  {emoji.get(level.value, '❓')} [{level.value.upper():12s}] {cmd:40s} | {reason}")

    print()
    print("━━━ 执行管线演示 ━━━")

    # 自动批准的安全命令
    result = pipeline.execute("ls -la", auto_approve=True)
    print(f"  ✅ {result['command']}")
    print(f"     Output: {result['output'][:100]}")

    # 需要确认的危险命令
    result = pipeline.execute("rm -rf ./temp", auto_approve=False)
    print(f"  ⚠️ {result['command']}")
    print(f"     {result['output']}")

    # 硬阻止
    result = pipeline.execute("sudo rm -rf /")
    print(f"  🚫 {result['command']}")
    print(f"     {result['output']}")

    print()
    print(f"统计: {pipeline.stats}")
    print()
    print("设计原则:")
    print("  1. 先匹配先生效 — 规则按顺序检查")
    print("  2. 默认拒绝 — 未知命令需审批")
    print("  3. Session 记忆 — 批准过的命令本次不再问")
    print("  4. 硬阻止不可绕过 — DENY 规则无例外")


if __name__ == "__main__":
    main()
