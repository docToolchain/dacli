"""Index builder for dacli.

Builds the in-memory StructureIndex from documents in documentation roots.
This module has no heavy external dependencies (no fastmcp, pydantic, etc.),
enabling the CLI to be packaged as a lightweight cross-platform zipapp.

Supports both single-root mode (backward compat) and multi-root mode (ADR-014).
"""

import logging
from pathlib import Path

from dacli.asciidoc_parser import AsciidocStructureParser, CircularIncludeError
from dacli.file_utils import find_doc_files
from dacli.markdown_parser import MarkdownStructureParser
from dacli.models import Document, DocumentRoot
from dacli.structure_index import Section, StructureIndex

logger = logging.getLogger(__name__)


def count_descendants(section: Section) -> int:
    """Count total descendants of a section recursively."""
    count = len(section.children)
    for child in section.children:
        count += count_descendants(child)
    return count


def build_index(
    roots_or_path: list[DocumentRoot] | Path,
    index: StructureIndex,
    asciidoc_parser: AsciidocStructureParser | None = None,
    markdown_parser: MarkdownStructureParser | None = None,
    *,
    respect_gitignore: bool = True,
    include_hidden: bool = False,
) -> None:
    """Build the structure index from documents across all roots.

    Supports two calling conventions:
    1. Multi-root mode (ADR-014): build_index(roots, index, ...)
       - roots: List of DocumentRoot objects
       - Parsers are created internally with namespace prefixes

    2. Single-root mode (backward compat): build_index(path, index, parser, parser, ...)
       - path: Single Path to docs root
       - Parsers provided by caller

    Args:
        roots_or_path: List of DocumentRoot objects, or a single Path
        index: StructureIndex to populate
        asciidoc_parser: Parser for AsciiDoc (only used in single-root mode)
        markdown_parser: Parser for Markdown (only used in single-root mode)
        respect_gitignore: If True, exclude files matching .gitignore patterns
        include_hidden: If True, include files in hidden directories
    """
    # Handle both calling conventions
    if isinstance(roots_or_path, Path):
        # Single-root backward compat mode
        roots = [DocumentRoot(
            name=roots_or_path.name,
            path=roots_or_path.resolve(),
            mode="workspace",
        )]
        # Use provided parsers or create defaults
        if asciidoc_parser is None:
            asciidoc_parser = AsciidocStructureParser(base_path=roots_or_path)
        if markdown_parser is None:
            markdown_parser = MarkdownStructureParser(base_path=roots_or_path)
        parsers_provided = True
    else:
        roots = roots_or_path
        parsers_provided = False

    multi_root = len(roots) > 1
    documents: list[Document] = []
    all_circular_include_errors: list[dict] = []

    for root in roots:
        # In multi-root mode, create namespaced parsers for each root
        if not parsers_provided:
            namespace = root.name if multi_root else None
            asciidoc_parser = AsciidocStructureParser(
                base_path=root.path, namespace=namespace,
            )
            markdown_parser = MarkdownStructureParser(
                base_path=root.path, namespace=namespace,
            )

        root_documents, circular_errors = _build_index_for_root(
            root.path,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=respect_gitignore,
            include_hidden=include_hidden,
        )
        documents.extend(root_documents)
        all_circular_include_errors.extend(circular_errors)

    # Build unified index
    warnings = index.build_from_documents(documents)
    for warning in warnings:
        logger.warning("Index: %s", warning)

    # Issue #251: Store circular include errors on the index for validation
    index._circular_include_errors = all_circular_include_errors


def _build_index_for_root(
    docs_root: Path,
    asciidoc_parser: AsciidocStructureParser,
    markdown_parser: MarkdownStructureParser,
    *,
    respect_gitignore: bool = True,
    include_hidden: bool = False,
) -> tuple[list[Document], list[dict]]:
    """Build documents for a single documentation root.

    Args:
        docs_root: Root directory containing documentation
        asciidoc_parser: Parser for AsciiDoc files (may have namespace set)
        markdown_parser: Parser for Markdown files (may have namespace set)
        respect_gitignore: If True, exclude files matching .gitignore patterns
        include_hidden: If True, include files in hidden directories

    Returns:
        Tuple of (documents, circular_include_errors)
    """
    documents: list[Document] = []

    # Find all AsciiDoc files first (Issue #184)
    all_adoc_files = list(
        find_doc_files(
            docs_root, "*.adoc", respect_gitignore=respect_gitignore, include_hidden=include_hidden
        )
    )

    # Scan for include directives to identify included files (Issue #184)
    included_files: set[Path] = set()
    for adoc_file in all_adoc_files:
        included_files.update(AsciidocStructureParser.scan_includes(adoc_file))

    # Filter: only parse files that are NOT included by others (Issue #184)
    root_adoc_files = [f for f in all_adoc_files if f not in included_files]

    # Issue #251: Detect circular includes in the include graph
    circular_include_errors: list[dict] = []
    if all_adoc_files:
        include_graph: dict[Path, set[Path]] = {}
        for adoc_file in all_adoc_files:
            resolved = adoc_file.resolve()
            includes = AsciidocStructureParser.scan_includes(adoc_file)
            include_graph[resolved] = includes

        circular_files: set[Path] = set()
        visited: set[Path] = set()
        in_stack: set[Path] = set()

        def _find_cycles(node: Path, path_list: list[Path]) -> None:
            if node in in_stack:
                cycle_start = path_list.index(node)
                for f in path_list[cycle_start:]:
                    circular_files.add(f)
                return
            if node in visited:
                return
            visited.add(node)
            in_stack.add(node)
            path_list.append(node)
            for neighbor in include_graph.get(node, set()):
                _find_cycles(neighbor, path_list)
            path_list.pop()
            in_stack.remove(node)

        for adoc_file in all_adoc_files:
            _find_cycles(adoc_file.resolve(), [])

        for circ_file in circular_files:
            message = f"Circular include detected: {circ_file.name} is part of an include cycle"
            circular_include_errors.append(
                {
                    "file": circ_file,
                    "include_chain": list(circular_files),
                    "message": message,
                }
            )

    logger.info(
        f"Found {len(all_adoc_files)} AsciiDoc files, "
        f"{len(included_files)} included, "
        f"{len(root_adoc_files)} root documents"
    )

    # Parse root AsciiDoc files only
    for adoc_file in root_adoc_files:
        try:
            doc = asciidoc_parser.parse_file(adoc_file)
            documents.append(doc)
        except CircularIncludeError as e:
            logger.warning("Circular include in %s: %s", adoc_file, e)
            circular_include_errors.append(
                {
                    "file": adoc_file,
                    "include_chain": e.include_chain,
                    "message": str(e),
                }
            )
        except Exception as e:
            logger.warning("Failed to parse %s: %s", adoc_file, e)

    # Find and parse Markdown files
    for md_file in find_doc_files(
        docs_root, "*.md", respect_gitignore=respect_gitignore, include_hidden=include_hidden
    ):
        try:
            md_doc = markdown_parser.parse_file(md_file)
            doc = Document(
                file_path=md_doc.file_path,
                title=md_doc.title,
                sections=md_doc.sections,
                elements=md_doc.elements,
            )
            documents.append(doc)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", md_file, e)

    return documents, circular_include_errors


def find_root_for_file(roots: list[DocumentRoot], file_path: Path) -> DocumentRoot | None:
    """Find which DocumentRoot a file belongs to.

    Args:
        roots: List of documentation roots
        file_path: Absolute path to a file

    Returns:
        The DocumentRoot containing the file, or None
    """
    resolved = file_path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.path)
            return root
        except ValueError:
            continue
    return None
