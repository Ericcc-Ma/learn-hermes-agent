# s07: Curator — Auto State Transitions

[中文](README.md) · [English](README.en.md)

s01 → ... → s06 → `s07` → [s08](../s08_curator_llm/) → ... → s12
> *"30 days unused → mark stale, 90 days → archive, rules decide"* — Pure-rule auto state transitions, zero LLM cost.
>
> **Self-Evolution Layer**: Long-term Maintenance (Curator) — Phase 1: rule-driven skill library maintenance.

---

## Problem

s03 lets the agent auto-create skills. s05 defines lifecycle states. But state transitions require manual triggers — users must remember to run `/curator`. After a month, `.skills/` bloats to 50+ skills, most of them zombies.

**Automated periodic maintenance is needed. But skill transition rules are deterministic (30 days unused → stale, 90 days → archived) — no LLM required.**

---

## Solution

**Curator two-phase execution. Phase 1: Pure-rule auto transitions (zero LLM cost).**

### Trigger Mechanism

Not a cron daemon — an **idle-triggered** mechanism:

```python
class CuratorScheduler:
    interval_hours = 168      # 7 days
    min_idle_hours = 2        # Agent idle ≥ 2 hours

    def should_run(self) -> bool:
        hours_since_last = (now() - self.last_run_at).total_seconds() / 3600
        return hours_since_last >= self.interval_hours
```

### Auto State Transitions (Pure Rules)

```python
def apply_automatic_transitions(skills, config):
    for name, skill in skills.items():
        if skill.pinned: continue                    # Never touch pinned
        if skill.source in ("bundled", "hub"): continue  # Default: skip

        days = (now() - skill.last_activity_at).days

        if skill.state == "active" and days >= 30:
            skill.state = "stale"                    # Active → Stale
        elif skill.state == "stale" and days >= 90:
            skill.state = "archived"                 # Stale → Archived
        elif skill.state == "stale" and days < 30:
            skill.state = "active"                   # Reactivate
```

### CLI Control

```bash
hermes curator status           # View status
hermes curator run              # Trigger immediately
hermes curator run --dry-run    # Preview mode
hermes curator pause            # Pause
hermes curator resume           # Resume
hermes curator pin <skill>      # Pin skill
hermes curator restore <skill>  # Restore archived skill
```

---

## Try It

```sh
python s07_curator_state/code.py
```

Try: create test skills, simulate time, observe transitions, pin skills for exemption.

---

## Next

Curator Phase 1 is pure rules — zero LLM cost. But as skills accumulate, even active ones can overlap and fragment. LLM-powered intelligent merging is needed.

s08 Curator: LLM Review → prefix clustering + umbrella merging + demotion + report generation.

<details>
<summary>Deep Dive into Hermes Source</summary>

Curator Phase 1 (pure-rule transitions) is in:

| File | Lines | Role |
|------|-------|------|
| `agent/curator.py` | 268-323 | `apply_automatic_transitions()` — the rule engine |
| `agent/curator.py` | ~100-150 | Idle trigger, scheduling, last_run_at tracking |

What the teaching version simplifies:
- Production Curator is NOT a cron daemon — it uses idle-triggered scheduling
- First install seeds `last_run_at` and waits a full cycle before running
- Config lives in `~/.hermes/config.yaml` with defaults: interval=168h, idle=2h
- The production state machine handles 200+ skills without performance issues
- Phase 1 runs synchronously (zero LLM cost); Phase 2 spawns a forked agent

</details>

<!-- translation-sync: zh@v1, en@v1 -->
