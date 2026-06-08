"""
s05: Skill Lifecycle — 技能的生老病死

active → stale → archived 状态机 + Umbrella 结构 + pin 豁免。
技能来源区分: bundled / hub / agent-created。

Usage:
    python s05_skill_lifecycle/code.py
"""

import json
import os
import re
import shutil
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path

from llm import get_client
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

SKILLS_DIR = Path(".skills")
ARCHIVE_DIR = SKILLS_DIR / ".archive"

# ── Config ────────────────────────────────────────────

@dataclass
class CuratorConfig:
    enabled: bool = True
    stale_after_days: int = 30
    archive_after_days: int = 90
    prune_builtins: bool = False

curator_config = CuratorConfig()

# ── Skill Record ──────────────────────────────────────

@dataclass
class SkillRecord:
    name: str
    description: str = ""
    state: str = "active"      # active | stale | archived | pinned
    source: str = "agent"      # bundled | hub | agent-created
    last_activity_at: str = ""
    created_at: str = ""
    pinned: bool = False
    path: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "state": self.state, "source": self.source,
            "last_activity_at": self.last_activity_at,
            "created_at": self.created_at, "pinned": self.pinned,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SkillRecord":
        return cls(**{k: d.get(k, "") for k in [
            "name", "description", "state", "source",
            "last_activity_at", "created_at", "pinned", "path",
        ]})


# ── Skill Registry ────────────────────────────────────

