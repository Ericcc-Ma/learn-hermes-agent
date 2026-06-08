# s16: Agent Teams — delegate_task + 角色系统

[中文](README.md) · [English](README.en.md)

![Agent Teams](images/agent-teams.svg)

s01 → ... → s15 → `s16` → [s17](../s17_mcp_plugin/) → ... → s24
> *"一个搞不定，delegate 出去"* — LLM 自主调用 delegate_task 工具 spawn 子 agent，支持 leaf/orchestrator 角色。
>
> **Hermes 特性**: Agent Teams — 由 LLM 驱动的即时任务委托。

---

## 问题

单个 agent 处理复杂任务时上下文膨胀。需要能把子任务分派出去，每个子 agent 有独立上下文。

---

## 解决方案

**delegate_task 工具** — LLM 像调用其他 tool 一样调用它，自主决定何时、如何 spawn 子 agent。

### 两种模式

| 模式 | 参数 | 行为 |
|------|------|------|
| **Single** | `goal` + `context` + `role` | 启动 1 个子 agent |
| **Batch** | `tasks: [{goal, context, role}, ...]` | 并发启动 N 个（受 `max_concurrent_children` 限制） |

### 角色系统

```
        Parent (depth=0)
              │ delegate_task()
     ┌────────┼────────┐
     ▼        ▼        ▼
  leaf    leaf    orchestrator (depth=1)
 (默认)              │ delegate_task()
                     ▼
                   leaf (depth=2, max)
```

- **leaf**（默认）: 纯 worker，被剥夺 delegate_task、clarify、memory 等工具
- **orchestrator**: 保留 delegate_task，可继续 spawn。受 `max_spawn_depth`（默认 1）限制

### 关键配置

| 配置 | 默认 | 说明 |
|------|------|------|
| `max_concurrent_children` | 3 | 单次最多并行数 |
| `max_spawn_depth` | 1 | 最大嵌套深度 |
| `max_iterations` | 90 | 子 agent 最大迭代数 |

### 同步模型

delegate_task 是**同步**的——父 agent 等待所有子 agent 完成，拿到 summary 后继续。不持久，不跨 turn 存活。

---

## 试一下

```sh
python s16_agent_teams/agent_teams.py
```

---

<details>
<summary>深入 Hermes 源码</summary>

生产版 delegate_task 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `tools/delegate_tool.py` | delegate_task 工具定义、参数校验 |
| `run_agent.py`(~4793) | `_dispatch_delegate_task()` — 分发子 agent |
| `agent/conversation_loop.py` | assistant message 中的 tool_call 检测 |
| `agent/agent_init.py`(~929) | worker 初始化、kanban guidance 注入 |

教学版简化了什么:
- 生产版 delegate_task 是真实 fork 子进程，教学版用函数调用模拟
- 生产版 role 系统会动态剥夺 worker 的特定工具集
- 生产版 `max_spawn_depth` 有硬限制防止无限嵌套
- 生产版子 agent 的 summary 会注入父 agent 的对话上下文

</details>

<!-- translation-sync: zh@v1 -->
