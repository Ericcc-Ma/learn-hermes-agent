# s12: Complete Self-Evolving Agent — Six Layers in Place

[中文](README.md) · [English](README.en.md)

s01 → s02 → ... → s11 → `s12`
> *"Six layers in place, one self-evolving agent"* — All self-evolution mechanisms integrated into one complete agent.
>
> **Self-Evolution Layer**: All six layers — Background Review + Skill Management + Curator + Memory + Context + Insights.

---

## Overview

s01 through s11 built Hermes' six-layer self-evolution architecture layer by layer. This chapter integrates them all into one complete, runnable agent.

---

## Complete Architecture

```
                    ┌─────────────────────────────────┐
                    │         User Interaction          │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │      Agent Loop (s01)            │
                    │      while True:                 │
                    │        response = LLM(...)       │
                    │        if stop: break            │
                    │        execute tools             │
                    └──────────────┬──────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
  ┌──────────┐            ┌──────────────┐          ┌──────────────┐
  │ Pre-turn  │            │   Mid-turn    │          │  Post-turn    │
  └──────────┘            └──────────────┘          └──────────────┘
  │                       │                         │
  │ Memory prefetch (s04) │ Error recovery (s11)     │ BG review (s02,s03)
  │ Skill catalog (s05)   │ Context compact (s09)    │ Memory extract (s04)
  │                       │                         │ Skill detection (s06)
  │                       │                         │
  ┌───────────────────────┼─────────────────────────┐
  │              Long-term Maintenance (s07, s08)    │
  │  ┌─────────────┐    ┌─────────────────┐         │
  │  │ Curator P1  │    │  Curator P2     │         │
  │  │ Auto trans.  │    │  LLM merge      │         │
  │  └─────────────┘    └─────────────────┘         │
  └─────────────────────────────────────────────────┘
  │
  │ Insights Engine (s10) — quantify all activity
  │
  ▼
  [Reports] Token stats | Cost analysis | Tool patterns | Evolution metrics
```

---

## Six Layer Mapping

| Layer | Chapters | Mechanism | Trigger |
|-------|----------|-----------|---------|
| 1. Real-time Learning | s02, s03 | Background Review (memory + skill) | Nudge (every N turns) |
| 2. Skill Management | s05, s06 | Lifecycle + safety guardrails | Event-driven |
| 3. Long-term Maintenance | s07, s08 | Curator (rules + LLM) | Idle trigger (every 7 days) |
| 4. Memory System | s04 | FTS5 + pluggable providers | Every turn injection |
| 5. Context Management | s09 | Compression + memory prefetch | Token threshold trigger |
| 6. Data Analytics | s10 | Insights engine | On-demand query |

---

## Complete Agent Loop

```python
def self_evolving_agent_loop(query, client, state):
    messages.append({"role": "user", "content": query})

    while True:
        # ═══ Pre-turn ═══
        relevant = memory_manager.prefetch(query)           # s04
        skills_catalog = skill_registry.list_active()       # s05
        system = assemble_system(relevant, skills_catalog)

        # ═══ Mid-turn ═══
        if should_compact(messages):                        # s09
            memory_manager.on_pre_compress()
            messages = compact(messages)

        response = safe_api_call(client, state, ...)        # s11

        if response.stop_reason != "tool_use":
            # ═══ Post-turn ═══
            if should_nudge_memory(state):                  # s02
                background_memory_review(messages)
            if should_nudge_skill(state):                   # s03
                background_skill_review(messages)
            return response

        execute_tools(response.content)

    # ═══ Idle ═══
    if curator.should_run():                                # s07, s08
        curator.auto_transitions()
        curator.llm_review()
```

---

## Key Design Principles (Recap)

### 1. Learn, Don't Just Memorize
User preferences are embedded in skill bodies, not just memories.

### 2. Class-Level Umbrella Structure
Goal: a few rich class-level skills, not many narrow one-off entries.

### 3. Protection & Safety
Bundled/Hub skills never touched. Archived skills recoverable. Environment failures forbidden from capture.

### 4. Background Non-Invasive
All learning/maintenance runs in the background, preserving the prompt cache.

### 5. Observable
Curator generates full reports. Insights provides quantitative analysis.

### 6. User Control
Curator can pause/resume/disable. Skills can be pinned. Dry-run preview supported.

---

## All Chapters Recap

| Chapter | Topic | Motto |
|---------|-------|-------|
| s01 | Agent Loop + Memory | One loop + one memory file |
| s02 | Background Memory Review | Ask "what did I learn?" after every conversation |
| s03 | Background Skill Review | Distill good solutions into skills |
| s04 | Memory System | Memory shouldn't be just one file |
| s05 | Skill Lifecycle | Skills have a lifecycle |
| s06 | Skill Creation | Rules for what to learn and what not |
| s07 | Curator State | 30 days unused → mark stale |
| s08 | Curator LLM | Merge periodically when too many skills |
| s09 | Context Management | Compress when full, protect what matters |
| s10 | Insights | You can't optimize what you don't measure |
| s11 | Error Recovery | Errors are learning starting points |
| s12 | Complete Agent | Six layers, one self-evolving agent |

---

## Try It

```sh
python s12_comprehensive/code.py
```

Try these prompts to experience the full self-evolution flow:

1. "I prefer tabs over spaces, and I always use pytest with --cov."
2. "Every PR needs: lint → typecheck → test → review."
3. "Stop using camelCase in Python files."
4. After multiple interactions, run `/insights` for stats.
5. Run `/curator` to trigger skill library curation.

Watch: are memories auto-saved? Are skills auto-created from corrections? Does Curator manage states correctly? Does Insights track accurately?

---

**Agency comes from the model. Self-evolution comes from the harness. Every conversation is a learning opportunity. Knowledge learned is automatically distilled into reusable skills and memories.**

**Build the harness that learns. The model will do the rest.**

<details>
<summary>Deep Dive into Hermes Source</summary>

The complete self-evolving agent integrates all six layers. Source file index:

| Layer | Key Files |
|-------|-----------|
| 1. Real-time Learning | `agent/background_review.py`, `agent/conversation_loop.py` |
| 2. Skill Management | `tools/skill_usage.py`, `tools/skill_manage.py`, `agent/skill_utils.py` |
| 3. Long-term Maintenance | `agent/curator.py` (full: scheduling + Phase 1 + Phase 2) |
| 4. Memory System | `agent/memory_manager.py`, `agent/memory_provider.py`, `plugins/memory/` |
| 5. Context Management | `agent/conversation_compression.py`, `agent/context_compressor.py`, `trajectory_compressor.py` |
| 6. Data Analytics | `agent/insights.py` |

Additional core files: `run_agent.py` (AIAgent main class), `agent/agent_init.py` (initialization), `agent/skill_commands.py` (CLI).

The teaching implementation captures the essence of each layer while simplifying:
- Background execution model (synchronous vs. async forked agents)
- Full event/hook bus behavior (teaching code uses minimal lifecycle events)
- Production permission governance and multi-session state management

</details>

<!-- translation-sync: zh@v1, en@v1 -->
