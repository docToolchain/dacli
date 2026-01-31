"""Tests for Issue #226: CLI search command warns on invalid scope.

When a --scope that doesn't exist is provided, the CLI should warn the user
instead of silently returning 0 results.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli


@pytest.fixture
def temp_doc_with_sections(tmp_path: Path) -> Path:
    """Create a Markdown file with sections."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Test Document

## Section 1

Some content about testing.

## Section 2

More content here.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestSearchInvalidScope:
    """Test that invalid scope shows a warning."""

    def test_invalid_scope_shows_warning(self, temp_doc_with_sections: Path):
        """Issue #226: Invalid scope should show warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(temp_doc_with_sections),
                "search", "test", "--scope", "nonexistent-section"
            ],
        )

        assert result.exit_code == 0
        # Should warn about invalid scope
        assert "Warning:" in result.output or "not found" in result.output.lower()
        assert "nonexistent-section" in result.output

    def test_valid_scope_no_warning(self, temp_doc_with_sections: Path):
        """Valid scope should not show a warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(temp_doc_with_sections),
                "search", "test", "--scope", "test"
            ],
        )

        assert result.exit_code == 0
        # Should not have warning about scope not found
        assert "Warning:" not in result.output
        assert "not found" not in result.output.lower() or "total_results" in result.output

    def test_no_scope_no_warning(self, temp_doc_with_sections: Path):
        """Search without scope should not show a warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_with_sections), "search", "test"],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output
