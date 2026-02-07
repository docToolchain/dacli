"""Tests for Issue #186: Experimental `dacli ask` command.

Tests for LLM provider abstraction, context building from documentation,
ask service orchestration, and CLI/MCP integration.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dacli.cli import cli
from dacli.mcp_app import create_mcp_server

# -- Fixtures --


@pytest.fixture
def docs_with_content(tmp_path: Path) -> Path:
    """Create documentation with searchable content."""
    doc = tmp_path / "guide.adoc"
    doc.write_text(
        """\
= User Guide

== Introduction

This is the introduction to dacli.
dacli helps you navigate documentation projects.

== Installation

Install dacli using uv:

[source,bash]
----
uv tool install dacli
----

== Usage

Run dacli with --help to see available commands.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def docs_minimal(tmp_path: Path) -> Path:
    """Create minimal documentation."""
    doc = tmp_path / "readme.md"
    doc.write_text("# Readme\n\nA simple readme.\n", encoding="utf-8")
    return tmp_path


# -- LLM Provider Tests --


class TestLLMProviderInterface:
    """Test LLM provider availability detection and selection."""

    def test_claude_code_available_when_binary_found(self):
        """ClaudeCodeProvider.is_available() returns True when claude binary exists."""
        from dacli.services.llm_provider import ClaudeCodeProvider

        with patch("shutil.which", return_value="/usr/bin/claude"):
            provider = ClaudeCodeProvider()
            assert provider.is_available() is True

    def test_claude_code_unavailable_when_binary_missing(self):
        """ClaudeCodeProvider.is_available() returns False when claude binary missing."""
        from dacli.services.llm_provider import ClaudeCodeProvider

        with patch("shutil.which", return_value=None):
            provider = ClaudeCodeProvider()
            assert provider.is_available() is False

    def test_claude_code_provider_name(self):
        """ClaudeCodeProvider has correct name."""
        from dacli.services.llm_provider import ClaudeCodeProvider

        assert ClaudeCodeProvider().name == "claude-code"

    def test_anthropic_api_available_with_key(self):
        """AnthropicAPIProvider.is_available() returns True when API key set."""
        from dacli.services.llm_provider import AnthropicAPIProvider

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            provider = AnthropicAPIProvider()
            assert provider.is_available() is True

    def test_anthropic_api_unavailable_without_key(self):
        """AnthropicAPIProvider.is_available() returns False without API key."""
        from dacli.services.llm_provider import AnthropicAPIProvider

        with patch.dict(os.environ, {}, clear=True):
            # Also ensure ANTHROPIC_API_KEY is not in env
            env = os.environ.copy()
            env.pop("ANTHROPIC_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                provider = AnthropicAPIProvider()
                assert provider.is_available() is False

    def test_anthropic_api_provider_name(self):
        """AnthropicAPIProvider has correct name."""
        from dacli.services.llm_provider import AnthropicAPIProvider

        assert AnthropicAPIProvider().name == "anthropic-api"

    def test_auto_detect_prefers_claude_code(self):
        """get_provider() prefers Claude Code when available."""
        from dacli.services.llm_provider import get_provider

        with patch("shutil.which", return_value="/usr/bin/claude"):
            provider = get_provider()
            assert provider.name == "claude-code"

    def test_auto_detect_falls_back_to_anthropic_api(self):
        """get_provider() falls back to Anthropic API when Claude Code unavailable."""
        from dacli.services.llm_provider import get_provider

        with (
            patch("shutil.which", return_value=None),
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}),
        ):
            provider = get_provider()
            assert provider.name == "anthropic-api"

    def test_auto_detect_raises_when_none_available(self):
        """get_provider() raises RuntimeError when no provider available."""
        from dacli.services.llm_provider import get_provider

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        with (
            patch("shutil.which", return_value=None),
            patch.dict(os.environ, env, clear=True),
        ):
            with pytest.raises(RuntimeError, match="No LLM provider available"):
                get_provider()

    def test_explicit_provider_selection(self):
        """get_provider(preferred='claude-code') returns that provider."""
        from dacli.services.llm_provider import get_provider

        with patch("shutil.which", return_value="/usr/bin/claude"):
            provider = get_provider(preferred="claude-code")
            assert provider.name == "claude-code"

    def test_explicit_provider_unavailable_raises(self):
        """get_provider(preferred='claude-code') raises if unavailable."""
        from dacli.services.llm_provider import get_provider

        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="not available"):
                get_provider(preferred="claude-code")

    def test_claude_code_ask_calls_subprocess(self):
        """ClaudeCodeProvider.ask() calls claude CLI via subprocess."""
        from dacli.services.llm_provider import ClaudeCodeProvider

        provider = ClaudeCodeProvider()
        mock_result = MagicMock()
        mock_result.stdout = "This is the answer."
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            response = provider.ask("system prompt", "user question")

        assert response.text == "This is the answer."
        assert response.provider == "claude-code"
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "claude" in call_args[0][0][0]

    def test_claude_code_ask_handles_error(self):
        """ClaudeCodeProvider.ask() raises on subprocess failure."""
        from dacli.services.llm_provider import ClaudeCodeProvider

        provider = ClaudeCodeProvider()

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=120),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                provider.ask("system", "question")

    def test_anthropic_api_ask_calls_sdk(self):
        """AnthropicAPIProvider.ask() calls the Anthropic SDK."""
        from dacli.services.llm_provider import AnthropicAPIProvider

        provider = AnthropicAPIProvider()

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="SDK answer")]
        mock_message.model = "claude-sonnet-4-20250514"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("dacli.services.llm_provider.anthropic") as mock_anthropic:
                mock_anthropic.Anthropic.return_value = mock_client
                response = provider.ask("system prompt", "user question")

        assert response.text == "SDK answer"
        assert response.provider == "anthropic-api"
        assert response.model == "claude-sonnet-4-20250514"

    def test_llm_response_dataclass(self):
        """LLMResponse stores text, provider, and model."""
        from dacli.services.llm_provider import LLMResponse

        resp = LLMResponse(text="answer", provider="test", model="test-model")
        assert resp.text == "answer"
        assert resp.provider == "test"
        assert resp.model == "test-model"


