# Learn Hermes Agent -- 自进化 Agent Harness 工程

[中文](README.md) · [English](README.en.md)

<p align="center">
  <img src="assets/social-preview.svg" alt="Learn Hermes Agent" width="800">
</p>

<p align="center">
  <a href="https://github.com/hongye/learn-hermes-agent/actions"><img src="https://img.shields.io/github/actions/workflow/status/hongye/learn-hermes-agent/test.yml?style=flat-square" alt="CI"></a>
  <a href="https://github.com/hongye/learn-hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/chapters-12-brightgreen?style=flat-square" alt="Chapters"></a>
  <a href="#"><img src="https://img.shields.io/badge/llm-anthropic%20%7C%20deepseek%20%7C%20openai%20%7C%20qwen%20%7C%20glm-7C4DFF?style=flat-square" alt="LLM"></a>
  <a href="#"><img src="https://img.shields.io/badge/languages-中文%20%7C%20English-blue?style=flat-square" alt="Languages"></a>
</p>

## Agency 来自模型。自进化来自 Harness。

一个 agent 能感知、推理、行动，这是模型训练出来的。但一个 agent 能**从每次对话中学习、自动沉淀知识、长期自我改进**——这是 harness 赋予的。

`learn-claude-code` 教了你如何造载具——让 agent 能动手的环境。本仓库教你造**会自己进化的载具**——让 agent 在运行中自动积累知识、创建技能、整理技能库、最终越用越聪明。

---

## 什么是自进化 Agent

普通 agent 每次对话从零开始。关了重开，什么都不记得。用户纠正过的错误下次照样犯。发现的好方案下次照样找不到。

自进化 agent 不同：

```
每次对话 → 背景审查 → 提取记忆/技能 → 持久化
                                            ↓
下次对话 → 加载记忆 → 匹配技能 → Agent 更聪明了
                     ↓
               定期整理（Curator）→ 技能库不膨胀
```

**核心思想**：对话不只是完成任务，更是学习机会。学到的每一个教训、每一条偏好、每一种模式，都自动转化为可复用的知识资产。

---

## Hermes 自进化体系：六层架构

Hermes 是 Claude Code 的自进化子系统。它的架构分为六个层次：

```
第 1 层：实时学习    — Background Review（背景审查）
第 2 层：技能管理    — Skill Lifecycle（生命周期）
第 3 层：长期维护    — Curator System（技能库整理）
第 4 层：记忆系统    — Memory System（持久化知识）
第 5 层：上下文管理  — Context Management（压缩与注入）
第 6 层：数据分析    — Insights Engine（使用分析）
```

每一层解决一个问题，每一层在前一层的基础上叠加。

---

## 12 个递进课程

**每个课程添加一个自进化机制。每个机制有一句格言。**

> **s01** &nbsp; *"一个循环 + 一个记忆文件 = 最简单的学习 agent"* — 在 agent loop 上加 MEMORY.md，记住用户偏好
>
> **s02** &nbsp; *"每次对话结束，问自己'学到了什么'"* — 背景记忆审查，自动从对话中提取记忆
>
> **s03** &nbsp; *"好方案不只用一次，沉淀为技能"* — 背景技能审查，从纠正和发现中自动创建技能
>
> **s04** &nbsp; *"记忆不该只有一个文件"* — 双层架构、可插拔提供者、FTS5 全文搜索
>
> **s05** &nbsp; *"技能有生老病死"* — active → stale → archived 生命周期，pin 豁免，Umbrella 结构
>
> **s06** &nbsp; *"什么该学、什么不该学——有规则"* — 信号优先级、禁止捕获列表、安全护栏
>
> **s07** &nbsp; *"30 天不用就标记，90 天归档，规则说了算"* — 纯规则自动状态转换，零 LLM 成本
>
> **s08** &nbsp; *"技能太多会乱，定期合并整理"* — LLM 审查合并，前缀聚类，伞形构建
>
> **s09** &nbsp; *"上下文满了就压，但重要的事要留在外面"* — 对话压缩、轨迹压缩、记忆预取
>
> **s10** &nbsp; *"你不知道自己用了多少 token？那怎么优化"* — Token/成本追踪、工具模式分析
>
> **s11** &nbsp; *"出错了不是终点，是学习的起点"* — 错误检测、模型降级、自愈策略
>
> **s12** &nbsp; *"六层归位，一个会自己进化的 agent"* — 全部机制回到一个完整自进化 agent

