"""
s01: Agent Loop + Memory — 记住用户是谁

最简自进化 agent: agent loop + MEMORY.md 持久化记忆。
每轮对话结束后自动提取并保存记忆，下次对话自动加载。

Usage:
    python s01_agent_loop/code.py
"""

import json
import os
import re
from pathlib import Path

from llm import get_client
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

MEMORY_DIR = Path(".memory")
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"

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

MEMORY_TOOL = {
    "name": "memory",
    "description": "Save a fact to persistent memory. Use for user preferences, feedback, project facts, or references.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Short kebab-case name for this memory"},
            "mem_type": {"type": "string", "enum": ["user", "feedback", "project", "reference"],
                         "description": "Type of memory"},
            "description": {"type": "string", "description": "One-line summary"},
            "body": {"type": "string", "description": "Full memory content"},
        },
        "required": ["name", "mem_type", "description", "body"],
    },
}

TOOLS = [BASH_TOOL, MEMORY_TOOL]


# ── Tool Handlers ─────────────────────────────────────

def run_bash(command: str) -> str:
    """Execute a shell command safely."""
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


# ── Memory System ─────────────────────────────────────

def write_memory(name: str, mem_type: str, description: str, body: str):
    """Append a memory entry to MEMORY.md."""
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
    """Read MEMORY.md and return formatted memory context."""
    if not MEMORY_FILE.exists():
        return ""

    content = MEMORY_FILE.read_text(encoding="utf-8")
    if not content.strip():
        return ""

    return f"""<memory-context>
[System note: The following is recalled memory context, NOT new user input.
Treat as authoritative reference data — this is the agent's persistent memory.]

{content}
</memory-context>"""


def build_system() -> str:
    """Build the system prompt with injected memories."""
    base = (
        "You are a helpful coding agent. You have access to a bash tool and a memory tool.\n"
        "Use the memory tool to save important facts about the user, their preferences, "
        "or project context that should persist across sessions."
    )
    memories = load_memories()
    if memories:
        return memories + "\n\n" + base
    return base


def extract_and_save_memory(messages, client):
    """After conversation ends, extract memories from the dialogue."""
    recent = ""
    for m in messages[-8:]:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, dict) and block.get("type") == "tool_use":
                    text_parts.append(f"[tool: {block.get('name', '?')}]")
            content = " ".join(text_parts)
        recent += f"[{role}] {str(content)[:300]}\n"

    prompt = f"""Examine this conversation excerpt. Is there anything worth remembering?

Memory types:
- user: personal info, coding preferences, work style
- feedback: how the agent should behave, corrections
- project: ongoing work, goals, constraints
- reference: URLs, dashboards, external resources

Recent conversation:
{recent}

Return a JSON array of new memories to save.
Return [] if nothing new or significant. Do NOT save trivial one-off facts.

Format:
[{{"name": "kebab-case-name", "mem_type": "user|feedback|project|reference",
   "description": "one-line summary", "body": "full detail including why and how to apply"}}]
"""
    try:
        response = client.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            system="You are a memory extraction agent. Return ONLY valid JSON.",
        )
        text = extract_text(response.content)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
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
        return count
    except (json.JSONDecodeError, Exception):
        return 0


# ── Agent Loop ────────────────────────────────────────

def extract_text(content) -> str:
    """Extract text from API response content blocks."""
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
    """Execute tool_use blocks and return tool_result messages."""
    results = []
    for block in content:
        if hasattr(block, "type") and block.type == "tool_use":
            handler = TOOL_HANDLERS.get(block.name)
            if handler:
                output = handler(**block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output),
                })
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            handler = TOOL_HANDLERS.get(block["name"])
            if handler:
                output = handler(**block["input"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": str(output),
                })
    return results


def memory_handler(name: str, mem_type: str, description: str, body: str) -> str:
    """Handle memory tool call."""
    write_memory(name, mem_type, description, body)
    return f"Memory saved: {name} ({mem_type})"


TOOL_HANDLERS = {
    "bash": run_bash,
    "memory": memory_handler,
}


def agent_loop(query: str, client, messages=None):
    """Main agent loop with memory injection and extraction."""
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": query})

    while True:
        system = build_system()

        response = client.messages.create(
            model=MODEL,
            system=system,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # Conversation ended — extract memories
            n = extract_and_save_memory(messages, client)
            if n > 0:
                print(f"  [Memory: extracted {n} new memories after conversation]\n")
            return response

        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})


# ── Main ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("s01: Agent Loop + Memory — 最简单的自进化 agent")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Memory: {MEMORY_FILE}")
    print()
    print("试试: 'I prefer tabs over spaces. Remember that.'")
    print("试试: 'Create a file hello.py'")
    print("试试: 退出重跑, 问 'What are my coding preferences?'")
    print("输入 /exit 退出")
    print()

    messages = []

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

        response = agent_loop(query, CLIENT, messages)
        text = extract_text(response.content)
        print(text)
        print()


if __name__ == "__main__":
    main()
