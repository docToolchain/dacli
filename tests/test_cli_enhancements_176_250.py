"""Tests for Issues #250 and #176: CLI enhancements.

Issue #250: CLI update command should warn when content is empty/whitespace-only.
Issue #176: Clearer error message when --format is placed after the command.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli


@pytest.fixture
def temp_doc_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test documents."""
    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Test Document

== Introduction

Some introductory content.

== Details

More detailed content here.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestUpdateEmptyContentWarning:
    """Issue #250: update command should warn when content is empty."""

    def test_empty_content_shows_warning(self, temp_doc_dir: Path):
        """Passing --content '' should show a warning on stderr."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "update",
                "test:introduction",
                "--content",
                "",
            ],
        )

        assert "Warning: Section content will be cleared" in result.stderr

    def test_whitespace_only_content_shows_warning(self, temp_doc_dir: Path):
        """Passing --content with only whitespace should show a warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "update",
                "test:introduction",
                "--content",
                "   \n  ",
            ],
        )

        assert "Warning: Section content will be cleared" in result.stderr

    def test_non_empty_content_no_warning(self, temp_doc_dir: Path):
        """Passing --content with actual content should NOT show a warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "update",
                "test:introduction",
                "--content",
                "New content here",
            ],
        )

        assert "Warning" not in result.stderr

    def test_empty_content_still_succeeds(self, temp_doc_dir: Path):
        """Empty content should still succeed (just warn, not block)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "update",
                "test:introduction",
                "--content",
                "",
            ],
        )

        # Should succeed (exit code 0) despite the warning
        assert result.exit_code == 0


class TestFormatPositionError:
    """Issue #176: Better error when --format is placed after the command."""

    def test_format_after_command_gives_helpful_error(self, temp_doc_dir: Path):
        """'dacli structure --format json' should give a helpful error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "structure", "--format", "json"],
        )

        # Should mention that --format is a global option
        assert result.exit_code != 0
        output = result.output
        assert "--format" in output
        assert "global" in output.lower() or "before" in output.lower()

    def test_format_before_command_works(self, temp_doc_dir: Path):
        """'dacli --format json structure' should work fine (no error)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "--format", "json", "structure"],
        )

        assert result.exit_code == 0

    def test_format_after_search_gives_helpful_error(self, temp_doc_dir: Path):
        """'dacli search "test" --format json' should give a helpful error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "search", "test", "--format", "json"],
        )

        assert result.exit_code != 0
        output = result.output
        assert "--format" in output
        assert "global" in output.lower() or "before" in output.lower()

    def test_format_after_section_gives_helpful_error(self, temp_doc_dir: Path):
        """'dacli section intro --format json' should give a helpful error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "section",
                "test:introduction",
                "--format",
                "json",
            ],
        )

        assert result.exit_code != 0
        output = result.output
        assert "--format" in output
        assert "global" in output.lower() or "before" in output.lower()
