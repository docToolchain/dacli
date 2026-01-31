# GitHub Issues for dacli

This file contains bug reports and enhancement suggestions discovered during CLI testing. Each issue is formatted for direct copy-paste into GitHub Issues.

---

## Issue 1: `structure --max-depth` accepts negative values

**Labels:** `bug`, `cli`

### Title
CLI: `structure --max-depth` accepts negative values without error

### Description
The `structure` command accepts negative values for the `--max-depth` parameter without raising an error. This is inconsistent with the validation behavior of `sections-at-level`, which correctly rejects negative level values.

### Steps to Reproduce
```bash
dacli --docs-root /path/to/docs structure --max-depth -1
```

### Expected Behavior
Error message similar to `sections-at-level`:
```
Error: Invalid value for max-depth: Value must be non-negative, got -1.
```

### Actual Behavior
Command executes successfully and returns results (appears to treat -1 as unlimited depth, same as not specifying the parameter).

### Environment
- dacli version: 0.4.20
- Python: 3.12.3
- OS: Linux

### Suggested Fix
Add validation in the CLI layer to reject negative `--max-depth` values before calling the service layer.

---

## Issue 2: `search --limit` accepts negative values

**Labels:** `bug`, `cli`

### Title
CLI: `search --limit` accepts negative values without error

### Description
The `search` command accepts negative values for the `--limit` / `--max-results` parameter without validation. Negative limits don't make semantic sense for result limiting.

### Steps to Reproduce
```bash
dacli --docs-root /path/to/docs search "test" --limit -5
```

### Expected Behavior
Error message:
```
Error: Invalid value for --limit: Value must be a positive integer, got -5.
```

### Actual Behavior
Command executes successfully and returns normal search results (negative value is likely ignored or treated as unlimited).

### Environment
- dacli version: 0.4.20
- Python: 3.12.3
- OS: Linux

### Suggested Fix
Add validation in the CLI layer to ensure `--limit` is a positive integer.

---

## Issue 3: `search --limit 0` behavior is semantically unclear

**Labels:** `enhancement`, `cli`, `documentation`

### Title
CLI: Clarify or change `search --limit 0` behavior

### Description
When `search --limit 0` is specified, the command returns 0 results. This behavior is semantically ambiguous:
- Some CLI tools treat `limit 0` as "unlimited" (e.g., MySQL)
- Others treat it literally as "return 0 results"

The current behavior (returning 0 results) may not be what users expect.

### Steps to Reproduce
```bash
dacli --docs-root /path/to/docs search "content" --limit 0
```

### Expected Behavior (Option A - Reject)
```
Error: Invalid value for --limit: Value must be at least 1, got 0.
```

### Expected Behavior (Option B - Unlimited)
```
query: content
results:
  [all matching results...]
total_results: N
```

### Actual Behavior
```
query: content
results:
total_results: 0
```

### Suggested Resolution
Either:
1. Reject `--limit 0` with a clear error message
2. Treat `--limit 0` as "no limit" and document this behavior
3. Document the current behavior clearly in the help text

---

## Issue 4: `update` command allows empty content without warning

**Labels:** `enhancement`, `cli`, `ux`

### Title
CLI: `update` command should warn or reject empty content

### Description
The `update` command accepts empty content (`--content ""`), which effectively clears the entire section content. While this might be intentional, it's a potentially destructive operation that could benefit from a confirmation or warning.

### Steps to Reproduce
```bash
dacli --docs-root /path/to/docs update doc:section --content ""
```

### Current Behavior
- Command succeeds silently
- Section content is completely removed (only heading remains)

### Suggested Enhancement
Option A: Require `--force` flag for empty content
```bash
dacli update doc:section --content "" --force
# Without --force:
# Error: Cannot clear section content. Use --force to confirm.
```

Option B: Interactive confirmation
```
Warning: This will clear all content from section 'doc:section'. Continue? [y/N]
```

Option C: At minimum, show a warning
```
Warning: Section content cleared.
success: True
...
```

### Impact
Protects users from accidentally clearing section content when they may have intended to provide actual content.

---

## Issue 5: `insert` command allows empty content

**Labels:** `enhancement`, `cli`, `ux`

### Title
CLI: `insert` command should warn or reject empty content

### Description
The `insert` command accepts empty content (`--content ""`), which inserts blank lines into the document. This is unlikely to be the intended behavior and may indicate user error.

