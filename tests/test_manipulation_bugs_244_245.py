"""Tests for Issues #244 and #245: manipulation.py bugs.

Bug #245: update_section with preserve_title=False can corrupt document hierarchy
when content has a different heading level than the original section, even without
children. Should always validate heading level matches.

Bug #244: insert_content with position="after" doesn't add a blank line before
the next heading when inserted content itself is a heading.
"""

from pathlib import Path

import pytest

from dacli.file_handler import FileSystemHandler
from dacli.mcp_app import create_mcp_server
from dacli.services.content_service import update_section as service_update_section
from dacli.structure_index import StructureIndex

# ============================================================================
# Bug #245: update_section preserve_title=False heading level validation
# ============================================================================


@pytest.fixture
def adoc_doc_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with an AsciiDoc document."""
    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Test Document

== Section 1

Content of section 1.

== Section 2

Content of section 2.

=== Subsection 2.1

Content of subsection 2.1.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def md_doc_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with a Markdown document."""
    doc_file = tmp_path / "test.md"
    doc_file.write_text(
        """# Test Document

## Section 1

Content of section 1.

## Section 2

Content of section 2.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def index_and_handler(adoc_doc_dir: Path):
    """Create index and file handler for AsciiDoc tests."""
    from dacli.asciidoc_parser import AsciidocStructureParser

    parser = AsciidocStructureParser(base_path=adoc_doc_dir)
    index = StructureIndex()
    file_handler = FileSystemHandler()

    documents = []
    for doc_file in adoc_doc_dir.glob("*.adoc"):
        doc = parser.parse_file(doc_file)
        documents.append(doc)

    index.build_from_documents(documents)

    return index, file_handler


class TestBug245HeadingLevelValidation:
    """Bug #245: preserve_title=False should always validate heading level."""

    def test_same_level_succeeds(self, index_and_handler, adoc_doc_dir: Path):
        """preserve_title=False with same heading level should succeed."""
        index, file_handler = index_and_handler

        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="== Renamed Section 1\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is True

    def test_different_level_without_children_rejected(self, index_and_handler, adoc_doc_dir: Path):
        """Bug #245: preserve_title=False with different heading level should
        fail even when section has NO children."""
        index, file_handler = index_and_handler

        # Section 1 is level 1 (==), try to change to level 2 (===)
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="=== Wrong Level Title\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is False
        assert "error" in result
        assert "heading level" in result["error"].lower()

        # Verify original content is unchanged
        doc_file = adoc_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Section 1" in file_content
        assert "Content of section 1." in file_content

    def test_deeper_level_without_children_rejected(self, index_and_handler, adoc_doc_dir: Path):
        """Bug #245: Changing from level 1 to level 3 should fail."""
        index, file_handler = index_and_handler

        # Section 1 is level 1 (==), try to change to level 3 (====)
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="==== Much Deeper Title\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is False
        assert "heading level" in result["error"].lower()

    def test_shallower_level_without_children_rejected(self, index_and_handler, adoc_doc_dir: Path):
        """Bug #245: Changing to a shallower level should also fail."""
        index, file_handler = index_and_handler

        # Subsection 2.1 is level 2 (===), try to change to level 1 (==)
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-2.subsection-21",
            content="== Too Shallow Title\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is False
        assert "heading level" in result["error"].lower()

    def test_markdown_different_level_rejected(self, md_doc_dir: Path):
        """Bug #245: Markdown heading level mismatch should also be rejected."""
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.models import Document

        parser = MarkdownStructureParser()
        index = StructureIndex()
        file_handler = FileSystemHandler()

        doc_file = md_doc_dir / "test.md"
        md_doc = parser.parse_file(doc_file)
        doc = Document(
            file_path=md_doc.file_path,
            title=md_doc.title,
            sections=md_doc.sections,
            elements=md_doc.elements,
        )
        index.build_from_documents([doc])

        # Section 1 is level 2 (##), try to change to level 3 (###)
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="### Wrong Level\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is False
        assert "heading level" in result["error"].lower()

    def test_with_children_still_rejected(self, index_and_handler, adoc_doc_dir: Path):
        """Existing behavior: section with children + level change still rejected."""
        index, file_handler = index_and_handler

        # Section 2 has children (subsection 2.1), change level should fail
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-2",
            content="=== Wrong Level\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is False
        assert "error" in result


# ============================================================================
# Bug #244: insert_content "after" missing blank line before next heading
# ============================================================================


@pytest.fixture
def md_for_insert(tmp_path: Path) -> Path:
    """Create a Markdown file for testing insert blank line handling."""
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


class TestBug244InsertAfterBlankLine:
    """Bug #244: insert_content after should add blank line before next heading."""

    def _get_insert_tool(self, mcp):
        """Helper to get the insert_content tool from MCP server."""
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "insert_content":
                return tool
        raise AssertionError("insert_content tool not found")

    def test_insert_heading_after_section_blank_line_before_next(self, md_for_insert: Path):
        """Bug #244: When inserting heading content after a section, there should
        be a blank line before the next heading."""
        mcp = create_mcp_server(md_for_insert)
        insert_tool = self._get_insert_tool(mcp)

        # Insert a new heading section after Section 1
        result = insert_tool.fn(
            path="test:section-1",
            position="after",
            content="## New Section\n\nNew content.\n",
        )

        assert result.get("success") is True

        doc_file = md_for_insert / "test.md"
        content = doc_file.read_text()
        lines = content.split("\n")

        # Find "## Section 2" line
        sec2_idx = next(i for i, line in enumerate(lines) if "## Section 2" in line)

        # The line before Section 2 should be blank
        assert lines[sec2_idx - 1].strip() == "", (
            f"Expected blank line before '## Section 2' but got: '{lines[sec2_idx - 1]}'\n"
            f"Full content:\n{content}"
        )

    def test_insert_plain_text_after_section_blank_line_before_next(self, md_for_insert: Path):
        """Inserting plain text after a section should also have blank line
        before next heading."""
        mcp = create_mcp_server(md_for_insert)
        insert_tool = self._get_insert_tool(mcp)

        # Insert plain text (non-heading) after Section 1
        result = insert_tool.fn(
            path="test:section-1",
            position="after",
            content="Some additional paragraph.\n",
        )

        assert result.get("success") is True

        doc_file = md_for_insert / "test.md"
        content = doc_file.read_text()
        lines = content.split("\n")

        # Find "## Section 2" line
        sec2_idx = next(i for i, line in enumerate(lines) if "## Section 2" in line)

        # The line before Section 2 should be blank
        assert lines[sec2_idx - 1].strip() == "", (
            f"Expected blank line before '## Section 2' but got: '{lines[sec2_idx - 1]}'\n"
            f"Full content:\n{content}"
        )

    def test_insert_heading_after_has_blank_line_separation(self, md_for_insert: Path):
        """Inserted heading content should have blank line separation
        from next heading."""
        mcp = create_mcp_server(md_for_insert)
        insert_tool = self._get_insert_tool(mcp)

        # Insert content that ends without trailing blank line
        result = insert_tool.fn(
            path="test:section-1",
            position="after",
            content="## Inserted Heading\n\nInserted body.",
        )

        assert result.get("success") is True

        doc_file = md_for_insert / "test.md"
        content = doc_file.read_text()
        lines = content.split("\n")

        # Find all heading positions
        sec2_idx = next(i for i, line in enumerate(lines) if "## Section 2" in line)
        inserted_idx = next(i for i, line in enumerate(lines) if "## Inserted Heading" in line)

        # Inserted heading should come before Section 2
        assert inserted_idx < sec2_idx

        # There should be a blank line between inserted content and Section 2
        assert lines[sec2_idx - 1].strip() == "", (
            f"Expected blank line before '## Section 2' "
            f"but got: '{lines[sec2_idx - 1]}'\n"
            f"Full content:\n{content}"
        )
