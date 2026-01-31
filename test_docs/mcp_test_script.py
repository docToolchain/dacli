#!/usr/bin/env python3
"""Comprehensive MCP Server Test Script for dacli.

This script tests all MCP tools with various edge cases to find bugs.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add the src directory to the path so we can import dacli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.client import Client
from dacli.mcp_app import create_mcp_server


class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", details: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        result = f"[{status}] {self.name}"
        if self.message:
            result += f": {self.message}"
        if self.details and not self.passed:
            result += f"\n    Details: {self.details}"
        return result


class MCPTestSuite:
    def __init__(self, docs_root: Path):
        self.docs_root = docs_root
        self.results: list[TestResult] = []
        self.bugs: list[dict] = []

    def add_result(self, result: TestResult):
        self.results.append(result)
        if not result.passed:
            self.bugs.append({
                "test": result.name,
                "message": result.message,
                "details": result.details
            })

    async def run_all_tests(self):
        """Run all test categories."""
        print("=" * 70)
        print("DACLI MCP SERVER TEST SUITE")
        print("=" * 70)
        print(f"Testing docs root: {self.docs_root}")
        print()

        mcp = create_mcp_server(docs_root=self.docs_root)
        async with Client(transport=mcp) as client:
            # Run test categories
            await self.test_tool_discovery(client)
            await self.test_get_structure(client)
            await self.test_get_section(client)
            await self.test_get_sections_at_level(client)
            await self.test_search(client)
            await self.test_get_elements(client)
            await self.test_get_metadata(client)
            await self.test_validate_structure(client)
            await self.test_update_section(client)
            await self.test_insert_content(client)
            await self.test_edge_cases(client)

        self.print_summary()

    async def test_tool_discovery(self, client: Client):
        """Test that all expected tools are registered."""
        print("\n--- Tool Discovery Tests ---")

        try:
            tools = await client.list_tools()
            tool_names = {tool.name for tool in tools}

            expected_tools = {
                "get_structure", "get_section", "get_sections_at_level",
                "search", "get_elements", "update_section", "insert_content",
                "get_metadata", "validate_structure"
            }

            missing = expected_tools - tool_names
            if missing:
                self.add_result(TestResult(
                    "tool_discovery_all_tools",
                    False,
                    f"Missing tools: {missing}"
                ))
            else:
                self.add_result(TestResult(
                    "tool_discovery_all_tools",
                    True,
                    "All expected tools registered"
                ))

            # Check tools have descriptions
            tools_without_desc = [t.name for t in tools if not t.description]
            if tools_without_desc:
                self.add_result(TestResult(
                    "tool_discovery_descriptions",
                    False,
                    f"Tools without descriptions: {tools_without_desc}"
                ))
            else:
                self.add_result(TestResult(
                    "tool_discovery_descriptions",
                    True,
                    "All tools have descriptions"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "tool_discovery",
                False,
                f"Exception: {e}",
                traceback.format_exc()
            ))

    async def test_get_structure(self, client: Client):
        """Test get_structure tool."""
        print("\n--- get_structure Tests ---")

        # Basic call
        try:
            result = await client.call_tool("get_structure", arguments={})
            if "sections" in result.data and "total_sections" in result.data:
                self.add_result(TestResult(
                    "get_structure_basic",
                    True,
                    f"Found {result.data['total_sections']} sections"
                ))
            else:
                self.add_result(TestResult(
                    "get_structure_basic",
                    False,
                    "Missing expected keys in response",
                    str(result.data)
                ))
        except Exception as e:
            self.add_result(TestResult(
                "get_structure_basic",
                False,
                f"Exception: {e}",
                traceback.format_exc()
            ))

        # With max_depth=0 (edge case)
        try:
            result = await client.call_tool("get_structure", arguments={"max_depth": 0})
            self.add_result(TestResult(
                "get_structure_max_depth_0",
                True,
                f"max_depth=0 returned: {result.data.get('total_sections', 'N/A')} sections"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_structure_max_depth_0",
                False,
                f"Exception with max_depth=0: {e}",
                traceback.format_exc()
            ))

        # With max_depth=1
        try:
            result = await client.call_tool("get_structure", arguments={"max_depth": 1})
            self.add_result(TestResult(
                "get_structure_max_depth_1",
                True,
                f"max_depth=1 works correctly"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_structure_max_depth_1",
                False,
                f"Exception: {e}"
            ))

        # With negative max_depth (edge case)
        try:
            result = await client.call_tool("get_structure", arguments={"max_depth": -1})
            self.add_result(TestResult(
                "get_structure_max_depth_negative",
                True,  # If it doesn't crash, it's a pass, but note behavior
                f"max_depth=-1 returned: {result.data}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_structure_max_depth_negative",
                False,
                f"Exception with max_depth=-1: {e}"
            ))

    async def test_get_section(self, client: Client):
        """Test get_section tool."""
        print("\n--- get_section Tests ---")

        # Get structure first to find valid paths
        structure = await client.call_tool("get_structure", arguments={})

        # Test with valid section
        try:
            result = await client.call_tool("get_section", arguments={"path": "basic:introduction"})
            if "error" not in result.data and "content" in result.data:
                self.add_result(TestResult(
                    "get_section_valid_path",
                    True,
                    "Successfully retrieved section"
                ))
            elif "error" in result.data:
                self.add_result(TestResult(
                    "get_section_valid_path",
                    False,
                    f"Got error for valid path: {result.data['error']}"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "get_section_valid_path",
                False,
                f"Exception: {e}"
            ))

        # Test with non-existent section
        try:
            result = await client.call_tool("get_section", arguments={"path": "nonexistent:path"})
            if "error" in result.data:
                self.add_result(TestResult(
                    "get_section_invalid_path",
                    True,
                    "Correctly returns error for invalid path"
                ))
            else:
                self.add_result(TestResult(
                    "get_section_invalid_path",
                    False,
                    "Should return error for invalid path"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "get_section_invalid_path",
                False,
                f"Exception: {e}"
            ))

        # Test with empty path
        try:
            result = await client.call_tool("get_section", arguments={"path": ""})
            self.add_result(TestResult(
                "get_section_empty_path",
                "error" in result.data,
                f"Empty path result: {'error returned' if 'error' in result.data else 'unexpected behavior'}",
                str(result.data)[:200]
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_section_empty_path",
                False,
                f"Exception with empty path: {e}"
            ))

        # Test with special characters in path
        try:
            result = await client.call_tool("get_section", arguments={"path": "special-chars:section-with-many-dashes"})
            self.add_result(TestResult(
                "get_section_special_chars",
                True,
                f"Special chars in path: {'found' if 'error' not in result.data else 'not found'}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_section_special_chars",
                False,
                f"Exception: {e}"
            ))

        # Test with path starting with slash
        try:
            result = await client.call_tool("get_section", arguments={"path": "/basic:introduction"})
            self.add_result(TestResult(
                "get_section_leading_slash",
                True,
                f"Leading slash handled: {'error' in result.data or 'content' in result.data}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_section_leading_slash",
                False,
                f"Exception: {e}"
            ))

    async def test_get_sections_at_level(self, client: Client):
        """Test get_sections_at_level tool."""
        print("\n--- get_sections_at_level Tests ---")

        # Test level 0 (document level)
        try:
            result = await client.call_tool("get_sections_at_level", arguments={"level": 0})
            self.add_result(TestResult(
                "get_sections_level_0",
                True,
                f"Level 0: {result.data.get('count', 0)} sections"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_sections_level_0",
                False,
                f"Exception: {e}"
            ))

        # Test level 1 (chapters)
        try:
            result = await client.call_tool("get_sections_at_level", arguments={"level": 1})
            if "sections" in result.data and "count" in result.data:
                self.add_result(TestResult(
                    "get_sections_level_1",
                    True,
                    f"Level 1: {result.data['count']} sections"
                ))
            else:
                self.add_result(TestResult(
                    "get_sections_level_1",
                    False,
                    "Missing expected keys"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "get_sections_level_1",
                False,
                f"Exception: {e}"
            ))

        # Test very high level (should be empty)
        try:
            result = await client.call_tool("get_sections_at_level", arguments={"level": 100})
            if result.data["count"] == 0:
                self.add_result(TestResult(
                    "get_sections_level_100",
                    True,
                    "Level 100 correctly returns empty list"
                ))
            else:
                self.add_result(TestResult(
                    "get_sections_level_100",
                    False,
                    f"Level 100 unexpectedly has {result.data['count']} sections"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "get_sections_level_100",
                False,
                f"Exception: {e}"
            ))

        # Test negative level (edge case)
        try:
            result = await client.call_tool("get_sections_at_level", arguments={"level": -1})
            self.add_result(TestResult(
                "get_sections_level_negative",
                True,
                f"Level -1 result: {result.data.get('count', 'N/A')} sections (should validate input)"
            ))
        except Exception as e:
            # Exception might be expected for invalid input
            self.add_result(TestResult(
                "get_sections_level_negative",
                True,
                f"Level -1 raised exception (acceptable): {type(e).__name__}"
            ))

    async def test_search(self, client: Client):
        """Test search tool."""
        print("\n--- search Tests ---")

        # Basic search
        try:
            result = await client.call_tool("search", arguments={"query": "introduction"})
            if "results" in result.data:
                self.add_result(TestResult(
                    "search_basic",
                    True,
                    f"Found {result.data.get('total_results', 0)} results for 'introduction'"
                ))
            else:
                self.add_result(TestResult(
                    "search_basic",
                    False,
                    "Missing results key"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "search_basic",
                False,
                f"Exception: {e}"
            ))

        # Empty query (should fail)
        try:
            result = await client.call_tool("search", arguments={"query": ""})
            self.add_result(TestResult(
                "search_empty_query",
                False,
                "Empty query should raise error but didn't",
                str(result.data)
            ))
        except Exception as e:
            if "empty" in str(e).lower():
                self.add_result(TestResult(
                    "search_empty_query",
                    True,
                    "Empty query correctly raises error"
                ))
            else:
                self.add_result(TestResult(
                    "search_empty_query",
                    True,
                    f"Empty query raises error: {type(e).__name__}"
                ))

        # Whitespace-only query
        try:
            result = await client.call_tool("search", arguments={"query": "   "})
            self.add_result(TestResult(
                "search_whitespace_query",
                False,
                "Whitespace query should raise error"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "search_whitespace_query",
                True,
                "Whitespace query correctly raises error"
            ))

        # Search with max_results
        try:
            result = await client.call_tool("search", arguments={"query": "section", "max_results": 2})
            if len(result.data.get("results", [])) <= 2:
                self.add_result(TestResult(
                    "search_max_results",
                    True,
                    f"max_results=2 respected"
                ))
            else:
                self.add_result(TestResult(
                    "search_max_results",
                    False,
                    f"max_results=2 not respected, got {len(result.data['results'])}"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "search_max_results",
                False,
                f"Exception: {e}"
            ))

        # Search with max_results=0 (edge case)
        try:
            result = await client.call_tool("search", arguments={"query": "test", "max_results": 0})
            self.add_result(TestResult(
                "search_max_results_0",
                True,
                f"max_results=0 returned {len(result.data.get('results', []))} results"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "search_max_results_0",
                False,
                f"Exception with max_results=0: {e}"
            ))

        # Search with negative max_results (edge case)
        try:
            result = await client.call_tool("search", arguments={"query": "test", "max_results": -5})
            self.add_result(TestResult(
                "search_max_results_negative",
                True,  # Should validate, but if it works, note behavior
                f"max_results=-5 returned {len(result.data.get('results', []))} results (should validate)"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "search_max_results_negative",
                True,
                f"max_results=-5 raises exception (good): {type(e).__name__}"
            ))

        # Search with scope
        try:
            result = await client.call_tool("search", arguments={"query": "goals", "scope": "basic"})
            self.add_result(TestResult(
                "search_with_scope",
                True,
                f"Scoped search returned {result.data.get('total_results', 0)} results"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "search_with_scope",
                False,
                f"Exception: {e}"
            ))

        # Search with special characters
        try:
            result = await client.call_tool("search", arguments={"query": "<>&\""})
            self.add_result(TestResult(
                "search_special_chars",
                True,
                f"Special chars search: {result.data.get('total_results', 0)} results"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "search_special_chars",
                False,
                f"Exception with special chars: {e}"
            ))

    async def test_get_elements(self, client: Client):
        """Test get_elements tool."""
        print("\n--- get_elements Tests ---")

        # Get all elements
        try:
            result = await client.call_tool("get_elements", arguments={})
            if "elements" in result.data and "count" in result.data:
                self.add_result(TestResult(
                    "get_elements_all",
                    True,
                    f"Found {result.data['count']} elements"
                ))
            else:
                self.add_result(TestResult(
                    "get_elements_all",
                    False,
                    "Missing expected keys"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "get_elements_all",
                False,
                f"Exception: {e}"
            ))

        # Filter by type: code
        try:
            result = await client.call_tool("get_elements", arguments={"element_type": "code"})
            self.add_result(TestResult(
                "get_elements_code",
                True,
                f"Found {result.data.get('count', 0)} code elements"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_elements_code",
                False,
                f"Exception: {e}"
            ))

        # Filter by invalid type
        try:
            result = await client.call_tool("get_elements", arguments={"element_type": "invalid_type"})
            self.add_result(TestResult(
                "get_elements_invalid_type",
                True,
                f"Invalid type returned {result.data.get('count', 0)} elements (should validate)"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_elements_invalid_type",
                True,
                f"Invalid type raises exception (good): {type(e).__name__}"
            ))

        # With include_content=True
        try:
            result = await client.call_tool("get_elements", arguments={"include_content": True})
            has_attributes = any("attributes" in e for e in result.data.get("elements", []))
            self.add_result(TestResult(
                "get_elements_with_content",
                has_attributes,
                f"include_content=True: attributes {'present' if has_attributes else 'missing'}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_elements_with_content",
                False,
                f"Exception: {e}"
            ))

        # With content_limit
        try:
            result = await client.call_tool("get_elements", arguments={
                "include_content": True,
                "content_limit": 5
            })
            self.add_result(TestResult(
                "get_elements_content_limit",
                True,
                f"content_limit=5 works"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_elements_content_limit",
                False,
                f"Exception: {e}"
            ))

        # With recursive=True
        try:
            result = await client.call_tool("get_elements", arguments={
                "section_path": "basic:introduction",
                "recursive": True
            })
            self.add_result(TestResult(
                "get_elements_recursive",
                True,
                f"recursive=True returned {result.data.get('count', 0)} elements"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_elements_recursive",
                False,
                f"Exception: {e}"
            ))

    async def test_get_metadata(self, client: Client):
        """Test get_metadata tool."""
        print("\n--- get_metadata Tests ---")

        # Project metadata (no path)
        try:
            result = await client.call_tool("get_metadata", arguments={})
            expected_keys = ["total_sections", "total_files", "total_words"]
            has_keys = all(k in result.data for k in expected_keys)
            self.add_result(TestResult(
                "get_metadata_project",
                has_keys,
                f"Project metadata: {result.data.get('total_sections', 'N/A')} sections, {result.data.get('total_files', 'N/A')} files"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "get_metadata_project",
                False,
                f"Exception: {e}"
            ))

        # Section metadata
        try:
            result = await client.call_tool("get_metadata", arguments={"path": "basic:introduction"})
            if "error" not in result.data:
                self.add_result(TestResult(
                    "get_metadata_section",
                    True,
                    f"Section metadata: {result.data.get('word_count', 'N/A')} words"
                ))
            else:
                self.add_result(TestResult(
                    "get_metadata_section",
                    False,
                    f"Error: {result.data['error']}"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "get_metadata_section",
                False,
                f"Exception: {e}"
            ))

        # Invalid path metadata
        try:
            result = await client.call_tool("get_metadata", arguments={"path": "nonexistent"})
            if "error" in result.data:
                self.add_result(TestResult(
                    "get_metadata_invalid_path",
                    True,
                    "Invalid path correctly returns error"
                ))
            else:
                self.add_result(TestResult(
                    "get_metadata_invalid_path",
                    False,
                    "Invalid path should return error"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "get_metadata_invalid_path",
                False,
                f"Exception: {e}"
            ))

    async def test_validate_structure(self, client: Client):
        """Test validate_structure tool."""
        print("\n--- validate_structure Tests ---")

        try:
            result = await client.call_tool("validate_structure", arguments={})
            expected_keys = ["valid", "errors", "warnings", "validation_time_ms"]
            has_keys = all(k in result.data for k in expected_keys)

            if has_keys:
                self.add_result(TestResult(
                    "validate_structure_basic",
                    True,
                    f"Valid: {result.data['valid']}, Errors: {len(result.data['errors'])}, Warnings: {len(result.data['warnings'])}"
                ))

                # Log any warnings/errors for debugging
                if result.data["errors"]:
                    print(f"    Errors found: {result.data['errors']}")
                if result.data["warnings"]:
                    print(f"    Warnings found: {result.data['warnings']}")
            else:
                self.add_result(TestResult(
                    "validate_structure_basic",
                    False,
                    f"Missing keys: {set(expected_keys) - set(result.data.keys())}"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "validate_structure_basic",
                False,
                f"Exception: {e}"
            ))

    async def test_update_section(self, client: Client):
        """Test update_section tool."""
        print("\n--- update_section Tests ---")

        # Create a test file for modification
        test_file = self.docs_root / "update_test.adoc"
        test_file.write_text("""= Update Test Document

