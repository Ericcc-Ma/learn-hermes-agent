# s21: Worktree Isolation — 各干各的目录，互不干扰

[中文](README.md)

s01 → ... → s20 → `s21` → [s22](../s22_planning/) → s23 → s24
> *"各干各的目录，互不干扰"* — git worktree 并行隔离，每个任务独立文件系统空间。
>
> **Harness 基础**: Worktree — 多任务并行时的文件隔离方案。

---

## 问题

多个子 agent 并行工作时，如果共享同一个工作目录——文件修改会互相冲突。A agent 正在写 `auth.py`，B agent 也在改同一个文件。

**需要文件系统级别的隔离。**

---

## 解决方案

Git worktree — 零拷贝创建独立工作目录，共享 `.git` 对象数据库：

```
repo/
  .git/              ← 共享
  worktree_main/     ← 主工作目录
hermes/worktrees/
  wt_a1b2/           ← agent A 的隔离目录
  wt_c3d4/           ← agent B 的隔离目录
```

每个 worktree 有自己的分支，修改互不影响。完成后的改动可以 merge 回去也可以丢弃。

---

## 试一下

```sh
python s21_worktree/code.py
```

<details>
<summary>深入 Hermes 源码</summary>

生产版 worktree 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/conversation_loop.py` | EnterWorktree/ExitWorktree 工具实现 |
| `agent/agent_runtime_helpers.py` | worktree 生命周期管理 |

教学版简化了什么:
- 生产版 worktree 基于 git worktree add 创建隔离分支
- 生产版支持 worktree.baseRef 配置 (fresh=从远程拉, head=从本地)
- 生产版 agent 可以在 worktree 中自由切换，通过 EnterWorktree 工具
- 生产版 worktree 清理支持 keep/remove 两种模式

</details>

<!-- translation-sync: zh@v1 -->
