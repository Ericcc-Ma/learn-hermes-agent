# s10: Insights — Usage Analytics & Introspection

[中文](README.md) · [English](README.en.md)

s01 → ... → s09 → `s10` → [s11](../s11_error_recovery/) → s12
> *"You don't know how many tokens you're using? How can you optimize?"* — Token/cost tracking + tool usage patterns + activity trends.
>
> **Self-Evolution Layer**: Data Analytics — quantify self-evolution effectiveness, guide optimization.

---

## Problem

An agent runs hundreds of conversations. But:
- How much did it cost? Unknown.
- Which tools consume the most time? Unknown.
- Did self-evolution improve efficiency? Unknown.
- Are skills loaded on demand or stuffed into system prompt? Unknown.

**Without quantification, there is no optimization. Self-evolution needs data feedback.**

---

## Solution

**Insights Engine**: analyze historical sessions from an SQLite state database, generating quantitative reports.

### Analysis Dimensions

| Dimension | What's Tracked |
|-----------|---------------|
| **Token Consumption** | Input / output / cache read / cache write |
| **Cost Estimates** | Per model, per provider breakdown |
| **Tool Usage** | Most-used tools, tool combinations |
| **Activity Trends** | Daily / weekly / monthly activity |
| **Session Metrics** | Session duration, turns, interruption rate |

### CLI

```bash
hermes insights           # Last 30 days
hermes insights --days 7  # Last 7 days
```

---

## How It Works

```python
class InsightsEngine:
    def token_breakdown(self, days=30):
        return self.db.execute("""
            SELECT date(created_at), SUM(input_tokens), SUM(output_tokens)
            FROM sessions WHERE created_at >= date('now', ?)
            GROUP BY date(created_at)
        """, (f"-{days} days",)).fetchall()

    def tool_usage_ranking(self, days=30, top_n=10):
        return self.db.execute("""
            SELECT tool_name, COUNT(*) as calls
            FROM tool_events WHERE created_at >= date('now', ?)
            GROUP BY tool_name ORDER BY calls DESC LIMIT ?
        """, (f"-{days} days", top_n)).fetchall()

    def cost_estimate(self, days=30):
        # Supports 200+ model pricing
        ...
```

### Pricing Table (Multi-Provider)

Pricing is tracked per model, supporting Anthropic, DeepSeek, OpenAI, and others. The table in `s10_insights/code.py` maps model IDs to per-million-token costs.

---

## Try It

```sh
python s10_insights/code.py
```

Run a few conversations first, then `/insights` to see statistics. Use `/simulate-data` to generate sample data.

---

## Next

Usage analytics let you see the effectiveness of self-evolution. But agents encounter various errors in production — API timeouts, token overflows, malformed responses. Self-healing capability is needed.

s11 Error Recovery → error detection + retry strategies + model fallback + self-healing flow.

<details>
<summary>Deep Dive into Hermes Source</summary>

The Insights engine is implemented in:

| File | Lines | Role |
|------|-------|------|
| `agent/insights.py` | full | Analytics engine, SQLite queries, report generation |

What the teaching version simplifies:
- Production supports 200+ model pricing entries for accurate cost estimation
- Analysis dimensions include: token consumption, cost by model/provider, tool patterns, activity trends, session metrics, platform breakdown (CLI/Telegram/Discord/etc.)
- CLI: `hermes insights --days 7` for weekly reports
- Data comes from a real SQLite state database with session-level granularity
- Cache read/write tokens are tracked separately for prompt cache cost analysis

</details>

<details>
<summary>Deep Dive into Hermes Source</summary>

This section maps to the following source files in the production Hermes codebase:

- **`agent/insights.py`** — The complete Insights analytics engine implementation. In production, this reads historical session records from Hermes' SQLite state database and provides multi-dimensional analysis: (1) **Token consumption**: input/output/cache read/cache write token stats, aggregated by day/week/month; (2) **Cost estimates**: supports 200+ model pricing tables, broken down by model/provider; (3) **Tool usage patterns**: most-used tools ranking, tool combination analysis (e.g., bash+write pair frequency); (4) **Activity trends**: daily/weekly/monthly activity changes; (5) **Model/platform breakdown**: by model (Claude/Gemini/GPT, etc.) and platform (CLI/Telegram/Discord, etc.); (6) **Session metrics**: session duration, turns, interruption rate.
- **CLI commands** — Production triggers via `hermes insights` (default last 30 days, `--days 7` for 7 days), outputting formatted tables and summaries. Production data comes from the SQLite database that Hermes auto-writes after each conversation turn (not manual tracking).

**What the teaching version simplifies**:
- Production uses a full SQLite database (multi-table joins); the teaching version simulates with in-memory counters
- Production supports precise cost estimation for 200+ models (accounting for input/output/cache pricing differences); the teaching version uses simplified model unit prices
- Production can break down stats by platform (CLI/Telegram/Discord, etc.); the teaching version has a single terminal platform
- Production Insights can track self-evolution effectiveness (e.g., skill load count, memory hit rate, token savings from Curator merges); the teaching version tracks only basic metrics

</details>

<!-- translation-sync: zh@v1, en@v1 -->
