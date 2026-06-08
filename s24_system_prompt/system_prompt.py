"""
s24: System Prompt Assembly — prompt 是拼出来的，不是写死的

Hermes 的 system prompt 运行时组装: 分段定义 + 按需拼接 + 条件注入。
不同 profile、不同平台、不同上下文 → 拼出不同的 prompt。

Usage:
    python s24_system_prompt/code.py
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()


# ── Prompt Section ─────────────────────────────────────

@dataclass
class PromptSection:
    """一个 prompt 片段"""
    name: str                  # 片段名称
    content: str               # 片段内容
    priority: int = 100        # 排序优先级（越小越靠前）
    condition: str = ""        # 条件表达式（为空表示总是注入）
    max_tokens: int = 0        # token 预算限制
    enabled: bool = True


# ── System Prompt Builder ──────────────────────────────

class SystemPromptBuilder:
    """运行时组装 system prompt"""

    def __init__(self):
        self._sections: dict[str, PromptSection] = {}
        self._init_defaults()

    def _init_defaults(self):
        """初始化默认 prompt 片段"""
        defaults = [
            PromptSection("identity",
                "You are Hermes, a self-evolving AI agent. You learn from every conversation.",
                priority=10),
            PromptSection("safety",
                "SAFETY: Do NOT execute destructive commands without confirmation. "
                "Do NOT access files outside the project directory. "
                "Do NOT share sensitive information.",
                priority=20),
            PromptSection("tools",
                "TOOLS: You have access to bash, file operations, web search, "
                "and MCP tools. Use them effectively.",
                priority=50),
            PromptSection("memory_context",
                "",  # 运行时填充
                priority=40,
                condition="has_memories"),
            PromptSection("gateway_context",
                "",  # 运行时填充
                priority=30,
                condition="has_gateway_context"),
            PromptSection("skills_catalog",
                "",  # 运行时填充
                priority=60,
                condition="has_skills"),
            PromptSection("planning_instruction",
                "PLANNING: For complex tasks, use todo_write to create a plan first. "
                "Break large tasks into smaller, manageable steps.",
                priority=70),
            PromptSection("self_evolution",
                "SELF-EVOLUTION: After conversations, review for patterns worth saving "
                "as memories or skills. Learn from corrections.",
                priority=80),
        ]
        for s in defaults:
            self.add_section(s)

    def add_section(self, section: PromptSection):
        self._sections[section.name] = section

    def update_section(self, name: str, content: str):
        if name in self._sections:
            self._sections[name].content = content

    def remove_section(self, name: str):
        self._sections.pop(name, None)

    def build(self, context: dict = None) -> str:
        """根据上下文组装最终的 system prompt"""
        context = context or {}
        active_sections = []

        for section in sorted(self._sections.values(), key=lambda s: s.priority):
            if not section.enabled:
                continue

            # 条件检查
            if section.condition:
                if not context.get(section.condition, False):
                    continue

            # Token 预算限制
            content = section.content
            if section.max_tokens > 0 and len(content) // 4 > section.max_tokens:
                content = content[:section.max_tokens * 4] + "\n... [truncated]"

            if content.strip():
                active_sections.append(content)

        return "\n\n".join(active_sections)

    def estimate_tokens(self, context: dict = None) -> int:
        """估算 prompt 的 token 数"""
        return len(self.build(context)) // 4

    def list_sections(self) -> list[dict]:
        return [
            {"name": s.name, "priority": s.priority,
             "condition": s.condition or "always",
             "enabled": s.enabled,
             "chars": len(s.content)}
            for s in sorted(self._sections.values(), key=lambda s: s.priority)
        ]


# ── Per-Platform Prompt Variation ─────────────────────

class PlatformPromptConfig:
    """不同平台的 prompt 配置"""

    PLATFORM_CONFIGS = {
        "cli": {
            "identity": "Interactive CLI coding agent session.",
        },
        "telegram": {
            "identity": "Messaging-based assistant. Keep responses concise (< 500 chars). "
                       "Use Telegram markdown formatting.",
        },
        "cron": {
            "identity": "Scheduled task executor. No interactive questions. "
                       "Complete the task and report results.",
            "safety": "CRON MODE: Auto-approve safe operations. No user interaction available.",
        },
    }

    @classmethod
    def apply(cls, builder: SystemPromptBuilder, platform: str):
        config = cls.PLATFORM_CONFIGS.get(platform, {})
        for section_name, content in config.items():
            builder.update_section(section_name, content)


# ── Main ──────────────────────────────────────────────

def main():
    builder = SystemPromptBuilder()

    print("=" * 60)
    print("s24: System Prompt Assembly — prompt 是拼出来的")
    print("=" * 60)
    print()

    # 1. 查看所有片段
    print("Prompt 片段注册表:")
    for s in builder.list_sections():
        cond = f" (if {s['condition']})" if s['condition'] != "always" else ""
        status = "✅" if s['enabled'] else "❌"
        print(f"  {status} [{s['priority']:3d}] {s['name']:25s} {s['chars']:4d} chars{cond}")

    # 2. 基础 context（无额外注入）
    print("\n━━━ 基础 prompt（无记忆、无技能、无 gateway）━━━")
    base = builder.build({})
    print(f"  Tokens: ~{len(base)//4}")
    print(f"  Preview: {base[:200]}...")

    # 3. 有记忆 + 有技能的 context
    builder.update_section("memory_context",
        "<memory-context>\n- User prefers tabs over spaces\n"
        "- Project uses pytest with --cov\n</memory-context>")
    builder.update_section("skills_catalog",
        "SKILLS:\n- code-review: Review code for bugs and style\n"
        "- deploy: Deployment checklist and verification")

    print("\n━━━ 完整 prompt（有记忆 + 有技能）━━━")
    full = builder.build({
        "has_memories": True,
        "has_skills": True,
    })
    print(f"  Tokens: ~{len(full)//4}")
    print(f"  Preview: {full[:200]}...")

    # 4. CLI vs Cron platform
    print("\n━━━ 不同平台的 prompt 差异 ━━━")
    builder2 = SystemPromptBuilder()

    # CLI
    PlatformPromptConfig.apply(builder2, "cli")
    cli_prompt = builder2.build()
    print(f"  CLI:  ~{len(cli_prompt)//4} tokens")

    # Cron
    builder3 = SystemPromptBuilder()
    PlatformPromptConfig.apply(builder3, "cron")
    cron_prompt = builder3.build()
    print(f"  Cron: ~{len(cron_prompt)//4} tokens")

    print()
    print("设计原则:")
    print("  1. 分段定义 — 每个关注点一个独立片段")
    print("  2. 按需拼接 — 条件表达式控制是否注入")
    print("  3. 优先级排序 — 越小越靠前")
    print("  4. Token 预算 — 每段可设上限")
    print("  5. 平台差异 — 同一套片段，不同平台拼出不同 prompt")


if __name__ == "__main__":
    main()
