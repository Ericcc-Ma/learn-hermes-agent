# s05: Skill Lifecycle — The Life and Death of Skills

[中文](README.md) · [English](README.en.md)

s01 → ... → s04 → `s05` → [s06](../s06_skill_creation/) → ... → s12
> *"Skills have a lifecycle"* — active → stale → archived state machine, pin exemption, umbrella directory structure.
>
> **Self-Evolution Layer**: Skill Management — lifecycle and organization of skills.

---

## Problem

s03 lets the agent auto-create skills. But skills only increase, never decrease. After a month, `.skills/` has 50 skills, most from early in the project, long unused. Every startup scans 50 skills, wasting 100+ tokens on an unused catalog.

Skills need a **lifecycle** — active after creation, degraded when unused for long periods, eventually archived. But never deleted — just moved out of sight.

---

## Solution

**Three-level state machine** + **umbrella directory structure** + **pin exemption**.

### State Machine

```
active ──(30d unused)──► stale ──(90d unused)──► archived
  ▲                         │                        │
  │                         │                        │
  └───(used again)──────────┘                        │
                                                     │
                                          .skills/.archive/
                                          (recoverable, never deleted)
```

| State | Meaning | In system prompt | load_skill works |
|-------|---------|-----------------|------------------|
| **active** | In active use | ✅ Yes | ✅ Yes |
| **stale** | Long unused | ✅ Yes (marked) | ✅ Yes |
| **archived** | Archived | ❌ No | ❌ Must restore first |
| **pinned** | Exempt from all transitions | ✅ Yes | ✅ Yes |

### Umbrella Directory Structure

```
.skills/<skill-name>/
├── SKILL.md          # Class-level instructions (required)
├── DESCRIPTION.md    # Short description for skill matching
├── references/       # Session-specific details, domain knowledge
├── templates/        # Copy-modify template files
├── scripts/          # Statically re-runnable scripts
└── assets/           # Static assets
```

The goal: a small number of rich **class-level skills** (umbrellas), not many narrow one-off entries.

---

## Try It

```sh
python s05_skill_lifecycle/code.py
```

Try: create skills, load them, simulate time passing, observe stale/archive transitions, pin skills to exempt them.

---

## Next

The state machine handles the lifecycle. But skill creation rules are still too crude — what should and shouldn't be learned needs explicit safety guardrails.

s06 Skill Creation → signal priorities + forbidden capture list + action priority strategy.

<details>
<summary>Deep Dive into Hermes Source</summary>

The skill lifecycle system is managed by these source files:

| File | Lines | Role |
|------|-------|------|
| `tools/skill_usage.py` | full | Skill usage telemetry, lifecycle state management |
| `agent/curator.py` | 268-323 | `apply_automatic_transitions()` — pure-rule state machine |
| `agent/skill_utils.py` | full | Skill directory structure, parsing |

What the teaching version simplifies:
- Production has 3 skill sources: bundled (shipped with Hermes), hub-installed (from agentskills.io), and agent-created
- Bundled and hub skills are never auto-transitioned (only agent-created ones)
- The umbrella directory structure includes `references/`, `templates/`, `scripts/`, and `assets/` subdirectories
- Pinned skills are tracked via explicit pin/unpin commands, not just a boolean flag

</details>

<!-- translation-sync: zh@v1, en@v1 -->
