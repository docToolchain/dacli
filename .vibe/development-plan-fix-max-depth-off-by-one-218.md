# Development Plan: Fix #218 - get_structure max_depth off-by-one

*Generated on 2026-01-31 by Vibe Feature MCP*
*Workflow: [bugfix](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/bugfix)*

## Goal
Fix the off-by-one error in get_structure's max_depth parameter so that max_depth=N shows sections up to depth N (not N-1).

## Key Decisions
- Change condition from `current_depth < max_depth` to `current_depth <= max_depth`
- This maintains max_depth=0 showing only root (no children)

## Notes
- Issue: https://github.com/docToolchain/dacli/issues/218
- Branch: fix/max-depth-off-by-one-218
- Root cause already identified in issue: condition `current_depth < max_depth` should be `<=`

## Reproduce

### Phase Entrance Criteria:
- [x] Issue #218 has been reviewed and understood

### Tasks
- [ ] Create test document with nested sections
- [ ] Call get_structure with different max_depth values
- [ ] Verify off-by-one behavior

### Completed
- [x] Created development plan file

## Analyze

### Phase Entrance Criteria:
- [ ] Bug has been successfully reproduced
- [ ] Steps to reproduce are documented

### Tasks
- [ ] Verify root cause in structure_index.py
- [ ] Check if CLI has same issue

### Completed
*None yet*

## Fix

### Phase Entrance Criteria:
- [ ] Root cause verified
- [ ] Solution approach confirmed

### Tasks
- [ ] Write failing test
- [ ] Change `<` to `<=` in _section_to_dict
- [ ] Verify existing tests pass

### Completed
*None yet*

## Verify

### Phase Entrance Criteria:
- [ ] Fix implemented
- [ ] All tests pass

### Tasks
- [ ] Run full test suite
- [ ] Manual verification
- [ ] Test edge cases

### Completed
*None yet*

## Finalize

### Phase Entrance Criteria:
- [ ] All tests pass
- [ ] No regressions

### Tasks
- [ ] Update version
- [ ] Create commit
- [ ] Create PR

### Completed
*None yet*

---
*This plan is maintained by the LLM.*
