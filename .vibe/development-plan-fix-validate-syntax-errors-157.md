# Development Plan: Fix validate syntax errors (Issue #157)

*Generated on 2026-01-23 by Vibe Feature MCP*
*Workflow: [tdd](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/tdd)*

## Goal

Fix bug where `validate` command only detects the last unclosed block instead of all unclosed blocks.

**Root Cause:** `current_block_element` stores only ONE element. When multiple blocks are opened without closing, only the last one is tracked.

**Solution:** Replace single element tracking with a stack (`open_blocks: list[Element]`) to track all open blocks.

## Key Decisions

1. Unclosed blocks remain **Warnings** (not Errors) - document stays `valid: true`
2. `unresolved_include` feature moved to separate Issue #160
3. Related Issue #158 (section consumes content) will be fixed by same change

## Notes

- Affected file: `src/dacli/asciidoc_parser.py` - `_parse_elements()` method
- Need to handle: code blocks, plantuml, mermaid, ditaa, tables
- Each block type uses same `----` or `|===` delimiter pattern

## Explore

### Phase Entrance Criteria
- [x] Initial phase - no entrance criteria

### Tasks
- [x] Analyze root cause in `_parse_elements()` method
- [x] Identify all block types that need tracking
- [x] Review current warning generation logic
- [x] Document solution approach

### Completed
- [x] Created development plan file
- [x] Root cause identified: single `current_block_element` variable
- [x] Block types: code, plantuml, mermaid, ditaa, table

## Red

### Phase Entrance Criteria
- [ ] Exploration complete - root cause understood
- [ ] Solution approach documented
- [ ] All affected block types identified

### Tasks
- [ ] Write test for multiple unclosed code blocks
- [ ] Write test for mixed unclosed blocks (code + table)
- [ ] Verify tests fail with current implementation

### Completed
*None yet*

## Green

### Phase Entrance Criteria
- [ ] Failing tests written and verified
- [ ] Test covers multiple unclosed blocks scenario

### Tasks
- [ ] Replace `current_block_element` with `open_blocks` stack
- [ ] Update block opening logic to push to stack
- [ ] Update block closing logic to pop from stack
- [ ] Generate warnings for all unclosed blocks at end
- [ ] Run tests to verify they pass

### Completed
*None yet*

## Refactor

### Phase Entrance Criteria
- [ ] All tests passing
- [ ] Multiple unclosed blocks correctly detected

### Tasks
- [ ] Review code for duplication
- [ ] Ensure consistent handling across all block types
- [ ] Update version number
- [ ] Self code review

### Completed
*None yet*

---
*This plan is maintained by the LLM. Tool responses provide guidance on which section to focus on and what tasks to work on.*
