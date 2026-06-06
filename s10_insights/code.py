"""
s10: Insights — 用量分析与自省

Token/成本追踪 + 工具模式分析 + 活动趋势。
从 SQLite 数据库分析历史会话，生成量化报告。

Usage:
    python s10_insights/code.py
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta

from llm import get_client
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

DB_PATH = ".hermes/state.db"

# ── Pricing (USD per 1M tokens) ──────────────────────

MODEL_PRICING = {
    # Anthropic (USD per 1M tokens)
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-8": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
    # DeepSeek (CNY → USD approx, per 1M tokens)
    "deepseek-chat": {"input": 0.27, "output": 1.10, "cache_read": 0.07, "cache_write": 0.27},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19, "cache_read": 0.14, "cache_write": 0.55},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.0, "cache_read": 1.25, "cache_write": 2.50},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_read": 0.075, "cache_write": 0.15},
}

# ── Database ──────────────────────────────────────────

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            model TEXT NOT NULL,
            turn_count INTEGER DEFAULT 0,
            tool_calls INTEGER DEFAULT 0,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            cache_write_tokens INTEGER DEFAULT 0,
            interrupted INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tool_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            tool_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            duration_ms INTEGER DEFAULT 0,
            success INTEGER DEFAULT 1,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS memory_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            event_type TEXT NOT NULL,  -- extract, consolidate, load
            created_at TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)
    conn.commit()
    return conn

# ── Insights Engine ───────────────────────────────────

class InsightsEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def token_breakdown(self, days: int = 30) -> dict:
        conn = self._connect()
        rows = conn.execute("""
            SELECT
                date(started_at) as day,
                COUNT(*) as sessions,
                SUM(input_tokens) as input_tk,
                SUM(output_tokens) as output_tk,
                SUM(cache_read_tokens) as cache_read_tk,
                SUM(cache_write_tokens) as cache_write_tk
            FROM sessions
            WHERE started_at >= date('now', ? || ' days')
            GROUP BY day ORDER BY day
        """, (f"-{days}",)).fetchall()
        conn.close()
        return [dict(zip(["day", "sessions", "input_tk", "output_tk", "cache_read_tk", "cache_write_tk"], r)) for r in rows]

    def cost_estimate(self, days: int = 30) -> dict:
        conn = self._connect()
        rows = conn.execute("""
            SELECT model, SUM(input_tokens) as input_tk, SUM(output_tokens) as output_tk,
                   SUM(cache_read_tokens) as cache_read, SUM(cache_write_tokens) as cache_write
            FROM sessions WHERE started_at >= date('now', ? || ' days')
            GROUP BY model
        """, (f"-{days}",)).fetchall()
        conn.close()

        total_cost = 0.0
        model_costs = {}
        for model, inp, out, cr, cw in rows:
            pricing = MODEL_PRICING.get(model, MODEL_PRICING.get("claude-sonnet-4-6", {}))
            cost = (
                (inp or 0) * pricing.get("input", 0) / 1_000_000 +
                (out or 0) * pricing.get("output", 0) / 1_000_000 +
                (cr or 0) * pricing.get("cache_read", 0) / 1_000_000 +
                (cw or 0) * pricing.get("cache_write", 0) / 1_000_000
            )
            model_costs[model] = round(cost, 4)
            total_cost += cost
        return {"by_model": model_costs, "total_usd": round(total_cost, 4)}

    def tool_usage_ranking(self, days: int = 30, top_n: int = 10) -> list:
        conn = self._connect()
        rows = conn.execute("""
            SELECT tool_name, COUNT(*) as calls,
                   AVG(duration_ms) as avg_ms
            FROM tool_events
            WHERE created_at >= date('now', ? || ' days')
            GROUP BY tool_name ORDER BY calls DESC LIMIT ?
        """, (f"-{days}", top_n)).fetchall()
        conn.close()
        return [{"tool": r[0], "calls": r[1], "avg_ms": round(r[2], 1) if r[2] else 0} for r in rows]

    def session_metrics(self, days: int = 30) -> dict:
        conn = self._connect()
        row = conn.execute("""
            SELECT COUNT(*) as total, AVG(turn_count) as avg_turns,
                   AVG(tool_calls) as avg_tools, SUM(interrupted) as interrupted
            FROM sessions WHERE started_at >= date('now', ? || ' days')
        """, (f"-{days}",)).fetchone()
        conn.close()
        return {"total_sessions": row[0] or 0, "avg_turns": round(row[1] or 0, 1),
                "avg_tool_calls": round(row[2] or 0, 1), "interrupted": row[3] or 0}

    def memory_activity(self, days: int = 30) -> list:
        conn = self._connect()
        rows = conn.execute("""
            SELECT date(created_at) as day, event_type, SUM(count) as total
            FROM memory_events WHERE created_at >= date('now', ? || ' days')
            GROUP BY day, event_type ORDER BY day
        """, (f"-{days}",)).fetchall()
        conn.close()
        return [{"day": r[0], "type": r[1], "count": r[2]} for r in rows]


# ── Session Tracker ───────────────────────────────────

class SessionTracker:
    def __init__(self, conn):
        self.conn = conn
        self.session_id = None
        self.turn_count = 0
        self.tool_calls = 0
        self.start_time = None

    def start_session(self):
        self.start_time = datetime.now()
        cur = self.conn.execute(
            "INSERT INTO sessions (started_at, model) VALUES (?, ?)",
            (self.start_time.isoformat(), MODEL)
        )
        self.session_id = cur.lastrowid
        self.turn_count = 0
        self.tool_calls = 0

    def record_turn(self):
        self.turn_count += 1

    def record_tool(self, tool_name: str, duration_ms: float = 0, success: bool = True):
        self.tool_calls += 1
        self.conn.execute(
            "INSERT INTO tool_events (session_id, tool_name, created_at, duration_ms, success) VALUES (?, ?, ?, ?, ?)",
            (self.session_id, tool_name, datetime.now().isoformat(), int(duration_ms), int(success))
        )

    def record_memory_event(self, event_type: str, count: int):
        self.conn.execute(
            "INSERT INTO memory_events (session_id, event_type, created_at, count) VALUES (?, ?, ?, ?)",
            (self.session_id, event_type, datetime.now().isoformat(), count)
        )

    def end_session(self, interrupted: bool = False):
        if self.session_id:
            self.conn.execute(
                "UPDATE sessions SET ended_at=?, turn_count=?, tool_calls=?, interrupted=? WHERE id=?",
                (datetime.now().isoformat(), self.turn_count, self.tool_calls, int(interrupted), self.session_id)
            )
        self.conn.commit()


# ── Main ──────────────────────────────────────────────

def main():
    conn = init_db()
    engine = InsightsEngine()
    tracker = SessionTracker(conn)

    print("=" * 60)
    print("s10: Insights — 用量分析与自省")
    print("=" * 60)
    print()
    print("/insights        — 最近 30 天报告")
    print("/insights 7      — 最近 7 天报告")
    print("/tools           — 工具使用排行")
    print("/cost            — 成本估算")
    print("/simulate-data   — 生成模拟数据")
    print("/exit            — 退出")
    print()

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!"); break
        if not query: continue
        if query == "/exit": break

        elif query.startswith("/insights"):
            days = int(query.split()[-1]) if len(query.split()) > 1 else 30
            print(f"\n  📊 Insights (last {days} days)")
            print(f"  {'─' * 40}")
            metrics = engine.session_metrics(days)
            print(f"  Sessions: {metrics['total_sessions']} (avg {metrics['avg_turns']} turns, {metrics['avg_tool_calls']} tools)")
            print(f"  Interrupted: {metrics['interrupted']}")
            cost = engine.cost_estimate(days)
            print(f"  Cost: ${cost['total_usd']:.4f}")
            for model, c in cost['by_model'].items():
                print(f"    - {model}: ${c:.4f}")
            print(f"  Token breakdown:")
            for row in engine.token_breakdown(days):
                total_tk = (row.get('input_tk', 0) or 0) + (row.get('output_tk', 0) or 0)
                print(f"    {row['day']}: {total_tk:,} tokens ({row['sessions']} sessions)")
            print()

        elif query == "/tools":
            print("\n  🔧 Tool Usage Ranking (30d)")
            for r in engine.tool_usage_ranking(30, 10):
                bar = "█" * min(r['calls'], 40)
                print(f"  {r['tool']:20s} {r['calls']:4d} {bar}")
            print()

        elif query == "/cost":
            cost = engine.cost_estimate(30)
            print(f"\n  💰 Cost Estimate (30d)")
            print(f"  Total: ${cost['total_usd']:.4f}")
            for model, c in cost['by_model'].items():
                print(f"  {model}: ${c:.4f}")
            print()

        elif query == "/simulate-data":
            print("  Generating sample data...")
            tracker.start_session()
            for i in range(5):
                tracker.record_turn()
                tracker.record_tool("bash", duration_ms=100 + i * 20)
                if i % 2 == 0:
                    tracker.record_tool("load_skill", duration_ms=50)
            tracker.record_memory_event("extract", 2)
            tracker.record_memory_event("consolidate", 1)
            tracker.end_session()
            print("  Done! Try /insights now.")
        else:
            print(f"  Unknown: {query}")
        print()


if __name__ == "__main__":
    main()