### Steps to Reproduce
```bash
dacli --docs-root /path/to/docs insert doc:section --position before --content ""
```

### Current Behavior
- Command succeeds
- Blank lines are inserted at the specified position

### Suggested Enhancement
Show a warning or reject empty content:
```
Error: Cannot insert empty content. Provide content to insert.
```

Or at minimum:
```
Warning: Inserting empty content (blank lines only).
success: True
...
```

---

## Issue 6: Empty AsciiDoc files displayed with filename as title

**Labels:** `enhancement`, `parser`, `ux`

### Title
Empty AsciiDoc files are treated as valid documents with filename as title

### Description
When an AsciiDoc file is completely empty (0 bytes or only whitespace), it appears in the document structure as a valid document with the filename (without extension) as its title. This may confuse users who might not expect empty files to appear in the structure.

### Steps to Reproduce
```bash
# Create empty file
echo "" > /path/to/docs/empty.adoc

# Check structure
dacli --docs-root /path/to/docs structure
```

### Current Behavior
```yaml
sections:
  path: empty
  title: empty
  level: 0
  location:
    file: /path/to/docs/empty.adoc
    line: 1
    end_line: 1
  children:
```

### Suggested Enhancement
Option A: Exclude empty files from structure
- Files with no content or only whitespace are not included

Option B: Mark as empty in output
```yaml
sections:
  path: empty
  title: empty (no content)
  level: 0
  ...
```

Option C: Report in validation
```yaml
warnings:
  type: empty_file
  path: empty.adoc
  message: File has no content
```

### Impact
Helps users identify and clean up empty placeholder files in their documentation.

---

## Issue 7: Circular includes reported as orphaned files, not as circular

**Labels:** `enhancement`, `validation`

### Title
Validation: Circular includes could be detected and reported more specifically

### Description
When two AsciiDoc files include each other circularly (A includes B, B includes A), the validation reports them as "orphaned files" rather than detecting the circular dependency explicitly.

### Steps to Reproduce
```bash
# Create circular_a.adoc
cat > circular_a.adoc << 'EOF'
= Document A
include::circular_b.adoc[]
EOF

# Create circular_b.adoc
cat > circular_b.adoc << 'EOF'
= Document B
include::circular_a.adoc[]
EOF

# Validate
dacli --docs-root . validate
```

### Current Behavior
```yaml
warnings:
  type: orphaned_file
  path: circular_a.adoc
  message: File is not included in any document
  type: orphaned_file
  path: circular_b.adoc
  message: File is not included in any document
```

### Expected Behavior
```yaml
errors:
  type: circular_include
  path: circular_a.adoc:2
  message: Circular include detected: circular_a.adoc -> circular_b.adoc -> circular_a.adoc
```

### Note
This may be by design if both files are treated as separate root documents (both have level-0 titles). In that case, the behavior is correct but the documentation could clarify this.

---

## Issue 8: Improve input validation consistency across commands

**Labels:** `enhancement`, `cli`, `consistency`

### Title
CLI: Unify input validation across all commands

### Description
Some commands have strict input validation while others do not. This inconsistency can confuse users.

### Comparison Table

| Command | Parameter | Negative Values | Zero Values |
|---------|-----------|-----------------|-------------|
| `sections-at-level` | `LEVEL` | Rejected | Allowed |
| `structure` | `--max-depth` | Allowed (BUG) | Allowed |
| `search` | `--limit` | Allowed (BUG) | Allowed (returns 0) |

### Suggested Fix
Implement consistent validation across all numeric parameters:
1. Negative values should be rejected for all count/level/limit parameters
2. Zero should either be consistently rejected or have documented meaning
3. Validation error messages should follow a consistent format

### Implementation Notes
Consider creating a shared validation decorator or helper function that can be applied to all numeric CLI parameters.

---

## Summary

| Issue # | Type | Priority | Effort |
|---------|------|----------|--------|
| 1 | Bug | Medium | Low |
| 2 | Bug | Medium | Low |
| 3 | Enhancement | Low | Low |
| 4 | Enhancement | Low | Medium |
| 5 | Enhancement | Low | Low |
| 6 | Enhancement | Low | Medium |
| 7 | Enhancement | Low | Medium |
| 8 | Enhancement | Medium | Medium |

**Total: 2 bugs, 6 enhancements**
