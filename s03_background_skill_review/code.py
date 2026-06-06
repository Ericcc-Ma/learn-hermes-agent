"""
s03: Background Review — Skill Nudge

在 s02 的记忆审查基础上，增加技能审查维度。
检测对话中的纠正、新技术模式、技能过时信号，自动创建/更新技能。

Usage:
    python s03_background_skill_review/code.py
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
SKILLS_DIR = Path(".skills")

# ── Config ────────────────────────────────────────────

class Config:
    MEMORY_NUDGE_INTERVAL = 5      # 每 5 轮触发记忆审查
    SKILL_NUDGE_INTERVAL = 10       # 每 10 次工具迭代触发技能审查

config = Config()

# ── Forbidden Capture Patterns ───────────────────────

FORBIDDEN_PATTERNS = [
    r"(missing|not found|not installed).*(binary|executable|command)",
    r"(browser|chrome|selenium).*(don['']t work|not working|broken)",
    r"(network|connection|timeout).*(error|failed|unavailable)",
    r"(api key|credential|auth).*(missing|invalid|expired|not set)",
]

def is_forbidden_signal(body: str) -> bool:
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            return True
    return False

# ── Tools ─────────────────────────────────────────────

BASH_TOOL = {
    "name": "bash",
    "description": "Execute a shell command. Returns stdout/stderr.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string"}
        },
        "required": ["command"],
    },
}

LOAD_SKILL_TOOL = {
    "name": "load_skill",
    "description": "Load a skill's full content by name.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Skill name to load"}
        },
        "required": ["name"],
    },
}

TOOLS = [BASH_TOOL, LOAD_SKILL_TOOL]

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


def load_skill(name: str) -> str:
    skill_file = SKILLS_DIR / name / "SKILL.md"
    if skill_file.exists():
        return skill_file.read_text(encoding="utf-8")
    return f"Skill not found: {name}"


TOOL_HANDLERS = {"bash": run_bash, "load_skill": load_skill}


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
[System note: The following is recalled memory context, NOT new user input.]

{content}
</memory-context>"""


# ── Skill System ──────────────────────────────────────

SKILL_REGISTRY: dict = {}

def scan_skills():
    """Scan .skills/ directory and populate registry."""
    SKILL_REGISTRY.clear()
    if not SKILLS_DIR.exists():
        return
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        skill_file = d / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8")
            # Parse name and description from first lines
            lines = content.split("\n")
            name = d.name
            desc = ""
            for line in lines:
                line = line.strip()
                if line.startswith("# "):
                    desc = line.lstrip("# ").strip()
                    break
            SKILL_REGISTRY[name] = {
                "name": name,
                "description": desc,
                "path": str(d),
            }


def create_skill(name: str, description: str, body: str):
    """Create a new skill file."""
    skill_dir = SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    content = f"""# {description}

{body}
"""
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    SKILL_REGISTRY[name] = {
        "name": name,
        "description": description,
        "path": str(skill_dir),
    }
    print(f"  [Skill: created '{name}']")


def update_skill(name: str, new_content: str):
    """Update an existing skill's SKILL.md."""
    skill_dir = SKILLS_DIR / name
    if skill_dir.exists():
        (skill_dir / "SKILL.md").write_text(new_content, encoding="utf-8")
        print(f"  [Skill: updated '{name}']")


def append_skill_reference(name: str, ref_name: str, content: str):
    """Add a reference file under an existing skill."""
    skill_dir = SKILLS_DIR / name
    if skill_dir.exists():
        refs_dir = skill_dir / "references"
        refs_dir.mkdir(exist_ok=True)
        (refs_dir / f"{ref_name}.md").write_text(content, encoding="utf-8")
        print(f"  [Skill: added reference '{ref_name}' to '{name}']")


def list_skills() -> str:
    if not SKILL_REGISTRY:
        return "(no skills available)"
    return "\n".join(
        f"- **{s['name']}**: {s['description']}"
        for s in SKILL_REGISTRY.values()
    )


def build_system() -> str:
    catalog = list_skills()
    base = (
        f"You are a helpful coding agent.\n\n"
        f"Available skills (use load_skill to get full details):\n{catalog}\n"
    )
    memories = load_memories()
    if memories:
        return memories + "\n\n" + base
    return base


# ── Background Review ─────────────────────────────────

def background_memory_review(messages_snapshot: list):
    """后台记忆审查"""
    print("\n  ⏳ [BackgroundReview:Memory] 启动记忆审查...")

    dialogue = format_snapshot(messages_snapshot[-12:])

    prompt = f"""Review this conversation for new memories.
Look for: user preferences, feedback, project facts, references.

Conversation:
{dialogue}

Return JSON array of memories or []."""
    try:
        response = CLIENT.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            system="Return ONLY valid JSON array.",
        )
        text = extract_text(response.content)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            memories = json.loads(match.group())
            count = 0
            for m in memories:
                if isinstance(m, dict) and "name" in m:
                    write_memory(m["name"], m.get("mem_type", "user"),
                                m.get("description", ""), m.get("body", ""))
                    count += 1
            if count:
                print(f"  ✅ [BackgroundReview:Memory] {count} 条新记忆")
            else:
                print("  [BackgroundReview:Memory] 无新记忆")
    except Exception as e:
        print(f"  ⚠️ [BackgroundReview:Memory] {e}")


