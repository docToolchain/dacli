"""Tests for CLI interface.

Tests for the mcp-docs CLI tool specified in 06_cli_specification.adoc.
Uses click.testing.CliRunner for testing click commands.
"""

import json

import pytest
from click.testing import CliRunner


class TestCliBasic:
    """Test basic CLI functionality."""

    def test_cli_help_shows_commands(self):
        """CLI --help should list all available commands."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "structure" in result.output
        assert "section" in result.output
        assert "search" in result.output
        assert "elements" in result.output
        assert "metadata" in result.output
        assert "validate" in result.output
        assert "update" in result.output
        assert "insert" in result.output
        assert "sections-at-level" in result.output

    def test_cli_version_shows_version(self):
        """CLI --version should show the version number."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "version" in result.output.lower() or "." in result.output


class TestCliStructureCommand:
    """Test the 'structure' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        # Create a simple AsciiDoc file
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Introduction

Some introduction text.

== Architecture

Architecture description.
""")
        return tmp_path

    def test_structure_returns_json(self, sample_docs):
        """structure command should return valid JSON by default."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--docs-root", str(sample_docs), "structure"])

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert "sections" in data or "total_sections" in data

    def test_structure_with_max_depth(self, sample_docs):
        """structure --max-depth should limit returned depth."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "structure", "--max-depth", "1"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)


class TestCliSectionCommand:
    """Test the 'section' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Introduction

Introduction content here.
""")
        return tmp_path

    def test_section_returns_content(self, sample_docs):
        """section command should return section content as JSON."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "section", "introduction"]
        )

        # Exit code 0 for found, 3 for not found
        assert result.exit_code in (0, 3)
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_section_not_found_returns_error(self, sample_docs):
        """section command should return error for non-existent path."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "section", "nonexistent"]
        )

        assert result.exit_code == 3  # PATH_NOT_FOUND
        data = json.loads(result.output)
        assert "error" in data


class TestCliSearchCommand:
    """Test the 'search' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Authentication

This section covers authentication topics.
""")
        return tmp_path

    def test_search_returns_results(self, sample_docs):
        """search command should return JSON results."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "search", "authentication"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "query" in data
        assert "results" in data


class TestCliMetadataCommand:
    """Test the 'metadata' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Section One

Content.
""")
        return tmp_path

    def test_metadata_project_level(self, sample_docs):
        """metadata without path should return project metadata."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--docs-root", str(sample_docs), "metadata"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_files" in data or "total_sections" in data

    def test_metadata_section_level(self, sample_docs):
        """metadata with path should return section metadata."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "metadata", "section-one"]
        )

        # Exit code 0 for found, 3 for not found
        assert result.exit_code in (0, 3)
        data = json.loads(result.output)
        assert isinstance(data, dict)


class TestCliValidateCommand:
    """Test the 'validate' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Section

Content.
""")
        return tmp_path

    def test_validate_returns_result(self, sample_docs):
        """validate command should return validation result."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--docs-root", str(sample_docs), "validate"])

        assert result.exit_code in (0, 4)  # 0 = valid, 4 = validation errors
        data = json.loads(result.output)
        assert "valid" in data


class TestCliOutputFormats:
    """Test output format options."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test

== Section

Content.
""")
        return tmp_path

    def test_json_format_is_default(self, sample_docs):
        """Default output should be JSON."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--docs-root", str(sample_docs), "structure"])

        assert result.exit_code == 0
        # Should be valid JSON
        json.loads(result.output)

    def test_pretty_flag_formats_output(self, sample_docs):
        """--pretty flag should format output for readability."""
        from mcp_server.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--pretty", "structure"]
        )

        assert result.exit_code == 0
        # Pretty JSON has newlines and indentation
        assert "\n" in result.output
        json.loads(result.output)  # Still valid JSON
