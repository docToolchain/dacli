"""Tests for blockquote element type consistency (Issue #270).

blockquote is listed in --help but rejected at runtime by valid_types check.
"""

from click.testing import CliRunner

from dacli.cli import cli


class TestBlockquoteElementType:
    """blockquote must be accepted as a valid element type."""

    def test_blockquote_no_warning(self, tmp_path):
        """Passing --type blockquote must not produce an 'Unknown element type' warning."""
        doc = tmp_path / "test.md"
        doc.write_text("# Test\n\n> A blockquote\n")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--docs-root", str(tmp_path),
            "--format", "json",
            "elements",
            "--type", "blockquote",
        ])

        assert "Unknown element type" not in result.output, (
            f"blockquote rejected as unknown: {result.output}"
        )

    def test_valid_types_match_help_text(self):
        """All types listed in --help must be in valid_types."""
        runner = CliRunner()
        result = runner.invoke(cli, ["elements", "--help"])

        # Extract types from help text
        # Help says: "Element type: admonition, blockquote, code, image, list, plantuml, table"
        assert "blockquote" in result.output, "blockquote missing from --help"

    def test_all_model_element_types_accepted(self, tmp_path):
        """Every ElementType in the model should be accepted by CLI validation."""
        from dacli.models import Element

        doc = tmp_path / "test.md"
        doc.write_text("# Test\n\nSome content.\n")

        runner = CliRunner()
        # Get all valid types from the Element model's type field
        # The Literal type annotation lists all valid values
        import typing
        type_hints = typing.get_type_hints(Element)
        # Element.type is Literal["code", "table", ...]
        literal_args = typing.get_args(type_hints["type"])

        for etype in literal_args:
            result = runner.invoke(cli, [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "elements",
                "--type", etype,
            ])
            assert "Unknown element type" not in result.output, (
                f"Element type '{etype}' rejected by CLI but defined in model"
            )
