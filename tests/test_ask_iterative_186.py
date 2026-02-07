"""Tests for Issue #186: Iterative context building for `dacli ask`.

The ask command iterates through ALL sections one by one, passing each
section + question + previous findings to the LLM. The LLM decides
relevance (no keyword search). A final consolidation step combines all
findings into a coherent answer with source references.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dacli.services.llm_provider import LLMResponse

# -- Fixtures --


@pytest.fixture
def docs_multi_section(tmp_path: Path) -> Path:
    """Create documentation with multiple distinct sections."""
    doc = tmp_path / "guide.adoc"
    doc.write_text(
        """\
= Security Guide

== Authentication

Authentication uses JWT tokens.
Users authenticate via OAuth2 flow.

== Authorization

Authorization uses RBAC (Role-Based Access Control).
Permissions are checked after authentication.

== API Endpoints

The /api/login endpoint handles authentication.
The /api/admin endpoint requires admin role.

== Deployment

Deploy using Docker containers.
Use docker-compose for local development.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def index_and_handler(docs_multi_section: Path):
    """Build index and file handler for multi-section docs."""
    from dacli.asciidoc_parser import AsciidocStructureParser
    from dacli.file_handler import FileSystemHandler
    from dacli.markdown_parser import MarkdownStructureParser
    from dacli.mcp_app import _build_index
    from dacli.structure_index import StructureIndex

    idx = StructureIndex()
    fh = FileSystemHandler()
    parser = AsciidocStructureParser(base_path=docs_multi_section)
    md_parser = MarkdownStructureParser()
    _build_index(docs_multi_section, idx, parser, md_parser)
    return idx, fh


# -- Section Collection Tests --


class TestSectionCollection:
    """Test that all sections are collected without keyword filtering."""

    def test_get_all_sections_returns_flat_list(self, index_and_handler):
        """_get_all_sections returns all sections as a flat list."""
        from dacli.services.ask_service import _get_all_sections

        idx, _ = index_and_handler
        sections = _get_all_sections(idx)

        assert len(sections) >= 4  # Auth, Authz, API, Deployment
        paths = [s["path"] for s in sections]
        # All sections should be present
        assert any("authentication" in p for p in paths)
        assert any("authorization" in p for p in paths)
        assert any("deployment" in p for p in paths)

    def test_get_all_sections_includes_title_and_level(self, index_and_handler):
        """Each section has path, title, and level."""
        from dacli.services.ask_service import _get_all_sections

        idx, _ = index_and_handler
        sections = _get_all_sections(idx)

        for s in sections:
            assert "path" in s
            assert "title" in s
            assert "level" in s


# -- Iterative Context Building Tests --


class TestIterativeAsk:
    """Test the iterative section-by-section LLM approach."""

    def test_calls_llm_per_section_then_consolidates(self, index_and_handler):
        """LLM is called once per section + once for consolidation."""
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

            ask_documentation(
                "How does authentication work?",
                idx, fh, max_sections=3,
            )

        # At least 2 calls: 1+ sections + 1 consolidation
        assert mock_provider.ask.call_count >= 2, (
            "Expected at least 2 LLM calls (1 section + consolidation)"
        )

    def test_iterates_all_sections_not_just_keyword_matches(
        self, index_and_handler
    ):
        """Sections are iterated regardless of keyword match."""
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

            # Question with no keyword match in docs
            ask_documentation(
                "Wo finde ich den Schraubenzieher?",
                idx, fh, max_sections=5,
            )

        # Should still iterate through sections (LLM decides relevance)
        # At least 2 calls: section iterations + consolidation
        assert len(call_prompts) >= 2

    def test_accumulates_findings_across_iterations(self, index_and_handler):
        """Each iteration includes findings from previous iterations."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler
        call_prompts = []

        def capture_ask(system_prompt, user_message):
            call_prompts.append(user_message)
            return LLMResponse(
                text="KEY_POINTS: Found something relevant",
                provider="test", model=None,
            )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.side_effect = capture_ask
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation("auth", idx, fh, max_sections=3)

        # Second section call should contain findings from first
        if len(call_prompts) >= 2:
            assert "Found something" in call_prompts[1]

    def test_returns_sources_with_paths(self, index_and_handler):
        """Result includes source references with section paths."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="Answer", provider="test", model=None,
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            result = ask_documentation("auth", idx, fh, max_sections=3)

        assert "sources" in result
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) > 0
        assert "path" in result["sources"][0]
        assert "title" in result["sources"][0]

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

            ask_documentation("auth", idx, fh, max_sections=2)

        # Last call should be consolidation — contains "All findings"
        last_prompt = call_prompts[-1]
        assert "All findings" in last_prompt

    def test_max_sections_limits_iterations(self, index_and_handler):
        """max_sections limits how many sections are evaluated."""
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

            ask_documentation("auth", idx, fh, max_sections=1)

        # 1 section + 1 consolidation = 2 calls max
        assert mock_provider.ask.call_count <= 2

    def test_result_includes_iterations_count(self, index_and_handler):
        """Result reports how many iterations were performed."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="Answer", provider="test", model=None,
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            result = ask_documentation("auth", idx, fh, max_sections=3)

        assert "iterations" in result
        assert isinstance(result["iterations"], int)
        assert result["iterations"] >= 1

    def test_handles_empty_docs_gracefully(self, tmp_path: Path):
        """When no sections exist, still returns a meaningful response."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.file_handler import FileSystemHandler
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.mcp_app import _build_index
        from dacli.services.ask_service import ask_documentation
        from dacli.structure_index import StructureIndex

        # Empty docs directory
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
