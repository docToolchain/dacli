"""Main entry point for MCP Documentation Server."""

import argparse
import sys

from mcp_server import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="mcp-docs-server",
        description="MCP Documentation Server - LLM interaction with documentation",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--docs-root",
        type=str,
        default=".",
        help="Root directory containing documentation files",
    )
    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # TODO: Implement server startup
    print(f"MCP Documentation Server v{__version__}")
    print(f"Docs root: {args.docs_root}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
