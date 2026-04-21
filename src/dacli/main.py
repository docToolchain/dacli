"""Main entry point for dacli MCP server.

This module provides the CLI entry point for running the MCP server.
The server can be configured via command line arguments or environment variables.

Usage:
    # Single-root (backward compatible):
    uv run dacli-mcp --docs-root /path/to/docs

    # Multi-root (ADR-014):
    uv run dacli-mcp --workspace name=my-project,path=/path/to/docs \
                     --reference name=base-api,path=/path/to/api-docs

    Or with environment variable:
    PROJECT_PATH=/path/to/docs uv run dacli-mcp

MCP Client Configuration (e.g., Claude Desktop):
    {
        "mcpServers": {
            "dacli": {
                "command": "uv",
                "args": ["run", "dacli-mcp"],
                "cwd": "/path/to/dacli",
                "env": {"PROJECT_PATH": "/path/to/documentation"}
            }
        }
    }
"""

import argparse
import os
import sys
from pathlib import Path

from dacli import __version__
from dacli.mcp_app import create_mcp_server
from dacli.root_config import RootConfigError, resolve_roots


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="dacli-mcp",
        description="dacli MCP server - LLM interaction with documentation",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--docs-root",
        type=str,
        default=None,
        help="Root directory containing documentation files (single-root mode). "
        "Can also be set via PROJECT_PATH environment variable. "
        "Cannot be combined with --workspace/--reference.",
    )
    parser.add_argument(
        "--workspace",
        action="append",
        default=None,
        metavar="name=X,path=Y[,type=Z]",
        help="Read-write documentation root (repeatable). "
        "Required keys: name, path. Optional: type.",
    )
    parser.add_argument(
        "--reference",
        action="append",
        default=None,
        metavar="name=X,path=Y[,type=Z]",
        help="Read-only documentation root (repeatable). "
        "Required keys: name, path. Optional: type.",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        default=False,
        help="Include files that would normally be excluded by .gitignore patterns.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        default=False,
        help="Include files in hidden directories (starting with '.').",
    )
    return parser


def get_docs_root(args_docs_root: str | None) -> Path | None:
    """Determine the documentation root directory from legacy options.

    Priority:
    1. Command line argument (--docs-root)
    2. PROJECT_PATH environment variable
    3. None (caller decides default)

    Args:
        args_docs_root: Value from command line argument (may be None)

    Returns:
        Resolved path to documentation root, or None if not specified
    """
    if args_docs_root is not None:
        return Path(args_docs_root).resolve()

    env_path = os.environ.get("PROJECT_PATH")
    if env_path:
        return Path(env_path).resolve()

    return None


def main() -> int:
    """Main entry point.

    Creates and runs the MCP server with stdio transport.
    """
    parser = create_parser()
    args = parser.parse_args()

    docs_root = get_docs_root(args.docs_root)

    try:
        roots = resolve_roots(
            workspaces=args.workspace,
            references=args.reference,
            docs_root=docs_root,
        )
    except RootConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Create and run MCP server
    mcp = create_mcp_server(
        roots=roots,
        respect_gitignore=not args.no_gitignore,
        include_hidden=args.include_hidden,
    )

    # Run with stdio transport (default for MCP)
    mcp.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
