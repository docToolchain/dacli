#!/usr/bin/env python3
"""Detailed bug tests for dacli MCP server."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.client import Client
from dacli.mcp_app import create_mcp_server


async def test_max_depth_behavior():
    """Test max_depth parameter behavior in detail."""
    print("\n=== Detailed max_depth Behavior Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        print("\nExpected behavior:")
        print("  max_depth=0: Should show root documents only (no children)")
        print("  max_depth=1: Should show root + their direct children")
        print("  max_depth=2: Should show root + children + grandchildren")
        print()

        for depth in [0, 1, 2, 3, -1, -5, None]:
            args = {} if depth is None else {"max_depth": depth}
            result = await client.call_tool("get_structure", arguments=args)

            def count_at_depth(sections, current_depth=0, counts=None):
                if counts is None:
                    counts = {}
                counts[current_depth] = counts.get(current_depth, 0) + len(sections)
                for s in sections:
                    if s.get("children"):
                        count_at_depth(s["children"], current_depth + 1, counts)
                return counts

            depth_counts = count_at_depth(result.data["sections"])
            max_seen_depth = max(depth_counts.keys()) if depth_counts else 0

            print(f"max_depth={depth}:")
            print(f"  Depth distribution: {depth_counts}")
            print(f"  Max visible depth: {max_seen_depth}")

            # Check if behavior is correct
            if depth == 0:
                if max_seen_depth > 0:
                    print(f"  BUG: max_depth=0 should show only root level, but shows depth {max_seen_depth}")
            elif depth == 1:
                if max_seen_depth > 1:
                    print(f"  BUG: max_depth=1 should show max depth 1, but shows depth {max_seen_depth}")
            elif depth is not None and depth < 0:
                print(f"  NOTE: Negative max_depth should probably be validated")


async def test_broken_include_detection():
    """Test if broken includes are detected properly."""
    print("\n=== Broken Include Detection Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Validate structure
        result = await client.call_tool("validate_structure", arguments={})

        print(f"Validation result: valid={result.data.get('valid')}")
        print(f"Errors: {result.data.get('errors', [])}")
        print(f"Warnings: {result.data.get('warnings', [])}")

        # Check specifically for broken_include document
        has_unresolved_include_error = any(
            'unresolved' in str(e).lower() or 'nonexistent' in str(e).lower()
            for e in result.data.get('errors', []) + result.data.get('warnings', [])
        )

        if not has_unresolved_include_error:
            print("\nPOTENTIAL BUG: broken_include.adoc contains 'include::nonexistent_file.adoc[]'")
            print("but validate_structure doesn't report this as an error or warning.")

        # Try to get content from broken_include document
        doc_result = await client.call_tool("get_section", arguments={"path": "broken_include:valid-section"})
        print(f"\nbroken_include:valid-section accessible: {'error' not in doc_result.data}")


async def test_circular_include_detection():
    """Test if circular includes are detected properly."""
    print("\n=== Circular Include Detection Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        result = await client.call_tool("validate_structure", arguments={})

        has_circular_error = any(
            'circular' in str(e).lower()
            for e in result.data.get('errors', []) + result.data.get('warnings', [])
        )

        print(f"Circular include detected: {has_circular_error}")

        if not has_circular_error:
            print("NOTE: circular_a.adoc and circular_b.adoc include each other.")
            print("They appear as orphaned files, but no circular include warning.")


async def test_negative_parameter_validation():
    """Test that negative parameters are validated."""
    print("\n=== Negative Parameter Validation Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        tests = [
            ("search", {"query": "test", "max_results": -5}),
            ("get_structure", {"max_depth": -1}),
            ("get_sections_at_level", {"level": -1}),
            ("get_elements", {"include_content": True, "content_limit": -10}),
        ]

        for tool_name, args in tests:
            try:
                result = await client.call_tool(tool_name, arguments=args)
                # If we get here, no validation error was raised
                print(f"{tool_name}({args}): No validation error raised")

                # Check if the result makes sense
                if tool_name == "search" and "results" in result.data:
                    if len(result.data["results"]) > 0:
                        print(f"  BUG: Returned {len(result.data['results'])} results with negative max_results")
                elif tool_name == "get_structure" and "sections" in result.data:
                    print(f"  Returns {len(result.data['sections'])} root sections (behavior undefined)")
                elif tool_name == "get_sections_at_level":
                    print(f"  Returns count={result.data.get('count', 'N/A')}")

            except Exception as e:
                print(f"{tool_name}({args}): Raised {type(e).__name__} (expected for validation)")


async def test_update_and_insert_with_special_content():
    """Test update and insert with special content."""
    print("\n=== Update/Insert Special Content Test ===")

    docs_root = Path(__file__).parent

    # Create a test file
    test_file = docs_root / "special_update_test.adoc"
    test_file.write_text("""= Special Update Test

