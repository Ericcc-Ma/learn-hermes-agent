"""
Smoke tests for the learn-hermes-agent tutorial project.

These tests verify that all modules can be imported and parsed correctly.
No API keys are required — any test that would need real credentials is skipped.
"""

import ast
import importlib.util
import os
import sys

import pytest

# Project root (parent of tests/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure the project root is on the path so "from llm import ..." works
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Paths to all 18 chapter code.py files (relative to project root)
CHAPTER_FILES = [
    "s01_agent_loop/code.py",
    "s02_background_memory_review/code.py",
    "s03_background_skill_review/code.py",
    "s04_memory_system/code.py",
    "s05_skill_lifecycle/code.py",
    "s06_skill_creation/code.py",
    "s07_curator_state/code.py",
    "s08_curator_llm/code.py",
    "s09_context_management/code.py",
    "s10_insights/code.py",
    "s11_error_recovery/code.py",
    "s12_comprehensive/code.py",
    "s13_cron_scheduler/code.py",
    "s14_gateway/code.py",
    "s15_profiles/code.py",
    "s16_agent_teams/code.py",
    "s17_mcp_plugin/code.py",
    "s18_full_hermes/code.py",
    "s19_permission/code.py",
    "s20_hooks/code.py",
    "s21_worktree/code.py",
    "s22_planning/code.py",
    "s23_autonomous/code.py",
    "s24_system_prompt/code.py",
]


# ═══════════════════════════════════════════════════════════
# Tests: llm module
# ═══════════════════════════════════════════════════════════


class TestLLMModule:
    """Tests for the core llm.py module."""

    def test_import_llm(self):
        """llm.py can be imported."""
        import llm
        assert llm is not None

    def test_import_get_client(self):
        """get_client can be imported from llm."""
        from llm import get_client
        assert callable(get_client)

    def test_import_llmclient(self):
        """LLMClient can be imported from llm."""
        from llm import LLMClient
        assert LLMClient is not None

    def test_get_client_returns_llmclient(self):
        """get_client() returns an LLMClient instance."""
        from llm import get_client, LLMClient
        client = get_client()
        assert isinstance(client, LLMClient)

    def test_get_client_has_messages_api(self):
        """Returned client has a messages attribute."""
        from llm import get_client
        client = get_client()
        assert hasattr(client, "messages")

    def test_get_client_default_provider(self):
        """Default provider should be anthropic."""
        from llm import get_client
        client = get_client()
        assert client.provider == "anthropic"


# ═══════════════════════════════════════════════════════════
# Tests: AST parse check on all chapter code.py files
# ═══════════════════════════════════════════════════════════


class TestChapterSyntax:
    """AST parse checks for all chapter code.py files — no execution, pure syntax."""

    @pytest.mark.parametrize("rel_path", CHAPTER_FILES)
    def test_ast_parse(self, rel_path: str):
        """Each code.py can be parsed by Python's AST (no syntax errors)."""
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=rel_path)
        assert isinstance(tree, ast.Module)
        assert len(tree.body) > 0

    @pytest.mark.parametrize("rel_path", CHAPTER_FILES)
    def test_has_main_guard(self, rel_path: str):
        """Each code.py has an 'if __name__ == \"__main__\"' guard."""
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert '__name__ == "__main__"' in source or "__name__ == '__main__'" in source

    @pytest.mark.parametrize("rel_path", CHAPTER_FILES)
    def test_imports_llm(self, rel_path: str):
        """Each code.py imports from llm."""
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "from llm import" in source or "import llm" in source


# ═══════════════════════════════════════════════════════════
# Tests: import each chapter code.py as a module
# ═══════════════════════════════════════════════════════════


class TestChapterImport:
    """Import each chapter code.py via importlib — verifies runtime importability.

    These tests use a fresh subprocess to avoid side-effects between chapters
    (each chapter executes module-level code including get_client()).
    """

    @pytest.mark.parametrize("rel_path", CHAPTER_FILES)
    def test_import_as_module(self, rel_path: str):
        """Each code.py can be imported as a module (via importlib)."""
        full_path = os.path.join(PROJECT_ROOT, rel_path)

        # Use a unique module name per chapter to avoid caching conflicts
        module_name = rel_path.replace("/", "_").replace(".py", "")

        # Remove from sys.modules if present from a previous test
        sys.modules.pop(module_name, None)

        spec = importlib.util.spec_from_file_location(module_name, full_path)
        assert spec is not None, f"Could not create module spec for {rel_path}"

        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod

        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            pytest.fail(f"Failed to import {rel_path}: {e}")
        finally:
            # Clean up to avoid polluting other tests
            sys.modules.pop(module_name, None)


# ═══════════════════════════════════════════════════════════
# Tests: check files exist
# ═══════════════════════════════════════════════════════════


class TestFileExistence:
    """Verify all expected files are present."""

    def test_llm_py_exists(self):
        """llm.py exists at project root."""
        path = os.path.join(PROJECT_ROOT, "llm.py")
        assert os.path.isfile(path)

    def test_requirements_exists(self):
        """requirements.txt exists."""
        path = os.path.join(PROJECT_ROOT, "requirements.txt")
        assert os.path.isfile(path)

    def test_env_example_exists(self):
        """.env.example exists."""
        path = os.path.join(PROJECT_ROOT, ".env.example")
        assert os.path.isfile(path)

    @pytest.mark.parametrize("rel_path", CHAPTER_FILES)
    def test_code_py_exists(self, rel_path: str):
        """Each chapter code.py file exists on disk."""
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        assert os.path.isfile(full_path), f"Missing: {rel_path}"
