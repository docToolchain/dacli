# Development Plan: Fix #214 - HTML comments in Markdown not ignored

*Generated on 2026-01-31 by Vibe Feature MCP*
*Workflow: [bugfix](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/bugfix)*

## Goal
Make the Markdown parser ignore headings inside HTML comment blocks (`<!-- -->`).

## Key Decisions
- Strip HTML comments from content before parsing headings
- Handle multi-line comments correctly

## Notes
- Issue: https://github.com/docToolchain/dacli/issues/214
- Branch: fix/markdown-html-comments-214
- AsciiDoc comments (`//`) already work correctly

## Reproduce

### Phase Entrance Criteria:
- [x] Issue #214 has been reviewed and understood

### Tasks
- [ ] Create Markdown file with HTML comment containing heading
- [ ] Run structure command
- [ ] Verify phantom section appears

### Completed
- [x] Created development plan file

## Analyze

### Phase Entrance Criteria:
- [ ] Bug has been successfully reproduced
- [ ] Steps to reproduce are documented

### Tasks
- [ ] Find Markdown parser implementation
- [ ] Understand heading detection logic
- [ ] Identify where comment stripping should happen

### Completed
*None yet*

## Fix

### Phase Entrance Criteria:
- [ ] Root cause identified
- [ ] Solution approach confirmed

### Tasks
- [ ] Write failing test
- [ ] Implement HTML comment stripping
- [ ] Handle multi-line comments

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
