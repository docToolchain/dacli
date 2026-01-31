"""Tests for Issue #217: Update with level change destroys hierarchy.

When using --no-preserve-title and changing the heading level, child sections
lose their parent relationship. This test ensures the operation is rejected
when the level change would break the document hierarchy.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli
from dacli.file_handler import FileSystemHandler
from dacli.services.content_service import update_section as service_update_section
from dacli.structure_index import StructureIndex


@pytest.fixture
def temp_doc_with_children(tmp_path: Path) -> Path:
    """Create a temporary directory with a document that has parent-child sections."""
    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Test Document

== Parent Section

Content of parent section.

=== Child Section

Content of child section.

== Another Section

Content of another section.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def index_and_handler(temp_doc_with_children: Path):
    """Create index and file handler for tests."""
    from dacli.asciidoc_parser import AsciidocStructureParser

    parser = AsciidocStructureParser(base_path=temp_doc_with_children)
    index = StructureIndex()
    file_handler = FileSystemHandler()

    # Parse and index the test documents
    documents = []
    for doc_file in temp_doc_with_children.glob("*.adoc"):
        doc = parser.parse_file(doc_file)
        documents.append(doc)

    index.build_from_documents(documents)

    return index, file_handler


class TestLevelChangeWithChildrenRejected:
    """Test that level changes are rejected when section has children."""

    def test_level_change_with_children_fails(
        self, index_and_handler, temp_doc_with_children: Path
    ):
        """Issue #217: Changing level when section has children should fail."""
        index, file_handler = index_and_handler

        # Try to change parent section from level 1 (==) to level 2 (===)
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:parent-section",
            content="=== Parent Now Level 2\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is False
        assert "error" in result
        # Error should mention level change or children/hierarchy
        error_msg = result["error"].lower()
        assert "level" in error_msg or "children" in error_msg or "hierarchy" in error_msg

        # Verify the original content is unchanged
        doc_file = temp_doc_with_children / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Parent Section" in file_content
        assert "=== Child Section" in file_content

    def test_same_level_with_children_succeeds(
        self, index_and_handler, temp_doc_with_children: Path
    ):
        """Keeping same level when section has children should succeed."""
        index, file_handler = index_and_handler

        # Change title but keep same level (==)
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:parent-section",
            content="== Renamed Parent\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is True

        # Verify the title was changed
        doc_file = temp_doc_with_children / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Renamed Parent" in file_content
        assert "=== Child Section" in file_content  # Child still there

    def test_level_change_without_children_succeeds(
        self, index_and_handler, temp_doc_with_children: Path
    ):
        """Changing level when section has NO children should succeed."""
        index, file_handler = index_and_handler

        # Change child section (which has no children) to different level
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:parent-section.child-section",
            content="==== Now Level 3\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is True

        # Verify the change was made
        doc_file = temp_doc_with_children / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "==== Now Level 3" in file_content


class TestCLILevelChangeValidation:
    """Test CLI --no-preserve-title with level change validation."""

    def test_cli_level_change_with_children_fails(self, temp_doc_with_children: Path):
        """CLI --no-preserve-title with level change on parent should fail."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_with_children),
                "update",
                "test:parent-section",
                "--content",
                "=== Parent Now Level 2\\n\\nNew content.",
                "--no-preserve-title",
            ],
        )

        assert result.exit_code != 0
        # Error should mention level change or children
        error_msg = result.output.lower()
        assert "level" in error_msg or "children" in error_msg or "hierarchy" in error_msg

        # Verify original content unchanged
        doc_file = temp_doc_with_children / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Parent Section" in file_content

    def test_cli_same_level_with_children_succeeds(self, temp_doc_with_children: Path):
        """CLI --no-preserve-title keeping same level should succeed."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_with_children),
                "update",
                "test:parent-section",
                "--content",
                "== Renamed Parent\\n\\nNew content.",
                "--no-preserve-title",
            ],
        )

        assert result.exit_code == 0

        # Verify the change was made
        doc_file = temp_doc_with_children / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Renamed Parent" in file_content