== Test Section

Original content.
""", encoding="utf-8")

    try:
        mcp = create_mcp_server(docs_root=docs_root)
        async with Client(transport=mcp) as client:
            # Test updating with content containing special characters
            special_contents = [
                "Content with <HTML> tags",
                "Content with 'quotes' and \"double quotes\"",
                "Content with\nnewlines\nand more newlines",
                "Content with\ttabs",
                "Content with unicode: foo bar baz",
                "= Content starting with equals (looks like heading)",
                "include::fake.adoc[]",  # Include directive in content
                "----\ncode block\n----",
                "",  # Empty content
            ]

            for content in special_contents:
                try:
                    result = await client.call_tool("update_section", arguments={
                        "path": "special_update_test:test-section",
                        "content": content,
                        "preserve_title": True
                    })
                    success = result.data.get("success", False)
                    print(f"Update with '{repr(content)[:40]}...': {'SUCCESS' if success else 'FAILED'}")
                    if not success:
                        print(f"  Error: {result.data.get('error', 'unknown')}")
                except Exception as e:
                    print(f"Update with '{repr(content)[:40]}...': EXCEPTION - {e}")
    finally:
        test_file.unlink(missing_ok=True)


async def test_concurrent_operations():
    """Test concurrent read operations."""
    print("\n=== Concurrent Operations Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Run multiple operations concurrently
        tasks = [
            client.call_tool("get_structure", arguments={}),
            client.call_tool("search", arguments={"query": "test"}),
            client.call_tool("get_elements", arguments={}),
            client.call_tool("get_metadata", arguments={}),
            client.call_tool("validate_structure", arguments={}),
        ]

        try:
            results = await asyncio.gather(*tasks)
            print(f"Concurrent operations: {len(results)} completed successfully")
            for i, r in enumerate(results):
                print(f"  Task {i}: {list(r.data.keys())[:3]}...")
        except Exception as e:
            print(f"Concurrent operations failed: {e}")


async def test_very_long_section_titles():
    """Test handling of very long section titles."""
    print("\n=== Very Long Section Titles Test ===")

    docs_root = Path(__file__).parent

    # Create a file with very long section title
    test_file = docs_root / "long_title_test.adoc"
    long_title = "A" * 500
    test_file.write_text(f"""= Long Title Test

== {long_title}

Content under very long title.
""", encoding="utf-8")

    try:
        mcp = create_mcp_server(docs_root=docs_root)
        async with Client(transport=mcp) as client:
            result = await client.call_tool("get_structure", arguments={})

            # Find the long title section
            def find_section(sections, partial_title):
                for s in sections:
                    if partial_title.lower() in s["title"].lower():
                        return s
                    if s.get("children"):
                        found = find_section(s["children"], partial_title)
                        if found:
                            return found
                return None

            long_section = find_section(result.data["sections"], "AAAA")
            if long_section:
                print(f"Long title section found")
                print(f"  Title length: {len(long_section['title'])}")
                print(f"  Path length: {len(long_section['path'])}")
                print(f"  Path: {long_section['path'][:100]}...")

                # Try to access it
                access_result = await client.call_tool("get_section", arguments={"path": long_section["path"]})
                print(f"  Accessible: {'error' not in access_result.data}")
            else:
                print("Long title section not found in structure")
    finally:
        test_file.unlink(missing_ok=True)


async def test_unicode_in_paths():
    """Test Unicode characters in file names and section paths."""
    print("\n=== Unicode in Paths Test ===")

    docs_root = Path(__file__).parent

    # Create a file with Unicode in name
    test_file = docs_root / "test_unicode_cafe.adoc"
    test_file.write_text("""= Unicode Cafe Document

