"""Property-based tests using Hypothesis.

These tests generate hundreds of random inputs to verify that our
parser utilities handle edge cases correctly and never crash.
"""

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from dacli.parser_utils import slugify, strip_doc_extension


class TestSlugifyProperties:
    """Property-based tests for the slugify function."""

    @given(st.text())
    def test_slugify_never_crashes(self, text):
        """Slugify should handle any text input without crashing."""
        result = slugify(text)
        assert isinstance(result, str)

    @given(st.text(min_size=1))
    def test_slugify_returns_lowercase(self, text):
        """Slugify output should always be lowercase."""
        result = slugify(text)
        assert result == result.lower()

    @given(st.text())
    def test_slugify_no_leading_trailing_dashes(self, text):
        """Slugify should not have leading or trailing dashes."""
        result = slugify(text)
        if result:  # Only check if result is non-empty
            assert not result.startswith("-")
            assert not result.endswith("-")

    @given(st.text())
    def test_slugify_no_multiple_dashes(self, text):
        """Slugify should collapse multiple dashes into one."""
        result = slugify(text)
        assert "--" not in result

    @given(st.text())
    def test_slugify_no_spaces_or_underscores(self, text):
        """Slugify should replace spaces and underscores with dashes."""
        result = slugify(text)
        assert " " not in result
        assert "_" not in result

    @given(st.text())
    def test_slugify_idempotent(self, text):
        """Applying slugify twice should give the same result."""
        first = slugify(text)
        second = slugify(first)
        assert first == second


class TestStripDocExtensionProperties:
    """Property-based tests for strip_doc_extension function."""

    @given(st.text(min_size=1))
    def test_strip_doc_extension_never_crashes(self, path_str):
        """strip_doc_extension should handle any path string."""
        try:
            path = Path(path_str)
            result = strip_doc_extension(path)
            assert isinstance(result, str)
        except (ValueError, OSError):
            # Some strings are not valid paths on all systems (e.g., null bytes)
            pass

    @given(
        st.text(
            alphabet=st.characters(
                blacklist_categories=("Cc", "Cs"),
                # Exclude path separators and invalid filename characters
                blacklist_characters="\x00\\/:",
            ),
            min_size=1,
        ),
        st.sampled_from([".md", ".adoc", ".asciidoc", ".txt", ".pdf", ""]),
    )
    def test_strip_only_known_extensions(self, basename, extension):
        """Only known doc extensions (.md, .adoc, .asciidoc) should be stripped."""
        path = Path(basename + extension)
        result = strip_doc_extension(path)

        # Known extensions should be removed
        if extension in {".md", ".adoc", ".asciidoc"}:
            assert not result.endswith(extension)
        # Unknown extensions should be preserved
        elif extension:
            assert result.endswith(extension)

    @given(
        st.text(
            alphabet=st.characters(
                blacklist_categories=("Cc", "Cs"),
                # Exclude characters that would be path separators or invalid in filenames
                blacklist_characters="\x00\\/:",
            ),
            min_size=1,
        )
    )
    def test_strip_preserves_dots_in_filename(self, filename):
        """Dots in filenames (like version numbers) should be preserved."""
        # Create a filename with version-like dots
        versioned = f"report_v1.2.3_{filename}"
        path = Path(versioned + ".md")
        result = strip_doc_extension(path)

        # Should remove .md extension but preserve internal dots
        # The version number should always be preserved
        assert "1.2.3" in result

    @given(st.text(alphabet=st.characters(blacklist_categories=("Cc", "Cs"))))
    def test_strip_uses_forward_slashes(self, path_str):
        """Result should use forward slashes, not backslashes."""
        try:
            path = Path(path_str)
            result = strip_doc_extension(path)
            # On Windows, Path uses backslashes, but our function should convert
            assert "\\" not in result
        except (ValueError, OSError):
            pass


class TestParserInvariants:
    """Property-based tests for parser invariants."""

    @given(st.text(), st.text())
    def test_slugify_concatenation_property(self, text1, text2):
        """Test that slugifying parts and joining is similar to slugifying whole.

        While not always identical (due to dash collapsing), both should be valid slugs.
        """
        slug1 = slugify(text1)
        slug2 = slugify(text2)
        combined_slug = slugify(text1 + " " + text2)

        # Both should be valid slugs (no multiple dashes, no leading/trailing dashes)
        for slug in [slug1, slug2, combined_slug]:
            if slug:
                assert not slug.startswith("-")
                assert not slug.endswith("-")
                assert "--" not in slug
