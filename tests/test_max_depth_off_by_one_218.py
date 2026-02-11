"""Tests for Issue #218: get_structure max_depth off-by-one error.

The max_depth parameter should include sections up to that depth,
not depth-1.
"""

from pathlib import Path

import pytest

from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.structure_index import StructureIndex


@pytest.fixture
def temp_nested_doc(tmp_path: Path) -> Path:
    """Create a temporary directory with nested sections."""
    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Document

== Level 1 Section

Content level 1.

=== Level 2 Section

Content level 2.

==== Level 3 Section

Content level 3.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def index(temp_nested_doc: Path) -> StructureIndex:
    """Build index from test document."""
    parser = AsciidocStructureParser(base_path=temp_nested_doc)
    index = StructureIndex()

    documents = []
    for doc_file in temp_nested_doc.glob("*.adoc"):
        doc = parser.parse_file(doc_file)
        documents.append(doc)

    index.build_from_documents(documents)
    return index


def count_sections_by_depth(structure: dict, depth: int = 0) -> dict[int, int]:
    """Count sections at each depth level."""
    counts: dict[int, int] = {}

    def count_recursive(items: list, current_depth: int):
        for item in items:
            counts[current_depth] = counts.get(current_depth, 0) + 1
            if "children" in item:
                count_recursive(item["children"], current_depth + 1)

    if "documents" in structure:
        count_recursive(structure["documents"], 0)
    elif "sections" in structure:
        count_recursive(structure["sections"], 0)

    return counts


class TestMaxDepthBehavior:
    """Test that max_depth correctly limits section depth."""

    def test_max_depth_0_shows_only_root(self, index: StructureIndex):
        """max_depth=0 should show only the document root (no children)."""
        structure = index.get_structure(max_depth=0)

        counts = count_sections_by_depth(structure)
        max_visible_depth = max(counts.keys()) if counts else -1

        assert max_visible_depth == 0, f"max_depth=0 should show only depth 0. Counts: {counts}"

    def test_max_depth_1_shows_root_and_children(self, index: StructureIndex):
        """max_depth=1 should show root AND direct children (depth 0 and 1)."""
        structure = index.get_structure(max_depth=1)

        counts = count_sections_by_depth(structure)
        max_visible_depth = max(counts.keys()) if counts else -1

        # Issue #218: This was returning 0 instead of 1
        assert max_visible_depth == 1, f"max_depth=1 should show depths 0 and 1. Counts: {counts}"
        assert 1 in counts, f"Should have sections at depth 1. Counts: {counts}"

    def test_max_depth_2_shows_three_levels(self, index: StructureIndex):
        """max_depth=2 should show depths 0, 1, and 2."""
        structure = index.get_structure(max_depth=2)

        counts = count_sections_by_depth(structure)
        max_visible_depth = max(counts.keys()) if counts else -1

        # Issue #218: This was returning 1 instead of 2
        assert (
            max_visible_depth == 2
        ), f"max_depth=2 should show depths 0, 1, and 2. Counts: {counts}"
        assert 2 in counts, f"Should have sections at depth 2. Counts: {counts}"

    def test_max_depth_none_shows_all(self, index: StructureIndex):
        """max_depth=None should show all levels."""
        structure = index.get_structure(max_depth=None)

        counts = count_sections_by_depth(structure)
        max_visible_depth = max(counts.keys()) if counts else -1

        # Our test doc has 3 levels (0, 1, 2, 3 for doc + 3 section levels)
        assert max_visible_depth >= 2, f"max_depth=None should show all levels. Counts: {counts}"
