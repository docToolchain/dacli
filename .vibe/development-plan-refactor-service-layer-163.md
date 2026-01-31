# Development Plan: Service Layer Refactoring (Issue #163)

*Generated on 2026-01-24 by Vibe Feature MCP*
*Workflow: [epcc](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/epcc)*

## Goal
Extract duplicated business logic from `cli.py` and `mcp_app.py` into a shared Service Layer (`src/dacli/services/`). This improves maintainability and ensures CLI and MCP stay in sync.

## Key Decisions
- Services accept dependencies (index, file_handler, docs_root) instead of using globals
- Services return dict results, CLI/MCP handle I/O
- Start with MetadataService (simplest), then ValidationService, then ContentService
- Use functions instead of classes for simplicity (stateless services)

## Notes
- CLI uses `ctx.index`, MCP uses global `index`
- CLI has exit codes, MCP just returns dicts
- Hash computation differs (helper vs inline) - consolidate in service

## Service Interface Designs

### MetadataService (metadata_service.py)
```python
def get_project_metadata(index: StructureIndex) -> dict:
    """Returns: path, total_files, total_sections, total_words, last_modified, formats"""

def get_section_metadata(index: StructureIndex, path: str) -> dict:
    """Returns: path, title, file, word_count, last_modified, subsection_count
    Or: error dict if section not found"""
```

### ValidationService (validation_service.py)
```python
def validate_structure(
    index: StructureIndex,
    docs_root: Path
) -> dict:
    """Returns: valid, errors, warnings, validation_time_ms"""
```

### ContentService (content_service.py)
```python
def update_section(
    index: StructureIndex,
    file_handler: FileSystemHandler,
    path: str,
    content: str,
    preserve_title: bool = True,
    expected_hash: str | None = None,
) -> dict:
    """Returns: success, path, location, previous_hash, new_hash
    Or: error dict with success=False"""

def compute_hash(content: str) -> str:
    """Compute MD5 hash (first 8 chars) for optimistic locking."""
```

## Explore

### Phase Entrance Criteria:
- [x] Issue requirements understood
- [x] Feature branch created

### Tasks

### Completed
- [x] Created development plan file
- [x] Analyzed metadata logic duplication (~95% similar)
- [x] Analyzed validation logic duplication (~95% similar)
- [x] Analyzed update_section logic duplication (~85% similar)
- [x] Identified key differences (index access, output handling, exit codes)

## Plan

### Phase Entrance Criteria:
- [x] All duplicated code identified and documented
- [x] Common patterns and differences understood
- [x] Service interface designs drafted

### Tasks

### Completed
- [x] Design MetadataService interface
- [x] Design ValidationService interface
- [x] Design ContentService interface
- [x] Define implementation order: Metadata → Validation → Content

## Code

### Phase Entrance Criteria:
- [x] Service interfaces designed
- [x] Implementation order determined
- [x] Test strategy: Existing tests must pass (no new tests needed for pure refactoring)

### Tasks
- [ ] Create services/ package with __init__.py
- [ ] Implement MetadataService
- [ ] Update CLI to use MetadataService
- [ ] Update MCP to use MetadataService
- [ ] Verify all tests pass
- [ ] Implement ValidationService
- [ ] Update CLI to use ValidationService
- [ ] Update MCP to use ValidationService
- [ ] Verify all tests pass
- [ ] Implement ContentService with compute_hash
- [ ] Update CLI to use ContentService
- [ ] Update MCP to use ContentService
- [ ] Verify all tests pass
- [ ] Final verification: all 456 tests pass

### Completed
*None yet*

## Commit

### Phase Entrance Criteria:
- [ ] All services implemented
- [ ] CLI and MCP use services
- [ ] All tests pass
- [ ] No behavior changes

### Tasks
- [ ] Run linter
- [ ] Self code review
- [ ] Create PR

### Completed
*None yet*


---
*This plan is maintained by the LLM. Tool responses provide guidance on which section to focus on and what tasks to work on.*
