# s11: Error Recovery — 错误不是终点，是学习的起点

[中文](README.md) · [English](README.en.md)

s01 → ... → s10 → `s11` → [s12](../s12_comprehensive/)
> *"出错了不是终点，是学习的起点"* — 错误检测 + 重试策略 + 模型降级 + 自愈流程。
>
> **自进化层**: 错误恢复 — 让 agent 从失败中自愈，并把教训沉淀为技能。

---

## 问题

Agent 在实际运行中会遇到各种错误：
- API 返回 `overloaded_error`——模型太忙
- Token 超限——输出太长被截断
- 工具执行失败——命令不存在、权限不足
- Context window 爆满——需要压缩但不应该丢知识

普通 agent 遇到这些错误就崩溃了。自进化 agent 应该能**自动恢复，并从错误中学习**。

---

## 解决方案

### 三层恢复策略

| 层 | 策略 | 触发条件 |
|----|------|---------|
| 1. 重试 | 指数退避 + jitter | 临时错误（overloaded, timeout） |
| 2. 腾空间 | 自动压缩 + 降级到更小上下文 | token 超限 |
| 3. 换模型 | fallback 到更便宜/更可靠的模型 | 当前模型持续失败 |

### Token 升级策略

```python
def handle_token_limit(response, state):
    """Token 超限时的升级策略"""
    if state.max_output_tokens == 8000:
        # 第 1 次: 升级到 64K
        state.max_output_tokens = 64000
        return "upgraded to 64K"
    elif not state.has_attempted_reactive_compact:
        # 第 2 次: 压缩上下文
        state.has_attempted_reactive_compact = True
        return "compacting context"
    else:
        # 第 3 次: fallback 模型
        return "falling back to alternative model"
```

### 错误日志 → 技能

```python
def on_recovery_success(error_type, recovery_strategy, messages):
    """恢复成功后，检查是否值得沉淀为技能"""
    if error_type in ("token_limit", "context_overflow"):
        # 记录到 MEMORY.md: 哪些操作容易导致溢出
        background_memory_review(messages)
    if recovery_strategy == "novel_workaround":
        # 发现了新的变通方案 → 创建技能
        background_skill_review(messages)
```

---

## 试一下

```sh
python s11_error_recovery/code.py
```

---

## 接下来

所有自进化组件都已就位。最后一步：把所有机制整合到一个完整的自进化 agent 中。

s12 Complete Self-Evolving Agent → 六层架构完整集成。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/conversation_loop.py`（错误恢复路径）** — 生产版在主对话循环中内嵌了多层错误恢复逻辑。当 API 返回 `overloaded_error` 时，使用指数退避 + jitter 重试（而非固定间隔）；当遇到 token 超限时，按优先级升级策略：(1) 扩展 `max_output_tokens`，(2) 触发上下文压缩（reactive compact），(3) 降级到 fallback 模型。每次恢复成功后检查是否值得沉淀为技能（如发现新的变通方案）。
- **错误处理模式** — 生产版的错误处理不是简单的 try/catch，而是分层的：**瞬时错误**（overloaded/timeout）→ 重试 + 用户透明；**可恢复错误**（token_limit/context_overflow）→ 自动修复 + 用户告知；**致命错误**（auth_failure/rate_limit_exhausted）→ 优雅退出 + 状态保存。生产版还在 token 超限时保留对话的语义连续性（压缩而非截断）。

**教学版简化了什么**：
- 生产版的重试使用真实的指数退避 + jitter（防止惊群效应），教学版使用简单的固定间隔重试
- 生产版支持模型 fallback——当前模型持续失败时自动切换到配置的备用模型
- 生产版的错误恢复与背景审查联动——发现新的变通方案后自动触发技能审查
- 生产版在错误发生时保存对话快照（防止数据丢失），教学版依赖内存中的 messages 列表

</details>

<!-- translation-sync: zh@v1 -->
