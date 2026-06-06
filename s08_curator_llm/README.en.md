# s08: Curator — LLM Review & Umbrella Merging

[中文](README.md) · [English](README.en.md)

s01 → ... → s07 → `s08` → [s09](../s09_context_management/) → ... → s12
> *"Too many skills get messy — merge them periodically"* — LLM-driven prefix clustering + umbrella merging + demotion + report generation.
>
> **Self-Evolution Layer**: Long-term Maintenance (Curator) — Phase 2: LLM-powered intelligent merging.

---

## Problem

s07's Phase 1 solved the zombie skill problem (auto stale → archive). But there's another problem: skill **fragmentation**.

The agent auto-created 5 Python-related skills: `python-testing`, `python-linting`, `python-deploy`, `python-style`, `python-packaging`. Each is independent. Each consumes system prompt space. And they may conflict or overlap.

**Intelligent merging is needed — consolidating related narrow skills under umbrella skills.**

---

## Solution

**Curator Phase 2: LLM review & merging**. Fork an independent AIAgent (using a configurable auxiliary model) for prefix clustering and three merge strategies.

### Three Merge Strategies

| Strategy | Action | Use Case |
|----------|--------|----------|
| **a) merge_to_existing** | Patch umbrella + archive siblings | Related umbrella already exists |
| **b) create_umbrella** | New class-level skill + archive children | Multiple narrow skills group together |
| **c) demote_to_reference** | Move content into `references/` | Too narrow for standalone skill |

### Prefix Clustering

```python
# Skills: python-testing, python-linting, python-deploy,
#         react-components, react-hooks

# Detected clusters:
# Cluster "python": testing, linting, deploy
# Cluster "react": components, hooks

# Actions:
# → Create "python-development" umbrella, archive the three children
# → Create "react-patterns" umbrella, archive the two children
```

### Report System

Each Curator run generates reports under `~/.hermes/logs/curator/{YYYYMMDD-HHMMSS}/`:
- `run.json` — machine-readable complete record
- `REPORT.md` — human-readable review report

---

## Try It

```sh
python s08_curator_llm/code.py
```

Try: create 5-6 related skills (e.g., `python-X`, `python-Y`), trigger LLM review, observe clustering and merge suggestions.

---

## Next

Curator keeps the skill library clean. But as conversations grow longer, the context window fills up. Intelligent compression is needed.

s09 Context Management → conversation compression + trajectory compression + memory prefetch protection.

<details>
<summary>Deep Dive into Hermes Source</summary>

Curator Phase 2 (LLM review & merging) is in:

| File | Lines | Role |
|------|-------|------|
| `agent/curator.py` | 330-491 | `CURATOR_REVIEW_PROMPT`, merge strategy execution |
| `agent/curator.py` | ~400-450 | Report generation: `run.json` + `REPORT.md` |

What the teaching version simplifies:
- Production uses a configurable auxiliary model (default: gemini-3-flash via OpenRouter)
- Prefix clustering is done by the LLM review agent, not by code
- Three merge strategies: merge_to_existing, create_umbrella, demote_to_reference
- Reports are generated to `~/.hermes/logs/curator/{YYYYMMDD-HHMMSS}/`
- Cron job skill references are auto-rewritten after merges
- Rollback is supported: curator snapshots backup before each run

</details>

<details>
<summary>Deep Dive into Hermes Source</summary>

This section maps to the following source files in the production Hermes codebase:

- **`agent/curator.py:330-491`** — Curator Phase 2's complete implementation, including `CURATOR_REVIEW_PROMPT` and the execution logic for three merge strategies. In production, this code forks an independent `AIAgent` (using a configurable auxiliary model, default `google/gemini-3-flash-preview` to reduce review cost), injects the complete skill catalog (including SKILL.md bodies, DESCRIPTION.md, last_activity_at, etc.), and asks it to perform intelligent merge analysis.
- **Three merge strategies**: (a) **Merge into existing umbrella** — patch an existing skill via `skill_manage`, add new subsections, then archive siblings; (b) **Create new umbrella** — create a new class-level skill via `skill_manage create`, consolidate narrow skill content, then archive; (c) **Demote to support files** — move narrow skill bodies into an existing umbrella's `references/`, `templates/`, or `scripts/` subdirectories without creating a new skill.
- **Report system** — Each run generates under `~/.hermes/logs/curator/{YYYYMMDD-HHMMSS}/`: `run.json` (machine-readable full record), `REPORT.md` (human-readable review report), and `cron_rewrites.json` (if merging caused cron job skill reference changes).

**What the teaching version simplifies**:
- Production uses a configurable **auxiliary model** (auxiliary.curator config block) that can be a cheaper model to reduce review cost; the teaching version uses the main model
- Production's prefix clustering is based on skill name + `DESCRIPTION.md` semantic analysis (not just name prefixes), detecting functionally similar skills with different names
- Production merge operations involve real `skill_manage` tool calls (creating/modifying/archiving multiple files); the teaching version is file-level simulation
- Production hard rules: archive only (never delete), never touch bundled/hub skills, never touch pinned skills, auto-rewrite cron job skill references

</details>

<!-- translation-sync: zh@v1, en@v1 -->
