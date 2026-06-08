"""
s22: Planning System — 没计划的 agent 走哪算哪

Hermes 的任务规划系统: 先列步骤再动手，完成率翻倍。
TodoWrite 工具 + 任务依赖图 + 状态追踪。

Usage:
    python s22_planning/code.py
"""

import json
import os
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


# ── Task Status ────────────────────────────────────────

class TaskStatus(Enum):
    PENDING = "pending"        # 待开始
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"     # 已完成
    BLOCKED = "blocked"         # 被阻塞
    CANCELLED = "cancelled"     # 已取消


# ── Task Item ──────────────────────────────────────────

@dataclass
class TodoItem:
    """一个待办任务"""
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    blocked_by: list[str] = field(default_factory=list)  # 依赖的任务 ID
    blocks: list[str] = field(default_factory=list)       # 被此任务阻塞的任务 ID
    created_at: str = ""
    completed_at: str = ""
    order: int = 0               # 执行顺序
    activeForm: str = ""         # 进行中时的描述（如"正在安装依赖"）


# ── Task Manager ───────────────────────────────────────

class TaskManager:
    """任务管理器 — 维护任务依赖图和状态"""

    def __init__(self, tasks_file: Path = Path(".hermes") / "tasks.json"):
        self.tasks_file = tasks_file
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: dict[str, TodoItem] = {}
        self._load()

    def _load(self):
        if self.tasks_file.exists():
            try:
                data = json.loads(self.tasks_file.read_text())
                for item in data.get("tasks", []):
                    task = TodoItem(
                        id=item["id"], title=item["title"],
                        description=item.get("description", ""),
                        status=TaskStatus(item.get("status", "pending")),
                        blocked_by=item.get("blocked_by", []),
                        blocks=item.get("blocks", []),
                        created_at=item.get("created_at", ""),
                        completed_at=item.get("completed_at", ""),
                        order=item.get("order", 0),
                        activeForm=item.get("activeForm", ""),
                    )
                    self.tasks[task.id] = task
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        data = {
            "tasks": [
                {
                    "id": t.id, "title": t.title, "description": t.description,
                    "status": t.status.value, "blocked_by": t.blocked_by,
                    "blocks": t.blocks, "created_at": t.created_at,
                    "completed_at": t.completed_at, "order": t.order,
                    "activeForm": t.activeForm,
                }
                for t in sorted(self.tasks.values(), key=lambda x: x.order)
            ],
            "updated_at": datetime.now().isoformat(),
        }
        self.tasks_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def create(self, title: str, description: str = "",
               blocked_by: list[str] = None, activeForm: str = "") -> TodoItem:
        """创建新任务"""
        task = TodoItem(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            blocked_by=blocked_by or [],
            created_at=datetime.now().isoformat(),
            order=len(self.tasks),
            activeForm=activeForm,
        )
        # 更新被依赖任务的 blocks 字段
        for dep_id in task.blocked_by:
            if dep_id in self.tasks:
                self.tasks[dep_id].blocks.append(task.id)

        self.tasks[task.id] = task
        self._save()
        return task

    def start(self, task_id: str) -> bool:
        """开始执行任务 — 检查依赖是否满足"""
        if task_id not in self.tasks:
            return False
        task = self.tasks[task_id]

        # 检查依赖
        for dep_id in task.blocked_by:
            if dep_id in self.tasks and self.tasks[dep_id].status != TaskStatus.COMPLETED:
                print(f"  ⚠️ 任务 '{task.title}' 被 '{self.tasks[dep_id].title}' 阻塞")
                task.status = TaskStatus.BLOCKED
                self._save()
                return False

        task.status = TaskStatus.IN_PROGRESS
        if task.activeForm:
            print(f"  🔵 {task.activeForm}")
        self._save()
        return True

    def complete(self, task_id: str):
        """完成任务 — 解锁依赖它的任务"""
        if task_id not in self.tasks:
            return
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now().isoformat()
        print(f"  ✅ {task.title}")
        self._save()

    def cancel(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            self._save()

    def get_available(self) -> list[TodoItem]:
        """获取当前可开始的任务（依赖全部满足）"""
        available = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if all(
                dep_id in self.tasks and self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.blocked_by
            ):
                available.append(task)
        return sorted(available, key=lambda x: x.order)

    def status_report(self) -> str:
        """生成任务状态报告"""
        lines = ["\n  📋 任务状态:"]
        for task in sorted(self.tasks.values(), key=lambda x: x.order):
            emoji = {
                TaskStatus.PENDING: "⬜",
                TaskStatus.IN_PROGRESS: "🔵",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.BLOCKED: "🔒",
                TaskStatus.CANCELLED: "❌",
            }
            deps = f" (依赖: {', '.join(task.blocked_by)})" if task.blocked_by else ""
            info = f" — {task.activeForm}" if task.activeForm and task.status == TaskStatus.IN_PROGRESS else ""
            lines.append(f"  {emoji[task.status]} [{task.id}] {task.title}{deps}{info}")
        return "\n".join(lines)


# ── TodoWrite Tool ─────────────────────────────────────

TODO_WRITE_TOOL = {
    "name": "todo_write",
    "description": "Create and manage a structured task list. Plan before executing complex tasks.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                        "activeForm": {"type": "string"},
                        "blocked_by": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title"],
                },
            }
        },
        "required": ["tasks"],
    },
}


# ── Main ──────────────────────────────────────────────

def main():
    manager = TaskManager()

    print("=" * 60)
    print("s22: Planning System — 没计划的 agent 走哪算哪")
    print("=" * 60)
    print()

    # 演示: Agent 收到复杂任务，先列计划
    print("Agent 收到任务: '实现用户认证系统'")
    print("\nAgent 先列计划 (TodoWrite):")

    # 创建任务依赖图
    t1 = manager.create("设计数据库 schema", "users 表 + sessions 表")
    t2 = manager.create("实现注册接口", "POST /api/register", blocked_by=[t1.id])
    t3 = manager.create("实现登录接口", "POST /api/login + JWT", blocked_by=[t1.id])
    t4 = manager.create("写单元测试", "pytest 覆盖所有接口", blocked_by=[t2.id, t3.id])
    t5 = manager.create("部署到 staging", "验证 staging 环境", blocked_by=[t4.id])

    print(manager.status_report())

    # 模拟执行流程
    print("\n━━━ 执行流程 ━━━")

    print("\n第 1 步: 开始可执行的任务")
    for task in manager.get_available():
        manager.start(task.id)

    # 完成 t1
    manager.complete(t1.id)

    print("\n第 2 步: t1 完成后，t2 和 t3 解锁")
    for task in manager.get_available():
        manager.start(task.id)

    # 完成 t2, t3
    manager.complete(t2.id)
    manager.complete(t3.id)

    print("\n第 3 步: t2 和 t3 完成后，t4 解锁")
    for task in manager.get_available():
        manager.start(task.id)

    manager.complete(t4.id)

    print("\n最终状态:")
    print(manager.status_report())

    progress = sum(1 for t in manager.tasks.values() if t.status == TaskStatus.COMPLETED)
    print(f"\n  📊 进度: {progress}/{len(manager.tasks)} ({100*progress//len(manager.tasks)}%)")
    print()
    print("设计原则:")
    print("  1. 先列计划 → 再执行 — 完成率翻倍")
    print("  2. blocked_by 表示依赖 — 支持复杂 DAG")
    print("  3. activeForm — 进行中时显示当前动作")
    print("  4. 文件落盘 — 跨 session 持久化")


if __name__ == "__main__":
    main()
