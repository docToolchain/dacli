# Development Plan: Fix #216 - Insert --position before missing blank line

*Generated on 2026-01-31 by Vibe Feature MCP*
*Workflow: [bugfix](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/bugfix)*

## Goal
Fix the missing blank line between inserted section and following section when using `insert --position before`.

## Key Decisions
- Ensure consistent spacing behavior between `--position before` and `--position after`

## Notes
- Issue: https://github.com/docToolchain/dacli/issues/216
- Branch: fix/insert-before-blank-line-216
- Related: #223 (insert after - already fixed), same code location in cli.py

## Reproduce

### Phase Entrance Criteria:
- [x] Issue #216 has been reviewed and understood

### Tasks
- [ ] Create test document with multiple sections
- [ ] Run insert --position before command
- [ ] Verify missing blank line in output

### Completed
- [x] Created development plan file

## Analyze

### Phase Entrance Criteria:
- [ ] Bug has been successfully reproduced
- [ ] Steps to reproduce are documented

### Tasks
- [ ] Find the insert code in cli.py
- [ ] Compare before/after position handling
- [ ] Identify why blank line is missing

### Completed
*None yet*

## Fix

### Phase Entrance Criteria:
- [ ] Root cause identified
- [ ] Solution approach confirmed

### Tasks
- [ ] Write failing test
- [ ] Implement blank line handling for --position before
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
