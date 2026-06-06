# s07: Curator — 自动状态转换

[中文](README.md) · [English](README.en.md)

s01 → ... → s06 → `s07` → [s08](../s08_curator_llm/) → ... → s12
> *"30 天不用就标记，90 天归档，规则说了算"* — 纯规则自动状态转换，零 LLM 成本。
>
> **自进化层**: 长期维护（Curator）— 阶段 1：规则驱动的技能库维护。

---

## 问题

s03 让 agent 自动创建技能，s05 定义了生命周期状态。但状态转换需要手动触发——用户得记得运行 `/curator`。一个月后 `.skills/` 膨胀到 50+ 技能，大部分是僵尸。

**需要自动化的定期维护。但技能转换规则是确定性的（30 天不用 → stale，90 天 → archived），不需要 LLM。**

---

## 解决方案

**Curator 两阶段执行。阶段 1：纯规则自动转换（零 LLM 成本）。**

### 触发机制

不是 cron 守护进程，而是**空闲触发**：

```python
class CuratorScheduler:
    interval_hours = 168      # 7 天
    min_idle_hours = 2        # agent 空闲 ≥ 2 小时

    def should_run(self) -> bool:
        hours_since_last = (now() - self.last_run_at).total_seconds() / 3600
        if hours_since_last < self.interval_hours:
            return False
        if idle_time() < self.min_idle_hours:
            return False
        return True
```

### 自动状态转换（纯规则）

```python
def apply_automatic_transitions(skills: dict, config: CuratorConfig):
    for name, skill in skills.items():
        # 1. Pinned 技能：永不触碰
        if skill.pinned:
            continue

        # 2. Bundled/Hub 技能：默认不触碰
        if skill.source in ("bundled", "hub") and not config.prune_builtins:
            continue

        days_inactive = (now() - skill.last_activity_at).days

        # 3. Active → Stale (30d 未使用)
        if skill.state == "active" and days_inactive >= config.stale_after_days:
            skill.state = "stale"

        # 4. Stale → Archived (90d 未使用)
        elif skill.state == "stale" and days_inactive >= config.archive_after_days:
            skill.state = "archived"
            move_to_archive(skill)

        # 5. Stale → Active (被重新使用)
        elif skill.state == "stale" and days_inactive < config.stale_after_days:
            skill.state = "active"  # 自动重新激活
```

### CLI 控制

```bash
hermes curator status              # 查看状态
hermes curator run                 # 立即触发
hermes curator run --dry-run       # 预览模式
hermes curator pause               # 暂停
hermes curator resume              # 恢复
hermes curator pin <skill>         # 固定技能
hermes curator unpin <skill>       # 取消固定
hermes curator restore <skill>     # 恢复已归档技能
```

---

## 相对 s06 的变更

| 组件 | s06 | s07 |
|------|-----|-----|
| Curator | 无 | 阶段 1 规则引擎 + 调度器 |
| 触发 | 手动 nudge | 空闲触发 + 手动 trigger |
| LLM 成本 | 技能审查用 LLM | 自动转换零 LLM 成本 |
| 用户控制 | 无 | status/pause/resume/pin/dry-run |

---

## 试一下

```sh
python s07_curator_state/code.py
```

1. `/create test-skill` → 创建测试技能
2. `/simulate-time 35` → 模拟 35 天后
3. `/curator` → 观察 stale 转换
4. `/simulate-time 100` → 再模拟 100 天
5. `/curator` → 观察 archive
6. `/pin important-skill` → 固定 → 模拟时间 → 观察豁免

---

## 接下来

Curator 阶段 1 是纯规则的，零 LLM 成本。但技能越来越多之后，即使都 active，也会出现功能重叠、破碎分散的问题。需要 LLM 来智能合并。

s08 Curator: LLM Review → 前缀聚类 + 伞形合并 + 降级 + 报告生成。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/curator.py:268-323`** — `apply_automatic_transitions()` 方法，Curator 阶段 1 的完整实现。生产版在此处执行纯规则驱动的状态转换，零 LLM 成本。遍历所有 agent 创建的技能，检查：(1) 是否为 pinned 状态（跳过），(2) 来源是否为 bundled/hub（默认跳过，除非启用 `prune_builtins`），(3) 根据 `last_activity_at` 和配置的 `stale_after_days`（30 天）/ `archive_after_days`（90 天）自动标记 stale/archived，(4) 检测 stale 技能是否被重新激活。
- **`agent/curator.py`（空闲触发机制）** — 生产版的 Curator 不是 cron 守护进程，而是**空闲触发**机制：距上次运行 ≥ `interval_hours`（默认 168 小时 = 7 天）且 agent 空闲 ≥ `min_idle_hours`（默认 2 小时）。首次安装后不会立即运行——先播种 `last_run_at` 时间戳，等一个完整周期。支持 dry-run 预览模式（`--dry-run`）不实际修改文件。

**教学版简化了什么**：
- 生产版的空闲检测需要监控 agent 活动状态（是否有正在进行的对话），教学版简化为手动 `/curator` 触发
- 生产版有完整的 CLI 命令体系（`status`/`run`/`pause`/`resume`/`pin`/`unpin`/`restore`/`backup`/`rollback`），教学版用 `/` 命令模拟
- 生产版的配置通过 `~/.hermes/config.yaml` 管理（`curator.enabled`/`interval_hours`/`min_idle_hours`/`stale_after_days` 等），教学版用代码内常量
- 生产版支持快照备份和回滚（每次运行前自动快照），教学版无此机制

</details>

<!-- translation-sync: zh@v1 -->
