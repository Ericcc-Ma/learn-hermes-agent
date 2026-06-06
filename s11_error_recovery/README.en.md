# s11: Error Recovery — Errors Are Learning Starting Points

[中文](README.md) · [English](README.en.md)

s01 → ... → s10 → `s11` → [s12](../s12_comprehensive/)
> *"Errors aren't endpoints — they're learning starting points"* — Error detection + retry strategies + model fallback + self-healing.
>
> **Self-Evolution Layer**: Error Recovery — let the agent self-heal from failures and distill lessons into skills.

---

## Problem

Agents encounter various errors in production:
- API returns `overloaded_error` — model too busy
- Token limit exceeded — output truncated
- Tool execution failure — command not found, permission denied
- Context window full — needs compaction but shouldn't lose knowledge

A regular agent crashes on these. A self-evolving agent should **auto-recover and learn from the error**.

---

## Solution

### Three-Layer Recovery Strategy

| Layer | Strategy | Trigger |
|-------|----------|---------|
| 1. Retry | Exponential backoff + jitter | Transient errors (overloaded, timeout) |
| 2. Make Room | Auto-compact + reduce context | Token limit exceeded |
| 3. Switch Models | Fallback to cheaper/more reliable model | Current model persistently failing |

### Token Escalation Strategy

```python
def handle_token_limit(response, state):
    if not already_upgraded:
        state.max_output_tokens = 64000     # Upgrade to 64K
    elif not already_compacted:
        compact_context()                    # Make room
    else:
        switch_to_fallback_model()           # Last resort
```

### Provider-Aware Fallback Models

```python
_FALLBACK_MAP = {
    "claude-sonnet-4-6": "claude-haiku-4-5",
    "claude-opus-4-8": "claude-sonnet-4-6",
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-chat",
    "gpt-4o": "gpt-4o-mini",
}
```

### Error → Skill Learning

When recovery succeeds with a novel workaround, it's recorded. Repeated recoveries of the same type can trigger skill creation — turning error patterns into reusable knowledge.

---

## Try It

```sh
python s11_error_recovery/code.py
```

The agent automatically handles overload, token limit, and timeout errors. Recovery patterns are logged for learning.

---

## Next

All self-evolution components are in place. The final step: integrate all mechanisms into one complete self-evolving agent.

s12 Complete Self-Evolving Agent → all six layers integrated.

<details>
<summary>Deep Dive into Hermes Source</summary>

Error recovery patterns are distributed across:

| File | Lines | Role |
|------|-------|------|
| `agent/conversation_loop.py` | full | Multiple exit/recovery paths in the main loop |
| `agent/conversation_loop.py` | ~700-900 | max_tokens override, reactive compact, fallback logic |

What the teaching version simplifies:
- Production has 10+ distinct exit and continuation paths (vs. teaching version's 3)
- Token escalation: 8K → 64K → compact → fallback model
- `hasAttemptedReactiveCompact` prevents infinite compact loops
- `maxOutputTokensRecoveryCount` caps recovery attempts at 3
- The `transition` field records the last continuation reason for debugging
- Abort and stop hooks add additional exit paths

</details>

<!-- translation-sync: zh@v1, en@v1 -->
