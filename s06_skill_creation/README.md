# s06: Skill Creation — 什么该学，什么不该学

[中文](README.md) · [English](README.en.md)

s01 → ... → s05 → `s06` → [s07](../s07_curator_state/) → ... → s12
> *"什么该学、什么不该学——有规则"* — 信号优先级、禁止捕获列表、操作优先级策略。
>
> **自进化层**: 技能创建安全护栏 — 防止学错、学多、学坏。

---

## 问题

s03 的背景技能审查让 agent 能自动创建技能。但如果不加约束，agent 会：
- 把环境错误当技能保存（"npm install failed: missing node" → 创建 "node-installation" 技能？）
- 把一次性任务固化为技能（"帮我写这个脚本" → 创建 "write-script" 技能？）
- 把临时 bug 写成技能（"browser tools don't work right now" → 创建 "browser-broken" 技能？）

**自动学习需要安全护栏。不是所有信号都值得固化。**

---

## 解决方案

三层安全护栏：

### 1. 信号优先级（决定检测什么）

| 优先级 | 信号 | 触发条件 | 示例 |
|--------|------|---------|------|
| 🥇 最高 | 用户纠正 | 用户说 "stop doing X" / "don't format like this" | "每次部署前先跑 test suite" |
| 🥈 高 | 新技术/模式 | 非平凡的技巧、修复、变通方案 | 发现了一个 API 的坑和绕法 |
| 🥉 中 | 技能过时 | 当前加载的技能被证明错误/过时 | "那个文档已经过期了" |
| 低 | 重复模式 | 同类任务 3 次以上 | 每次 CR 都做同样的检查 |

### 2. 禁止捕获列表（决定不学什么）

```python
FORBIDDEN_PATTERNS = [
    # 环境依赖失败
    r"(missing|not found|not installed).*(binary|executable|command)",

    # 工具否定性断言（可能是临时故障）
    r"(browser|chrome|selenium).*(don't work|not working|broken)",

    # 网络/连接临时错误
    r"(network|connection|timeout).*(error|failed|unavailable)",

    # 凭证/认证缺失（环境配置问题）
    r"(api key|credential|auth).*(missing|invalid|expired|not set)",

    # 一次性任务叙事
    r"(write|create|make) (me |a |the ).*(script|file|program)",
]
```

### 3. 操作优先级（决定怎么做）

检测到信号后，不是全部创建新技能：

| 优先级 | 操作 | 条件 |
|--------|------|------|
| 1 | **更新当前已加载的技能** | 该技能在对话中被使用——最合适的扩展目标 |
| 2 | **更新已有伞形技能** | 通过 `skills_list` + `skill_view` 找到匹配的类级别技能 |
| 3 | **添加支持文件** | 在现有伞形技能下添加 `references/`、`templates/` 或 `scripts/` |
| 4 | **创建新伞形技能** | 只有当没有现有技能覆盖该类任务时 |

---

## 核心原则

### 学习而非记忆

用户偏好嵌入技能 body，不仅存记忆。记忆回答"用户是谁"，技能回答"如何为这个用户做这类任务"。

### 类级别伞形结构

目标是少量丰富的类级别技能，而非大量狭窄的一次性条目。一个伞形技能的 `references/` 子文件比五个窄兄妹技能更好。

### 保护与安全

- 内置/Hub 安装的技能永不触碰（除非显式启用 `prune_builtins`）
- 归档可恢复，永不删除（`.archive/` 目录）
- 禁止捕获环境依赖失败和工具否定性断言

---

## 试一下

```sh
python s06_skill_creation/code.py
```

试试触发不同信号：
1. "Every time you deploy, always run tests first, then lint, then build." → 应创建部署技能
2. "I hate when you format my SQL queries — stop doing that." → 应创建/更新格式规则技能
3. "npm install failed: python3 not found" → 应被禁止捕获
4. 查看 `/forbidden-log` 看到哪些信号被拦截

---

## 接下来

技能创建有了安全护栏。但技能越积越多，需要一个自动整理系统——Curator。

s07 Curator: Auto State Transitions → 纯规则自动 stale/archive，零 LLM 成本。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/background_review.py`（信号检测与禁止捕获）** — 生产版在此处实现了完整的信号分类和过滤逻辑。四类信号的检测各有不同的 prompt 权重：用户纠正信号（一等信号）在审查 prompt 中被重点强调，要求"必须嵌入技能"；新技术/模式需要判断是否"非平凡"；技能过时需要确认被加载或查阅过；重复模式需要 3 次以上的同类任务。
- **`agent/background_review.py`（禁止捕获模式）** — 生产版的禁止捕获列表比教学版更为精细，不仅限于正则匹配，还包括上下文判断（如：同样是 "command not found"，如果是用户主动安装过程中出现的 → 不捕获；如果是 agent 反复尝试同一条命令 → 可能是有价值的变通方案）。核心原则是防止将**临时故障固化为持久的自我约束**。

**教学版简化了什么**：
- 生产版的信号检测 prompt 约 50 行（包含对当前已加载技能、技能目录的完整上下文），教学版约 30 行
- 生产版的禁止捕获逻辑结合了正则 + 重试计数（重试后成功的 → 不捕获；反复失败的 → 可能是环境问题，也不捕获）
- 生产版的操作优先级涉及 `skill_manage` 工具的真实调用（创建/更新 SKILL.md、写入 references/、管理 DESCRIPTION.md），教学版是文件级模拟
- 生产版的"重复模式"检测需要跨会话分析（通过 Insights 的 SQLite 数据），教学版简化为内存计数

</details>

<!-- translation-sync: zh@v1 -->
