"""Tests for Issues #248 and #249: CLI should reject negative --max-depth and --limit.

Issue #248: `dacli structure --max-depth -1` accepts negative values without error.
Issue #249: `dacli search "test" --limit -5` accepts negative values without error.

Both should reject negative values with a clear error message,
following the same pattern as sections-at-level (Issue #199).
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


class TestStructureNegativeMaxDepth:
    """Issue #248: structure --max-depth should reject negative values."""

    def test_negative_max_depth_rejected(self, temp_doc_dir: Path):
        """--max-depth -1 should be rejected with clear error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "structure", "--max-depth", "-1"],
        )

        assert result.exit_code != 0
        assert "max-depth must be non-negative" in result.output

    def test_negative_max_depth_includes_value(self, temp_doc_dir: Path):
        """Error message should include the actual negative value."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "structure", "--max-depth", "-5"],
        )

        assert result.exit_code != 0
        assert "got -5" in result.output

    def test_max_depth_zero_works(self, temp_doc_dir: Path):
        """--max-depth 0 should work (returns only root level)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "structure", "--max-depth", "0"],
        )

        assert result.exit_code == 0

    def test_max_depth_positive_works(self, temp_doc_dir: Path):
        """--max-depth 2 should work normally."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "structure", "--max-depth", "2"],
        )

        assert result.exit_code == 0

    def test_max_depth_none_works(self, temp_doc_dir: Path):
        """Omitting --max-depth should work (returns full structure)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "structure"],
        )

        assert result.exit_code == 0

    def test_str_alias_negative_max_depth_rejected(self, temp_doc_dir: Path):
        """The 'str' alias should also reject negative --max-depth."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "str", "--max-depth", "-1"],
        )

        assert result.exit_code != 0
        assert "max-depth must be non-negative" in result.output


class TestSearchNegativeLimit:
    """Issue #249: search --limit should reject negative values."""

    def test_negative_limit_rejected(self, temp_doc_dir: Path):
        """--limit -5 should be rejected with clear error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "search", "test", "--limit", "-5"],
        )

        assert result.exit_code != 0
        assert "limit must be non-negative" in result.output

    def test_negative_limit_includes_value(self, temp_doc_dir: Path):
        """Error message should include the actual negative value."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "search", "test", "--limit", "-1"],
        )

        assert result.exit_code != 0
        assert "got -1" in result.output

    def test_negative_max_results_rejected(self, temp_doc_dir: Path):
        """--max-results -3 should also be rejected (alias for --limit)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "search",
                "test",
                "--max-results",
                "-3",
            ],
        )

        assert result.exit_code != 0
        assert "limit must be non-negative" in result.output

    def test_limit_zero_works(self, temp_doc_dir: Path):
        """--limit 0 should work (returns no results)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "search", "test", "--limit", "0"],
        )

        assert result.exit_code == 0

    def test_limit_positive_works(self, temp_doc_dir: Path):
        """--limit 5 should work normally."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "search", "test", "--limit", "5"],
        )

        assert result.exit_code == 0

    def test_search_alias_negative_limit_rejected(self, temp_doc_dir: Path):
        """The 's' alias should also reject negative --limit."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_dir), "s", "test", "--limit", "-5"],
        )

        assert result.exit_code != 0
        assert "limit must be non-negative" in result.output
