"""
s21: Worktree Isolation — 各干各的目录，互不干扰

Hermes 的 git worktree 并行隔离: 每个子任务拥有独立的文件系统空间。
通过 git worktree 创建临时分支工作目录，任务间文件修改互不影响。

Usage:
    python s21_worktree/code.py
"""

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()


# ── Worktree Record ────────────────────────────────────

@dataclass
class WorktreeRecord:
    """一个 git worktree 的记录"""
    worktree_id: str
    task_id: str              # 绑定的任务 ID
    branch: str               # worktree 对应的分支
    path: str                 # 文件系统路径
    base_ref: str = "main"    # 基于哪个分支创建
    created_at: str = ""
    status: str = "active"    # active | merged | removed
    created_by: str = ""


# ── Worktree Manager ───────────────────────────────────

class WorktreeManager:
    """Git Worktree 管理器 — 创建隔离的工作目录"""

    def __init__(self, worktree_base: Path = None):
        self.worktree_base = worktree_base or Path(".hermes") / "worktrees"
        self.worktree_base.mkdir(parents=True, exist_ok=True)
        self._worktrees: dict[str, WorktreeRecord] = {}
        self._repo_root = self._find_repo_root()

    def _find_repo_root(self) -> Optional[Path]:
        """找到 git 仓库根目录"""
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=10,
                cwd=os.getcwd(),
            )
            if r.returncode == 0:
                return Path(r.stdout.strip())
        except Exception:
            pass
        return None

    def create(self, task_id: str, base_ref: str = "main") -> Optional[WorktreeRecord]:
        """为任务创建隔离的 git worktree"""
        if not self._repo_root:
            print("  [Worktree] Not in a git repository — using temp directory")
            return self._create_temp_worktree(task_id)

        worktree_id = str(uuid.uuid4())[:8]
        branch = f"hermes/task-{task_id}-{worktree_id}"
        worktree_path = self.worktree_base / worktree_id

        try:
            # 确保 base_ref 是最新的
            subprocess.run(
                ["git", "fetch", "origin", base_ref],
                capture_output=True, text=True, timeout=30,
                cwd=str(self._repo_root),
            )

            # 创建 worktree
            r = subprocess.run(
                ["git", "worktree", "add", str(worktree_path), f"origin/{base_ref}"],
                capture_output=True, text=True, timeout=30,
                cwd=str(self._repo_root),
            )
            if r.returncode != 0:
                # Fallback: create from local branch
                r = subprocess.run(
                    ["git", "worktree", "add", str(worktree_path), base_ref],
                    capture_output=True, text=True, timeout=30,
                    cwd=str(self._repo_root),
                )

            if r.returncode == 0:
                # 在新 worktree 中创建任务分支
                subprocess.run(
                    ["git", "checkout", "-b", branch],
                    capture_output=True, text=True, timeout=10,
                    cwd=str(worktree_path),
                )

                record = WorktreeRecord(
                    worktree_id=worktree_id,
                    task_id=task_id,
                    branch=branch,
                    path=str(worktree_path),
                    base_ref=base_ref,
                    created_at=datetime.now().isoformat(),
                )
                self._worktrees[worktree_id] = record
                print(f"  [Worktree] created {worktree_id} → {worktree_path}")
                return record
            else:
                print(f"  [Worktree] git error: {r.stderr}")
                return self._create_temp_worktree(task_id)

        except Exception as e:
            print(f"  [Worktree] error: {e}")
            return self._create_temp_worktree(task_id)

    def _create_temp_worktree(self, task_id: str) -> WorktreeRecord:
        """Fallback: 创建临时目录模拟 worktree"""
        worktree_id = str(uuid.uuid4())[:8]
        temp_path = self.worktree_base / worktree_id
        temp_path.mkdir(parents=True, exist_ok=True)

        record = WorktreeRecord(
            worktree_id=worktree_id,
            task_id=task_id,
            branch=f"temp-{worktree_id}",
            path=str(temp_path),
            created_at=datetime.now().isoformat(),
        )
        self._worktrees[worktree_id] = record
        print(f"  [Worktree] created temp worktree {worktree_id} → {temp_path}")
        return record

    def cleanup(self, worktree_id: str, keep_changes: bool = False):
        """清理 worktree"""
        record = self._worktrees.get(worktree_id)
        if not record:
            return

        wt_path = Path(record.path)
        if wt_path.exists():
            if self._repo_root and not record.branch.startswith("temp-"):
                # 真正的 git worktree — 用 git 命令清理
                try:
                    subprocess.run(
                        ["git", "worktree", "remove", str(wt_path), "--force"],
                        capture_output=True, text=True, timeout=10,
                        cwd=str(self._repo_root),
                    )
                    subprocess.run(
                        ["git", "branch", "-D", record.branch],
                        capture_output=True, text=True, timeout=10,
                        cwd=str(self._repo_root),
                    )
                except Exception:
                    pass
            if not keep_changes and wt_path.exists():
                shutil.rmtree(str(wt_path), ignore_errors=True)

        record.status = "removed"
        print(f"  [Worktree] cleaned up {worktree_id}")

    def execute_in_worktree(self, worktree_id: str, command: str) -> str:
        """在 worktree 中执行命令"""
        record = self._worktrees.get(worktree_id)
        if not record:
            return f"Worktree not found: {worktree_id}"

        wt_path = Path(record.path)
        if not wt_path.exists():
            return f"Worktree path does not exist: {wt_path}"

        try:
            r = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=str(wt_path),
            )
            return r.stdout or "(no output)"
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error: {e}"

    def list_worktrees(self) -> list[WorktreeRecord]:
        return list(self._worktrees.values())


