"""
s08: Curator — LLM 审查与伞形合并 (Phase 2)

LLM 驱动的前缀聚类 + 三种合并策略 + 报告生成。
Fork 独立 agent 审查技能库，智能合并碎片化技能。

Usage:
    python s08_curator_llm/code.py
"""

import json
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from llm import get_client
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CURATOR_MODEL = os.getenv("CURATOR_MODEL_ID", MODEL)  # 可用便宜模型
CLIENT = get_client()

SKILLS_DIR = Path(".skills")
ARCHIVE_DIR = SKILLS_DIR / ".archive"
LOGS_DIR = Path(".hermes") / "logs" / "curator"

# ── Skill Registry (简版) ─────────────────────────────

class SkillRegistry:
    def __init__(self):
        self.skills: dict[str, dict] = {}

    def scan(self):
        self.skills.clear()
        for base_dir, default_state in [(SKILLS_DIR, "active"), (ARCHIVE_DIR, "archived")]:
            if not base_dir.exists():
                continue
            for d in sorted(base_dir.iterdir()):
                if not d.is_dir() or d.name.startswith("."):
                    continue
                sf = d / "SKILL.md"
                if not sf.exists():
                    continue
                content = sf.read_text(encoding="utf-8")
                desc = ""
                for line in content.split("\n"):
                    if line.strip().startswith("# "):
                        desc = line.strip().lstrip("# ").strip(); break
                self.skills[d.name] = {
                    "name": d.name, "description": desc, "state": default_state,
                    "source": "agent", "path": str(d), "content": content,
                    "pinned": False,
                }

    def create(self, name, desc, body, source="agent"):
        d = SKILLS_DIR / name; d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"# {desc}\n\n{body}", encoding="utf-8")
        self.skills[name] = {"name": name, "description": desc, "state": "active",
                             "source": source, "path": str(d), "content": body, "pinned": False}

    def archive(self, name):
        if name not in self.skills: return
        skill = self.skills[name]
        src = Path(skill["path"])
        if src.exists():
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            dst = ARCHIVE_DIR / src.name
            if not dst.exists():
                shutil.move(str(src), str(dst))
                skill["path"] = str(dst)
        skill["state"] = "archived"

    def add_reference(self, umbrella, ref_name, content):
        if umbrella not in self.skills: return
        ref_dir = Path(self.skills[umbrella]["path"]) / "references"
        ref_dir.mkdir(exist_ok=True)
        (ref_dir / f"{ref_name}.md").write_text(content)

    def patch_skill(self, name, append_body):
        if name not in self.skills: return
        skill_file = Path(self.skills[name]["path"]) / "SKILL.md"
        current = skill_file.read_text(encoding="utf-8")
        skill_file.write_text(current + "\n\n## Additional Patterns\n\n" + append_body)
        self.skills[name]["content"] = skill_file.read_text(encoding="utf-8")


registry = SkillRegistry()

# ── Curator Phase 2: LLM Review ──────────────────────

