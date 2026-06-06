# s02: Background Review — Auto Memory Review

[中文](README.md) · [English](README.en.md)

s01 → `s02` → [s03](../s03_background_skill_review/) → s04 → ... → s12
> *"After every conversation, ask 'what did I learn?'"* — Fork an independent agent in the background, auto-review each turn, extract memories.
>
> **Self-Evolution Layer**: Real-time Learning (Background Review) — the front line of the self-evolution system.

---

## Problem

s01's memory extraction runs only after the conversation fully ends. But a true self-evolving agent needs to be more proactive:

- Mid-conversation, the user says "don't use snake_case, use camelCase" — this should be remembered immediately
- The user corrects the agent's mistake — this lesson shouldn't wait until the end
- Long conversations degrade extraction quality when done all at once

**Passive memory extraction isn't enough. Active, periodic review is needed.**

---

## Solution

**The Nudge System**: After every N turns, fork an independent AIAgent in the background, replay a conversation snapshot, and ask "is there anything worth remembering?"

Key design decisions:
- **Background execution**: Doesn't block the main conversation, doesn't affect the prompt cache
- **Independent agent**: Forked with its own message list, doesn't pollute the main conversation
- **Read-only snapshot**: Reviews a copy of the conversation, not a reference

---

## How It Works

### Nudge Configuration

```python
class Config:
    MEMORY_NUDGE_INTERVAL = 5  # Review every 5 turns
```

### Review Scope — Four Dimensions

| Dimension | What to Look For | Example |
|-----------|-----------------|---------|
| User Preferences | Coding style, workflow, tool preferences | "Uses tabs, not spaces" |
| User Feedback | Corrections to agent behavior | "Stop formatting my code" |
| Project Facts | Architecture decisions, constraints | "Auth module is being rewritten" |
| References | URLs, dashboards, ticket numbers | "Pipeline bug is LINEAR-1234" |

### Review Agent

```python
def background_memory_review(messages_snapshot):
    dialogue = format_snapshot(messages_snapshot[-12:])
    review_prompt = f"""Review for: preferences, feedback, facts, references.
Conversation: {dialogue}
Return JSON array of memories or []."""
    # Fork independent agent, parse and save
```

---

## Nudge System Design Principles

### 1. Frequency Trade-off

Too frequent → wastes LLM calls, disrupts user experience
Too sparse → misses important information

Hermes defaults to 10 turns. The teaching version uses 5 for easier observation.

### 2. Snapshot, Not Reference

The review agent receives a copy (snapshot) of the conversation. This ensures the forked agent's modifications don't affect the main conversation, and the snapshot can be trimmed (last N turns only).

### 3. Write-Only Responsibility

The review agent is only responsible for writing new memories. Reading memories still happens in the main agent loop's `build_system()`. Clean separation of concerns.

---

## Try It

```sh
python s02_background_memory_review/code.py
```

Try multiple prompts and observe the nudge triggering every 5 turns. Watch for `[BackgroundReview]` output.

---

## Next

Now the agent can auto-extract memories. But memories are only "who the user is." True self-evolution also needs skills — "how to do this type of task." And the best skill creation signals come from user corrections.

s03 Background Review: Skill Review → auto-detect skill creation signals from conversation, distill good solutions into reusable skills.

<details>
<summary>Deep Dive into Hermes Source</summary>

This section maps to the following source files in the production Hermes codebase:

- **`agent/background_review.py:34-43`** — The core memory review implementation. In production, this code forks an independent `AIAgent` instance (with its own message list, avoiding pollution of the main conversation), injects a review prompt asking "Did the conversation reveal user preferences, personal information, or work style? Did the user express expectations about agent behavior?", and auto-saves results to `MEMORY.md` / `USER.md` via the `memory` tool.
- **`agent/conversation_loop.py`** — Nudge trigger logic. Production maintains two separate nudge counters: `memory.nudge_interval` (default: every 10 user turns) and `skills.creation_nudge_interval` (default: every 10 tool iterations). The post-turn hook in the main conversation loop checks these counters and decides whether to spawn a review agent.

**What the teaching version simplifies**:
- Production performs truly **asynchronous background** execution — forking an independent agent thread that does not block the main conversation or affect the prompt cache; the teaching version is synchronous/blocking
- Production reviews a **snapshot copy** of the conversation (`list(messages)`), so the forked agent's modifications never affect the main conversation state; the teaching version passes a direct reference
- Production can **trim the snapshot** to only the most recent N turns to reduce token costs; the teaching version takes the last 12 turns
- Production review results invoke the real `memory` tool (supporting create/update/delete/query); the teaching version uses simple file appending

</details>

<details>
<summary>Deep Dive into Hermes Source</summary>

The background review nudge system is implemented in these source files:

| File | Lines | Role |
|------|-------|------|
| `agent/background_review.py` | 34-43 | Memory review logic, snapshot replay, extraction prompt |
| `agent/conversation_loop.py` | 4714-4722 | Nudge trigger at conversation end |

What the teaching version simplifies:
- Production spawns a forked `AIAgent` with restricted permissions (`skipTranscript: true`, `maxTurns: 5`)
- Overlap protection: if the main agent already wrote memory files, skip extraction
- The production nudge is a fire-and-forget background task, not synchronous
- Snapshot includes structured metadata, not just raw messages

</details>

<!-- translation-sync: zh@v1, en@v1 -->
