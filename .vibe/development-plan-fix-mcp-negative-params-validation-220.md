# Development Plan: Issue #220 - MCP Negative Parameter Validation

*Generated on 2026-01-31 by Vibe Feature MCP*
*Workflow: [bugfix](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/bugfix)*
*Branch: fix/mcp-negative-params-validation-220*

## Goal
Add validation to MCP tools to reject negative parameter values where only non-negative values make sense (max_results, max_depth, level, content_limit).

## Affected Tools and Parameters
| Tool | Parameter | Current Behavior |
|------|-----------|-----------------|
| `search` | `max_results` | -5 returns 8 results |
| `get_structure` | `max_depth` | -1 returns structure with no children |
| `get_sections_at_level` | `level` | -1 returns 0 sections |
| `get_elements` | `content_limit` | No validation error |

## Key Decisions
*Important decisions will be documented here as they are made*

## Notes
*Additional context and observations*

## Reproduce

### Tasks
- [ ] Write tests that show negative parameters are currently accepted without error
- [ ] Verify current behavior matches issue description

### Completed
- [x] Created development plan file

## Analyze

### Phase Entrance Criteria
- [ ] Bug has been reproduced with failing tests
- [ ] Current behavior is documented

### Tasks
- [ ] Identify MCP tool definitions in codebase
- [ ] Determine best validation approach (Pydantic Field validators vs manual checks)

### Completed
*None yet*

## Fix

### Phase Entrance Criteria
- [ ] Root cause is identified
- [ ] Validation approach is decided

### Tasks
- [ ] Add validation to reject negative values with clear error messages
- [ ] Run tests to verify fix

### Completed
*None yet*

## Verify

### Phase Entrance Criteria
- [ ] Fix is implemented
- [ ] All new tests pass

### Tasks
- [ ] Run full test suite
- [ ] Run linting
- [ ] Bump version

### Completed
*None yet*

## Finalize

### Phase Entrance Criteria
- [ ] All tests pass
- [ ] Linting passes
- [ ] Version bumped

### Tasks
- [ ] Commit changes
- [ ] Push to fork
- [ ] Create PR

### Completed
*None yet*

---
*This plan is maintained by the LLM. Tool responses provide guidance on which section to focus on and what tasks to work on.*