# ── Task → Worktree Binding ────────────────────────────

class TaskIsolation:
    """任务-目录绑定: 每个任务绑定一个 worktree，通过 task_id 关联"""

    def __init__(self, wt_manager: WorktreeManager):
        self.wt_manager = wt_manager
        self._bindings: dict[str, str] = {}  # task_id → worktree_id

    def assign(self, task_id: str) -> Optional[WorktreeRecord]:
        """为任务分配 worktree"""
        worktree = self.wt_manager.create(task_id)
        if worktree:
            self._bindings[task_id] = worktree.worktree_id
        return worktree

    def get_worktree(self, task_id: str) -> Optional[WorktreeRecord]:
        """获取任务绑定的 worktree"""
        wt_id = self._bindings.get(task_id)
        if wt_id:
            return self.wt_manager._worktrees.get(wt_id)
        return None

    def release(self, task_id: str):
        """释放任务的 worktree"""
        wt_id = self._bindings.pop(task_id, None)
        if wt_id:
            self.wt_manager.cleanup(wt_id)


# ── Main ──────────────────────────────────────────────

def main():
    manager = WorktreeManager()
    isolation = TaskIsolation(manager)

    in_git = manager._repo_root is not None
    print("=" * 60)
    print("s21: Worktree Isolation — 各干各的目录，互不干扰")
    print("=" * 60)
    print(f"Git repo: {manager._repo_root or '❌ (using temp dirs)'}")
    print()

    # 演示: 为两个任务创建隔离目录
    print("创建任务隔离目录:")
    wt1 = isolation.assign("task_bugfix_123")
    wt2 = isolation.assign("task_feature_456")

    if wt1 and wt2:
        # 在各自的 worktree 中创建文件
        manager.execute_in_worktree(wt1.worktree_id, "echo 'bugfix work' > bugfix.txt")
        manager.execute_in_worktree(wt2.worktree_id, "echo 'feature work' > feature.txt")

        # 验证隔离
        print(f"\n检查 task_bugfix_123 目录:")
        result = manager.execute_in_worktree(wt1.worktree_id, "ls -la" if os.name != "nt" else "dir")
        print(f"  {result.strip()}")

        print(f"\n检查 task_feature_456 目录:")
        result = manager.execute_in_worktree(wt2.worktree_id, "ls -la" if os.name != "nt" else "dir")
        print(f"  {result.strip()}")

    # 清理
    if wt1:
        isolation.release("task_bugfix_123")
    if wt2:
        isolation.release("task_feature_456")

    print(f"\n剩余 worktree: {len(manager.list_worktrees())}")
    print()
    print("设计原则:")
    print("  1. 每个任务绑定独立 worktree — 文件修改互不干扰")
    print("  2. 基于 git worktree — 零拷贝创建，共享 .git 对象")
    print("  3. temp dir fallback — 非 git 仓库也能用")
    print("  4. cleanup 支持保留/丢弃两种模式")


if __name__ == "__main__":
    main()