# -- Context Building Tests --


class TestContextBuilding:
    """Test context assembly from search results."""

    def test_build_context_finds_relevant_sections(self, docs_with_content: Path):
        """_build_context returns sections matching the question."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import _build_context
        from dacli.structure_index import StructureIndex

        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=docs_with_content)
        from dacli.markdown_parser import MarkdownStructureParser

        md_parser = MarkdownStructureParser()
        _build_index(docs_with_content, idx, parser, md_parser)

        context = _build_context("installation", idx, fh, max_sections=5)
        assert len(context) > 0
        # Should find the installation section
        found_install = any("install" in c["content"].lower() for c in context)
        assert found_install, "Should find installation-related content"

    def test_build_context_respects_max_sections(self, docs_with_content: Path):
        """_build_context limits the number of sections returned."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import _build_context
        from dacli.structure_index import StructureIndex

        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=docs_with_content)
        md_parser = MarkdownStructureParser()
        _build_index(docs_with_content, idx, parser, md_parser)

        context = _build_context("dacli", idx, fh, max_sections=1)
        assert len(context) <= 1

    def test_build_context_returns_empty_for_no_match(self, docs_minimal: Path):
        """_build_context returns empty list when nothing matches."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import _build_context
        from dacli.structure_index import StructureIndex

        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=docs_minimal)
        md_parser = MarkdownStructureParser()
        _build_index(docs_minimal, idx, parser, md_parser)

        context = _build_context("xyznonexistent", idx, fh, max_sections=5)
        assert context == []

    def test_build_context_truncates_long_content(self, tmp_path: Path):
        """_build_context truncates sections exceeding MAX_SECTION_CHARS."""
        from dacli.services.ask_service import MAX_SECTION_CHARS, _build_context

        # Create a doc with very long content
        long_content = "x" * (MAX_SECTION_CHARS + 1000)
        doc = tmp_path / "long.md"
        doc.write_text(f"# Long Doc\n\n## Section\n\n{long_content}\n", encoding="utf-8")

        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.structure_index import StructureIndex

        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=tmp_path)
        md_parser = MarkdownStructureParser()
        _build_index(tmp_path, idx, parser, md_parser)

        context = _build_context("section", idx, fh, max_sections=5)
        if context:
            for c in context:
                # Allow small margin for truncation message
                assert len(c["content"]) <= MAX_SECTION_CHARS + 20


# -- Ask Service Tests --


class TestAskService:
    """Test the ask_documentation orchestration."""

    def test_ask_documentation_returns_answer(self, docs_with_content: Path):
        """ask_documentation returns a complete response dict."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import ask_documentation
        from dacli.services.llm_provider import LLMResponse
        from dacli.structure_index import StructureIndex

        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=docs_with_content)
        md_parser = MarkdownStructureParser()
        _build_index(docs_with_content, idx, parser, md_parser)

        mock_response = LLMResponse(
            text="dacli is a documentation CLI tool.",
            provider="claude-code",
            model="claude-sonnet-4-20250514",
        )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = mock_response
            mock_provider.name = "claude-code"
            mock_get.return_value = mock_provider

            result = ask_documentation("What is dacli?", idx, fh)

        assert result["answer"] == "dacli is a documentation CLI tool."
        assert result["provider"] == "claude-code"
        assert result["sections_used"] >= 0
        assert "experimental" in result

    def test_ask_documentation_with_no_context(self, docs_minimal: Path):
        """ask_documentation handles case when no relevant sections found."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import ask_documentation
        from dacli.services.llm_provider import LLMResponse
        from dacli.structure_index import StructureIndex

        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=docs_minimal)
        md_parser = MarkdownStructureParser()
        _build_index(docs_minimal, idx, parser, md_parser)

        mock_response = LLMResponse(
            text="I couldn't find relevant information.",
            provider="claude-code",
            model=None,
        )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = mock_response
            mock_provider.name = "claude-code"
            mock_get.return_value = mock_provider

            result = ask_documentation("xyznonexistent", idx, fh)

        assert "answer" in result

    def test_ask_documentation_propagates_provider_error(self, docs_minimal: Path):
        """ask_documentation propagates errors from the LLM provider."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import ask_documentation
        from dacli.structure_index import StructureIndex

        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=docs_minimal)
        md_parser = MarkdownStructureParser()
        _build_index(docs_minimal, idx, parser, md_parser)

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_get.side_effect = RuntimeError("No LLM provider available")

            result = ask_documentation("question", idx, fh)

        assert "error" in result
        assert "No LLM provider" in result["error"]

    def test_ask_documentation_passes_provider_name(self, docs_minimal: Path):
        """ask_documentation passes provider_name to get_provider."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import ask_documentation
        from dacli.services.llm_provider import LLMResponse
        from dacli.structure_index import StructureIndex

        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=docs_minimal)
        md_parser = MarkdownStructureParser()
        _build_index(docs_minimal, idx, parser, md_parser)

        mock_response = LLMResponse(text="answer", provider="anthropic-api", model=None)

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = mock_response
            mock_provider.name = "anthropic-api"
            mock_get.return_value = mock_provider

            ask_documentation("q", idx, fh, provider_name="anthropic-api")

        mock_get.assert_called_once_with(preferred="anthropic-api")


# -- CLI Tests --


class TestAskCLI:
    """Test the CLI ask command."""

    def test_ask_command_in_help(self, docs_minimal: Path):
        """The ask command appears in dacli --help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--docs-root", str(docs_minimal), "--help"])
        assert "ask" in result.output

    def test_ask_alias_works(self, docs_minimal: Path):
        """The 'a' alias resolves to 'ask'."""
        from dacli.cli import COMMAND_ALIASES

        assert COMMAND_ALIASES.get("a") == "ask"

    def test_ask_command_with_provider_option(self, docs_minimal: Path):
        """ask command accepts --provider option."""
        runner = CliRunner()

        with patch("dacli.cli.ask_documentation") as mock_ask:
            mock_ask.return_value = {
                "answer": "test answer",
                "provider": "claude-code",
                "sections_used": 0,
                "experimental": True,
            }
            result = runner.invoke(
                cli,
                [
                    "--docs-root", str(docs_minimal),
                    "ask", "What is this?",
                    "--provider", "claude-code",
                ],
            )

        assert result.exit_code == 0

    def test_ask_command_error_handling(self, docs_minimal: Path):
        """ask command shows error from service gracefully."""
        runner = CliRunner()

        with patch("dacli.cli.ask_documentation") as mock_ask:
            mock_ask.return_value = {
                "error": "No LLM provider available",
            }
            result = runner.invoke(
                cli,
                ["--docs-root", str(docs_minimal), "ask", "question"],
            )

        assert result.exit_code == 1

    def test_ask_in_experimental_group(self, docs_minimal: Path):
        """ask command is in the Experimental group."""
        from dacli.cli import COMMAND_GROUPS

        assert "Experimental" in COMMAND_GROUPS
        assert "ask" in COMMAND_GROUPS["Experimental"]


# -- MCP Tool Tests --


class TestAskMCPTool:
    """Test the MCP ask_documentation tool."""

    def test_ask_tool_registered(self, docs_minimal: Path):
        """ask_documentation tool is registered in MCP server."""
        mcp = create_mcp_server(docs_minimal)
        tool_names = [t.name for t in mcp._tool_manager._tools.values()]
        assert "ask_documentation_tool" in tool_names

    def test_ask_tool_returns_result(self, docs_minimal: Path):
        """ask_documentation MCP tool returns a result dict."""
        from dacli.services.llm_provider import LLMResponse

        mcp = create_mcp_server(docs_minimal)

        ask_tool = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "ask_documentation_tool":
                ask_tool = tool
                break

        assert ask_tool is not None

        mock_response = LLMResponse(text="MCP answer", provider="claude-code", model=None)

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_response = LLMResponse(text="MCP answer", provider="claude-code", model=None)
            mock_provider.ask.return_value = mock_response
            mock_provider.name = "claude-code"
            mock_get.return_value = mock_provider

            result = ask_tool.fn(question="What is this?")

        assert result["answer"] == "MCP answer"
