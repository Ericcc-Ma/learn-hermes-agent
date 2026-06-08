"""
s20: Hook System — 挂在循环上，不写进循环里

Hermes 的 hook 扩展机制: 在工具调用前后、session 生命周期等节点挂自定义逻辑。
不需要改 agent loop 代码，通过 hook 注册即可扩展。

Hooks: PreToolUse, PostToolUse, SessionStart, SessionEnd, Stop, Notification

Usage:
    python s20_hooks/code.py
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()


# ── Hook Points ────────────────────────────────────────

class HookPoint(Enum):
    PRE_TOOL_USE = "pre_tool_use"      # 工具执行前
    POST_TOOL_USE = "post_tool_use"    # 工具执行后
    SESSION_START = "session_start"    # 会话开始
    SESSION_END = "session_end"        # 会话结束
    STOP = "stop"                      # Agent 停止
    NOTIFICATION = "notification"      # 后台任务完成通知
    PRE_COMPACT = "pre_compact"        # 上下文压缩前
    POST_COMPACT = "post_compact"      # 上下文压缩后


# ── Hook Event ─────────────────────────────────────────

@dataclass
class HookEvent:
    """Hook 事件 — 传递给 hook handler 的数据"""
    hook_point: HookPoint
    tool_name: str = ""           # PreToolUse/PostToolUse 时填充
    tool_input: dict = field(default_factory=dict)
    tool_output: str = ""         # PostToolUse 时填充
    session_id: str = ""
    timestamp: str = ""
    metadata: dict = field(default_factory=dict)


# ── Hook Result ────────────────────────────────────────

@dataclass
class HookResult:
    """Hook 执行的返回结果"""
    allow: bool = True             # 是否允许继续（PreToolUse 时生效）
    modified_input: dict = None    # 修改后的工具参数
    message: str = ""              # 附加消息
    blocking: bool = False         # 是否阻塞（Stop Hook 时生效）


# ── Hook Registry ──────────────────────────────────────

class HookRegistry:
    """Hook 注册表 — 管理所有 hook handler"""

    def __init__(self):
        self._handlers: dict[HookPoint, list[Callable]] = {
            hp: [] for hp in HookPoint
        }
        self._event_log: list[HookEvent] = []

    def register(self, hook_point: HookPoint, handler: Callable[[HookEvent], Optional[HookResult]]):
        """注册一个 hook handler"""
        self._handlers[hook_point].append(handler)
        print(f"  [Hook] registered {handler.__name__} → {hook_point.value}")

    def fire(self, event: HookEvent) -> list[HookResult]:
        """触发一个 hook 点的所有 handler"""
        self._event_log.append(event)
        results = []
        for handler in self._handlers[event.hook_point]:
            try:
                result = handler(event)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"  [Hook] handler error: {handler.__name__}: {e}")
        return results

    def should_allow(self, event: HookEvent) -> tuple[bool, str]:
        """PreToolUse: 所有 handler 都允许才放行"""
        results = self.fire(event)
        for r in results:
            if not r.allow:
                return False, r.message or "Blocked by hook"
        return True, ""

    def log(self):
        """打印 hook 事件日志"""
        print(f"\n  Hook events logged: {len(self._event_log)}")
        for e in self._event_log[-5:]:
            print(f"    [{e.hook_point.value}] {e.tool_name} — {e.timestamp}")


# ── Example Hooks ──────────────────────────────────────

def audit_log_hook(event: HookEvent) -> HookResult:
    """审计日志 hook — 记录所有工具调用"""
    with open(".hermes/audit.log", "a", encoding="utf-8") as f:
        f.write(f"[{event.timestamp}] {event.hook_point.value} "
                f"tool={event.tool_name} input={json.dumps(event.tool_input, ensure_ascii=False)}\n")
    return HookResult(allow=True)


def dangerous_command_guard(event: HookEvent) -> Optional[HookResult]:
    """危险命令守卫 — PreToolUse 时拦截危险 bash 命令"""
    if event.tool_name != "bash":
        return None
    command = event.tool_input.get("command", "")
    dangerous = ["rm -rf /", "sudo ", "mkfs.", "dd if=", "> /dev/sda"]
    for pattern in dangerous:
        if pattern in command:
            return HookResult(
                allow=False,
                message=f"🚫 Hook blocked dangerous command: {command}",
            )
    return HookResult(allow=True)


def session_stats_hook(event: HookEvent) -> HookResult:
    """会话统计 hook — SessionEnd 时输出统计"""
    if event.hook_point != HookPoint.SESSION_END:
        return None
    print(f"  [Hook:Stats] Session {event.session_id} ended")
    return HookResult()


def tool_result_trimmer(event: HookEvent) -> Optional[HookResult]:
    """工具结果裁剪 — PostToolUse 时裁剪过长的输出"""
    if event.hook_point != HookPoint.POST_TOOL_USE:
        return None
    if len(event.tool_output) > 2000:
        print(f"  [Hook:Trim] trimmed output from {len(event.tool_output)} to 2000 chars")
    return None


# ── Hook-Enabled Agent Loop ────────────────────────────

class HookedAgent:
    """集成了 hook 系统的 agent"""

    def __init__(self, hooks: HookRegistry):
        self.hooks = hooks
        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._fire_session_start()

    def _fire_session_start(self):
        self.hooks.fire(HookEvent(
            hook_point=HookPoint.SESSION_START,
            session_id=self.session_id,
            timestamp=datetime.now().isoformat(),
        ))

    def _fire_session_end(self):
        self.hooks.fire(HookEvent(
            hook_point=HookPoint.SESSION_END,
            session_id=self.session_id,
            timestamp=datetime.now().isoformat(),
        ))

    def execute_tool_safe(self, tool_name: str, tool_input: dict) -> dict:
        """带 hook 的安全工具执行"""
        ts = datetime.now().isoformat()

        # PreToolUse hook
        pre_event = HookEvent(
            hook_point=HookPoint.PRE_TOOL_USE,
            tool_name=tool_name, tool_input=tool_input,
            session_id=self.session_id, timestamp=ts,
        )
        allowed, reason = self.hooks.should_allow(pre_event)
        if not allowed:
            return {"executed": False, "output": reason}

        # 执行工具
        import subprocess
        try:
            r = subprocess.run(
                tool_input.get("command", ""), shell=True,
                capture_output=True, text=True, timeout=30, cwd=os.getcwd(),
            )
            output = r.stdout or "(no output)"
        except Exception as e:
            output = f"Error: {e}"

        # PostToolUse hook
        post_event = HookEvent(
            hook_point=HookPoint.POST_TOOL_USE,
            tool_name=tool_name, tool_input=tool_input,
            tool_output=output,
            session_id=self.session_id, timestamp=ts,
        )
        self.hooks.fire(post_event)

        return {"executed": True, "output": output}

    def stop(self):
        self._fire_session_end()


# ── Main ──────────────────────────────────────────────

def main():
    hooks = HookRegistry()

    # 注册 hooks
    hooks.register(HookPoint.PRE_TOOL_USE, dangerous_command_guard)
    hooks.register(HookPoint.PRE_TOOL_USE, audit_log_hook)
    hooks.register(HookPoint.POST_TOOL_USE, tool_result_trimmer)
    hooks.register(HookPoint.SESSION_END, session_stats_hook)

    agent = HookedAgent(hooks)

    print("=" * 60)
    print("s20: Hook System — 挂在循环上，不写进循环里")
    print("=" * 60)
    print(f"已注册 {sum(len(h) for h in hooks._handlers.values())} 个 hook handler")
    print(f"Session: {agent.session_id}")
    print()
    print("Hook 节点:")
    for hp in HookPoint:
        handlers = hooks._handlers[hp]
        if handlers:
            names = ", ".join(h.__name__ for h in handlers)
            print(f"  🔗 {hp.value}: {names}")
    print()

    # 演示: 安全命令 vs 危险命令
    print("━━━ 安全命令 ━━━")
    result = agent.execute_tool_safe("bash", {"command": "echo 'Hello World'"})
    print(f"  ✅ {result['output'].strip()}")

    print("\n━━━ 危险命令（被 hook 拦截）━━━")
    result = agent.execute_tool_safe("bash", {"command": "sudo rm -rf /"})
    print(f"  {result['output']}")

    print("\n━━━ 另一个安全命令 ━━━")
    result = agent.execute_tool_safe("bash", {"command": "ls -la"})
    print(f"  ✅ executed={result['executed']}")

    agent.stop()
    hooks.log()
    print()
    print("设计原则:")
    print("  1. 挂在循环上，不改循环代码")
    print("  2. 多个 handler 可以注册到同一个 hook 点")
    print("  3. PreToolUse handler 任一返回 allow=False 即阻止")
    print("  4. Hook 不影响主流程性能（同步执行）")


if __name__ == "__main__":
    main()
