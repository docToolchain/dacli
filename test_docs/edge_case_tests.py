#!/usr/bin/env python3
"""Edge case tests for dacli MCP server to find bugs."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.client import Client
from dacli.mcp_app import create_mcp_server


async def test_path_consistency():
    """Test path format consistency between AsciiDoc and Markdown."""
    print("\n=== Path Consistency Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Get all section paths
        structure = await client.call_tool("get_structure", arguments={})

        def extract_paths(sections, paths=None):
            if paths is None:
                paths = []
            for s in sections:
                paths.append(s["path"])
                if s.get("children"):
                    extract_paths(s["children"], paths)
            return paths

        all_paths = extract_paths(structure.data["sections"])

        # Check for underscore vs dash inconsistency
        underscore_paths = [p for p in all_paths if "_" in p]
        dash_paths = [p for p in all_paths if "-" in p.split(":")[0]]  # In document name part

        print(f"Total paths: {len(all_paths)}")
        print(f"Paths with underscores: {len(underscore_paths)}")
        print(f"Paths with dashes in document name: {len(dash_paths)}")

        print("\nPaths with underscores (potential inconsistency):")
        for p in underscore_paths[:10]:
            print(f"  {p}")

        print("\nPaths with dashes in document name:")
        for p in dash_paths[:10]:
            print(f"  {p}")


async def test_markdown_paths():
    """Test Markdown file path handling."""
    print("\n=== Markdown Path Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Try different path formats for markdown
        test_paths = [
            "markdown_test:introduction",  # underscore (as generated)
            "markdown-test:introduction",  # dash (would be expected from asciidoc pattern)
            "markdown_test",               # just the document
            "markdown-test",               # just the document with dash
        ]

        for path in test_paths:
            result = await client.call_tool("get_section", arguments={"path": path})
            found = "error" not in result.data
            print(f"Path '{path}': {'FOUND' if found else 'NOT FOUND'}")
            if not found and "suggestions" in result.data.get("error", {}).get("details", {}):
                print(f"  Suggestions: {result.data['error']['details']['suggestions'][:3]}")


async def test_negative_parameters():
    """Test negative parameter handling."""
    print("\n=== Negative Parameter Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Test negative max_depth
        result = await client.call_tool("get_structure", arguments={"max_depth": -1})
        print(f"get_structure(max_depth=-1): sections returned = {len(result.data.get('sections', []))}")

        # Test negative level
        result = await client.call_tool("get_sections_at_level", arguments={"level": -1})
        print(f"get_sections_at_level(level=-1): count = {result.data.get('count', 'ERROR')}")

        # Test negative max_results
        result = await client.call_tool("search", arguments={"query": "test", "max_results": -5})
        print(f"search(max_results=-5): results = {len(result.data.get('results', []))}")

        # Test negative content_limit
        result = await client.call_tool("get_elements", arguments={"include_content": True, "content_limit": -10})
        print(f"get_elements(content_limit=-10): count = {result.data.get('count', 'ERROR')}")


async def test_special_characters_in_sections():
    """Test handling of special characters in section titles."""
    print("\n=== Special Characters Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Get all sections to see how special chars are handled
        result = await client.call_tool("get_sections_at_level", arguments={"level": 1})

        special_sections = []
        for s in result.data.get("sections", []):
            title = s.get("title", "")
            path = s.get("path", "")
            if any(c in title for c in ['<', '>', '&', '"', "'", '/', '\\']):
                special_sections.append((title, path))

        print(f"Sections with special chars in title:")
        for title, path in special_sections:
            print(f"  Title: '{title}' -> Path: '{path}'")

            # Try to access each
            get_result = await client.call_tool("get_section", arguments={"path": path})
            accessible = "error" not in get_result.data
            print(f"    Accessible: {accessible}")


async def test_duplicate_section_handling():
    """Test how duplicate section names are handled."""
    print("\n=== Duplicate Section Handling Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Search for "Introduction" which appears multiple times
        search_result = await client.call_tool("search", arguments={"query": "Introduction"})

        intro_paths = [r["path"] for r in search_result.data.get("results", [])]
        print(f"Found {len(intro_paths)} sections matching 'Introduction':")
        for p in intro_paths:
            print(f"  {p}")

        # Check duplicate_sections document specifically
        result = await client.call_tool("get_structure", arguments={})

        def find_duplicate_paths(sections, doc_name="duplicate_sections"):
            paths = []
            for s in sections:
                if s["path"].startswith(doc_name):
                    paths.append((s["path"], s["title"]))
                if s.get("children"):
                    paths.extend(find_duplicate_paths(s["children"], doc_name))
            return paths

        dup_paths = find_duplicate_paths(result.data["sections"])
        print(f"\nAll paths in duplicate_sections document:")
        for path, title in dup_paths:
            print(f"  {path} -> {title}")


async def test_empty_and_whitespace():
    """Test handling of empty and whitespace content."""
    print("\n=== Empty/Whitespace Content Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Get empty section content
        result = await client.call_tool("get_section", arguments={"path": "empty_sections:empty-section"})
        if "error" not in result.data:
            content = result.data.get("content", "")
            print(f"Empty section content: repr='{repr(content)}'")
            print(f"  Length: {len(content)}")
            print(f"  Is only whitespace: {content.strip() == ''}")
        else:
            print(f"Error getting empty section: {result.data['error']}")

        # Try section with only whitespace
        result2 = await client.call_tool("get_section", arguments={"path": "empty_sections:section-with-only-whitespace"})
        if "error" not in result2.data:
            content = result2.data.get("content", "")
            print(f"\nWhitespace section content: repr='{repr(content[:100])}'")
        else:
            print(f"Error getting whitespace section: {result2.data['error']}")


async def test_deep_nesting_access():
    """Test access to deeply nested sections."""
    print("\n=== Deep Nesting Access Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Get structure of deep_nesting document
        result = await client.call_tool("get_structure", arguments={})

        def find_deepest(sections, depth=0, max_depth=0, deepest_path=""):
            for s in sections:
                current_depth = depth + 1
                if current_depth > max_depth:
                    max_depth = current_depth
                    deepest_path = s["path"]
                if s.get("children"):
                    max_depth, deepest_path = find_deepest(s["children"], current_depth, max_depth, deepest_path)
            return max_depth, deepest_path

        max_depth, deepest_path = find_deepest(result.data["sections"])
        print(f"Maximum nesting depth: {max_depth}")
        print(f"Deepest path: {deepest_path}")

        # Try to access deepest section
        deep_result = await client.call_tool("get_section", arguments={"path": deepest_path})
        if "error" not in deep_result.data:
            print(f"Successfully accessed deepest section")
            print(f"Title: {deep_result.data.get('title', 'N/A')}")
        else:
            print(f"Error accessing deepest section: {deep_result.data['error']}")


async def test_include_file_detection():
    """Test that included files are not parsed as separate documents."""
    print("\n=== Include File Detection Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        result = await client.call_tool("get_structure", arguments={})

        all_docs = [s["path"] for s in result.data["sections"] if s["level"] == 0]

        print(f"Root-level documents found: {len(all_docs)}")
        for doc in all_docs:
            print(f"  {doc}")

        # Check if included_part is parsed as separate document
        included_as_separate = "included_part" in all_docs or "included-part" in all_docs
        print(f"\nIncluded file parsed as separate document: {included_as_separate}")

        if not included_as_separate:
            print("PASS: Include detection working correctly")
        else:
            print("POTENTIAL BUG: Included file should not be a separate root document")


async def test_broken_include_handling():
    """Test handling of broken (non-existent) includes."""
    print("\n=== Broken Include Handling Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        # Validate structure should report broken includes
        result = await client.call_tool("validate_structure", arguments={})

        print(f"Validation result: valid={result.data.get('valid')}")
        print(f"Errors: {result.data.get('errors', [])}")
        print(f"Warnings: {result.data.get('warnings', [])}")

        # Check if broken_include document is still accessible
        doc_result = await client.call_tool("get_section", arguments={"path": "broken_include"})
        accessible = "error" not in doc_result.data
        print(f"\nDocument with broken include accessible: {accessible}")


async def test_max_depth_boundary():
    """Test max_depth boundary conditions."""
    print("\n=== Max Depth Boundary Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        for depth in [0, 1, 2, 3, None]:
            args = {} if depth is None else {"max_depth": depth}
            result = await client.call_tool("get_structure", arguments=args)

            def count_total_children(sections):
                count = 0
                for s in sections:
                    children = s.get("children", [])
                    count += len(children)
                    count += count_total_children(children)
                return count

            child_count = count_total_children(result.data["sections"])
            print(f"max_depth={depth}: total_sections={result.data['total_sections']}, tree_children={child_count}")


async def test_search_edge_cases():
    """Test search edge cases."""
    print("\n=== Search Edge Cases Test ===")

    docs_root = Path(__file__).parent
    mcp = create_mcp_server(docs_root=docs_root)

    async with Client(transport=mcp) as client:
        test_queries = [
            "a",                    # Single character
            "aa" * 100,             # Very long query
            "test\nwith\nnewlines", # Query with newlines
            "test\twith\ttabs",     # Query with tabs
            "test with   multiple   spaces",
            "*",                    # Regex-like
            ".*",                   # Regex pattern
            "[test]",               # Brackets
            "(test)",               # Parentheses
            "test?",                # Question mark
            "test+",                # Plus
        ]

        for query in test_queries:
            try:
                result = await client.call_tool("search", arguments={"query": query})
                count = result.data.get("total_results", 0)
                print(f"Query '{repr(query)[:30]}': {count} results")
            except Exception as e:
                print(f"Query '{repr(query)[:30]}': EXCEPTION - {type(e).__name__}: {str(e)[:50]}")


async def main():
    """Run all edge case tests."""
    print("=" * 70)
    print("EDGE CASE TESTS FOR DACLI MCP SERVER")
    print("=" * 70)

    await test_path_consistency()
    await test_markdown_paths()
    await test_negative_parameters()
    await test_special_characters_in_sections()
    await test_duplicate_section_handling()
    await test_empty_and_whitespace()
    await test_deep_nesting_access()
    await test_include_file_detection()
    await test_broken_include_handling()
    await test_max_depth_boundary()
    await test_search_edge_cases()


if __name__ == "__main__":
    asyncio.run(main())
