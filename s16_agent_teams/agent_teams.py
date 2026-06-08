"""
s16: Agent Teams — delegate_task 工具 + 角色系统

Hermes 的 agent team 由 LLM 自主通过 delegate_task 工具触发。
两种模式: Single（单任务）和 Batch（并行批量）。
角色系统: leaf（纯 worker）和 orchestrator（可继续 spawn）。

Usage:
    python s16_agent_teams/agent_teams.py
"""

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()


# ── Role System ────────────────────────────────────────

class AgentRole(Enum):
    LEAF = "leaf"                # 纯 worker，被剥夺 delegate_task
    ORCHESTRATOR = "orchestrator"  # 可以继续 spawn 子 agent


# ── Delegate Config ────────────────────────────────────

@dataclass
class DelegateConfig:
    max_concurrent_children: int = 3    # 单次最多并行
    max_spawn_depth: int = 1            # 最大嵌套深度
    orchestrator_enabled: bool = True   # 是否允许 orchestrator 角色
    child_timeout_seconds: int = 300    # 子 agent 超时
    max_iterations: int = 90            # 子 agent 最大 tool-calling 迭代数
    inherit_mcp_toolsets: bool = False  # 子 agent 是否继承 MCP 工具集


# ── Delegate Task Schema ───────────────────────────────

@dataclass
class DelegateTask:
    """一次委托任务"""
    goal: str                        # 任务目标
    context: str = ""                # 额外上下文
    toolsets: list[str] = field(default_factory=list)  # 允许的工具集
    role: AgentRole = AgentRole.LEAF # 子 agent 角色


@dataclass
class DelegateBatch:
    """批量委托 — 并发启动 N 个子 agent"""
    tasks: list[DelegateTask] = field(default_factory=list)


# ── Agent Tree ─────────────────────────────────────────

class DelegateTree:
    """管理 agent 的嵌套层级"""

    def __init__(self, config: DelegateConfig = None):
        self.config = config or DelegateConfig()
        self.depth = 0
        self.children: list["DelegateTree"] = []
        self.parent: "DelegateTree" = None
        self.agent_id = str(uuid.uuid4())[:8]

    def can_spawn(self) -> tuple[bool, str]:
        """检查是否可以 spawn 子 agent"""
        if self.depth >= self.config.max_spawn_depth:
            return False, f"max depth reached (depth={self.depth}, max={self.config.max_spawn_depth})"
        return True, ""

    def spawn(self, task: DelegateTask) -> "DelegateTree":
        """spawn 一个子 agent"""
        ok, reason = self.can_spawn()
        if not ok:
            print(f"  [Delegate] blocked: {reason}")
            return None

        if len(self.children) >= self.config.max_concurrent_children:
            print(f"  [Delegate] blocked: max_concurrent_children={self.config.max_concurrent_children}")
            return None

        child = DelegateTree(self.config)
        child.depth = self.depth + 1
        child.parent = self
        self.children.append(child)
        print(f"  [Delegate] spawned {child.agent_id} (depth={child.depth}, role={task.role.value})")
        return child

    def execute(self, task: DelegateTask) -> str:
        """执行子 agent 的任务并返回 summary"""
        # 根据 role 决定可用工具
        if task.role == AgentRole.LEAF:
            disabled_tools = ["delegate_task", "clarify", "memory", "send_message", "execute_code"]
        else:
            disabled_tools = []

        print(f"  [{self.agent_id}] executing: {task.goal[:60]}...")

        try:
            response = CLIENT.messages.create(
                model=MODEL,
                system=f"You are a worker agent (role={task.role.value}). "
                       f"Disabled tools: {', '.join(disabled_tools)}. "
                       f"Complete this task: {task.goal}",
                messages=[{"role": "user", "content": f"Context: {task.context}\n\nGoal: {task.goal}"}],
                max_tokens=1000,
            )
            text = response.content[0].get("text", "") if response.content else ""
            print(f"  [{self.agent_id}] completed: {text[:100]}...")
            return text
        except Exception as e:
            return f"Error: {e}"


# ── Delegate Tool Definition ───────────────────────────

