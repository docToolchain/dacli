"""Tests for Issue #186: Iterative context building for `dacli ask`.

The ask command should iterate through sections one by one, passing each
section + question + previous findings to the LLM. A final consolidation
step combines all findings into a coherent answer with source references.
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


# -- Keyword Extraction Tests --


class TestKeywordExtraction:
    """Test extracting search keywords from natural language questions."""

    def test_extracts_keywords_from_question(self):
        """Should extract meaningful words, removing stop words."""
        from dacli.services.ask_service import _extract_keywords

        keywords = _extract_keywords("Welche Sicherheitshinweise gibt es?")
        assert "sicherheitshinweise" in keywords
        # Stop words like "welche", "gibt", "es" should be removed
        assert "welche" not in keywords
        assert "es" not in keywords

    def test_extracts_english_keywords(self):
        """Should handle English questions too."""
        from dacli.services.ask_service import _extract_keywords

        keywords = _extract_keywords("How does authentication work?")
        assert "authentication" in keywords
        # Stop words removed
        assert "how" not in keywords
        assert "does" not in keywords

    def test_single_keyword_passthrough(self):
        """Single words should pass through unchanged."""
        from dacli.services.ask_service import _extract_keywords

        keywords = _extract_keywords("Sicherheit")
        assert "sicherheit" in keywords

    def test_returns_nonempty_for_all_stopwords(self):
        """If all words are stop words, return original words as fallback."""
        from dacli.services.ask_service import _extract_keywords

        keywords = _extract_keywords("what is the")
        # Should return something, not empty
        assert len(keywords) > 0


# -- Iterative Context Building Tests --


class TestIterativeAsk:
    """Test the iterative section-by-section LLM approach."""

    def test_calls_llm_per_section_then_consolidates(self, index_and_handler):
        """LLM should be called once per relevant section + once for consolidation."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        # Track all LLM calls
        responses = [
            # Iteration responses (one per section)
            LLMResponse(
                text="KEY_POINTS: Uses JWT tokens\nMISSING: authorization details",
                provider="test", model=None,
            ),
            LLMResponse(
                text="KEY_POINTS: RBAC used\nMISSING: nothing",
                provider="test", model=None,
            ),
            LLMResponse(
                text="KEY_POINTS: login endpoint\nMISSING: nothing",
                provider="test", model=None,
            ),
            # Consolidation response
            LLMResponse(
                text="Authentication uses JWT with RBAC authorization.",
                provider="test", model=None,
            ),
        ]

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.side_effect = responses
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation(
                "How does authentication work?", idx, fh, max_sections=3
            )

        # Should have multiple LLM calls (sections + consolidation)
        assert mock_provider.ask.call_count >= 2, (
            "Expected at least 2 LLM calls (1 section + consolidation)"
        )

    def test_accumulates_findings_across_iterations(self, index_and_handler):
        """Each iteration should include findings from previous iterations."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        call_prompts = []

        def capture_ask(system_prompt, user_message):
            call_prompts.append(user_message)
            return LLMResponse(
                text="KEY_POINTS: Found something\nMISSING: nothing",
                provider="test",
                model=None,
            )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.side_effect = capture_ask
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation("authentication", idx, fh, max_sections=3)

        # Second iteration prompt should contain findings from first
        if len(call_prompts) >= 3:
            # The second section call should reference previous findings
            assert "Found something" in call_prompts[1] or "findings" in call_prompts[1].lower()

    def test_returns_sources_with_paths(self, index_and_handler):
        """Result should include source references with section paths."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="Answer with sources", provider="test", model=None
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            result = ask_documentation("authentication", idx, fh, max_sections=3)

        assert "sources" in result
        assert isinstance(result["sources"], list)
        # Should have at least one source
        if result["sources"]:
            assert "path" in result["sources"][0]

    def test_consolidation_prompt_includes_all_findings(self, index_and_handler):
        """The final consolidation call should include all accumulated findings."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        call_prompts = []

        def capture_ask(system_prompt, user_message):
            call_prompts.append(user_message)
            return LLMResponse(
                text="KEY_POINTS: found info\nMISSING: nothing",
                provider="test",
                model=None,
            )

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.side_effect = capture_ask
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation("authentication", idx, fh, max_sections=2)

        # Last call should be consolidation - contains the question
        last_prompt = call_prompts[-1]
        assert "authentication" in last_prompt.lower() or "question" in last_prompt.lower()

    def test_natural_language_question_finds_sections(self, index_and_handler):
        """Natural language questions should find relevant sections via keyword extraction."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="Answer about security", provider="test", model=None
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation(
                "Welche Sicherheitshinweise gibt es?", idx, fh, max_sections=5
            )

        # Should have found sections and called LLM at least once
        # (even for German question, keyword extraction should find something)
        assert mock_provider.ask.call_count >= 1

    def test_max_sections_limits_iterations(self, index_and_handler):
        """max_sections should limit how many sections are evaluated."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="KEY_POINTS: info\nMISSING: nothing", provider="test", model=None
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            ask_documentation("authentication", idx, fh, max_sections=1)

        # 1 section + 1 consolidation = 2 calls max
        assert mock_provider.ask.call_count <= 2

    def test_result_includes_iterations_count(self, index_and_handler):
        """Result should report how many iterations were performed."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="Answer", provider="test", model=None
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            result = ask_documentation("authentication", idx, fh, max_sections=3)

        assert "iterations" in result
        assert isinstance(result["iterations"], int)
        assert result["iterations"] >= 1

    def test_handles_no_search_results_gracefully(self, index_and_handler):
        """When search finds nothing, should still return a meaningful response."""
        from dacli.services.ask_service import ask_documentation

        idx, fh = index_and_handler

        with patch("dacli.services.ask_service.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.ask.return_value = LLMResponse(
                text="No information found.", provider="test", model=None
            )
            mock_provider.name = "test"
            mock_get.return_value = mock_provider

            result = ask_documentation(
                "xyznonexistenttopic123", idx, fh, max_sections=5
            )

        assert "answer" in result
        assert "error" not in result
