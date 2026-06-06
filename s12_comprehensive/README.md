# s12: Complete Self-Evolving Agent — 六层归位

[中文](README.md) · [English](README.en.md)

s01 → s02 → ... → s11 → `s12`
> *"六层归位，一个会自己进化的 agent"* — 全部自进化机制集成到一个完整的 agent。
>
> **自进化层**: 全部六层 — 背景审查 + 技能管理 + Curator + 记忆系统 + 上下文管理 + Insights。

---

## 概述

s01 到 s11 逐层构建了 Hermes 的六层自进化架构。本章把它们全部集成到一个完整的、可运行的 agent 中。

---

## 完整架构

```
                    ┌─────────────────────────────────┐
                    │         用户交互                  │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │      Agent Loop (s01)            │
                    │      while True:                 │
                    │        response = LLM(...)       │
                    │        if stop: break            │
                    │        execute tools             │
                    └──────────────┬──────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
  ┌──────────┐            ┌──────────────┐          ┌──────────────┐
  │ 每轮前    │            │   每轮中      │          │  每轮后       │
  └──────────┘            └──────────────┘          └──────────────┘
  │                       │                         │
  │ 记忆预取 (s04)         │ 错误恢复 (s11)           │ 背景审查 (s02,s03)
  │ 技能目录注入 (s05)      │ 上下文压缩 (s09)         │ 记忆提取 (s04)
  │                       │                         │ 技能信号检测 (s06)
  │                       │                         │
  ┌───────────────────────┼─────────────────────────┐
  │                  长期维护 (s07, s08)              │
  │  ┌─────────────┐    ┌─────────────────┐         │
  │  │ Curator P1  │    │  Curator P2     │         │
  │  │ 自动状态转换 │    │  LLM 审查合并    │         │
  │  │ (纯规则)    │    │  (前缀聚类+伞形) │         │
  │  └─────────────┘    └─────────────────┘         │
  └─────────────────────────────────────────────────┘
  │
  │ Insights 引擎 (s10) — 量化分析所有活动
  │
  ▼
  [报告] Token 统计 | 成本分析 | 工具模式 | 自进化效果
```

---

## 六层对应关系

| 层 | 章节 | 机制 | 触发方式 |
|----|------|------|---------|
| 1. 实时学习 | s02, s03 | Background Review (记忆+技能) | Nudge (每 N 轮) |
| 2. 技能管理 | s05, s06 | 生命周期 + 安全护栏 | 事件驱动 |
| 3. 长期维护 | s07, s08 | Curator (规则+LLM) | 空闲触发 (每 7 天) |
| 4. 记忆系统 | s04 | FTS5 + 可插拔提供者 | 每轮注入 |
| 5. 上下文管理 | s09 | 压缩 + 记忆预取保护 | Token 阈值触发 |
| 6. 数据分析 | s10 | Insights 引擎 | 按需查询 |

---

## 完整 Agent Loop

```python
def self_evolving_agent_loop(query, client, state):
    messages = state.messages or []
    messages.append({"role": "user", "content": query})

    while True:
        # ═══ 每轮前 ═══
        # 1. 记忆预取 (s04)
        relevant = memory_manager.prefetch(query)
        # 2. 技能目录注入 (s05)
        skills_catalog = skill_registry.list_active()
        # 3. 组装 system prompt
        system = assemble_system(relevant, skills_catalog, state)

        # ═══ 每轮中 ═══
        try:
            # 4. 上下文压缩检查 (s09)
            if should_compact(messages):
                memory_manager.on_pre_compress()
                messages = compact(messages)
            # 5. API 调用 + 错误恢复 (s11)
            response = safe_api_call(client, state, system, messages)
        except FatalError:
            break

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # ═══ 每轮后 ═══
            # 6. Nudge 检查 → 背景审查 (s02, s03)
            if should_nudge_memory(state):
                background_memory_review(messages)
            if should_nudge_skill(state):
                background_skill_review(messages, loaded_skills)
            # 7. Insights 记录 (s10)
            tracker.end_session()
            return response

        execute_tools(response.content)
        state.turn_count += 1
        state.tool_iterations += 1

    # ═══ 空闲时 ═══
    # 8. Curator 检查 (s07, s08)
    if curator.should_run():
        curator.auto_transitions()  # Phase 1: 纯规则
        curator.llm_review()         # Phase 2: LLM 合并
```

---

## 试一下

