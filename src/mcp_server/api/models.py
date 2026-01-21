"""Pydantic models for API responses.

These models define the JSON response structure for the Navigation API
as specified in 02_api_specification.adoc.
"""

from pydantic import BaseModel, Field


class LocationResponse(BaseModel):
    """Location of a section in a source file."""

    file: str = Field(description="Relative path to the file")
    line: int = Field(description="1-based line number")


class SectionResponse(BaseModel):
    """Section response for structure endpoint."""

    path: str = Field(description="Hierarchical path (e.g., '/chapter-1/section-2')")
    title: str = Field(description="Section title")
    level: int = Field(description="Nesting depth (1 = chapter)")
    location: LocationResponse
    children: list["SectionResponse"] = Field(default_factory=list)


class StructureResponse(BaseModel):
    """Response for GET /structure endpoint."""

    sections: list[SectionResponse]
    total_sections: int = Field(description="Total number of sections in index")


class SectionDetailResponse(BaseModel):
    """Detailed section response for GET /section/{path}."""

    path: str
    title: str
    level: int
    location: LocationResponse
    format: str = Field(description="Document format: 'asciidoc' or 'markdown'")


class SectionSummary(BaseModel):
    """Summary of a section (without children)."""

    path: str
    title: str


class SectionsAtLevelResponse(BaseModel):
    """Response for GET /sections endpoint."""

    level: int
    sections: list[SectionSummary]
    count: int


class ErrorDetail(BaseModel):
    """Error detail in error response."""

    code: str = Field(description="Error code (e.g., 'PATH_NOT_FOUND')")
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(default=None, description="Additional details")


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: ErrorDetail


# Allow forward references
SectionResponse.model_rebuild()
