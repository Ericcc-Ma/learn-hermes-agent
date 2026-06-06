"""
Unified LLM client — drop-in replacement for anthropic.Anthropic().

Supports: anthropic | deepseek | openai | openai_compat
Usage:
    from llm import get_client
    client = get_client()
    response = client.messages.create(model=..., system=..., messages=..., tools=..., max_tokens=...)

Provider config via env vars:
    LLM_PROVIDER        — anthropic (default) | deepseek | openai | openai_compat
    ANTHROPIC_API_KEY   — for anthropic
    DEEPSEEK_API_KEY    — for deepseek
    OPENAI_API_KEY      — for openai
    LLM_API_KEY         — for openai_compat
    LLM_BASE_URL        — for openai_compat (base URL for OpenAI-compatible endpoint)
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════
# Response wrapper
# ═══════════════════════════════════════════════════════════

@dataclass
class Response:
    """Normalized response matching anthropic.types.Message shape."""
    content: list
    stop_reason: str
    model: str = ""
    usage: Any = None
    id: str = ""


# ═══════════════════════════════════════════════════════════
# Provider presets
# ═══════════════════════════════════════════════════════════

PROVIDER_PRESETS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
}


# ═══════════════════════════════════════════════════════════
# Token estimation (rough: ~4 chars = 1 token)
# ═══════════════════════════════════════════════════════════

def _estimate_tokens(messages: list) -> int:
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total += len(json.dumps(block, ensure_ascii=False)) // 4
        elif isinstance(content, str):
            total += len(content) // 4
    return total


# ═══════════════════════════════════════════════════════════
# Tool schema translation: Anthropic <-> OpenAI
# ═══════════════════════════════════════════════════════════

def _anthropic_tools_to_openai(tools: list) -> list:
    """Convert Anthropic tool definitions to OpenAI format.

    Anthropic:  {"name": "...", "description": "...", "input_schema": {...}}
    OpenAI:     {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
    """
    if not tools:
        return None
    result = []
    for tool in tools:
        schema = tool.get("input_schema", {})
        # OpenAI requires "parameters", not "input_schema"
        params = {
            "type": schema.get("type", "object"),
            "properties": schema.get("properties", {}),
        }
        if "required" in schema:
            params["required"] = schema["required"]

        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": params,
            },
        })
    return result


# ═══════════════════════════════════════════════════════════
# Message translation: Anthropic content blocks -> OpenAI format
# ═══════════════════════════════════════════════════════════

def _anthropic_messages_to_openai(messages: list) -> list:
    """Convert Anthropic-format messages to OpenAI-compatible format.

    Anthropic uses content blocks in messages:
        {"role": "assistant", "content": [{"type": "text", "text": "..."},
                                           {"type": "tool_use", "id": "..", "name": "..", "input": {..}}]}
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "..", "content": ".."}]}

    OpenAI uses:
        {"role": "assistant", "content": "text", "tool_calls": [{"id": "..", "type": "function", "function": {...}}]}
        {"role": "tool", "tool_call_id": "..", "content": ".."}
    """
    result = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        # Simple string content — pass through
        if isinstance(content, str):
            result.append({"role": role, "content": content})
            continue

        # Content is a list of blocks — translate
        if isinstance(content, list):
            text_parts = []
            tool_calls = []
            tool_results = []

            for block in content:
                if not isinstance(block, dict):
                    # SDK object — extract dict
                    if hasattr(block, "type"):
                        block = {"type": block.type, "text": getattr(block, "text", ""),
                                 "name": getattr(block, "name", ""), "input": getattr(block, "input", {}),
                                 "id": getattr(block, "id", ""),
                                 "tool_use_id": getattr(block, "tool_use_id", ""),
                                 "content": getattr(block, "content", "")}
                    else:
                        continue

                btype = block.get("type", "")

                if btype == "text":
                    text_parts.append(str(block.get("text", "")))

                elif btype == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                        },
                    })

                elif btype == "tool_result":
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": block.get("tool_use_id", ""),
                        "content": str(block.get("content", "")),
                    })

            # Build OpenAI-format messages
            if role == "assistant":
                out = {"role": "assistant"}
                if text_parts:
                    out["content"] = "\n".join(text_parts)
                else:
                    out["content"] = None
                if tool_calls:
                    out["tool_calls"] = tool_calls
                result.append(out)

            elif role == "user":
                if tool_results:
                    # In OpenAI format, each tool_result is a separate "tool" role message
                    result.extend(tool_results)
                if text_parts:
                    result.append({"role": "user", "content": "\n".join(text_parts)})
                elif not tool_results:
                    result.append({"role": "user", "content": ""})

            else:
                result.append({"role": role, "content": "\n".join(text_parts) if text_parts else ""})

        else:
            result.append({"role": role, "content": str(content)})

    return result


# ═══════════════════════════════════════════════════════════
# Response normalization: OpenAI -> Anthropic-like
# ═══════════════════════════════════════════════════════════

def _openai_response_to_anthropic(openai_resp) -> Response:
    """Normalize an OpenAI chat completion response to Anthropic-like Response."""
    choice = openai_resp.choices[0]
    message = choice.message
    finish_reason = choice.finish_reason or "stop"

    # Map finish_reason to stop_reason
    stop_reason_map = {
        "stop": "end_turn",
        "tool_calls": "tool_use",
        "length": "max_tokens",
        "content_filter": "end_turn",
    }
    stop_reason = stop_reason_map.get(finish_reason, "end_turn")

    content_blocks = []

    # Text content
    if message.content:
        content_blocks.append({
            "type": "text",
            "text": message.content,
        })

    # Tool calls
    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                tool_input = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                tool_input = {}

            content_blocks.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.function.name,
                "input": tool_input,
            })

    return Response(
        content=content_blocks,
        stop_reason=stop_reason,
        model=openai_resp.model,
        usage=openai_resp.usage,
        id=openai_resp.id,
    )


# ═══════════════════════════════════════════════════════════
# Messages API (unified interface)
# ═══════════════════════════════════════════════════════════

class MessagesAPI:
    """Unified messages.create() matching anthropic.Anthropic().messages.create() signature."""

    def __init__(self, provider: str, api_key: str, base_url: str | None = None):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self._backend = None

    def _get_backend(self):
        if self._backend:
            return self._backend

        if self.provider == "anthropic":
            import anthropic
            self._backend = anthropic.Anthropic(api_key=self.api_key)
        else:
            from openai import OpenAI
            self._backend = OpenAI(api_key=self.api_key, base_url=self.base_url)

        return self._backend

    def create(
        self,
        *,
        model: str,
        messages: list,
        system: str | list = "",
        tools: list | None = None,
        max_tokens: int = 8000,
        temperature: float | None = None,
    ) -> Response:
        backend = self._get_backend()

        if self.provider == "anthropic":
            # — Anthropic native path —
            import anthropic as _anthro
            kwargs: dict = dict(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
            )
            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools
            if temperature is not None:
                kwargs["temperature"] = temperature

            resp = backend.messages.create(**kwargs)
            # Convert anthropic SDK objects to dicts for uniformity
            content = []
            for block in resp.content:
                if hasattr(block, "type"):
                    if block.type == "text":
                        content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": dict(block.input) if block.input else {},
                        })
                elif isinstance(block, dict):
                    content.append(block)
            return Response(
                content=content,
                stop_reason=resp.stop_reason,
                model=resp.model,
                usage=getattr(resp, "usage", None),
                id=getattr(resp, "id", ""),
            )

        else:
            # — OpenAI-compatible path (deepseek, openai, openai_compat, qwen, glm, etc.) —
            # Translate messages from Anthropic content-block format to OpenAI format
            openai_messages = _anthropic_messages_to_openai(messages)

            # System prompt: OpenAI uses a system message, not a keyword
            if system:
                system_text = system if isinstance(system, str) else " ".join(
                    b.get("text", "") for b in system if isinstance(b, dict) and b.get("type") == "text"
                )
                if system_text.strip():
                    openai_messages.insert(0, {"role": "system", "content": system_text})

            # Translate tool schemas
            openai_tools = _anthropic_tools_to_openai(tools) if tools else None

            kwargs: dict = dict(
                model=model,
                messages=openai_messages,
                max_tokens=max_tokens,
            )
            if openai_tools:
                kwargs["tools"] = openai_tools
            if temperature is not None:
                kwargs["temperature"] = temperature

            resp = backend.chat.completions.create(**kwargs)
            return _openai_response_to_anthropic(resp)


# ═══════════════════════════════════════════════════════════
# LLMClient (drop-in for anthropic.Anthropic)
# ═══════════════════════════════════════════════════════════

class LLMClient:
    """Drop-in replacement for anthropic.Anthropic().

    Usage:
        client = LLMClient(provider="deepseek", api_key="sk-...")
        response = client.messages.create(model=..., messages=..., ...)
    """

    def __init__(self, provider: str = "anthropic", api_key: str = "", base_url: str | None = None):
        self.messages = MessagesAPI(provider=provider, api_key=api_key, base_url=base_url)
        self.provider = provider
        self.api_key = api_key


# ═══════════════════════════════════════════════════════════
# Factory function
# ═══════════════════════════════════════════════════════════

def get_client(provider: str | None = None) -> LLMClient:
    """Create an LLM client based on environment configuration.

    Reads LLM_PROVIDER from env (default: anthropic).

    Provider-specific env vars:
        anthropic:    ANTHROPIC_API_KEY
        deepseek:     DEEPSEEK_API_KEY
        openai:       OPENAI_API_KEY
        openai_compat: LLM_API_KEY + LLM_BASE_URL
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        base_url = None

    elif provider in PROVIDER_PRESETS:
        preset = PROVIDER_PRESETS[provider]
        api_key = os.getenv(preset["api_key_env"], "")
        base_url = preset["base_url"]

    elif provider == "openai_compat":
        api_key = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")

    else:
        # Unknown provider — try as openai_compat with LLM_BASE_URL
        api_key = os.getenv("LLM_API_KEY", "")
        base_url = os.getenv("LLM_BASE_URL", "")

    if not api_key:
        print(f"[llm] WARNING: No API key found for provider '{provider}'. "
              f"Set the appropriate env var (e.g. ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, etc.)")

    return LLMClient(provider=provider, api_key=api_key, base_url=base_url)


# ═══════════════════════════════════════════════════════════
# Utility: extract text from response content (shared helper)
# ═══════════════════════════════════════════════════════════

def extract_text(content) -> str:
    """Extract text from response content — handles both SDK objects and dicts."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════
# Utility: execute tools from response content
# ═══════════════════════════════════════════════════════════

def execute_tools(content, handlers: dict) -> list:
    """Execute tool_use blocks and return tool_result dicts.

    Handles both Anthropic SDK objects and plain dicts.
    """
    results = []
    for block in content:
        name = None
        input_data = None
        block_id = None

        if hasattr(block, "type") and block.type == "tool_use":
            name = block.name
            input_data = dict(block.input) if block.input else {}
            block_id = block.id
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            name = block["name"]
            input_data = block.get("input", {})
            block_id = block.get("id", "")

        if name and name in handlers:
            try:
                output = handlers[name](**(input_data or {}))
            except Exception as e:
                output = f"Tool error: {e}"
            results.append({
                "type": "tool_result",
                "tool_use_id": block_id,
                "content": str(output),
            })
    return results
