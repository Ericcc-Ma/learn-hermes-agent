"""
s13: Cron Scheduler — 让 agent 在指定时间自动醒来

Hermes 的定时任务系统: JSON 文件落盘 + gateway ticker 调度 + delivery 分发。
任务定义持久化到 ~/.hermes/cron/jobs.json，gateway 每 60s tick 一次。

Usage:
    python s13_cron_scheduler/code.py
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

CRON_DIR = Path(".hermes") / "cron"
JOBS_FILE = CRON_DIR / "jobs.json"
OUTPUT_DIR = CRON_DIR / "output"
TICK_INTERVAL = 60  # 秒


# ── Cron Job Schema ────────────────────────────────────

def new_job(
    prompt: str,
    schedule: str,       # cron 表达式: "0 9 * * *"
    name: str = "",
    recurring: bool = True,
    profile: str = "",
) -> dict:
    """创建一个定时任务"""
    now = datetime.now().isoformat()
    return {
        "id": str(uuid.uuid4())[:8],
        "name": name or prompt[:50],
        "prompt": prompt,
        "schedule": schedule,
        "recurring": recurring,
        "profile": profile or "default",
        "created_at": now,
        "last_run_at": None,
        "next_run_at": None,
        "run_count": 0,
        "enabled": True,
        "last_delivery_error": None,
    }


# ── Job Storage (落盘到 jobs.json) ─────────────────────

def load_jobs() -> list[dict]:
    if not JOBS_FILE.exists():
        return []
    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Hermes wraps jobs in {"jobs": [...]}
        if isinstance(data, dict):
            return data.get("jobs", [])
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def save_jobs(jobs: list[dict]):
    CRON_DIR.mkdir(parents=True, exist_ok=True)
    tmp = JOBS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"jobs": jobs, "version": 1}, f, indent=2, ensure_ascii=False)
    tmp.replace(JOBS_FILE)


def create_job(prompt: str, schedule: str, **kwargs) -> dict:
    job = new_job(prompt, schedule, **kwargs)
    jobs = load_jobs()
    jobs.append(job)
    save_jobs(jobs)
    print(f"  [Cron] created job '{job['name']}' ({job['id']})")
    return job


def list_jobs() -> list[dict]:
    return load_jobs()


def remove_job(job_id: str):
    jobs = load_jobs()
    jobs = [j for j in jobs if j["id"] != job_id]
    save_jobs(jobs)
    print(f"  [Cron] removed job {job_id}")


# ── Cron Expression Parser (简化版) ────────────────────

def _next_cron(cron_expr: str, from_time: datetime = None) -> datetime | None:
    """计算 cron 表达式的下一次触发时间。支持简单格式。"""
    if from_time is None:
        from_time = datetime.now()

    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return None

    minute, hour, dom, month, dow = parts

    # 简化: 只处理 "*/N" 和具体数字
    try:
        if minute == "*":
            m = from_time.minute
        elif minute.startswith("*/"):
            interval = int(minute[2:])
            m = ((from_time.minute // interval) + 1) * interval
        else:
            m = int(minute)

        if hour == "*":
            h = from_time.hour
        elif hour.startswith("*/"):
            interval = int(hour[2:])
            h = ((from_time.hour // interval) + 1) * interval
        else:
            h = int(hour)

        next_run = from_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m)
        if next_run <= from_time:
            next_run += timedelta(hours=1)
        return next_run
    except (ValueError, TypeError):
        return None


# ── Job Execution ──────────────────────────────────────

def run_job(job: dict) -> tuple[bool, str]:
    """执行单个 cron 任务 — 启动独立 agent 处理 prompt"""
    job_id = job["id"]
    print(f"\n  ⏰ [Cron] running job '{job.get('name', job_id)}'...")

    # 保存输出
    run_dir = OUTPUT_DIR / job_id
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        messages = [{"role": "user", "content": f"[Cron job: {job.get('name', '')}]\n\n{job['prompt']}"}]

        response = CLIENT.messages.create(
            model=MODEL,
            system="You are a cron agent. Execute the scheduled task.",
            messages=messages,
            max_tokens=2000,
        )
        text = response.content[0].get("text", "") if response.content else ""

        # 保存输出
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        (run_dir / f"{ts}.md").write_text(f"# {job.get('name')}\n\n{text}", encoding="utf-8")

        print(f"  ✅ [Cron] job '{job_id}' completed")
        return True, text
    except Exception as e:
        error_msg = f"Cron job failed: {e}"
        print(f"  ❌ [Cron] {error_msg}")
        return False, error_msg


# ── Ticker (模拟 gateway 每 60s tick) ──────────────────

def tick(verbose: bool = True, sync: bool = True) -> int:
    """检查并执行到期任务。返回执行的任务数。"""
    jobs = load_jobs()
    now = datetime.now()
    due = []

    for job in jobs:
        if not job.get("enabled", True):
            continue
        schedule = job.get("schedule", "")
        if not schedule:
            continue

        next_run_str = job.get("next_run_at")
        if next_run_str:
            try:
                next_run = datetime.fromisoformat(next_run_str)
            except (ValueError, TypeError):
                next_run = _next_cron(schedule, now)
        else:
            next_run = _next_cron(schedule, now)

        if next_run is None:
            continue

        # 首次或需要更新 next_run_at
        if next_run_str is None:
            job["next_run_at"] = next_run.isoformat()
            save_jobs(jobs)

        if next_run <= now:
            due.append(job)

    if verbose and not due:
        print(f"  [Cron tick {now.strftime('%H:%M:%S')}] no jobs due")

    for job in due:
        success, output = run_job(job)
        job["last_run_at"] = now.isoformat()
        job["run_count"] = job.get("run_count", 0) + 1

        if job.get("recurring", True):
            job["next_run_at"] = _next_cron(job["schedule"], now).isoformat()
        else:
            job["enabled"] = False  # 一次性任务执行后禁用

    if due:
        save_jobs(jobs)

    return len(due)


def start_ticker(interval: int = TICK_INTERVAL):
    """启动后台 ticker 线程（模拟 gateway 行为）"""
    stop = threading.Event()

    def _loop():
        print(f"  [Cron ticker] started (interval={interval}s)")
        while not stop.is_set():
            tick(verbose=True)
            stop.wait(interval)

    t = threading.Thread(target=_loop, daemon=True, name="cron-ticker")
    t.start()
    return stop


# ── Tools ─────────────────────────────────────────────

CRON_TOOL = {
    "name": "cron_create",
    "description": "Schedule a recurring task. Use cron syntax: '0 9 * * *' = 9am daily.",
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "What to do at each trigger"},
            "schedule": {"type": "string", "description": "Cron expression: minute hour dom month dow"},
            "name": {"type": "string", "description": "Short name for this job"},
            "recurring": {"type": "boolean", "default": True},
        },
        "required": ["prompt", "schedule"],
    },
}

BASH_TOOL = {
    "name": "bash", "description": "Execute shell command.",
    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
}

TOOLS = [BASH_TOOL, CRON_TOOL]


def run_bash(command: str) -> str:
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=os.getcwd())
        return r.stdout or "(no output)"
    except Exception as e:
        return f"Error: {e}"


def cron_handler(prompt: str, schedule: str, name: str = "", recurring: bool = True) -> str:
    job = create_job(prompt, schedule, name=name, recurring=recurring)
    return f"Cron job created: {job['id']} — schedule: {schedule}"


TOOL_HANDLERS = {"bash": run_bash, "cron_create": cron_handler}


# ── Agent Loop ────────────────────────────────────────

def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def execute_tools(content) -> list:
    results = []
    for block in content:
        name, input_data, block_id = None, None, None
        if hasattr(block, "type") and block.type == "tool_use":
            name, input_data, block_id = block.name, block.input, block.id
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            name, input_data, block_id = block["name"], block["input"], block["id"]
        if name and name in TOOL_HANDLERS:
            output = TOOL_HANDLERS[name](**(input_data or {}))
            results.append({"type": "tool_result", "tool_use_id": block_id, "content": str(output)})
    return results


def agent_loop(query: str, client, messages=None):
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": query})

    while True:
        response = client.messages.create(
            model=MODEL,
            system="You are a coding agent. Use cron_create to schedule recurring tasks.",
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return response

        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})


# ── Main ──────────────────────────────────────────────

def main():
    # 初始化一些示例任务
    existing = load_jobs()
    if not existing:
        create_job("Summarize today's activity", "0 9 * * *", name="Daily Summary")
        create_job("Check for security updates", "0 */6 * * *", name="Security Check")

    print("=" * 60)
    print("s13: Cron Scheduler — 定时任务系统")
    print("=" * 60)
    print(f"Jobs file: {JOBS_FILE}")
    print(f"Existing jobs: {len(load_jobs())}")
    print()
    print("/jobs    — 列出所有定时任务")
    print("/tick    — 手动触发一次 tick")
    print("/create  — 创建新任务")
    print("/ticker  — 启动后台 ticker（模拟 gateway）")
    print("/exit    — 退出")
    print()

    messages = []
    ticker_stop = None

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query == "/exit":
            if ticker_stop:
                ticker_stop.set()
            break
        if query == "/jobs":
            for j in load_jobs():
                status = "✅" if j.get("enabled") else "⏸️"
                rec = "🔄" if j.get("recurring") else "1️⃣"
                print(f"  {status} {rec} [{j['id']}] {j.get('name')} — {j.get('schedule')}")
            print()
            continue
        if query == "/tick":
            tick()
            print()
            continue
        if query == "/ticker":
            ticker_stop = start_ticker(15)  # 15s for demo
            continue
        if query.startswith("/create "):
            parts = query.split(maxsplit=1)[1].split("|")
            if len(parts) >= 2:
                create_job(parts[1].strip(), parts[0].strip())
            print()
            continue

        response = agent_loop(query, CLIENT, messages)
        print(extract_text(response.content))
        print()


if __name__ == "__main__":
    main()
