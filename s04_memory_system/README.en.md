# s04: Memory System — Pluggable Memory Architecture

[中文](README.md) · [English](README.en.md)

s01 → s02 → s03 → `s04` → [s05](../s05_skill_lifecycle/) → ... → s12
> *"Memory shouldn't be just one file"* — Dual-layer architecture + FTS5 full-text search + pluggable providers + lifecycle hooks.
>
> **Self-Evolution Layer**: Memory System — the persistent knowledge base for cross-session learning.

---

## Problem

s01-s03's memory system is a single `MEMORY.md` file. Simple but fragile:
- Search is limited to filename and description — no full-text search
- No structured query interface
- No extensibility — want to switch to a vector database? Rewrite everything

Production needs: full-text search, replaceable storage backends, rich lifecycle events.

---

## Solution

**Dual-layer architecture**:

```
MemoryManager (orchestrator)
    ├── BuiltinProvider (always available)
    │   ├── SQLite + FTS5 full-text search
    │   ├── MEMORY.md (backward compatible)
    │   └── USER.md (user profile)
    └── ExternalProvider (optional, one at a time)
        ├── Honcho (dialectical user modeling)
        ├── Mem0 (vectorized memory)
        └── ... (other providers)
```

---

## Core Components

### Provider Interface (16 lifecycle hooks)

```python
class MemoryProvider(ABC):
    initialize()            # Connect, create resources
    system_prompt_block()   # Static system prompt text
    prefetch(query)         # Background recall before each turn
    sync_turn(user, asst)   # Async write after each turn
    on_session_end()        # Fact extraction at session end
    on_pre_compress()       # Extract insights before context compression
    get_tool_schemas()      # Tools exposed to the model
    handle_tool_call()      # Dispatch tool calls
    shutdown()              # Cleanup on exit
```

### FTS5 Full-Text Search

```sql
SELECT name, description FROM memories
JOIN memories_fts ON memories.id = memories_fts.rowid
WHERE memories_fts MATCH 'prefers tabs indentation'
ORDER BY rank LIMIT 5;
```

### Context Injection Format

Memory is injected into the system prompt via fenced blocks, clearly distinguished as reference data:

```xml
<memory-context>
[System note: The following is recalled memory context, NOT new user input.]

- [user-prefers-tabs](user-prefers-tabs.md) — User prefers tabs (type: user)

</memory-context>
```

---

## Try It

```sh
python s04_memory_system/code.py
```

Try: save memories, search them, observe FTS5 matching. Use `/memories` to list all.

---

## Next

The memory system is ready. But skills are just files in `.skills/` with no lifecycle management. Skills accumulate endlessly — they need stale/archive mechanics.

s05 Skill Lifecycle → active → stale → archived state machine + umbrella structure.

<details>
<summary>Deep Dive into Hermes Source</summary>

This section maps to the following source files in the production Hermes codebase:

- **`agent/memory_manager.py`** — The memory provider orchestrator. Production's `MemoryManager` coordinates built-in and external providers, manages the call order of 16 lifecycle hooks, ensures the `BuiltinProvider` (`MEMORY.md` + `USER.md` + SQLite FTS5) is always available, and allows only one external provider to be registered at a time (preventing tool schema bloat).
- **`agent/memory_provider.py`** — Abstract base class for memory providers. Defines the complete interface contract: `initialize()` (connect/create resources), `system_prompt_block()` (static system prompt), `prefetch(query)` (background recall before each turn), `sync_turn(user, asst)` (async write after each turn), `on_session_end()` (fact extraction at session end), `on_pre_compress()` (extract insights before compression), `get_tool_schemas()` / `handle_tool_call()` (tool exposure and dispatch), `shutdown()` (cleanup on exit), and more.
- **`plugins/memory/`** — External provider directory containing 8 pluggable implementations: **Honcho** (dialectical user modeling), **Holographic** (holographic memory storage), **Mem0** (vectorized memory), **Hindsight** (post-hoc insights), **RetainDB**, **Supermemory**, **ByteRover**, **OpenViking**.

**What the teaching version simplifies**:
- Production has a full abstract base class + 16 lifecycle hooks; the teaching version simplifies to `read()`/`write()`/`search()` three methods
- Production uses SQLite + FTS5 for full-text search (supporting BM25 ranking); the teaching version uses simple string matching
- Production supports structured queries across multiple memory types (user/feedback/project/reference); the teaching version uses flat text storage
- Production's context injection uses the `<memory-context>` fenced block format to strictly distinguish "system reference data" from "user input"; the teaching version uses a simplified format

</details>

<details>
<summary>Deep Dive into Hermes Source</summary>

The production memory system has a rich provider architecture:

| File | Lines | Role |
|------|-------|------|
| `agent/memory_manager.py` | full | Provider orchestrator, lifecycle coordination |
| `agent/memory_provider.py` | full | Abstract base class with 16 lifecycle hooks |
| `plugins/memory/honcho/` | full | Honcho dialectical user modeling plugin |
| `plugins/memory/holographic/` | full | Holographic memory plugin |
| `plugins/memory/mem0/` | full | Mem0 vector memory plugin |

Supported external providers: Honcho, Holographic, Mem0, Hindsight, RetainDB, Supermemory, ByteRover, OpenViking.

What the teaching version simplifies:
- Only one external provider can be registered at a time in production (prevents tool schema bloat)
- Production has 16 lifecycle hooks vs. the teaching version's 6
- Context injection uses specific XML fenced blocks to distinguish from user input
- Memory prefetch runs asynchronously (non-blocking) in production

</details>

<!-- translation-sync: zh@v1, en@v1 -->
