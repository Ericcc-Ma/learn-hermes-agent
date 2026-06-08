"""
s12: Complete Self-Evolving Agent — 六层归位

六层自进化架构完整集成：
  1. 实时学习 (Background Review)
  2. 技能管理 (Lifecycle)
  3. 长期维护 (Curator)
  4. 记忆系统 (Memory)
  5. 上下文管理 (Context)
  6. 数据分析 (Insights)

Usage:
    python s12_comprehensive/code.py
"""

import json
import os
import random
import re
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field

from llm import get_client
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

# ── Paths ─────────────────────────────────────────────

MEMORY_DIR = Path(".memory")
SKILLS_DIR = Path(".skills")
ARCHIVE_DIR = SKILLS_DIR / ".archive"
DB_PATH = Path(".hermes") / "state.db"
LOG_DIR = Path(".hermes") / "logs"

# ── Config ────────────────────────────────────────────

@dataclass
class HermesConfig:
    memory_nudge_interval: int = 5
    skill_nudge_interval: int = 10
    curator_interval_hours: int = 168
    curator_min_idle_hours: int = 2
    stale_after_days: int = 30
    archive_after_days: int = 90
    compact_threshold: int = 4000
    enabled: bool = True

config = HermesConfig()

# ── Forbidden Capture ─────────────────────────────────

FORBIDDEN_PATTERNS = [
    (r"(missing|not found|not installed).*(binary|executable|command)", "环境依赖失败"),
    (r"(browser|chrome|selenium).*(don['']t work|not working|broken)", "工具否定性断言"),
    (r"(api key|credential|auth).*(missing|invalid|expired|not set)", "凭证缺失"),
]

def is_forbidden(body: str) -> bool:
    return any(re.search(p, body, re.I) for p, _ in FORBIDDEN_PATTERNS)

# ═══════════════════════════════════════════════════════════
# Layer 4: Memory System (s04)
# ═══════════════════════════════════════════════════════════

