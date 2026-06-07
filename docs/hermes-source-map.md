# Hermes 源码地图

这份地图把 `learn-hermes-agent` 的 12 个教学章节，对齐到 `NousResearch/hermes-agent` 的生产源码。教学代码故意压缩到可读、可跑、可改；生产版则处理异步执行、权限、多平台、持久化、观测和恢复路径。

> 本项目参考的本地源码路径：`D:\study\hermes-agent`

## 总览

| 教程章节 | 教学目标 | Hermes 生产源码入口 | 生产版多了什么 |
|---|---|---|---|
| `s01_agent_loop` | 最小 agent loop + 单文件记忆 | `run_agent.py`, `agent/conversation_loop.py` | 流式响应、多工具并发、状态恢复、复杂退出路径 |
| `s02_background_memory_review` | 对话后自动提取记忆 | `agent/background_review.py`, `tools/memory_tool.py` | fork 独立审查 agent、快照隔离、非阻塞后台写入 |
| `s03_background_skill_review` | 从纠正和发现中生成技能 | `agent/background_review.py`, `tools/skill_manager_tool.py`, `tools/skills_tool.py` | 技能目录扫描、已加载技能更新、禁止捕获规则、工具化 CRUD |
| `s04_memory_system` | 可搜索、可插拔的记忆系统 | `agent/memory_manager.py`, `agent/memory_provider.py`, `tools/memory_tool.py`, `plugins/memory/` | SQLite/FTS、生命周期钩子、外部记忆提供者、结构化注入 |
| `s05_skill_lifecycle` | 技能状态、pin、archive | `tools/skill_usage.py`, `tools/skill_provenance.py`, `agent/curator.py` | bundled/hub/agent-created 来源区分、遥测更新、恢复策略 |
| `s06_skill_creation` | 什么该学、什么不该学 | `agent/background_review.py`, `tools/skills_guard.py`, `tools/skills_ast_audit.py` | 更细的风险判断、AST 审计、重复模式跨会话分析 |
| `s07_curator_state` | 规则驱动的 stale/archive | `agent/curator.py`, `hermes_cli/skills_config.py` | 空闲触发、配置化周期、dry-run、backup/rollback |
| `s08_curator_llm` | LLM 合并和伞形技能整理 | `agent/curator.py`, `tools/skill_manager_tool.py` | 辅助模型、报告目录、cron 引用重写、不可删除原则 |
| `s09_context_management` | 压缩与记忆预取 | `agent/conversation_compression.py`, `agent/context_compressor.py`, `trajectory_compressor.py` | token 阈值、多层压缩、训练轨迹后处理、辅助模型 |
| `s10_insights` | token/成本/工具模式分析 | `agent/insights.py`, `hermes_state.py`, `hermes_cli/status.py` | SQLite 多表查询、200+ 模型定价、平台维度分析 |
| `s11_error_recovery` | 重试、降级、自愈 | `agent/conversation_loop.py`, `model_tools.py`, `hermes_logging.py` | 指数退避、fallback 模型、语义连续性保存、错误分层 |
| `s12_comprehensive` | 六层集成 | `run_agent.py`, `cli.py`, `toolsets.py`, `tools/registry.py` | 完整 CLI、多平台入口、权限治理、MCP/浏览器/终端工具集 |

## 读源码顺序

1. 先读 `run_agent.py`：理解 `AIAgent` 如何把模型、工具、记忆、技能、压缩和错误恢复接起来。
2. 再读 `agent/background_review.py`：这是“自学习”的入口，记忆和技能都从这里沉淀。
3. 接着读 `agent/curator.py`：理解为什么技能不能无限增长，以及 Hermes 如何合并、归档、生成报告。
4. 然后读 `agent/memory_manager.py` 和 `tools/memory_tool.py`：看记忆如何作为工具被模型调用，又如何注入上下文。
5. 最后读 `agent/insights.py`、`hermes_state.py`、`trajectory_compressor.py`：这些决定长期运行后的可观测性和数据资产价值。

## 教学版为什么要简化

教学版保留核心机制，去掉生产复杂度：

- 后台任务从异步 fork 简化为同步函数，方便单步观察。
- SQLite/FTS 和多表状态在早期章节简化为文件或内存结构。
- 完整工具系统简化为直接函数调用，突出机制而不是框架。
- 辅助模型、权限、MCP、多平台入口放到“生产版对照”里解释，不阻塞学习主线。

这不是“玩具版”，而是把生产系统拆成可理解的最小剖面。读者学完 12 章后，再回到 Hermes 源码，会知道每个大文件到底在解决什么问题。
