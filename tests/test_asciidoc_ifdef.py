"""Tests for AsciiDoc ifdef/ifndef conditional block support (Issue #14).

Tests cover:
- ifdef::attr[] / endif::[] - include content when attribute is defined
- ifndef::attr[] / endif::[] - include content when attribute is NOT defined
- Single-line form: ifdef::attr[inline content]
- Nested conditions
- Attribute tracking from :attr: value definitions
- Interaction with existing parser features (sections, elements, includes)
"""

from dacli.asciidoc_parser import AsciidocStructureParser


class TestIfdefBasic:
    """Tests for basic ifdef::attr[] / endif::[] blocks."""

    def test_ifdef_includes_content_when_attr_defined(self, tmp_path):
        """Content inside ifdef block appears when attribute is defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifdef::backend[]
== Visible Section
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Visible Section" in section_titles
        assert "Always Visible" in section_titles

    def test_ifdef_excludes_content_when_attr_not_defined(self, tmp_path):
        """Content inside ifdef block is skipped when attribute is NOT defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document

ifdef::nonexistent[]
== Hidden Section
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Hidden Section" not in section_titles
        assert "Always Visible" in section_titles

    def test_ifdef_with_value_attribute(self, tmp_path):
        """ifdef works when attribute has a value."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:version: 1.0

ifdef::version[]
== Version Info
endif::[]
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Version Info" in section_titles


class TestIfndefBasic:
    """Tests for basic ifndef::attr[] / endif::[] blocks."""

    def test_ifndef_includes_content_when_attr_not_defined(self, tmp_path):
        """Content inside ifndef block appears when attribute is NOT defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document

ifndef::print[]
== Screen Only
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Screen Only" in section_titles
        assert "Always Visible" in section_titles

    def test_ifndef_excludes_content_when_attr_defined(self, tmp_path):
        """Content inside ifndef block is skipped when attribute IS defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:print: true

ifndef::print[]
== Screen Only
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Screen Only" not in section_titles
        assert "Always Visible" in section_titles


class TestSingleLineForm:
    """Tests for single-line ifdef/ifndef form."""

    def test_ifdef_single_line_included(self, tmp_path):
        """Single-line ifdef::attr[content] includes content when attr defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifdef::backend[NOTE: Backend is html]

== Section
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        admonitions = [e for e in doc.elements if e.type == "admonition"]
        assert len(admonitions) == 1
        assert admonitions[0].attributes.get("admonition_type") == "NOTE"

    def test_ifdef_single_line_excluded(self, tmp_path):
        """Single-line ifdef::attr[content] skips content when attr not defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document

ifdef::nonexistent[NOTE: This should not appear]

== Section
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        admonitions = [e for e in doc.elements if e.type == "admonition"]
        assert len(admonitions) == 0

    def test_ifndef_single_line_included(self, tmp_path):
        """Single-line ifndef::attr[content] includes when attr not defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document

ifndef::nonexistent[NOTE: This should appear]

== Section
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        admonitions = [e for e in doc.elements if e.type == "admonition"]
        assert len(admonitions) == 1

    def test_ifndef_single_line_excluded(self, tmp_path):
        """Single-line ifndef::attr[content] skips when attr IS defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifndef::backend[NOTE: This should not appear]

== Section
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        admonitions = [e for e in doc.elements if e.type == "admonition"]
        assert len(admonitions) == 0


class TestNestedConditions:
    """Tests for nested ifdef/ifndef blocks."""

    def test_nested_ifdef_both_true(self, tmp_path):
        """Nested ifdef blocks: both conditions true -> content visible."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html
:format: web

ifdef::backend[]
ifdef::format[]
== Nested Visible
endif::[]
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Nested Visible" in section_titles

    def test_nested_ifdef_outer_false(self, tmp_path):
        """Nested ifdef: outer condition false -> all content hidden."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:format: web

ifdef::nonexistent[]
ifdef::format[]
== Should Be Hidden
endif::[]
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Should Be Hidden" not in section_titles
        assert "Always Visible" in section_titles

    def test_nested_ifdef_inner_false(self, tmp_path):
        """Nested ifdef: inner condition false -> inner content hidden."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifdef::backend[]
== Outer Visible
ifdef::nonexistent[]
== Inner Hidden
endif::[]
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Outer Visible" in section_titles
        assert "Inner Hidden" not in section_titles
        assert "Always Visible" in section_titles

    def test_nested_ifndef_inside_ifdef(self, tmp_path):
        """ifndef nested inside ifdef works correctly."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifdef::backend[]
ifndef::print[]
== Web Only Content
endif::[]
endif::[]
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Web Only Content" in section_titles


class TestAttributeTracking:
    """Tests for attribute tracking from :attr: value definitions."""

    def test_attributes_defined_before_ifdef_are_tracked(self, tmp_path):
        """Attributes defined in document header are available for ifdef."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:sectnums:
