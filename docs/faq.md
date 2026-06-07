# FAQ

## 这个项目和 Hermes Agent 是什么关系？

`learn-hermes-agent` 是教学项目，不是 Hermes Agent 的源码镜像。它参考 `NousResearch/hermes-agent` 的自进化机制，把生产系统拆成 12 个能独立运行的小章节。

## 和 learn-claude-code 有什么区别？

`learn-claude-code` 讲 agent harness 的基础：循环、工具、权限、子 agent、任务系统、worktree 隔离等。

`learn-hermes-agent` 讲自进化层：背景审查、记忆、技能生成、技能生命周期、Curator、上下文压缩、Insights 和错误恢复。

简单说：

```text
learn-claude-code 解决：Agent 怎么能动手
learn-hermes-agent 解决：Agent 怎么越用越聪明
```

## 学这个需要先读 Hermes Agent 源码吗？

不需要。建议先按 `s01` 到 `s12` 跑完教学版，再用 `docs/hermes-source-map.md` 回到生产源码。

## 每章都需要真实 API Key 吗？

代码可以被测试和导入，不需要 API Key。要实际体验对话，需要配置 `.env`。项目支持 Anthropic、DeepSeek、OpenAI、Qwen/GLM/Moonshot 等 OpenAI-compatible provider，以及 Ollama。

## 为什么教学版很多地方是同步的？

生产版 Hermes 会 fork 独立 agent 在线程或后台任务里运行审查和整理。教学版先用同步版本保留因果关系，读者能直接看到“对话输入 -> 审查 -> 写入记忆/技能”的完整链路。

## 为什么强调技能，而不是只保存记忆？

记忆回答“用户是谁、项目是什么”。技能回答“以后遇到这类任务应该怎么做”。自进化 agent 不能只记事实，还要把可复用的工作方法沉淀成技能。

## 这个项目适合谁？

- 想理解 Hermes Agent / Claude Code 这类 agent harness 的工程师
- 想自己做长期运行 agent 的开发者
- 想把“AI 应用”从 prompt chain 提升到可学习系统的人
- 想读生产级 agent 源码但需要学习路径的人

## 推荐阅读顺序是什么？

1. 读根目录 `README.md`，理解自进化 agent 的六层架构。
2. 跑 `s01_agent_loop/code.py`，确认最小循环能工作。
3. 跑 `s02` 到 `s06`，理解记忆和技能如何自动生成。
4. 跑 `s07` 到 `s12`，理解长期维护、压缩、观测和恢复。
5. 对照 `docs/hermes-source-map.md` 阅读 Hermes 生产源码。
