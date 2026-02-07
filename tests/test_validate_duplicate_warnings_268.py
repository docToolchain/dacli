"""Tests for duplicate-path warnings in JSON validate output (Issue #268)."""

from dacli.models import Document, Section, SourceLocation
from dacli.services.validation_service import validate_structure
from dacli.structure_index import StructureIndex


class TestDuplicatePathWarningsInValidation:
    """Duplicate-path warnings must appear in validate_structure JSON output."""

    def test_duplicate_paths_appear_in_validation_warnings(self, tmp_path):
        """When documents have duplicate section paths, validate reports them."""
        doc1 = Document(
            file_path=tmp_path / "a.md",
            title="A",
            sections=[
                Section(
                    title="Introduction",
                    level=1,
                    path="intro",
                    source_location=SourceLocation(file=tmp_path / "a.md", line=1),
                )
            ],
            elements=[],
        )
        doc2 = Document(
            file_path=tmp_path / "b.md",
            title="B",
            sections=[
                Section(
                    title="Introduction",
                    level=1,
                    path="intro",  # Same path as doc1!
                    source_location=SourceLocation(file=tmp_path / "b.md", line=1),
                )
            ],
            elements=[],
        )

        index = StructureIndex()
        build_warnings = index.build_from_documents([doc1, doc2])
        assert len(build_warnings) > 0, "Should have duplicate path warnings"

        result = validate_structure(index, tmp_path)
        warning_types = [w["type"] for w in result["warnings"]]
        assert "duplicate_path" in warning_types, (
            f"duplicate_path not in warnings: {result['warnings']}"
        )

    def test_duplicate_path_warning_includes_details(self, tmp_path):
        """Duplicate path warning includes path, files and line numbers."""
        doc1 = Document(
            file_path=tmp_path / "a.md",
            title="A",
            sections=[
                Section(
                    title="Setup",
                    level=1,
                    path="setup",
                    source_location=SourceLocation(file=tmp_path / "a.md", line=5),
                )
            ],
            elements=[],
        )
        doc2 = Document(
            file_path=tmp_path / "b.md",
            title="B",
            sections=[
                Section(
                    title="Setup",
                    level=1,
                    path="setup",
                    source_location=SourceLocation(file=tmp_path / "b.md", line=3),
                )
            ],
            elements=[],
        )

        index = StructureIndex()
        index.build_from_documents([doc1, doc2])

        result = validate_structure(index, tmp_path)
        dup_warnings = [w for w in result["warnings"] if w["type"] == "duplicate_path"]
        assert len(dup_warnings) == 1

        warning = dup_warnings[0]
        assert warning["path"] == "setup"
        assert "message" in warning

    def test_no_duplicate_warnings_when_paths_unique(self, tmp_path):
        """No duplicate_path warnings when all paths are unique."""
        doc = Document(
            file_path=tmp_path / "a.md",
            title="A",
            sections=[
                Section(
                    title="Intro",
                    level=1,
                    path="intro",
                    source_location=SourceLocation(file=tmp_path / "a.md", line=1),
                )
            ],
            elements=[],
        )

        index = StructureIndex()
        index.build_from_documents([doc])

        result = validate_structure(index, tmp_path)
        dup_warnings = [w for w in result["warnings"] if w["type"] == "duplicate_path"]
        assert len(dup_warnings) == 0
