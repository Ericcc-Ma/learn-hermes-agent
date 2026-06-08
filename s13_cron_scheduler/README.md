# s13: Cron Scheduler — 让 agent 在指定时间自动醒来

[中文](README.md) · [English](README.en.md)

s01 → ... → s12 → `s13` → [s14](../s14_gateway/) → ... → s18
> *"定好时间，agent 自己醒来干活"* — JSON 文件落盘 + gateway ticker 调度 + delivery 分发。
>
> **Hermes 特性**: 定时任务系统 — 让 agent 从"踹一下动一下"变成"自己按时醒来"。

---

## 问题

s01-s12 的 agent 是被动的——用户发消息，agent 响应。关了 session 就什么都没了。

但很多场景需要主动触发：每天早上 9 点汇总昨日工作、每小时检查一次服务状态、每周一生成周报。

**Agent 需要定时任务——到时间自己醒来执行，不需要人推。**

---

## 解决方案

三层架构：

```
┌──────────────────────────────────────────────────┐
│              创建层 (Session)                      │
│  Agent 在对话中调用 cron_create 工具               │
│  → 写入 ~/.hermes/cron/jobs.json                  │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│              调度层 (Gateway Ticker)               │
│  后台线程每 60s tick() 一次                        │
│  → 检查 jobs.json 里有没有到期任务                 │
│  → 有就执行，没有就跳过                            │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│              执行层 (run_job)                      │
│  → fork 独立 agent 执行任务                        │
│  → 结果保存到 output/ 目录                        │
│  → 通过 gateway delivery 推送结果                  │
└──────────────────────────────────────────────────┘
```

---

## 核心机制

### 1. 任务持久化

任务存储在 `~/.hermes/cron/jobs.json`，JSON 格式落盘：

```json
{
  "jobs": [{
    "id": "a1b2c3d4",
    "name": "Daily Summary",
    "prompt": "Summarize today's activity and send to channel",
    "schedule": "0 9 * * *",
    "recurring": true,
    "enabled": true,
    "last_run_at": "2026-06-07T09:00:00",
    "next_run_at": "2026-06-08T09:00:00",
    "run_count": 5
  }],
  "version": 1
}
```

**关闭 session、重启电脑都不影响——任务是落盘的。**

### 2. Gateway Ticker

Gateway 启动时自动拉起一个 daemon 线程：

```python
# gateway/run.py:19756-19764
cron_thread = threading.Thread(
    target=_start_cron_ticker,
    args=(cron_stop,),
    daemon=True,
    name="cron-ticker",
)
cron_thread.start()
```

每 60 秒执行一次 `tick()`：
- 读 `jobs.json`
- 计算每个任务的下次触发时间
- 到期的任务交给 `run_job()`

### 3. 文件锁防并发

```python
# cron/scheduler.py:1982-1992
lock_fd = open(lock_file, "w")
fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # 非阻塞排他锁
# 如果另一个 tick 已经拿着锁，这个 tick 直接跳过
```

### 4. 一次性 vs 重复任务

| 类型 | `recurring` | 执行后 |
|------|------------|--------|
| 重复任务 | `true` | 自动计算下一次触发时间 |
| 一次性任务 | `false` | `enabled = false`，不再触发 |

---

## 试一下

```sh
python s13_cron_scheduler/code.py
```

1. `/jobs` 查看已有任务
2. `/tick` 手动触发一次
3. 输入 `schedule a task: 0 9 * * * | check deployment status`
4. `/ticker` 启动后台 ticker 观察自动执行

---

## 接下来

Cron 让 agent 能定时醒来。但结果怎么推送出去？需要 gateway——多平台消息网关。

s14 Gateway → 多平台消息路由 + delivery 分发 + session 管理。

<details>
<summary>深入 Hermes 源码</summary>

生产版 cron 系统位于以下源文件:

| 文件 | 职责 |
|------|------|
| `cron/scheduler.py` | tick() 调度器、run_job() 执行器、文件锁防并发 |
| `cron/jobs.py` | jobs.json 读写、任务 CRUD、原子替换 |
| `gateway/run.py`(:19756) | gateway 启动时自动拉起 cron ticker 线程 |
| `hermes_cli/cron.py` | CLI 命令: list/create/edit/pause/run/remove/status/tick |

教学版简化了什么:
- 生产版 gateway ticker 是 daemon 线程每 60s 触发，教学版用 threading.Event 模拟
- 生产版用 fcntl/msvcrt 文件锁防并发 tick，教学版省略
- 生产版支持 no_agent 模式 (纯脚本定时执行，不走 LLM)
- 生产版的 delivery 路由支持 E2EE 加密适配器

</details>

<!-- translation-sync: zh@v1 -->
