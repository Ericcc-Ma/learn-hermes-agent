"""
s02: Background Review — Memory Nudge

s01 的 memory 提取需要对话完全结束。真正的自进化 agent
在每 N 轮对话后，后台 fork 独立审查 agent，检查是否有值得保存的记忆。

Usage:
    python s02_background_memory_review/code.py
"""

import json
import os
import re
import time
from pathlib import Path

from llm import get_client
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

MEMORY_DIR = Path(".memory")
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"

# ── Config ────────────────────────────────────────────

class Config:
    MEMORY_NUDGE_INTERVAL = 5  # 每 5 轮触发一次记忆审查

config = Config()

# ── Tools ─────────────────────────────────────────────

BASH_TOOL = {
    "name": "bash",
    "description": "Execute a shell command. Returns stdout/stderr.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"}
        },
        "required": ["command"],
    },
}

TOOLS = [BASH_TOOL]


# ── Tool Handlers ─────────────────────────────────────

def run_bash(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=30, cwd=os.getcwd(),
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30s"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {"bash": run_bash}


# ── Memory System ─────────────────────────────────────

def write_memory(name: str, mem_type: str, description: str, body: str):
    MEMORY_DIR.mkdir(exist_ok=True)
    entry = f"""---
name: {name}
type: {mem_type}
description: {description}
---

{body}
"""
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write("\n---\n" + entry)
    print(f"  [Memory: saved '{name}']")


def load_memories() -> str:
    if not MEMORY_FILE.exists():
        return ""
    content = MEMORY_FILE.read_text(encoding="utf-8")
    if not content.strip():
        return ""
    return f"""<memory-context>
[System note: The following is recalled memory context, NOT new user input.
Treat as authoritative reference data.]

{content}
</memory-context>"""


def build_system() -> str:
    base = "You are a helpful coding agent. You have access to a bash tool."
    memories = load_memories()
    if memories:
        return memories + "\n\n" + base
    return base


# ── Background Review ─────────────────────────────────

def background_memory_review(messages_snapshot: list):
    """
    后台记忆审查：fork 独立 AIAgent，回放对话快照，
    自我询问"是否有值得保存的记忆/偏好？"

    这是 Hermes 自进化体系的最前线——nudge 机制的核心。
    """
    print("\n  ⏳ [BackgroundReview] 启动记忆审查...")

    # 构建审查对话
    dialogue = ""
    for m in messages_snapshot[-12:]:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, dict) and block.get("type") == "tool_use":
                    text_parts.append(f"[tool_use: {block.get('name', '?')}]")
                elif isinstance(block, dict) and block.get("type") == "tool_result":
                    text_parts.append(f"[tool_result: {str(block.get('content', ''))[:100]}]")
            content = " ".join(text_parts)
        dialogue += f"[{role}] {str(content)[:500]}\n"

    review_prompt = f"""You are a background memory reviewer. Review this conversation snapshot.

Look for:
1. User preferences (coding style, workflow, tools they like/dislike)
2. User feedback about agent behavior ("stop doing X", "don't format like this")
3. Project-specific facts (architecture decisions, constraints, goals)
4. Reference information (URLs, dashboards, ticket numbers)

Conversation:
{dialogue}

Return a JSON array of memories to save. Return [] if nothing new or significant.
Format: [{{"name": "kebab-case", "mem_type": "user|feedback|project|reference",
              "description": "one-line", "body": "full detail"}}]
"""
    try:
        response = CLIENT.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": review_prompt}],
            max_tokens=500,
            system="You are a memory review agent. Return ONLY valid JSON array.",
        )
        text = extract_text(response.content)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            print("  [BackgroundReview] 无新记忆")
            return 0

        memories = json.loads(match.group())
        count = 0
        for m in memories:
            if isinstance(m, dict) and "name" in m:
                write_memory(
                    name=m.get("name", "unknown"),
                    mem_type=m.get("mem_type", "user"),
                    description=m.get("description", ""),
                    body=m.get("body", ""),
                )
                count += 1

        if count > 0:
            print(f"  ✅ [BackgroundReview] 提取了 {count} 条新记忆")
        else:
            print("  [BackgroundReview] 无新记忆")
        return count
    except Exception as e:
        print(f"  ⚠️ [BackgroundReview] 审查失败: {e}")
        return 0


# ── Agent Loop ────────────────────────────────────────

def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def execute_tools(content) -> list:
    results = []
    for block in content:
        name, input_data, block_id = None, None, None
        if hasattr(block, "type") and block.type == "tool_use":
            name, input_data, block_id = block.name, block.input, block.id
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            name, input_data, block_id = block["name"], block["input"], block["id"]

        if name and name in TOOL_HANDLERS:
            output = TOOL_HANDLERS[name](**(input_data or {}))
            results.append({
                "type": "tool_result",
                "tool_use_id": block_id,
                "content": str(output),
            })
    return results


def agent_loop(query: str, client, messages=None):
    global turn_count
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": query})

    while True:
        system = build_system()

        response = client.messages.create(
            model=MODEL, system=system,
            messages=messages, tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # 对话结束 → 检查是否触发 nudge
            turn_count += 1
            if turn_count % config.MEMORY_NUDGE_INTERVAL == 0:
                background_memory_review(messages)
            return response

        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})
        turn_count += 1

        # 每 N 轮触发一次背景审查
        if turn_count % config.MEMORY_NUDGE_INTERVAL == 0:
            background_memory_review(messages)


# ── Main ──────────────────────────────────────────────

turn_count = 0

def main():
    global turn_count
    print("=" * 60)
    print("s02: Background Review — 自动背景记忆审查")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Nudge interval: 每 {config.MEMORY_NUDGE_INTERVAL} 轮审查一次")
    print(f"Memory: {MEMORY_FILE}")
    print()
    print("Agent 会在每 N 轮对话后自动审查是否有值得保存的记忆。")
    print("试试多次对话，观察背景审查的触发。")
    print("输入 /exit 退出, /reset 重置")
    print()

    messages = []
    turn_count = 0

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query == "/exit":
            break
        if query == "/reset":
            messages = []
            turn_count = 0
            print("[会话已重置]")
            continue

        response = agent_loop(query, CLIENT, messages)
        text = extract_text(response.content)
        print(text)
        print()


if __name__ == "__main__":
    main()
