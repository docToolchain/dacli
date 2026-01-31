# Development Plan: Fix #217 - Update with level change destroys hierarchy

*Generated on 2026-01-31 by Vibe Feature MCP*
*Workflow: [bugfix](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/bugfix)*

## Goal
Prevent update command from silently destroying document hierarchy when changing heading levels with `--no-preserve-title`.

## Key Decisions
- **Approach:** Reject the operation if level change would break hierarchy (Option 1 from issue)
- This is safer than auto-adjusting child levels (complex, error-prone)

## Notes
- Issue: https://github.com/docToolchain/dacli/issues/217
- Branch: fix/update-level-change-hierarchy-217
- Related: #208, #223 (hierarchy preservation issues)

## Reproduce

### Phase Entrance Criteria:
- [x] Issue #217 has been reviewed and understood

### Tasks
*All completed*

### Completed
- [x] Created development plan file
- [x] Created feature branch
- [x] Created test document with parent-child hierarchy
- [x] Reproduced bug: test:level-1.child became test:child (sibling)
- [x] Documented: Level change causes children to lose parent relationship

## Analyze

### Phase Entrance Criteria:
- [x] Bug has been successfully reproduced
- [x] Steps to reproduce are documented

### Tasks
*All completed*

### Completed
- [x] Found: content_service.py:update_section()
- [x] Understood: preserve_title=False skips title validation but not level check
- [x] Root cause: Lines 141-155 only check for title presence, not level change with children

## Fix

### Phase Entrance Criteria:
- [x] Root cause identified
- [x] Solution approach confirmed

### Tasks
*All completed*

### Completed
- [x] Write failing test (tests/test_level_change_hierarchy_217.py)
- [x] Implement level change detection in content_service.py
- [x] Add error message when children would be affected
- [x] Verify existing tests pass (559 tests)

## Verify

### Phase Entrance Criteria:
- [x] Fix implemented
- [x] All tests pass

### Tasks
*All completed*

### Completed
- [x] Run full test suite (559 passed)
- [x] Linting passed (ruff check)
- [x] All edge cases covered (5 test cases)

## Finalize

### Phase Entrance Criteria:
- [x] All tests pass
- [x] No regressions

### Tasks
- [x] Update version (0.4.10 → 0.4.11)
- [ ] Create commit
- [ ] Create PR

### Completed
- [x] Version bumped in pyproject.toml, __init__.py, uv.lock

---
*This plan is maintained by the LLM.*
