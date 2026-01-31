"""Tests for Issue #219: validate_structure doesn't detect broken includes.

When a document contains an include directive referencing a non-existent file,
validate_structure should report an error.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.cli import cli
from dacli.services.validation_service import validate_structure
from dacli.structure_index import StructureIndex


@pytest.fixture
def temp_doc_with_broken_include(tmp_path: Path) -> Path:
    """Create a temporary directory with a document containing broken include."""
    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Document with Broken Include

== Valid Section

Some content.

include::nonexistent_file.adoc[]

== After Broken Include

More content.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def temp_doc_with_valid_include(tmp_path: Path) -> Path:
    """Create a temporary directory with a document containing valid include."""
    # Create the included file first
    included_file = tmp_path / "included.adoc"
    included_file.write_text("Included content.\n", encoding="utf-8")

    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Document with Valid Include

== Valid Section

Some content.

include::included.adoc[]

== After Include

More content.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestValidateBrokenIncludes:
    """Test that validate_structure detects broken includes."""

    def test_broken_include_reported_as_error(
        self, temp_doc_with_broken_include: Path
    ):
        """Issue #219: Broken includes should be reported as errors."""
        parser = AsciidocStructureParser(base_path=temp_doc_with_broken_include)
        index = StructureIndex()

        # Parse documents
        documents = []
        for doc_file in temp_doc_with_broken_include.glob("*.adoc"):
            doc = parser.parse_file(doc_file)
            documents.append(doc)

        index.build_from_documents(documents)

        # Validate
        result = validate_structure(index, temp_doc_with_broken_include)

        # Should NOT be valid due to broken include
        assert result["valid"] is False, (
            f"Expected valid=False for broken include. Result: {result}"
        )

        # Should have an error about the unresolved include
        error_types = [e["type"] for e in result["errors"]]
        assert "unresolved_include" in error_types, (
            f"Expected 'unresolved_include' error. Errors: {result['errors']}"
        )

        # Error should mention the missing file
        unresolved_errors = [
            e for e in result["errors"] if e["type"] == "unresolved_include"
        ]
        assert len(unresolved_errors) == 1
        assert "nonexistent_file.adoc" in unresolved_errors[0]["message"]

    def test_valid_include_no_error(self, temp_doc_with_valid_include: Path):
        """Valid includes should not cause errors."""
        parser = AsciidocStructureParser(base_path=temp_doc_with_valid_include)
        index = StructureIndex()

        documents = []
        for doc_file in temp_doc_with_valid_include.glob("*.adoc"):
            doc = parser.parse_file(doc_file)
            documents.append(doc)

        index.build_from_documents(documents)

        result = validate_structure(index, temp_doc_with_valid_include)

        # Should be valid
        assert result["valid"] is True

        # Should have no unresolved_include errors
        error_types = [e["type"] for e in result["errors"]]
        assert "unresolved_include" not in error_types


class TestCLIValidateBrokenIncludes:
    """Test CLI validate command with broken includes."""

    def test_cli_validate_reports_broken_include(
        self, temp_doc_with_broken_include: Path
    ):
        """CLI validate should report broken includes."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(temp_doc_with_broken_include), "validate"],
        )

        # Should indicate not valid
        assert "valid: False" in result.output or "valid: false" in result.output.lower()
        assert "unresolved_include" in result.output or "nonexistent_file" in result.output