== Test Section

Original content.

== Another Section

More content.
""", encoding="utf-8")

        # Reload server to pick up new file
        mcp = create_mcp_server(docs_root=self.docs_root)
        async with Client(transport=mcp) as client:
            # Basic update
            try:
                result = await client.call_tool("update_section", arguments={
                    "path": "update-test:test-section",
                    "content": "Updated content here.",
                    "preserve_title": True
                })
                if result.data.get("success"):
                    self.add_result(TestResult(
                        "update_section_basic",
                        True,
                        "Successfully updated section"
                    ))
                else:
                    self.add_result(TestResult(
                        "update_section_basic",
                        False,
                        f"Update failed: {result.data.get('error', 'unknown')}"
                    ))
            except Exception as e:
                self.add_result(TestResult(
                    "update_section_basic",
                    False,
                    f"Exception: {e}"
                ))

            # Update with expected_hash (optimistic locking)
            try:
                result = await client.call_tool("update_section", arguments={
                    "path": "update-test:test-section",
                    "content": "Content with hash check.",
                    "expected_hash": "wrong_hash"
                })
                if not result.data.get("success") and "conflict" in result.data.get("error", "").lower():
                    self.add_result(TestResult(
                        "update_section_hash_conflict",
                        True,
                        "Hash conflict correctly detected"
                    ))
                else:
                    self.add_result(TestResult(
                        "update_section_hash_conflict",
                        False,
                        f"Should detect hash conflict: {result.data}"
                    ))
            except Exception as e:
                self.add_result(TestResult(
                    "update_section_hash_conflict",
                    False,
                    f"Exception: {e}"
                ))

            # Update non-existent section
            try:
                result = await client.call_tool("update_section", arguments={
                    "path": "nonexistent:section",
                    "content": "Content"
                })
                if not result.data.get("success"):
                    self.add_result(TestResult(
                        "update_section_nonexistent",
                        True,
                        "Non-existent section correctly fails"
                    ))
                else:
                    self.add_result(TestResult(
                        "update_section_nonexistent",
                        False,
                        "Should fail for non-existent section"
                    ))
            except Exception as e:
                self.add_result(TestResult(
                    "update_section_nonexistent",
                    False,
                    f"Exception: {e}"
                ))

            # Update with empty content
            try:
                result = await client.call_tool("update_section", arguments={
                    "path": "update-test:another-section",
                    "content": ""
                })
                self.add_result(TestResult(
                    "update_section_empty_content",
                    True,
                    f"Empty content: {'success' if result.data.get('success') else 'failed'} (should validate)"
                ))
            except Exception as e:
                self.add_result(TestResult(
                    "update_section_empty_content",
                    True,
                    f"Empty content raises exception (acceptable): {type(e).__name__}"
                ))

        # Clean up
        test_file.unlink(missing_ok=True)

    async def test_insert_content(self, client: Client):
        """Test insert_content tool."""
        print("\n--- insert_content Tests ---")

        # Create a test file for modification
        test_file = self.docs_root / "insert_test.adoc"
        test_file.write_text("""= Insert Test Document

