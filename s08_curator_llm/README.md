# s08: Curator — LLM 审查与伞形合并

[中文](README.md) · [English](README.en.md)

s01 → ... → s07 → `s08` → [s09](../s09_context_management/) → ... → s12
> *"技能太多会乱，定期合并整理"* — LLM 驱动的前缀聚类 + 伞形合并 + 降级 + 报告生成。
>
> **自进化层**: 长期维护（Curator）— 阶段 2：LLM 智能合并。

---

## 问题

s07 的阶段 1 解决了僵尸技能问题（自动 stale → archive）。但还有另一个问题：技能**碎片化**。

agent 自动创建了 5 个关于 Python 的技能：`python-testing`、`python-linting`、`python-deploy`、`python-style`、`python-packaging`。每个都是独立的技能，每个都要占 system prompt 空间。而且它们之间可能有矛盾或重复。

**需要智能合并——把相关的窄技能整合到伞形技能下。**

---

## 解决方案

**Curator 阶段 2：LLM 审查合并**。Fork 独立 AIAgent（使用可配置的辅助模型），进行前缀聚类和三种合并策略。

### 三种合并策略

| 策略 | 操作 | 适用场景 |
|------|------|---------|
| **a) 合并到已有伞形** | patch 已有技能 + archive 兄妹 | 已有相关伞形技能 |
| **b) 创建新伞形** | 创建类级别技能 + archive 子技能 | 多个窄技能分组到新伞形 |
| **c) 降级为支持文件** | 内容移入 `references/` 或 `templates/` | 太窄，不值得作为独立技能 |

### 前缀聚类

```python
# 按命名前缀聚类
skills = ["python-testing", "python-linting", "python-deploy",
          "react-components", "react-hooks", "git-workflow"]

# 检测到两个聚类:
# Cluster "python": testing, linting, deploy
# Cluster "react": components, hooks

# 操作:
# → 创建 "python-development" 伞形技能，archive 三个子技能
# → 创建 "react-patterns" 伞形技能，archive 两个子技能
```

### LLM 审查 Prompt

```python
CURATOR_REVIEW_PROMPT = """You are a skill library curator.
Review the following skills and suggest mergers.

Rules:
1. ONLY merge agent-created skills (NOT bundled or hub-installed)
2. Can archive but NEVER delete
3. Can create umbrella skills with references/ sub-files
4. Pinned skills are exempt from all changes

Current skills:
{skills_catalog}

Suggest mergers in JSON format:
{{
  "mergers": [
    {{
      "strategy": "merge_to_existing|create_umbrella|demote_to_reference",
      "target": "existing-umbrella-name",
      "skills_to_merge": ["skill-1", "skill-2"],
      "new_umbrella_name": "name (for create_umbrella)",
      "new_umbrella_body": "body (for create_umbrella)",
      "reason": "why this merger"
    }}
  ]
}}
"""
```

### 报告系统

每次 Curator 运行在 `~/.hermes/logs/curator/{YYYYMMDD-HHMMSS}/` 下生成：
- `run.json` — 机器可读的完整记录
- `REPORT.md` — 人类可读的审查报告

---

## 相对 s07 的变更

| 组件 | s07 | s08 |
|------|-----|-----|
| LLM 参与 | 无（纯规则） | 阶段 2 用 LLM 审查合并 |
| 合并能力 | 无 | 前缀聚类 + 三种策略 |
| 辅助模型 | 无 | 可用便宜模型（Haiku/Gemini Flash） |
| 报告 | 纯状态变更日志 | run.json + REPORT.md |
| 安全护栏 | pin 豁免 | pin 豁免 + 不触碰 bundled/hub |

---

## 试一下

```sh
python s08_curator_llm/code.py
```

1. 创建 5-6 个相关技能（如 `python-X`, `python-Y`）
2. `/curator-review` → 触发 LLM 审查
3. 观察前缀聚类和合并建议
4. 查看生成的 `REPORT.md`

---

## 接下来

Curator 让技能库不膨胀。但 agent 对话越来越长时，上下文窗口会满。需要智能压缩。

s09 Context Management → 对话压缩 + 轨迹压缩 + 记忆预取 + 上下文注入格式。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/curator.py:330-491`** — Curator 阶段 2 的完整实现，包括 `CURATOR_REVIEW_PROMPT` 和三种合并策略的执行逻辑。生产版在此处 fork 一个独立的 `AIAgent`（使用可配置的辅助模型，默认 `google/gemini-3-flash-preview` 降低审查成本），向其注入完整的技能目录（包括 SKILL.md body、DESCRIPTION.md、last_activity_at 等元数据），让其进行智能合并分析。
- **三种合并策略的具体实现**：(a) **合并到已有伞形** — 通过 `skill_manage` patch 已有技能，在伞形技能下添加新小节，然后 archive 兄妹技能；(b) **创建新伞形** — 通过 `skill_manage create` 创建新类级别技能，将窄技能的内容整合进去，然后 archive；(c) **降级为支持文件** — 将窄技能的 body 移入现有伞形技能的 `references/`、`templates/` 或 `scripts/` 子目录，不创建新技能。
- **报告系统** — 每次运行在 `~/.hermes/logs/curator/{YYYYMMDD-HHMMSS}/` 下生成 `run.json`（机器可读的完整记录）和 `REPORT.md`（人类可读的审查报告），以及 `cron_rewrites.json`（如果合并导致了 cron 任务中技能引用的变更）。

**教学版简化了什么**：
- 生产版使用可配置的**辅助模型**（auxiliary.curator 配置块），可以用便宜模型降低审查成本；教学版使用主模型
- 生产版的前缀聚类基于技能名称 + `DESCRIPTION.md` 语义分析（而非仅名称前缀），能发现命名不同但功能相似的技能
- 生产版的合并操作涉及真实的 `skill_manage` 工具调用（需要创建/修改/archive 多个文件），教学版是文件级模拟
- 生产版的硬规则包括：只能 archive 不能 delete、不触碰 bundled/hub 技能、不触碰 pinned 技能、自动重写 cron 任务中的技能引用

</details>

<!-- translation-sync: zh@v1 -->
