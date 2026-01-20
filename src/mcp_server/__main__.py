"""Allow running as python -m mcp_server."""

from mcp_server.main import main

if __name__ == "__main__":
    raise SystemExit(main())
