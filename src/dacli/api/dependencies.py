"""Shared dependencies for API routers.

This module provides the shared StructureIndex instance used by all API routers.
The index is set once during app initialization and accessed by routers.
"""

from fastapi import HTTPException

from dacli.api.models import ErrorDetail, ErrorResponse
from dacli.structure_index import StructureIndex

# Global index reference - set by create_app, used by all routers
_index: StructureIndex | None = None


def set_index(index: StructureIndex) -> None:
    """Set the global structure index.

    Args:
        index: The StructureIndex to use for all API operations.
    """
    global _index
    _index = index


def get_index() -> StructureIndex:
    """Get the global structure index.

    Returns:
        The configured StructureIndex.

    Raises:
        HTTPException: If the index has not been initialized (503 status).
    """
    if _index is None:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INDEX_NOT_READY",
                    message="Server index is not initialized",
                )
            ).model_dump(),
        )
    return _index
