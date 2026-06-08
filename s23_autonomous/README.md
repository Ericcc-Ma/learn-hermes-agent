# s23: Kanban Dispatcher — 中心调度 + Worker 执行

[中文](README.md) · [English](README.en.md)

![Kanban Dispatcher](images/autonomous-agents.svg)

s01 → ... → s22 → `s23` → [s24](../s24_system_prompt/)
> *"不是 worker 自己扫板，是 Dispatcher 中心分配"* — 每 60s tick + claim TTL + 失败保护。
>
> **Hermes 特性**: Kanban Dispatcher — 持久化的多 agent 工作队列。

---

## 问题

s16 的 delegate_task 是同步的、不持久的——父 agent 关了，子 agent 也没了。需要一种**异步、持久化**的多 agent 协作方式。

---

## 解决方案

**Kanban Dispatcher** — 事件循环驱动的工作队列：

```
         Kanban Board (SQLite)
        ┌──────────────────────┐
        │  todo → ready → running → done
        │              ↓
        │          blocked (failure_limit)
        └──────────────────────┘
                ▲       │
        reclaim │       │ claim + spawn
                │       ▼
        ┌──────────────────────────────┐
        │  Dispatcher (dispatch_once)   │
        │  - 每 60 秒一次 tick            │
        │  - 回收 stale/crashed 任务      │
        │  - promote ready 任务           │
        │  - claim + spawn worker        │
        └──────────┬───────────────────┘
                   │ _default_spawn()
                   ▼
        ┌──────────────────────────┐
        │  Worker Process           │
        │  hermes -p <profile>      │
        │  chat -q "work kanban    │
        │  task <id>"              │
        └──────────────────────────┘
```

### 6 步调度循环

每个 tick (60s) 执行:

1. **Reclaim** — 回收超时 TTL 的 running 任务
2. **Stale 检测** — 回收无心跳的 running 任务
3. **Crash 检测** — 检测 host-local PID 已死亡的 worker
4. **Promote** — 满足依赖的 todo → ready
5. **Claim + Spawn** — 原子认领 ready 任务, fork 子进程
6. **失败保护** — 连续 `failure_limit`（默认 2）次失败后自动 block

### 三种模式对比

| | delegate_task (s16) | Cron (s13) | Kanban (s23) |
|---|---|---|---|
| 谁触发 | LLM 自主决策 | 定时调度 | Dispatcher 事件循环 |
| 生命周期 | 同步，跟随父 turn | 异步持久化 job | 异步持久化 task |
| 持久性 | 不持久 | jobs.json | SQLite board |
| 嵌套 | max_spawn_depth | 禁用 delegate_task | kanban_create 子任务 |

---

## 试一下

```sh
python s23_autonomous/autonomous.py
```

---

<details>
<summary>深入 Hermes 源码</summary>

生产版 Kanban 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `hermes_cli/kanban_db.py` | Board CRUD、dispatch_once、claim/reclaim 逻辑 |
| `hermes_cli/kanban.py` | CLI: kanban create/status/daemon |
| `cli.py`(~15486) | goal_mode worker loop |
| `agent/conversation_loop.py`(~4476) | kanban_complete 信号 |

教学版简化了什么:
- 生产版 Dispatcher 嵌入 gateway 进程（`dispatch_in_gateway: true`）
- 生产版 Worker 是通过 `subprocess.Popen` 启动的真实独立进程
- 生产版 claim 使用 SQLite 行锁实现原子操作
- 生产版支持 goal_mode（Ralph 式 goal judge loop）和 classic 两种 worker 模式
- 生产版有 Board/Tenant/Profile 三层隔离

</details>

<!-- translation-sync: zh@v1 -->
