"""Index builder for dacli.

Builds the in-memory StructureIndex from documents in a docs root directory.
This module has no heavy external dependencies (no fastmcp, pydantic, etc.),
enabling the CLI to be packaged as a lightweight cross-platform zipapp.
"""

import logging
from pathlib import Path

from dacli.asciidoc_parser import AsciidocStructureParser, CircularIncludeError
from dacli.file_utils import find_doc_files
from dacli.markdown_parser import MarkdownStructureParser
from dacli.models import Document
from dacli.structure_index import StructureIndex

logger = logging.getLogger(__name__)


def build_index(
    docs_root: Path,
    index: StructureIndex,
    asciidoc_parser: AsciidocStructureParser,
    markdown_parser: MarkdownStructureParser,
    *,
    respect_gitignore: bool = True,
    include_hidden: bool = False,
) -> None:
    """Build the structure index from documents in docs_root.

    Args:
        docs_root: Root directory containing documentation
        index: StructureIndex to populate
        asciidoc_parser: Parser for AsciiDoc files
        markdown_parser: Parser for Markdown files
        respect_gitignore: If True, exclude files matching .gitignore patterns
        include_hidden: If True, include files in hidden directories
    """
    documents: list[Document] = []

    # Find all AsciiDoc files first (Issue #184)
    all_adoc_files = list(
        find_doc_files(
            docs_root, "*.adoc", respect_gitignore=respect_gitignore, include_hidden=include_hidden
        )
    )

    # Scan for include directives to identify included files (Issue #184)
    # Included files should not be parsed as separate root documents
    included_files: set[Path] = set()
    for adoc_file in all_adoc_files:
        included_files.update(AsciidocStructureParser.scan_includes(adoc_file))

    # Filter: only parse files that are NOT included by others (Issue #184)
    root_adoc_files = [f for f in all_adoc_files if f not in included_files]

    # Issue #251: Detect circular includes in the include graph
    # Files that include each other circularly all end up in included_files
    # with none of them becoming root documents. Detect these cycles.
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
            message = f"Circular include detected: {circ_file.name} " f"is part of an include cycle"
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
            # Issue #251: Catch circular includes during parsing too
            logger.warning("Circular include in %s: %s", adoc_file, e)
            circular_include_errors.append(
                {
                    "file": adoc_file,
                    "include_chain": e.include_chain,
                    "message": str(e),
                }
            )
        except Exception as e:
            # Log but continue with other files
            logger.warning("Failed to parse %s: %s", adoc_file, e)

    # Find and parse Markdown files
    for md_file in find_doc_files(
        docs_root, "*.md", respect_gitignore=respect_gitignore, include_hidden=include_hidden
    ):
        try:
            md_doc = markdown_parser.parse_file(md_file)
            # Convert MarkdownDocument to Document
            doc = Document(
                file_path=md_doc.file_path,
                title=md_doc.title,
                sections=md_doc.sections,
                elements=md_doc.elements,
            )
            documents.append(doc)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", md_file, e)

    # Build index
    warnings = index.build_from_documents(documents)
    for warning in warnings:
        logger.warning("Index: %s", warning)

    # Issue #251: Store circular include errors on the index for validation
    index._circular_include_errors = circular_include_errors
