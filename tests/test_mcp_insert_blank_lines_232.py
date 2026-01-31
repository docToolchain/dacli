"""Tests for Issue #232: MCP insert_content blank line handling.

The MCP insert_content tool should handle blank lines like the CLI does:
- Add blank line before headings when inserting before
- Add blank line after content when next line is a heading
"""

from pathlib import Path

import pytest

from dacli.mcp_app import create_mcp_server


@pytest.fixture
def temp_doc_for_blank_lines(tmp_path: Path) -> Path:
    """Create a Markdown file for testing blank line handling."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Document

## Section 1

Content 1.

## Section 2

Content 2.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestMcpInsertBlankLines:
    """Test that MCP insert_content handles blank lines correctly."""

    def test_insert_before_adds_blank_line_after_content(
        self, temp_doc_for_blank_lines: Path
    ):
        """Issue #232: Insert before should add blank line when next is heading."""
        mcp = create_mcp_server(temp_doc_for_blank_lines)

        insert_tool = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "insert_content":
                insert_tool = tool
                break

        # Insert content before Section 2
        result = insert_tool.fn(
            path="test:section-2",
            position="before",
            content="Some new paragraph.\n"
        )

        assert result.get("success") is True

        # Read and check - should have blank line before Section 2
        doc_file = temp_doc_for_blank_lines / "test.md"
        content = doc_file.read_text()

        # The content should have proper separation
        assert "Some new paragraph." in content
        # There should be a blank line between our content and Section 2
        lines = content.split("\n")
        para_idx = next(i for i, line in enumerate(lines) if "Some new paragraph" in line)
        sec2_idx = next(i for i, line in enumerate(lines) if "## Section 2" in line)

        # Should have blank line between them
        assert sec2_idx > para_idx + 1, (
            f"Should have blank line between content and Section 2.\n"
            f"Content:\n{content}"
        )

    def test_insert_after_adds_blank_line_before_next_heading(
        self, temp_doc_for_blank_lines: Path
    ):
        """Issue #232: Insert after should add blank line before next heading."""
        mcp = create_mcp_server(temp_doc_for_blank_lines)

        insert_tool = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "insert_content":
                insert_tool = tool
                break

        # Insert content after Section 1
        result = insert_tool.fn(
            path="test:section-1",
            position="after",
            content="## New Section\n\nNew content.\n"
        )

        assert result.get("success") is True

        # Read and check
        doc_file = temp_doc_for_blank_lines / "test.md"
        content = doc_file.read_text()

        # The new section should be properly separated from Section 2
        assert "## New Section" in content
        lines = content.split("\n")
        new_idx = next(i for i, line in enumerate(lines) if "## New Section" in line)
        sec2_idx = next(i for i, line in enumerate(lines) if "## Section 2" in line)

        # New section should appear before Section 2
        assert new_idx < sec2_idx
