"""Tests for ADR-014: Multi-Root Documentation Sources (Phase 1).

Tests cover:
- Root config parsing and validation
- Namespace-prefixed paths in multi-root mode
- Access mode enforcement (reference = read-only)
- get_namespaces tool output
- Document role detection
- Backward compatibility (single-root unchanged)
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli
from dacli.models import DocumentRoot, detect_document_role
from dacli.root_config import RootConfigError, parse_root_spec, resolve_roots


# --- Document role detection ---


class TestDocumentRoleDetection:
    """Test detect_document_role for well-known filenames."""

    @pytest.mark.parametrize(
        "filename,expected_role",
        [
            ("README.md", "project-meta"),
            ("readme.adoc", "project-meta"),
            ("LLM.md", "project-meta"),
            ("CLAUDE.md", "project-meta"),
            ("CHANGELOG.md", "project-meta"),
            ("TODO.md", "project-meta"),
            ("INSTALL.adoc", "project-meta"),
            ("ROADMAP.md", "project-meta"),
            ("AGENTS.md", "project-meta"),
            ("architecture.adoc", "documentation"),
            ("api-spec.md", "documentation"),
            ("index.adoc", "documentation"),
            ("01_introduction.adoc", "documentation"),
        ],
    )
    def test_role_detection(self, filename, expected_role):
        assert detect_document_role(Path(filename)) == expected_role


# --- Root config parsing ---


class TestParseRootSpec:
    """Test parse_root_spec key=value parsing."""

    def test_parse_minimal_spec(self, tmp_path):
        root = parse_root_spec(f"name=my-docs,path={tmp_path}", "workspace")
        assert root.name == "my-docs"
        assert root.path == tmp_path
        assert root.mode == "workspace"
        assert root.doc_type is None

    def test_parse_spec_with_type(self, tmp_path):
        root = parse_root_spec(f"name=my-docs,path={tmp_path},type=arc42", "reference")
        assert root.doc_type == "arc42"
        assert root.mode == "reference"

    def test_reject_unknown_keys(self, tmp_path):
        with pytest.raises(RootConfigError, match="Unknown key"):
            parse_root_spec(f"name=x,path={tmp_path},foo=bar", "workspace")

    def test_reject_missing_name(self, tmp_path):
        with pytest.raises(RootConfigError, match="Missing required"):
            parse_root_spec(f"path={tmp_path}", "workspace")

    def test_reject_missing_path(self):
        with pytest.raises(RootConfigError, match="Missing required"):
            parse_root_spec("name=x", "workspace")

    def test_reject_duplicate_key(self, tmp_path):
        with pytest.raises(RootConfigError, match="Duplicate key"):
            parse_root_spec(f"name=x,name=y,path={tmp_path}", "workspace")

    def test_reject_invalid_format(self):
        with pytest.raises(RootConfigError, match="Invalid key=value"):
            parse_root_spec("name_without_equals", "workspace")


class TestResolveRoots:
    """Test resolve_roots validation and backward compat."""

    def test_default_cwd_workspace(self):
        roots = resolve_roots()
        assert len(roots) == 1
        assert roots[0].mode == "workspace"
        assert roots[0].path == Path.cwd().resolve()

    def test_docs_root_single_workspace(self, tmp_path):
        roots = resolve_roots(docs_root=tmp_path)
        assert len(roots) == 1
        assert roots[0].name == tmp_path.name
        assert roots[0].mode == "workspace"

    def test_multi_root(self, tmp_path):
        ws = tmp_path / "ws"
        ref = tmp_path / "ref"
        ws.mkdir()
        ref.mkdir()
        roots = resolve_roots(
            workspaces=[f"name=ws,path={ws}"],
            references=[f"name=ref,path={ref}"],
        )
        assert len(roots) == 2
        assert roots[0].mode == "workspace"
        assert roots[1].mode == "reference"

    def test_reject_docs_root_with_workspace(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        with pytest.raises(RootConfigError, match="Cannot combine"):
            resolve_roots(
                workspaces=[f"name=ws,path={ws}"],
                docs_root=tmp_path,
            )

    def test_reject_namespace_collision(self, tmp_path):
        ws = tmp_path / "ws"
        ref = tmp_path / "ref"
        ws.mkdir()
        ref.mkdir()
        with pytest.raises(RootConfigError, match="Namespace collision"):
            resolve_roots(
                workspaces=[f"name=same,path={ws}"],
                references=[f"name=same,path={ref}"],
            )

    def test_reject_nonexistent_path(self, tmp_path):
        with pytest.raises(RootConfigError, match="does not exist"):
            resolve_roots(workspaces=[f"name=x,path={tmp_path}/nonexistent"])


# --- Multi-root integration ---


@pytest.fixture
def multi_root_dirs(tmp_path):
    """Create workspace and reference doc roots with test content."""
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    (ws_dir / "guide.adoc").write_text(
        "= User Guide\n\n== Getting Started\n\nWelcome.\n\n=== Installation\n\nRun pip install.\n",
        encoding="utf-8",
    )
    (ws_dir / "README.md").write_text("# Readme\n\nProject description.\n", encoding="utf-8")

    ref_dir = tmp_path / "reference"
    ref_dir.mkdir()
    (ref_dir / "api.adoc").write_text(
        "= API Reference\n\n== Endpoints\n\nGET /items\n",
        encoding="utf-8",
    )

    return ws_dir, ref_dir


class TestMultiRootCLI:
    """Test multi-root behavior through the CLI."""

    def test_namespaces_command(self, multi_root_dirs):
        ws_dir, ref_dir = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--workspace", f"name=myapp,path={ws_dir}",
                "--reference", f"name=api-ref,path={ref_dir}",
                "--format", "json",
                "namespaces",
            ],
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["total_namespaces"] == 2
        names = [ns["name"] for ns in data["namespaces"]]
        assert "myapp" in names
        assert "api-ref" in names

        # Check modes
        ns_map = {ns["name"]: ns for ns in data["namespaces"]}
        assert ns_map["myapp"]["mode"] == "workspace"
        assert ns_map["api-ref"]["mode"] == "reference"

    def test_namespace_prefixed_paths(self, multi_root_dirs):
        ws_dir, ref_dir = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--workspace", f"name=myapp,path={ws_dir}",
                "--reference", f"name=api-ref,path={ref_dir}",
                "--format", "json",
                "structure", "--max-depth", "0",
            ],
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        paths = [s["path"] for s in data["sections"]]
        # All paths should have namespace prefix
        assert any(p.startswith("myapp:") for p in paths)
        assert any(p.startswith("api-ref:") for p in paths)

    def test_read_from_reference(self, multi_root_dirs):
        ws_dir, ref_dir = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--workspace", f"name=myapp,path={ws_dir}",
                "--reference", f"name=api-ref,path={ref_dir}",
                "section", "api-ref:api:endpoints",
            ],
        )
        assert result.exit_code == 0
        assert "GET /items" in result.output

    def test_write_to_reference_rejected(self, multi_root_dirs):
        ws_dir, ref_dir = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--workspace", f"name=myapp,path={ws_dir}",
                "--reference", f"name=api-ref,path={ref_dir}",
                "update", "api-ref:api:endpoints",
                "--content", "hacked",
            ],
        )
        assert result.exit_code != 0
        assert "read-only reference" in result.output

    def test_insert_to_reference_rejected(self, multi_root_dirs):
        ws_dir, ref_dir = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--workspace", f"name=myapp,path={ws_dir}",
                "--reference", f"name=api-ref,path={ref_dir}",
                "insert", "api-ref:api:endpoints",
                "--position", "after",
                "--content", "hacked",
            ],
        )
        assert result.exit_code != 0
        assert "read-only reference" in result.output

    def test_write_to_workspace_allowed(self, multi_root_dirs):
        ws_dir, ref_dir = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--workspace", f"name=myapp,path={ws_dir}",
                "--reference", f"name=api-ref,path={ref_dir}",
                "--format", "json",
                "update", "myapp:guide:getting-started",
                "--content", "Updated content.",
            ],
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["success"] is True

    def test_search_across_roots(self, multi_root_dirs):
        ws_dir, ref_dir = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--workspace", f"name=myapp,path={ws_dir}",
                "--reference", f"name=api-ref,path={ref_dir}",
                "--format", "json",
                "search", "Endpoints",
            ],
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["total_results"] >= 1
        # Result should come from reference namespace
        assert any("api-ref:" in r["path"] for r in data["results"])

    def test_document_roles(self, multi_root_dirs):
        ws_dir, _ = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(ws_dir),
                "--format", "json",
                "namespaces",
            ],
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        docs = data["namespaces"][0]["documents"]
        roles = {d["slug"]: d["role"] for d in docs}
        assert roles["readme"] == "project-meta"
        assert roles["guide"] == "documentation"


# --- Single-root backward compatibility ---


class TestSingleRootBackwardCompat:
    """Verify --docs-root behavior is unchanged."""

    def test_docs_root_no_namespace_prefix(self, multi_root_dirs):
        ws_dir, _ = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(ws_dir),
                "--format", "json",
                "structure", "--max-depth", "0",
            ],
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        paths = [s["path"] for s in data["sections"]]
        # No namespace prefix in single-root mode
        assert all(":" not in p or p.count(":") == 0 or "/" in p.split(":")[0] or p.split(":")[0].islower() for p in paths)
        # Specifically: paths should NOT start with "workspace:"
        assert not any(p.startswith("workspace:") for p in paths)

    def test_namespaces_single_root(self, multi_root_dirs):
        ws_dir, _ = multi_root_dirs
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(ws_dir),
                "--format", "json",
                "namespaces",
            ],
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["total_namespaces"] == 1
        assert data["namespaces"][0]["mode"] == "workspace"


# --- Normalize path in multi-root ---


class TestNormalizePathMultiRoot:
    """Test normalize_path with multi_root flag."""

    def test_two_colons_valid_in_multi_root(self):
        from dacli.structure_index import StructureIndex
        path = "ns:file:section"
        normalized, had_extra = StructureIndex.normalize_path(path, multi_root=True)
        assert normalized == "ns:file:section"
        assert had_extra is False

    def test_two_colons_normalized_in_single_root(self):
        from dacli.structure_index import StructureIndex
        path = "file:section:subsection"
        normalized, had_extra = StructureIndex.normalize_path(path, multi_root=False)
        assert normalized == "file:section.subsection"
        assert had_extra is True

    def test_three_colons_normalized_in_multi_root(self):
        from dacli.structure_index import StructureIndex
        path = "ns:file:section:sub"
        normalized, had_extra = StructureIndex.normalize_path(path, multi_root=True)
        assert normalized == "ns:file:section.sub"
        assert had_extra is True


# --- Parse path components ---


class TestParsePathComponents:
    """Test parse_path_components for all formats."""

    def test_single_root_file_section(self):
        from dacli.structure_index import StructureIndex
        ns, file, section = StructureIndex.parse_path_components("guides/install:prerequisites")
        assert ns is None
        assert file == "guides/install"
        assert section == "prerequisites"

    def test_multi_root_namespace_file_section(self):
        from dacli.structure_index import StructureIndex
        ns, file, section = StructureIndex.parse_path_components("myapp:guides/install:prerequisites")
        assert ns == "myapp"
        assert file == "guides/install"
        assert section == "prerequisites"

    def test_one_colon_ambiguous(self):
        """With 1 colon, parse_path_components can't distinguish namespace:file
        from file:section. It defaults to single-root (file:section) interpretation.
        Multi-root paths with sections always have 2 colons."""
        from dacli.structure_index import StructureIndex
        ns, file, section = StructureIndex.parse_path_components("myapp:guides/install")
        # 1 colon = single-root interpretation (file:section)
        assert ns is None
        assert file == "myapp"
        assert section == "guides/install"

    def test_file_only_with_slash(self):
        from dacli.structure_index import StructureIndex
        ns, file, section = StructureIndex.parse_path_components("guides/install")
        assert ns is None
        assert file == "guides/install"
        assert section == ""

    def test_legacy_section_only(self):
        from dacli.structure_index import StructureIndex
        ns, file, section = StructureIndex.parse_path_components("introduction")
        assert ns is None
        assert file == ""
        assert section == "introduction"