```sh
python s12_comprehensive/code.py
```

试试这些 prompt 体验完整的自进化流程：

1. "I prefer tabs over spaces, and I always use pytest with --cov for testing."
2. "In this project, every PR needs: lint → typecheck → test → review."
3. "Stop using camelCase in Python files — I always use snake_case."
4. 多次交互后运行 `/insights` 查看统计
5. 运行 `/curator` 触发技能库整理

观察重点：记忆是否自动保存？技能是否从纠正中自动创建？Curator 是否正确管理技能状态？Insights 是否准确追踪？

---

## 关键设计原则回顾

### 1. 学习而非记忆
用户偏好嵌入技能 body，不仅存记忆。记忆回答"用户是谁"，技能回答"如何为这个用户做这类任务"。

### 2. 类级别伞形结构
目标是少量丰富的类级别技能，而非大量狭窄的一次性条目。

### 3. 保护与安全
- 内置/Hub 技能永不触碰
- 归档可恢复，永不删除
- 禁止捕获环境依赖失败和工具否定性断言

### 4. 后台非侵入
所有学习/维护都在后台执行（或同步但轻量），不破坏 prompt cache。

### 5. 可观测
Curator 生成完整报告，Insights 提供量化分析，所有操作有迹可循。

### 6. 用户控制
Curator 可暂停/恢复/禁用，技能可 pin 豁免，支持 dry-run 预览。

---

## 全部章节回顾

| 章节 | 主题 | 格言 |
|------|------|------|
| s01 | Agent Loop + Memory | 一个循环 + 一个记忆文件 = 最简单的学习 agent |
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
| s12 | Complete Agent | 六层归位，一个会自己进化的 agent |

---

**Agency 来自模型。自进化来自 Harness。每次对话都是学习机会，学到的知识自动沉淀为可复用的技能和记忆。**

**Build the harness that learns. The model will do the rest.**

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 全部六层自进化架构的源码文件，完整索引如下：

| 层 | 核心文件 | 关键行号/方法 |
|------|---------|-------------|
| **1. 实时学习** | `agent/background_review.py` | 34-43 (记忆审查), 45-148 (技能审查) |
| | `agent/conversation_loop.py` | ~4714-4722 (nudge 触发与 spawn) |
| **2. 技能管理** | `tools/skill_usage.py` | 生命周期状态管理、使用遥测 |
| | `agent/curator.py` | 268-323 (自动状态转换) |
| **3. 长期维护** | `agent/curator.py` | 330-491 (LLM 审查合并 + 报告系统) |
| | `agent/skill_manage.py` | 技能 CRUD 工具实现 |
| **4. 记忆系统** | `agent/memory_manager.py` | 记忆提供者编排器 |
| | `agent/memory_provider.py` | 16 个生命周期钩子的抽象基类 |
| | `plugins/memory/` | 8 个外部提供者（Honcho/Mem0/Holographic 等） |
| **5. 上下文管理** | `agent/conversation_compression.py` | 对话压缩触发与编排 |
| | `agent/context_compressor.py` | 结构化摘要生成 |
| | `trajectory_compressor.py` | 轨迹后处理（训练数据用） |
| **6. 数据分析** | `agent/insights.py` | SQLite 分析引擎（200+ 模型定价） |
| **整合层** | `run_agent.py` | AIAgent 主类，整合所有子系统 |
| | `agent/agent_init.py` | Agent 初始化（nudge 间隔配置等） |

**教学版整体简化了什么**：
- **异步变同步**：生产版的 Background Review 和 Curator 都在后台独立线程 fork `AIAgent` 运行，教学版全部同步
- **可配置变固定**：所有 nudge 间隔、Curator 周期、stale/archive 天数在生产版通过 `~/.hermes/config.yaml` 配置，教学版用代码常量
- **工具系统变直接调用**：生产版通过完整的工具调用系统（`skill_manage`/`memory` 工具 + MCP/Bash 等），教学版直接操作文件
- **辅助模型变主模型**：生产版的压缩和 Curator 审查可使用便宜的辅助模型（节省成本），教学版统一使用主模型
- **多平台变单平台**：生产版支持 CLI/Telegram/Discord/Web 等多平台，Insights 按平台分解，教学版只在终端运行
- **持久化变内存**：生产版所有状态持久化到 SQLite（会话、token 统计、工具事件），教学版大部分在内存中

</details>

<!-- translation-sync: zh@v1 -->
