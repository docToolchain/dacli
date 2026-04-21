"""Validation service for document structure validation.

Provides shared logic for CLI and MCP validation operations.
"""

import time
from pathlib import Path

from dacli.file_utils import find_doc_files
from dacli.structure_index import StructureIndex


def _relativize(file_path: Path, docs_roots: list[Path]) -> Path:
    """Make a path relative to the first matching root.

    Args:
        file_path: Absolute file path
        docs_roots: List of resolved root paths

    Returns:
        Relative path, or the original path if no root matches
    """
    for root in docs_roots:
        try:
            return file_path.relative_to(root)
        except ValueError:
            continue
    return file_path


def validate_structure(index: StructureIndex, docs_roots: Path | list[Path]) -> dict:
    """Validate the document structure.

    Checks for:
    - Orphaned files (not included in any document)
    - Parse warnings (unclosed blocks, tables)

    Args:
        index: The structure index to validate.
        docs_roots: Root directory or list of root directories (ADR-014).

    Returns:
        Dictionary with:
        - valid: True if no errors, False otherwise
        - errors: List of error objects
        - warnings: List of warning objects
        - validation_time_ms: Time taken for validation
    """
    # Normalize to list for uniform handling
    if isinstance(docs_roots, Path):
        docs_roots = [docs_roots]
    resolved_roots = [r.resolve() for r in docs_roots]

    start_time = time.time()

    errors: list[dict] = []
    warnings: list[dict] = []

    # Issue #251: Report circular include errors explicitly
    circular_files: set[Path] = set()
    for circ_error in index._circular_include_errors:
        file_path = circ_error["file"]
        rel_path = _relativize(file_path, resolved_roots)
        errors.append(
            {
                "type": "circular_include",
                "path": str(rel_path),
                "message": circ_error["message"],
            }
        )
        circular_files.add(file_path.resolve())
        for chain_path in circ_error["include_chain"]:
            circular_files.add(chain_path.resolve())

    # Get all indexed files
    indexed_files = set(index._file_to_sections.keys())

    # Get all doc files across all roots (respecting gitignore)
    all_doc_files: set[Path] = set()
    for docs_root in resolved_roots:
        for adoc_file in find_doc_files(docs_root, "*.adoc"):
            all_doc_files.add(adoc_file.resolve())
        for md_file in find_doc_files(docs_root, "*.md"):
            all_doc_files.add(md_file.resolve())

    # Check for orphaned files (files not indexed)
    # Issue #251: Exclude files involved in circular includes from orphaned detection
    indexed_resolved = {f.resolve() for f in indexed_files}
    for doc_file in all_doc_files:
        if doc_file not in indexed_resolved and doc_file not in circular_files:
            rel_path = _relativize(doc_file, resolved_roots)
            warnings.append(
                {
                    "type": "orphaned_file",
                    "path": str(rel_path),
                    "message": "File is not included in any document",
                }
            )

    # Collect parse warnings from all documents (Issue #148)
    for doc in index._documents:
        for pw in doc.parse_warnings:
            rel_path = _relativize(pw.file, resolved_roots)
            warnings.append(
                {
                    "type": pw.type.value,
                    "path": f"{rel_path}:{pw.line}",
                    "message": pw.message,
                }
            )

    # Issue #268: Include duplicate-path warnings from index build
    for build_warning in index._build_warnings:
        if "Duplicate section path" in build_warning:
            import re

            match = re.search(r"Duplicate section path: '([^']+)'", build_warning)
            dup_path = match.group(1) if match else "unknown"
            warnings.append(
                {
                    "type": "duplicate_path",
                    "path": dup_path,
                    "message": build_warning,
                }
            )

    # Issue #219: Check for unresolved includes
    for doc in index._documents:
        if hasattr(doc, "includes"):
            for include in doc.includes:
                if not include.target_path.exists():
                    source_loc = include.source_location
                    rel_source = _relativize(source_loc.file, resolved_roots)
                    rel_target = _relativize(include.target_path, resolved_roots)
                    errors.append(
                        {
                            "type": "unresolved_include",
                            "path": f"{rel_source}:{source_loc.line}",
                            "include_path": str(rel_target),
                            "message": f"Include file '{rel_target}' not found",
                        }
                    )

    # Calculate validation time
    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "validation_time_ms": elapsed_ms,
    }
