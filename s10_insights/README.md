# s10: Insights — 用量分析与自省

[中文](README.md) · [English](README.en.md)

s01 → ... → s09 → `s10` → [s11](../s11_error_recovery/) → s12
> *"你不知道自己用了多少 token？那怎么优化"* — Token/成本追踪 + 工具模式分析 + 活动趋势。
>
> **自进化层**: 数据分析 — 量化自进化效果，指导优化方向。

---

## 问题

Agent 运行了几百次对话。但：
- 花了多少钱？不知道。
- 哪些工具最耗时？不知道。
- 自进化后效率是否有提升？不知道。
- 技能是按需加载的吗，还是全塞 system prompt 了？不知道。

**没有量化，就无法优化。自进化需要数据反馈。**

---

## 解决方案

**Insights 引擎**：从 SQLite 状态数据库分析历史会话，生成量化报告。

### 分析维度

| 维度 | 追踪内容 |
|------|---------|
| **Token 消耗** | 输入/输出/cache 读/cache 写 |
| **成本估算** | 按模型/提供商分解 |
| **工具使用** | 最常用工具、工具组合 |
| **活动趋势** | 日/周/月活跃度变化 |
| **会话指标** | 会话时长、轮次、中断率 |

### CLI

```bash
hermes insights           # 最近 30 天
hermes insights --days 7  # 最近 7 天
```

---

## 工作原理

```python
class InsightsEngine:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)

    def token_breakdown(self, days=30):
        """Token 消耗分解"""
        return self.db.execute("""
            SELECT
                date(created_at) as day,
                SUM(input_tokens) as input,
                SUM(output_tokens) as output,
                SUM(cache_read_tokens) as cache_read,
                SUM(cache_write_tokens) as cache_write
            FROM sessions
            WHERE created_at >= date('now', ?)
            GROUP BY day ORDER BY day
        """, (f"-{days} days",)).fetchall()

    def tool_usage_ranking(self, days=30):
        """工具使用排行"""
        return self.db.execute("""
            SELECT tool_name, COUNT(*) as calls
            FROM tool_events
            WHERE created_at >= date('now', ?)
            GROUP BY tool_name ORDER BY calls DESC
        """, (f"-{days} days",)).fetchall()

    def cost_estimate(self, days=30):
        """成本估算（基于模型定价）"""
        # 支持 200+ 模型定价
        ...
```

---

## 试一下

```sh
python s10_insights/code.py
```

1. 运行几次对话后，`/insights` 查看统计

---

## 接下来

用量分析让你看到自进化的成效。但 agent 在实际运行中还会遇到各种错误——API 超时、token 超限、模型返回异常。需要自愈能力。

s11 Error Recovery → 错误检测 + 重试策略 + 模型降级 + 自愈流程。

<details>
<summary>深入 Hermes 源码</summary>

本节对应 Hermes 生产源码中的以下文件：

- **`agent/insights.py`** — Insights 分析引擎的完整实现。生产版从 Hermes 的 SQLite 状态数据库中读取历史会话记录，提供多维度分析：(1) **Token 消耗**：输入/输出/cache 读/cache 写 token 统计，按日/周/月聚合；(2) **成本估算**：支持 200+ 模型定价表，按模型/提供商分解费用；(3) **工具使用模式**：最常用工具排行、工具组合分析（如 bash+write 组合频率）；(4) **活动趋势**：日/周/月活跃度变化；(5) **模型/平台分解**：按模型（Claude/Gemini/GPT 等）、平台（CLI/Telegram/Discord 等）统计；(6) **会话指标**：会话时长、轮次、中断率。
- **CLI 命令** — 生产版通过 `hermes insights` 命令触发（默认最近 30 天，`--days 7` 指定 7 天），输出格式化的表格和摘要。生产版的数据来自 Hermes 在每轮对话后自动写入的 SQLite 数据库（而非手动追踪）。

**教学版简化了什么**：
- 生产版使用了完整的 SQLite 数据库（多表联合查询），教学版使用内存计数器模拟
- 生产版支持 200+ 模型的精确成本估算（包含不同模型的输入/输出/cache 定价差异），教学版用简化的模型单价
- 生产版可以按平台（CLI/Telegram/Discord 等）分解统计，教学版只有一个终端平台
- 生产版的 Insights 能追踪自进化效果（如：技能加载次数、记忆命中率、Curator 合并后的 token 节省量），教学版仅追踪基础指标

</details>

<!-- translation-sync: zh@v1 -->