class MemorySystem:
    def __init__(self, memory_dir: Path = MEMORY_DIR):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(exist_ok=True)
        self.db_path = self.memory_dir / "memory.db"
        self._init_db()

    def _init_db(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("""CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE, mem_type TEXT, description TEXT, body TEXT,
            created_at TEXT, updated_at TEXT)""")
        self.conn.commit()

    def write(self, name: str, mem_type: str, description: str, body: str):
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT INTO memories (name, mem_type, description, body, created_at, updated_at)
               VALUES (?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET
               mem_type=?, description=?, body=?, updated_at=?""",
            (name, mem_type, description, body, now, now, mem_type, description, body, now))
        self.conn.commit()
        # Also write MEMORY.md for backward compat
        mem_file = self.memory_dir / "MEMORY.md"
        entry = f"---\nname: {name}\ntype: {mem_type}\ndescription: {description}\n---\n\n{body}\n"
        with open(mem_file, "a", encoding="utf-8") as f:
            f.write("\n---\n" + entry)

    def search(self, query: str, limit: int = 5) -> list:
        rows = self.conn.execute(
            "SELECT name, mem_type, description, body FROM memories WHERE name LIKE ? OR description LIKE ? OR body LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()
        return [{"name": r[0], "mem_type": r[1], "description": r[2], "body": r[3]} for r in rows]

    def system_block(self) -> str:
        rows = self.conn.execute("SELECT name, mem_type, description FROM memories ORDER BY updated_at DESC LIMIT 20").fetchall()
        if not rows: return ""
        lines = "\n".join(f"- [{r[0]}]({r[0]}.md) — {r[2]} (type: {r[1]})" for r in rows)
        return f"<memory-context>\n[System note: recalled memory, NOT new input.]\n\n{lines}\n</memory-context>"

    def close(self):
        self.conn.close()

memory = MemorySystem()

# ═══════════════════════════════════════════════════════════
# Layer 2: Skill Lifecycle (s05)
# ═══════════════════════════════════════════════════════════

class SkillRegistry:
    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir
        self.skills: dict[str, dict] = {}
        self.loaded_this_session: set = set()

    def scan(self):
        self.skills.clear()
        dirs = [(self.skills_dir, "active"), (ARCHIVE_DIR, "archived")]
        for base_dir, default_state in dirs:
            if not base_dir.exists(): continue
            for d in sorted(base_dir.iterdir()):
                if not d.is_dir() or d.name.startswith("."): continue
                sf = d / "SKILL.md"
                if not sf.exists(): continue
                content = sf.read_text(encoding="utf-8")
                desc = ""
                for line in content.split("\n"):
                    if line.strip().startswith("# "):
                        desc = line.strip()[2:].strip(); break
                meta_file = d / ".skill_meta.json"
                if meta_file.exists():
                    meta = json.loads(meta_file.read_text())
                else:
                    meta = {"state": default_state, "pinned": False, "source": "agent",
                            "last_activity_at": datetime.now().isoformat(), "created_at": datetime.now().isoformat()}
                self.skills[d.name] = {**meta, "name": d.name, "description": desc, "path": str(d), "content": content}

    def create(self, name: str, description: str, body: str):
        d = self.skills_dir / name; d.mkdir(parents=True, exist_ok=True)
        content = f"# {description}\n\n{body}"
        (d / "SKILL.md").write_text(content, encoding="utf-8")
        meta = {"state": "active", "pinned": False, "source": "agent",
                "last_activity_at": datetime.now().isoformat(), "created_at": datetime.now().isoformat()}
        (d / ".skill_meta.json").write_text(json.dumps(meta, indent=2))
        self.skills[name] = {**meta, "name": name, "description": description, "path": str(d), "content": content}
        print(f"  [Skill] created '{name}'")

    def update(self, name: str, body: str):
        if name not in self.skills: return
        Path(self.skills[name]["path"]).joinpath("SKILL.md").write_text(body, encoding="utf-8")
        self.skills[name]["content"] = body
        self._touch(name)

    def add_reference(self, umbrella: str, ref_name: str, content: str):
        if umbrella not in self.skills: return
        ref_dir = Path(self.skills[umbrella]["path"]) / "references"
        ref_dir.mkdir(exist_ok=True)
        (ref_dir / f"{ref_name}.md").write_text(content)

    def _touch(self, name: str):
        if name in self.skills:
            self.skills[name]["last_activity_at"] = datetime.now().isoformat()
            self._save_meta(name)

    def record_usage(self, name: str):
        if name not in self.skills: return
        skill = self.skills[name]
        skill["last_activity_at"] = datetime.now().isoformat()
        if skill.get("state") == "stale":
            skill["state"] = "active"
            print(f"  [Skill] {name}: reactivated")
        self._save_meta(name)
        self.loaded_this_session.add(name)

    def pin(self, name: str):
        if name in self.skills:
            self.skills[name]["pinned"] = True
            self.skills[name]["state"] = "pinned"
            self._save_meta(name)

    def _save_meta(self, name: str):
        if name in self.skills:
            skill = self.skills[name]
            meta = {k: skill[k] for k in ("state", "pinned", "source", "last_activity_at", "created_at")}
            Path(skill["path"]).joinpath(".skill_meta.json").write_text(json.dumps(meta, indent=2))

    def list_visible(self) -> list:
        return [s for s in self.skills.values() if s.get("state") != "archived"]

    def find_matching(self, hint: str) -> str | None:
        keywords = set(re.findall(r"\w+", hint.lower()))
        for name, s in self.skills.items():
            skill_words = set(re.findall(r"\w+", (s.get("description", "") + name).lower()))
            if keywords & skill_words: return name
        return None

skills = SkillRegistry()

# ═══════════════════════════════════════════════════════════
# Layer 3: Curator (s07, s08)
# ═══════════════════════════════════════════════════════════

class Curator:
    def __init__(self):
        self.state_file = SKILLS_DIR / ".curator_state.json"
        self.last_run_at: datetime | None = None
        self.paused: bool = False
        self._load()

    def _load(self):
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            if data.get("last_run_at"):
                self.last_run_at = datetime.fromisoformat(data["last_run_at"])
            self.paused = data.get("paused", False)

    def save(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "paused": self.paused,
        }))

    def should_run(self, idle_seconds: float = 9999) -> bool:
        if self.paused: return False
        if not self.last_run_at: return True
        if (datetime.now() - self.last_run_at).total_seconds() / 3600 < config.curator_interval_hours:
            return False
        if (idle_seconds / 3600) < config.curator_min_idle_hours:
            return False
        return True

    def phase1_auto_transitions(self, dry_run: bool = False) -> list:
        """纯规则状态转换"""
        transitions = []
        now = datetime.now()
        for name, skill in list(skills.skills.items()):
            if skill.get("pinned"): continue
            if skill.get("source") in ("bundled", "hub"): continue

            try: last = datetime.fromisoformat(skill.get("last_activity_at", ""))
            except: continue
            days = (now - last).days

            if skill.get("state") == "active" and days >= config.stale_after_days:
                if not dry_run:
                    skill["state"] = "stale"; skills._save_meta(name)
                transitions.append({"skill": name, "from": "active", "to": "stale", "days": days})
            elif skill.get("state") == "stale" and days >= config.archive_after_days:
                if not dry_run:
                    skill["state"] = "archived"
                    src = Path(skill["path"])
                    if src.exists():
                        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                        dst = ARCHIVE_DIR / src.name
                        if not dst.exists(): shutil.move(str(src), str(dst))
                        skill["path"] = str(dst)
                    skills._save_meta(name)
                transitions.append({"skill": name, "from": "stale", "to": "archived", "days": days})

        if not dry_run:
            self.last_run_at = now; self.save()
        return transitions

    def phase2_llm_review(self, dry_run: bool = True) -> list:
        """LLM 审查合并"""
        candidates = {n: s for n, s in skills.skills.items()
                      if s.get("state") != "archived" and not s.get("pinned") and s.get("source") == "agent"}
        if len(candidates) < 2: return []

        catalog = "\n".join(f"- {n}: {s['description']}" for n, s in candidates.items())
        prompt = f"""You are a skill curator. Suggest mergers for these skills.

Three strategies:
a) merge_to_existing: patch umbrella + archive children
b) create_umbrella: new class-level skill + archive merged
c) demote_to_reference: move narrow skill → references/ of umbrella