== Cafe Section

Content with cafe.
""", encoding="utf-8")

    try:
        mcp = create_mcp_server(docs_root=docs_root)
        async with Client(transport=mcp) as client:
            result = await client.call_tool("get_structure", arguments={})

            # Find the unicode document
            def find_doc(sections, partial):
                for s in sections:
                    if partial in s["path"]:
                        return s
                    if s.get("children"):
                        found = find_doc(s["children"], partial)
                        if found:
                            return found
                return None

            unicode_doc = find_doc(result.data["sections"], "cafe")
            if unicode_doc:
                print(f"Unicode document found: {unicode_doc['path']}")
                print(f"Title: {unicode_doc['title']}")

                # Try to access
                access_result = await client.call_tool("get_section", arguments={"path": unicode_doc["path"]})
                print(f"Accessible: {'error' not in access_result.data}")
            else:
                print("Unicode document not found - checking all paths:")
                for s in result.data["sections"]:
                    if "unicode" in s["path"].lower() or "cafe" in s["path"].lower():
                        print(f"  Found: {s['path']}")
    finally:
        test_file.unlink(missing_ok=True)


async def test_empty_document():
    """Test handling of empty documents."""
    print("\n=== Empty Document Test ===")

    docs_root = Path(__file__).parent

    # Create an empty file
    test_file = docs_root / "empty_document.adoc"
    test_file.write_text("", encoding="utf-8")

    try:
        mcp = create_mcp_server(docs_root=docs_root)
        async with Client(transport=mcp) as client:
            result = await client.call_tool("get_structure", arguments={})

            # Check if empty document appears
            has_empty = any("empty_document" in s["path"] for s in result.data["sections"])
            print(f"Empty document in structure: {has_empty}")

            if has_empty:
                # Try to access it
                access_result = await client.call_tool("get_section", arguments={"path": "empty_document"})
                print(f"Empty document accessible: {'error' not in access_result.data}")
                if "content" in access_result.data:
                    print(f"Content: '{access_result.data['content']}'")
    finally:
        test_file.unlink(missing_ok=True)


async def test_document_without_title():
    """Test handling of documents without a title."""
    print("\n=== Document Without Title Test ===")

    docs_root = Path(__file__).parent

    # Create a file without title
    test_file = docs_root / "no_title_doc.adoc"
    test_file.write_text("""== Just a Section

Content without document title.
""", encoding="utf-8")

    try:
        mcp = create_mcp_server(docs_root=docs_root)
        async with Client(transport=mcp) as client:
            result = await client.call_tool("get_structure", arguments={})

            # Check for the document
            no_title_docs = [s for s in result.data["sections"] if "no_title" in s["path"]]
            print(f"Documents without title found: {len(no_title_docs)}")
            for doc in no_title_docs:
                print(f"  Path: {doc['path']}, Title: '{doc['title']}'")
    finally:
        test_file.unlink(missing_ok=True)


async def main():
    """Run all detailed bug tests."""
    print("=" * 70)
    print("DETAILED BUG TESTS FOR DACLI MCP SERVER")
    print("=" * 70)

    await test_max_depth_behavior()
    await test_broken_include_detection()
    await test_circular_include_detection()
    await test_negative_parameter_validation()
    await test_update_and_insert_with_special_content()
    await test_concurrent_operations()
    await test_very_long_section_titles()
    await test_unicode_in_paths()
    await test_empty_document()
    await test_document_without_title()


if __name__ == "__main__":
    asyncio.run(main())
