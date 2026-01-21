"""Unit tests for AsciiDoc Parser (Issue #3).

Tests cover:
- Parser instantiation
- Section extraction from AsciiDoc files
- Hierarchical section structure
- Section path generation

AC-ADOC-01: Sektion-Extraktion
"""

from pathlib import Path

import pytest

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "asciidoc"


class TestAsciidocParserBasic:
    """Basic tests for AsciidocParser instantiation."""

    def test_parser_can_be_instantiated(self):
        """Test that AsciidocParser can be instantiated with a base path."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=Path("."))
        assert parser is not None
        assert parser.base_path == Path(".")

    def test_parser_accepts_max_include_depth(self):
        """Test that parser accepts max_include_depth parameter."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=Path("."), max_include_depth=10)
        assert parser.max_include_depth == 10

    def test_parser_default_max_include_depth_is_20(self):
        """Test that default max_include_depth is 20."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=Path("."))
        assert parser.max_include_depth == 20


class TestSectionExtraction:
    """Tests for section extraction (AC-ADOC-01)."""

    def test_parse_file_returns_asciidoc_document(self):
        """Test that parse_file returns an AsciidocDocument."""
        from mcp_server.asciidoc_parser import AsciidocDocument, AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        assert isinstance(doc, AsciidocDocument)

    def test_parse_file_extracts_document_title(self):
        """Test that document title is extracted."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        assert doc.title == "Haupttitel"

    def test_parse_file_extracts_sections(self):
        """Test that sections are extracted from the document."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        # Document should have a root section (title) with children
        assert len(doc.sections) >= 1

    def test_section_levels_are_correct(self):
        """Test that section levels are correctly determined."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        # Root section (= Haupttitel) should be level 0
        root = doc.sections[0]
        assert root.level == 0
        assert root.title == "Haupttitel"

        # Children (== Kapitel 1, == Kapitel 2) should be level 1
        assert len(root.children) == 2
        assert root.children[0].level == 1
        assert root.children[0].title == "Kapitel 1"
        assert root.children[1].level == 1
        assert root.children[1].title == "Kapitel 2"

    def test_nested_sections_hierarchy(self):
        """Test that nested sections form correct hierarchy."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        # Kapitel 2 should have Unterkapitel as child
        root = doc.sections[0]
        kapitel2 = root.children[1]
        assert len(kapitel2.children) == 1
        assert kapitel2.children[0].title == "Unterkapitel"
        assert kapitel2.children[0].level == 2


class TestSectionPaths:
    """Tests for hierarchical section paths."""

    def test_root_section_path(self):
        """Test that root section has correct path."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        assert root.path == "haupttitel"

    def test_chapter_section_path(self):
        """Test that chapter sections have correct hierarchical paths."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        assert root.children[0].path == "haupttitel.kapitel-1"
        assert root.children[1].path == "haupttitel.kapitel-2"

    def test_subsection_path(self):
        """Test that subsections have correct hierarchical paths."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        unterkapitel = root.children[1].children[0]
        assert unterkapitel.path == "haupttitel.kapitel-2.unterkapitel"


class TestSourceLocation:
    """Tests for source location tracking."""

    def test_section_has_source_location(self):
        """Test that sections have source location."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        assert root.source_location is not None
        assert root.source_location.file == FIXTURES_DIR / "simple_sections.adoc"
        assert root.source_location.line == 1  # First line

    def test_chapter_source_location(self):
        """Test that chapter has correct source location."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        kapitel1 = root.children[0]
        assert kapitel1.source_location.line == 3  # "== Kapitel 1" is on line 3


class TestDocumentAttributes:
    """Tests for document attribute parsing (AC-ADOC-02)."""

    def test_parse_attributes_from_document(self):
        """Test that document attributes are extracted."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_attributes.adoc")

        assert "author" in doc.attributes
        assert doc.attributes["author"] == "Max Mustermann"

    def test_parse_multiple_attributes(self):
        """Test that multiple attributes are extracted."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_attributes.adoc")

        assert doc.attributes["author"] == "Max Mustermann"
        assert doc.attributes["project"] == "MCP Server"
        assert doc.attributes["version"] == "1.0.0"
        assert doc.attributes["imagesdir"] == "./images"

    def test_attribute_in_title_is_resolved(self):
        """Test that attribute references in title are resolved."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_attributes.adoc")

        # Title should have {project} resolved to "MCP Server"
        assert doc.title == "MCP Server Dokumentation"


class TestIncludeDirectives:
    """Tests for include directive handling (AC-ADOC-03, AC-ADOC-04)."""

    def test_include_directive_is_recorded(self):
        """Test that include directives are recorded in includes list."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_include.adoc")

        assert len(doc.includes) == 1
        assert doc.includes[0].target_path == FIXTURES_DIR / "include_partial.adoc"

    def test_include_directive_source_location(self):
        """Test that include directive has correct source location."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_include.adoc")

        assert doc.includes[0].source_location.line == 7
        assert doc.includes[0].source_location.file == FIXTURES_DIR / "with_include.adoc"

    def test_included_sections_are_merged(self):
        """Test that sections from included file are merged into document."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_include.adoc")

        # Document should have root section with 4 children:
        # Erstes Kapitel, Eingebundener Abschnitt (from include), Letztes Kapitel
        root = doc.sections[0]
        section_titles = [s.title for s in root.children]

        assert "Erstes Kapitel" in section_titles
        assert "Eingebundener Abschnitt" in section_titles
        assert "Letztes Kapitel" in section_titles

    def test_included_section_has_resolved_from_info(self):
        """Test that included sections track their source file."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_include.adoc")

        root = doc.sections[0]
        # Find the included section
        included_section = next(
            s for s in root.children if s.title == "Eingebundener Abschnitt"
        )

        # Source location should reference the included file
        assert (
            included_section.source_location.file
            == FIXTURES_DIR / "include_partial.adoc"
        )
        assert included_section.source_location.resolved_from is not None
        assert (
            included_section.source_location.resolved_from.file
            == FIXTURES_DIR / "with_include.adoc"
        )


class TestEdgeCases:
    """Tests for edge cases."""

    def test_parse_nonexistent_file_raises_error(self):
        """Test that parsing nonexistent file raises FileNotFoundError."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        with pytest.raises(FileNotFoundError):
            parser.parse_file(FIXTURES_DIR / "nonexistent.adoc")

    def test_parse_empty_file(self):
        """Test that parsing empty file returns document with no sections."""
        from mcp_server.asciidoc_parser import AsciidocParser

        # Create empty file
        empty_file = FIXTURES_DIR / "empty.adoc"
        empty_file.write_text("")

        try:
            parser = AsciidocParser(base_path=FIXTURES_DIR)
            doc = parser.parse_file(empty_file)
            assert doc.title == ""
            assert doc.sections == []
        finally:
            empty_file.unlink()
