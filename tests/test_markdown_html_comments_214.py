"""Tests for Issue #214: HTML comments in Markdown not ignored.

Headings inside HTML comment blocks should not appear in the structure.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli
from dacli.markdown_parser import MarkdownStructureParser
from dacli.structure_index import StructureIndex


@pytest.fixture
def temp_doc_with_html_comment(tmp_path: Path) -> Path:
    """Create a Markdown file with HTML comment containing heading."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Document

## Section 1

Content

<!--
## This is commented out
Should not appear in structure
-->

## Section 2

Content
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def temp_doc_with_single_line_comment(tmp_path: Path) -> Path:
    """Create a Markdown file with single-line HTML comment."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Document

## Section 1

<!-- ## Single line commented heading -->

## Section 2

Content
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def temp_doc_with_multiple_comments(tmp_path: Path) -> Path:
    """Create a Markdown file with multiple HTML comments."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Document

## Section 1

<!--
## Commented 1
-->

## Section 2

<!-- ## Commented 2 -->

## Section 3

<!--
## Commented 3
More content
## Another commented heading
-->

## Section 4
""",
        encoding="utf-8",
    )
    return tmp_path


class TestMarkdownHtmlComments:
    """Test that HTML comments are properly ignored."""

    def test_multiline_comment_ignored(self, temp_doc_with_html_comment: Path):
        """Issue #214: Multi-line HTML comments should be ignored."""
        parser = MarkdownStructureParser(base_path=temp_doc_with_html_comment)
        index = StructureIndex()

        documents = []
        for doc_file in temp_doc_with_html_comment.glob("*.md"):
            doc = parser.parse_file(doc_file)
            documents.append(doc)

        index.build_from_documents(documents)

        # Get all section paths
        structure = index.get_structure()
        paths = []

        def collect_paths(sections):
            for s in sections:
                paths.append(s["path"])
                if s.get("children"):
                    collect_paths(s["children"])

        collect_paths(structure["sections"])

        # Should have 3 sections: document, section-1, section-2
        assert (
            "test:this-is-commented-out" not in paths
        ), f"Commented heading should not appear. Paths: {paths}"
        assert "test:section-1" in paths
        assert "test:section-2" in paths

    def test_single_line_comment_ignored(self, temp_doc_with_single_line_comment: Path):
        """Single-line HTML comments should also be ignored."""
        parser = MarkdownStructureParser(base_path=temp_doc_with_single_line_comment)
        index = StructureIndex()

        documents = []
        for doc_file in temp_doc_with_single_line_comment.glob("*.md"):
            doc = parser.parse_file(doc_file)
            documents.append(doc)

        index.build_from_documents(documents)

        structure = index.get_structure()
        paths = []

        def collect_paths(sections):
            for s in sections:
                paths.append(s["path"])
                if s.get("children"):
                    collect_paths(s["children"])

        collect_paths(structure["sections"])

        assert "test:single-line-commented-heading" not in paths
        assert "test:section-1" in paths
        assert "test:section-2" in paths

    def test_multiple_comments_all_ignored(self, temp_doc_with_multiple_comments: Path):
        """Multiple HTML comments should all be ignored."""
        parser = MarkdownStructureParser(base_path=temp_doc_with_multiple_comments)
        index = StructureIndex()

        documents = []
        for doc_file in temp_doc_with_multiple_comments.glob("*.md"):
            doc = parser.parse_file(doc_file)
            documents.append(doc)

        index.build_from_documents(documents)

        structure = index.get_structure()
        paths = []

        def collect_paths(sections):
            for s in sections:
                paths.append(s["path"])
                if s.get("children"):
                    collect_paths(s["children"])

        collect_paths(structure["sections"])

        # Should only have sections 1-4, no commented headings
        assert (
            len([p for p in paths if "commented" in p.lower()]) == 0
        ), f"No commented headings should appear. Paths: {paths}"
        assert "test:section-1" in paths
        assert "test:section-2" in paths
        assert "test:section-3" in paths
        assert "test:section-4" in paths


class TestCLIHtmlComments:
    """Test CLI with HTML comments."""

    def test_cli_structure_ignores_html_comments(self, temp_doc_with_html_comment: Path):
        """CLI structure command should not show commented headings."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_with_html_comment), "structure"],
        )

        assert result.exit_code == 0
        assert "this-is-commented-out" not in result.output
        assert "section-1" in result.output
        assert "section-2" in result.output
