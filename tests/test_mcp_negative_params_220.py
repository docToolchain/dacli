"""Tests for Issue #220: MCP tools should validate negative parameter values.

Negative values for parameters like max_results, max_depth, level, and
content_limit should be rejected with a clear error message.
"""

from pathlib import Path

import pytest

from dacli.mcp_app import create_mcp_server


@pytest.fixture
def temp_doc_folder(tmp_path: Path) -> Path:
    """Create a simple documentation folder for testing."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Test Document

## Section 1

Some content here.

```python
print("hello")
```

## Section 2

More content.

### Subsection 2.1

Nested content.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def mcp_server(temp_doc_folder: Path):
    """Create an MCP server for testing."""
    return create_mcp_server(temp_doc_folder)


class TestSearchNegativeMaxResults:
    """Test that search rejects negative max_results."""

    def test_search_negative_max_results_should_error(self, mcp_server):
        """Issue #220: search with negative max_results should raise error."""
        # Get the search tool
        search_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "search":
                search_tool = tool
                break

        assert search_tool is not None, "search tool not found"

        # Currently this does NOT raise an error - it should after fix
        with pytest.raises(ValueError, match="max_results must be non-negative"):
            search_tool.fn(query="test", max_results=-5)


class TestGetStructureNegativeMaxDepth:
    """Test that get_structure rejects negative max_depth."""

    def test_get_structure_negative_max_depth_should_error(self, mcp_server):
        """Issue #220: get_structure with negative max_depth should raise error."""
        # Get the get_structure tool
        get_structure_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "get_structure":
                get_structure_tool = tool
                break

        assert get_structure_tool is not None, "get_structure tool not found"

        # Currently this does NOT raise an error - it should after fix
        with pytest.raises(ValueError, match="max_depth must be non-negative"):
            get_structure_tool.fn(max_depth=-1)


class TestGetSectionsAtLevelNegativeLevel:
    """Test that get_sections_at_level rejects negative level."""

    def test_get_sections_at_level_negative_should_error(self, mcp_server):
        """Issue #220: get_sections_at_level with negative level should raise error."""
        # Get the get_sections_at_level tool
        get_sections_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "get_sections_at_level":
                get_sections_tool = tool
                break

        assert get_sections_tool is not None, "get_sections_at_level tool not found"

        # Currently this does NOT raise an error - it should after fix
        with pytest.raises(ValueError, match="level must be positive"):
            get_sections_tool.fn(level=-1)

    def test_get_sections_at_level_zero_should_error(self, mcp_server):
        """Issue #220: get_sections_at_level with level=0 should raise error."""
        get_sections_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "get_sections_at_level":
                get_sections_tool = tool
                break

        assert get_sections_tool is not None

        # Level 0 doesn't make sense (levels are 1-based)
        with pytest.raises(ValueError, match="level must be positive"):
            get_sections_tool.fn(level=0)


class TestGetElementsNegativeContentLimit:
    """Test that get_elements rejects negative content_limit."""

    def test_get_elements_negative_content_limit_should_error(self, mcp_server):
        """Issue #220: get_elements with negative content_limit should raise error."""
        # Get the get_elements tool
        get_elements_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "get_elements":
                get_elements_tool = tool
                break

        assert get_elements_tool is not None, "get_elements tool not found"

        # Currently this does NOT raise an error - it should after fix
        with pytest.raises(ValueError, match="content_limit must be non-negative"):
            get_elements_tool.fn(include_content=True, content_limit=-10)
