"""
s16: Agent Teams — 一个搞不定，组队来

Hermes 的 agent 团队系统: 子 agent 派生 + 异步邮箱通信 + 任务板自组织。
每个子 agent 拥有独立的上下文窗口，通过 JSONL mailbox 协议协调。

Usage:
    python s16_agent_teams/code.py
"""

import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

TEAMS_DIR = Path(".hermes") / "teams"


# ── Mailbox Protocol (JSONL) ───────────────────────────

@dataclass
class TeamMessage:
    """团队邮箱消息 — 固定 request-reply 格式"""
    msg_id: str
    from_agent: str          # 发送者 agent ID
    to_agent: str             # 接收者 agent ID ("broadcast" = 全员)
    msg_type: str             # request | reply | announce | task_claim
    subject: str
    body: str
    timestamp: str = ""
    reply_to: str = ""        # 回复哪个消息


# ── Agent Mailbox ──────────────────────────────────────

class AgentMailbox:
    """每个 agent 的独立邮箱"""

    def __init__(self, agent_id: str, mailbox_dir: Path = TEAMS_DIR):
        self.agent_id = agent_id
        self.mailbox_dir = mailbox_dir / agent_id
        self.mailbox_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_file = self.mailbox_dir / "inbox.jsonl"
        self.outbox_file = self.mailbox_dir / "outbox.jsonl"

    def send(self, to: str, msg_type: str, subject: str, body: str,
             reply_to: str = "") -> TeamMessage:
        """发送消息"""
        msg = TeamMessage(
            msg_id=str(uuid.uuid4())[:8],
            from_agent=self.agent_id,
            to_agent=to,
            msg_type=msg_type,
            subject=subject,
            body=body,
            timestamp=datetime.now().isoformat(),
            reply_to=reply_to,
        )
        # 写入自己和目标的邮箱
        for mailbox_dir in [self.mailbox_dir, TEAMS_DIR / to]:
            if mailbox_dir.exists():
                outbox = mailbox_dir / "inbox.jsonl"
                with open(outbox, "a", encoding="utf-8") as f:
                    f.write(json.dumps(msg.__dict__, ensure_ascii=False) + "\n")
        print(f"  [Mailbox] {self.agent_id} → {to}: [{msg_type}] {subject}")
        return msg

    def poll(self) -> list[TeamMessage]:
        """拉取新消息"""
        if not self.inbox_file.exists():
            return []
        messages = []
        with open(self.inbox_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(TeamMessage(**json.loads(line)))
                    except (json.JSONDecodeError, TypeError):
                        pass
        # 清空已读
        self.inbox_file.write_text("")
        return messages


# ── Team Member ────────────────────────────────────────

class TeamMember:
    """团队成员 — 有独立上下文和邮箱的 agent"""

    def __init__(self, agent_id: str, role: str, skills: list[str] = None):
        self.agent_id = agent_id
        self.role = role                      # leader | worker | reviewer
        self.skills = skills or []
        self.mailbox = AgentMailbox(agent_id)
        self.messages: list = []              # 独立的消息列表（上下文隔离）
        self.busy = False

    def think(self, task: str) -> str:
        """独立推理 — 拥有自己的上下文窗口"""
        self.messages.append({"role": "user", "content": task})
        try:
            response = CLIENT.messages.create(
                model=MODEL,
                system=f"You are agent '{self.agent_id}' (role: {self.role}). "
                       f"Skills: {', '.join(self.skills)}. "
                       "Be concise and focused.",
                messages=self.messages,
                max_tokens=1000,
            )
            text = response.content[0].get("text", "") if response.content else ""
            self.messages.append({"role": "assistant", "content": text})
            return text
        except Exception as e:
            return f"Error: {e}"

    def claim_task(self, task_board: "TaskBoard") -> str:
        """从任务板认领一个任务"""
        available = task_board.get_available(self.agent_id)
        if not available:
            return ""
        task = available[0]
        task_board.claim(task["id"], self.agent_id)
        print(f"  [Team] {self.agent_id} claimed: {task['title']}")
        return task["id"]


# ── Task Board ─────────────────────────────────────────

@dataclass
class TaskItem:
    task_id: str
    title: str
    description: str
    status: str = "pending"     # pending | claimed | in_progress | done
    assigned_to: str = ""
    blocked_by: list = field(default_factory=list)
    created_by: str = ""


class TaskBoard:
    """团队共享任务板"""

    def __init__(self, board_dir: Path = TEAMS_DIR / "boards"):
        self.board_dir = board_dir
        self.board_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: dict[str, TaskItem] = {}

    def add(self, title: str, description: str, created_by: str = "leader",
            blocked_by: list = None) -> TaskItem:
        task = TaskItem(
            task_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            created_by=created_by,
            blocked_by=blocked_by or [],
        )
        self.tasks[task.task_id] = task
        return task

    def get_available(self, agent_id: str) -> list[TaskItem]:
        """获取当前 agent 可认领的任务"""
        return [
            t for t in self.tasks.values()
            if t.status in ("pending",)
            and not t.blocked_by  # 没有被阻塞
            and t.assigned_to == ""
        ]

    def claim(self, task_id: str, agent_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = "claimed"
            self.tasks[task_id].assigned_to = agent_id

    def complete(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = "done"

    def status_report(self) -> str:
        lines = []
        for t in self.tasks.values():
            emoji = {"pending": "⬜", "claimed": "🔵", "in_progress": "🟡", "done": "✅"}
            assignee = f" ({t.assigned_to})" if t.assigned_to else ""
            lines.append(f"  {emoji.get(t.status, '❓')} [{t.task_id}] {t.title}{assignee}")
        return "\n".join(lines)


# ── Team Orchestrator ──────────────────────────────────

class TeamOrchestrator:
    """团队协调器 — 分派任务、收集结果"""

    def __init__(self):
        self.leader = TeamMember("leader", "leader", ["planning", "delegation"])
        self.board = TaskBoard()

    def create_worker(self, name: str, skills: list[str]) -> TeamMember:
        return TeamMember(name, "worker", skills)

    def delegate(self, worker: TeamMember, task: str) -> str:
        """委派任务给 worker — 通过 mailbox 发送"""
        task_id = str(uuid.uuid4())[:8]
        self.board.add(task, f"Delegated to {worker.agent_id}", created_by="leader")
        self.board.claim(task_id, worker.agent_id)

        # 通过 mailbox 通知 worker
        self.leader.mailbox.send(
            worker.agent_id,
            "request",
            f"New task: {task[:50]}",
            f"Task ID: {task_id}\nDescription: {task}",
        )
        return task_id

    def collect_results(self, worker: TeamMember) -> str:
        """收集 worker 的回复"""
        replies = worker.mailbox.poll()
        if not replies:
            return ""
        return "\n".join(f"[{r.from_agent}] {r.body[:200]}" for r in replies)


# ── Main ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("s16: Agent Teams — 多 agent 协作系统")
    print("=" * 60)
    print()
    print("团队模式:")
    print("  1. Leader 分解任务 → 写入 TaskBoard")
    print("  2. Worker 自主认领 → 独立上下文推理")
    print("  3. 通过 Mailbox (JSONL) 异步通信")
    print("  4. Leader 收集结果 → 汇总输出")
    print()

    # Demo: 模拟一个团队任务
    team = TeamOrchestrator()

    # 创建 worker
    researcher = team.create_worker("researcher", ["web_search", "analysis"])
    coder = team.create_worker("coder", ["bash", "write_file"])
    reviewer = team.create_worker("reviewer", ["code_review"])

    # Leader 分解任务
    print("Leader 分解任务:")
    team.board.add("Research API options", "Find the best REST API framework for Python")
    team.board.add("Implement endpoint", "Write the /users endpoint", blocked_by=["task_1"])
    team.board.add("Review code", "Code review for the implementation", blocked_by=["task_2"])
    print(team.board.status_report())

    # Worker 自主认领
    print("\nWorker 自主认领:")
    researcher.claim_task(team.board)
    print(team.board.status_report())

    # 完成任务
    team.board.complete(list(team.board.tasks.keys())[0])
    print("\n任务完成:")
    print(team.board.status_report())

    # Mailbox 通信演示
    print("\nMailbox 通信:")
    team.leader.mailbox.send("coder", "request", "Implement /users", "Please implement the users CRUD endpoint")
    team.leader.mailbox.send("reviewer", "request", "Review needed", "Please review the implementation")
    msgs = team.leader.mailbox.poll()
    print(f"  Leader inbox: {len(msgs)} new messages")

    print("\n  ✅ Agent Teams 演示完成")
    print("  关键设计:")
    print("  - 每个 agent 有独立上下文（消息列表隔离）")
    print("  - 通过 JSONL mailbox 异步通信")
    print("  - TaskBoard 支持依赖关系 (blocked_by)")
    print("  - Worker 自主认领, 非 Leader 逐一分派")


if __name__ == "__main__":
    main()
