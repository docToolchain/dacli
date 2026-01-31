"""Tests for Issue #229: MCP insert_content 'after' position with children.

The MCP insert_content tool should insert after ALL descendants,
not just the section's own content.
"""

from pathlib import Path

import pytest

from dacli.mcp_app import create_mcp_server


@pytest.fixture
def temp_doc_with_children(tmp_path: Path) -> Path:
    """Create a Markdown file with parent and child sections."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Document

## Parent Section

Parent content.

### Child Section

Child content.

## Next Section

Next content.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestMcpInsertAfterWithChildren:
    """Test that MCP insert_content 'after' includes children."""

    def test_insert_after_parent_goes_after_children(self, temp_doc_with_children: Path):
        """Issue #229: Insert after parent should go after all children."""
        mcp = create_mcp_server(temp_doc_with_children)

        # Get the insert_content tool
        insert_tool = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "insert_content":
                insert_tool = tool
                break

        assert insert_tool is not None, "insert_content tool not found"

        # Insert after "Parent Section"
        result = insert_tool.fn(
            path="test:parent-section",
            position="after",
            content="## Inserted Section\n\nInserted content.\n"
        )

        assert result.get("success") is True, f"Insert failed: {result.get('error')}"

        # Read the file and check position
        doc_file = temp_doc_with_children / "test.md"
        content = doc_file.read_text()

        # "Inserted Section" should appear AFTER "Child content" but BEFORE "Next Section"
        child_pos = content.find("Child content")
        inserted_pos = content.find("Inserted Section")
        next_pos = content.find("Next Section")

        assert child_pos < inserted_pos < next_pos, (
            f"Inserted section should be between child and next section.\n"
            f"Positions: child={child_pos}, inserted={inserted_pos}, next={next_pos}\n"
            f"Content:\n{content}"
        )

    def test_insert_after_leaf_section(self, temp_doc_with_children: Path):
        """Insert after a section without children should work correctly."""
        mcp = create_mcp_server(temp_doc_with_children)

        insert_tool = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "insert_content":
                insert_tool = tool
                break

        # Insert after "Child Section" (no children)
        result = insert_tool.fn(
            path="test:parent-section.child-section",
            position="after",
            content="### Another Child\n\nNew content.\n"
        )

        assert result.get("success") is True

        # Read and verify
        doc_file = temp_doc_with_children / "test.md"
        content = doc_file.read_text()

        child_pos = content.find("Child content")
        another_pos = content.find("Another Child")
        next_pos = content.find("Next Section")

        assert child_pos < another_pos < next_pos
