# Development Plan: Fix #219 - validate_structure doesn't detect broken includes

*Generated on 2026-01-31 by Vibe Feature MCP*
*Workflow: [bugfix](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/bugfix)*

## Goal
Make validate_structure detect and report unresolved/broken include directives.

## Key Decisions
- Report broken includes as errors (not warnings) since they affect document integrity

## Notes
- Issue: https://github.com/docToolchain/dacli/issues/219
- Branch: fix/validate-broken-includes-219
- This is an MCP issue (validate_structure tool)

## Reproduce

### Phase Entrance Criteria:
- [x] Issue #219 has been reviewed and understood

### Tasks
- [ ] Create test document with broken include
- [ ] Call validate_structure via MCP or CLI
- [ ] Verify broken include is NOT reported

### Completed
- [x] Created development plan file

## Analyze

### Phase Entrance Criteria:
- [ ] Bug has been successfully reproduced
- [ ] Steps to reproduce are documented

### Tasks
- [ ] Find validate_structure implementation
- [ ] Understand how includes are currently handled
- [ ] Identify where broken include detection should happen

### Completed
*None yet*

## Fix

### Phase Entrance Criteria:
- [ ] Root cause identified
- [ ] Solution approach confirmed

### Tasks
- [ ] Write failing test
- [ ] Implement broken include detection
- [ ] Add proper error reporting

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
