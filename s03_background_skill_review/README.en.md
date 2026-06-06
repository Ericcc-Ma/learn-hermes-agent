# s03: Background Review — Auto Skill Review

[中文](README.md) · [English](README.en.md)

s01 → s02 → `s03` → [s04](../s04_memory_system/) → ... → s12
> *"Good solutions aren't one-offs — distill them into skills"* — Detect corrections, discoveries, and outdated signals in conversations; auto-create or update skills.
>
> **Self-Evolution Layer**: Real-time Learning (Background Review) — automatic skill generation.

---

## Problem

s02 lets the agent auto-extract memories — knowing the user uses tabs, prefers functional components, has an auth rewrite in progress. But memories are **declarative knowledge** ("who the user is"), not **procedural knowledge** ("how to do this type of task").

The user corrects the agent: "Always run the test suite before deploying." That's a workflow. It should become a skill. Next time the agent deploys, this skill loads automatically — no need for the user to repeat it.

**Memory answers "who the user is." Skills answer "how to do tasks for this user."**

---

## Solution

Extend Background Review with a **skill review** dimension. Four signals trigger skill creation/update:

| Signal | Priority | Description | Example |
|--------|----------|-------------|---------|
| **User Correction** | 🥇 Highest | User corrects agent style/format/workflow | "Stop doing X", "Always Y before Z" |
| **New Technique** | 🥈 High | Non-trivial trick, fix, workaround discovered | Found an API quirk and workaround |
| **Outdated Skill** | 🥉 Medium | Loaded skill proven wrong or missing steps | "That doc is outdated" |
| **Repeated Pattern** | Low | Same task type appeared 3+ times | Same review steps every time |

---

## How It Works

### Signal Detection

The review agent analyzes conversation snapshots for these four signals, in priority order. User corrections get the highest priority — they represent direct user intent and must be embedded in skills.

### Action Priority (What to Do)

Not every signal creates a new skill:

| Priority | Action | Condition |
|----------|--------|-----------|
| 1 | **Update currently loaded skill** | Skill was used in this conversation |
| 2 | **Update existing umbrella skill** | Found matching class-level skill |
| 3 | **Add reference file** | Add `references/` under existing umbrella |
| 4 | **Create new skill** | No existing skill covers this task |

### Forbidden Capture List

Not every correction should become a skill. These are **forbidden**:

| Forbidden | Reason |
|-----------|--------|
| Environment dependency failures | Missing binaries, unconfigured credentials |
| Tool negation assertions | "Browser tools don't work" — likely temporary |
| Session-specific transient errors | Retry-resolved one-off errors |
| One-off task narratives | "Write me a script" — not reusable |

---

## Try It

```sh
python s03_background_skill_review/code.py
```

Try deliberately triggering different signals:
1. "Let me show you how I deploy: first run tests, then build, then push."
2. "Stop using camelCase — I always use snake_case in Python."
3. Repeatedly do similar tasks to observe repeated pattern detection.

Watch: did `.skills/` auto-create new skills? Does the forbidden capture list work?

---

## Next

Now the agent can auto-create both memories and skills. But the memory system is still a single `MEMORY.md` file. Production needs full-text search, multiple memory types, and pluggable external providers.

s04 Memory System → FTS5 full-text search + pluggable provider architecture + lifecycle hooks.

<details>
<summary>Deep Dive into Hermes Source</summary>

This section maps to the following source files in the production Hermes codebase:

- **`agent/background_review.py:45-148`** — The complete skill review implementation. In production, this code defines four review signal types and action priorities:
  - **User Correction** (top priority): Detects "stop doing X", "don't format like this" and similar expressions of dissatisfaction — **must be embedded into a skill**
  - **New Technique/Pattern**: Detects non-trivial tricks, fixes, workarounds, and debugging paths
  - **Outdated Skill**: A currently loaded or consulted skill is proven wrong, missing steps, or out of date
  - **Repeated Pattern**: Same type of task appears 3+ times
  
  Action priority (first matching wins): (1) update currently loaded skill → (2) update existing umbrella skill → (3) add `references/`/`templates/`/`scripts/` support files → (4) create new umbrella skill

- **`agent/background_review.py` (forbidden capture logic)** — Production defines strict forbidden capture patterns: environment dependency failures (missing binaries/unconfigured credentials), tool negation assertions ("browser tools don't work"), session-specific transient errors (resolved on retry), and one-off task narratives. These rules prevent the agent from solidifying transient failures into permanent self-constraints.

**What the teaching version simplifies**:
- Production's action priority involves scanning the existing skill directory (via `skills_list` + `skill_view` to find matching umbrella skills); the teaching version uses simple name prefix matching
- Production skill updates trigger real `skill_manage` tool calls (full SKILL.md rewrite/patch); the teaching version is file-level replacement
- Production's forbidden capture uses more sophisticated regex + context judgment; the teaching version uses basic regex lists
- The production signal detection prompt is more detailed (~50 lines) and includes references to currently loaded skill context

</details>

<details>
<summary>Deep Dive into Hermes Source</summary>

The skill review system lives in these production source files:

| File | Lines | Role |
|------|-------|------|
| `agent/background_review.py` | 45-148 | Skill review signals, priority rules, action dispatch |
| `tools/skill_manage.py` | full | Skill CRUD tool implementation |
| `agent/skill_utils.py` | full | Skill utility functions |

What the teaching version simplifies:
- Production has 4 operation priorities (update_loaded > update_existing > append_reference > create_new)
- The forbidden capture list in production is maintained in code with pattern matching
- Production supports "conditional skills" activated by glob patterns on file paths
- The review agent uses the same AIAgent fork pattern as memory review

</details>

<!-- translation-sync: zh@v1, en@v1 -->
