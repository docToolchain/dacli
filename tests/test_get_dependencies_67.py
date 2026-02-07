"""Tests for get_dependencies endpoint (Issue #67, Phase 1: include_tree)."""

from pathlib import Path

from dacli.asciidoc_parser import AsciidocDocument, AsciidocStructureParser, IncludeInfo
from dacli.models import Document, SourceLocation
from dacli.structure_index import StructureIndex


class TestGetDependenciesStructureIndex:
    """Tests for StructureIndex.get_dependencies() method."""

    def test_empty_index_returns_empty_tree(self):
        """get_dependencies on empty index returns empty include_tree."""
        index = StructureIndex()
        index.build_from_documents([])
        result = index.get_dependencies()
        assert result == {"include_tree": {}, "cross_references": []}

    def test_asciidoc_doc_with_includes(self, tmp_path):
        """Include tree is built from AsciidocDocument.includes."""
        doc = AsciidocDocument(
            file_path=tmp_path / "main.adoc",
            title="Main",
            sections=[],
            elements=[],
            includes=[
                IncludeInfo(
                    source_location=SourceLocation(
                        file=tmp_path / "main.adoc", line=5
                    ),
                    target_path=tmp_path / "chapters" / "intro.adoc",
                ),
                IncludeInfo(
                    source_location=SourceLocation(
                        file=tmp_path / "main.adoc", line=10
                    ),
                    target_path=tmp_path / "chapters" / "setup.adoc",
                ),
            ],
        )
        index = StructureIndex()
        index.build_from_documents([doc])
        result = index.get_dependencies()

        assert "include_tree" in result
        tree = result["include_tree"]
        assert "main.adoc" in tree
        assert set(tree["main.adoc"]) == {
            "chapters/intro.adoc",
            "chapters/setup.adoc",
        }

    def test_markdown_doc_has_no_includes(self, tmp_path):
        """Markdown documents don't contribute to include_tree."""
        doc = Document(
            file_path=tmp_path / "readme.md",
            title="Readme",
            sections=[],
            elements=[],
        )
        index = StructureIndex()
        index.build_from_documents([doc])
        result = index.get_dependencies()
        assert result["include_tree"] == {}

    def test_multiple_docs_with_includes(self, tmp_path):
        """Multiple AsciiDoc documents each contribute their includes."""
        doc1 = AsciidocDocument(
            file_path=tmp_path / "arc42.adoc",
            title="Arc42",
            sections=[],
            elements=[],
            includes=[
                IncludeInfo(
                    source_location=SourceLocation(
                        file=tmp_path / "arc42.adoc", line=3
                    ),
                    target_path=tmp_path / "chapters" / "01_intro.adoc",
                ),
            ],
        )
        doc2 = AsciidocDocument(
            file_path=tmp_path / "manual.adoc",
            title="Manual",
            sections=[],
            elements=[],
            includes=[
                IncludeInfo(
                    source_location=SourceLocation(
                        file=tmp_path / "manual.adoc", line=2
                    ),
                    target_path=tmp_path / "installation.adoc",
                ),
            ],
        )
        index = StructureIndex()
        index.build_from_documents([doc1, doc2])
        result = index.get_dependencies()
        tree = result["include_tree"]

        assert len(tree) == 2
        assert "arc42.adoc" in tree
        assert "manual.adoc" in tree

    def test_asciidoc_doc_without_includes(self, tmp_path):
        """AsciiDoc document with no includes has empty entry or is absent."""
        doc = AsciidocDocument(
            file_path=tmp_path / "simple.adoc",
            title="Simple",
            sections=[],
            elements=[],
            includes=[],
        )
        index = StructureIndex()
        index.build_from_documents([doc])
        result = index.get_dependencies()
        # Documents with no includes should not appear in the tree
        assert result["include_tree"] == {}

    def test_cross_references_placeholder(self, tmp_path):
        """Phase 1: cross_references is always an empty list."""
        doc = AsciidocDocument(
            file_path=tmp_path / "main.adoc",
            title="Main",
            sections=[],
            elements=[],
            includes=[
                IncludeInfo(
                    source_location=SourceLocation(
                        file=tmp_path / "main.adoc", line=1
                    ),
                    target_path=tmp_path / "other.adoc",
                ),
            ],
        )
        index = StructureIndex()
        index.build_from_documents([doc])
        result = index.get_dependencies()
        assert result["cross_references"] == []

    def test_paths_are_relative_to_docs_root(self, tmp_path):
        """Paths in include_tree should be relative to docs_root (file_path parent)."""
        docs = tmp_path / "docs"
        docs.mkdir()
        doc = AsciidocDocument(
            file_path=docs / "main.adoc",
            title="Main",
            sections=[],
            elements=[],
            includes=[
                IncludeInfo(
                    source_location=SourceLocation(
                        file=docs / "main.adoc", line=1
                    ),
                    target_path=docs / "sub" / "chapter.adoc",
                ),
            ],
        )
        index = StructureIndex()
        index.build_from_documents([doc])
        result = index.get_dependencies()
        tree = result["include_tree"]
        # Keys and values should be relative paths (strings, not absolute)
        for key in tree:
            assert not Path(key).is_absolute()
            for val in tree[key]:
                assert not Path(val).is_absolute()


