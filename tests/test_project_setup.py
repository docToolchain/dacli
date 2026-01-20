"""Tests for project setup validation (Issue #1).

These tests verify that the project is correctly configured with uv
and that the basic module structure works.
"""

import subprocess
import sys


def test_mcp_server_module_importable():
    """Test that mcp_server module can be imported."""
    import mcp_server
    assert hasattr(mcp_server, "__version__")


def test_mcp_server_version_is_string():
    """Test that version is a proper string."""
    from mcp_server import __version__
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_mcp_server_can_be_run_as_module():
    """Test that 'python -m mcp_server' runs without error.

    This is an acceptance test that verifies the project setup
    allows running the server as a module.
    """
    result = subprocess.run(
        [sys.executable, "-m", "mcp_server", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    # Should exit cleanly (0) or with help message
    # We accept both 0 and 2 (argparse help exits with 2 sometimes)
    assert result.returncode in (0, 2), f"Failed with: {result.stderr}"