:toc:
:custom-attr: value

ifdef::custom-attr[]
== Custom Section
endif::[]
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Custom Section" in section_titles

    def test_attribute_without_value_is_still_defined(self, tmp_path):
        """Attribute set as :attr: (empty value) is still considered defined."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:sectnums:

ifdef::sectnums[]
== Numbered Section
endif::[]
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Numbered Section" in section_titles


class TestEndifVariants:
    """Tests for endif directive variants."""

    def test_endif_with_attribute_name(self, tmp_path):
        """endif::attr[] (with attribute name) works as block closer."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifdef::backend[]
== Visible
endif::backend[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Visible" in section_titles
        assert "Always Visible" in section_titles

    def test_endif_without_attribute_name(self, tmp_path):
        """endif::[] (without attribute name) works as block closer."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifdef::backend[]
== Visible
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Visible" in section_titles
        assert "Always Visible" in section_titles


class TestConditionalWithElements:
    """Tests for conditional blocks interacting with elements."""

    def test_ifdef_hides_code_block(self, tmp_path):
        """Code block inside false ifdef is not extracted as element."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document

== Section

ifdef::nonexistent[]
[source,python]
----
def hidden():
    pass
----
endif::[]

[source,python]
----
def visible():
    pass
----
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        code_elements = [e for e in doc.elements if e.type == "code"]
        assert len(code_elements) == 1
        assert "visible" in code_elements[0].attributes.get("content", "")

    def test_ifdef_hides_admonition(self, tmp_path):
        """Admonition inside false ifdef is not extracted as element."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document

== Section

ifdef::nonexistent[]
WARNING: This should be hidden
endif::[]

NOTE: This should be visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        admonitions = [e for e in doc.elements if e.type == "admonition"]
        assert len(admonitions) == 1
        assert admonitions[0].attributes.get("admonition_type") == "NOTE"

    def test_ifdef_hides_image(self, tmp_path):
        """Image inside false ifdef is not extracted as element."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document

== Section

ifdef::nonexistent[]
image::hidden.png[Hidden]
endif::[]

image::visible.png[Visible]
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        images = [e for e in doc.elements if e.type == "image"]
        assert len(images) == 1
        assert images[0].attributes.get("target") == "visible.png"


class TestConditionalWithIncludes:
    """Tests for conditional blocks interacting with include directives."""

    def test_ifdef_hides_include(self, tmp_path):
        """Include directive inside false ifdef is not processed."""
        included = tmp_path / "included.adoc"
        included.write_text("== Included Section\n\nContent from include.\n")

        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document

ifdef::nonexistent[]
include::included.adoc[]
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Included Section" not in section_titles
        assert "Always Visible" in section_titles

    def test_ifdef_includes_include_when_true(self, tmp_path):
        """Include directive inside true ifdef IS processed."""
        included = tmp_path / "included.adoc"
        included.write_text("== Included Section\n\nContent from include.\n")

        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifdef::backend[]
include::included.adoc[]
endif::[]

== Always Visible
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "Included Section" in section_titles
        assert "Always Visible" in section_titles


class TestRealWorldPatterns:
    """Tests based on real-world AsciiDoc patterns commonly seen in projects."""

    def test_imagesdir_conditional(self, tmp_path):
        """Common pattern: ifndef::imagesdir[:imagesdir: default] works."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
ifndef::imagesdir[:imagesdir: ./images]

= Test Document

== Section

image::diagram.png[Diagram]
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        assert doc.attributes.get("imagesdir") == "./images"

    def test_multiple_ifdef_blocks(self, tmp_path):
        """Multiple sequential ifdef/endif blocks work correctly."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
= Test Document
:backend: html

ifdef::backend[]
== HTML Section
endif::[]

ifdef::nonexistent[]
== Hidden Section
endif::[]

ifdef::backend[]
== Another HTML Section
endif::[]
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        section_titles = [s.title for s in doc.sections[0].children]
        assert "HTML Section" in section_titles
        assert "Hidden Section" not in section_titles
        assert "Another HTML Section" in section_titles

    def test_spec_file_ifdef_pattern(self, tmp_path):
        """Pattern from actual spec file: ifndef at file start."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""\
:jbake-title: Test Spec
:jbake-type: page_toc
ifndef::imagesdir[:imagesdir: ../../images]

= Test Specification

== Introduction

Content here.
""")
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)

        assert doc.title == "Test Specification"
        assert "imagesdir" in doc.attributes
