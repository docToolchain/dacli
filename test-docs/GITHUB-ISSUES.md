# GitHub Issues to Create

Run these commands to create issues on doctoolchain/dacli:

```bash
# First authenticate with GitHub CLI
gh auth login

# Then create the issues:
```

---

## Issue 1: Critical Bug - insert --position after corrupts document structure

```bash
gh issue create --repo doctoolchain/dacli --title "Critical: insert --position after corrupts document structure by inserting after header instead of after section" --body "$(cat <<'EOF'
## Description

The `insert --position after` command inserts content directly after the section header instead of after the entire section (including all child sections). This corrupts the document hierarchy by moving child sections under the wrong parent.

## Steps to Reproduce

1. Create a document with nested sections:
```asciidoc
= Document

== Introduction

Introduction content.

=== Overview

Overview content.

=== Goals

Goals content.

== Architecture

Architecture content.
```

2. Run the insert command:
```bash
dacli --docs-root ./docs insert "doc:introduction" --position after --content "
== New Section

New content."
```

3. Check the structure:
```bash
dacli --docs-root ./docs section "doc:introduction.overview"
```

## Expected Behavior

The new section should be inserted AFTER the entire "Introduction" section including its child sections (Overview, Goals). The resulting structure should be:
- Introduction
  - Overview
  - Goals
- New Section
- Architecture

## Actual Behavior

The new section is inserted directly after the "Introduction" header, BEFORE "Overview". This makes "Overview" and "Goals" become children of "New Section" instead of "Introduction":
- Introduction
- New Section
  - Overview
  - Goals
- Architecture

Error when trying to access the original path:
```
error:
  code: PATH_NOT_FOUND
  message: Section 'doc:introduction.overview' not found
  details:
    suggestions:
      - doc:new-section.overview
```

## Impact

This bug can silently corrupt document structure, breaking existing section paths and potentially causing data loss when documentation tools or scripts rely on specific paths.

## Environment

- dacli version: 0.4.9
- OS: Linux
- Affects: Both AsciiDoc and Markdown formats

## Suggested Fix

The insert logic should use the section's `end_line` (which includes all child sections) to determine where to insert content for `--position after`, not the section header's end line.
EOF
)"
```

---

## Issue 2: Empty files shown with invalid line range (end_line: 0)

```bash
gh issue create --repo doctoolchain/dacli --title "Empty files displayed in structure with invalid line range (end_line: 0)" --body "$(cat <<'EOF'
## Description

When a documentation folder contains empty files, these are included in the structure output with an invalid line range where `end_line: 0`. Since line numbers typically start at 1, this is inconsistent and could cause issues for tools that process the structure output.

## Steps to Reproduce

1. Create an empty AsciiDoc or Markdown file:
```bash
touch docs/empty.adoc
```

2. Get the structure in JSON format:
```bash
dacli --docs-root ./docs --format json structure
```

## Actual Output

```json
{
  "path": "empty",
  "title": "empty",
  "level": 0,
  "location": {
    "file": "/path/to/docs/empty.adoc",
    "line": 1,
    "end_line": 0
  },
  "children": []
}
```

## Expected Behavior

Either:
1. Skip empty files entirely (they have no content to document)
2. Use a valid line range like `line: 1, end_line: 1`

## Environment

- dacli version: 0.4.9
EOF
)"
```

---

## Issue 3: Invalid element types silently return empty results

```bash
gh issue create --repo doctoolchain/dacli --title "elements command silently returns empty for invalid element types" --body "$(cat <<'EOF'
## Description

When using the `elements` command with an invalid `--type` value, the command returns `count: 0` without any warning or error message. This makes it difficult to detect typos or understand why no elements were found.

## Steps to Reproduce

```bash
dacli --docs-root ./docs elements --type invalid_type
```

## Actual Output

```yaml
elements:
count: 0
```

## Expected Behavior

Either:
1. Return an error message indicating the type is invalid
2. Show a warning message listing valid element types (code, table, image, diagram, list)

For example:
```
Warning: Unknown element type 'invalid_type'. Valid types are: code, table, image, diagram, list
```

## Environment

- dacli version: 0.4.9
EOF
)"
```

---

## Issue 4: Search with non-existent scope returns no warning

```bash
gh issue create --repo doctoolchain/dacli --title "search command does not warn when scope path doesn't exist" --body "$(cat <<'EOF'
## Description

When using the `search` command with a `--scope` that doesn't exist in the documentation, the command silently returns 0 results without any indication that the scope path is invalid.

## Steps to Reproduce

```bash
dacli --docs-root ./docs search "test" --scope "nonexistent-section"
```

## Actual Output

```yaml
query: test
results:
total_results: 0
```

## Expected Behavior

The command should warn that the specified scope doesn't exist:
```
Warning: Scope 'nonexistent-section' not found in documentation structure.
query: test
results:
total_results: 0
```

This helps users identify typos in scope paths or understand that they're searching in the wrong location.

## Environment

- dacli version: 0.4.9
EOF
)"
```

---

## Summary

| Issue | Severity | Title |
|-------|----------|-------|
| 1 | CRITICAL | insert --position after corrupts document structure |
| 2 | LOW | Empty files with invalid line range |
| 3 | LOW | Invalid element types silently return empty |
| 4 | LOW | Search with non-existent scope returns no warning |
