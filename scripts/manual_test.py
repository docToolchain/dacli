#!/usr/bin/env python3
"""Manual Test Script for MCP Documentation Server.

This script performs comprehensive manual testing of the MCP server.
Run it to verify all tools work correctly before releases or after changes.

Usage:
    uv run python scripts/manual_test.py [--docs-root PATH]

Examples:
    # Test with project docs
    uv run python scripts/manual_test.py

    # Test with custom docs directory
    uv run python scripts/manual_test.py --docs-root /path/to/docs
"""

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.client import Client

from mcp_server.mcp_app import create_mcp_server


class TestResult:
    """Tracks test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: list[str] = []

    def ok(self, msg: str) -> None:
        self.passed += 1
        print(f"  ✅ {msg}")

    def fail(self, msg: str, error: str | None = None) -> None:
        self.failed += 1
        full_msg = f"{msg}: {error}" if error else msg
        self.errors.append(full_msg)
        print(f"  ❌ {full_msg}")

    def summary(self) -> bool:
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        if self.errors:
            print("\nErrors:")
            for e in self.errors:
                print(f"  - {e}")
        return self.failed == 0


async def test_server_creation(docs_root: Path, results: TestResult) -> None:
    """Test 1: Server Creation and Tool Registration."""
    print()
    print("=" * 60)
    print("TEST 1: Server Creation")
    print("=" * 60)

    try:
        mcp = create_mcp_server(docs_root=docs_root)
        results.ok(f"Server created: {mcp.name}")

        tools = mcp._tool_manager._tools
        expected_tools = {
            "get_structure",
            "get_section",
            "get_sections_at_level",
            "search",
            "get_elements",
            "update_section",
            "insert_content",
        }

        registered = set(tools.keys())
        if expected_tools.issubset(registered):
            results.ok(f"All {len(expected_tools)} expected tools registered")
        else:
            missing = expected_tools - registered
            results.fail(f"Missing tools: {missing}")

        print(f"\n  Registered tools: {sorted(registered)}")

    except Exception as e:
        results.fail("Server creation", str(e))


async def test_get_structure(client: Client, results: TestResult) -> dict | None:
    """Test 2: get_structure tool."""
    print()
    print("=" * 60)
    print("TEST 2: get_structure")
    print("=" * 60)

    try:
        # Basic call
        result = await client.call_tool("get_structure", arguments={})
        if "sections" in result.data and "total_sections" in result.data:
            results.ok(f"Returns structure with {result.data['total_sections']} sections")
        else:
            results.fail("Missing 'sections' or 'total_sections' in response")
            return None

        # With max_depth
        result_depth = await client.call_tool("get_structure", arguments={"max_depth": 1})
        if "sections" in result_depth.data:
            results.ok("max_depth parameter works")
        else:
            results.fail("max_depth parameter failed")

        return result.data

    except Exception as e:
        results.fail("get_structure", str(e))
        return None


async def test_get_sections_at_level(client: Client, results: TestResult) -> None:
    """Test 3: get_sections_at_level tool."""
    print()
    print("=" * 60)
    print("TEST 3: get_sections_at_level")
    print("=" * 60)

    try:
        for level in [1, 2, 3]:
            result = await client.call_tool(
                "get_sections_at_level", arguments={"level": level}
            )

            if "level" not in result.data:
                results.fail(f"Level {level}: missing 'level' in response")
                continue
            if "sections" not in result.data:
                results.fail(f"Level {level}: missing 'sections' in response")
                continue
            if "count" not in result.data:
                results.fail(f"Level {level}: missing 'count' in response")
                continue

            results.ok(f"Level {level}: {result.data['count']} sections")

        # Empty level
        result = await client.call_tool(
            "get_sections_at_level", arguments={"level": 99}
        )
        if result.data["sections"] == [] and result.data["count"] == 0:
            results.ok("Empty level returns empty list")
        else:
            results.fail("Empty level should return empty list")

    except Exception as e:
        results.fail("get_sections_at_level", str(e))


async def test_get_section(
    client: Client, structure: dict | None, results: TestResult
) -> None:
    """Test 4: get_section tool."""
    print()
    print("=" * 60)
    print("TEST 4: get_section")
    print("=" * 60)

    if not structure or not structure.get("sections"):
        results.fail("No sections available for testing")
        return

    try:
        # Get first section path
        first_section = structure["sections"][0]
        path = first_section["path"]

        result = await client.call_tool("get_section", arguments={"path": path})

        if "error" in result.data:
            results.fail(f"Section '{path}'", result.data["error"])
            return

        required_fields = ["path", "title", "content", "location", "format"]
        for field in required_fields:
            if field in result.data:
                results.ok(f"Has '{field}' field")
            else:
                results.fail(f"Missing '{field}' field")

        # Test non-existent section
        result_404 = await client.call_tool(
            "get_section", arguments={"path": "nonexistent-path-xyz"}
        )
        if "error" in result_404.data:
            results.ok("Returns error for non-existent section")
        else:
            results.fail("Should return error for non-existent section")

    except Exception as e:
        results.fail("get_section", str(e))


async def test_search(client: Client, results: TestResult) -> None:
    """Test 5: search tool."""
    print()
    print("=" * 60)
    print("TEST 5: search")
    print("=" * 60)

    try:
        # Basic search
        result = await client.call_tool("search", arguments={"query": "introduction"})

        required_fields = ["query", "results", "total_results"]
        for field in required_fields:
            if field in result.data:
                results.ok(f"Has '{field}' field")
            else:
                results.fail(f"Missing '{field}' field")

        # Search with results
        if result.data["total_results"] > 0:
            results.ok(f"Found {result.data['total_results']} results for 'introduction'")
        else:
            results.ok("No results for 'introduction' (may be expected)")

        # Search with max_results
        result_limited = await client.call_tool(
            "search", arguments={"query": "a", "max_results": 2}
        )
        if len(result_limited.data["results"]) <= 2:
            results.ok("max_results parameter works")
        else:
            results.fail("max_results not respected")

        # Empty search
        result_empty = await client.call_tool(
            "search", arguments={"query": "xyznonexistent123"}
        )
        if result_empty.data["total_results"] == 0:
            results.ok("Empty search returns 0 results")
        else:
            results.fail("Unexpected results for nonsense query")

    except Exception as e:
        results.fail("search", str(e))


async def test_get_elements(client: Client, results: TestResult) -> None:
    """Test 6: get_elements tool."""
    print()
    print("=" * 60)
    print("TEST 6: get_elements")
    print("=" * 60)

    try:
        result = await client.call_tool("get_elements", arguments={})

        if "elements" in result.data and "count" in result.data:
            results.ok(f"Returns {result.data['count']} elements")
        else:
            results.fail("Missing 'elements' or 'count' in response")
            return

        # Check element structure
        if result.data["elements"]:
            elem = result.data["elements"][0]
            required_fields = ["type", "parent_section", "location"]
            for field in required_fields:
                if field in elem:
                    results.ok(f"Element has '{field}' field")
                else:
                    results.fail(f"Element missing '{field}' field")

            # Count by type
            types: dict[str, int] = {}
            for e in result.data["elements"]:
                types[e["type"]] = types.get(e["type"], 0) + 1
            print(f"\n  Elements by type: {types}")
        else:
            results.ok("No elements in docs (may be expected)")

    except Exception as e:
        results.fail("get_elements", str(e))


async def test_write_operations(results: TestResult) -> None:
    """Test 7: Write operations (update_section, insert_content)."""
    print()
    print("=" * 60)
    print("TEST 7: Write Operations (isolated)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test document
        doc_file = tmpdir / "test.adoc"
        doc_file.write_text(
            """= Test Document

