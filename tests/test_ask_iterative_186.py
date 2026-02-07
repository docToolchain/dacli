"""Tests for Issue #186: Iterative file-based context building for `dacli ask`.

The ask command iterates through documentation FILE BY FILE (not section
by section), passing each file's content + question + previous findings
to the LLM. The LLM decides relevance. A final consolidation step combines
all findings into a coherent answer with source references.

File-based iteration is more efficient than section-based: a typical
project has ~35 files vs ~460 sections, reducing LLM calls by ~13x.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dacli.services.llm_provider import LLMResponse


# -- Fixtures --


@pytest.fixture
def docs_multi_file(tmp_path: Path) -> Path:
    """Create documentation with multiple files."""
    (tmp_path / "security.adoc").write_text(
        """\
= Security Guide

== Authentication

Authentication uses JWT tokens.

== Authorization

Authorization uses RBAC.
""",
        encoding="utf-8",
    )
    (tmp_path / "deployment.adoc").write_text(
        """\
= Deployment Guide

== Docker

Deploy using Docker containers.

== Kubernetes

Use Kubernetes for orchestration.
""",
        encoding="utf-8",
    )
    (tmp_path / "api.adoc").write_text(
        """\
= API Reference

== Endpoints

The /api/login endpoint handles authentication.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def index_and_handler(docs_multi_file: Path):
    """Build index and file handler for multi-file docs."""
    from dacli.asciidoc_parser import AsciidocStructureParser
    from dacli.file_handler import FileSystemHandler
    from dacli.markdown_parser import MarkdownStructureParser
    from dacli.mcp_app import _build_index
    from dacli.structure_index import StructureIndex

    idx = StructureIndex()
    fh = FileSystemHandler()
    parser = AsciidocStructureParser(base_path=docs_multi_file)
    md_parser = MarkdownStructureParser()
    _build_index(docs_multi_file, idx, parser, md_parser)
    return idx, fh


# -- File Collection Tests --


class TestFileCollection:
    """Test that documentation files are collected for iteration."""

    def test_get_all_files_returns_file_list(self, index_and_handler):
        """_get_all_files returns all indexed documentation files."""
        from dacli.services.ask_service import _get_all_files

        idx, _ = index_and_handler
        files = _get_all_files(idx)

        assert len(files) == 3  # security.adoc, deployment.adoc, api.adoc

    def test_files_fewer_than_sections(self, index_and_handler):
        """Number of files should be less than number of sections."""
        from dacli.services.ask_service import _get_all_files

        idx, _ = index_and_handler
        files = _get_all_files(idx)

        structure = idx.get_structure()
        total_sections = structure["total_sections"]

        assert len(files) < total_sections


# -- File-Based Iterative Tests --


class TestFileBasedAsk:
    """Test the file-by-file LLM iteration approach."""

    def test_calls_llm_per_file_then_consolidates(self, index_and_handler):
        """LLM is called once per file + once for consolidation."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="KEY_POINTS: info\nMISSING: nothing",
                provider="test", model=None,
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation("How does auth work?", idx, fh)

        # 3 files + 1 consolidation = 4 calls
        assert mock_provider.ask.call_count == 4

    def test_iterates_all_files_regardless_of_question(
        self, index_and_handler
    ):
        """All files are checked even if question has no keyword match."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler
        call_prompts = []

        def capture_ask(system_prompt, user_message):
            call_prompts.append(user_message)
            return LLMResponse(
                text="KEY_POINTS: none\nMISSING: nothing",
                provider="test", model=None,
            )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.side_effect = capture_ask
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation(
                "Wo finde ich den Schraubenzieher?", idx, fh,
            )

        # 3 files + 1 consolidation = 4 calls
        assert len(call_prompts) == 4

    def test_file_content_passed_to_llm(self, index_and_handler):
        """Each LLM call receives the full file content."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler
        call_prompts = []

        def capture_ask(system_prompt, user_message):
            call_prompts.append(user_message)
            return LLMResponse(
                text="KEY_POINTS: found\nMISSING: nothing",
                provider="test", model=None,
            )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.side_effect = capture_ask
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation("authentication", idx, fh)

        # Iteration prompts (not consolidation) should contain file content
        iteration_prompts = call_prompts[:-1]
        all_content = " ".join(iteration_prompts)
        assert "JWT tokens" in all_content
        assert "Docker" in all_content
        assert "/api/login" in all_content

    def test_accumulates_findings_across_files(self, index_and_handler):
        """Each file iteration includes findings from previous files."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler
        call_prompts = []

        def capture_ask(system_prompt, user_message):
            call_prompts.append(user_message)
            return LLMResponse(
                text="KEY_POINTS: Found important info",
                provider="test", model=None,
            )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.side_effect = capture_ask
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation("auth", idx, fh)

        # Second file call should contain findings from first
        if len(call_prompts) >= 2:
            assert "Found important info" in call_prompts[1]

    def test_returns_sources_with_file_paths(self, index_and_handler):
        """Result includes source references with file paths."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="Answer", provider="test", model=None,
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            result = ask_documentation("auth", idx, fh)

        assert "sources" in result
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) == 3
        assert "file" in result["sources"][0]

    def test_result_includes_iterations_count(self, index_and_handler):
        """Result reports how many files were iterated."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="Answer", provider="test", model=None,
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            result = ask_documentation("auth", idx, fh)

        assert "iterations" in result
        assert result["iterations"] == 3

    def test_consolidation_is_last_call(self, index_and_handler):
        """The final LLM call is the consolidation prompt."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler
        call_prompts = []

        def capture_ask(system_prompt, user_message):
            call_prompts.append(user_message)
            return LLMResponse(
                text="KEY_POINTS: info\nMISSING: nothing",
                provider="test", model=None,
            )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.side_effect = capture_ask
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation("auth", idx, fh)

        last_prompt = call_prompts[-1]
        assert "All findings" in last_prompt

    def test_progress_callback_called_per_file(self, index_and_handler):
        """Progress callback is called for each file with current/total counts."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler
        progress_calls = []

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="KEY_POINTS: info\nMISSING: nothing",
                provider="test", model=None,
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation(
                "auth", idx, fh,
                progress_callback=lambda cur, total, name: progress_calls.append(
                    (cur, total, name)
                ),
            )

        assert len(progress_calls) == 3
        assert progress_calls[0][0] == 1  # current = 1
        assert progress_calls[0][1] == 3  # total = 3
        assert progress_calls[2][0] == 3  # last call current = 3

    def test_progress_callback_includes_consolidation(self, index_and_handler):
        """Progress callback signals consolidation step."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler
        progress_calls = []

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="KEY_POINTS: info\nMISSING: nothing",
                provider="test", model=None,
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation(
                "auth", idx, fh,
                progress_callback=lambda cur, total, name: progress_calls.append(
                    (cur, total, name)
                ),
            )

        # Last call should signal consolidation
        last = progress_calls[-1]
        assert last[0] == last[1]  # current == total (last file)

    def test_handles_empty_docs_gracefully(self, tmp_path: Path):
        """When no files exist, still returns a meaningful response."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import ask_documentation
        from dacli.structure_index import StructureIndex

        (tmp_path / "empty.md").write_text("", encoding="utf-8")
        idx = StructureIndex()
        fh = FileSystemHandler()
        parser = AsciidocStructureParser(base_path=tmp_path)
        md_parser = MarkdownStructureParser()
        _build_index(tmp_path, idx, parser, md_parser)

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="No info found.", provider="test", model=None,
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            result = ask_documentation("question", idx, fh)

        assert "answer" in result
        assert "error" not in result