DELEGATE_TOOL = {
    "name": "delegate_task",
    "description": (
        "Delegate work to sub-agents. Use single mode for one task, "
        "batch mode for parallel execution of N tasks."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["single", "batch"],
                "description": "single: one task. batch: parallel N tasks",
            },
            "goal": {"type": "string", "description": "Task goal (single mode)"},
            "context": {"type": "string", "description": "Additional context"},
            "role": {
                "type": "string",
                "enum": ["leaf", "orchestrator"],
                "description": "leaf=worker (no delegate), orchestrator=can spawn own children",
            },
            "toolsets": {
                "type": "array", "items": {"type": "string"},
                "description": "Allowed toolsets for the child agent",
            },
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "context": {"type": "string"},
                        "role": {"type": "string", "enum": ["leaf", "orchestrator"]},
                    },
                    "required": ["goal"],
                },
                "description": "List of tasks (batch mode)",
            },
        },
        "required": ["mode"],
    },
}


# ── Demonstration ──────────────────────────────────────

def demo_single_delegate():
    """演示: LLM 调用 delegate_task 单任务"""
    print("\n━━━ Single Mode ━━━")
    config = DelegateConfig()
    tree = DelegateTree(config)

    task = DelegateTask(
        goal="Review auth.py for SQL injection vulnerabilities",
        context="This is a security audit for the authentication module",
        role=AgentRole.LEAF,
    )

    child = tree.spawn(task)
    if child:
        summary = child.execute(task)
        print(f"  Summary: {summary[:200]}")

        # leaf 不能再 spawn
        ok, reason = child.can_spawn()
        print(f"  Leaf can spawn? {ok} ({reason})")


def demo_batch_delegate():
    """演示: LLM 调用 delegate_task 批量并行"""
    print("\n━━━ Batch Mode ━━━")
    config = DelegateConfig()
    tree = DelegateTree(config)

    tasks = [
        DelegateTask(goal="Research REST API frameworks", role=AgentRole.LEAF),
        DelegateTask(goal="Implement /users endpoint", role=AgentRole.LEAF),
        DelegateTask(goal="Write unit tests", role=AgentRole.LEAF),
    ]

    print(f"  Spawning {len(tasks)} parallel workers (max={config.max_concurrent_children})...")
    children = []
    for task in tasks:
        child = tree.spawn(task)
        if child:
            children.append(child)

    print(f"  Spawned {len(children)}/{len(tasks)} workers")
    for child in children:
        child.execute(DelegateTask(goal="demo task"))

    # 清理
    tree.children = []


def demo_orchestrator():
    """演示: orchestrator 角色 — 可以继续 spawn"""
    print("\n━━━ Orchestrator Role ━━━")
    config = DelegateConfig(max_spawn_depth=2)  # 允许最多 2 层嵌套
    root = DelegateTree(config)

    # 第一层: orchestrator
    orch = root.spawn(DelegateTask(
        goal="Design and implement the auth module",
        role=AgentRole.ORCHESTRATOR,
    ))
    print(f"  Depth: root={root.depth}, orchestrator={orch.depth if orch else 'N/A'}")

    # orchestrator spawn 自己的 worker
    if orch:
        worker = orch.spawn(DelegateTask(goal="Write login endpoint", role=AgentRole.LEAF))
        if worker:
            print(f"  Depth: root={root.depth}, orch={orch.depth}, worker={worker.depth}")
            # worker 不能再 spawn
            ok, reason = worker.can_spawn()
            print(f"  Worker can spawn? {ok} ({reason})")


def main():
    print("=" * 60)
    print("s16: Agent Teams — delegate_task + 角色系统")
    print("=" * 60)
    print()
    print("Hermes agent team 由 LLM 自主通过 delegate_task 工具触发")
    print()
    print("三种触发模式:")
    print("  ┌──────────────┬────────────┬──────────────────────┐")
    print("  │ delegate_task│  LLM 决策  │  对话中即时 spawn      │")
    print("  │ Cron         │  定时调度  │  到时间自动触发        │")
    print("  │ Kanban       │  事件循环  │  Dispatcher 中心分配   │")
    print("  └──────────────┴────────────┴──────────────────────┘")
    print()
    print("角色系统:")
    print("  leaf (默认):  纯 worker, 被剥夺 delegate_task")
    print("  orchestrator: 保留 delegate_task, 可继续 spawn")
    print(f"  最大嵌套深度: max_spawn_depth=1 (最多 2 层)")
    print()

    demo_single_delegate()
    demo_batch_delegate()
    demo_orchestrator()

    print()
    print("关键设计:")
    print("  1. delegate_task 是同步的 — 父 agent 等子 agent 完成")
    print("  2. leaf worker 被禁用 delegate_task/clarify/memory 等工具")
    print("  3. orchestrator 受 max_spawn_depth 限制防止无限嵌套")
    print("  4. max_concurrent_children 控制并行度")
    print("  5. 不持久 — 不跨 turn 存活")


if __name__ == "__main__":
    main()
