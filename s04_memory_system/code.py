"""
s04: Memory System — 可插拔记忆架构

从单文件 MEMORY.md 进化到多文件 + FTS5 搜索 + 可插拔提供者架构。
演示双层架构: 内置提供者 (Builtin) + 外部提供者接口。

Usage:
    python s04_memory_system/code.py
"""

import json
import os
import re
import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime

from llm import get_client
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

MEMORY_DIR = Path(".memory")
SKILLS_DIR = Path(".skills")

# ── Memory Provider Interface ─────────────────────────

class MemoryProvider(ABC):
    """可插拔记忆提供者抽象基类。

    Hermes 支持多个外部提供者（Honcho, Mem0, Holographic 等）。
    同时只允许注册一个外部提供者，防止工具 schema 膨胀。
    """

    @abstractmethod
    def initialize(self): ...

    @abstractmethod
    def system_prompt_block(self) -> str: ...

    @abstractmethod
    def prefetch(self, query: str) -> str: ...

    @abstractmethod
    def sync_turn(self, user_msg: str, asst_msg: str): ...

    @abstractmethod
    def on_session_end(self): ...

    @abstractmethod
    def handle_tool_call(self, name: str, args: dict) -> str: ...

    @abstractmethod
    def get_tool_schemas(self) -> list: ...

    @abstractmethod
    def shutdown(self): ...


# ── Builtin Memory Provider ───────────────────────────

class BuiltinMemoryProvider(MemoryProvider):
    """内置记忆提供者：FTS5 全文搜索 + MEMORY.md + USER.md

    这是 Hermes 的默认记忆提供者，无需外部依赖。
    """

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(exist_ok=True)
        self.db_path = self.memory_dir / "memory.db"
        self._init_db()

    def _init_db(self):
        """初始化 FTS5 全文搜索数据库"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                mem_type TEXT NOT NULL,
                description TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(name, description, body, content=memories, content_rowid=id)
        """)
        # Triggers to keep FTS in sync
        self.conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS mem_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, name, description, body)
                VALUES (new.id, new.name, new.description, new.body);
            END;
            CREATE TRIGGER IF NOT EXISTS mem_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, name, description, body)
                VALUES ('delete', old.id, old.name, old.description, old.body);
            END;
            CREATE TRIGGER IF NOT EXISTS mem_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, name, description, body)
                VALUES ('delete', old.id, old.name, old.description, old.body);
                INSERT INTO memories_fts(rowid, name, description, body)
                VALUES (new.id, new.name, new.description, new.body);
            END;
        """)
        self.conn.commit()

    def initialize(self):
        print("  [BuiltinMemory] FTS5 database initialized")

    def system_prompt_block(self) -> str:
        """生成注入 system prompt 的记忆上下文"""
        # 读取所有最新记忆条目
        rows = self.conn.execute(
            "SELECT name, mem_type, description FROM memories ORDER BY updated_at DESC LIMIT 20"
        ).fetchall()
        if not rows:
            return ""

        lines = []
        for name, mtype, desc in rows:
            lines.append(f"- [{name}]({name}.md) — {desc} (type: {mtype})")

        index = "\n".join(lines)

        return f"""<memory-context>
