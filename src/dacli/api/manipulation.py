"""Manipulation API router.

Provides endpoints for modifying document content:
- PUT /section/{path} - Update a section's content
- POST /section/{path}/insert - Insert content relative to a section
"""

from pathlib import Path as FilePath

from fastapi import APIRouter, HTTPException, Path

from dacli.api.dependencies import get_index
from dacli.api.models import (
    ErrorResponse,
    InsertContentRequest,
    InsertContentResponse,
    LocationResponse,
    UpdateSectionRequest,
    UpdateSectionResponse,
)
from dacli.file_handler import FileReadError, FileSystemHandler, FileWriteError
from dacli.models import Section

router = APIRouter(prefix="/api/v1", tags=["Manipulation"])

# File handler for atomic operations
_file_handler: FileSystemHandler = FileSystemHandler()


def _get_section_end_line(section: Section, file_path: FilePath) -> int:
    """Get the end line of a section.

    Uses the end_line from SourceLocation (populated by parsers).
    Falls back to reading file length if end_line is not set.

    Args:
        section: The section to get end line for
        file_path: Path to the file containing the section

    Returns:
        The end line number (1-based)
    """
    if section.source_location.end_line is not None:
        return section.source_location.end_line

    # Fallback: read file to get total lines
    try:
        content = _file_handler.read_file(file_path)
        return len(content.splitlines())
    except FileReadError:
        return section.source_location.line + 10  # Last resort fallback


def _get_section_end_with_children(section: Section, file_path: FilePath) -> int:
    """Get the end line of a section including ALL child sections recursively.

    Issue #208: When inserting "after" a section, we need to insert after all
    descendants, not just after the direct content of the section.

    Args:
        section: The section to get end line for (including children)
        file_path: Path to the file containing the section

    Returns:
        The end line number (1-based) of the last descendant, or the section
        itself if it has no children
    """
    if not section.children:
        # No children, use direct end_line
        return _get_section_end_line(section, file_path)

    # Find the last child recursively
    last_child = section.children[-1]
    return _get_section_end_with_children(last_child, file_path)


@router.put(
    "/section/{path:path}",
    response_model=UpdateSectionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Section not found"},
        500: {"model": ErrorResponse, "description": "Write operation failed"},
    },
    summary="Update section content",
    description="Updates the content of a specific section.",
)
def update_section(
    path: str = Path(description="Hierarchical path to the section"),
    request: UpdateSectionRequest = ...,
) -> UpdateSectionResponse:
    """Update a section's content."""
    index = get_index()

    # Normalize path
    normalized_path = f"/{path}" if not path.startswith("/") else path

    # Find the section
    section = index.get_section(normalized_path)
    if section is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "PATH_NOT_FOUND",
                    "message": f"Section '{normalized_path}' not found",
                }
            },
        )

    file_path = section.source_location.file
    start_line = section.source_location.line
    end_line = _get_section_end_line(section, file_path)

    # Prepare content
    new_content = request.content
    if request.preserve_title:
        stripped_content = new_content.lstrip()
        has_explicit_title = stripped_content.startswith("=") or stripped_content.startswith("#")
        if not has_explicit_title:
            # Prepend the original title line
            level_markers = "=" * (section.level + 1)
            new_content = f"{level_markers} {section.title}\n\n{new_content}"

    # Ensure content ends with newline
    if not new_content.endswith("\n"):
        new_content += "\n"

    # Perform atomic update
    try:
        _file_handler.update_section(
            path=file_path,
            start_line=start_line,
            end_line=end_line,
            new_content=new_content,
        )
    except FileWriteError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "WRITE_FAILED",
                    "message": "Failed to write changes to file",
                    "details": {
                        "file": str(file_path),
                        "reason": str(e),
                    },
                }
            },
        )

    return UpdateSectionResponse(
        success=True,
        path=normalized_path,
        location=LocationResponse(
            file=str(file_path),
            line=start_line,
        ),
    )


@router.post(
    "/section/{path:path}/insert",
    response_model=InsertContentResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Section not found"},
        500: {"model": ErrorResponse, "description": "Write operation failed"},
    },
    summary="Insert content relative to section",
    description="Inserts content before, after, or appended to a section.",
)
def insert_content(
    path: str = Path(description="Hierarchical path to the reference section"),
    request: InsertContentRequest = ...,
) -> InsertContentResponse:
    """Insert content relative to a section."""
    index = get_index()

    # Normalize path
    normalized_path = f"/{path}" if not path.startswith("/") else path

    # Find the section
    section = index.get_section(normalized_path)
    if section is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "PATH_NOT_FOUND",
                    "message": f"Section '{normalized_path}' not found",
                }
            },
        )

    file_path = section.source_location.file
    start_line = section.source_location.line
    end_line = _get_section_end_line(section, file_path)

    # Determine insert position
    content = request.content
    if not content.endswith("\n"):
        content += "\n"

    try:
        file_content = _file_handler.read_file(file_path)
        lines = file_content.splitlines(keepends=True)

        if request.position == "before":
            # Insert before the section starts
            insert_line = start_line
            new_lines = (
                lines[: start_line - 1]
                + [content]
                + lines[start_line - 1 :]
            )
        elif request.position == "after":
            # Issue #208: Insert after the section AND all its children
            # Use _get_section_end_with_children to include all descendants
            end_with_children = _get_section_end_with_children(section, file_path)
            insert_line = end_with_children + 1
            new_lines = (
                lines[:end_with_children]
                + [content]
                + lines[end_with_children:]
            )
        else:  # append
            # Append content at end of section (before the last line/children)
            insert_line = end_line
            new_lines = (
                lines[: end_line - 1]
                + [content]
                + lines[end_line - 1 :]
            )

        new_file_content = "".join(new_lines)
        _file_handler.write_file(file_path, new_file_content)

    except FileReadError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "READ_FAILED",
                    "message": f"Failed to read file: {e}",
                }
            },
        )
    except FileWriteError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "WRITE_FAILED",
                    "message": "Failed to write changes to file",
                    "details": {
                        "file": str(file_path),
                        "reason": str(e),
                    },
                }
            },
        )

    return InsertContentResponse(
        success=True,
        inserted_at=LocationResponse(
            file=str(file_path),
            line=insert_line,
        ),
    )
