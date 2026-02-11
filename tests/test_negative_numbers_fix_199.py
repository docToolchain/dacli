"""Tests for Issue #199: sections-at-level cannot handle negative numbers.

These tests verify that:
1. Negative numbers can be parsed (not treated as options)
2. Negative numbers are rejected with clear error message
3. Zero and positive numbers continue to work correctly
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

== Level 1 Section A

Content here.

=== Level 2 Section A.1

Nested content.

== Level 1 Section B

More content.

=== Level 2 Section B.1

More nested content.

=== Level 2 Section B.2

Even more nested.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestNegativeNumberParsing:
    """Test that negative numbers are parsed correctly."""

    def test_negative_one_is_parsed_not_treated_as_option(self, temp_doc_dir: Path):
        """Negative number -1 should be parsed as argument, not option (Issue #199)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "sections-at-level",
                "-1",
            ],
        )

        # Should NOT fail with "No such option: -1"
        assert "No such option: -1" not in result.output

        # Should fail with validation error instead
        assert result.exit_code != 0
        assert "Level must be non-negative" in result.output

    def test_negative_ten_is_parsed(self, temp_doc_dir: Path):
        """Larger negative number -10 should be parsed as argument."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "sections-at-level",
                "-10",
            ],
        )

        # Should NOT fail with "No such option: -10"
        assert "No such option: -10" not in result.output

        # Should fail with validation error
        assert result.exit_code != 0
        assert "Level must be non-negative" in result.output


class TestNegativeNumberValidation:
    """Test validation of negative levels."""

    def test_negative_level_rejected_with_clear_message(self, temp_doc_dir: Path):
        """Negative level should be rejected with helpful error message."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "sections-at-level",
                "-1",
            ],
        )

        assert result.exit_code != 0
        assert "Level must be non-negative" in result.output
        assert "got -1" in result.output
        assert "Document hierarchies start at level 0" in result.output

    def test_negative_level_error_includes_level_value(self, temp_doc_dir: Path):
        """Error message should include the actual negative value provided."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "sections-at-level",
                "-5",
            ],
        )

        assert result.exit_code != 0
        assert "got -5" in result.output


class TestPositiveNumbersStillWork:
    """Test that zero and positive numbers continue to work correctly."""

    def test_level_zero_works(self, temp_doc_dir: Path):
        """Level 0 (document root) should work."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "sections-at-level",
                "0",
            ],
        )

        assert result.exit_code == 0
        # Should return the document root
        assert "test" in result.output or "count" in result.output

    def test_level_one_works(self, temp_doc_dir: Path):
        """Level 1 (top-level sections) should work."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "sections-at-level",
                "1",
            ],
        )

        assert result.exit_code == 0
        # Should return both Level 1 sections
        assert "Level 1 Section A" in result.output or "level-1-section-a" in result.output
        assert "Level 1 Section B" in result.output or "level-1-section-b" in result.output

    def test_level_two_works(self, temp_doc_dir: Path):
        """Level 2 (nested sections) should work."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "sections-at-level",
                "2",
            ],
        )

        assert result.exit_code == 0
        # Should return level 2 sections
        assert "Level 2 Section A.1" in result.output or "level-2-section-a-1" in result.output

    def test_level_one_json_format(self, temp_doc_dir: Path):
        """Level 1 with JSON format should work."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "--format",
                "json",
                "sections-at-level",
                "1",
            ],
        )

        assert result.exit_code == 0
        assert '"level": 1' in result.output
        assert '"count":' in result.output
        assert '"sections":' in result.output


class TestAliasStillWorks:
    """Test that the 'lv' alias still works correctly."""

    def test_lv_alias_with_positive_number(self, temp_doc_dir: Path):
        """The 'lv' alias should work with positive numbers."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "lv",  # Using alias
                "1",
            ],
        )

        assert result.exit_code == 0
        assert "Level 1 Section" in result.output or "level-1-section" in result.output

    def test_lv_alias_rejects_negative(self, temp_doc_dir: Path):
        """The 'lv' alias should also reject negative numbers."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "lv",  # Using alias
                "-1",
            ],
        )

        assert result.exit_code != 0
        assert "Level must be non-negative" in result.output
