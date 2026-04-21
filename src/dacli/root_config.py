"""Multi-root configuration parsing and validation (ADR-014).

Shared between MCP and CLI entry points. Handles parsing of
--workspace/--reference key=value specs and backward-compatible
--docs-root conversion.
"""

from pathlib import Path

from dacli.models import DocumentRoot

# Keys accepted in root specs
_REQUIRED_KEYS = {"name", "path"}
_OPTIONAL_KEYS = {"type"}
_ALL_KEYS = _REQUIRED_KEYS | _OPTIONAL_KEYS


class RootConfigError(Exception):
    """Raised for invalid root configuration."""


def parse_root_spec(spec: str, mode: str) -> DocumentRoot:
    """Parse a key=value root specification string.

    Format: name=my-docs,path=/path/to/docs[,type=arc42]

    Args:
        spec: Comma-separated key=value string
        mode: 'workspace' or 'reference'

    Returns:
        Parsed DocumentRoot

    Raises:
        RootConfigError: On missing keys, unknown keys, or invalid values
    """
    pairs: dict[str, str] = {}
    for part in spec.split(","):
        part = part.strip()
        if "=" not in part:
            raise RootConfigError(
                f"Invalid key=value pair '{part}' in --{mode} spec. "
                f"Expected format: name=my-docs,path=/path/to/docs"
            )
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in pairs:
            raise RootConfigError(f"Duplicate key '{key}' in --{mode} spec")
        pairs[key] = value

    # Check for unknown keys (forward compatibility — reject early)
    unknown = set(pairs.keys()) - _ALL_KEYS
    if unknown:
        raise RootConfigError(
            f"Unknown key(s) {unknown} in --{mode} spec. "
            f"Allowed keys: {sorted(_ALL_KEYS)}"
        )

    # Check required keys
    missing = _REQUIRED_KEYS - set(pairs.keys())
    if missing:
        raise RootConfigError(
            f"Missing required key(s) {missing} in --{mode} spec. "
            f"Expected format: name=my-docs,path=/path/to/docs"
        )

    path = Path(pairs["path"]).resolve()

    return DocumentRoot(
        name=pairs["name"],
        path=path,
        mode=mode,
        doc_type=pairs.get("type"),
    )


def resolve_roots(
    workspaces: list[str] | None = None,
    references: list[str] | None = None,
    docs_root: Path | None = None,
) -> list[DocumentRoot]:
    """Resolve root specifications into a validated list of DocumentRoots.

    Handles three modes:
    - --docs-root only: backward compat, single workspace
    - --workspace/--reference: multi-root mode
    - Neither: defaults to cwd as single workspace

    Args:
        workspaces: List of --workspace spec strings
        references: List of --reference spec strings
        docs_root: Legacy --docs-root path

    Returns:
        Validated list of DocumentRoot objects

    Raises:
        RootConfigError: On conflicts, collisions, or invalid paths
    """
    workspaces = workspaces or []
    references = references or []
    has_multi_root = bool(workspaces or references)

    if docs_root is not None and has_multi_root:
        raise RootConfigError(
            "Cannot combine --docs-root with --workspace/--reference. "
            "Use --workspace instead of --docs-root for multi-root mode."
        )

    roots: list[DocumentRoot] = []

    if has_multi_root:
        for spec in workspaces:
            roots.append(parse_root_spec(spec, "workspace"))
        for spec in references:
            roots.append(parse_root_spec(spec, "reference"))
    else:
        # Backward compat: --docs-root or cwd
        if docs_root is None:
            docs_root = Path.cwd()
        docs_root = docs_root.resolve()
        roots.append(DocumentRoot(
            name=docs_root.name,
            path=docs_root,
            mode="workspace",
        ))

    # Validate paths exist
    for root in roots:
        if not root.path.exists():
            raise RootConfigError(
                f"Documentation root does not exist: {root.path} "
                f"(namespace '{root.name}')"
            )
        if not root.path.is_dir():
            raise RootConfigError(
                f"Documentation root is not a directory: {root.path} "
                f"(namespace '{root.name}')"
            )

    # Check namespace collisions
    seen_names: dict[str, Path] = {}
    for root in roots:
        if root.name in seen_names:
            raise RootConfigError(
                f"Namespace collision: '{root.name}' is used by both "
                f"{seen_names[root.name]} and {root.path}. "
                f"Each root must have a unique name."
            )
        seen_names[root.name] = root.path

    return roots
