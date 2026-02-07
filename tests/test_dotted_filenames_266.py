"""Tests for dotted filenames producing unique paths (Issue #266)."""

from dacli.markdown_parser import MarkdownStructureParser
from dacli.structure_index import StructureIndex


class TestDottedFilenames:
    """Files with dots in names (e.g. version numbers) must have unique paths."""

    def test_version_numbered_files_have_unique_paths(self, tmp_path):
        """DACLI_TEST_RESULTS_v0.4.27.md and v0.4.28.md must not collide."""
        f1 = tmp_path / "RESULTS_v0.4.27.md"
        f2 = tmp_path / "RESULTS_v0.4.28.md"
        f1.write_text("# Results v0.4.27\n\nContent.\n")
        f2.write_text("# Results v0.4.28\n\nContent.\n")

        parser = MarkdownStructureParser(base_path=tmp_path)
        doc1 = parser.parse_file(f1)
        doc2 = parser.parse_file(f2)

        index = StructureIndex()
        warnings = index.build_from_documents([doc1, doc2])

        assert len(warnings) == 0, f"Unexpected warnings: {warnings}"

        structure = index.get_structure()
        paths = [s["path"] for s in structure["sections"]]
        assert len(paths) == len(set(paths)), f"Duplicate paths found: {paths}"

    def test_cli_context_passes_base_path_to_markdown_parser(self, tmp_path):
        """CliContext must pass docs_root as base_path to MarkdownStructureParser."""
        from dacli.cli import CliContext

        f1 = tmp_path / "test_v1.2.3.md"
        f1.write_text("# Test v1.2.3\n")

        ctx = CliContext(
            docs_root=tmp_path,
            output_format="json",
            pretty=False,
        )
        # The markdown parser should have base_path set
        assert ctx.markdown_parser.base_path == tmp_path

    def test_file_prefix_without_base_path_strips_only_known_extensions(self, tmp_path):
        """Without base_path, only .md extension should be stripped, not version dots."""
        f1 = tmp_path / "report_v2.1.5.md"
        f1.write_text("# Report\n")

        # BUG #266: Without base_path, Path(stem).with_suffix("") strips ".5"
        parser = MarkdownStructureParser()  # No base_path!
        doc = parser.parse_file(f1)

        # The path should preserve the full version number
        assert doc.sections[0].path == "report_v2.1.5"

    def test_get_file_prefix_preserves_version_dots(self, tmp_path):
        """_get_file_prefix must not strip version-like suffixes."""
        parser = MarkdownStructureParser(base_path=tmp_path)
        prefix = parser._get_file_prefix(tmp_path / "data_v3.2.1.md")
        assert prefix == "data_v3.2.1"

    def test_subdirectory_file_with_dots(self, tmp_path):
        """Files with dots in subdirectories also get correct paths."""
        sub = tmp_path / "reports"
        sub.mkdir()
        f1 = sub / "sprint_2.0.1.md"
        f1.write_text("# Sprint 2.0.1\n\nNotes.\n")

        parser = MarkdownStructureParser(base_path=tmp_path)
        doc = parser.parse_file(f1)

        assert doc.sections[0].path == "reports/sprint_2.0.1"


class TestDottedFilenamesAsciiDoc:
    """AsciiDoc files with dots in names must also have unique paths."""

    def test_asciidoc_file_with_version_dots(self, tmp_path):
        """AsciiDoc _get_file_prefix must preserve version dots."""
        from dacli.asciidoc_parser import AsciidocStructureParser

        f1 = tmp_path / "release_v1.2.3.adoc"
        f1.write_text("= Release v1.2.3\n\nContent.\n")

        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(f1)

        assert doc.sections[0].path == "release_v1.2.3"