Skills:{catalog}

Return JSON: {{"mergers": [{{"strategy": "...", "target": "...", "skills_to_merge": [...], "new_umbrella_name": "...",
"new_umbrella_description": "...", "new_umbrella_body": "...", "reason": "..."}}]}}
Return [] if no good candidates."""
        try:
            response = CLIENT.messages.create(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=2000)
            text = extract_text(response.content)
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match: return []
            mergers = json.loads(match.group()).get("mergers", [])

            if dry_run:
                print(f"  [Curator:LLM DRY RUN] {len(mergers)} suggested")
                return mergers

            applied = []
            for m in mergers:
                strategy = m["strategy"]
                merge_list = m.get("skills_to_merge", [])
                if strategy == "create_umbrella":
                    skills.create(m["new_umbrella_name"], m.get("new_umbrella_description", ""), m.get("new_umbrella_body", ""))
                    for sn in merge_list:
                        if sn in skills.skills:
                            skills.add_reference(m["new_umbrella_name"], sn, skills.skills[sn].get("content", ""))
                            skills.skills[sn]["state"] = "archived"
                            skills._save_meta(sn)
                    applied.append(m)
                elif strategy == "merge_to_existing":
                    target = m.get("target", "")
                    if target in skills.skills:
                        for sn in merge_list:
                            if sn in skills.skills and sn != target:
                                skills.patch_skill(target, skills.skills[sn].get("content", ""))
                                skills.skills[sn]["state"] = "archived"
                                skills._save_meta(sn)
                        applied.append(m)
            return applied
        except Exception as e:
            print(f"  ⚠️ [Curator:LLM] failed: {e}")
            return []

curator = Curator()

# ═══════════════════════════════════════════════════════════
# Layer 6: Insights (s10)
# ═══════════════════════════════════════════════════════════

class InsightsTracker:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init()
        self.session_id = None
        self.turns = 0
        self.tool_calls = 0

    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT, model TEXT, turn_count INTEGER DEFAULT 0,
                tool_calls INTEGER DEFAULT 0, input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS tool_events (id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER, tool_name TEXT, created_at TEXT, duration_ms INTEGER);
            CREATE TABLE IF NOT EXISTS memory_events (id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER, event_type TEXT, created_at TEXT, count INTEGER);
            CREATE TABLE IF NOT EXISTS skill_events (id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER, event_type TEXT, skill_name TEXT, created_at TEXT);
        """)
        self.conn.commit()

    def start_session(self):
        cur = self.conn.execute("INSERT INTO sessions (started_at, model) VALUES (?,?)",
                                (datetime.now().isoformat(), MODEL))
        self.session_id = cur.lastrowid
        self.turns = 0
        self.tool_calls = 0

    def record_turn(self): self.turns += 1

    def record_tool(self, name: str, ms: float = 0):
        self.tool_calls += 1
        self.conn.execute("INSERT INTO tool_events (session_id, tool_name, created_at, duration_ms) VALUES (?,?,?,?)",
                          (self.session_id, name, datetime.now().isoformat(), int(ms)))

    def record_memory(self, etype: str, count: int = 1):
        self.conn.execute("INSERT INTO memory_events (session_id, event_type, created_at, count) VALUES (?,?,?,?)",
                          (self.session_id, etype, datetime.now().isoformat(), count))

    def record_skill_event(self, etype: str, name: str):
        self.conn.execute("INSERT INTO skill_events (session_id, event_type, skill_name, created_at) VALUES (?,?,?,?)",
                          (self.session_id, etype, name, datetime.now().isoformat()))

    def end_session(self):
        if self.session_id:
            self.conn.execute("UPDATE sessions SET turn_count=?, tool_calls=? WHERE id=?",
                              (self.turns, self.tool_calls, self.session_id))
        self.conn.commit()

    def report(self, days: int = 30) -> str:
        row = self.conn.execute("""
            SELECT COUNT(*), COALESCE(SUM(turn_count),0), COALESCE(SUM(tool_calls),0)
            FROM sessions WHERE started_at >= date('now', ? || ' days')
        """, (f"-{days}",)).fetchone()
        tool_rows = self.conn.execute("""
            SELECT tool_name, COUNT(*) FROM tool_events
            WHERE created_at >= date('now', ? || ' days')
            GROUP BY tool_name ORDER BY COUNT(*) DESC LIMIT 5
        """, (f"-{days}",)).fetchall()
        mem_rows = self.conn.execute("""
            SELECT event_type, SUM(count) FROM memory_events
            WHERE created_at >= date('now', ? || ' days')
            GROUP BY event_type
        """, (f"-{days}",)).fetchall()

        report = f"📊 Insights ({days}d): {row[0]} sessions, {row[1]} turns, {row[2]} tools\n"
        if tool_rows:
            report += "Tools: " + ", ".join(f"{t[0]}={t[1]}" for t in tool_rows) + "\n"
        if mem_rows:
            report += "Memory: " + ", ".join(f"{m[0]}={m[1]}" for m in mem_rows)
        return report

