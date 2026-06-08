"""
s11: Error Recovery — 错误恢复与自愈

重试策略 + 模型降级 + token 升级 + 错误日志→技能转化。
从失败中自愈，并把教训沉淀为可复用知识。

Usage:
    python s11_error_recovery/code.py
"""

import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path

from llm import get_client
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")

# Provider-aware fallback mapping: when primary model fails, fall back to a cheaper/smaller one
_FALLBACK_MAP = {
    # Anthropic
    "claude-sonnet-4-6": "claude-haiku-4-5",
    "claude-opus-4-8": "claude-sonnet-4-6",
    "claude-haiku-4-5": "claude-haiku-4-5",
    # DeepSeek
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-chat",
    # OpenAI
    "gpt-4o": "gpt-4o-mini",
    "gpt-4o-mini": "gpt-4o-mini",
}
FALLBACK_MODEL = _FALLBACK_MAP.get(MODEL, MODEL)
CLIENT = get_client()

SKILLS_DIR = Path(".skills")
MEMORY_DIR = Path(".memory")

# ── Recovery State ────────────────────────────────────

class RecoveryState:
    def __init__(self):
        self.max_output_tokens = 8000
        self.max_output_tokens_override = 0
        self.recovery_count = 0
        self.has_attempted_reactive_compact = False
        self.consecutive_failures = 0
        self.current_model = MODEL
        self.fallback_used = False

    def reset(self):
        self.max_output_tokens = 8000
        self.max_output_tokens_override = 0
        self.has_attempted_reactive_compact = False

    def get_max_tokens(self) -> int:
        if self.max_output_tokens_override:
            return self.max_output_tokens_override
        return self.max_output_tokens


# ── Error Classifier ──────────────────────────────────

def classify_error(error: Exception) -> str:
    """分类错误类型，决定恢复策略"""
    msg = str(error).lower()

    if any(kw in msg for kw in ("overload", "overloaded", "rate limit", "429", "503")):
        return "overloaded"
    if any(kw in msg for kw in ("token", "too long", "context length", "max_tokens")):
        return "token_limit"
    if any(kw in msg for kw in ("timeout", "timed out", "connection")):
        return "timeout"
    if any(kw in msg for kw in ("permission", "denied", "forbidden", "401", "403")):
        return "permission"
    return "unknown"


# ── Recovery Strategies ───────────────────────────────

