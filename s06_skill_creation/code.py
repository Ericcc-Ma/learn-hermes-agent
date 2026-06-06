"""
s06: Skill Creation — 什么该学，什么不该学

信号优先级 + 禁止捕获列表 + 操作优先级策略。
三层安全护栏防止学错、学多、学坏。

Usage:
    python s06_skill_creation/code.py
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from llm import get_client
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

SKILLS_DIR = Path(".skills")
MEMORY_DIR = Path(".memory")

# ── Forbidden Capture Patterns ────────────────────────

FORBIDDEN_PATTERNS = [
    (r"(missing|not found|not installed).*(binary|executable|command)", "环境依赖失败"),
    (r"(browser|chrome|selenium).*(don['']t work|not working|broken)", "工具否定性断言"),
    (r"(network|connection|timeout).*(error|failed|unavailable)", "网络临时错误"),
    (r"(api key|credential|auth).*(missing|invalid|expired|not set)", "凭证缺失"),
    (r"(write|create|make) (me |a |the ).*(script|file|program)", "一次性任务叙事"),
]

forbidden_log: list[dict] = []

def is_forbidden(body: str, context: str = "") -> tuple[bool, str]:
    """检查内容是否属于禁止捕获。返回 (is_forbidden, reason)"""
    for pattern, reason in FORBIDDEN_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            forbidden_log.append({
                "pattern": pattern, "reason": reason,
                "body_preview": body[:200], "context": context[:200],
                "timestamp": datetime.now().isoformat(),
            })
            return True, reason
    return False, ""

# ── Signal Priorities ─────────────────────────────────

SIGNAL_PRIORITIES = {
    "correction": 1,    # 用户纠正 — 最高
    "technique": 2,     # 新技术/模式 — 高
    "outdated": 3,      # 技能过时 — 中
    "repeated": 4,      # 重复模式 — 低
}

ACTION_PRIORITIES = {
    "update_loaded": 1,     # 更新当前已加载的技能
    "update_existing": 2,   # 更新已有伞形技能
    "append_reference": 3,  # 添加 references/ 文件
    "create_new": 4,        # 创建新技能
}

# ── Skill Registry ────────────────────────────────────

class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, dict] = {}
        self.loaded_skills: set = set()  # 本轮已加载的技能

    def scan(self):
        if not self.skills_dir.exists():
            return
        for d in sorted(self.skills_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            sf = d / "SKILL.md"
            if sf.exists():
                content = sf.read_text(encoding="utf-8")
                desc = ""
                for line in content.split("\n"):
                    if line.strip().startswith("# "):
                        desc = line.strip().lstrip("# ").strip()
                        break
                self.skills[d.name] = {
                    "name": d.name, "description": desc,
                    "path": str(d), "content": content,
                }

    def create(self, name: str, description: str, body: str):
        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = f"# {description}\n\n{body}"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        self.skills[name] = {"name": name, "description": description, "path": str(skill_dir), "content": content}
        print(f"  [Skill: created '{name}']")

    def update(self, name: str, body: str):
        if name in self.skills:
            skill_dir = Path(self.skills[name]["path"])
            (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
            self.skills[name]["content"] = body
            print(f"  [Skill: updated '{name}']")

    def add_reference(self, name: str, ref_name: str, content: str):
        if name in self.skills:
            ref_dir = Path(self.skills[name]["path"]) / "references"
            ref_dir.mkdir(exist_ok=True)
            (ref_dir / f"{ref_name}.md").write_text(content)
            print(f"  [Skill: added ref '{ref_name}' to '{name}']")

    def mark_loaded(self, name: str):
        self.loaded_skills.add(name)

    def find_matching_umbrella(self, name_hint: str) -> str | None:
        """找匹配的已有伞形技能"""
        keywords = set(re.findall(r"\w+", name_hint.lower()))
        for name, skill in self.skills.items():
            skill_words = set(re.findall(r"\w+", (skill.get("description", "") + name).lower()))
            if keywords & skill_words:
                return name
        return None


# ── Background Skill Review with Safety ───────────────

def background_skill_review(messages_snapshot: list, registry: SkillRegistry):
    """后台技能审查——带完整安全护栏"""
    print("\n  ⏳ [BackgroundReview:Skill] 启动技能审查...")

    dialogue = format_snapshot(messages_snapshot[-16:])
    loaded = ", ".join(registry.loaded_skills) if registry.loaded_skills else "none"

    prompt = f"""You are a skill reviewer. Analyze this conversation.

