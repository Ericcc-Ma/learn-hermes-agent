"""
s23: Autonomous Agents — 队友自己看板，有活就认领

Hermes 的自主 agent 模式: 空闲循环 + 自动认领任务 + 自组织。
Agent 不需要 leader 逐个分配 — 自己看任务板，自己认领。

Usage:
    python s23_autonomous/code.py
"""

import json
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

TEAMS_DIR = Path(".hermes") / "teams"


# ── Task Board (shared) ───────────────────────────────

class TaskStatus(Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class BoardTask:
    task_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str = ""
    blocked_by: list[str] = field(default_factory=list)


class SharedTaskBoard:
    """共享任务板 — 所有 agent 从这里认领任务"""

    def __init__(self):
        self.tasks: dict[str, BoardTask] = {}
        self._lock = threading.Lock()

    def post(self, title: str, description: str = "",
             blocked_by: list[str] = None) -> BoardTask:
        """发布新任务到板上"""
        task = BoardTask(
            task_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            blocked_by=blocked_by or [],
        )
        with self._lock:
            self.tasks[task.task_id] = task
        print(f"  [Board] posted: {title}")
        return task

    def get_open(self) -> list[BoardTask]:
        """获取所有可认领的任务"""
        with self._lock:
            return [
                t for t in self.tasks.values()
                if t.status == TaskStatus.PENDING
                and all(
                    dep_id in self.tasks and self.tasks[dep_id].status == TaskStatus.DONE
                    for dep_id in t.blocked_by
                )
            ]

    def claim(self, task_id: str, agent_id: str) -> bool:
        """认领任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            if task.status != TaskStatus.PENDING:
                return False
            task.status = TaskStatus.CLAIMED
            task.assigned_to = agent_id
        print(f"  [{agent_id}] claimed: {task.title}")
        return True

    def complete(self, task_id: str):
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.DONE

    def status_report(self) -> str:
        with self._lock:
            lines = ["\n  📋 Task Board:"]
            for t in self.tasks.values():
                emoji = {"pending": "⬜", "claimed": "🔵", "in_progress": "🟡", "done": "✅"}
                who = f" ← {t.assigned_to}" if t.assigned_to else ""
                lines.append(f"  {emoji.get(t.status.value, '❓')} [{t.task_id}] {t.title}{who}")
            return "\n".join(lines)


# ── Autonomous Agent ──────────────────────────────────

class AutonomousAgent:
    """自主 agent — 空闲时自动扫描任务板，认领并执行"""

    def __init__(self, agent_id: str, board: SharedTaskBoard,
                 skills: list[str] = None,
                 idle_interval: float = 5.0):
        self.agent_id = agent_id
        self.board = board
        self.skills = skills or []
        self.idle_interval = idle_interval
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.stats = {"claimed": 0, "completed": 0}

    def start(self):
        """启动自主循环"""
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._idle_loop, daemon=True, name=f"agent-{self.agent_id}"
        )
        self._thread.start()
        print(f"  [{self.agent_id}] started (skills: {', '.join(self.skills)})")

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        print(f"  [{self.agent_id}] stopped ({self.stats['completed']} completed)")

    def _idle_loop(self):
        """空闲循环 — 每隔 idle_interval 秒扫描一次任务板"""
        while not self._stop_event.is_set():
            if not self._running:
                self._stop_event.wait(1)
                continue

            # 1. 扫描任务板
            open_tasks = self.board.get_open()

            # 2. 筛选自己能做的任务
            for task in open_tasks:
                if self._can_handle(task):
                    if self.board.claim(task.task_id, self.agent_id):
                        self.stats["claimed"] += 1
                        # 3. 执行任务
                        self._execute(task)
                        self.board.complete(task.task_id)
                        self.stats["completed"] += 1
                        break  # 一次只做一个

            # 4. 等待下一轮
            self._stop_event.wait(self.idle_interval)

    def _can_handle(self, task: BoardTask) -> bool:
        """判断这个 agent 能否处理该任务"""
        if not self.skills:  # 没有限制 = 什么都能做
            return True
        # 简单匹配: 任务标题或描述中包含技能关键词
        text = (task.title + " " + task.description).lower()
        return any(skill.lower() in text for skill in self.skills)

    def _execute(self, task: BoardTask):
        """执行任务"""
        print(f"  [{self.agent_id}] executing: {task.title}...")
        # 模拟执行时间
        time.sleep(random.uniform(0.5, 2.0))
        print(f"  [{self.agent_id}] ✅ {task.title}")


# ── Heartbeat ──────────────────────────────────────────

class HeartbeatMonitor:
    """心跳监控 — 确保 agent 还在正常运行"""

    def __init__(self):
        self._heartbeats: dict[str, float] = {}

    def record(self, agent_id: str):
        self._heartbeats[agent_id] = time.time()

    def get_stale(self, timeout: float = 30.0) -> list[str]:
        """返回超时未心跳的 agent 列表"""
        now = time.time()
        return [aid for aid, ts in self._heartbeats.items() if now - ts > timeout]


# ── Main ──────────────────────────────────────────────

def main():
    board = SharedTaskBoard()
    monitor = HeartbeatMonitor()

    print("=" * 60)
    print("s23: Autonomous Agents — 自己看板，有活就认领")
    print("=" * 60)
    print()

    # 1. 发布任务到板上
    print("发布任务:")
    board.post("Fix login bug", "Users cannot login with OAuth")
    board.post("Add rate limiting", "Implement rate limiting for API endpoints")
    board.post("Code review: PR #42", "Review the authentication refactor")
    board.post("Update API docs", "Update swagger documentation")
    board.post("Database optimization", "Add indexes for slow queries",
               blocked_by=["task_fix_login"])  # 依赖先修 bug
    print(board.status_report())

    # 2. 创建不同技能的自主 agent
    print("\n启动自主 agent 团队:")
    bug_fixer = AutonomousAgent("bug-fixer", board, skills=["bug", "fix", "error"])
    api_dev = AutonomousAgent("api-dev", board, skills=["api", "rate", "endpoint"])
    reviewer = AutonomousAgent("reviewer", board, skills=["review", "docs", "documentation"])

    bug_fixer.start()
    api_dev.start()
    reviewer.start()

    # 3. 运行几秒让 agent 认领任务
    print("\nAgent 正在自主认领任务...\n")
    time.sleep(3)

    print(board.status_report())

    # 停止
    bug_fixer.stop()
    api_dev.stop()
    reviewer.stop()

    print(f"\n  Bug-fixer: claimed={bug_fixer.stats['claimed']}, completed={bug_fixer.stats['completed']}")
    print(f"  API-dev:   claimed={api_dev.stats['claimed']}, completed={api_dev.stats['completed']}")
    print(f"  Reviewer:  claimed={reviewer.stats['claimed']}, completed={reviewer.stats['completed']}")
    print()
    print("设计原则:")
    print("  1. 空闲循环 (idle loop) — 每隔 N 秒扫描一次任务板")
    print("  2. 自主认领 — agent 自己判断能不能做，不需要 leader 分配")
    print("  3. 技能匹配 — 任务标题/描述匹配 agent 技能才认领")
    print("  4. 心跳监控 — 检测 agent 是否正常运行")


if __name__ == "__main__":
    main()
