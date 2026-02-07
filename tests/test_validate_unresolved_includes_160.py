"""Tests for Issue #160: Detect unresolved includes in validate command.

Ensures the validate command (MCP tool, CLI, and service layer) correctly
detects and reports missing include files as 'unresolved_include' errors.

The implementation was done in Issue #219. This test file adds MCP-level
coverage and closes Issue #160 which originally requested this feature.
"""

from pathlib import Path

import pytest
import pytest_asyncio
from click.testing import CliRunner
from fastmcp.client import Client

from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.cli import cli
from dacli.mcp_app import create_mcp_server
from dacli.services.validation_service import validate_structure
from dacli.structure_index import StructureIndex

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def docs_with_broken_include(tmp_path: Path) -> Path:
    """Create docs directory with a document that has a broken include."""
    doc = tmp_path / "chapter.adoc"
    doc.write_text(
        "= Chapter\n\n== Section\n\nSome text.\n\ninclude::missing.adoc[]\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def docs_with_valid_include(tmp_path: Path) -> Path:
    """Create docs directory with a document that has a valid include."""
    included = tmp_path / "included.adoc"
    included.write_text("Included content.\n", encoding="utf-8")

    doc = tmp_path / "chapter.adoc"
    doc.write_text(
        "= Chapter\n\n== Section\n\nSome text.\n\ninclude::included.adoc[]\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def docs_with_multiple_broken_includes(tmp_path: Path) -> Path:
    """Create docs directory with multiple broken includes."""
    doc = tmp_path / "chapter.adoc"
    doc.write_text(
        "= Chapter\n\n"
        "include::missing_a.adoc[]\n\n"
        "== Section\n\n"
        "include::missing_b.adoc[]\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest_asyncio.fixture
async def mcp_broken(docs_with_broken_include: Path):
    """MCP client wired to docs with a broken include."""
    mcp = create_mcp_server(docs_root=docs_with_broken_include)
    async with Client(transport=mcp) as client:
        yield client


@pytest_asyncio.fixture
async def mcp_valid(docs_with_valid_include: Path):
    """MCP client wired to docs with a valid include."""
    mcp = create_mcp_server(docs_root=docs_with_valid_include)
    async with Client(transport=mcp) as client:
        yield client


@pytest_asyncio.fixture
async def mcp_multiple_broken(docs_with_multiple_broken_includes: Path):
    """MCP client wired to docs with multiple broken includes."""
    mcp = create_mcp_server(docs_root=docs_with_multiple_broken_includes)
    async with Client(transport=mcp) as client:
        yield client


# ── MCP Tool Tests ────────────────────────────────────────────────────────


class TestMCPValidateUnresolvedIncludes:
    """MCP validate_structure tool detects unresolved includes (Issue #160)."""

    async def test_broken_include_makes_valid_false(self, mcp_broken: Client):
        """validate_structure returns valid=false when an include is missing."""
        result = await mcp_broken.call_tool("validate_structure", arguments={})
        assert result.data["valid"] is False

    async def test_broken_include_reports_error_type(self, mcp_broken: Client):
        """The error entry has type 'unresolved_include'."""
        result = await mcp_broken.call_tool("validate_structure", arguments={})
        error_types = [e["type"] for e in result.data["errors"]]
        assert "unresolved_include" in error_types

    async def test_broken_include_error_has_path_and_message(
        self, mcp_broken: Client
    ):
        """The error entry includes path (file:line) and a descriptive message."""
        result = await mcp_broken.call_tool("validate_structure", arguments={})
        errors = [
            e for e in result.data["errors"] if e["type"] == "unresolved_include"
        ]
        assert len(errors) == 1
        error = errors[0]
        # path should be file:line format
        assert ":" in error["path"]
        # message should mention the missing file
        assert "missing.adoc" in error["message"]

    async def test_valid_include_no_unresolved_error(self, mcp_valid: Client):
        """Valid includes should not produce unresolved_include errors."""
        result = await mcp_valid.call_tool("validate_structure", arguments={})
        error_types = [e["type"] for e in result.data["errors"]]
        assert "unresolved_include" not in error_types

    async def test_multiple_broken_includes_all_reported(
        self, mcp_multiple_broken: Client
    ):
        """Each broken include produces its own error entry."""
        result = await mcp_multiple_broken.call_tool(
            "validate_structure", arguments={}
        )
        errors = [
            e for e in result.data["errors"] if e["type"] == "unresolved_include"
        ]
        assert len(errors) == 2
        messages = [e["message"] for e in errors]
        assert any("missing_a.adoc" in m for m in messages)
        assert any("missing_b.adoc" in m for m in messages)


# ── Service-Layer Tests ───────────────────────────────────────────────────


class TestServiceValidateUnresolvedIncludes:
    """Service-level validate_structure detects unresolved includes (#160)."""

    def test_service_broken_include_detected(
        self, docs_with_broken_include: Path
    ):
        """validate_structure reports unresolved_include for missing file."""
        parser = AsciidocStructureParser(base_path=docs_with_broken_include)
        index = StructureIndex()
        docs = [
            parser.parse_file(f)
            for f in docs_with_broken_include.glob("*.adoc")
        ]
        index.build_from_documents(docs)

        result = validate_structure(index, docs_with_broken_include)

        assert result["valid"] is False
        error_types = [e["type"] for e in result["errors"]]
        assert "unresolved_include" in error_types

    def test_service_valid_include_clean(self, docs_with_valid_include: Path):
        """validate_structure has no unresolved_include for existing file."""
        parser = AsciidocStructureParser(base_path=docs_with_valid_include)
        index = StructureIndex()
        docs = [
            parser.parse_file(f)
            for f in docs_with_valid_include.glob("*.adoc")
        ]
        index.build_from_documents(docs)

        result = validate_structure(index, docs_with_valid_include)

        error_types = [e["type"] for e in result["errors"]]
        assert "unresolved_include" not in error_types


# ── CLI Tests ─────────────────────────────────────────────────────────────


class TestCLIValidateUnresolvedIncludes:
    """CLI validate command detects unresolved includes (Issue #160)."""

    def test_cli_reports_broken_include(self, docs_with_broken_include: Path):
        """CLI validate exits with error and shows unresolved_include."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(docs_with_broken_include), "validate"],
        )
        assert result.exit_code != 0
        assert "unresolved_include" in result.output

    def test_cli_clean_when_include_exists(self, docs_with_valid_include: Path):
        """CLI validate exits cleanly when all includes resolve."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(docs_with_valid_include), "validate"],
        )
        assert result.exit_code == 0
        assert "unresolved_include" not in result.output
