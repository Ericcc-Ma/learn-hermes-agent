# s14: Gateway — 多平台消息网关

[中文](README.md) · [English](README.en.md)

s01 → ... → s13 → `s14` → [s15](../s15_profiles/) → ... → s18
> *"一个 gateway，连接所有平台"* — 多平台消息路由 + delivery 分发 + session 管理 + cron ticker。
>
> **Hermes 特性**: Gateway — agent 的多平台统一入口。

---

## 问题

s13 的 cron 任务执行完了——结果发给谁？用户可能在 Telegram 上，也可能在 Discord、Slack、微信上。

每个平台的消息格式、发送方式、认证机制都不一样。需要一个统一的消息网关来适配所有平台。

---

## 解决方案

**Gateway 架构**：三层设计，平台无关。

### 1. 平台适配层 (Platform Adapters)

每个平台一个 Adapter，实现 `send()` 和 `receive()` 两个方法：

| 平台 | Adapter | 通信方式 |
|------|---------|---------|
| CLI | `CLIAdapter` | stdin/stdout |
| Telegram | `TelegramAdapter` | Bot API / 长轮询 |
| Discord | `DiscordAdapter` | WebSocket |
| Slack | `SlackAdapter` | WebSocket / Events API |
| Cron | `CronAdapter` | 文件输出 |
| API | `ApiServerAdapter` | HTTP REST |

### 2. 消息标准化

所有平台的消息统一为 `GatewayMessage`：

```python
@dataclass
class GatewayMessage:
    platform: Platform      # CLI / Telegram / Discord / ...
    channel_id: str         # 来源频道
    user_id: str            # 发送者
    text: str               # 消息内容
    message_id: str         # 平台消息 ID（用于回复）
```

### 3. Delivery 路由

Agent 回复通过 `DeliveryRouter` 路由回正确的平台：

```python
router.deliver(platform, channel_id, response_text, reply_to=msg_id)
```

---

## Gateway 还管什么

### Session 管理

跨平台保持对话连续性——同一个用户在 Telegram 上说了 A，在 Discord 上继续聊 B，gateway 按 `platform:channel:user` 维护独立 session。

### Cron Ticker

Gateway 启动时自动拉起 cron ticker 后台线程（s13 的内容），定时任务的结果通过 delivery 路由分发给对应平台。

### 动态上下文注入

每条消息注入来源信息，让 agent 知道"这条消息是谁、从哪个平台来的"：

```xml
<gateway-context>
Platform: telegram
Channel: private-chat-123
User: @johndoe
</gateway-context>
```

---

## 试一下

```sh
python s14_gateway/code.py
```

1. `/send Hello from CLI` — 模拟 CLI 消息
2. `/telegram` — 注册 Telegram adapter
3. `/status` — 查看 gateway 状态

---

## 接下来

Gateway 连接了多平台。但不同用户可能需要不同的配置——不同的模型、不同的 skill 集合、不同的权限。

s15 Profiles → 多 profile 隔离 + 独立 gateway 实例 + 配置继承。

<!-- translation-sync: zh@v1 -->
