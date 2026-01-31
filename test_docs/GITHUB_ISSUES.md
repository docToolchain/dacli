# GitHub Issues für docToolchain/dacli

Die folgenden Bugs wurden beim Testen des dacli MCP-Servers gefunden. Da das `gh` CLI nicht installiert werden konnte, sind hier die Issue-Texte zum manuellen Erstellen.

---

## Issue #1: get_structure max_depth Off-By-One Error

**Repository:** docToolchain/dacli
**Title:** `get_structure: max_depth parameter has off-by-one error`
**Labels:** bug

### Body:

```markdown
## Bug Description

The `max_depth` parameter in the `get_structure` MCP tool has an off-by-one error. When `max_depth=N` is specified, the structure only shows sections up to depth N-1 instead of depth N.

## Expected Behavior

- `max_depth=0`: Show only root documents (no children)
- `max_depth=1`: Show root documents + their direct children
- `max_depth=2`: Show root documents + children + grandchildren

## Actual Behavior

- `max_depth=0`: Shows only root documents (correct)
- `max_depth=1`: Shows only root documents (INCORRECT - should also show direct children)
- `max_depth=2`: Shows root + children (INCORRECT - should also show grandchildren)

## Test Results

max_depth=0:
  Depth distribution: {0: 11}
  Max visible depth: 0
max_depth=1:
  Depth distribution: {0: 11}
  Max visible depth: 0  # Should be 1!
max_depth=2:
  Depth distribution: {0: 11, 1: 61}
  Max visible depth: 1  # Should be 2!
max_depth=None:
  Depth distribution: {0: 11, 1: 61, 2: 18, 3: 4, 4: 2, 5: 2}
  Max visible depth: 5

## Root Cause

In `structure_index.py`, the `get_structure` method calls `_section_to_dict` with `current_depth=1`:

# Line 119
self._section_to_dict(s, max_depth, current_depth=1)

And `_section_to_dict` uses the condition `current_depth < max_depth`:

# Line 642
if max_depth is None or current_depth < max_depth:
    result["children"] = [...]
else:
    result["children"] = []

When `max_depth=1` and `current_depth=1`, the condition `1 < 1` is `False`, so no children are included.

## Suggested Fix

Either:
1. Change the condition to `current_depth <= max_depth`
2. Or start `current_depth` at 0 instead of 1

## Version

- dacli version: 0.4.9
```

---

## Issue #2: validate_structure Does Not Detect Broken Includes

**Repository:** docToolchain/dacli
**Title:** `validate_structure: Broken (unresolved) includes are not detected`
**Labels:** bug

### Body:

```markdown
## Bug Description

When a document contains an `include::` directive referencing a non-existent file, `validate_structure` reports `valid=True` with no errors or warnings about the missing include.

## Steps to Reproduce

1. Create a document `broken_include.adoc` with:
= Document with Broken Include

== Valid Section

Some content.

include::nonexistent_file.adoc[]

== After Broken Include

More content.

2. Start the MCP server with this document
3. Call `validate_structure`
4. Observe the result

## Expected Behavior

The validation should report an error or warning about the unresolved include:

{
  "valid": false,
  "errors": [
    {
      "type": "unresolved_include",
      "file": "broken_include.adoc",
      "line": 8,
      "include_path": "nonexistent_file.adoc",
      "message": "Include file 'nonexistent_file.adoc' not found"
    }
  ]
}

## Actual Behavior

{
  "valid": true,
  "errors": [],
  "warnings": [
    // Only orphaned file warnings, nothing about the broken include
  ]
}

## Impact

Users cannot rely on `validate_structure` to detect broken includes, which is one of its documented purposes ("unresolved includes" is listed as an error type in the tool description).

## Version

- dacli version: 0.4.9
```

---

## Issue #3: Negative Parameter Values Not Validated

**Repository:** docToolchain/dacli
**Title:** `MCP Tools: Negative parameter values are not validated`
**Labels:** bug, enhancement

### Body:

```markdown
## Bug Description

Several MCP tools accept negative values for parameters that should logically only accept non-negative integers. This leads to undefined or confusing behavior.

## Affected Tools and Parameters

| Tool | Parameter | Negative Value | Actual Behavior |
|------|-----------|---------------|-----------------|
| `search` | `max_results` | -5 | Returns 8 results |
| `get_structure` | `max_depth` | -1 | Returns structure with no children |
| `get_sections_at_level` | `level` | -1 | Returns 0 sections |
| `get_elements` | `content_limit` | -10 | No validation error |

## Test Code

result = await client.call_tool("search", arguments={"query": "test", "max_results": -5})
# Returns 8 results instead of raising an error or returning 0

result = await client.call_tool("get_structure", arguments={"max_depth": -1})
# Returns 11 root sections with no children

result = await client.call_tool("get_sections_at_level", arguments={"level": -1})
# Returns count=0, no error

## Expected Behavior

Either:
1. **Validate and reject**: Raise a validation error for negative values with a clear message
2. **Document and handle**: Treat negative values as "unlimited" and document this behavior

## Suggested Fix

Add validation to reject negative values:

@mcp.tool()
def search(query: str, max_results: int = 20) -> dict:
    if max_results < 0:
        raise ValueError("max_results must be non-negative")
    # ...

Or use Pydantic validators for automatic validation.

## Version

- dacli version: 0.4.9
```

---

## Erstellen der Issues

Um diese Issues auf GitHub zu erstellen:

1. Gehe zu https://github.com/docToolchain/dacli/issues/new
2. Kopiere den Titel und Body aus den obigen Abschnitten
3. Füge passende Labels hinzu (z.B. `bug`)
4. Submit das Issue

Alternativ, wenn das `gh` CLI verfügbar ist:

```bash
# Issue #1
gh issue create --repo docToolchain/dacli \
  --title "get_structure: max_depth parameter has off-by-one error" \
  --body-file issue1.md \
  --label bug

# Issue #2
gh issue create --repo docToolchain/dacli \
  --title "validate_structure: Broken (unresolved) includes are not detected" \
  --body-file issue2.md \
  --label bug

# Issue #3
gh issue create --repo docToolchain/dacli \
  --title "MCP Tools: Negative parameter values are not validated" \
  --body-file issue3.md \
  --label bug,enhancement
```