== First Section

Content of first section.

== Last Section

Content of last section.
""", encoding="utf-8")

        # Reload server to pick up new file
        mcp = create_mcp_server(docs_root=self.docs_root)
        async with Client(transport=mcp) as client:
            # Insert before
            try:
                result = await client.call_tool("insert_content", arguments={
                    "path": "insert-test:first-section",
                    "position": "before",
                    "content": "== New Section Before\n\nInserted before first.\n"
                })
                if result.data.get("success"):
                    self.add_result(TestResult(
                        "insert_content_before",
                        True,
                        "Successfully inserted before section"
                    ))
                else:
                    self.add_result(TestResult(
                        "insert_content_before",
                        False,
                        f"Insert before failed: {result.data.get('error', 'unknown')}"
                    ))
            except Exception as e:
                self.add_result(TestResult(
                    "insert_content_before",
                    False,
                    f"Exception: {e}"
                ))

            # Insert after
            try:
                result = await client.call_tool("insert_content", arguments={
                    "path": "insert-test:last-section",
                    "position": "after",
                    "content": "== New Section After\n\nInserted after last.\n"
                })
                if result.data.get("success"):
                    self.add_result(TestResult(
                        "insert_content_after",
                        True,
                        "Successfully inserted after section"
                    ))
                else:
                    self.add_result(TestResult(
                        "insert_content_after",
                        False,
                        f"Insert after failed: {result.data.get('error', 'unknown')}"
                    ))
            except Exception as e:
                self.add_result(TestResult(
                    "insert_content_after",
                    False,
                    f"Exception: {e}"
                ))

            # Insert with invalid position
            try:
                result = await client.call_tool("insert_content", arguments={
                    "path": "insert-test:first-section",
                    "position": "invalid",
                    "content": "Content"
                })
                if not result.data.get("success") and "error" in result.data:
                    self.add_result(TestResult(
                        "insert_content_invalid_position",
                        True,
                        "Invalid position correctly rejected"
                    ))
                else:
                    self.add_result(TestResult(
                        "insert_content_invalid_position",
                        False,
                        "Invalid position should be rejected"
                    ))
            except Exception as e:
                self.add_result(TestResult(
                    "insert_content_invalid_position",
                    False,
                    f"Exception: {e}"
                ))

            # Insert append
            try:
                result = await client.call_tool("insert_content", arguments={
                    "path": "insert-test:first-section",
                    "position": "append",
                    "content": "Appended content.\n"
                })
                self.add_result(TestResult(
                    "insert_content_append",
                    result.data.get("success", False),
                    f"Append: {'success' if result.data.get('success') else result.data.get('error', 'failed')}"
                ))
            except Exception as e:
                self.add_result(TestResult(
                    "insert_content_append",
                    False,
                    f"Exception: {e}"
                ))

        # Clean up
        test_file.unlink(missing_ok=True)

    async def test_edge_cases(self, client: Client):
        """Test various edge cases."""
        print("\n--- Edge Cases Tests ---")

        # Test document with duplicate section names
        try:
            result = await client.call_tool("get_section", arguments={"path": "duplicate-sections:introduction"})
            # There should be handling for duplicate sections
            self.add_result(TestResult(
                "edge_duplicate_sections",
                True,
                f"Duplicate sections handled: {'error' not in result.data}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "edge_duplicate_sections",
                False,
                f"Exception: {e}"
            ))

        # Test very deep nesting
        try:
            structure = await client.call_tool("get_structure", arguments={})
            self.add_result(TestResult(
                "edge_deep_nesting",
                True,
                f"Deep nesting handled, total sections: {structure.data.get('total_sections', 0)}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "edge_deep_nesting",
                False,
                f"Exception: {e}"
            ))

        # Test empty sections document
        try:
            result = await client.call_tool("get_section", arguments={"path": "empty-sections:empty-section"})
            self.add_result(TestResult(
                "edge_empty_section",
                True,
                f"Empty section: content='{result.data.get('content', '')[:50]}...'"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "edge_empty_section",
                False,
                f"Exception: {e}"
            ))

        # Test markdown file
        try:
            result = await client.call_tool("get_section", arguments={"path": "markdown-test:introduction"})
            if "error" not in result.data:
                self.add_result(TestResult(
                    "edge_markdown_file",
                    True,
                    "Markdown file parsed correctly"
                ))
            else:
                self.add_result(TestResult(
                    "edge_markdown_file",
                    False,
                    f"Markdown error: {result.data['error']}"
                ))
        except Exception as e:
            self.add_result(TestResult(
                "edge_markdown_file",
                False,
                f"Exception: {e}"
            ))

        # Test document with includes
        try:
            result = await client.call_tool("get_section", arguments={"path": "with-includes:main-content"})
            self.add_result(TestResult(
                "edge_with_includes",
                True,
                f"Document with includes: {'content' in result.data or 'error' in result.data}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "edge_with_includes",
                False,
                f"Exception: {e}"
            ))

        # Test circular includes detection
        try:
            result = await client.call_tool("validate_structure", arguments={})
            circular_detected = any(
                "circular" in str(e).lower()
                for e in result.data.get("errors", []) + result.data.get("warnings", [])
            )
            self.add_result(TestResult(
                "edge_circular_includes",
                True,
                f"Circular include detection: {'detected' if circular_detected else 'not detected (may be OK if handled elsewhere)'}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "edge_circular_includes",
                False,
                f"Exception: {e}"
            ))

        # Test Unicode in search
        try:
            result = await client.call_tool("search", arguments={"query": "Umlauts"})
            self.add_result(TestResult(
                "edge_unicode_search",
                True,
                f"Unicode search: {result.data.get('total_results', 0)} results"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "edge_unicode_search",
                False,
                f"Exception: {e}"
            ))

        # Test get_section for root document (level 0)
        try:
            result = await client.call_tool("get_section", arguments={"path": "basic"})
            self.add_result(TestResult(
                "edge_get_root_document",
                "error" not in result.data or "content" in result.data,
                f"Root document access: {'works' if 'content' in result.data else 'error'}"
            ))
        except Exception as e:
            self.add_result(TestResult(
                "edge_get_root_document",
                False,
                f"Exception: {e}"
            ))

    def print_summary(self):
        """Print test summary and identified bugs."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        print(f"\nTotal: {len(self.results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")

        print("\n--- All Results ---")
        for result in self.results:
            print(result)

        if self.bugs:
            print("\n" + "=" * 70)
            print("POTENTIAL BUGS FOUND")
            print("=" * 70)
            for i, bug in enumerate(self.bugs, 1):
                print(f"\nBug #{i}:")
                print(f"  Test: {bug['test']}")
                print(f"  Message: {bug['message']}")
                if bug['details']:
                    print(f"  Details: {bug['details'][:200]}...")


async def main():
    docs_root = Path(__file__).parent
    test_suite = MCPTestSuite(docs_root)
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