tracker = InsightsTracker()

# ═══════════════════════════════════════════════════════════
# Layer 1: Background Review (s02, s03)
# ═══════════════════════════════════════════════════════════

def background_memory_review(msgs: list):
    print("\n  ⏳ [BG:Memory] reviewing...")
    dialogue = format_snapshot(msgs[-12:])
    prompt = f"""Review this conversation for memories (preferences, feedback, facts, refs).
Conversation:\n{dialogue}\nReturn JSON array of memories or []."""
    try:
        response = CLIENT.messages.create(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=500)
        text = extract_text(response.content)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            mems = json.loads(match.group())
            count = 0
            for m in mems:
                if isinstance(m, dict) and "name" in m:
                    memory.write(m["name"], m.get("mem_type", "user"), m.get("description", ""), m.get("body", ""))
                    count += 1
            if count:
                print(f"  ✅ [BG:Memory] {count} saved")
                tracker.record_memory("extract", count)
    except Exception as e:
        print(f"  ⚠️ [BG:Memory] {e}")


def background_skill_review(msgs: list):
    print("\n  ⏳ [BG:Skill] reviewing...")
    dialogue = format_snapshot(msgs[-16:])
    loaded = ", ".join(skills.loaded_this_session) if skills.loaded_this_session else "none"
    available = ", ".join(skills.skills.keys()) if skills.skills else "none"

    prompt = f"""Review for skill signals (priority: correction > technique > outdated > repeated).
Loaded: {loaded}. Available: {available}.
Conversation:\n{dialogue}
Return JSON: {{"signals": [{{"action": "create|update|append", "skill_name": "...",
"skill_description": "...", "skill_body": "...", "signal_type": "..."}}]}} or []."""
    try:
        response = CLIENT.messages.create(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=1000)
        text = extract_text(response.content)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            for sig in result.get("signals", []):
                body = sig.get("skill_body", "")
                name = sig.get("skill_name", "")
                if is_forbidden(body):
                    print(f"  🚫 Forbidden: {name}")
                    continue
                action = sig.get("action", "create")
                if action == "update" and name in skills.skills:
                    skills.update(name, body)
                elif action == "append":
                    umbrella = skills.find_matching(name)
                    if umbrella: skills.add_reference(umbrella, name, body)
                else:
                    skills.create(name, sig.get("skill_description", name), body)
                tracker.record_skill_event(action, name)
            if result.get("signals"):
                print(f"  ✅ [BG:Skill] {len(result['signals'])} applied")
    except Exception as e:
        print(f"  ⚠️ [BG:Skill] {e}")

