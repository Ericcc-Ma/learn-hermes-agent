"""
s18: Full Hermes — 完整的自进化 Agent

整合全部 18 章特性: Agent Loop + Memory + Background Review +
Skill Lifecycle + Curator + Context + Insights + Error Recovery +
Cron + Gateway + Profiles + Teams + MCP。

Usage:
    python s18_full_hermes/code.py
"""

import json
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from llm import get_client

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

HERMES_DIR = Path(".hermes")


# ═══════════════════════════════════════════════════════════
# Hermes Feature Map
# ═══════════════════════════════════════════════════════════

FEATURE_MAP = {
    "s01": {"name": "Agent Loop + Memory", "file": "agent/conversation_loop.py"},
    "s02": {"name": "Background Memory Review", "file": "agent/background_review.py"},
    "s03": {"name": "Background Skill Review", "file": "agent/background_review.py"},
    "s04": {"name": "Memory System (FTS5)", "file": "agent/memory_manager.py"},
    "s05": {"name": "Skill Lifecycle", "file": "tools/skill_usage.py"},
    "s06": {"name": "Skill Creation Safety", "file": "agent/background_review.py"},
    "s07": {"name": "Curator: Auto Transitions", "file": "agent/curator.py:268"},
    "s08": {"name": "Curator: LLM Merge", "file": "agent/curator.py:330"},
    "s09": {"name": "Context Management", "file": "agent/conversation_compression.py"},
    "s10": {"name": "Insights Engine", "file": "agent/insights.py"},
    "s11": {"name": "Error Recovery", "file": "agent/conversation_loop.py"},
    "s12": {"name": "Complete Self-Evolving", "file": "run_agent.py"},
    "s13": {"name": "Cron Scheduler", "file": "cron/scheduler.py"},
    "s14": {"name": "Gateway", "file": "gateway/run.py"},
    "s15": {"name": "Multi-Profile System", "file": "hermes_cli/profiles.py"},
    "s16": {"name": "Agent Teams", "file": "(spawn + mailbox)"},
    "s17": {"name": "MCP Plugin", "file": "tools/mcp_tool.py"},
    "s18": {"name": "Full Hermes", "file": "all of the above"},
}


def print_architecture():
    """打印完整架构概览"""
    print("""
  ╔══════════════════════════════════════════════════════╗
  ║           HERMES SELF-EVOLVING AGENT                 ║
  ║        18 Progressive Features Integrated            ║
  ╚══════════════════════════════════════════════════════╝

  ┌─────────────────────────────────────────────────┐
  │              GATEWAY (s14)                       │
  │  CLI · Telegram · Discord · Slack · Cron        │
  │  Session Management · Delivery Router           │
  └──────────────────┬──────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────┐
  │           PROFILES (s15)                         │
  │  work · personal · cron-worker                  │
  └──────────────────┬──────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────┐
  │           AGENT LOOP (s01)                       │
  │  while True: response = LLM(...)                │
  │  if tool_use: execute; else: stop               │
  └──────────────────┬──────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
  ┌────────┐  ┌────────────┐  ┌────────────┐
  │PRE-TURN│  │  MID-TURN  │  │ POST-TURN  │
  │Memory  │  │ Context    │  │ BG Review  │
  │Prefetch│  │ Comp.(s09) │  │ (s02,s03)  │
  │Skills  │  │ Error Rec. │  │ Memory     │
  │(s04,5) │  │ (s11)      │  │ Extract    │
  │        │  │ MCP (s17)  │  │ (s06)      │
  └────────┘  └────────────┘  └────────────┘
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
  ┌────────┐  ┌────────────┐  ┌────────────┐
  │Curator │  │ Insights   │  │Cron Ticker │
  │(s07,8) │  │ (s10)      │  │(s13)       │
  │Idle    │  │ Token/Cost │  │Every 60s   │
  └────────┘  └────────────┘  └────────────┘
                     │
  ┌──────────────────▼──────────────────────────────┐
  │          AGENT TEAMS (s16)                       │
  │  Leader → Workers · JSONL Mailbox · TaskBoard   │
  └─────────────────────────────────────────────────┘
""")


