"""AsciiDoc Parser for MCP Documentation Server.

This module provides the AsciidocParser class for parsing AsciiDoc documents.
It extracts sections, elements, cross-references, and handles includes.

Current implementation focuses on section extraction (AC-ADOC-01).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from mcp_server.models import (
    CrossReference,
    Document,
    Section,
    SourceLocation,
)

# Regex patterns from specification
SECTION_PATTERN = re.compile(r"^(={1,6})\s+(.+?)(?:\s+=*)?$")
ATTRIBUTE_PATTERN = re.compile(r"^:([a-zA-Z0-9_-]+):\s*(.*)$")
INCLUDE_PATTERN = re.compile(r"^include::(.+?)\[(.*)\]$")


def _title_to_slug(title: str) -> str:
    """Convert a section title to a URL-friendly slug.

    Args:
        title: The section title

    Returns:
        A lowercase slug with spaces replaced by dashes
    """
    # Remove special characters, convert to lowercase, replace spaces with dashes
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


@dataclass
class IncludeInfo:
    """Information about a resolved include directive.

    Attributes:
        source_location: Where the include directive was found
        target_path: The resolved path to the included file
        options: Include options (leveloffset, lines, etc.)
    """

    source_location: SourceLocation
    target_path: Path
    options: dict[str, str] = field(default_factory=dict)


@dataclass
class AsciidocDocument(Document):
    """A parsed AsciiDoc document.

    Extends Document with AsciiDoc-specific fields.

    Attributes:
        attributes: Document attributes (:attr: value)
        cross_references: List of cross-references found
        includes: List of resolved includes
    """

    attributes: dict[str, str] = field(default_factory=dict)
    cross_references: list[CrossReference] = field(default_factory=list)
    includes: list[IncludeInfo] = field(default_factory=list)


class AsciidocParser:
    """Parser for AsciiDoc documents.

    Parses AsciiDoc files and extracts structure, elements, and references.
    Currently implements section extraction (AC-ADOC-01).

    Attributes:
        base_path: Base path for resolving relative file paths
        max_include_depth: Maximum depth for nested includes (default: 20)
    """

    def __init__(self, base_path: Path, max_include_depth: int = 20):
        """Initialize the parser.

        Args:
            base_path: Base path for resolving relative file paths
            max_include_depth: Maximum depth for nested includes
        """
        self.base_path = base_path
        self.max_include_depth = max_include_depth

    def parse_file(
        self, file_path: Path, _depth: int = 0
    ) -> AsciidocDocument:
        """Parse an AsciiDoc file.

        Args:
            file_path: Path to the AsciiDoc file
            _depth: Internal parameter for tracking include depth

        Returns:
            Parsed AsciidocDocument

        Raises:
            FileNotFoundError: If the file does not exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Parse attributes first (they can be used in sections)
        attributes = self._parse_attributes(lines)

        # Expand includes and collect include info
        expanded_lines, includes = self._expand_includes(
            lines, file_path, _depth
        )

        # Parse sections with attribute substitution
        sections, title = self._parse_sections(
            expanded_lines, file_path, attributes
        )

        return AsciidocDocument(
            file_path=file_path,
            title=title,
            sections=sections,
            elements=[],
            attributes=attributes,
            cross_references=[],
            includes=includes,
        )

    def _expand_includes(
        self,
        lines: list[str],
        file_path: Path,
        depth: int,
    ) -> tuple[list[tuple[str, Path, int, SourceLocation | None]], list[IncludeInfo]]:
        """Expand include directives in lines.

        Args:
            lines: Document lines
            file_path: Path to the source file
            depth: Current include depth

        Returns:
            Tuple of (expanded lines with source info, list of IncludeInfo)
        """
        expanded: list[tuple[str, Path, int, SourceLocation | None]] = []
        includes: list[IncludeInfo] = []

        for line_num, line in enumerate(lines, start=1):
            match = INCLUDE_PATTERN.match(line)
            if match and depth < self.max_include_depth:
                include_path = match.group(1)
                options_str = match.group(2)

                # Parse options
                options: dict[str, str] = {}
                if options_str:
                    for opt in options_str.split(","):
                        if "=" in opt:
                            key, value = opt.split("=", 1)
                            options[key.strip()] = value.strip()

                # Resolve include path relative to current file
                target_path = (file_path.parent / include_path).resolve()

                # Record include info
                include_info = IncludeInfo(
                    source_location=SourceLocation(file=file_path, line=line_num),
                    target_path=target_path,
                    options=options,
                )
                includes.append(include_info)

                # Expand the included file
                if target_path.exists():
                    included_content = target_path.read_text(encoding="utf-8")
                    included_lines = included_content.splitlines()

                    # Create resolved_from reference
                    resolved_from = SourceLocation(file=file_path, line=line_num)

                    for inc_line_num, inc_line in enumerate(included_lines, start=1):
                        expanded.append(
                            (inc_line, target_path, inc_line_num, resolved_from)
                        )
            else:
                expanded.append((line, file_path, line_num, None))

        return expanded, includes

    def _parse_attributes(self, lines: list[str]) -> dict[str, str]:
        """Parse document attributes from lines.

        Attributes are defined as :name: value at the start of the document.

        Args:
            lines: Document lines

        Returns:
            Dictionary of attribute name to value
        """
        attributes: dict[str, str] = {}

        for line in lines:
            match = ATTRIBUTE_PATTERN.match(line)
            if match:
                name = match.group(1)
                value = match.group(2).strip()
                attributes[name] = value
            elif line.strip() and not line.startswith(":"):
                # Stop parsing attributes when we hit non-attribute content
                # (but continue through empty lines)
                if SECTION_PATTERN.match(line):
                    break

        return attributes

    def _substitute_attributes(self, text: str, attributes: dict[str, str]) -> str:
        """Substitute attribute references in text.

        Replaces {attribute} with the attribute value.

        Args:
            text: Text with potential attribute references
            attributes: Dictionary of attribute name to value

        Returns:
            Text with attribute references substituted
        """
        result = text
        for name, value in attributes.items():
            result = result.replace(f"{{{name}}}", value)
        return result

    def _parse_sections(
        self,
        lines: list[tuple[str, Path, int, SourceLocation | None]],
        file_path: Path,
        attributes: dict[str, str] | None = None,
    ) -> tuple[list[Section], str]:
        """Parse sections from document lines.

        Args:
            lines: Expanded lines with source info (line, file, line_num, resolved_from)
            file_path: Path to the main source file
            attributes: Document attributes for substitution

        Returns:
            Tuple of (list of top-level sections, document title)
        """
        if not lines:
            return [], ""

        if attributes is None:
            attributes = {}

        sections: list[Section] = []
        section_stack: list[Section] = []
        document_title = ""

        for line_text, source_file, line_num, resolved_from in lines:
            match = SECTION_PATTERN.match(line_text)
            if match:
                equals = match.group(1)
                raw_title = match.group(2).strip()
                # Substitute attribute references in title
                title = self._substitute_attributes(raw_title, attributes)
                level = len(equals) - 1  # = is level 0, == is level 1, etc.

                # Create section with proper source location
                source_location = SourceLocation(
                    file=source_file,
                    line=line_num,
                    resolved_from=resolved_from,
                )

                section = Section(
                    title=title,
                    level=level,
                    path="",  # Will be set below
                    source_location=source_location,
                    children=[],
                    anchor=None,
                )

                # Document title (level 0)
                if level == 0:
                    document_title = title
                    section.path = _title_to_slug(title)
                    sections.append(section)
                    section_stack = [section]
                else:
                    # Find parent section
                    while section_stack and section_stack[-1].level >= level:
                        section_stack.pop()

                    if section_stack:
                        parent = section_stack[-1]
                        section.path = f"{parent.path}.{_title_to_slug(title)}"
                        parent.children.append(section)
                    else:
                        # No parent found, add as top-level
                        section.path = _title_to_slug(title)
                        sections.append(section)

                    section_stack.append(section)

        return sections, document_title
