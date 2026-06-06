# s03: Background Review — 自动背景技能审查

[中文](README.md) · [English](README.en.md)

s01 → s02 → `s03` → [s04](../s04_memory_system/) → ... → s12
> *"好方案不只用一次，沉淀为技能"* — 检测对话中的纠正、发现、过时信号，自动创建或更新技能。
>
> **自进化层**: 实时学习（Background Review）— 技能自动生成。

---

## 问题

s02 让 agent 能自动提取记忆——知道用户用 tab、喜欢函数组件、项目在重写 auth。但记忆是**陈述性知识**（"用户是谁"），不是**程序性知识**（"怎么做这类任务"）。

用户纠正 agent 说"每次部署前要先跑 test suite"——这是一个工作流，应该变成技能。下次 agent 做部署时自动加载这个技能，不需要用户再说一遍。

**记忆回答"用户是谁"，技能回答"如何为用户做这类任务"。**

---

## 解决方案

扩展 Background Review，增加**技能审查**维度。四种信号触发技能创建/更新：

| 信号 | 优先级 | 说明 | 示例 |
|------|--------|------|------|
| **用户纠正** | 🥇 最高 | 用户纠正 agent 的风格/格式/工作流 | "stop doing X", "don't format like this" |
| **新技术/模式** | 🥈 高 | 非平凡的技巧、修复、变通方案 | 发现了一个 API 的坑和绕法 |
| **技能过时** | 🥉 中 | 当前加载的技能被证明错误/缺少步骤 | "那个文档已经过期了" |
| **重复模式** | 低 | 同类任务出现了 3 次以上 | 每次 CR 都做同样的检查步骤 |

---

## 工作原理

### 审查信号检测

```python
def background_skill_review(messages_snapshot, loaded_skills):
    """后台技能审查：检测四类信号"""

    dialogue = format_snapshot(messages_snapshot)

    review_prompt = f"""You are a background skill reviewer. Analyze this conversation.

Look for these signals (in priority order):

1. USER CORRECTION (highest priority):
   - User corrected the agent's style/format/workflow
   - "stop doing X", "don't format like this", "I hate when you Y"
   - These MUST be embedded in a skill
   - Example: User says "每次部署前先跑 test suite" → create deploy-checklist skill

2. NEW TECHNIQUE/PATTERN:
   - Non-trivial trick, fix, workaround, or debugging path discovered
   - A pattern the user taught the agent that should be reused

3. OUTDATED SKILL:
   - A currently loaded skill was proven wrong, missing steps, or out of date
   - Mark the skill for update

4. REPEATED PATTERN:
   - Same type of task appeared 3+ times
   - Can be abstracted into a reusable skill

Currently loaded skills: {", ".join(loaded_skills) if loaded_skills else "none"}

Conversation:
{dialogue}

Return JSON:
{{
  "detected_signals": [
    {{
      "signal_type": "correction|technique|outdated|repeated",
      "action": "create|update|append_reference",
      "skill_name": "kebab-case-name",
      "skill_description": "one-line",
      "skill_body": "full SKILL.md content",
      "reason": "why this signal triggered"
    }}
  ]
}}

If no signals detected, return {{"detected_signals": []}}.
"""
    response = CLIENT.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content": review_prompt}],
        max_tokens=1000,
    )
    return parse_skill_review_response(response)
```

### 操作优先级

检测到信号后，不是全部创建新技能。按优先级选择操作：

```python
def apply_skill_actions(detected_signals, skill_registry):
    """按优先级应用技能操作"""

    for signal in detected_signals:
        action = signal["action"]
        name = signal["skill_name"]

        if action == "update_loaded":
            # 优先 1: 更新当前已加载的技能（最合适的扩展目标）
            update_existing_skill(name, signal["skill_body"])

        elif action == "update_existing":
            # 优先 2: 更新已有伞形技能
            umbrella = find_matching_umbrella(name, skill_registry)
            if umbrella:
                append_to_skill(umbrella, signal)

        elif action == "append_reference":
            # 优先 3: 在已有技能下添加 references/ 文件
            umbrella = find_matching_umbrella(name, skill_registry)
            if umbrella:
                write_reference_file(umbrella, name, signal["skill_body"])

        elif action == "create_new":
            # 优先 4: 创建新伞形技能
            create_skill(name, signal["skill_description"], signal["skill_body"])
```

