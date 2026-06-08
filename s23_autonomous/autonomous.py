"""
s23: Kanban Dispatcher — 中心调度 + Worker 执行

Hermes 的团队调度不是 worker 自己扫板认领，而是 Kanban Dispatcher 模式:
Dispatcher 每 60s tick → 扫描 ready 任务 → spawn worker 进程 → 分配任务。
Worker 定期 heartbeat 保持 claim，超时则 reclaim 给其他 worker。

Usage:
    python s23_autonomous/autonomous.py
"""

import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

KANBAN_DIR = Path(".hermes") / "kanban"
DEFAULT_CLAIM_TTL = 15 * 60       # 15 分钟无心跳则 reclaim
DISPATCH_INTERVAL = 60             # 每 60s tick
FAILURE_LIMIT = 2                  # 连续失败 2 次自动 block


class TaskStatus(Enum):
    TODO = "todo"
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    BLOCKED = "blocked"


@dataclass
class KanbanTask:
    task_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    assignee: str = ""
    blocked_by: list[str] = field(default_factory=list)
    failure_count: int = 0
    claim_lock: str = ""
    claim_expires: str = ""
    goal_mode: bool = False


class KanbanBoard:
    """SQLite 持久化任务板"""

    def __init__(self):
        self.db_path = KANBAN_DIR / "board.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, title TEXT, description TEXT DEFAULT '',
                status TEXT DEFAULT 'todo', assignee TEXT DEFAULT '',
                blocked_by TEXT DEFAULT '[]', failure_count INTEGER DEFAULT 0,
                claim_lock TEXT DEFAULT '', claim_expires TEXT DEFAULT '',
                goal_mode INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT
            )
        """)
        self.conn.commit()

    def create(self, title: str, **kwargs) -> KanbanTask:
        tid = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with self._lock:
            self.conn.execute(
                "INSERT INTO tasks (id,title,description,status,blocked_by,created_at,updated_at,goal_mode) "
                "VALUES (?,'todo',?,?,?,?,?,?)",
                (tid, title, kwargs.get("description", ""),
                 json.dumps(kwargs.get("blocked_by", [])),
                 now, now, int(kwargs.get("goal_mode", False))),
            )
            self.conn.commit()
        print(f"  [Board] created: {title}")
        return KanbanTask(task_id=tid, title=title, **kwargs)

    def promote_ready(self) -> int:
        """将依赖满足的 todo 任务提升为 ready"""
        now = datetime.now().isoformat()
        promoted = 0
        with self._lock:
            rows = self.conn.execute(
                "SELECT id, title, blocked_by FROM tasks WHERE status='todo'"
            ).fetchall()
            for tid, title, blocked_json in rows:
                blocked = json.loads(blocked_json)
                if all(
                    self.conn.execute("SELECT status FROM tasks WHERE id=?", (d,)).fetchone()
                    and self.conn.execute("SELECT status FROM tasks WHERE id=?", (d,)).fetchone()[0] == "done"
                    for d in blocked
                ):
                    self.conn.execute(
                        "UPDATE tasks SET status='ready', updated_at=? WHERE id=?", (now, tid)
                    )
                    promoted += 1
            self.conn.commit()
        return promoted

    def claim_and_spawn(self, worker_id: str) -> KanbanTask | None:
        """原子认领一个 ready 任务"""
        now = datetime.now().isoformat()
        with self._lock:
            row = self.conn.execute(
                "SELECT id, title FROM tasks WHERE status='ready' LIMIT 1"
            ).fetchone()
            if not row:
                return None
            tid, title = row
            lock_id = str(uuid.uuid4())[:8]
            self.conn.execute(
                "UPDATE tasks SET status='running', assignee=?, claim_lock=?, "
                "claim_expires=?, updated_at=? WHERE id=?",
                (worker_id, lock_id, now.isoformat(), now.isoformat(), tid),
            )
            self.conn.commit()
        print(f"  [Dispatcher] claimed '{title}' → {worker_id}")
        return KanbanTask(task_id=tid, title=title, status=TaskStatus.RUNNING,
                          assignee=worker_id, claim_lock=lock_id)

    def complete(self, task_id: str):
        with self._lock:
            self.conn.execute("UPDATE tasks SET status='done', updated_at=? WHERE id=?",
                              (datetime.now().isoformat(), task_id))
            self.conn.commit()
        print(f"  [Worker] completed: {task_id}")

    def reclaim_stale(self, ttl: int = DEFAULT_CLAIM_TTL) -> int:
        """回收超时 TTL 的 running 任务"""
        reclaimed = 0
        now = datetime.now()
        with self._lock:
            rows = self.conn.execute(
                "SELECT id, title, claim_expires FROM tasks WHERE status='running'"
            ).fetchall()
            for tid, title, expires in rows:
                try:
                    exp = datetime.fromisoformat(expires)
                    if (now - exp).total_seconds() > ttl:
                        self.conn.execute(
                            "UPDATE tasks SET status='ready', assignee='', "
                            "claim_lock='', claim_expires='' WHERE id=?", (tid,)
                        )
                        reclaimed += 1
                        print(f"  [Dispatcher] reclaimed stale: {title}")
                except (ValueError, TypeError):
                    pass
            self.conn.commit()
        return reclaimed

    def block_on_failure(self, task_id: str):
        with self._lock:
            row = self.conn.execute("SELECT failure_count FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row:
                count = row[0] + 1
                if count >= FAILURE_LIMIT:
                    self.conn.execute("UPDATE tasks SET status='blocked', failure_count=? WHERE id=?",
                                      (count, task_id))
                    print(f"  [Dispatcher] blocked after {count} failures: {task_id}")
                else:
                    self.conn.execute("UPDATE tasks SET failure_count=?, status='todo' WHERE id=?",
                                      (count, task_id))

    def status_report(self) -> str:
        with self._lock:
            rows = self.conn.execute(
                "SELECT id, title, status, assignee FROM tasks ORDER BY created_at"
            ).fetchall()
        lines = ["\n  📋 Kanban Board:"]
        emoji = {"todo": "⬜", "ready": "🟢", "running": "🔵", "done": "✅", "blocked": "🔒"}
        for tid, title, status, assignee in rows:
            who = f" ← {assignee}" if assignee else ""
            lines.append(f"  {emoji.get(status, '❓')} [{tid}] {title}{who}")
        return "\n".join(lines)


class KanbanDispatcher:
    """中心调度器 — 每 60s tick 一次，6 步调度循环"""

    def __init__(self, board: KanbanBoard):
        self.board = board
        self._running = False
        self._stop = threading.Event()
        self.stats = {"ticks": 0, "spawned": 0, "reclaimed": 0, "promoted": 0}

    def start(self):
        self._running = True
        self._stop.clear()
        threading.Thread(target=self._loop, daemon=True, name="kanban-dispatcher").start()
        print(f"  [Dispatcher] started (interval={DISPATCH_INTERVAL}s)")

    def stop(self):
        self._running = False
        self._stop.set()
        print(f"  [Dispatcher] stopped. stats={self.stats}")

    def _loop(self):
        while not self._stop.is_set():
            self._tick()
            self._stop.wait(DISPATCH_INTERVAL)

    def _tick(self):
        """一次调度周期: 6 个步骤"""
        self.stats["ticks"] += 1
        # 1. Reclaim 超时任务
        self.stats["reclaimed"] += self.board.reclaim_stale()
        # 2. Promote ready 任务
        self.stats["promoted"] += self.board.promote_ready()
        # 3. Claim + Spawn
        task = self.board.claim_and_spawn(f"worker-{uuid.uuid4().hex[:4]}")
        if task:
            self.stats["spawned"] += 1
            time.sleep(0.3)
            self.board.complete(task.task_id)


def main():
    board = KanbanBoard()
    dispatcher = KanbanDispatcher(board)

    print("=" * 60)
    print("s23: Kanban Dispatcher — 中心调度 + Worker 执行")
    print("=" * 60)
    print()
    print("Hermes 团队调度不是 worker 自己扫板，是 Dispatcher 中心分配:")
    print()
    print("  ┌────────────────────────────────────────────┐")
    print("  │         Kanban Dispatcher                  │")
    print("  │  每 60s tick:                              │")
    print("  │  1. Reclaim 超时 (TTL=15min)               │")
    print("  │  2. Promote ready 任务                     │")
    print("  │  3. Claim + Spawn worker 进程              │")
    print("  │  4. 失败保护 (连续{0}次→block)              │".format(FAILURE_LIMIT))
    print("  └──────────────┬─────────────────────────────┘")
    print("                 │ spawn 独立进程")
    print("                 ▼")
    print("  ┌──────────────────────────────────────────┐")
    print("  │  Worker: hermes -p <p> chat -q ...        │")
    print("  │  定期 heartbeat · 完成 → complete         │")
    print("  └──────────────────────────────────────────┘")
    print()

    board.create("Fix login bug")
    board.create("Add rate limiting")
    board.create("Update API docs", blocked_by=["fix_login_bug"])

    print(board.status_report())

    print("\nDispatcher tick:")
    dispatcher._tick()
    print(board.status_report())

    print(f"\n{dispatcher.stats}")
    print()
    print("三种 Agent Team 触发模式对比:")
    print("  ┌──────────────┬──────────┬──────────────────┐")
    print("  │ delegate_task│ LLM 决策 │ 同步, 不持久      │")
    print("  │ Cron         │ 定时调度 │ 异步, jobs.json   │")
    print("  │ Kanban       │ 事件循环 │ 异步, SQLite 持久  │")
    print("  └──────────────┴──────────┴──────────────────┘")


if __name__ == "__main__":
    main()