def curator_llm_review(dry_run: bool = True) -> dict:
    """Curator 阶段 2：LLM 审查技能库，建议合并"""
    print("\n  ⏳ [Curator:LLM] 启动技能库审查...")

    # 只审查 agent 创建的、非 archived、非 pinned 的技能
    candidates = {
        name: s for name, s in registry.skills.items()
        if s["state"] != "archived" and not s["pinned"]
        and s.get("source", "agent") == "agent"
    }

    if len(candidates) < 2:
        print("  [Curator:LLM] 技能太少，跳过合并审查")
        return {"mergers": [], "dry_run": dry_run}

    # 构建技能目录供 LLM 审查
    catalog = "\n".join(
        f"- {name}: {s['description']}" for name, s in candidates.items()
    )

    prompt = f"""You are a skill library curator. Review these skills and suggest mergers.

RULES:
1. ONLY merge agent-created skills (NOT bundled or hub-installed)
2. Archive merged skills — NEVER delete
3. Prefer umbrella skills with references/ sub-files over many narrow skills
4. Pinned skills are exempt — do not touch them
5. Group by prefix clusters (e.g., "python-*", "react-*", "deploy-*")

THREE MERGE STRATEGIES:
a) merge_to_existing: append to an existing umbrella skill, then archive children
b) create_umbrella: create a new class-level skill, archive the merged skills
c) demote_to_reference: move narrow skill content into references/ of an umbrella

Current skills:
{catalog}

Return JSON:
{{"mergers": [
  {{"strategy": "merge_to_existing|create_umbrella|demote_to_reference",
    "target": "existing-skill (for merge_to_existing/demote)",
    "skills_to_merge": ["skill-name-1", "skill-name-2"],
    "new_umbrella_name": "name (for create_umbrella)",
    "new_umbrella_description": "description",
    "new_umbrella_body": "SKILL.md body",
    "reason": "why this merger"}}
]}}
Return {{"mergers": []}} if no good candidates."""
    try:
        response = CLIENT.messages.create(
            model=CURATOR_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            system="Return ONLY valid JSON. Be conservative — suggest only clear improvements.",
        )
        text = extract_text(response.content)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            print("  [Curator:LLM] 无合并建议")
            return {"mergers": [], "dry_run": dry_run}

        result = json.loads(match.group())
        mergers = result.get("mergers", [])

        if dry_run:
            print(f"  [DRY RUN] {len(mergers)} suggested mergers:")
            for m in mergers:
                print(f"    - {m['strategy']}: {m.get('skills_to_merge', [])}")
            return {"mergers": mergers, "dry_run": True}

        # 实际执行合并
        applied = []
        for m in mergers:
            strategy = m["strategy"]
            skills = m.get("skills_to_merge", [])

            if strategy == "merge_to_existing":
                target = m.get("target", "")
                if target and target in registry.skills:
                    for skill_name in skills:
                        if skill_name in registry.skills and skill_name != target:
                            content = registry.skills[skill_name].get("content", "")
                            registry.patch_skill(target, f"From {skill_name}:\n{content}")
                            registry.archive(skill_name)
                    applied.append(m)
                    print(f"  ✅ Merged {skills} → {target}")

            elif strategy == "create_umbrella":
                name = m.get("new_umbrella_name", "merged-skill")
                desc = m.get("new_umbrella_description", "Merged skill")
                body = m.get("new_umbrella_body", "")
                registry.create(name, desc, body)
                for skill_name in skills:
                    if skill_name in registry.skills:
                        content = registry.skills[skill_name].get("content", "")
                        registry.add_reference(name, skill_name, content)
                        registry.archive(skill_name)
                applied.append(m)
                print(f"  ✅ Created umbrella '{name}' from {skills}")

            elif strategy == "demote_to_reference":
                target = m.get("target", "")
                if target and target in registry.skills:
                    for skill_name in skills:
                        if skill_name in registry.skills:
                            content = registry.skills[skill_name].get("content", "")
                            registry.add_reference(target, skill_name, content)
                            registry.archive(skill_name)
                    applied.append(m)
                    print(f"  ✅ Demoted {skills} → references/{target}/")

        # 生成报告
        _generate_report(applied, mergers)
        return {"mergers": applied, "dry_run": False}

    except Exception as e:
        print(f"  ⚠️ [Curator:LLM] Review failed: {e}")
        return {"mergers": [], "dry_run": dry_run, "error": str(e)}


def _generate_report(applied: list, all_suggestions: list):
    """生成 Curator 运行报告"""
    run_dir = LOGS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    run_data = {
        "timestamp": datetime.now().isoformat(),
        "applied_mergers": len(applied),
        "total_suggestions": len(all_suggestions),
        "mergers": applied,
    }
    (run_dir / "run.json").write_text(json.dumps(run_data, indent=2, ensure_ascii=False))

    report = f"# Curator Report — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += f"## Summary\n\n- Mergers applied: {len(applied)}\n"
    report += f"- Total suggestions: {len(all_suggestions)}\n\n"
    if applied:
        report += "## Applied Mergers\n\n"
        for m in applied:
            report += f"- **{m['strategy']}**: {m.get('reason', 'no reason')}\n"
    (run_dir / "REPORT.md").write_text(report)
    print(f"  📄 Report: {run_dir}")


# ── Helpers ───────────────────────────────────────────

def extract_text(content) -> str:
    if isinstance(content, str): return content
    parts = []
    for block in content:
        if hasattr(block, "text"): parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text": parts.append(block.get("text", ""))
    return "\n".join(parts)


# ── Main ──────────────────────────────────────────────

def main():
    registry.scan()

    print("=" * 60)
    print("s08: Curator — LLM 审查与伞形合并 (Phase 2)")
    print("=" * 60)
    print(f"Review model: {CURATOR_MODEL}")
    print(f"Skills: {len(registry.skills)}")
    print()
    print("/skills           — 列出所有技能")
    print("/create <prefix>-<name>  — 创建测试技能 (用前缀分组)")
    print("/curator-review   — LLM 审查 (dry-run)")
    print("/curator-review!  — LLM 审查 (实际执行)")
    print("/exit             — 退出")
    print()

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!"); break

        if not query: continue
        if query == "/exit": break
        elif query == "/skills":
            for name, s in sorted(registry.skills.items()):
                status = f"[{s['state']}]"
                if s.get("pinned"): status += " 📌"
                print(f"  {status} {name}: {s['description']}")
            print()
        elif query.startswith("/create "):
            name = query.split()[-1]
            desc = f"Auto-created: {name}"
            body = f"# {name}\n\nThis is a test skill for the {name.split('-')[0] if '-' in name else 'general'} domain."
            registry.create(name, desc, body)
            print(f"  Created: {name}")
        elif query == "/curator-review":
            curator_llm_review(dry_run=True)
        elif query == "/curator-review!":
            curator_llm_review(dry_run=False)
        else:
            print(f"  Unknown command: {query}")
        print()


if __name__ == "__main__":
    main()
