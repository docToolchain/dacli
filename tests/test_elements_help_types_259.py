"""Tests for Issue #259: elements help text lists incorrect element types.

The help text for `dacli elements --type` should list the actual valid types:
admonition, code, image, list, plantuml, table (not 'diagram').
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli
from dacli.mcp_app import create_mcp_server


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    """Create minimal docs for testing."""
    (tmp_path / "test.md").write_text("# Test\n\nContent.\n", encoding="utf-8")
    return tmp_path


class TestElementsHelpTypes:
    """Test that element type help texts match actual valid types."""

    VALID_TYPES = {"admonition", "code", "image", "list", "plantuml", "table"}

    def test_cli_help_lists_correct_types(self, docs_dir: Path):
        """CLI help for elements should list all valid types including plantuml/admonition."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--docs-root", str(docs_dir), "elements", "--help"])
        assert result.exit_code == 0
        # Should contain the correct types
        assert "plantuml" in result.output
        assert "admonition" in result.output
        # Should NOT contain 'diagram' as a type
        assert "diagram" not in result.output

    def test_mcp_tool_docstring_lists_correct_types(self, docs_dir: Path):
        """MCP get_elements tool docstring should list correct types in Args section."""
        mcp = create_mcp_server(docs_dir)
        elements_tool = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_elements":
                elements_tool = tool
                break
        assert elements_tool is not None
        docstring = elements_tool.fn.__doc__
        # The Args section listing valid types should include the correct ones
        assert "'plantuml'" in docstring
        assert "'admonition'" in docstring
        # The type listing should NOT contain 'diagram' as a quoted type
        assert "'diagram'" not in docstring

    def test_cli_accepts_plantuml_type(self, docs_dir: Path):
        """CLI should accept plantuml as a valid element type without warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(docs_dir), "elements", "--type", "plantuml"]
        )
        assert "Warning" not in result.output

    def test_cli_accepts_admonition_type(self, docs_dir: Path):
        """CLI should accept admonition as a valid element type without warning."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(docs_dir), "elements", "--type", "admonition"]
        )
        assert "Warning" not in result.output

    def test_cli_warns_on_diagram_type(self, docs_dir: Path):
        """CLI should warn when 'diagram' is used as element type."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(docs_dir), "elements", "--type", "diagram"]
        )
        assert "Warning" in result.output