== Introduction

Original content.

== Chapter One

Chapter content.
"""
        )

        try:
            mcp = create_mcp_server(docs_root=tmpdir)

            async with Client(transport=mcp) as client:
                # Test update_section
                result = await client.call_tool(
                    "update_section",
                    arguments={
                        "path": "test-document.introduction",
                        "content": "Updated content.",
                        "preserve_title": True,
                    },
                )

                if result.data.get("success"):
                    content = doc_file.read_text()
                    if "Updated content" in content:
                        results.ok("update_section works")
                    else:
                        results.fail("update_section: content not updated in file")
                else:
                    results.fail(
                        "update_section", result.data.get("error", "Unknown error")
                    )

                # Test insert_content (after)
                result = await client.call_tool(
                    "insert_content",
                    arguments={
                        "path": "test-document.introduction",
                        "position": "after",
                        "content": "== New Section\n\nInserted.\n",
                    },
                )

                if result.data.get("success"):
                    content = doc_file.read_text()
                    if "== New Section" in content:
                        results.ok("insert_content (after) works")
                    else:
                        results.fail("insert_content: content not found in file")
                else:
                    results.fail(
                        "insert_content", result.data.get("error", "Unknown error")
                    )

                # Test insert_content (before)
                result = await client.call_tool(
                    "insert_content",
                    arguments={
                        "path": "test-document.chapter-one",
                        "position": "before",
                        "content": "== Preface\n\nBefore chapter.\n",
                    },
                )

                if result.data.get("success"):
                    results.ok("insert_content (before) works")
                else:
                    results.fail(
                        "insert_content (before)",
                        result.data.get("error", "Unknown error"),
                    )

                # Test invalid position
                result = await client.call_tool(
                    "insert_content",
                    arguments={
                        "path": "test-document.introduction",
                        "position": "invalid",
                        "content": "test",
                    },
                )

                if not result.data.get("success") and "error" in result.data:
                    results.ok("Invalid position returns error")
                else:
                    results.fail("Invalid position should return error")

        except Exception as e:
            results.fail("Write operations", str(e))


async def run_all_tests(docs_root: Path) -> bool:
    """Run all manual tests."""
    print("=" * 60)
    print("MCP Documentation Server - Manual Tests")
    print("=" * 60)
    print(f"Docs Root: {docs_root}")

    results = TestResult()

    # Test 1: Server Creation
    await test_server_creation(docs_root, results)

    # Tests 2-6: Read-only operations with real docs
    try:
        mcp = create_mcp_server(docs_root=docs_root)
        async with Client(transport=mcp) as client:
            structure = await test_get_structure(client, results)
            await test_get_sections_at_level(client, results)
            await test_get_section(client, structure, results)
            await test_search(client, results)
            await test_get_elements(client, results)
    except Exception as e:
        results.fail("Client connection", str(e))

    # Test 7: Write operations (isolated)
    await test_write_operations(results)

    return results.summary()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manual test script for MCP Documentation Server"
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=Path("src/docs"),
        help="Root directory containing documentation (default: src/docs)",
    )
    args = parser.parse_args()

    docs_root = args.docs_root.resolve()
    if not docs_root.exists():
        print(f"Error: Docs root does not exist: {docs_root}")
        return 1

    success = asyncio.run(run_all_tests(docs_root))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