def retry_with_backoff(fn, max_retries: int = 3, base_delay: float = 1.0):
    """指数退避重试"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_error = e
            error_type = classify_error(e)

            if error_type == "permission":
                raise  # 权限错误不重试

            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"  🔄 [Retry] {error_type}: attempt {attempt + 1}/{max_retries}, waiting {delay:.1f}s")
                time.sleep(delay)
    raise last_error


def handle_token_limit(state: RecoveryState) -> str:
    """Token 超限时的升级策略"""
    if state.max_output_tokens_override == 0:
        state.max_output_tokens_override = 64000
        state.recovery_count += 1
        return "upgraded to 64K output tokens"

    if not state.has_attempted_reactive_compact:
        state.has_attempted_reactive_compact = True
        state.recovery_count += 1
        return "attempting reactive compact"

    # 尝试 fallback 模型
    if not state.fallback_used:
        state.current_model = FALLBACK_MODEL
        state.fallback_used = True
        state.recovery_count += 1
        return f"falling back to {FALLBACK_MODEL}"

    return "all strategies exhausted"


def handle_overloaded(state: RecoveryState) -> str:
    """模型过载时的降级策略"""
    state.consecutive_failures += 1

    if state.consecutive_failures >= 3 and not state.fallback_used:
        state.current_model = FALLBACK_MODEL
        state.fallback_used = True
        return f"switching to {FALLBACK_MODEL} after {state.consecutive_failures} consecutive failures"

    return f"will retry (failure {state.consecutive_failures}/3)"


# ── Error → Skill Learning ────────────────────────────

def learn_from_recovery(error_type: str, strategy: str, context: str):
    """从成功恢复中学习"""
    print(f"  📝 [SelfHeal] Recording recovery pattern: {error_type} → {strategy}")

    # 保存到 recovery log
    log_dir = Path(".hermes") / "logs" / "recovery"
    log_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error_type,
        "strategy": strategy,
        "context_preview": context[:200],
    }
    log_file = log_dir / f"recovery-{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Safe API Call ─────────────────────────────────────

def safe_api_call(client, state: RecoveryState, **kwargs):
    """带自动恢复的 API 调用包装器"""
    max_tokens = state.get_max_tokens()

    def make_call():
        return client.messages.create(**kwargs, max_tokens=max_tokens)

    try:
        return retry_with_backoff(make_call)
    except Exception as e:
        error_type = classify_error(e)
        print(f"  ⚠️ [Error] {error_type}: {str(e)[:200]}")

        if error_type == "token_limit":
            strategy = handle_token_limit(state)
            print(f"  🔧 [Recovery] {strategy}")

            if "falling back" in strategy:
                kwargs["model"] = state.current_model

            learn_from_recovery(error_type, strategy, kwargs.get("messages", [])[-1].get("content", "")[:200])

            # Retry with new settings
            return make_call()

        elif error_type == "overloaded":
            strategy = handle_overloaded(state)
            print(f"  🔧 [Recovery] {strategy}")

            if "switching" in strategy:
                kwargs["model"] = state.current_model
                # Wait and retry
                time.sleep(5)
                return make_call()

            # Retry with backoff
            time.sleep(2 ** state.consecutive_failures)
            return make_call()

        elif error_type == "timeout":
            learn_from_recovery(error_type, "extended_timeout", "")
            kwargs["max_tokens"] = min(state.get_max_tokens(), 4000)
            return retry_with_backoff(make_call, max_retries=5, base_delay=2.0)

        else:
            raise  # Unknown/permission errors bubble up


# ── Tools ─────────────────────────────────────────────

BASH_TOOL = {"name": "bash", "description": "Execute a shell command.",
             "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}

def run_bash(command: str) -> str:
    import subprocess
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=os.getcwd())
        return r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr else "") or "(no output)"
    except subprocess.TimeoutExpired: return "Command timed out"
    except Exception as e: return f"Error: {e}"

TOOL_HANDLERS = {"bash": run_bash}


def extract_text(content) -> str:
    if isinstance(content, str): return content
    parts = []
    for block in content:
        if hasattr(block, "text"): parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text": parts.append(block.get("text", ""))
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


# ── Agent Loop ────────────────────────────────────────

recovery_state = RecoveryState()

def agent_loop(query: str, client, messages=None):
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": query})

    while True:
        try:
            response = safe_api_call(
                client, recovery_state,
                model=recovery_state.current_model,
                system="You are a helpful coding agent.",
                messages=messages,
                tools=[BASH_TOOL],
            )
            # Success — reset consecutive failures
            recovery_state.consecutive_failures = 0

        except Exception as e:
            print(f"  ❌ [Fatal] Unrecoverable error: {e}")
            return None

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return response

        results = execute_tools(response.content)
        messages.append({"role": "user", "content": results})


# ── Main ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("s11: Error Recovery — 错误恢复与自愈")
    print("=" * 60)
    print(f"Primary model: {MODEL}")
    print(f"Fallback model: {FALLBACK_MODEL}")
    print(f"Output tokens: {recovery_state.get_max_tokens()}")
    print()
    print("Agent 会自动处理 overload、token limit、timeout 等错误。")
    print("恢复模式会自动学习，把教训沉淀到日志。")
    print("/status  — 查看恢复状态")
    print("/exit    — 退出")
    print()

    messages = []

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!"); break
        if not query: continue
        if query == "/exit": break
        if query == "/status":
            print(f"  Current model: {recovery_state.current_model}")
            print(f"  Max output: {recovery_state.get_max_tokens()}")
            print(f"  Recovery count: {recovery_state.recovery_count}")
            print(f"  Consecutive failures: {recovery_state.consecutive_failures}")
            print(f"  Fallback used: {recovery_state.fallback_used}")
            print(); continue

        response = agent_loop(query, CLIENT, messages)
        if response:
            print(extract_text(response.content))
        print()


if __name__ == "__main__":
    main()
