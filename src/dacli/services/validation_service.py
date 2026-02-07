"""Validation service for document structure validation.

Provides shared logic for CLI and MCP validation operations.
"""

import time
from pathlib import Path

from dacli.file_utils import find_doc_files
from dacli.structure_index import StructureIndex


def validate_structure(index: StructureIndex, docs_root: Path) -> dict:
    """Validate the document structure.

    Checks for:
    - Orphaned files (not included in any document)
    - Parse warnings (unclosed blocks, tables)

    Args:
        index: The structure index to validate.
        docs_root: Root directory of documentation.

    Returns:
        Dictionary with:
        - valid: True if no errors, False otherwise
        - errors: List of error objects
        - warnings: List of warning objects
        - validation_time_ms: Time taken for validation
    """
    start_time = time.time()

    errors: list[dict] = []
    warnings: list[dict] = []

    # Issue #251: Report circular include errors explicitly
    docs_root_resolved = docs_root.resolve()
    circular_files: set[Path] = set()
    for circ_error in index._circular_include_errors:
        file_path = circ_error["file"]
        try:
            rel_path = file_path.relative_to(docs_root_resolved)
        except ValueError:
            rel_path = file_path
        errors.append({
            "type": "circular_include",
            "path": str(rel_path),
            "message": circ_error["message"],
        })
        # Track all files involved in circular includes
        circular_files.add(file_path.resolve())
        for chain_path in circ_error["include_chain"]:
            circular_files.add(chain_path.resolve())

    # Get all indexed files
    indexed_files = set(index._file_to_sections.keys())

    # Get all doc files in docs_root (respecting gitignore)
    all_doc_files: set[Path] = set()
    for adoc_file in find_doc_files(docs_root, "*.adoc"):
        all_doc_files.add(adoc_file.resolve())
    for md_file in find_doc_files(docs_root, "*.md"):
        all_doc_files.add(md_file.resolve())

    # Check for orphaned files (files not indexed)
    # Issue #251: Exclude files involved in circular includes from orphaned detection
    indexed_resolved = {f.resolve() for f in indexed_files}
    for doc_file in all_doc_files:
        if doc_file not in indexed_resolved and doc_file not in circular_files:
            try:
                rel_path = doc_file.relative_to(docs_root_resolved)
            except ValueError:
                rel_path = doc_file
            warnings.append({
                "type": "orphaned_file",
                "path": str(rel_path),
                "message": "File is not included in any document",
            })

    # Collect parse warnings from all documents (Issue #148)
    for doc in index._documents:
        for pw in doc.parse_warnings:
            try:
                rel_path = pw.file.relative_to(docs_root_resolved)
            except ValueError:
                rel_path = pw.file
            warnings.append({
                "type": pw.type.value,
                "path": f"{rel_path}:{pw.line}",
                "message": pw.message,
            })

    # Issue #268: Include duplicate-path warnings from index build
    for build_warning in index._build_warnings:
        if "Duplicate section path" in build_warning:
            # Parse the warning string to extract the path
            # Format: "Duplicate section path: 'path' (first at file:line, duplicate at file:line)"
            import re
            match = re.search(r"Duplicate section path: '([^']+)'", build_warning)
            dup_path = match.group(1) if match else "unknown"
            warnings.append({
                "type": "duplicate_path",
                "path": dup_path,
                "message": build_warning,
            })

    # Issue #219: Check for unresolved includes
    for doc in index._documents:
        # Only AsciiDoc documents have includes (check for attribute)
        if hasattr(doc, "includes"):
            for include in doc.includes:
                if not include.target_path.exists():
                    source_loc = include.source_location
                    try:
                        rel_source = source_loc.file.relative_to(docs_root_resolved)
                    except ValueError:
                        rel_source = source_loc.file
                    try:
                        rel_target = include.target_path.relative_to(docs_root_resolved)
                    except ValueError:
                        rel_target = include.target_path
                    errors.append({
                        "type": "unresolved_include",
                        "path": f"{rel_source}:{source_loc.line}",
                        "include_path": str(rel_target),
                        "message": f"Include file '{rel_target}' not found",
                    })

    # Calculate validation time
    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "validation_time_ms": elapsed_ms,
    }