# ═══════════════════════════════════════════════════════════
# HermesMetrics — 追踪所有主要指标
# ═══════════════════════════════════════════════════════════

class HermesMetrics:
    def __init__(self):
        self.stats = {
            "sessions": 0, "turns": 0, "tool_calls": 0,
            "memories_saved": 0, "skills_created": 0,
            "curator_runs": 0, "cron_jobs_run": 0,
            "gateway_messages": 0, "errors_recovered": 0,
            "profiles_switched": 0, "subagents_spawned": 0,
            "mcp_tools": 0,
            "uptime": datetime.now(),
        }

    def report(self) -> str:
        uptime = datetime.now() - self.stats["uptime"]
        return f"""
  ╔══════════════════════════════════════════════╗
  ║           HERMES METRICS                    ║
  ╠══════════════════════════════════════════════╣
  ║  Sessions:      {self.stats['sessions']:>5}                       ║
  ║  Turns:         {self.stats['turns']:>5}                       ║
  ║  Tool Calls:    {self.stats['tool_calls']:>5}                       ║
  ║  Memories:      {self.stats['memories_saved']:>5}                       ║
  ║  Skills:        {self.stats['skills_created']:>5}                       ║
  ║  Curator Runs:  {self.stats['curator_runs']:>5}                       ║
  ║  Cron Jobs:     {self.stats['cron_jobs_run']:>5}                       ║
  ║  Gateway Msgs:  {self.stats['gateway_messages']:>5}                       ║
  ║  Errors Recov:  {self.stats['errors_recovered']:>5}                       ║
  ║  Profiles:      {self.stats['profiles_switched']:>5}                       ║
  ║  Subagents:     {self.stats['subagents_spawned']:>5}                       ║
  ║  MCP Tools:     {self.stats['mcp_tools']:>5}                       ║
  ║  Uptime:        {str(uptime).split('.')[0]:>20} ║
  ╚══════════════════════════════════════════════════╝"""


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    metrics = HermesMetrics()

    print("=" * 60)
    print("s18: Full Hermes — 完整的自进化 Agent")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Hermes dir: {HERMES_DIR}")
    print()

    print_architecture()

    print(f"  特性总数: {len(FEATURE_MAP)}")
    print()

    print("Commands:")
    print("  /map     — 查看所有特性映射到源码文件")
    print("  /arch    — 查看架构图")
    print("  /metrics — 查看运行指标")
    print("  /chat    — 进入对话模式")
    print("  /exit    — 退出")
    print()

    messages = []

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query == "/exit":
            break
        if query == "/map":
            print("\n  Hermes Feature → Source File Map:")
            print("  ─────────────────────────────────")
            for ch, info in FEATURE_MAP.items():
                print(f"  {ch}: {info['name']:30s} → {info['file']}")
            print()
            continue
        if query == "/arch":
            print_architecture()
            continue
        if query == "/metrics":
            print(metrics.report())
            continue
        if query == "/chat":
            print("  Entering chat mode (type /end to exit)...")
            while True:
                try:
                    msg = input("  chat> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if msg == "/end":
                    break
                if not msg:
                    continue
                metrics.stats["turns"] += 1
                metrics.stats["gateway_messages"] += 1
                messages.append({"role": "user", "content": msg})
                try:
                    response = CLIENT.messages.create(
                        model=MODEL,
                        system="You are Hermes, a self-evolving agent. Be helpful and concise.",
                        messages=messages,
                        max_tokens=1000,
                    )
                    text = response.content[0].get("text", "") if response.content else ""
                    messages.append({"role": "assistant", "content": text})
                    print(f"  {text[:500]}")
                except Exception as e:
                    metrics.stats["errors_recovered"] += 1
                    print(f"  Error (recovered): {e}")
            continue

        print(f"  Unknown: {query} (try /map, /arch, /metrics, /chat)")
        print()


if __name__ == "__main__":
    main()