### 禁止捕获列表

不是所有纠正都应该固化为技能。以下内容**禁止捕获**：

| 禁止捕获 | 原因 |
|---------|------|
| 环境依赖失败 | 缺少二进制文件、未配置凭证——环境问题不是技能 |
| 工具否定性断言 | "browser tools don't work"——可能是临时故障 |
| 会话特定临时错误 | 重试已解决的——一次性错误 |
| 一次性任务叙事 | "帮我写这个脚本"——不是可复用的模式 |

```python
FORBIDDEN_PATTERNS = [
    r"(missing|not found|not installed).*(binary|executable|command)",
    r"(browser|chrome|selenium).*(don['']t work|not working|broken)",
    r"(network|connection|timeout).*(error|failed|unavailable)",
    r"(api key|credential|auth).*(missing|invalid|expired|not set)",
]

def is_forbidden_signal(signal_body: str) -> bool:
    """检查是否属于禁止捕获的内容"""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, signal_body, re.IGNORECASE):
            return True
    return False
```

---

## 相对 s02 的变更

| 组件 | s02 | s03 |
|------|-----|-----|
| 审查维度 | 仅记忆审查 | 记忆审查 + 技能审查 |
| 信号检测 | 无 | 四类信号 + 优先级 |
| 技能操作 | 无 | create/update/append_reference |
| 安全护栏 | 无 | 禁止捕获列表 |
| 技能目录 | 无 | `.skills/` 目录，SKILL.md 文件 |
| Nudge 触发 | 每 5 轮 | 每 10 次工具迭代（技能审查） + 每 5 轮（记忆审查） |

---

## 试一下

```sh
python s03_background_skill_review/code.py
```

试试这些 prompt（故意触发不同的信号）：

1. `Let me show you how I deploy: first run tests, then build, then push to staging.`
2. `Stop using camelCase — I always use snake_case in Python projects.`
3. `In this project, every PR needs: lint check, type check, unit tests, and one reviewer approval.`
4. 多次做类似任务，观察重复模式检测

观察重点：`.skills/` 目录下是否自动创建了新技能？`SKILL.md` 内容是否准确？禁止捕获列表是否工作？

---

## 接下来

现在 agent 能从对话中自动创建记忆和技能了。但记忆系统还只是单文件 `MEMORY.md`。生产环境需要全文搜索、多种记忆类型、可插拔的外部提供者。

s04 Memory System → FTS5 全文搜索 + 可插拔提供者架构 + 生命周期钩子。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/background_review.py:45-148`** — 技能审查的完整实现。生产版在这段代码中定义了四类审查信号和操作优先级：
  - **用户纠正**（一等信号）：检测 "stop doing X"、"don't format like this" 等不满表达，**必须嵌入技能**
  - **新技术/模式**：检测非平凡的技巧、修复、变通方案、调试路径
  - **技能过时**：当前被加载或查阅的技能被证明是错误的、缺少步骤或已过时
  - **重复模式**：同类任务出现 3 次以上
  
  操作优先级（选择最早匹配的）：(1) 更新当前已加载的技能 → (2) 更新已有伞形技能 → (3) 添加 `references/`/`templates/`/`scripts/` 支持文件 → (4) 创建新伞形技能

- **`agent/background_review.py`（禁止捕获逻辑）** — 生产版定义了严格的禁止捕获模式：环境依赖失败（缺少二进制/未配置凭证）、工具否定性断言（"browser tools don't work"）、会话特定临时错误（重试已解决的）、一次性任务叙事。这些规则防止 agent 将临时故障固化为持久的自我约束。

**教学版简化了什么**：
- 生产版的操作优先级涉及对现有技能目录的扫描（通过 `skills_list` + `skill_view` 查找匹配的伞形技能），教学版简化为名称前缀匹配
- 生产版的技能更新会触发 `skill_manage` 工具调用（完整的 SKILL.md 重写/补丁），教学版是文件级替换
- 生产版的禁止捕获使用更复杂的正则 + 上下文判断，教学版使用基础正则列表
- 生产版的信号检测 prompt 更为详细（约 50 行），包含对当前已加载技能上下文的引用

</details>

<!-- translation-sync: zh@v1 -->
