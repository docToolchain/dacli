"""Shared utility functions for document parsers.

This module contains common functionality used by both the AsciiDoc
and Markdown parsers, following the DRY principle.
"""

import re
from pathlib import Path

from dacli.models import Section

# Known document extensions to strip from file paths (Issue #266)
KNOWN_DOC_EXTENSIONS = {".md", ".adoc", ".asciidoc"}


def strip_doc_extension(file_path: Path) -> str:
    """Remove only known document extensions from a file path.

    Unlike Path.with_suffix(""), this only removes known extensions (.md, .adoc,
    .asciidoc) and preserves dots that are part of the filename (e.g. version
    numbers like "report_v1.2.3.md" → "report_v1.2.3").

    Args:
        file_path: Path to strip extension from

    Returns:
        String path with known extension removed, using forward slashes.
    """
    path_str = str(file_path).replace("\\", "/")
    suffix = file_path.suffix.lower()
    if suffix in KNOWN_DOC_EXTENSIONS:
        # Remove only the last suffix if it's a known doc extension
        return path_str[: -len(file_path.suffix)]
    return path_str


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to convert

    Returns:
        Lowercase slug with spaces/underscores replaced by dashes,
        multiple dashes collapsed, and leading/trailing dashes trimmed.
        Unicode characters are preserved.

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Übersicht")
        'übersicht'
        >>> slugify("hello_world")
        'hello-world'
    """
    # Remove special characters but preserve Unicode word characters
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    # Convert spaces and underscores to dashes
    slug = re.sub(r"[\s_]+", "-", slug)
    # Collapse multiple dashes
    slug = re.sub(r"-+", "-", slug)
    # Trim leading/trailing dashes
    return slug.strip("-")


def collect_all_sections(sections: list[Section], result: list[Section]) -> None:
    """Recursively collect all sections into a flat list.

    Args:
        sections: List of sections to process
        result: List to append sections to (modified in place)

    Example:
        >>> all_sections = []
        >>> collect_all_sections(doc.sections, all_sections)
    """
    for section in sections:
        result.append(section)
        collect_all_sections(section.children, result)


def find_section_by_path(sections: list[Section], path: str) -> Section | None:
    """Recursively find a section by path.

    Args:
        sections: List of sections to search
        path: Section path to find (e.g., "introduction.goals")

    Returns:
        The section if found, None otherwise
    """
    for section in sections:
        if section.path == path:
            return section
        # Search in children
        found = find_section_by_path(section.children, path)
        if found:
            return found
    return None
