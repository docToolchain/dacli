"""Tests for Issue #216: Insert --position before missing blank line.

When inserting content before a section, there should be a blank line
between the inserted content and the following section.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli


@pytest.fixture
def temp_doc_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test document."""
    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Document

== Section A

Content A

== Section B

Content B
""",
        encoding="utf-8",
    )
    return tmp_path


class TestInsertBeforeBlankLine:
    """Test that insert --position before adds blank line correctly."""

    def test_insert_section_before_adds_blank_line(self, temp_doc_dir: Path):
        """Issue #216: Inserting a section before another should add blank line."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "insert",
                "test:section-b",
                "--position",
                "before",
                "--content",
                "== Before B\n\nContent before B",
            ],
        )

        assert result.exit_code == 0

        # Check the file content
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")

        # There should be a blank line between "Content before B" and "== Section B"
        assert (
            "Content before B\n\n== Section B" in file_content
        ), f"Missing blank line before Section B. Content:\n{file_content}"

    def test_insert_content_before_heading_adds_blank_line(self, temp_doc_dir: Path):
        """Insert plain content before a heading should add blank line."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "insert",
                "test:section-b",
                "--position",
                "before",
                "--content",
                "Some plain content without heading",
            ],
        )

        assert result.exit_code == 0

        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")

        # There should be a blank line between the content and Section B
        assert (
            "Some plain content without heading\n\n== Section B" in file_content
        ), f"Missing blank line before Section B. Content:\n{file_content}"

    def test_insert_before_preserves_existing_blank_lines(self, temp_doc_dir: Path):
        """Don't add extra blank lines if content already ends with them."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "insert",
                "test:section-b",
                "--position",
                "before",
                "--content",
                "== Before B\n\nContent before B\n\n",  # Already has trailing blank line
            ],
        )

        assert result.exit_code == 0

        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")

        # Should have exactly one blank line (not extra)
        assert "Content before B\n\n== Section B" in file_content
        # Should NOT have triple newlines
        assert "Content before B\n\n\n== Section B" not in file_content
