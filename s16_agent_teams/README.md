# s16: Agent Teams — 一个搞不定，组队来

[中文](README.md) · [English](README.en.md)

s01 → ... → s15 → `s16` → [s17](../s17_mcp_plugin/) → s18
> *"大任务拆小，每个子 agent 独立上下文"* — 子 agent 派生 + 异步邮箱通信 + 任务板自组织。
>
> **Hermes 特性**: Agent Teams — 多 agent 协作，上下文隔离。

---

## 问题

单个 agent 处理大型任务时有两个瓶颈：
1. **上下文窗口** — 所有子任务挤在一个消息列表里，token 很快耗尽
2. **注意力分散** — 一个 agent 同时思考多个子问题，质量下降

**需要多 agent 协作——每个 agent 专注一件事，独立上下文，异步协调。**

---

## 解决方案

三个核心机制：子 agent 派生 + JSONL 邮箱 + 任务板自组织。

### 1. 子 Agent 派生 (Fresh Context)

```python
# 主 agent spawn 一个专注 review 的子 agent
reviewer = TeamMember("reviewer", "worker", ["code_review"])
# reviewer 有自己独立的 messages 列表——上下文完全隔离
result = reviewer.think("Review this PR for security issues")
```

### 2. JSONL Mailbox 协议

每个 agent 有一个 inbox.jsonl，通信格式固定：

```jsonl
{"msg_id": "a1b2", "from_agent": "leader", "to_agent": "coder",
 "msg_type": "request", "subject": "Implement /users",
 "body": "Please implement CRUD...", "timestamp": "..."}
```

### 3. 任务板 (Task Board)

```
[⬜] task_1 Research API options
[⬜] task_2 Implement endpoint  (blocked_by: task_1)
[⬜] task_3 Review code         (blocked_by: task_2)

→ Worker 看到 task_1 没阻塞 → 自动认领
→ task_2 被 task_1 阻塞 → 等待
→ task_1 完成 → task_2 解锁 → 下一个 worker 认领
```

### 团队拓扑

```
              ┌──────────┐
              │  Leader  │ ← 分解任务、汇总结果
              └────┬─────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
      ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│Researcher│ │  Coder   │ │ Reviewer │
│(独立ctx) │ │(独立ctx) │ │(独立ctx) │
└──────────┘ └──────────┘ └──────────┘
      │            │            │
      └────────────┼────────────┘
                   │
           ┌───────▼───────┐
           │   TaskBoard   │ ← 共享任务状态
           └───────────────┘
```

---

## 试一下

```sh
python s16_agent_teams/code.py
```

观察：Leader 分解任务 → Worker 认领 → 完成 → 依赖解锁 → 下一 worker 接手。

---

## 接下来

Agent 的能力受限于内置工具。怎么接入外部能力？MCP 协议——把外部工具接进同一个工具池。

s17 MCP Plugin → 多传输 + 通道路由 + 工具池组装。

<!-- translation-sync: zh@v1 -->
