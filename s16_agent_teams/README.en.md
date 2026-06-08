# s16: Agent Teams — delegate_task + Role System

[中文](README.md) · [English](README.en.md)

![Agent Teams](images/agent-teams.svg)

s01 → ... → s15 → `s16` → [s17](../s17_mcp_plugin/) → ... → s24
> *"Too big? Delegate it"* — the LLM calls the `delegate_task` tool on its own to spawn sub-agents, with leaf/orchestrator roles.
>
> **Hermes Feature**: Agent Teams — LLM-driven, immediate task delegation.

---

## Problem

A single agent's context grows quickly on complex work. The harness needs a way to delegate subtasks so each sub-agent can work with an isolated context.

---

## Solution

**The `delegate_task` tool** — the LLM calls it like any other tool and decides when and how to spawn sub-agents.

### Two Modes

| Mode | Parameters | Behavior |
|------|------------|----------|
| **Single** | `goal` + `context` + `role` | Starts one sub-agent |
| **Batch** | `tasks: [{goal, context, role}, ...]` | Starts N sub-agents concurrently, capped by `max_concurrent_children` |

### Role System

```text
        Parent (depth=0)
              │ delegate_task()
     ┌────────┼────────┐
     ▼        ▼        ▼
  leaf    leaf    orchestrator (depth=1)
 (default)             │ delegate_task()
                       ▼
                     leaf (depth=2, max)
```

- **leaf** (default): a pure worker. Tools such as `delegate_task`, `clarify`, and `memory` are stripped.
- **orchestrator**: keeps `delegate_task` and can spawn more children, bounded by `max_spawn_depth` (default: 1).

### Key Configuration

| Config | Default | Meaning |
|--------|---------|---------|
| `max_concurrent_children` | 3 | Maximum number of parallel children per delegation |
| `max_spawn_depth` | 1 | Maximum nesting depth |
| `max_iterations` | 90 | Maximum tool-calling iterations for a child agent |

### Synchronous Model

`delegate_task` is **synchronous**: the parent agent waits until all child agents finish, receives their summaries, and then continues. It is not persistent and does not survive across turns.

---

## Try It

```sh
python s16_agent_teams/agent_teams.py
```

---

<details>
<summary>Hermes Source Deep Dive</summary>

The production `delegate_task` system lives in these source files:

| File | Responsibility |
|------|----------------|
| `tools/delegate_tool.py` | `delegate_task` tool definition and parameter validation |
| `run_agent.py` (~4793) | `_dispatch_delegate_task()` — dispatches sub-agents |
| `agent/conversation_loop.py` | Detects tool calls in assistant messages |
| `agent/agent_init.py` (~929) | Worker initialization and kanban guidance injection |

What the teaching version simplifies:

- Production `delegate_task` forks real child processes; the teaching version simulates that with function calls.
- Production role handling dynamically strips selected toolsets from workers.
- Production `max_spawn_depth` is a hard guard against unbounded nesting.
- Production child summaries are injected back into the parent agent's conversation context.

</details>

<!-- translation-sync: en@v1 -->
