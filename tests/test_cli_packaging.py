"""Tests for CLI packaging: verify the CLI can work without heavy MCP dependencies.

The CLI was refactored to import build_index from index_builder instead of
mcp_app, enabling packaging as a cross-platform zipapp with only pure-Python
dependencies (click, pyyaml, pathspec).
"""

import ast
import importlib
import sys
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src"


class TestIndexBuilderModule:
    """Test that index_builder.py is self-contained and works independently."""

    def test_index_builder_imports_no_heavy_deps(self):
        """index_builder.py must not import fastmcp, pydantic, or cryptography."""
        source = (SRC_DIR / "dacli" / "index_builder.py").read_text()
        tree = ast.parse(source)

        heavy_deps = {"fastmcp", "pydantic", "cryptography", "fastapi", "uvicorn", "pydocket"}
        imported_modules = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module.split(".")[0])

        violations = imported_modules & heavy_deps
        assert not violations, (
            f"index_builder.py imports heavy dependencies: {violations}. "
            "This breaks cross-platform zipapp packaging."
        )

    def test_build_index_function_exists(self):
        """build_index function should be importable from index_builder."""
        from dacli.index_builder import build_index

        assert callable(build_index)

    def test_build_index_works(self, tmp_path):
        """build_index should successfully index documents."""
        from dacli.asciidoc_parser import AsciidocStructureParser
        from dacli.index_builder import build_index
        from dacli.markdown_parser import MarkdownStructureParser
        from dacli.structure_index import StructureIndex

        # Create a minimal AsciiDoc file
        doc = tmp_path / "test.adoc"
        doc.write_text("= Test Document\n\n== Section One\n\nContent here.\n")

        index = StructureIndex()
        build_index(
            tmp_path,
            index,
            AsciidocStructureParser(tmp_path),
            MarkdownStructureParser(tmp_path),
            respect_gitignore=False,
        )

        structure = index.get_structure()
        assert len(structure["sections"]) > 0


class TestCliImportChain:
    """Test that the CLI module does not transitively import heavy dependencies."""

    def test_cli_module_does_not_import_fastmcp_directly(self):
        """cli.py must not directly import from mcp_app or fastmcp."""
        source = (SRC_DIR / "dacli" / "cli.py").read_text()
        tree = ast.parse(source)

        forbidden = {"fastmcp", "dacli.mcp_app"}
        imported_modules = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        violations = imported_modules & forbidden
        assert not violations, (
            f"cli.py imports from {violations}. "
            "The CLI must import build_index from index_builder, not mcp_app."
        )


class TestMcpAppBackwardCompat:
    """Test that mcp_app still exposes _build_index for backward compatibility."""

    def test_build_index_importable_from_mcp_app(self):
        """_build_index should still be importable from mcp_app."""
        from dacli.mcp_app import _build_index

        assert callable(_build_index)

    def test_mcp_app_build_index_is_same_function(self):
        """mcp_app._build_index should be the same as index_builder.build_index."""
        from dacli.index_builder import build_index
        from dacli.mcp_app import _build_index

        assert _build_index is build_index