# ═══════════════════════════════════════════════════════════
# Layer 5: Context Management (s09)
# ═══════════════════════════════════════════════════════════

def should_compact(msgs: list) -> bool:
    return sum(len(json.dumps(m.get("content", ""), ensure_ascii=False)) for m in msgs) // 4 > config.compact_threshold

def compact_messages(msgs: list) -> list:
    if len(msgs) <= 9: return msgs
    head = msgs[:3]; tail = msgs[-6:]; middle = msgs[3:-6]
    dialogue = format_snapshot(middle)
    try:
        response = CLIENT.messages.create(model=MODEL,
            messages=[{"role": "user", "content": f"Summarize:\n{dialogue}"}], max_tokens=500)
        summary = extract_text(response.content)
    except:
        summary = f"[{len(middle)} messages compressed]"
    return list(head) + [{"role": "user", "content": f"<summary>\n{summary}\n</summary>"}] + list(tail)

# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def extract_text(content) -> str:
    if isinstance(content, str): return content
    parts = []
    for block in content:
        if hasattr(block, "text"): parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text": parts.append(block.get("text", ""))
    return "\n".join(parts)

def format_snapshot(msgs: list) -> str:
    out = ""
    for m in msgs:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text": parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use": parts.append(f"[tool: {block.get('name', '?')}]")
                    elif block.get("type") == "tool_result": parts.append(f"[result: {str(block.get('content', ''))[:80]}]")
            content = " ".join(parts)
        out += f"[{role}] {str(content)[:400]}\n"
    return out

# ── Tools ─────────────────────────────────────────────

