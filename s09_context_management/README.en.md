# s09: Context Management — Compress When Full

[中文](README.md) · [English](README.en.md)

s01 → ... → s08 → `s09` → [s10](../s10_insights/) → ... → s12
> *"Context fills up — compress it, but keep the important stuff out"* — Conversation compression + trajectory compression + memory prefetch protection.
>
> **Self-Evolution Layer**: Context Management — protecting self-evolved knowledge from being swallowed by compression.

---

## Problem

An agent working for 30 minutes accumulates a messages list stuffed with intermediate processes. Old tool results, stale file contents — consuming context without producing value. When context nears token limits, compression is necessary.

But compression has risks: memories from s02's background review, auto-created skills from s03 — these self-evolution artifacts, if swallowed by compression, leave the agent dumb again next session.

**Intelligent compression is needed: compress intermediate processes, protect self-evolution artifacts.**

---

## Solution

**Four-layer compaction strategy** + **memory prefetch protection**.

### Conversation Compression

```python
def auto_compact(messages, token_limit):
    # Protect head (system prompt + early context) and tail (recent)
    head = messages[:3]
    tail = messages[-8:]
    # Compress the middle
    middle = messages[3:-8]
    summary = summarize_with_aux_model(middle)
    return head + [summary_message(summary)] + tail
```

### Structured Summary Template

```
Completed:
- ✅ Fixed auth module token expiration bug
- ✅ Updated API documentation

Remaining Work:  (NOT "Next Steps" — prevents reading as active instruction)
- ⬜ Performance: add database query indexes
- ⬜ Deploy script needs new environment adaptation

Key Decisions:
- Use Redis instead of Memcached for session storage

User Constraints:
- All API endpoints must have rate limiting
```

### Memory Prefetch Protection

Before compression, notify the memory provider to extract insights (`on_pre_compress()` hook), ensuring critical knowledge isn't lost during compression.

### Context Injection Format

Memory and skill content is injected via fenced blocks, clearly distinguished as system reference data (not new user input):

```xml
<memory-context>
[System note: recalled memory context, NOT new user input.]
...memory content...
</memory-context>
```

---

## Try It

```sh
python s09_context_management/code.py
```

Make multiple file operations to accumulate messages, observe compression triggers. Check if memories persist after compression.

---

## Next

The agent now has complete self-evolution capability — learning, memory, skills, curation, compression. But how to measure effectiveness? Token usage? Cost?

s10 Insights Engine → token/cost/tool pattern analysis.

<details>
<summary>Deep Dive into Hermes Source</summary>

Context management spans multiple source files:

| File | Lines | Role |
|------|-------|------|
| `agent/conversation_compression.py` | full | Auto-compact trigger, orchestration |
| `agent/context_compressor.py` | full | Summary generation with structured templates |
| `trajectory_compressor.py` | full | Post-hoc trajectory compression for training data |

What the teaching version simplifies:
- Production has 4 compression layers: toolResultBudget → microCompact → snipCompact → autoCompact
- The structured summary uses "Remaining Work" (not "Next Steps") to prevent being read as active instruction
- Pre-compress hook notifies memory providers to extract insights before compression
- Trajectory compression preserves training signal quality by protecting first/last turns
- Production can compress JSONL trajectories to target token budgets

</details>

<details>
<summary>Deep Dive into Hermes Source</summary>

This section maps to the following source files in the production Hermes codebase:

- **`agent/conversation_compression.py`** — Conversation compression trigger and orchestration. In production, this monitors token usage and auto-triggers compression when the conversation exceeds thresholds, using an auxiliary model (cheap/fast) to summarize middle turns. It protects the head (system prompt + early context) and tail (recent interactions), only compressing middle tool calls and responses.
- **`agent/context_compressor.py`** — Core compression implementation. Production's compressor uses structured summary templates (distinguishing "Completed" from "Remaining Work"), with the key design decision of using **"Remaining Work"** instead of "Next Steps" (to prevent being read as active instructions). Before compression, it calls the memory provider's `on_pre_compress()` hook to extract insights.
- **`trajectory_compressor.py`** — Post-hoc trajectory compression tool. Compresses completed agent trajectories (JSONL format), protecting first and last turns, compressing middle tool responses, and preserving training signal quality. Supports `--target_max_tokens` (target token budget) and `--sample_percent` (sampling percentage) parameters. Used for generating training data or archiving long sessions.

**What the teaching version simplifies**:
- Production uses precise token counting (model-specific tokenizers) to determine compression timing; the teaching version uses simple message count estimation
- Production compression uses an auxiliary model asynchronously, non-blocking to the main conversation; the teaching version is synchronous blocking
- Production's `trajectory_compressor.py` is a standalone CLI tool (batch operations on JSONL files); the teaching version doesn't include this component
- Production compression summaries include more structured fields (key decisions, user constraints, loaded skills); the teaching version only distinguishes completed/remaining

</details>

<!-- translation-sync: zh@v1, en@v1 -->