class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, SkillRecord] = {}
        self.simulated_now: datetime | None = None  # for testing

    def now(self) -> datetime:
        return self.simulated_now or datetime.now()

    def scan(self):
        """扫描 skills/ 目录，加载所有技能"""
        self.skills.clear()
        if not self.skills_dir.exists():
            return

        for d in sorted(self.skills_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            skill_file = d / "SKILL.md"
            if not skill_file.exists():
                continue

            content = skill_file.read_text(encoding="utf-8")
            meta = self._parse_meta(d, content)
            self.skills[meta.name] = meta

        # Also scan archive
        if ARCHIVE_DIR.exists():
            for d in sorted(ARCHIVE_DIR.iterdir()):
                if not d.is_dir():
                    continue
                skill_file = d / "SKILL.md"
                if not skill_file.exists():
                    continue
                content = skill_file.read_text(encoding="utf-8")
                meta = self._parse_meta(d, content)
                meta.state = "archived"
                meta.path = str(d)
                self.skills[meta.name] = meta

    def _parse_meta(self, dir_path: Path, content: str) -> SkillRecord:
        name = dir_path.name
        desc = ""
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                desc = line.lstrip("# ").strip()
                break

        # Check for a metadata file
        meta_file = dir_path / ".skill_meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            return SkillRecord.from_dict(meta)

        now = self.now().isoformat()
        return SkillRecord(
            name=name, description=desc,
            state="active", source="agent",
            last_activity_at=now, created_at=now,
            path=str(dir_path),
        )

    def create(self, name: str, description: str, body: str):
        """创建新技能"""
        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        content = f"# {description}\n\n{body}"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        now = self.now().isoformat()
        record = SkillRecord(
            name=name, description=description,
            state="active", source="agent",
            last_activity_at=now, created_at=now,
            path=str(skill_dir),
        )
        self.skills[name] = record
        self._save_meta(skill_dir, record)
        print(f"  [Skill] created '{name}'")

    def update(self, name: str, body: str):
        """更新已有技能"""
        if name not in self.skills:
            return
        skill_dir = Path(self.skills[name].path)
        (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
        self._touch(name)
        print(f"  [Skill] updated '{name}'")

    def add_reference(self, name: str, ref_name: str, content: str):
        """在技能下添加 references/ 文件"""
        if name not in self.skills:
            return
        skill_dir = Path(self.skills[name].path)
        refs_dir = skill_dir / "references"
        refs_dir.mkdir(exist_ok=True)
        (refs_dir / f"{ref_name}.md").write_text(content)
        self._touch(name)
        print(f"  [Skill] added reference '{ref_name}' to '{name}'")

    def _touch(self, name: str):
        if name in self.skills:
            self.skills[name].last_activity_at = self.now().isoformat()
            self._save_meta(Path(self.skills[name].path), self.skills[name])

    def record_activity(self, name: str):
        """记录技能使用（每次被 load_skill 时调用）"""
        if name not in self.skills:
            return
        skill = self.skills[name]
        skill.last_activity_at = self.now().isoformat()

        # 如果 stale 的被再次使用，重新激活
        if skill.state == "stale":
            skill.state = "active"
            print(f"  [Skill] {name}: stale → active (reactivated)")

        self._save_meta(Path(skill.path), skill)

    def pin(self, name: str):
        if name in self.skills:
            self.skills[name].pinned = True
            self.skills[name].state = "pinned"
            self._save_meta(Path(self.skills[name].path), self.skills[name])
            print(f"  [Skill] pinned '{name}'")

    def unpin(self, name: str):
        if name in self.skills:
            self.skills[name].pinned = False
            self.skills[name].state = "active"
            self._save_meta(Path(self.skills[name].path), self.skills[name])
            print(f"  [Skill] unpinned '{name}'")

    def _save_meta(self, dir_path: Path, record: SkillRecord):
        meta_file = dir_path / ".skill_meta.json"
        meta_file.write_text(json.dumps(record.to_dict(), indent=2))

    def list_active(self) -> list[SkillRecord]:
        return [s for s in self.skills.values()
                if s.state in ("active", "stale", "pinned")]

    def list_all(self) -> list[SkillRecord]:
        return list(self.skills.values())

    def _save_meta(self, dir_path: Path, record: SkillRecord):
        meta_file = dir_path / ".skill_meta.json"
        meta_file.write_text(json.dumps(record.to_dict(), indent=2))

    def list_active(self) -> list[SkillRecord]:
        return [s for s in self.skills.values()
                if s.state in ("active", "stale", "pinned")]

    def list_all(self) -> list[SkillRecord]:
        return list(self.skills.values())


# ── Curator: Auto State Transitions ────────────────────

def apply_automatic_transitions(registry: SkillRegistry, config: CuratorConfig):
    """Curator 阶段 1：纯规则自动状态转换（零 LLM 成本）"""
    print("\n  ── Curator Phase 1: Auto Transitions ──")
    now = registry.now()
    changes = 0

    for name, skill in list(registry.skills.items()):
        if skill.pinned or skill.state == "pinned":
            continue
        if skill.source in ("bundled", "hub") and not config.prune_builtins:
            continue

        days_inactive = (now - datetime.fromisoformat(skill.last_activity_at)).days

        if skill.state == "active" and days_inactive >= config.stale_after_days:
            skill.state = "stale"
            registry._save_meta(Path(skill.path), skill)
            print(f"    {name}: active → stale ({days_inactive}d inactive)")
            changes += 1

        elif skill.state == "stale" and days_inactive >= config.archive_after_days:
            skill.state = "archived"
            _archive_skill(skill)
            registry._save_meta(Path(skill.path), skill)
            print(f"    {name}: stale → archived ({days_inactive}d inactive)")
            changes += 1

    if changes == 0:
        print("    (no transitions)")
    print(f"    Total: {changes} transitions")
    return changes


def _archive_skill(skill: SkillRecord):
    """将技能移到 .archive/ 目录（保留文件，可恢复）"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(skill.path)
    dst = ARCHIVE_DIR / src.name
    if src.exists() and not dst.exists():
        shutil.move(str(src), str(dst))
        skill.path = str(dst)


# ── Tools ─────────────────────────────────────────────

BASH_TOOL = {
    "name": "bash",
    "description": "Execute a shell command.",
    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
}

LOAD_SKILL_TOOL = {
    "name": "load_skill",
    "description": "Load a skill's full content by name.",
    "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
}

def run_bash(command: str) -> str:
    import subprocess
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=os.getcwd())
        return r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr else "") or "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error: {e}"

TOOL_HANDLERS = {"bash": run_bash}

registry = SkillRegistry(SKILLS_DIR)

def load_skill_handler(name: str) -> str:
    if name not in registry.skills:
        return f"Skill not found: {name}"
    skill = registry.skills[name]

    if skill.state == "archived":
        return f"Skill '{name}' is archived. Use 'curator restore {name}' to restore it."

    # Record activity
    registry.record_activity(name)

    skill_file = Path(skill.path) / "SKILL.md"
    if skill_file.exists():
        return skill_file.read_text(encoding="utf-8")
    return f"Skill file not found: {name}"

TOOL_HANDLERS["load_skill"] = load_skill_handler

def build_system() -> str:
    active = registry.list_active()
    if not active:
        catalog = "(no skills available)"
    else:
        lines = []
        for s in active:
            tag = " [STALE]" if s.state == "stale" else ""
            tag = " [PINNED]" if s.state == "pinned" else tag
            lines.append(f"- **{s.name}**{tag}: {s.description}")
        catalog = "\n".join(lines)

    return (
        f"You are a helpful coding agent.\n\n"
        f"Available skills:\n{catalog}\n\n"
        "Use load_skill to get full details."
    )


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
    tools = [BASH_TOOL, LOAD_SKILL_TOOL]

    while True:
        system = build_system()
        response = client.messages.create(
            model=MODEL, system=system, messages=messages,
            tools=tools, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return response
        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})


# ── Main ──────────────────────────────────────────────

def main():
    registry.scan()

    print("=" * 60)
    print("s05: Skill Lifecycle — 技能的生老病死")
    print("=" * 60)
    print(f"Active skills: {len(registry.list_active())}")
    print(f"Config: stale={curator_config.stale_after_days}d, archive={curator_config.archive_after_days}d")
    print()
    print("Commands:")
    print("  /skills          — 列出所有技能及状态")
    print("  /create <name>   — 创建测试技能")
    print("  /pin <name>      — 固定技能")
    print("  /simulate-time N — 模拟 N 天后")
    print("  /curator         — 运行自动状态转换")
    print("  /exit            — 退出")
    print()

    messages = []

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!"); break

        if not query: continue

        if query == "/exit":
            break
        elif query == "/skills":
            for s in registry.list_all():
                status = f"[{s.state}]"
                if s.pinned: status += " 📌"
                days = (registry.now() - datetime.fromisoformat(s.last_activity_at)).days
                print(f"  {status} {s.name} (last used: {days}d ago)")
            print()
            continue
        elif query.startswith("/simulate-time "):
            days = int(query.split()[-1])
            registry.simulated_now = datetime.now() + timedelta(days=days)
            print(f"  Simulated: {registry.now().isoformat()} (+{days}d)")
            continue
        elif query == "/curator":
            apply_automatic_transitions(registry, curator_config)
            continue
        elif query.startswith("/pin "):
            registry.pin(query.split()[-1])
            continue
        elif query.startswith("/create "):
            name = query.split()[-1]
            registry.create(name, f"Auto-created skill: {name}", f"# {name}\n\nAuto-created test skill.")
            continue

        response = agent_loop(query, CLIENT, messages)
        print(extract_text(response.content))
        print()


if __name__ == "__main__":
    main()
