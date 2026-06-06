"""
s07: Curator — 自动状态转换 (Phase 1)

纯规则驱动的技能自动状态转换：active → stale → archived。
空闲触发机制 + dry-run 预览 + pin 豁免。

Usage:
    python s07_curator_state/code.py
"""

import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from llm import get_client
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

SKILLS_DIR = Path(".skills")
ARCHIVE_DIR = SKILLS_DIR / ".archive"
STATE_FILE = SKILLS_DIR / ".curator_state.json"

# ── Config ────────────────────────────────────────────

class CuratorConfig:
    enabled: bool = True
    interval_hours: int = 168          # 7 天
    min_idle_hours: int = 2            # 空闲阈值
    stale_after_days: int = 30
    archive_after_days: int = 90
    prune_builtins: bool = False

config = CuratorConfig()

# ── Curator State ─────────────────────────────────────

class CuratorState:
    def __init__(self):
        self.last_run_at: datetime | None = None
        self.paused: bool = False
        self.simulated_now: datetime | None = None
        self._load()

    def _load(self):
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            if data.get("last_run_at"):
                self.last_run_at = datetime.fromisoformat(data["last_run_at"])
            self.paused = data.get("paused", False)

    def save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "paused": self.paused,
        }, indent=2))

    def now(self) -> datetime:
        return self.simulated_now or datetime.now()

    def hours_since_last_run(self) -> float:
        if not self.last_run_at:
            return float("inf")
        return (self.now() - self.last_run_at).total_seconds() / 3600

    def should_run(self, idle_seconds: float = 9999) -> bool:
        if self.paused:
            return False
        if not config.enabled:
            return False
        if self.hours_since_last_run() < config.interval_hours:
            return False
        if (idle_seconds / 3600) < config.min_idle_hours:
            return False
        return True

curator_state = CuratorState()

# ── Skill Record ──────────────────────────────────────

class SkillRecord:
    def __init__(self, name: str, description: str = "", state: str = "active",
                 source: str = "agent", last_activity_at: str = "", created_at: str = "",
                 pinned: bool = False, path: str = ""):
        self.name = name
        self.description = description
        self.state = state
        self.source = source
        self.last_activity_at = last_activity_at or curator_state.now().isoformat()
        self.created_at = created_at or curator_state.now().isoformat()
        self.pinned = pinned
        self.path = path

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d: dict) -> "SkillRecord":
        return cls(**d)


class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, SkillRecord] = {}

    def scan(self):
        self.skills.clear()
        dirs = [(self.skills_dir, "active")]
        if ARCHIVE_DIR.exists():
            dirs.append((ARCHIVE_DIR, "archived"))

        for base_dir, default_state in dirs:
            if not base_dir.exists():
                continue
            for d in sorted(base_dir.iterdir()):
                if not d.is_dir() or d.name.startswith("."):
                    continue
                sf = d / "SKILL.md"
                if not sf.exists():
                    continue

                meta_file = d / ".skill_meta.json"
                if meta_file.exists():
                    record = SkillRecord.from_dict(json.loads(meta_file.read_text()))
                else:
                    content = sf.read_text(encoding="utf-8")
                    desc = ""
                    for line in content.split("\n"):
                        if line.strip().startswith("# "):
                            desc = line.strip().lstrip("# ").strip()
                            break
                    record = SkillRecord(name=d.name, description=desc, state=default_state, path=str(d))

                self.skills[record.name] = record

    def create(self, name: str, description: str, body: str, source: str = "agent"):
        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {description}\n\n{body}", encoding="utf-8")
        record = SkillRecord(name=name, description=description, state="active", source=source, path=str(skill_dir))
        self.skills[name] = record
        self._save_meta(record)
        print(f"  [Skill] created '{name}'")

    def _save_meta(self, record: SkillRecord):
        meta_file = Path(record.path) / ".skill_meta.json"
        meta_file.write_text(json.dumps(record.to_dict(), indent=2))

    def record_activity(self, name: str):
        if name in self.skills:
            skill = self.skills[name]
            skill.last_activity_at = curator_state.now().isoformat()
            if skill.state == "stale":
                skill.state = "active"
                print(f"  [Skill] {name}: reactivated")
            self._save_meta(skill)

    def pin(self, name: str):
        if name in self.skills:
            self.skills[name].pinned = True
            self.skills[name].state = "pinned"
            self._save_meta(self.skills[name])

    def unpin(self, name: str):
        if name in self.skills:
            self.skills[name].pinned = False
            self.skills[name].state = "active"
            self._save_meta(self.skills[name])

    def restore(self, name: str):
        """从归档恢复技能"""
        archived = ARCHIVE_DIR / name
        if not archived.exists():
            print(f"  Skill '{name}' not found in archive")
            return
        target = self.skills_dir / name
        shutil.move(str(archived), str(target))
        if name in self.skills:
            self.skills[name].state = "active"
            self.skills[name].path = str(target)
            self.skills[name].last_activity_at = curator_state.now().isoformat()
            self._save_meta(self.skills[name])
        print(f"  [Curator] restored '{name}' from archive")


