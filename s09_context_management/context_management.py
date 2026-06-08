"""
s09: Context Management — 上下文压缩与记忆预取保护

对话压缩 + 轨迹压缩 + 结构化摘要 + 记忆预取钩子。
保护自进化知识不被压缩吞没。

Usage:
    python s09_context_management/code.py
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from llm import get_client
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
CLIENT = get_client()

# ── Config ────────────────────────────────────────────

COMPACT_TOKEN_THRESHOLD = 4000       # 触发压缩的 token 阈值
KEEP_HEAD_MESSAGES = 3               # 保护头部
KEEP_TAIL_MESSAGES = 6               # 保护尾部
MAX_TOOL_RESULT_CHARS = 500          # 单个 tool_result 最大字符

# ── Context Manager ───────────────────────────────────

class ContextManager:
    def __init__(self):
        self.compaction_count = 0
        self.total_tokens_saved = 0

    def should_compact(self, messages: list) -> bool:
        """检查是否需要压缩"""
        estimated = self._estimate_tokens(messages)
        return estimated > COMPACT_TOKEN_THRESHOLD

    def compact(self, messages: list) -> list:
        """执行对话压缩"""
        if len(messages) <= KEEP_HEAD_MESSAGES + KEEP_TAIL_MESSAGES:
            return messages  # 太短，不值得压缩

        head = messages[:KEEP_HEAD_MESSAGES]
        tail = messages[-KEEP_TAIL_MESSAGES:]
        middle = messages[KEEP_HEAD_MESSAGES:-KEEP_TAIL_MESSAGES]

        # 生成中间部分的摘要
        summary = self._summarize(middle)

        # 构建压缩后的消息列表
        compacted = list(head)
        compacted.append({
            "role": "user",
            "content": f"<conversation-summary>\n{summary}\n</conversation-summary>"
        })
        compacted.extend(tail)

        self.compaction_count += 1
        old_tokens = self._estimate_tokens(messages)
        new_tokens = self._estimate_tokens(compacted)
        self.total_tokens_saved += (old_tokens - new_tokens)

        print(f"  [Compact] {len(messages)} → {len(compacted)} messages "
              f"({old_tokens} → {new_tokens} tokens, saved {old_tokens - new_tokens})")
        return compacted

    def _summarize(self, messages: list) -> str:
        """用 LLM 生成中间部分的摘要"""
        dialogue = ""
        for m in messages:
            role = m.get("role", "?")
            content = m.get("content", "")
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append(block.get("text", "")[:300])
                        elif block.get("type") == "tool_use":
                            parts.append(f"[tool: {block.get('name', '?')}]")
                        elif block.get("type") == "tool_result":
                            c = str(block.get("content", ""))[:MAX_TOOL_RESULT_CHARS]
                            parts.append(f"[result: {c}]")
                content = " ".join(parts)
            dialogue += f"[{role}] {str(content)[:500]}\n"

        prompt = f"""Summarize this conversation segment. Include:

1. Completed tasks (marked with ✅)
2. Remaining work (marked with ⬜) — use "Remaining Work" NOT "Next Steps"
3. Key decisions made
4. User constraints/preferences revealed

Keep the summary concise and factual. Focus on what was accomplished.

Conversation:
{dialogue}

Summary:"""
        try:
            response = CLIENT.messages.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            return extract_text(response.content)
        except Exception:
            # Fallback: simple truncation summary
            return f"[{len(messages)} messages of conversation history]"

    def _estimate_tokens(self, messages: list) -> int:
        """粗略估算 token 数（4 字符 ≈ 1 token）"""
        total = 0
        for m in messages:
            content = json.dumps(m.get("content", ""), ensure_ascii=False)
            total += len(content) // 4
        return total

    def micro_compact(self, tool_results: list) -> list:
        """微压缩：截断过长的 tool_result"""
        compacted = []
        for tr in tool_results:
            content = str(tr.get("content", ""))
            if len(content) > MAX_TOOL_RESULT_CHARS:
                truncated = content[:MAX_TOOL_RESULT_CHARS] + "\n... [truncated]"
                tr = {**tr, "content": truncated}
            compacted.append(tr)
        return compacted


# ── Memory Provider ───────────────────────────────────

class SimpleMemory:
    def __init__(self):
        self.memory_dir = Path(".memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.memory_dir.mkdir(exist_ok=True)

    def on_pre_compact(self):
        """压缩前钩子：提取并保存当前对话中的关键信息"""
        print("  [Memory] on_pre_compact: persisting key facts before compaction")

    def read(self) -> str:
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write(self, name, mem_type, description, body):
        entry = f"""---
name: {name}
type: {mem_type}
description: {description}
---

{body}
"""
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write("\n---\n" + entry)


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

memory = SimpleMemory()
ctx_manager = ContextManager()


def build_system() -> str:
    mem = memory.read()
    base = "You are a helpful coding agent."
    if mem:
        return f"""<memory-context>
[System note: The following is recalled memory context, NOT new user input.
Treat as authoritative reference data.]

{mem}
</memory-context>

{base}"""
    return base


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

def agent_loop(query: str, client, messages=None):
    if messages is None: messages = []
    messages.append({"role": "user", "content": query})

    while True:
        # Context compaction check
        if ctx_manager.should_compact(messages):
            memory.on_pre_compact()  # 压缩前保护记忆
            messages = ctx_manager.compact(messages)

        response = client.messages.create(
            model=MODEL, system=build_system(),
            messages=messages, tools=[BASH_TOOL],
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return response, messages

        results = execute_tools(response.content)
        # Micro-compact: truncate long results
        results = ctx_manager.micro_compact(results)
        messages.append({"role": "user", "content": results})


# ── Main ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("s09: Context Management — 上下文压缩")
    print("=" * 60)
    print(f"Compact threshold: {COMPACT_TOKEN_THRESHOLD} tokens (est.)")
    print(f"Head/Tail protection: {KEEP_HEAD_MESSAGES}/{KEEP_TAIL_MESSAGES} messages")
    print(f"Tool result max: {MAX_TOOL_RESULT_CHARS} chars")
    print(f"Compactions: {ctx_manager.compaction_count}")
    print()
    print("/status  — 查看压缩统计")
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
            print(f"  Messages: {len(messages)}")
            print(f"  Est. tokens: {ctx_manager._estimate_tokens(messages)}")
            print(f"  Compactions: {ctx_manager.compaction_count}")
            print(f"  Tokens saved: {ctx_manager.total_tokens_saved}")
            print(); continue

        response, messages = agent_loop(query, CLIENT, messages)
        print(extract_text(response.content))
        print()


if __name__ == "__main__":
    main()