SIGNALS to detect (priority order):
1. USER CORRECTION (highest): user corrected agent style/format/workflow
2. NEW TECHNIQUE: non-trivial trick, fix, workaround discovered
3. OUTDATED SKILL: loaded skill was wrong or missing steps
4. REPEATED PATTERN: same task type appeared 3+ times

IMPORTANT: Do NOT flag environment errors, missing tools, network issues,
or one-off script requests as skill-worthy.

Currently loaded: {loaded}
Available skills: {", ".join(registry.skills.keys()) if registry.skills else "none"}

Conversation:
{dialogue}

Return JSON:
{{"detected_signals": [
  {{"signal_type": "correction|technique|outdated|repeated",
    "action": "update_loaded|update_existing|append_reference|create_new",
    "target_skill": "existing-skill-name or empty for new",
    "skill_name": "kebab-case-name",
    "skill_description": "one-line",
    "skill_body": "full SKILL.md content"}}
]}}
Return [] if nothing."""
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
        applied = 0
        skipped = 0

        for sig in sorted(signals, key=lambda s: SIGNAL_PRIORITIES.get(s.get("signal_type", ""), 99)):
            body = sig.get("skill_body", "")
            name = sig.get("skill_name", "")
            action = sig.get("action", "create_new")
            signal_type = sig.get("signal_type", "")
            target = sig.get("target_skill", "")

            # 安全护栏 1: 禁止捕获检查
            forbidden, reason = is_forbidden(body, name)
            if forbidden:
                print(f"  🚫 禁止捕获: '{name}' ({reason})")
                skipped += 1
                continue

            # 安全护栏 2: 操作优先级
            if action == "update_loaded" and registry.loaded_skills:
                # 找第一个已加载的技能来更新
                loaded_target = list(registry.loaded_skills)[0]
                registry.update(loaded_target, body)
                applied += 1

            elif action in ("update_existing", "append_reference"):
                umbrella = target or registry.find_matching_umbrella(name)
                if umbrella:
                    if action == "append_reference":
                        ref_name = sig.get("skill_description", name).replace(" ", "-").lower()
                        registry.add_reference(umbrella, ref_name, body)
                    else:
                        registry.update(umbrella, body)
                    applied += 1
                else:
                    # 没有匹配的伞形 → 降级为创建
                    registry.create(name, sig.get("skill_description", name), body)
                    applied += 1

            elif action == "create_new":
                # 检查是否已有匹配技能
                umbrella = registry.find_matching_umbrella(name)
                if umbrella:
                    registry.add_reference(umbrella, name, body)
                else:
                    registry.create(name, sig.get("skill_description", name), body)
                applied += 1

        if applied:
            print(f"  ✅ [BackgroundReview:Skill] {applied} applied, {skipped} skipped")
        else:
            print("  [BackgroundReview:Skill] 无操作")
    except Exception as e:
        print(f"  ⚠️ [BackgroundReview:Skill] {e}")


# ── Helpers ───────────────────────────────────────────

def format_snapshot(messages) -> str:
    dialogue = ""
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text": parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use": parts.append(f"[tool: {block.get('name', '?')}]")
            content = " ".join(parts)
        dialogue += f"[{role}] {str(content)[:500]}\n"
    return dialogue


def extract_text(content) -> str:
    if isinstance(content, str): return content
    parts = []
    for block in content:
        if hasattr(block, "text"): parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text": parts.append(block.get("text", ""))
    return "\n".join(parts)


def execute_tools(content, handlers) -> list:
    results = []
    for block in content:
        name, input_data, block_id = None, None, None
        if hasattr(block, "type") and block.type == "tool_use":
            name, input_data, block_id = block.name, block.input, block.id
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            name, input_data, block_id = block["name"], block["input"], block["id"]
        if name and name in handlers:
            output = handlers[name](**(input_data or {}))
            results.append({"type": "tool_result", "tool_use_id": block_id, "content": str(output)})
    return results


# ── Agent Loop ────────────────────────────────────────

BASH_TOOL = {"name": "bash", "description": "Execute a shell command.",
             "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}
LOAD_SKILL_TOOL = {"name": "load_skill", "description": "Load a skill's full content.",
                   "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}

def run_bash(command: str) -> str:
    import subprocess
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=os.getcwd())
        return r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr else "") or "(no output)"
    except subprocess.TimeoutExpired: return "Command timed out"
    except Exception as e: return f"Error: {e}"

skill_registry = SkillRegistry(SKILLS_DIR)

def load_skill_handler(name: str) -> str:
    if name in skill_registry.skills:
        skill_registry.mark_loaded(name)
        return skill_registry.skills[name]["content"]
    return f"Skill not found: {name}"

TOOL_HANDLERS = {"bash": run_bash, "load_skill": load_skill_handler}

def build_system() -> str:
    lines = []
    for name, s in skill_registry.skills.items():
        lines.append(f"- **{name}**: {s.get('description', '')}")
    catalog = "\n".join(lines) if lines else "(no skills)"
    return f"You are a helpful coding agent.\n\nSkills:\n{catalog}\n\nUse load_skill for details."


turn_count = 0
SKILL_NUDGE_INTERVAL = 10

def agent_loop(query: str, client, messages=None):
    global turn_count
    if messages is None: messages = []
    messages.append({"role": "user", "content": query})

    while True:
        response = client.messages.create(
            model=MODEL, system=build_system(),
            messages=messages, tools=[BASH_TOOL, LOAD_SKILL_TOOL],
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            turn_count += 1
            if turn_count % SKILL_NUDGE_INTERVAL == 0:
                background_skill_review(messages, skill_registry)
            return response

        results = execute_tools(response.content, TOOL_HANDLERS)
        messages.append({"role": "user", "content": results})
        turn_count += 1
        if turn_count % SKILL_NUDGE_INTERVAL == 0:
            background_skill_review(messages, skill_registry)


# ── Main ──────────────────────────────────────────────

def main():
    global turn_count
    skill_registry.scan()
    turn_count = 0

    print("=" * 60)
    print("s06: Skill Creation — 什么该学，什么不该学")
    print("=" * 60)
    print(f"Forbidden patterns: {len(FORBIDDEN_PATTERNS)}")
    print("信号优先级: correction > technique > outdated > repeated")
    print("操作优先级: update_loaded > update_existing > append_ref > create_new")
    print()
    print("/skills      — 列出技能")
    print("/forbidden   — 显示被拦截的信号日志")
    print("/exit        — 退出")
    print()

    messages = []

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!"); break
        if not query: continue
        if query == "/exit": break
        if query == "/skills":
            for name, s in skill_registry.skills.items():
                print(f"  - {name}: {s.get('description', '')}")
            print()
            continue
        if query == "/forbidden":
            if not forbidden_log:
                print("  (no forbidden signals intercepted)")
            else:
                for entry in forbidden_log:
                    print(f"  🚫 [{entry['reason']}] {entry['body_preview'][:100]}")
            print()
            continue

        response = agent_loop(query, CLIENT, messages)
        print(extract_text(response.content))
        print()


if __name__ == "__main__":
    main()
