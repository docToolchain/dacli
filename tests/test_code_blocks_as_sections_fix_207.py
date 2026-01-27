"""Tests for Issue #207: Code blocks are parsed as sections.

These tests verify that headings/sections inside code blocks and other
delimited blocks are NOT parsed as document sections.
"""

from pathlib import Path

import pytest

from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.markdown_parser import MarkdownStructureParser


class TestAsciiDocCodeBlocks:
    """Test that AsciiDoc code blocks don't create phantom sections."""

    @pytest.fixture
    def parser(self, tmp_path: Path) -> AsciidocStructureParser:
        """Create parser instance."""
        return AsciidocStructureParser(base_path=tmp_path)

    def test_source_block_with_section_marker(self, parser, tmp_path: Path):
        """Section markers inside source blocks should be ignored (Issue #207)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section with Code

[source,asciidoc]
----
== This looks like a section but is code
Should not be parsed as section
----

== Real Next Section

Content here.
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        # Should have 3 sections: document title + 2 real sections
        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        assert len(all_sections) == 3
        section_titles = [s.title for s in all_sections]
        assert "Document" in section_titles
        assert "Section with Code" in section_titles
        assert "Real Next Section" in section_titles
        # The phantom section should NOT exist
        assert "This looks like a section but is code" not in section_titles

    def test_listing_block_with_section_marker(self, parser, tmp_path: Path):
        """Section markers inside listing blocks should be ignored (Issue #207)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section

----
== This is inside a listing block
Not a real section
----

== Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "This is inside a listing block" not in section_titles

    def test_literal_block_with_section_marker(self, parser, tmp_path: Path):
        """Section markers inside literal blocks (....) should be ignored (Issue #207)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section

....
== This is inside a literal block
Not a real section
....

== Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "This is inside a literal block" not in section_titles

    def test_sidebar_block_with_section_marker(self, parser, tmp_path: Path):
        """Section markers inside sidebar blocks (****) should be ignored (Issue #207)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section

****
== This is inside a sidebar block
Not a real section
****

== Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "This is inside a sidebar block" not in section_titles

    def test_example_block_with_section_marker(self, parser, tmp_path: Path):
        """Section markers inside example blocks (====) should be ignored (Issue #207)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section

====
== This is inside an example block
Not a real section
====

== Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "This is inside an example block" not in section_titles

    def test_quote_block_with_section_marker(self, parser, tmp_path: Path):
        """Section markers inside quote blocks (____) should be ignored (Issue #207)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section

____
== This is inside a quote block
Not a real section
____

== Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "This is inside a quote block" not in section_titles

    def test_table_with_section_marker(self, parser, tmp_path: Path):
        """Section markers inside tables should be ignored (Issue #207)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section

|===
| Column 1 | Column 2

| == Not a section | Data
|===

== Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "Not a section" not in section_titles

    def test_multiple_code_blocks_with_sections(self, parser, tmp_path: Path):
        """Multiple code blocks with section markers should all be ignored (Issue #207)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== First Section

[source,asciidoc]
----
== Phantom 1
----

== Second Section

[source,markdown]
----
## Phantom 2
----

== Third Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        # Should have 4 sections: document + 3 real sections
        assert len(all_sections) == 4
        section_titles = [s.title for s in all_sections]
        assert "Phantom 1" not in section_titles
        assert "Phantom 2" not in section_titles

    def test_nested_block_example(self, parser, tmp_path: Path):
        """Code block showing another code block should not create phantom sections."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== How to Write AsciiDoc

This example shows AsciiDoc syntax:

[source,asciidoc]
----
== Example Section

[source,python]
\\----
print("hello")
\\----
----

== Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "Example Section" not in section_titles  # Inside code block

    def test_real_sections_still_work(self, parser, tmp_path: Path):
        """Real sections outside blocks should still be parsed correctly (regression)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document Title

== Chapter 1

Content 1

=== Subsection 1.1

Content 1.1

== Chapter 2

Content 2
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        # Should have all real sections
        assert len(all_sections) == 4
        section_titles = [s.title for s in all_sections]
        assert "Document Title" in section_titles
        assert "Chapter 1" in section_titles
        assert "Subsection 1.1" in section_titles
        assert "Chapter 2" in section_titles


class TestMarkdownCodeBlocks:
    """Test that Markdown code blocks don't create phantom sections."""

    @pytest.fixture
    def parser(self, tmp_path: Path) -> MarkdownStructureParser:
        """Create parser instance."""
        return MarkdownStructureParser(base_path=tmp_path)

    def test_fenced_code_block_with_heading(self, parser, tmp_path: Path):
        """Headings inside fenced code blocks should be ignored (Issue #207)."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """# Document

## Section with Code

```markdown
## This looks like a heading but is code
Should not be parsed as section
```

## Real Next Section

Content here.
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "Document" in section_titles
        assert "Section with Code" in section_titles
        assert "Real Next Section" in section_titles
        # The phantom section should NOT exist
        assert "This looks like a heading but is code" not in section_titles

    def test_multiple_heading_levels_in_code(self, parser, tmp_path: Path):
        """Multiple heading levels inside code blocks should all be ignored."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """# Document

## Section

```
# H1 in code
## H2 in code
### H3 in code
```

## Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "H1 in code" not in section_titles
        assert "H2 in code" not in section_titles
        assert "H3 in code" not in section_titles

    def test_code_fence_with_language_specifier(self, parser, tmp_path: Path):
        """Code blocks with language specifiers should ignore headings."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """# Document

## API Documentation

```python
# Not a markdown heading, just a Python comment
## Also not a heading
def hello():
    pass
```

## Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "Not a markdown heading, just a Python comment" not in section_titles
        assert "Also not a heading" not in section_titles

    def test_tildes_code_fence(self, parser, tmp_path: Path):
        """Tilde code fences (~~~) should also prevent heading parsing."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """# Document

## Section

~~~
## Heading inside tildes
~~~

## Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "Heading inside tildes" not in section_titles

    def test_multiple_code_blocks(self, parser, tmp_path: Path):
        """Multiple code blocks with headings should all be handled correctly."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """# Document

## First Section

```
## Phantom 1
```

## Second Section

```markdown
# Phantom 2
```

## Third Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        assert "Phantom 1" not in section_titles
        assert "Phantom 2" not in section_titles

    def test_real_headings_still_work(self, parser, tmp_path: Path):
        """Real headings outside code blocks should still be parsed (regression)."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """# Document Title

## Chapter 1

Content 1

### Subsection 1.1

Content 1.1

## Chapter 2

Content 2
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        # Should have all real sections
        section_titles = [s.title for s in all_sections]
        assert "Document Title" in section_titles
        assert "Chapter 1" in section_titles
        assert "Subsection 1.1" in section_titles
        assert "Chapter 2" in section_titles

    def test_blockquote_with_heading_is_already_safe(self, parser, tmp_path: Path):
        """Blockquotes with headings don't match HEADING_PATTERN (verification test)."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """# Document

## Section

> ## This is a quoted heading
> Not a real section

## Next Section
""",
            encoding="utf-8",
        )

        doc = parser.parse_file(test_file)

        all_sections = []
        def collect(sections):
            for s in sections:
                all_sections.append(s)
                collect(s.children)
        collect(doc.sections)

        section_titles = [s.title for s in all_sections]
        # Blockquotes already don't match because pattern starts with ^#{1,6}
        assert "This is a quoted heading" not in section_titles