def background_skill_review(messages_snapshot: list):
    """后台技能审查——Hermes 自进化体系的核心"""
    print("\n  ⏳ [BackgroundReview:Skill] 启动技能审查...")

    dialogue = format_snapshot(messages_snapshot[-16:])
    loaded = ", ".join(SKILL_REGISTRY.keys()) if SKILL_REGISTRY else "none"

    prompt = f"""You are a background skill reviewer. Analyze this conversation.

Detect these signals (priority order):

1. USER CORRECTION (highest): User corrected agent's style/format/workflow.
   "stop doing X", "don't format like this", "每次部署前先跑 test suite"
   → create or update a skill

2. NEW TECHNIQUE: Non-trivial trick, fix, workaround discovered.

3. OUTDATED SKILL: A loaded skill was wrong or missing steps.
   → update the skill

4. REPEATED PATTERN: Same task type appeared 3+ times.
   → create a reusable skill

Currently loaded skills: {loaded}

Conversation:
{dialogue}

Return JSON:
{{"detected_signals": [
  {{"signal_type": "correction|technique|outdated|repeated",
    "action": "create|update|append_reference",
    "skill_name": "kebab-case",
    "skill_description": "one-line",
    "skill_body": "full SKILL.md content including instructions"}}
]}}
Return empty list if nothing detected."""
    try:
        response = CLIENT.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            system="Return ONLY valid JSON.",
        )
        text = extract_text(response.content)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            print("  [BackgroundReview:Skill] 无技能信号")
            return

        result = json.loads(match.group())
        signals = result.get("detected_signals", [])

        count = 0
        for sig in signals:
            name = sig.get("skill_name", "")
            body = sig.get("skill_body", "")
            action = sig.get("action", "create")
            signal_type = sig.get("signal_type", "")

            # 禁止捕获检查
            if is_forbidden_signal(body):
                print(f"  🚫 [Skill] 禁止捕获信号: {name} ({signal_type})")
                continue

            if action == "update" and name in SKILL_REGISTRY:
                update_skill(name, body)
                count += 1
            elif action == "append_reference" and name in SKILL_REGISTRY:
                ref_name = sig.get("skill_description", "reference").replace(" ", "-")
                append_skill_reference(name, ref_name, body)
                count += 1
            elif action == "create":
                desc = sig.get("skill_description", name)
                create_skill(name, desc, body)
                count += 1
            else:
                # Fallback: 创建新技能
                desc = sig.get("skill_description", name)
                create_skill(name, desc, body)
                count += 1

        if count:
            print(f"  ✅ [BackgroundReview:Skill] {count} 个技能操作")
        else:
            print("  [BackgroundReview:Skill] 无新技能")
    except Exception as e:
        print(f"  ⚠️ [BackgroundReview:Skill] {e}")


# ── Helpers ───────────────────────────────────────────

def format_snapshot(messages: list) -> str:
    dialogue = ""
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, dict) and block.get("type") == "tool_use":
                    text_parts.append(f"[tool: {block.get('name', '?')}]")
                elif isinstance(block, dict) and block.get("type") == "tool_result":
                    c = str(block.get("content", ""))[:100]
                    text_parts.append(f"[tool_result: {c}]")
            content = " ".join(text_parts)
        dialogue += f"[{role}] {str(content)[:500]}\n"
    return dialogue


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


# ── Agent Loop ────────────────────────────────────────

turn_count = 0
tool_iteration_count = 0

def agent_loop(query: str, client, messages=None):
    global turn_count, tool_iteration_count
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
            turn_count += 1
            # 记忆 nudge
            if turn_count % config.MEMORY_NUDGE_INTERVAL == 0:
                background_memory_review(messages)
            # 技能 nudge
            if tool_iteration_count >= config.SKILL_NUDGE_INTERVAL:
                background_skill_review(messages)
                tool_iteration_count = 0
            return response

        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})
        turn_count += 1
        tool_iteration_count += 1

        # 记忆 nudge
        if turn_count % config.MEMORY_NUDGE_INTERVAL == 0:
            background_memory_review(messages)
        # 技能 nudge
        if tool_iteration_count > 0 and tool_iteration_count % config.SKILL_NUDGE_INTERVAL == 0:
            background_skill_review(messages)
            tool_iteration_count = 0


# ── Main ──────────────────────────────────────────────

def main():
    global turn_count, tool_iteration_count
    scan_skills()

    print("=" * 60)
    print("s03: Background Review — 自动背景技能审查")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Memory nudge: 每 {config.MEMORY_NUDGE_INTERVAL} 轮")
    print(f"Skill nudge: 每 {config.SKILL_NUDGE_INTERVAL} 次工具迭代")
    print(f"Skills: {len(SKILL_REGISTRY)} loaded from {SKILLS_DIR}")
    print()
    print("Agent 会检测对话中的纠正、新技术、技能过时信号。")
    print("试试故意纠正 agent，观察技能自动创建。")
    print("输入 /exit 退出, /reset 重置, /skills 查看技能")
    print()

    messages = []
    turn_count = 0
    tool_iteration_count = 0

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
            tool_iteration_count = 0
            print("[会话已重置]")
            continue
        if query == "/skills":
            print(list_skills())
            print()
            continue

        response = agent_loop(query, CLIENT, messages)
        text = extract_text(response.content)
        print(text)
        print()


if __name__ == "__main__":
    main()
