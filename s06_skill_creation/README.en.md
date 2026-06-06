# s06: Skill Creation — What to Learn, What Not to Learn

[中文](README.md) · [English](README.en.md)

s01 → ... → s05 → `s06` → [s07](../s07_curator_state/) → ... → s12
> *"What to learn, what not to learn — rules exist"* — Signal priorities, forbidden capture list, action priority strategy.
>
> **Self-Evolution Layer**: Skill Creation Safety — prevents learning wrong, too much, or harmful things.

---

## Problem

s03's background skill review lets the agent auto-create skills. Without constraints, the agent will:
- Save environment errors as skills ("npm install failed: missing node" → create "node-installation" skill?)
- Solidify one-off tasks ("Write me this script" → create "write-script" skill?)
- Capture temporary bugs ("Browser tools don't work right now" → create "browser-broken" skill?)

**Auto-learning needs safety guardrails. Not every signal deserves to be solidified.**

---

## Solution

Three layers of safety guardrails:

### 1. Signal Priority (What to Detect)

| Priority | Signal | Triggers When |
|----------|--------|--------------|
| 🥇 Highest | User Correction | User says "stop doing X" / "don't format like this" |
| 🥈 High | New Technique | Non-trivial trick, fix, workaround discovered |
| 🥉 Medium | Outdated Skill | Loaded skill proven wrong or outdated |
| Low | Repeated Pattern | Same task type 3+ times |

### 2. Forbidden Capture List (What NOT to Learn)

```python
FORBIDDEN_PATTERNS = [
    r"(missing|not found).*(binary|executable|command)",   # Env failures
    r"(browser|chrome).*(don't work|not working)",          # Tool negation
    r"(network|connection|timeout).*(error|failed)",         # Transient errors
    r"(api key|credential|auth).*(missing|invalid)",         # Config issues
]
```

### 3. Action Priority (How to Apply)

| Priority | Action | Condition |
|----------|--------|-----------|
| 1 | Update currently loaded skill | Skill was used in conversation |
| 2 | Update existing umbrella skill | Found matching class-level skill |
| 3 | Add reference file | Add under existing umbrella's `references/` |
| 4 | Create new skill | Only when nothing covers this task |

---

## Core Principles

### Learn, Don't Just Memorize

User preferences are embedded in skill bodies, not just memories. Memory answers "who the user is." Skills answer "how to do tasks for this user."

### Class-Level Umbrella Structure

Goal: a few rich class-level skills, not many narrow one-off entries. One umbrella skill with `references/` sub-files is better than five narrow sibling skills.

### Protection & Safety

- Bundled/Hub skills are never touched
- Archived skills are recoverable, never deleted
- Environment failures and tool negations are forbidden from capture

---

## Try It

```sh
python s06_skill_creation/code.py
```

Try: trigger different signals, observe forbidden capture interception with `/forbidden`, test action priorities.

---

## Next

Skill creation now has safety guardrails. But skills keep accumulating — we need an automated curation system: the Curator.

s07 Curator: Auto State Transitions → pure-rule stale/archive transitions, zero LLM cost.

<details>
<summary>Deep Dive into Hermes Source</summary>

The skill creation safety system references these source files:

| File | Lines | Role |
|------|-------|------|
| `agent/background_review.py` | 45-148 | Signal detection, priority-based action dispatch |
| `tools/skill_manage.py` | full | Skill creation with validation |

The four signal types and their priorities are encoded in the review prompt. The forbidden capture rules prevent persisting:
- Environment dependency failures
- Tool negation assertions (temporary issues)
- Session-specific transient errors
- One-off task narratives

What the teaching version simplifies:
- Production review agent has access to the full skill registry for deduplication
- The "update_loaded > update_existing > append_reference > create_new" priority chain is implemented via cascade logic
- Conditional skills (with `paths` frontmatter) are matched by glob against current workspace files
- Dynamic skills can be registered at runtime via MCP

</details>

<!-- translation-sync: zh@v1, en@v1 -->
