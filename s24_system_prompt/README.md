# s24: System Prompt Assembly — prompt 是拼出来的

[中文](README.md)

s01 → ... → s23 → `s24`
> *"prompt 是拼出来的，不是写死的"* — 分段定义 + 按需注入 + 条件拼接 + 平台差异。
>
> **Harness 基础**: System Prompt — 运行时组装，不同场景不同 prompt。

---

## 问题

System prompt 通常是一大段硬编码字符串。加了新工具要手动加描述、换了 profile 要手动改 prompt、不同平台需要不同的行为——全都改代码很痛苦。

---

## 解决方案

**分段 + 条件注入**：

```python
sections = [
    ("identity",    "You are Hermes...",               priority=10),
    ("safety",      "SAFETY: Do NOT...",               priority=20),
    ("memory_ctx",  "<memory-context>...</memory>",    priority=40, condition="has_memories"),
    ("skills",      "SKILLS: code-review, deploy",     priority=60, condition="has_skills"),
]
```

最终 prompt = 所有满足条件的片段按优先级排序拼接。

同一个 builder，CLI 平台和 Cron 平台拼出不同的 prompt。

---

## 试一下

```sh
python s24_system_prompt/code.py
```

<details>
<summary>深入 Hermes 源码</summary>

生产版 system prompt 组装位于以下源文件:

| 文件 | 职责 |
|------|------|
| `agent/system_prompt.py` | 主 system prompt 构建器 |
| `agent/prompt_builder.py` | 分段 prompt 组装、条件注入 |
| `agent/memory_provider.py` | memory context 注入 |
| `gateway/session_context.py` | gateway 平台上下文注入 |

教学版简化了什么:
- 生产版 system prompt 有 20+ 个分段，按 priority 排序拼接
- 生产版每段的注入条件包括: profile、platform、has_memories 等
- 生产版 prompt cache TTL 感知: 记忆注入时机考虑 cache 有效性
- 生产版不同平台 (CLI/Telegram/Cron) 的 prompt 有很大差异

</details>

<!-- translation-sync: zh@v1 -->