---

## 核心模式

```python
def agent_loop(messages):
    while True:
        # 1. 每轮前：注入相关记忆和技能
        inject_memories(messages)
        inject_skills(messages)

        response = client.messages.create(
            model=MODEL, system=build_system(),
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # 2. 每轮后：背景审查，提取学习
            spawn_background_review(messages)
            return

        # 3. 执行工具
        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})
```

循环不变。自进化机制挂在循环的前后。模型负责决策，harness 负责学习。

---

## 全部章节

| 章节 | 主题 | 关键概念 |
|---|---|---|
| [s01](./s01_agent_loop/) | Agent Loop + Memory | `agent_loop` / `MEMORY.md` / 记忆持久化 |
| [s02](./s02_background_memory_review/) | 背景记忆审查 | `BackgroundReview` / nudge / 对话快照 |
| [s03](./s03_background_skill_review/) | 背景技能审查 | 信号检测 / 技能自动创建 / 优先级规则 |
| [s04](./s04_memory_system/) | 记忆系统深度 | FTS5 / 可插拔提供者 / 生命周期钩子 |
| [s05](./s05_skill_lifecycle/) | 技能生命周期 | active/stale/archived / pin / Umbrella 结构 |
| [s06](./s06_skill_creation/) | 技能自动创建 | 信号优先级 / 禁止捕获 / 操作优先级 |
| [s07](./s07_curator_state/) | Curator 自动转换 | 纯规则状态机 / 空闲触发 / 配置管理 |
| [s08](./s08_curator_llm/) | Curator LLM 合并 | 前缀聚类 / 伞形合并 / 降级 / 报告生成 |
| [s09](./s09_context_management/) | 上下文管理 | 对话压缩 / 轨迹压缩 / 记忆预取 / 注入格式 |
| [s10](./s10_insights/) | Insights 引擎 | Token 统计 / 成本分析 / 工具模式 / 趋势 |
| [s11](./s11_error_recovery/) | 错误恢复 | 重试策略 / fallback 模型 / 自愈流程 |
| [s12](./s12_comprehensive/) | 完整自进化 Agent | 六层架构完整集成 |

---

## 学习路径

主线：能记住 → 能学习 → 能管理知识 → 能整理 → 能分析 → 能自愈 → 完整进化

```mermaid
flowchart TD
    classDef stage1 fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#0D47A1,rx:12,ry:12,text-align:left
    classDef stage2 fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#1B5E20,rx:12,ry:12,text-align:left
    classDef stage3 fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,rx:12,ry:12,text-align:left
    classDef stage4 fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#4A148C,rx:12,ry:12,text-align:left

    subgraph Phase1 ["🌱 阶段 1：基础自进化（记忆 + 学习）"]
        direction LR
        S1["<b>1. 让 Agent 能记住</b><br/>━━━━━━━━━━━━━<br/><b>s01 Agent Loop + Memory</b><br/>└─ 循环 + MEMORY.md<br/><br/><b>s02 背景记忆审查</b><br/>└─ 自动从对话提取记忆"]:::stage1

        S2["<b>2. 让 Agent 能学习</b><br/>━━━━━━━━━━━━━<br/><b>s03 背景技能审查</b><br/>└─ 从纠正中创建技能<br/><br/><b>s04 记忆系统深度</b><br/>└─ FTS5 + 可插拔提供者"]:::stage2

        S1 ==> S2
    end

    subgraph Phase2 ["🚀 阶段 2：高级自进化（管理 + 整理 + 分析 + 自愈）"]
        direction LR
        S3["<b>3. 管理知识资产</b><br/>━━━━━━━━━━━━━<br/><b>s05 技能生命周期</b><br/>└─ 状态转换 + umbrella<br/><br/><b>s06 技能创建规则</b><br/>└─ 信号优先级 + 安全</b>"]:::stage3

        S4["<b>4. 长期维护 + 整合</b><br/>━━━━━━━━━━━━━<br/><b>s07 Curator 自动转换</b><br/>└─ 纯规则 stale/archive<br/><br/><b>s08 Curator LLM 合并</b><br/>└─ 前缀聚类 + 伞形构建<br/><br/><b>s09 上下文管理</b><br/>└─ 压缩 + 预取 + 注入<br/><br/><b>s10 Insights 引擎</b><br/>└─ token/成本/模式<br/><br/><b>s11 错误恢复</b><br/>└─ 重试 + 降级 + 自愈<br/><br/><b>s12 完整自进化 Agent</b><br/>└─ 六层全部集成"]:::stage4

        S3 ==> S4
    end

    Phase1 ==> Phase2
```

