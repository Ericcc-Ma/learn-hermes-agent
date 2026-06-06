# s01: Agent Loop + Memory — Remembering Who the User Is

[中文](README.md) · [English](README.en.md)

`s01` → [s02](../s02_background_memory_review/) → s03 → s04 → ... → s12
> *"One loop + one memory file = the simplest learning agent"* — Add MEMORY.md on top of the agent loop to remember user preferences across sessions.
>
> **Self-Evolution Layer**: Memory Persistence — the foundation. Without memory, there is no learning.

---

## Problem

You tell an agent "I use tabs, not spaces." This session it complies. Next session, you have to say it again.

The agent remembers nothing. LLMs have no persistent state — all information lives in the context window and vanishes when the session ends. You have to manually repeat everything, over and over.

This isn't the model being unintelligent. It's the harness not giving it the ability to remember.

---

## Solution

Add the simplest possible persistent memory on top of the agent loop: a `MEMORY.md` file in a `.memory/` directory.

```
User: "I use tabs, not spaces"
   ↓
Agent Loop: normal conversation
   ↓
Conversation ends → extract memories → write to MEMORY.md
   ↓
Next conversation → read MEMORY.md → inject into SYSTEM prompt → Agent knows your preference
```

Just three mechanisms:
1. **Store**: `MEMORY.md` file with YAML frontmatter + markdown body
2. **Load**: Read `MEMORY.md` before every turn, inject into system prompt
3. **Write**: After every turn, check for information worth saving

---

## How It Works

### 1. Storage: MEMORY.md

```python
MEMORY_DIR = Path(".memory")
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"

def write_memory(name, mem_type, description, body):
    MEMORY_DIR.mkdir(exist_ok=True)
    entry = f"---\nname: {name}\ntype: {mem_type}\ndescription: {description}\n---\n\n{body}\n"
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write("\n---\n" + entry)
```

### 2. Loading: Inject into system prompt

```python
def load_memories() -> str:
    if not MEMORY_FILE.exists():
        return ""
    content = MEMORY_FILE.read_text(encoding="utf-8")
    return f"""<memory-context>
[System note: The following is recalled memory context, NOT new user input.
Treat as authoritative reference data.]

{content}
</memory-context>"""
```

### 3. Writing: Extract after conversation

```python
def extract_and_save_memory(messages, client):
    recent = format_recent_messages(messages[-6:])
    prompt = f"""Is there anything worth remembering from this conversation?
- User preferences / feedback / project facts / references
Return JSON array or []."""
    response = client.messages.create(...)
    # Parse and save memories
```

### 4. Assembly: Complete agent loop

Under 50 lines of changes, and the agent now has cross-session memory. The remaining 11 chapters layer on top of this foundation.

---

## Four Memory Types

| Type | Answers | Example |
|------|---------|---------|
| `user` | Who the user is | "Uses tabs, not spaces" |
| `feedback` | How to behave | "Don't mock the database" |
| `project` | What's happening | "Auth rewrite is compliance-driven" |
| `reference` | Where things are | "Pipeline bug is in LINEAR-1234" |

---

## Try It

```sh
python s01_agent_loop/code.py
```

Try these prompts:
1. `I prefer using tabs for indentation, not spaces. Remember that.`
2. `Create a Python file called hello.py`
3. Exit, re-run, ask `What did I tell you about my coding preferences?`

---

## Next

Now the agent can remember — but only when the user explicitly says "remember" or when the conversation fully ends. A true self-evolving agent should **automatically** review every conversation turn for learnings. And not just memories — also skill-worthy patterns.

s02 Background Review: Memory Review → fork an independent agent in the background, auto-review every turn, extract memories.

<details>
<summary>Deep Dive into Hermes Source</summary>

This section maps to the following source files in the production Hermes codebase:

- **`agent/conversation_loop.py`** (~line 4714-4722) — The central hub of the main conversation loop. In production, nudge counters here determine whether to trigger background reviews after each turn, checking `_should_review_memory` and `_should_review_skills` flags and calling `_spawn_background_review()` to fork an independent review agent. The teaching version simplifies this to a synchronous `extract_and_save_memory()` call.
- **`run_agent.py`** — The `AIAgent` main class, Hermes' "brain," integrating the memory manager, skill registry, Curator scheduler, context compressor, and all other subsystems. The teaching version's `code.py` (~160 lines) is an extreme simplification of the production codebase which spans thousands of lines.

**What the teaching version simplifies**:
- Production nudge intervals are configurable (default: memory review every 10 turns, skill review every 10 tool iterations); the teaching version hardcodes 5 turns for easy observation
- The production memory system uses SQLite + FTS5 full-text search + pluggable external providers (Honcho, Mem0, etc.); the teaching version simplifies to single-file `MEMORY.md` reads/writes
- Production's `build_system()` also injects skill catalogs, Curator status, and Insights summaries; the teaching version injects only memory
- The production agent loop includes context compression, error recovery with exponential backoff, model fallback, and other complete mechanisms

</details>

<details>
<summary>Deep Dive into Hermes Source</summary>

The teaching version's 30-line `while True` loop is the core of Hermes' actual implementation. Key source files:

| File | Lines | Role |
|------|-------|------|
| `agent/conversation_loop.py` | ~4714-4722 | Main agent loop, turn handling, stop_reason check |
| `run_agent.py` | full | AIAgent main class, integrates all subsystems |
| `agent/agent_init.py` | full | Agent initialization, nudge interval config |

What the teaching version simplifies:
- Production code has 10+ exit/recovery paths vs. the teaching version's 1
- Production uses streaming tool execution (`StreamingToolExecutor`) for concurrent tool calls
- The `State` object has 10+ fields tracking compaction, recovery, and hooks state
- `stop_reason` is unreliable in streaming; CC checks content blocks directly

</details>

<!-- translation-sync: zh@v1, en@v1 -->
