"""Tests for Issue #251: Report circular includes explicitly instead of as orphaned files.

When two AsciiDoc files include each other circularly (A includes B, B includes A),
the validation should report them as "circular_include" errors, not as "orphaned_file"
warnings.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli
from dacli.mcp_app import create_mcp_server


@pytest.fixture
def temp_circular_include(tmp_path: Path) -> Path:
    """Create a temporary directory with two files that include each other."""
    file_a = tmp_path / "file_a.adoc"
    file_b = tmp_path / "file_b.adoc"

    file_a.write_text(
        """= File A

Some content in A.

include::file_b.adoc[]
""",
        encoding="utf-8",
    )

    file_b.write_text(
        """= File B

Some content in B.

include::file_a.adoc[]
""",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def temp_self_circular_include(tmp_path: Path) -> Path:
    """Create a temporary directory with a file that includes itself."""
    file_a = tmp_path / "self_ref.adoc"
    file_a.write_text(
        """= Self Referencing Doc

include::self_ref.adoc[]
""",
        encoding="utf-8",
    )
    return tmp_path


class TestCircularIncludeValidation:
    """Test that circular includes are reported as errors, not orphaned files."""

    def test_circular_include_reported_as_error(self, temp_circular_include: Path):
        """Issue #251: Circular includes should be reported as circular_include errors."""
        mcp = create_mcp_server(temp_circular_include)

        # Access validate_structure tool
        tools = {t.name: t for t in mcp._tool_manager._tools.values()}
        result = tools["validate_structure"].fn()

        # Should NOT be valid due to circular include
        assert (
            result["valid"] is False
        ), f"Expected valid=False for circular include. Result: {result}"

        # Should have a circular_include error
        error_types = [e["type"] for e in result["errors"]]
        assert (
            "circular_include" in error_types
        ), f"Expected 'circular_include' error. Errors: {result['errors']}"

    def test_circular_include_not_reported_as_orphaned(self, temp_circular_include: Path):
        """Issue #251: Files involved in circular includes should NOT be reported as orphaned."""
        mcp = create_mcp_server(temp_circular_include)

        tools = {t.name: t for t in mcp._tool_manager._tools.values()}
        result = tools["validate_structure"].fn()

        # Check that no orphaned_file warnings exist for the circular files
        orphaned_warnings = [w for w in result["warnings"] if w["type"] == "orphaned_file"]
        orphaned_paths = [w["path"] for w in orphaned_warnings]

        assert (
            "file_a.adoc" not in orphaned_paths
        ), f"file_a.adoc should not be orphaned. Warnings: {result['warnings']}"
        assert (
            "file_b.adoc" not in orphaned_paths
        ), f"file_b.adoc should not be orphaned. Warnings: {result['warnings']}"

    def test_circular_include_error_contains_chain(self, temp_circular_include: Path):
        """Circular include error should include the include chain."""
        mcp = create_mcp_server(temp_circular_include)

        tools = {t.name: t for t in mcp._tool_manager._tools.values()}
        result = tools["validate_structure"].fn()

        circular_errors = [e for e in result["errors"] if e["type"] == "circular_include"]
        assert len(circular_errors) >= 1

        # The error message should mention the files involved
        error = circular_errors[0]
        assert "message" in error
        assert "circular" in error["message"].lower() or "Circular" in error["message"]

    def test_self_circular_include_reported_as_error(self, temp_self_circular_include: Path):
        """A file that includes itself should be reported as circular_include error."""
        mcp = create_mcp_server(temp_self_circular_include)

        tools = {t.name: t for t in mcp._tool_manager._tools.values()}
        result = tools["validate_structure"].fn()

        # Should NOT be valid
        assert result["valid"] is False

        # Should have a circular_include error
        error_types = [e["type"] for e in result["errors"]]
        assert (
            "circular_include" in error_types
        ), f"Expected 'circular_include' error for self-include. Errors: {result['errors']}"

        # Should NOT have orphaned_file warning for the file
        orphaned_paths = [w["path"] for w in result["warnings"] if w["type"] == "orphaned_file"]
        assert "self_ref.adoc" not in orphaned_paths


class TestCLICircularIncludeValidation:
    """Test CLI validate command with circular includes."""

    def test_cli_validate_reports_circular_include(self, temp_circular_include: Path):
        """CLI validate should report circular includes as errors."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_circular_include), "validate"],
        )

        assert "circular_include" in result.output
        # Exit code 4 = EXIT_VALIDATION_ERROR (validation found errors)
        assert result.exit_code == 4