---

## 如何阅读

每章一个文件夹，包含：

```
s04_memory_system/
  README.md              # 完整叙事 + 内联代码
  code.py                # 独立可运行实现
  images/                # SVG 图表
```

从 s01 读到 s12，按顺序。每章假定你已读过前面章节，章末有通往下一章的钩子。

---

## 快速开始

```sh
git clone <learn-hermes-agent-repo>
cd learn-hermes-agent
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 选择 LLM_PROVIDER 并填入 API Key

# 使用 Anthropic（默认）
python s01_agent_loop/code.py

# 使用 DeepSeek
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-... MODEL_ID=deepseek-chat python s01_agent_loop/code.py

# 使用通义千问
LLM_PROVIDER=openai_compat LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 LLM_API_KEY=sk-... python s01_agent_loop/code.py
```

---

## 支持的语言模型

通过统一的 `llm.py` 模块，支持多种 LLM provider。设置 `LLM_PROVIDER` 环境变量即可切换：

| Provider | 模型示例 | 环境变量 |
|----------|---------|---------|
| **Anthropic** | claude-sonnet-4-6, claude-opus-4-8 | `ANTHROPIC_API_KEY` |
| **DeepSeek** | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` |
| **OpenAI** | gpt-4o, gpt-4o-mini | `OPENAI_API_KEY` |
| **通义千问 / Qwen** | qwen-plus, qwen-max | `LLM_API_KEY` + `LLM_BASE_URL` |
| **智谱 / GLM** | glm-4-flash, glm-4-plus | `LLM_API_KEY` + `LLM_BASE_URL` |
| **月之暗面 / Moonshot** | moonshot-v1-8k | `LLM_API_KEY` + `LLM_BASE_URL` |
| **Ollama (本地)** | llama3, qwen2.5, etc. | `LLM_BASE_URL` |

```bash
# 使用 DeepSeek
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-... MODEL_ID=deepseek-chat python s01_agent_loop/code.py

# 使用通义千问
LLM_PROVIDER=openai_compat LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 LLM_API_KEY=sk-... MODEL_ID=qwen-plus python s01_agent_loop/code.py
```

所有 provider 通过 `LLM_PROVIDER=openai_compat` + 自设 `LLM_BASE_URL` 即可接入任意 OpenAI 兼容接口。

---

## 与 learn-claude-code 的关系

`learn-claude-code` 教 harness 基础——循环、工具、权限、子 agent、任务系统等让 agent 能"动手"的机制。本仓库假定你已理解这些基础，专注于**自进化层**——让 agent 越用越聪明的机制。

```
learn-claude-code                   learn-hermes-agent
(agent harness 基础:                 (自进化 harness:
 循环、工具、权限、子 agent、          背景审查、技能生命周期、
 任务系统、worktree 隔离)             Curator、记忆系统、Insights)
```

两仓库互补。合在一起，覆盖了从"能动手"到"会进化"的完整 harness 工程。

---

## 项目结构

```
learn-hermes-agent/
  s01_agent_loop/              # Agent Loop + 基础记忆
  s02_background_memory_review/ # 背景记忆审查
  s03_background_skill_review/  # 背景技能审查
  s04_memory_system/            # 记忆系统深度
  s05_skill_lifecycle/          # 技能生命周期管理
  s06_skill_creation/           # 技能自动创建规则
  s07_curator_state/            # Curator 自动状态转换
  s08_curator_llm/              # Curator LLM 审查合并
  s09_context_management/       # 上下文管理
  s10_insights/                 # Insights 分析引擎
  s11_error_recovery/           # 错误恢复与自愈
  s12_comprehensive/            # 完整自进化 Agent
  skills/                       # 示例技能文件
  tests/                        # 测试
```

---

## 许可证

MIT

---

**Agency 来自模型。自进化来自 Harness。每次对话都是学习机会，学到的知识自动沉淀为可复用的技能和记忆。**

**Build the harness that learns. The model will do the rest.**
