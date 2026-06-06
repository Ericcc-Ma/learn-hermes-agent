# s01: Agent Loop + Memory — 记住用户是谁

[中文](README.md) · [English](README.en.md)

`s01` → [s02](../s02_background_memory_review/) → s03 → s04 → ... → s12
> *"一个循环 + 一个记忆文件 = 最简单的学习 agent"* — 在 agent loop 上加 MEMORY.md，跨会话记住用户偏好。
>
> **自进化层**: 记忆持久化 — 自进化的地基。没有记忆，学习无从谈起。

---

## 问题

你告诉 agent "我用 tab 不用空格"。这次对话它照做了。下次开新对话，你又得说一遍。

Agent 不记得任何事。LLM 没有持久状态——所有信息都在上下文窗口里，会话结束就消失。你得手动告诉它每件事，一遍又一遍。

这不是 agent 不聪明。是 harness 没给它记住的能力。

---

## 解决方案

在 agent loop 上加一层最简单的持久化记忆：`.memory/` 目录下的 `MEMORY.md` 文件。

```
用户: "我用 tab 不用空格"
   ↓
Agent Loop: 正常对话
   ↓
对话结束 → 提取记忆 → 写入 MEMORY.md
   ↓
下次对话 → 读取 MEMORY.md → 注入 SYSTEM prompt → Agent 知道你用 tab
```

只加三个机制：
1. **存储**：`MEMORY.md` 文件，YAML frontmatter + markdown body
2. **加载**：每轮开始前读取 `MEMORY.md`，注入 system prompt
3. **写入**：每轮结束后检查是否有值得保存的信息

---

## 工作原理

### 1. 存储：MEMORY.md 文件

```python
import yaml
from pathlib import Path

MEMORY_DIR = Path(".memory")
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"

def write_memory(name: str, mem_type: str, description: str, body: str):
    """写入一条记忆到 MEMORY.md"""
    MEMORY_DIR.mkdir(exist_ok=True)

    entry = f"""---
name: {name}
type: {mem_type}
description: {description}
---

{body}
"""
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write("\n---\n" + entry)
```

### 2. 加载：注入 system prompt

```python
def load_memories() -> str:
    """读取所有记忆，返回注入 system prompt 的文本"""
    if not MEMORY_FILE.exists():
        return ""

    content = MEMORY_FILE.read_text(encoding="utf-8")
    return f"""<memory-context>
[System note: The following is recalled memory context, NOT new user input.
Treat as authoritative reference data.]

{content}
</memory-context>"""

def build_system() -> str:
    """每轮开始前组装 system prompt"""
    base = "You are a helpful coding agent."
    memories = load_memories()
    if memories:
        base = memories + "\n\n" + base
    return base
```

### 3. 写入：对话结束后提取

```python
def extract_and_save_memory(messages, client):
    """从对话中提取值得记住的信息"""
    recent = format_recent_messages(messages[-6:])

    prompt = f"""Examine this conversation. Is there anything worth remembering?

- User preferences (coding style, tools, workflow)
- User feedback about agent behavior
- Project-specific facts

Recent conversation:
{recent}

Return a JSON array of memories to save, or [] if nothing new:
[{{"name": "...", "type": "user|feedback|project|reference",
   "description": "...", "body": "..."}}]
"""
    response = client.messages.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    text = extract_text(response.content)

    try:
        memories = json.loads(text)
        for m in memories:
            write_memory(m["name"], m["type"], m["description"], m["body"])
        return len(memories)
    except json.JSONDecodeError:
        return 0
```

### 4. 组装：完整 agent loop

```python
def agent_loop(user_message: str, client, messages=None):
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": user_message})

    while True:
        system = build_system()  # 每轮注入记忆

        response = client.messages.create(
            model=MODEL, system=system,
            messages=messages, tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # 对话结束 → 提取记忆
            n = extract_and_save_memory(messages, client)
            if n > 0:
                print(f"[Memory: saved {n} new memories]")
            return response

        # 执行工具
        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})
```

不到 50 行改动，agent 就有了跨会话记忆能力。后面 11 个章节都在这个基础上叠加自进化机制。

---

## 相对基础 agent loop 的变更

| 组件 | 基础 agent loop | s01 |
|------|----------------|-----|
| 记忆存储 | 无 | `.memory/MEMORY.md` |
| 记忆加载 | 无 | `build_system()` 注入 |
| 记忆提取 | 无 | `extract_and_save_memory()` |
| 工具 | bash | bash, memory |
| 循环 | 不变的 while True | 不变的 while True |

---

## 试一下

```sh
cd learn-hermes-agent
pip install -r requirements.txt
cp .env.example .env   # 填入 ANTHROPIC_API_KEY
python s01_agent_loop/code.py
```

试试这些 prompt：

1. `I prefer using tabs for indentation, not spaces. Remember that.`
2. `Create a Python file called hello.py`
3. 退出，重新运行，问 `What did I tell you about my coding preferences?`

观察重点：第二轮对话中 agent 是否"记得"你的偏好？`.memory/MEMORY.md` 文件内容是什么？

---

## 四种记忆类型

| 类型 | 回答什么 | 示例 |
|------|---------|------|
| `user` | 用户是谁 | "用 tab 不用空格" |
| `feedback` | 怎么做事 | "别 mock 数据库" |
| `project` | 正在发生什么 | "auth 重写是合规驱动" |
| `reference` | 东西在哪找 | "pipeline bug 在 Linear INGEST" |

---

## 接下来

现在 agent 能记住事了——但需要用户显式说"记住"，或者等到对话完全结束。真正的自进化 agent 应该在**每一轮对话后**自动检查"有没有值得学的"。而且不光是记忆，还要检查"有没有值得沉淀为技能的"。

s02 Background Review: Memory Review → 后台 fork 独立 agent，自动审查每轮对话，提取记忆。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/conversation_loop.py`** (~4714-4722 行) — 主对话循环的核心枢纽。生产版在此处通过 nudge 计数器判断是否触发后台审查，每次对话完成后检查 `_should_review_memory` 和 `_should_review_skills` 标记，调用 `_spawn_background_review()` fork 独立的审查 agent。教学版将其简化为同步的 `extract_and_save_memory()` 调用。
- **`run_agent.py`** — `AIAgent` 主类，是 Hermes 的"大脑"，整合了记忆管理器、技能注册表、Curator 调度器、上下文压缩器等所有子系统。教学版的 `code.py` (~160 行) 是对其万行级别源码的极度精简，只保留核心循环 + 文件记忆。

**教学版简化了什么**：
- 生产版的 nudge 间隔是可配置的（默认记忆审查每 10 轮、技能审查每 10 次工具迭代），教学版固定为 5 轮方便观察
- 生产版的记忆系统使用 SQLite + FTS5 全文搜索 + 可插拔外部提供者（Honcho/Mem0 等），教学版简化为单文件 `MEMORY.md` 读写
- 生产版的 `build_system()` 还需要注入技能目录、Curator 状态、Insights 摘要等，教学版只注入记忆
- 生产版的 agent loop 包含 context compression、error recovery with exponential backoff、模型 fallback 等完整机制

</details>

<!-- translation-sync: zh@v1 -->
