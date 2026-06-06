# s05: Skill Lifecycle — 技能的生老病死

[中文](README.md) · [English](README.en.md)

s01 → ... → s04 → `s05` → [s06](../s06_skill_creation/) → ... → s12
> *"技能有生老病死"* — active → stale → archived 状态机，pin 豁免，Umbrella 目录结构。
>
> **自进化层**: 技能管理 — 技能的生命周期与组织方式。

---

## 问题

s03 让 agent 能自动创建技能。但技能只会增加，不会减少。一个月后 `.skills/` 下有 50 个技能，大部分是项目早期创建的，早就没人用了。agent 每次启动扫描 50 个技能，100+ token 浪费在没人用的目录上。

技能需要**生命周期**——创建后活跃，长时间不用就降级，最终归档。但不删除——只是移出视线。

---

## 解决方案

**三级状态机** + **Umbrella 目录结构** + **Pin 豁免机制**。

### 状态机

```
active ──(30天未使用)──► stale ──(90天未使用)──► archived
  ▲                         │                        │
  │                         │                        │
  └───(被再次使用)──────────┘                        │
                                                     │
                                          .skills/.archive/
                                          （可恢复，永不删除）
```

| 状态 | 含义 | 在 system prompt 中 | 可被 load_skill 加载 |
|------|------|---------------------|---------------------|
| **active** | 活跃使用中 | ✅ 显示 | ✅ 是 |
| **stale** | 长时间未使用 | ✅ 显示（标记） | ✅ 是 |
| **archived** | 已归档 | ❌ 不显示 | ❌ 需先恢复 |
| **pinned** | 豁免所有自动转换 | ✅ 显示 | ✅ 是 |

### Umbrella 目录结构

```
.skills/<skill-name>/
├── SKILL.md          # 类级别指令（必需）
├── DESCRIPTION.md    # 简短描述（用于技能匹配）
├── references/       # 会话特定细节、领域知识库
│   ├── api-quirks.md
│   └── debug-recipes.md
├── templates/        # 可复制修改的模板文件
│   └── config-template.yaml
├── scripts/          # 可静态重跑的脚本
│   └── verify-setup.sh
└── assets/           # 静态资源
```

目标是少量丰富的**类级别技能**（伞形），而非大量狭窄的一次性条目。一个伞形技能的 `references/` 子文件比五个窄兄妹技能更好。

---

## 工作原理

### 技能元数据

```python
@dataclass
class SkillRecord:
    name: str
    description: str
    state: str              # active | stale | archived | pinned
    source: str             # bundled | hub | agent-created
    last_activity_at: str   # ISO timestamp
    created_at: str
    pinned: bool = False
    path: str = ""
```

### 状态转换逻辑

```python
def apply_automatic_transitions(skills: dict, config: Config):
    now = datetime.now()

    for name, skill in skills.items():
        if skill.pinned:
            continue  # Pinned 技能永不触碰
        if skill.source in ("bundled", "hub"):
            continue  # 内置/hub 技能不自动转换

        days_inactive = (now - parse_ts(skill.last_activity_at)).days

        if skill.state == "active" and days_inactive >= config.stale_after_days:
            skill.state = "stale"
            print(f"  [Curator] {name}: active → stale ({days_inactive}d)")

        elif skill.state == "stale" and days_inactive >= config.archive_after_days:
            skill.state = "archived"
            archive_skill(skill)
            print(f"  [Curator] {name}: stale → archived ({days_inactive}d)")

        elif skill.state == "stale" and days_inactive < config.stale_after_days:
            # 被重新使用了，重新激活
            skill.state = "active"
            print(f"  [Curator] {name}: stale → active (reactivated)")
```

### 使用追踪

```python
def record_skill_activity(name: str, registry: dict):
    """每次技能被加载时更新 last_activity_at"""
    if name in registry:
        registry[name].last_activity_at = datetime.now().isoformat()
        if registry[name].state == "stale":
            registry[name].state = "active"  # 重新激活
```

---

## 试一下

```sh
python s05_skill_lifecycle/code.py
```

试试：
1. 创建几个技能 → `/skills` 查看状态
2. 加载某个技能 → 观察 `last_activity_at` 更新
3. `/simulate-time 35` → 模拟 35 天后 → 观察 stale 转换
4. `/pin <name>` 固定技能 → 模拟时间 → 观察 pin 豁免

---

## 接下来

状态机管好了技能的"生老病死"。但技能创建规则还太粗糙——什么该学、什么不该学，需要明确的安全护栏。

s06 Skill Creation → 信号优先级 + 禁止捕获列表 + 操作优先级策略。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`tools/skill_usage.py`** — 技能使用遥测与生命周期状态管理。生产版在此处追踪每次技能的加载事件，更新 `last_activity_at` 时间戳，这个时间戳是 Curator 判断 stale/archive 的唯一依据。同时负责在技能被重新使用时从 stale 自动恢复到 active。
- **`agent/curator.py`** — Curator 的状态转换逻辑（`apply_automatic_transitions()` 方法，268-323 行）。生产版遍历所有 agent 创建的技能，根据 `last_activity_at` 判断：(1) active 且超过 `stale_after_days`（默认 30 天）→ stale，(2) stale 且超过 `archive_after_days`（默认 90 天）→ archived，(3) stale 但在 30 天内被重新使用 → active。
- **技能目录结构（伞形模式）** — 生产版的每个技能目录包含 `SKILL.md`（类级别指令，必需）、`DESCRIPTION.md`（用于技能匹配的简短描述）、`references/`（会话特定细节/领域知识库）、`templates/`（可复制修改的模板）、`scripts/`（可静态重跑的脚本）、`assets/`（静态资源）。

**教学版简化了什么**：
- 生产版的技能来源分三种（Bundled/Hub-installed/Agent-created），只有 Agent-created 受 Curator 管理；教学版统一为 agent-created
- 生产版的 `pinned` 状态豁免所有自动转换，通过 `hermes curator pin <name>` 设置；教学版用 `/pin` 模拟
- 生产版的 `archived` 技能移到 `.archive/` 目录（`mv` 即可恢复，永不删除）；教学版仅标记状态
- 生产版的技能匹配基于 `DESCRIPTION.md` 的语义匹配而非精确名称匹配；教学版用名称前缀

</details>

<!-- translation-sync: zh@v1 -->