registry = SkillRegistry(SKILLS_DIR)

# ── Curator Phase 1: Auto State Transitions ───────────

def apply_automatic_transitions(dry_run: bool = False) -> dict:
    """Curator 阶段 1：纯规则自动状态转换（零 LLM 成本）"""
    now = curator_state.now()
    report = {"transitions": [], "errors": [], "dry_run": dry_run}

    for name, skill in list(registry.skills.items()):
        # Pinned 豁免
        if skill.pinned or skill.state == "pinned":
            continue

        # Bundled/Hub 默认不触碰
        if skill.source in ("bundled", "hub") and not config.prune_builtins:
            continue

        try:
            last_active = datetime.fromisoformat(skill.last_activity_at)
        except (ValueError, TypeError):
            continue
        days_inactive = (now - last_active).days

        # Active → Stale
        if skill.state == "active" and days_inactive >= config.stale_after_days:
            if not dry_run:
                skill.state = "stale"
                registry._save_meta(skill)
            report["transitions"].append({
                "skill": name, "from": "active", "to": "stale",
                "days_inactive": days_inactive,
            })

        # Stale → Archived
        elif skill.state == "stale" and days_inactive >= config.archive_after_days:
            if not dry_run:
                skill.state = "archived"
                _archive_skill(skill)
                registry._save_meta(skill)
            report["transitions"].append({
                "skill": name, "from": "stale", "to": "archived",
                "days_inactive": days_inactive,
            })

        # Stale → Active (reactivated by usage)
        elif skill.state == "stale" and days_inactive < config.stale_after_days:
            if not dry_run:
                skill.state = "active"
                registry._save_meta(skill)
            report["transitions"].append({
                "skill": name, "from": "stale", "to": "active (reactivated)",
                "days_inactive": days_inactive,
            })

    if not dry_run:
        curator_state.last_run_at = now
        curator_state.save()

    return report


def _archive_skill(skill: SkillRecord):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(skill.path)
    dst = ARCHIVE_DIR / src.name
    if src.exists() and not dst.exists():
        shutil.move(str(src), str(dst))
        skill.path = str(dst)


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

def load_skill_handler(name: str) -> str:
    if name not in registry.skills:
        return f"Skill not found: {name}"
    skill = registry.skills[name]
    if skill.state == "archived":
        return f"Skill '{name}' is archived. Use /restore {name} to restore."
    registry.record_activity(name)
    sf = Path(skill.path) / "SKILL.md"
    return sf.read_text(encoding="utf-8") if sf.exists() else f"File not found"

TOOL_HANDLERS = {"bash": run_bash, "load_skill": load_skill_handler}

def build_system() -> str:
    lines = []
    for s in registry.skills.values():
        if s.state in ("archived",):
            continue
        tag = f" [{s.state.upper()}]" if s.state != "active" else ""
        lines.append(f"- **{s.name}**{tag}: {s.description}")
    return f"You are a coding agent.\n\nSkills:\n" + ("\n".join(lines) if lines else "(none)")

