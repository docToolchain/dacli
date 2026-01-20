# MCP Documentation Server

Enables LLM interaction with large AsciiDoc/Markdown documentation projects through hierarchical, content-aware access via the Model Context Protocol (MCP).

## Installation

```bash
uv sync
```

## Usage

```bash
uv run python -m mcp_server --docs-root ./docs
```

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linter
uv run ruff check src tests
```

## License

MIT
