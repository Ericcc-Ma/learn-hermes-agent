"""
Unit tests for the llm.py module.

Tests cover:
- get_client() factory function with different providers
- anthropic_to_openai_tools conversion
- openai_response_to_anthropic normalization
- extract_text helper (SDK objects and plain dicts)
- execute_tools helper
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ═══════════════════════════════════════════════════════════
# Helpers: fake SDK-style objects for testing
# ═══════════════════════════════════════════════════════════


class FakeTextBlock:
    """Simulates an Anthropic SDK TextBlock."""
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class FakeToolUseBlock:
    """Simulates an Anthropic SDK ToolUseBlock."""
    def __init__(self, tool_id: str, name: str, input_data: dict):
        self.type = "tool_use"
        self.id = tool_id
        self.name = name
        self.input = input_data


class FakeOpenAIChoiceMessage:
    """Simulates an OpenAI chat completion choice message."""
    def __init__(self, content: str = "", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeOpenAIChoice:
    """Simulates an OpenAI chat completion choice."""
    def __init__(self, message: FakeOpenAIChoiceMessage, finish_reason: str = "stop"):
        self.message = message
        self.finish_reason = finish_reason


class FakeOpenAIResponse:
    """Simulates an OpenAI chat completion response."""
    def __init__(self, choices: list, model: str = "gpt-4o", usage=None, resp_id: str = "chatcmpl-abc123"):
        self.choices = choices
        self.model = model
        self.usage = usage
        self.id = resp_id


class FakeToolCallFunction:
    """Simulates an OpenAI tool call function."""
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    """Simulates an OpenAI tool call."""
    def __init__(self, func: FakeToolCallFunction, tc_id: str = "call_abc123"):
        self.id = tc_id
        self.function = func


# ═══════════════════════════════════════════════════════════
# Tests: get_client()
# ═══════════════════════════════════════════════════════════


class TestGetClient:
    """Tests for the get_client() factory function."""

    def test_anthropic_provider_no_key(self):
        """get_client(provider='anthropic') with no API key: warns but returns LLMClient."""
        from llm import get_client, LLMClient

        with patch.dict(os.environ, {}, clear=True):
            client = get_client(provider="anthropic")
            assert isinstance(client, LLMClient)
            assert client.provider == "anthropic"
            assert client.api_key == ""

    def test_anthropic_provider_from_env(self):
        """get_client() reads LLM_PROVIDER from environment."""
        from llm import get_client

        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}, clear=True):
            client = get_client()
            assert client.provider == "anthropic"

    def test_deepseek_provider_no_key(self):
        """get_client(provider='deepseek') with no API key: returns LLMClient with correct base_url."""
        from llm import get_client, LLMClient

        with patch.dict(os.environ, {}, clear=True):
            client = get_client(provider="deepseek")
            assert isinstance(client, LLMClient)
            assert client.provider == "deepseek"
            # base_url should be set on the MessagesAPI
            assert client.messages.base_url == "https://api.deepseek.com"

    def test_deepseek_provider_from_env(self):
        """get_client() reads LLM_PROVIDER='deepseek' from env."""
        from llm import get_client

        with patch.dict(os.environ, {"LLM_PROVIDER": "deepseek"}, clear=True):
            client = get_client()
            assert client.provider == "deepseek"

    def test_openai_provider_no_key(self):
        """get_client(provider='openai') with no API key: returns LLMClient."""
        from llm import get_client, LLMClient

        with patch.dict(os.environ, {}, clear=True):
            client = get_client(provider="openai")
            assert isinstance(client, LLMClient)
            assert client.provider == "openai"
            assert client.messages.base_url == "https://api.openai.com/v1"

    def test_openai_compat_provider(self):
        """get_client(provider='openai_compat') reads LLM_API_KEY and LLM_BASE_URL."""
        from llm import get_client

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai_compat",
            "LLM_API_KEY": "sk-test-compat",
            "LLM_BASE_URL": "https://custom.api.com/v1",
        }, clear=True):
            client = get_client()
            assert client.provider == "openai_compat"
            assert client.api_key == "sk-test-compat"
            assert client.messages.base_url == "https://custom.api.com/v1"

    def test_unknown_provider_falls_back(self):
        """Unknown provider uses LLM_API_KEY and LLM_BASE_URL from env."""
        from llm import get_client

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "some_unknown_provider",
            "LLM_API_KEY": "sk-unknown",
            "LLM_BASE_URL": "http://localhost:8080/v1",
        }, clear=True):
            client = get_client()
            assert client.provider == "some_unknown_provider"
            assert client.api_key == "sk-unknown"
            assert client.messages.base_url == "http://localhost:8080/v1"

    def test_provider_explicit_arg_overrides_env(self):
        """Explicit provider argument overrides LLM_PROVIDER env var."""
        from llm import get_client

        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
            client = get_client(provider="deepseek")
            assert client.provider == "deepseek"

    def test_missing_key_warning(self, capsys):
        """When no API key is set, a warning is printed."""
        from llm import get_client

        with patch.dict(os.environ, {}, clear=True):
            client = get_client(provider="anthropic")
            captured = capsys.readouterr()
            assert "WARNING" in captured.out
            assert "ANTHROPIC_API_KEY" in captured.out


# ═══════════════════════════════════════════════════════════
# Tests: anthropic_to_openai_tools conversion
# ═══════════════════════════════════════════════════════════


class TestAnthropicToOpenaiTools:
    """Tests for _anthropic_tools_to_openai() conversion function."""

    def test_empty_tools_returns_none(self):
        """Empty list or None returns None."""
        from llm import _anthropic_tools_to_openai
        assert _anthropic_tools_to_openai([]) is None
        assert _anthropic_tools_to_openai(None) is None

    def test_single_simple_tool(self):
        """A single simple tool converts correctly."""
        from llm import _anthropic_tools_to_openai

        anthropic_tools = [
            {
                "name": "get_weather",
                "description": "Get the current weather",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"},
                    },
                    "required": ["location"],
                },
            }
        ]

        result = _anthropic_tools_to_openai(anthropic_tools)

        assert len(result) == 1
        assert result[0]["type"] == "function"
        func = result[0]["function"]
        assert func["name"] == "get_weather"
        assert func["description"] == "Get the current weather"
        assert func["parameters"]["type"] == "object"
        assert "location" in func["parameters"]["properties"]
        assert func["parameters"]["required"] == ["location"]

    def test_multiple_tools(self):
        """Multiple tools convert correctly."""
        from llm import _anthropic_tools_to_openai

        anthropic_tools = [
            {
                "name": "bash",
                "description": "Run a shell command",
                "input_schema": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
            {
                "name": "read_file",
                "description": "Read a file",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            },
        ]

        result = _anthropic_tools_to_openai(anthropic_tools)

        assert len(result) == 2
        assert result[0]["function"]["name"] == "bash"
        assert result[1]["function"]["name"] == "read_file"
        # Second tool has no required array
        assert "required" not in result[1]["function"]["parameters"]

    def test_tool_without_description(self):
        """Tool without description field defaults to empty string."""
        from llm import _anthropic_tools_to_openai

        anthropic_tools = [
            {
                "name": "minimal_tool",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]

        result = _anthropic_tools_to_openai(anthropic_tools)
        assert result[0]["function"]["description"] == ""

    def test_tool_without_input_schema(self):
        """Tool without input_schema gets empty defaults."""
        from llm import _anthropic_tools_to_openai

        anthropic_tools = [
            {"name": "bare_tool", "description": "A tool with no schema"},
        ]

        result = _anthropic_tools_to_openai(anthropic_tools)
        params = result[0]["function"]["parameters"]
        assert params["type"] == "object"
        assert params["properties"] == {}


# ═══════════════════════════════════════════════════════════
# Tests: openai_response_to_anthropic normalization
# ═══════════════════════════════════════════════════════════


class TestOpenaiResponseToAnthropic:
    """Tests for _openai_response_to_anthropic() normalization."""

    def test_simple_text_response(self):
        """A simple text-only OpenAI response normalizes correctly."""
        from llm import _openai_response_to_anthropic

        msg = FakeOpenAIChoiceMessage(content="Hello, how can I help?")
        choice = FakeOpenAIChoice(msg, finish_reason="stop")
        resp = FakeOpenAIResponse(choices=[choice], model="gpt-4o")

        result = _openai_response_to_anthropic(resp)

        assert len(result.content) == 1
        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Hello, how can I help?"
        assert result.stop_reason == "end_turn"
        assert result.model == "gpt-4o"

    def test_tool_call_response(self):
        """Response with tool calls normalizes correctly."""
        from llm import _openai_response_to_anthropic
        import json

        func = FakeToolCallFunction(
            name="get_weather",
            arguments=json.dumps({"location": "Beijing"}),
        )
        tc = FakeToolCall(func, tc_id="call_xyz")
        msg = FakeOpenAIChoiceMessage(content="", tool_calls=[tc])
        choice = FakeOpenAIChoice(msg, finish_reason="tool_calls")
        resp = FakeOpenAIResponse(choices=[choice], model="gpt-4o")

        result = _openai_response_to_anthropic(resp)

        assert result.stop_reason == "tool_use"
        assert len(result.content) == 1
        block = result.content[0]
        assert block["type"] == "tool_use"
        assert block["id"] == "call_xyz"
        assert block["name"] == "get_weather"
        assert block["input"] == {"location": "Beijing"}

    def test_text_and_tool_call(self):
        """Response with both text and tool calls."""
        from llm import _openai_response_to_anthropic
        import json

        func = FakeToolCallFunction(
            name="bash",
            arguments=json.dumps({"command": "ls"}),
        )
        tc = FakeToolCall(func, tc_id="call_456")
        msg = FakeOpenAIChoiceMessage(
            content="Let me list the files.",
            tool_calls=[tc],
        )
        choice = FakeOpenAIChoice(msg, finish_reason="tool_calls")
        resp = FakeOpenAIResponse(choices=[choice])

        result = _openai_response_to_anthropic(resp)

        assert len(result.content) == 2
        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Let me list the files."
        assert result.content[1]["type"] == "tool_use"
        assert result.content[1]["name"] == "bash"

    def test_length_finish_reason(self):
        """finish_reason='length' maps to stop_reason='max_tokens'."""
        from llm import _openai_response_to_anthropic

        msg = FakeOpenAIChoiceMessage(content="Trunca")
        choice = FakeOpenAIChoice(msg, finish_reason="length")
        resp = FakeOpenAIResponse(choices=[choice])

        result = _openai_response_to_anthropic(resp)
        assert result.stop_reason == "max_tokens"

    def test_malformed_tool_arguments(self):
        """Tool call with invalid JSON arguments defaults to empty dict."""
        from llm import _openai_response_to_anthropic

        func = FakeToolCallFunction(name="bad_tool", arguments="not-valid-json{{{")
        tc = FakeToolCall(func, tc_id="call_bad")
        msg = FakeOpenAIChoiceMessage(content="", tool_calls=[tc])
        choice = FakeOpenAIChoice(msg, finish_reason="tool_calls")
        resp = FakeOpenAIResponse(choices=[choice])

        result = _openai_response_to_anthropic(resp)
        assert result.content[0]["input"] == {}


# ═══════════════════════════════════════════════════════════
# Tests: extract_text helper
# ═══════════════════════════════════════════════════════════


class TestExtractText:
    """Tests for the extract_text() utility function."""

    def test_string_input(self):
        """Passing a plain string returns it unchanged."""
        from llm import extract_text
        assert extract_text("hello") == "hello"
        assert extract_text("") == ""

    def test_sdk_text_blocks(self):
        """SDK-style objects with .text attribute are extracted."""
        from llm import extract_text

        content = [
            FakeTextBlock("Hello "),
            FakeTextBlock("world!"),
        ]
        result = extract_text(content)
        assert result == "Hello \nworld!"

    def test_dict_text_blocks(self):
        """Plain dicts with type='text' are extracted."""
        from llm import extract_text

        content = [
            {"type": "text", "text": "First paragraph."},
            {"type": "text", "text": "Second paragraph."},
        ]
        result = extract_text(content)
        assert result == "First paragraph.\nSecond paragraph."

    def test_mixed_sdk_and_dicts(self):
        """Mixed SDK objects and dicts are both handled."""
        from llm import extract_text

        content = [
            FakeTextBlock("From SDK. "),
            {"type": "text", "text": "From dict."},
        ]
        result = extract_text(content)
        assert result == "From SDK. \nFrom dict."

    def test_skips_non_text_blocks(self):
        """Tool use blocks and other non-text types are skipped."""
        from llm import extract_text

        content = [
            FakeTextBlock("Hello."),
            FakeToolUseBlock("t1", "bash", {"command": "ls"}),
            {"type": "tool_use", "id": "t2", "name": "read", "input": {}},
            {"type": "text", "text": " World."},
        ]
        result = extract_text(content)
        assert result == "Hello.\n World."

    def test_empty_blocks_with_text_key(self):
        """Dict text blocks with missing 'text' key return empty string."""
        from llm import extract_text

        content = [
            {"type": "text"},  # no 'text' key
        ]
        result = extract_text(content)
        assert result == ""


# ═══════════════════════════════════════════════════════════
# Tests: execute_tools helper
# ═══════════════════════════════════════════════════════════


class TestExecuteTools:
    """Tests for the execute_tools() utility function."""

    def test_empty_content_returns_empty_list(self):
        """Empty content returns empty list."""
        from llm import execute_tools
        assert execute_tools([], {}) == []

    def test_no_matching_handlers(self):
        """Blocks with no matching handler produce no results."""
        from llm import execute_tools

        content = [
            {"type": "tool_use", "name": "nonexistent", "input": {}, "id": "t1"},
        ]
        results = execute_tools(content, {})
        assert results == []

    def test_sdk_tool_use_block(self):
        """SDK-style tool_use blocks are executed."""
        from llm import execute_tools

        def my_handler(x: int, y: int = 0) -> int:
            return x + y

        content = [
            FakeToolUseBlock("t1", "add", {"x": 3, "y": 4}),
        ]
        results = execute_tools(content, {"add": my_handler})

        assert len(results) == 1
        assert results[0]["type"] == "tool_result"
        assert results[0]["tool_use_id"] == "t1"
        assert results[0]["content"] == "7"

    def test_dict_tool_use_block(self):
        """Dict-style tool_use blocks are executed."""
        from llm import execute_tools

        def greet(name: str) -> str:
            return f"Hello, {name}!"

        content = [
            {"type": "tool_use", "name": "greet", "input": {"name": "World"}, "id": "t2"},
        ]
        results = execute_tools(content, {"greet": greet})

        assert len(results) == 1
        assert results[0]["content"] == "Hello, World!"

    def test_multiple_tool_calls(self):
        """Multiple tool_use blocks all get executed."""
        from llm import execute_tools

        def double(x: int) -> int:
            return x * 2

        def triple(x: int) -> int:
            return x * 3

        content = [
            FakeToolUseBlock("t1", "double", {"x": 5}),
            FakeToolUseBlock("t2", "triple", {"x": 5}),
        ]
        handlers = {"double": double, "triple": triple}
        results = execute_tools(content, handlers)

        assert len(results) == 2
        assert results[0]["content"] == "10"
        assert results[1]["content"] == "15"

    def test_handler_raises_exception(self):
        """When a handler raises, the error is captured as the tool result."""
        from llm import execute_tools

        def failer(msg: str) -> str:
            raise ValueError("Boom!")

        content = [
            FakeToolUseBlock("t1", "failer", {"msg": "test"}),
        ]
        results = execute_tools(content, {"failer": failer})

        assert len(results) == 1
        assert "Tool error" in results[0]["content"]

    def test_tool_use_without_input(self):
        """Tool use block with None input passes empty dict."""
        from llm import execute_tools

        def no_args() -> str:
            return "no args needed"

        content = [
            FakeToolUseBlock("t1", "no_args", None),
        ]
        results = execute_tools(content, {"no_args": no_args})
        assert results[0]["content"] == "no args needed"