BASH_TOOL = {"name": "bash", "description": "Execute a shell command.",
             "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}
LOAD_SKILL_TOOL = {"name": "load_skill", "description": "Load a skill's full content by name.",
                   "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}
MEMORY_SEARCH_TOOL = {"name": "memory_search", "description": "Search persistent memory.",
                      "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}

TOOLS = [BASH_TOOL, LOAD_SKILL_TOOL, MEMORY_SEARCH_TOOL]

def run_bash(command: str) -> str:
    import subprocess
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=os.getcwd())
        return r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr else "") or "(no output)"
    except subprocess.TimeoutExpired: return "Command timed out"
    except Exception as e: return f"Error: {e}"

def load_skill_handler(name: str) -> str:
    if name not in skills.skills: return f"Skill not found: {name}"
    s = skills.skills[name]
    if s.get("state") == "archived": return f"Skill '{name}' is archived."
    skills.record_usage(name)
    sf = Path(s["path"]) / "SKILL.md"
    return sf.read_text(encoding="utf-8") if sf.exists() else "File not found"

def memory_search_handler(query: str) -> str:
    results = memory.search(query)
    if not results: return "No memories found."
    return "\n".join(f"- [{r['mem_type']}] {r['name']}: {r['description']}" for r in results)

TOOL_HANDLERS = {"bash": run_bash, "load_skill": load_skill_handler, "memory_search": memory_search_handler}

def execute_tools(content) -> list:
    results = []
    for block in content:
        name, input_data, block_id = None, None, None
        if hasattr(block, "type") and block.type == "tool_use":
            name, input_data, block_id = block.name, block.input, block.id
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            name, input_data, block_id = block["name"], block["input"], block["id"]
        if name and name in TOOL_HANDLERS:
            t0 = time.time()
            output = TOOL_HANDLERS[name](**(input_data or {}))
            tracker.record_tool(name, (time.time() - t0) * 1000)
            results.append({"type": "tool_result", "tool_use_id": block_id, "content": str(output)})
    return results

def build_system() -> str:
    parts = []
    mem_block = memory.system_block()
    if mem_block: parts.append(mem_block)

    visible = skills.list_visible()
    skill_lines = []
    for s in visible:
        tag = f" [{s.get('state', '').upper()}]" if s.get("state") != "active" else ""
        skill_lines.append(f"- **{s['name']}**{tag}: {s['description']}")
    parts.append("Skills:\n" + ("\n".join(skill_lines) if skill_lines else "(none)"))
    parts.append("Use load_skill for details, memory_search to find memories.")

    return "\n\n".join(parts)

# ═══════════════════════════════════════════════════════════
# Agent Loop
# ═══════════════════════════════════════════════════════════

class AgentState:
    def __init__(self):
        self.messages: list = []
        self.turn_count: int = 0
        self.tool_iterations: int = 0

def self_evolving_agent_loop(query: str, client, state: AgentState):
    state.messages.append({"role": "user", "content": query})

    while True:
        # Pre-turn: inject memory + skills
        system = build_system()

        # Context compaction
        if should_compact(state.messages):
            print("  [Compact] condensing context...")
            state.messages = compact_messages(state.messages)

        response = client.messages.create(
            model=MODEL, system=system,
            messages=state.messages, tools=TOOLS,
            max_tokens=8000,
        )
        state.messages.append({"role": "assistant", "content": response.content})
        state.turn_count += 1
        tracker.record_turn()

        if response.stop_reason != "tool_use":
            # Post-turn background review
            if state.turn_count % config.memory_nudge_interval == 0:
                background_memory_review(state.messages)
            if state.tool_iterations > 0 and state.tool_iterations % config.skill_nudge_interval == 0:
                background_skill_review(state.messages)
                state.tool_iterations = 0
            return response

        results = execute_tools(response.content)
        state.messages.append({"role": "user", "content": results})
        state.tool_iterations += 1

        # Mid-turn nudge
        if state.tool_iterations > 0 and state.tool_iterations % config.skill_nudge_interval == 0:
            background_skill_review(state.messages)
            state.tool_iterations = 0

        if state.turn_count % config.memory_nudge_interval == 0:
            background_memory_review(state.messages)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    skills.scan()
    tracker.start_session()

    print("=" * 60)
    print("s12: Complete Self-Evolving Agent — 六层归位")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Skills: {len(skills.skills)} ({len(skills.list_visible())} visible)")
    print(f"Memory entries: {len(memory.search('', 100))}")
    print(f"Config: memory_nudge={config.memory_nudge_interval}, skill_nudge={config.skill_nudge_interval}")
    print()
    print("六层自进化架构已全部就位:")
    print("  1. 实时学习 (Background Review)")
    print("  2. 技能管理 (Lifecycle)")
    print("  3. 长期维护 (Curator)")
    print("  4. 记忆系统 (Memory)")
    print("  5. 上下文管理 (Context)")
    print("  6. 数据分析 (Insights)")
    print()
    print("Commands:")
    print("  /skills    — 列出技能")
    print("  /memories  — 搜索记忆")
    print("  /insights  — 查看统计")
    print("  /curator   — 运行 Curator (dry-run)")
    print("  /curator!  — 运行 Curator (实际)")
    print("  /pin <n>   — 固定技能")
    print("  /exit      — 退出")
    print()

    state = AgentState()
    last_activity = time.time()

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!"); break

        if not query: continue
        last_activity = time.time()

        if query == "/exit": break
        elif query == "/skills":
            for s in skills.list_visible():
                tag = f" [{s.get('state', '')}]" if s.get("state") != "active" else ""
                if s.get("pinned"): tag += " 📌"
                print(f"  {tag} {s['name']}: {s['description']}")
            print()
        elif query.startswith("/memories"):
            q = query.split(maxsplit=1)[1] if len(query.split()) > 1 else ""
            for r in memory.search(q, 10):
                print(f"  [{r['mem_type']}] {r['name']}: {r['description']}")
            print()
        elif query == "/insights":
            print(tracker.report(30))
            print()
        elif query == "/curator":
            t = curator.phase1_auto_transitions(dry_run=True)
            for tr in t: print(f"  [DRY] {tr['skill']}: {tr['from']} → {tr['to']} ({tr['days']}d)")
            m = curator.phase2_llm_review(dry_run=True)
            print(f"  [DRY] {len(m)} LLM merge suggestions")
            print()
        elif query == "/curator!":
            t = curator.phase1_auto_transitions(dry_run=False)
            for tr in t: print(f"  {tr['skill']}: {tr['from']} → {tr['to']} ({tr['days']}d)")
            m = curator.phase2_llm_review(dry_run=False)
            print(f"  Applied {len(m)} LLM mergers")
            print()
        elif query.startswith("/pin "):
            skills.pin(query.split()[-1])
            print()
        else:
            response = self_evolving_agent_loop(query, CLIENT, state)
            print(extract_text(response.content))
            print()

    # Cleanup
    tracker.end_session()
    memory.close()
    print(f"\n{tracker.report(1)}")


if __name__ == "__main__":
    main()
