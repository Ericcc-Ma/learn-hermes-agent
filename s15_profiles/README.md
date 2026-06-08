# s15: Multi-Profile System — 一套代码，多套配置

[中文](README.md) · [English](README.en.md)

s01 → ... → s14 → `s15` → [s16](../s16_agent_teams/) → ... → s18
> *"一套 Hermes，多个人设"* — 独立 profile 隔离模型、技能、平台、权限，支持继承。
>
> **Hermes 特性**: Profile 系统 — 同一个 agent 实例按场景切换不同配置。

---

## 问题

一个 Hermes 实例可能被多种场景共用：
- 工作时用公司模型 + 代码审查技能 + Slack 平台
- 个人时用便宜模型 + 智能家居技能 + Telegram 平台
- Cron 任务用轻量模型 + 仅必要的工具

如果只有一个全局配置，每次切换场景都得手动改——模型、system prompt、工具列表、平台绑定……繁琐且容易出错。

---

## 解决方案

**Profile Manager** — 每个 profile 是一个独立的配置单元，支持继承。

### Profile 配置结构

```python
@dataclass
class ProfileConfig:
    name: str                 # profile 名称
    model: str                # 覆盖全局 model
    system_prompt: str        # 自定义 system prompt
    skills: list[str]         # 启用的技能
    disabled_toolsets: list[str]  # 禁用的工具集
    platforms: list[str]      # 绑定的平台
    gateway_enabled: bool     # 是否启动独立 gateway
    parent: str               # 继承自哪个 profile
```

### 典型用法

```python
# 工作 profile
manager.create("work",
    model="claude-opus-4-8",
    skills=["code-review", "deploy-checklist"],
    disabled_toolsets=["social_media"],
    platforms=["slack", "api_server"],
)

# 个人 profile — 继承 work 的限制
manager.create("personal",
    model="deepseek-chat",
    skills=["home-automation"],
    parent="work",
    platforms=["telegram", "discord"],
)

# Cron 专用 profile
manager.create("cron-worker",
    model="claude-haiku-4-5",
    disabled_toolsets=["messaging", "clarify", "cronjob"],
    gateway_enabled=False,
)
```

### 继承链

```
default ──► work ──► personal
             │           │
             │           └─ model=deepseek-chat (覆盖)
             │              skills += [home-automation]
             │              platforms = [telegram, discord]
             │
             └─ model=opus, skills=[code-review, ...]
                disabled=[social_media], platforms=[slack]
```

子 profile 的字段覆盖父 profile，没指定的字段自动继承。

---

## 试一下

```sh
python s15_profiles/code.py
```

1. `/list` — 查看所有 profile
2. `/switch personal` — 切换到个人 profile
3. `/active` — 查看当前配置详情

---

## 接下来

一个 agent 搞不定的任务怎么办？拆成多个 agent 协作。Hermes 支持 spawn 子 agent、团队邮箱通信、自主认领任务。

s16 Agent Teams → 子 agent 派生 + 团队协作 + 任务板自组织。

<!-- translation-sync: zh@v1 -->
