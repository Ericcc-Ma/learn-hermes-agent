# s18: Full Hermes — 完整的自进化 Agent

[中文](README.md) · [English](README.en.md)

s01 → s02 → ... → s17 → `s18`
> *"18 个机制，一个完整的 Hermes"* — 从 agent loop 到多平台 gateway，所有机制回到一个完整实现。
>
> **Hermes 全特性**: 全部 18 章覆盖了 Hermes Agent 的核心架构。

---

## 完整特性清单

| 章节 | 特性 | 核心文件 |
|------|------|---------|
| s01 | Agent Loop + Memory | `run_agent.py`, `agent/conversation_loop.py` |
| s02 | Background Memory Review | `agent/background_review.py` |
| s03 | Background Skill Review | `agent/background_review.py` |
| s04 | Memory System (FTS5 + Pluggable) | `agent/memory_manager.py`, `agent/memory_provider.py` |
| s05 | Skill Lifecycle | `tools/skill_usage.py` |
| s06 | Skill Creation Safety | `agent/background_review.py` (forbidden patterns) |
| s07 | Curator: Auto Transitions | `agent/curator.py:268-323` |
| s08 | Curator: LLM Merge | `agent/curator.py:330-491` |
| s09 | Context Management | `agent/conversation_compression.py`, `agent/context_compressor.py` |
| s10 | Insights Engine | `agent/insights.py` |
| s11 | Error Recovery | `agent/conversation_loop.py` (recovery paths) |
| s12 | Complete Self-Evolving Agent | 六层架构集成 |
| s13 | Cron Scheduler | `cron/scheduler.py`, `cron/jobs.py` |
| s14 | Gateway | `gateway/run.py`, `gateway/session.py` |
| s15 | Multi-Profile System | `hermes_cli/profiles.py` |
| s16 | Agent Teams | `delegate_task` + leaf/orchestrator roles |
| s17 | MCP Plugin | `tools/mcp_tool.py`, MCP transports |
| s18 | Full Hermes | 全部集成 |

---

## 完整架构图

![Full Hermes](images/full-hermes.svg)

```
                        ┌──────────────┐
                        │   Users      │
                        │ CLI Telegram │
                        │ Discord Slack│
                        └──────┬───────┘
                               │
                    ┌──────────▼──────────┐
                    │     GATEWAY (s14)    │
                    │  Platform Adapters   │
                    │  Session Management  │
                    │  Delivery Router     │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │  Profile A   │   │  Profile B   │   │  Cron Worker │
  │  (work)      │   │  (personal)  │   │  (s15)       │
  │  s15         │   │              │   │              │
  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
         │                  │                   │
         └──────────────────┼───────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │       AGENT LOOP (s01)     │
              │    while True:             │
              │      response = LLM(...)   │
              │      execute tools         │
              └─────────────┬─────────────┘
                            │
    ┌───────────────────────┼───────────────────────┐
    │                       │                       │
    ▼                       ▼                       ▼
┌────────┐          ┌──────────────┐        ┌──────────────┐
│PRE-TURN│          │   MID-TURN   │        │  POST-TURN   │
├────────┤          ├──────────────┤        ├──────────────┤
│Memory  │          │Context Comp. │        │Background    │
│Prefetch│          │(s09)         │        │Review (s02,3)│
│(s04)   │          │Error Recovery│        │Memory Extract│
│Skills  │          │(s11)         │        │Skill Detect  │
│(s05)   │          │MCP Tools     │        │(s06)         │
│        │          │(s17)         │        │              │
└────────┘          └──────────────┘        └──────────────┘
                            │
    ┌───────────────────────┼───────────────────────┐
    │                       │                       │
    ▼                       ▼                       ▼
┌────────────┐     ┌──────────────┐      ┌──────────────────┐
│CURATOR     │     │ INSIGHTS     │      │  CRON TICKER     │
│(s07, s08)  │     │ (s10)        │      │  (s13)           │
│Idle trigger│     │ Token/Cost   │      │  Every 60s tick  │
│Auto trans. │     │ Tool Stats   │      │  → run_job()     │
│LLM merge   │     │ Trends       │      │  → delivery      │
└────────────┘     └──────────────┘      └──────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │     AGENT TEAMS (s16)     │
              │   delegate_task tool      │
              │   leaf/orchestrator roles │
              │   synchronous summaries   │
              └───────────────────────────┘
```

---

## 试一下

```sh
python s18_full_hermes/full_hermes.py
```

这个文件整合了前面 17 章所有机制的关键代码片段，展示了完整架构。

输入 `/map` 查看所有特性清单，`/help` 查看所有命令。

---

## 全部 18 章回顾

| # | 主题 | 格言 |
|----|------|------|
| s01 | Agent Loop + Memory | 一个循环 + 一个记忆文件 |
| s02 | Background Memory Review | 每次对话结束，问自己"学到了什么" |
| s03 | Background Skill Review | 好方案不只用一次，沉淀为技能 |
| s04 | Memory System | 记忆不该只有一个文件 |
| s05 | Skill Lifecycle | 技能有生老病死 |
| s06 | Skill Creation | 什么该学、什么不该学——有规则 |
| s07 | Curator State | 30 天不用就标记，规则说了算 |
| s08 | Curator LLM | 技能太多会乱，定期合并整理 |
| s09 | Context Management | 上下文满了就压，重要的事留在外面 |
| s10 | Insights | 你不知道用了多少 token？那怎么优化 |
| s11 | Error Recovery | 出错了不是终点，是学习的起点 |
| s12 | Complete Self-Evolving | 六层归位，一个会自己进化的 agent |
| s13 | Cron Scheduler | 定好时间，agent 自己醒来干活 |
| s14 | Gateway | 一个 gateway，连接所有平台 |
| s15 | Profiles | 一套 Hermes，多个人设 |
| s16 | Agent Teams | 一个搞不定，组队来 |
| s17 | MCP Plugin | 能力不够？接上 MCP |
| s18 | Full Hermes | 全部机制，一个完整 agent |

---

**Agency 来自模型。自进化来自 Harness。Build the harness that learns.**

<details>
<summary>深入 Hermes 源码</summary>

完整 Hermes 系统核心文件索引:

| 层级 | 核心文件 |
|------|---------|
| 入口 | `cli.py`, `hermes_cli/main.py` |
| Gateway | `gateway/run.py`, `gateway/session.py` |
| Agent Loop | `run_agent.py`, `agent/conversation_loop.py` |
| 记忆系统 | `agent/memory_manager.py`, `agent/memory_provider.py` |
| 技能系统 | `tools/skill_usage.py`, `tools/skill_manage.py` |
| Curator | `agent/curator.py` (scheduling + Phase 1 + Phase 2) |
| Cron | `cron/scheduler.py`, `cron/jobs.py` |
| MCP | `tools/mcp_tool.py`, `tools/mcp_oauth_manager.py` |
| Profiles | `hermes_cli/profiles.py`, `hermes_cli/config.py` |
| 上下文 | `agent/conversation_compression.py`, `agent/context_compressor.py` |
| 错误恢复 | `agent/conversation_loop.py` (recovery paths) |

</details>

<!-- translation-sync: zh@v1 -->
