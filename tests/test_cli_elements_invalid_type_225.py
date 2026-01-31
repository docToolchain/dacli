"""Tests for Issue #225: CLI elements command warns on invalid element type.

When an invalid --type is provided, the CLI should warn the user
instead of silently returning count: 0.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli


@pytest.fixture
def temp_doc_with_elements(tmp_path: Path) -> Path:
    """Create a Markdown file with various elements."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Test Document

## Section 1

Some content.

```python
print("hello")
```

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |

## Section 2

More content.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestElementsInvalidType:
    """Test that invalid element type shows a warning."""

    def test_invalid_type_shows_warning(self, temp_doc_with_elements: Path):
        """Issue #225: Invalid element type should show warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_with_elements), "elements", "--type", "invalid_type"],
        )

        assert result.exit_code == 0
        # Should warn about invalid type - look for the specific warning format
        assert "Warning:" in result.output or "Unknown element type" in result.output
        assert "invalid_type" in result.output
        # Should suggest valid types
        assert "code" in result.output

    def test_valid_type_no_warning(self, temp_doc_with_elements: Path):
        """Valid element type should not show a warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_with_elements), "elements", "--type", "code"],
        )

        assert result.exit_code == 0
        # Should not have the specific warning message
        assert "Warning:" not in result.output
        assert "Unknown element type" not in result.output
        # Should have found the code block
        assert "count: 1" in result.output or '"count": 1' in result.output

    def test_all_valid_types_accepted(self, temp_doc_with_elements: Path):
        """All valid element types should be accepted without warning."""
        runner = CliRunner()
        valid_types = ["code", "table", "image", "plantuml", "admonition", "list"]

        for element_type in valid_types:
            result = runner.invoke(
                cli,
                ["--docs-root", str(temp_doc_with_elements), "elements", "--type", element_type],
            )

            assert result.exit_code == 0, f"Failed for type: {element_type}"
            assert "Warning:" not in result.output, f"Unexpected warning for: {element_type}"
            assert "Unknown element type" not in result.output, (
                f"Unexpected unknown for: {element_type}"
            )
