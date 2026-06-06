# s09: Context Management — 上下文满了就压

[中文](README.md) · [English](README.en.md)

s01 → ... → s08 → `s09` → [s10](../s10_insights/) → ... → s12
> *"上下文满了就压，但重要的事要留在外面"* — 对话压缩 + 轨迹压缩 + 记忆预取 + 注入格式。
>
> **自进化层**: 上下文管理 — 保护自进化的知识不被压缩吞没。

---

## 问题

Agent 连续工作 30 分钟，messages 列表塞满了中间过程。旧的 tool_result、过时的文件内容——占着上下文但不产生价值。当上下文接近 token 上限时，必须压缩。

但压缩有风险：s02 的背景审查提取的记忆、s03 自动创建的技能——这些自进化的产物如果被压缩吞没，下一次对话 agent 又变傻了。

**需要智能压缩：压缩中间过程，保护自进化产物。**

---

## 解决方案

**四层压缩策略** + **记忆预取保护**。

### 对话压缩

```python
def auto_compact(messages, token_limit):
    """当对话超过 token 阈值时自动压缩"""
    if count_tokens(messages) < token_limit:
        return messages

    # 保护头部（系统提示 + 早期上下文）和尾部（最近交互）
    head = messages[:3]
    tail = messages[-8:]

    # 压缩中间部分
    middle = messages[3:-8]
    summary = summarize_with_aux_model(middle)

    return head + [summary_message(summary)] + tail
```

### 结构化摘要模板

```
已解决问题:
- ✅ 修复了 auth 模块的 token 过期 bug
- ✅ 完成了 API 文档更新

待解决问题:
- ⬜ 性能优化：数据库查询需要添加索引
- ⬜ 部署脚本需要适配新环境

关键决策:
- 使用 Redis 替代 Memcached 做会话存储

用户约束:
- 所有 API 端点必须加 rate limiting
```

关键设计：**"Remaining Work" 替代 "Next Steps"**（防止被 LLM 读取为活跃指令）。

### 轨迹压缩

后处理已完成的 agent 轨迹（JSONL），压缩中间工具响应，保留训练信号质量：

```bash
python trajectory_compressor.py --input=data/my_run --target_max_tokens=16000
```

### 记忆预取保护

压缩前先通知记忆提供者提取洞察（`on_pre_compress()` 钩子），确保压缩过程中不会丢失重要知识。

---

## 上下文注入格式

记忆和技能内容通过 fenced block 注入，区分为"系统参考数据"而非"新用户输入"：

```xml
<memory-context>
[System note: The following is recalled memory context, NOT new user input.
Treat as authoritative reference data.]

...记忆内容...

</memory-context>
```

---

## 试一下

```sh
python s09_context_management/code.py
```

1. 做多次文件操作，让 messages 积累 → 观察压缩触发
2. 在压缩前后查看记忆是否保留

---

## 接下来

Agent 现在有了完整的自进化能力——学习、记忆、技能、整理、压缩。但怎么衡量效果？用了多少 token？成本多少？

s10 Insights Engine → token/成本/工具模式分析。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/conversation_compression.py`** — 对话压缩的触发与编排。生产版在此处监控 token 使用量，当对话超过阈值时自动触发压缩，使用辅助模型（便宜/快速）总结中间轮次。保护头部（系统提示 + 早期上下文）和尾部（最近交互），只压缩中间的工具调用和响应。
- **`agent/context_compressor.py`** — 上下文压缩的核心实现。生产版的压缩器使用结构化摘要模板（区分"已解决问题"和"待解决问题"），关键设计是使用 **"Remaining Work"** 替代 "Next Steps"（防止被 LLM 读取为活跃指令）。压缩前先调用记忆提供者的 `on_pre_compress()` 钩子提取洞察。
- **`trajectory_compressor.py`** — 轨迹后处理压缩工具。用于压缩已完成的 agent 轨迹（JSONL 格式），保护首尾轮次，压缩中间工具响应，保留训练信号质量。支持 `--target_max_tokens`（目标 token 预算）和 `--sample_percent`（采样百分比）参数。用于生成训练数据或长会话归档。

**教学版简化了什么**：
- 生产版使用精确的 token 计数判断压缩时机（基于模型特定的 tokenizer），教学版用简单的消息数量估算
- 生产版的压缩使用辅助模型异步执行，不阻塞主对话；教学版是同步阻塞
- 生产版的 `trajectory_compressor.py` 是一个独立的 CLI 工具（可对 JSONL 文件批量操作），教学版不含此组件
- 生产版的压缩摘要包含更多结构化字段（关键决策、用户约束、已加载技能），教学版仅区分 已解决/待解决

</details>

<!-- translation-sync: zh@v1 -->