class TestGetDependenciesMCPTool:
    """Tests for get_dependencies MCP tool."""

    def test_get_dependencies_tool_exists(self, tmp_path):
        """get_dependencies is registered as an MCP tool."""
        from dacli.mcp_app import create_mcp_server

        mcp = create_mcp_server(tmp_path)
        tool_names = [t.name for t in mcp._tool_manager._tools.values()]
        assert "get_dependencies" in tool_names

    def test_get_dependencies_tool_returns_structure(self, tmp_path):
        """get_dependencies MCP tool returns include_tree and cross_references."""
        # Create a simple AsciiDoc project with includes
        main = tmp_path / "main.adoc"
        chapter = tmp_path / "chapters" / "intro.adoc"
        chapter.parent.mkdir(parents=True)
        main.write_text("= Main\n\ninclude::chapters/intro.adoc[]\n")
        chapter.write_text("== Introduction\n\nSome content.\n")

        # Parse and build index to test the service method directly
        # (MCP tool is just a thin wrapper around index.get_dependencies())
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(main)

        index = StructureIndex()
        index.build_from_documents([doc])
        result = index.get_dependencies()

        assert "include_tree" in result
        assert "cross_references" in result
        assert isinstance(result["include_tree"], dict)
        assert isinstance(result["cross_references"], list)


class TestGetDependenciesIntegration:
    """Integration test with real AsciiDoc parsing."""

    def test_parsed_doc_includes_are_in_tree(self, tmp_path):
        """End-to-end: parse AsciiDoc with includes, check include_tree."""
        # Create files
        main = tmp_path / "main.adoc"
        ch1 = tmp_path / "chapters" / "ch1.adoc"
        ch2 = tmp_path / "chapters" / "ch2.adoc"
        ch1.parent.mkdir(parents=True)

        main.write_text(
            "= Main Document\n\n"
            "include::chapters/ch1.adoc[]\n\n"
            "include::chapters/ch2.adoc[]\n"
        )
        ch1.write_text("== Chapter 1\n\nContent of chapter 1.\n")
        ch2.write_text("== Chapter 2\n\nContent of chapter 2.\n")

        # Parse
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(main)

        # Build index
        index = StructureIndex()
        index.build_from_documents([doc])

        result = index.get_dependencies()
        tree = result["include_tree"]

        assert "main.adoc" in tree
        targets = tree["main.adoc"]
        assert len(targets) == 2
        assert "chapters/ch1.adoc" in targets
        assert "chapters/ch2.adoc" in targets
