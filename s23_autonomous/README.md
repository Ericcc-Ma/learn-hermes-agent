# s23: Autonomous Agents — 自己看板，有活就认领

[中文](README.md) · [English](README.en.md)

s01 → ... → s22 → `s23` → [s24](../s24_system_prompt/)
> *"队友自己看板，有活就认领"* — 空闲循环 + 技能匹配 + 自主认领，无需 leader 逐个分配。
>
> **Harness 基础**: Autonomous Agents — 自组织的多 agent 系统。

---

## 问题

s16 的 Agent Teams 是 leader 分配任务给 worker。但 leader 本身成为瓶颈——需要知道每个 worker 的能力，还要追踪谁在忙谁空闲。

**能否让 agent 自己认领任务？像蜂群一样自组织。**

---

## 解决方案

![Autonomous Agents](images/autonomous-agents.svg)

三个核心机制：

### 1. 空闲循环 (Idle Loop)

每个 agent 每隔 N 秒扫描一次共享任务板：

```python
while not stopped:
    tasks = board.get_open()     # 扫板
    for task in tasks:
        if can_handle(task):     # 我能做吗？
            claim(task)           # 认领
            execute(task)         # 执行
            break
    sleep(idle_interval)         # 等下一轮
```

### 2. 技能匹配

Agent 根据任务标题/描述判断自己能不能做——不是所有任务都认领。

### 3. 心跳监控

定期记录心跳，检测失联 agent——失联超时自动释放其任务。

---

## 试一下

```sh
python s23_autonomous/code.py
```

<details>
<summary>深入 Hermes 源码</summary>

生产版自主 agent 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/background_review.py` | idle loop 实现、任务认领逻辑 |
| `cron/scheduler.py` | cron ticker 的自主调度 |
| `gateway/run.py` | gateway 心跳 + 空闲检测 |

教学版简化了什么:
- 生产版自主 agent 通过 heartbeat 机制 (每 30s) 检查待处理任务
- 生产版 agent 可以给自己注册 cron 任务: "每 5 分钟检查一次队列"
- 生产版支持 auto_claim: agent 根据 skill 自动匹配并认领任务
- 生产版有心跳监控和超时自动释放任务机制

</details>

<!-- translation-sync: zh@v1 -->
