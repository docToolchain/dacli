"""Tests for Issue #246: Markdown headings with inline HTML comments not recognized.

Headings like `## Important <!-- TODO: review -->` should be recognized as headings.
The inline HTML comment should be stripped from the title.
"""

from pathlib import Path

import pytest

from dacli.markdown_parser import MarkdownStructureParser
from dacli.structure_index import StructureIndex


@pytest.fixture
def temp_doc_inline_comment(tmp_path: Path) -> Path:
    """Create a Markdown file with headings containing inline HTML comments."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Document

## Important <!-- TODO: review -->

Some content here.

## Normal Section

More content.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def temp_doc_multiple_inline_comments(tmp_path: Path) -> Path:
    """Create a Markdown file with various inline comment patterns."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Project <!-- draft -->

## Getting Started <!-- needs update -->

Content.

## Installation

Steps here.

## FAQ <!-- TODO --> <!-- WIP -->

Questions.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def temp_doc_mixed_comments(tmp_path: Path) -> Path:
    """Inline comments on headings + block comments (should still skip block)."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Document

## Visible <!-- note -->

Content.

<!--
## Hidden Heading
This is fully commented out.
-->

## Also Visible

More content.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestInlineHtmlCommentHeadings:
    """Issue #246: Headings with inline HTML comments should be recognized."""

    def test_heading_with_inline_comment_is_recognized(
        self, temp_doc_inline_comment: Path
    ):
        """A heading with an inline HTML comment should appear in structure."""
        parser = MarkdownStructureParser(base_path=temp_doc_inline_comment)
        index = StructureIndex()

        documents = []
        for doc_file in temp_doc_inline_comment.glob("*.md"):
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

        assert "test:important" in paths, (
            f"Heading with inline comment should be recognized. Paths: {paths}"
        )
        assert "test:normal-section" in paths

    def test_inline_comment_stripped_from_title(
        self, temp_doc_inline_comment: Path
    ):
        """The inline HTML comment should be stripped from the heading title."""
        parser = MarkdownStructureParser(base_path=temp_doc_inline_comment)

        for doc_file in temp_doc_inline_comment.glob("*.md"):
            doc = parser.parse_file(doc_file)

        root = doc.sections[0]
        # Find the "Important" section
        important_section = next(
            (s for s in root.children if "Important" in s.title), None
        )
        assert important_section is not None, (
            "Should find a section with 'Important' in title"
        )
        assert "<!--" not in important_section.title
        assert "-->" not in important_section.title
        assert important_section.title == "Important"

    def test_multiple_inline_comments_all_recognized(
        self, temp_doc_multiple_inline_comments: Path
    ):
        """Multiple headings with inline comments should all be recognized."""
        parser = MarkdownStructureParser(
            base_path=temp_doc_multiple_inline_comments
        )
        index = StructureIndex()

        documents = []
        for doc_file in temp_doc_multiple_inline_comments.glob("*.md"):
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

        assert "test:getting-started" in paths
        assert "test:installation" in paths
        assert "test:faq" in paths

    def test_h1_with_inline_comment_title_cleaned(
        self, temp_doc_multiple_inline_comments: Path
    ):
        """H1 document title should have inline comment stripped."""
        parser = MarkdownStructureParser(
            base_path=temp_doc_multiple_inline_comments
        )

        for doc_file in temp_doc_multiple_inline_comments.glob("*.md"):
            doc = parser.parse_file(doc_file)

        assert doc.title == "Project"
        assert "<!--" not in doc.title

    def test_mixed_inline_and_block_comments(
        self, temp_doc_mixed_comments: Path
    ):
        """Inline comments on headings + block comments should both work."""
        parser = MarkdownStructureParser(base_path=temp_doc_mixed_comments)
        index = StructureIndex()

        documents = []
        for doc_file in temp_doc_mixed_comments.glob("*.md"):
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

        # Inline comment heading should be visible
        assert "test:visible" in paths
        assert "test:also-visible" in paths
        # Block comment heading should remain hidden
        assert "test:hidden-heading" not in paths
