"""Tests for Issue #224: Empty files should have valid line range.

Empty files should either be skipped or have a valid line range (end_line >= line).
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli


@pytest.fixture
def temp_doc_with_empty_file(tmp_path: Path) -> Path:
    """Create a folder with an empty file and a normal file."""
    # Empty file
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("", encoding="utf-8")

    # Normal file with content
    normal_file = tmp_path / "normal.md"
    normal_file.write_text(
        """# Normal Document

Some content here.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestEmptyFilesLineRange:
    """Test that empty files have valid line ranges."""

    def test_empty_file_valid_line_range(self, temp_doc_with_empty_file: Path):
        """Issue #224: Empty files should have valid line range (end_line >= line)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_with_empty_file), "--format", "json", "structure"],
        )

        assert result.exit_code == 0

        import json
        data = json.loads(result.output)

        # Find all sections and check line ranges
        def check_line_ranges(sections):
            for section in sections:
                location = section.get("location", {})
                line = location.get("line", 1)
                end_line = location.get("end_line", 1)

                # end_line should be >= line (valid range)
                assert end_line >= line, (
                    f"Invalid line range for '{section.get('path')}': "
                    f"line={line}, end_line={end_line}"
                )

                # Check children recursively
                if section.get("children"):
                    check_line_ranges(section["children"])

        check_line_ranges(data.get("sections", []))

    def test_normal_file_line_range(self, temp_doc_with_empty_file: Path):
        """Normal files should have proper line ranges."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_with_empty_file), "--format", "json", "structure"],
        )

        assert result.exit_code == 0

        import json
        data = json.loads(result.output)

        # Find the normal document
        for section in data.get("sections", []):
            if "normal" in section.get("path", "").lower():
                location = section.get("location", {})
                assert location.get("line", 0) >= 1
                assert location.get("end_line", 0) >= 1
                break
