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

<!-- translation-sync: zh@v1 -->