[System note: The following is recalled memory context, NOT new user input.
Treat as authoritative reference data — this is the agent's persistent memory.]

{index}
</memory-context>"""

    def prefetch(self, query: str) -> str:
        """每轮前用 FTS5 搜索相关记忆"""
        try:
            rows = self.conn.execute(
                """SELECT m.name, m.mem_type, m.description, m.body
                   FROM memories m
                   JOIN memories_fts fts ON m.id = fts.rowid
                   WHERE memories_fts MATCH ?
                   ORDER BY rank LIMIT 5""",
                (query,)
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS5 query parsing error — fallback to LIKE
            search = f"%{query}%"
            rows = self.conn.execute(
                "SELECT name, mem_type, description, body FROM memories "
                "WHERE name LIKE ? OR description LIKE ? OR body LIKE ? LIMIT 5",
                (search, search, search)
            ).fetchall()

        if not rows:
            return ""

        parts = []
        for name, mtype, desc, body in rows:
            parts.append(f"---\nname: {name}\ntype: {mtype}\ndescription: {desc}\n---\n\n{body}")

        return "\n".join(parts)

    def sync_turn(self, user_msg: str, asst_msg: str):
        """每轮后异步写入。Builtin 不在此处写入——用 background_review 替代。"""
        pass

    def write_memory(self, name: str, mem_type: str, description: str, body: str):
        """写入或更新一条记忆"""
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT INTO memories (name, mem_type, description, body, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
               mem_type=excluded.mem_type, description=excluded.description,
               body=excluded.body, updated_at=excluded.updated_at""",
            (name, mem_type, description, body, now, now)
        )
        self.conn.commit()

        # Also write to MEMORY.md for backward compat
        mem_file = self.memory_dir / "MEMORY.md"
        entry = f"""---
name: {name}
type: {mem_type}
description: {description}
---

{body}
"""
        with open(mem_file, "a", encoding="utf-8") as f:
            f.write("\n---\n" + entry)

    def search(self, query: str, limit: int = 5) -> list:
        """搜索记忆，返回匹配条目"""
        rows = self.conn.execute(
            """SELECT name, mem_type, description, body
               FROM memories WHERE name LIKE ? OR description LIKE ?
               OR body LIKE ? ORDER BY updated_at DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        return [{"name": r[0], "mem_type": r[1], "description": r[2], "body": r[3]} for r in rows]

    def on_session_end(self):
        """会话结束时的清理"""
        print("  [BuiltinMemory] Session ended, memories persisted to SQLite")

    def handle_tool_call(self, name: str, args: dict) -> str:
        if name == "memory_search":
            results = self.search(args.get("query", ""), args.get("limit", 5))
            return json.dumps(results, ensure_ascii=False, indent=2)
        elif name == "memory_write":
            self.write_memory(
                name=args.get("name", "unknown"),
                mem_type=args.get("mem_type", "user"),
                description=args.get("description", ""),
                body=args.get("body", ""),
            )
            return f"Memory saved: {args.get('name')}"
        return f"Unknown memory operation: {name}"

    def get_tool_schemas(self) -> list:
        return [
            {
                "name": "memory_search",
                "description": "Search persistent memory using keywords. Returns matching entries.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 5}
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "memory_write",
                "description": "Write a fact to persistent memory.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "mem_type": {"type": "string", "enum": ["user", "feedback", "project", "reference"]},
                        "description": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["name", "mem_type", "description", "body"],
                },
            },
        ]

    def shutdown(self):
        self.conn.close()


# ── Memory Manager ────────────────────────────────────

class MemoryManager:
    """编排记忆提供者的管理器。

    同时只有一个外部提供者被注册。
    Builtin 始终作为 fallback 存在。
    """

    def __init__(self, memory_dir: Path = MEMORY_DIR):
        self.builtin = BuiltinMemoryProvider(memory_dir)
        self.external: MemoryProvider | None = None
        self.builtin.initialize()

    def register_external(self, provider: MemoryProvider):
        """注册外部记忆提供者（替换之前的）"""
        if self.external:
            self.external.shutdown()
        self.external = provider
        provider.initialize()
        print(f"  [MemoryManager] Registered external provider: {type(provider).__name__}")

    def get_active_provider(self) -> MemoryProvider:
        """获取当前活跃的提供者（外部优先）"""
        return self.external or self.builtin

    def system_prompt_block(self) -> str:
        block = self.builtin.system_prompt_block()
        if self.external:
            block += "\n" + self.external.system_prompt_block()
        return block

    def prefetch(self, query: str) -> str:
        result = self.builtin.prefetch(query)
        if self.external:
            result += "\n" + self.external.prefetch(query)
        return result

    def get_all_tools(self) -> list:
        tools = self.builtin.get_tool_schemas()
        if self.external:
            tools.extend(self.external.get_tool_schemas())
        return tools


# ── Initialize ────────────────────────────────────────

memory_manager = MemoryManager()

# ── Tools ─────────────────────────────────────────────

BASH_TOOL = {
    "name": "bash",
    "description": "Execute a shell command.",
    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
}

def run_bash(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=os.getcwd())
        return result.stdout + ("\n[stderr]\n" + result.stderr if result.stderr else "") or "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30s"
    except Exception as e:
        return f"Error: {e}"

TOOL_HANDLERS = {"bash": run_bash}

def rebuild_tools():
    """每轮前重建工具列表（包含记忆工具）"""
    return [BASH_TOOL] + memory_manager.get_all_tools()

def build_system() -> str:
    memory_block = memory_manager.system_prompt_block()
    base = "You are a helpful coding agent."
    if memory_block:
        return memory_block + "\n\n" + base
    return base


# ── Agent Loop ────────────────────────────────────────

def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def execute_tools(content) -> list:
    results = []
    for block in content:
        name, input_data, block_id = None, None, None
        if hasattr(block, "type") and block.type == "tool_use":
            name, input_data, block_id = block.name, block.input, block.id
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            name, input_data, block_id = block["name"], block["input"], block["id"]

        if not name:
            continue

        # Try builtin handler first, then memory provider
        if name in TOOL_HANDLERS:
            output = TOOL_HANDLERS[name](**(input_data or {}))
        else:
            provider = memory_manager.get_active_provider()
            try:
                output = provider.handle_tool_call(name, input_data or {})
            except Exception:
                output = f"Unknown tool: {name}"

        results.append({"type": "tool_result", "tool_use_id": block_id, "content": str(output)})
    return results


def agent_loop(query: str, client, messages=None):
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": query})

    while True:
        system = build_system()
        tools = rebuild_tools()

        response = client.messages.create(
            model=MODEL, system=system,
            messages=messages, tools=tools,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            memory_manager.builtin.on_session_end()
            return response

        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})


# ── Main ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("s04: Memory System — 可插拔记忆架构")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Provider: Builtin (FTS5 + SQLite)")
    print()
    print("试试: 'Save a memory: the production DB is at db.prod.example.com'")
    print("试试: 'Search memory for database'")
    print("试试: 'Remember that I use pytest with coverage'")
    print("输入 /exit 退出, /memories 查看所有记忆")
    print()

    messages = []

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query == "/exit":
            memory_manager.builtin.shutdown()
            break
        if query == "/memories":
            results = memory_manager.builtin.search("", 30)
            for r in results:
                print(f"  [{r['mem_type']}] {r['name']}: {r['description']}")
            print()
            continue

        response = agent_loop(query, CLIENT, messages)
        text = extract_text(response.content)
        print(text)
        print()


if __name__ == "__main__":
    main()