def extract_text(content) -> str:
    if isinstance(content, str): return content
    parts = []
    for block in content:
        if hasattr(block, "text"): parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text": parts.append(block.get("text", ""))
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
            results.append({"type": "tool_result", "tool_use_id": block_id, "content": str(output)})
    return results

def agent_loop(query: str, client, messages=None):
    if messages is None: messages = []
    messages.append({"role": "user", "content": query})
    while True:
        response = client.messages.create(
            model=MODEL, system=build_system(), messages=messages,
            tools=[BASH_TOOL, LOAD_SKILL_TOOL], max_tokens=8000)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use": return response
        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})


# ── Main ──────────────────────────────────────────────

def main():
    registry.scan()

    print("=" * 60)
    print("s07: Curator — 自动状态转换 (Phase 1: 纯规则)")
    print("=" * 60)
    print(f"Skills: {len(registry.skills)}")
    print(f"Config: stale={config.stale_after_days}d, archive={config.archive_after_days}d")
    print(f"Interval: {config.interval_hours}h ({config.interval_hours // 24}d)")
    print(f"Paused: {curator_state.paused}")
    if curator_state.last_run_at:
        print(f"Last run: {curator_state.last_run_at.isoformat()}")
    print()
    print("/skills       — 列出技能及状态")
    print("/create <n>   — 创建测试技能")
    print("/pin <n>      — 固定技能")
    print("/simulate N   — 模拟 N 天后")
    print("/curator      — 运行自动转换 (dry-run)")
    print("/curator!     — 运行自动转换 (实际执行)")
    print("/restore <n>  — 恢复已归档技能")
    print("/pause        — 暂停 Curator")
    print("/resume       — 恢复 Curator")
    print("/exit         — 退出")
    print()

    messages = []
    last_interaction = time.time()

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!"); break

        if not query: continue
        last_interaction = time.time()

        if query == "/exit": break
        elif query == "/skills":
            for s in sorted(registry.skills.values(), key=lambda x: x.name):
                status = f"[{s.state}]"
                if s.pinned: status += " 📌"
                try:
                    days = (curator_state.now() - datetime.fromisoformat(s.last_activity_at)).days
                except: days = "?"
                print(f"  {status} {s.name} ({days}d since last use)")
            print()

        elif query.startswith("/create "):
            name = query.split()[-1]
            registry.create(name, f"Skill: {name}", f"# {name}\n\nAuto-created skill for testing.")
        elif query.startswith("/pin "):
            registry.pin(query.split()[-1])
        elif query.startswith("/simulate "):
            days = int(query.split()[-1])
            curator_state.simulated_now = curator_state.now() + timedelta(days=days)
            print(f"  ⏰ Simulated time: {curator_state.now().isoformat()} (+{days}d)")
        elif query == "/curator":
            report = apply_automatic_transitions(dry_run=True)
            print_curator_report(report)
        elif query == "/curator!":
            report = apply_automatic_transitions(dry_run=False)
            print_curator_report(report)
        elif query.startswith("/restore "):
            registry.restore(query.split()[-1])
        elif query == "/pause":
            curator_state.paused = True; curator_state.save()
            print("  Curator paused")
        elif query == "/resume":
            curator_state.paused = False; curator_state.save()
            print("  Curator resumed")
        else:
            response = agent_loop(query, CLIENT, messages)
            print(extract_text(response.content))
        print()


def print_curator_report(report: dict):
    if report["dry_run"]:
        print("  [DRY RUN — no actual changes]")
    transitions = report["transitions"]
    if not transitions:
        print("  No transitions needed.")
    else:
        for t in transitions:
            arrow = "→"
            print(f"  {t['skill']}: {t['from']} {arrow} {t['to']} ({t['days_inactive']}d inactive)")


if __name__ == "__main__":
    main()
