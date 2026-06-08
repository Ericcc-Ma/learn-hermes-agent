# s20: Hook System — 挂在循环上，不写进循环里

[中文](README.md)

s01 → ... → s19 → `s20` → [s21](../s21_worktree/) → ... → s24
> *"挂在循环上，不写进循环里"* — PreToolUse/PostToolUse/SessionStart/Stop 等扩展点。
>
> **Harness 基础**: Hooks — 不改 agent loop 代码即可扩展功能。

---

## 问题

s19 的权限检查写在 `execute_tool` 里面。如果还要加审计日志、结果裁剪、会话统计……全都塞进 agent loop，代码越来越臃肿。

**需要扩展点——在不修改 agent loop 的情况下注入自定义逻辑。**

---

## 解决方案

**Hook 注册表** — 在关键节点（工具前后、会话起止等）设置 hook 点，任何函数注册到对应 hook 点即可自动触发。

### 8 个 Hook 节点

| Hook | 触发时机 | 典型用途 |
|------|---------|---------|
| `PRE_TOOL_USE` | 工具执行前 | 权限检查、参数校验、审计 |
| `POST_TOOL_USE` | 工具执行后 | 结果裁剪、二次处理、缓存 |
| `SESSION_START` | 会话开始 | 加载配置、预热资源 |
| `SESSION_END` | 会话结束 | 统计、清理、持久化 |
| `STOP` | Agent 停止 | 优雅关闭、资源释放 |
| `NOTIFICATION` | 后台任务完成 | 推送通知、更新状态 |
| `PRE_COMPACT` | 上下文压缩前 | 提取关键信息 |
| `POST_COMPACT` | 上下文压缩后 | 校验摘要完整性 |

### 阻塞机制

PreToolUse hook 的 handler 返回 `allow=False` 即可阻止工具执行——这就是 s19 权限系统的底层实现。

---

## 试一下

```sh
python s20_hooks/code.py
```

观察安全命令通过、危险命令被 hook 拦截、session 统计日志。

<!-- translation-sync: zh@v1 -->
