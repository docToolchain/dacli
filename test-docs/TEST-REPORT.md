# dacli Test Report

**Version Tested:** 0.4.9
**Date:** 2026-01-31
**Test Environment:** Linux 4.4.0, Python 3.12

## Executive Summary

Extensive testing of the dacli CLI tool was performed, covering both AsciiDoc and Markdown documentation parsing. While the core functionality (structure parsing, section reading, searching) works well, **one critical bug** was discovered that can corrupt document structure, along with several minor issues.

## Test Coverage

### Tested Commands
- `dacli structure` - ✅ Works correctly
- `dacli section` - ✅ Works correctly
- `dacli search` - ✅ Works correctly
- `dacli elements` - ✅ Works correctly
- `dacli metadata` - ✅ Works correctly
- `dacli validate` - ✅ Works correctly
- `dacli update` - ✅ Works correctly
- `dacli insert` - ❌ **Critical bug found**
- `dacli sections-at-level` - ✅ Works correctly

### Tested Formats
- AsciiDoc (.adoc) - ✅ Parsing works
- Markdown (.md) - ✅ Parsing works

### Tested Features
- Hierarchical section navigation - ✅
- Code block extraction - ✅
- Table extraction - ✅
- PlantUML/diagram extraction - ✅
- JSON/YAML/Text output formats - ✅
- Optimistic locking (hash validation) - ✅
- Error handling for missing sections - ✅
- Error handling for invalid paths - ✅

---

## Critical Bug

### BUG-001: `insert --position after` Corrupts Document Structure

**Severity:** CRITICAL
**Reproducibility:** 100%
**Affects:** Both AsciiDoc and Markdown

**Description:**
The `insert --position after` command inserts content directly after the section header instead of after the entire section (including all child sections). This corrupts the document hierarchy by moving child sections under the wrong parent.

**Steps to Reproduce:**
```bash
# Given a document structure:
# - Introduction
#   - Overview
#   - Goals
# - Architecture

# Run:
dacli --docs-root ./docs insert "doc:introduction" --position after --content "
== New Section

New content."

# Expected: New Section is inserted AFTER Introduction (and its children)
# Actual: New Section is inserted AFTER Introduction header, BEFORE Overview
```

**Result:**
- Before: `introduction.overview`, `introduction.goals`
- After: `new-section.overview`, `new-section.goals` (Overview and Goals become children of New Section!)

**Impact:**
This bug can silently corrupt document structure, breaking existing section paths and potentially causing data loss.

---

## Minor Issues

### ISSUE-001: Empty Files Shown with Invalid Line Range

**Severity:** LOW
**Affects:** Structure output

**Description:**
Empty files are displayed in structure output with `end_line: 0`, which is an invalid line range (line numbers should start at 1).

**Steps to Reproduce:**
```bash
# Create an empty .adoc file
touch docs/empty.adoc

# Get structure
dacli --docs-root ./docs --format json structure
# Shows: {"path": "empty", "location": {"line": 1, "end_line": 0}}
```

**Expected:** Empty files should either be skipped or have a valid line range.

---

### ISSUE-002: Invalid Element Types Silently Return Empty Results

**Severity:** LOW
**Affects:** `elements` command

**Description:**
When specifying an invalid element type, the command returns `count: 0` without any warning or error message.

**Steps to Reproduce:**
```bash
dacli --docs-root ./docs elements --type invalid_type
# Returns: elements: [] count: 0
# Expected: Error or warning about invalid type
```

---

### ISSUE-003: Search with Invalid Scope Returns No Warning

**Severity:** LOW
**Affects:** `search` command

**Description:**
When specifying a non-existent scope, search returns 0 results without indicating that the scope doesn't exist.

**Steps to Reproduce:**
```bash
dacli --docs-root ./docs search "test" --scope "nonexistent"
# Returns: total_results: 0
# Expected: Warning that scope 'nonexistent' doesn't exist
```

---

### ISSUE-004: Negative max-depth Values Accepted Without Warning

**Severity:** LOW
**Affects:** `structure` command

**Description:**
Negative values for `--max-depth` are accepted and behave like `--max-depth 0`, which may be confusing.

**Steps to Reproduce:**
```bash
dacli --docs-root ./docs structure --max-depth -1
# Works without error, shows only root sections
```

**Expected:** Either reject negative values with an error, or document this behavior.

---

## Working Features (Positive Tests)

The following features were tested and work correctly:

1. **Structure Parsing**
   - Correctly parses nested sections up to 6 levels deep
   - Handles special characters in section titles (äöü, &, <, >)
   - Handles very long section titles

2. **Section Content Retrieval**
   - Correctly returns section content with line numbers
   - Properly identifies AsciiDoc vs Markdown format

3. **Search**
   - Full-text search works correctly
   - Respects `--limit` parameter
   - Works with special characters (äöü)

4. **Elements Extraction**
   - Code blocks with language detection
   - Tables
   - PlantUML diagrams
   - `--include-content` flag works correctly
   - `--recursive` flag works correctly

5. **Update Command**
   - Content updates work correctly
   - Optimistic locking with hash validation works
   - Hash conflict detection works

6. **Error Handling**
   - Non-existent sections return proper error codes
   - Invalid docs-root paths are rejected
   - Empty search queries are rejected

---

## Recommendations

1. **Immediate:** Fix BUG-001 as it can cause silent data corruption
2. **High:** Add validation for element types with helpful error messages
3. **Medium:** Add warnings for empty scopes in search
4. **Low:** Validate and reject negative max-depth values or document behavior

---

## Test Files Used

- `test-docs/asciidoc/index.adoc` - Main AsciiDoc test file
- `test-docs/asciidoc/advanced.adoc` - Edge cases in AsciiDoc
- `test-docs/asciidoc/empty.adoc` - Empty file test
- `test-docs/markdown/index.md` - Main Markdown test file
- `test-docs/markdown/edge-cases.md` - Edge cases in Markdown
