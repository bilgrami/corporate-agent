"""Tests for file bundler module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from genai_cli.bundler import FileBundler, _is_binary, _matches_any
from genai_cli.config import ConfigManager


@pytest.fixture
def bundler(mock_config: ConfigManager) -> FileBundler:
    return FileBundler(mock_config)


class TestHelpers:
    def test_is_binary_false(self, tmp_path: Path) -> None:
        f = tmp_path / "text.py"
        f.write_text("hello world")
        assert _is_binary(f) is False

    def test_is_binary_true(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\x03")
        assert _is_binary(f) is True

    def test_matches_any_glob(self) -> None:
        assert _matches_any("src/__pycache__/mod.pyc", ["**/*.pyc"]) is True
        assert _matches_any("src/main.py", ["**/*.pyc"]) is False

    def test_matches_any_name(self) -> None:
        assert _matches_any("project/.env", ["**/.env"]) is True
        assert _matches_any(".env", [".env"]) is True


class TestClassifyFile:
    def test_python_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("main.py")) == "code"

    def test_js_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("app.js")) == "code"

    def test_ts_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("app.ts")) == "code"

    def test_tsx_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("component.tsx")) == "code"

    def test_java_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("Main.java")) == "code"

    def test_go_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("main.go")) == "code"

    def test_rs_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("lib.rs")) == "code"

    def test_sql_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("query.sql")) == "code"

    def test_md_is_docs(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("README.md")) == "docs"

    def test_yaml_is_docs(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("config.yaml")) == "docs"

    def test_json_is_docs(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("package.json")) == "docs"

    def test_sh_is_scripts(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("setup.sh")) == "scripts"

    def test_makefile_is_scripts(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("Makefile")) == "scripts"

    def test_dockerfile_is_scripts(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("Dockerfile")) == "scripts"

    def test_ipynb_is_notebooks(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("analysis.ipynb")) == "notebooks"

    def test_unknown_returns_none(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("image.png")) is None

    def test_cpp_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("main.cpp")) == "code"

    def test_h_is_code(self, bundler: FileBundler) -> None:
        assert bundler.classify_file(Path("header.h")) == "code"


class TestDiscoverFiles:
    def test_discover_from_dir(
        self, bundler: FileBundler, sample_project_dir: Path
    ) -> None:
        result, unmatched = bundler.discover_files([str(sample_project_dir / "src")])
        assert "code" in result
        names = [p.name for p in result["code"]]
        assert "main.py" in names
        assert "utils.py" in names

    def test_discover_single_file(
        self, bundler: FileBundler, sample_python_file: Path
    ) -> None:
        result, unmatched = bundler.discover_files([str(sample_python_file)])
        assert "code" in result
        assert len(result["code"]) == 1

    def test_excludes_pycache(
        self, bundler: FileBundler, sample_project_dir: Path
    ) -> None:
        result, unmatched = bundler.discover_files([str(sample_project_dir)])
        all_paths = []
        for paths in result.values():
            all_paths.extend(str(p) for p in paths)
        assert not any("__pycache__" in p for p in all_paths)

    def test_excludes_env(
        self, bundler: FileBundler, sample_project_dir: Path
    ) -> None:
        result, unmatched = bundler.discover_files([str(sample_project_dir)])
        all_paths = []
        for paths in result.values():
            all_paths.extend(p.name for p in paths)
        assert ".env" not in all_paths

    def test_filter_by_type(
        self, bundler: FileBundler, sample_project_dir: Path
    ) -> None:
        result, unmatched = bundler.discover_files(
            [str(sample_project_dir)], file_type="code"
        )
        assert "docs" not in result

    def test_size_limit(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        big = tmp_path / "big.py"
        big.write_text("x" * (600 * 1024))  # 600KB > 500KB limit
        result, unmatched = bundler.discover_files([str(big)])
        assert "code" not in result or big not in result.get("code", [])


class TestGlobExpansion:
    """Tests for glob pattern expansion in discover_files."""

    def test_glob_expansion(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        """*.py pattern expands to matching files."""
        (tmp_path / "a.py").write_text("# a")
        (tmp_path / "b.py").write_text("# b")
        (tmp_path / "c.txt").write_text("# c")

        result, unmatched = bundler.discover_files(
            [str(tmp_path / "*.py")]
        )
        assert "code" in result
        names = {p.name for p in result["code"]}
        assert "a.py" in names
        assert "b.py" in names
        assert "c.txt" not in names
        assert unmatched == []

    def test_absolute_path(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        """Absolute path resolves and bundles."""
        f = tmp_path / "external.py"
        f.write_text("x = 1\n")

        result, unmatched = bundler.discover_files([str(f)])
        assert "code" in result
        assert len(result["code"]) == 1
        assert result["code"][0].name == "external.py"
        assert unmatched == []

    def test_unmatched_paths(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        """Non-existent paths returned in unmatched list."""
        result, unmatched = bundler.discover_files(
            [str(tmp_path / "nonexistent.py"), str(tmp_path / "nope/*.py")]
        )
        assert len(unmatched) == 2
        assert not result

    def test_recursive_glob(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        """Recursive **/*.py pattern finds nested files."""
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "mod.py").write_text("# mod")
        (tmp_path / "top.py").write_text("# top")

        result, unmatched = bundler.discover_files(
            [str(tmp_path / "**/*.py")]
        )
        assert "code" in result
        names = {p.name for p in result["code"]}
        assert "mod.py" in names
        assert "top.py" in names


class TestExcludePatterns:
    """Tests for expanded exclude patterns."""

    def test_exclude_venv(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        """.venv/ directory skipped during walk."""
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "pkg.py").write_text("# venv file")
        (tmp_path / "app.py").write_text("# app")

        result, _ = bundler.discover_files([str(tmp_path)])
        all_paths = []
        for paths in result.values():
            all_paths.extend(str(p) for p in paths)
        assert not any(".venv" in p for p in all_paths)
        assert any("app.py" in p for p in all_paths)

    def test_exclude_gitignore_dirs(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        """All .gitignore-standard dirs excluded."""
        for dirname in ["node_modules", ".git", "dist", "build", "__pycache__",
                        ".pytest_cache", ".mypy_cache", ".ruff_cache",
                        ".tox", ".eggs", "htmlcov", ".idea", ".vscode"]:
            d = tmp_path / dirname
            d.mkdir()
            (d / "file.py").write_text(f"# {dirname}")

        (tmp_path / "real.py").write_text("# real code")

        result, _ = bundler.discover_files([str(tmp_path)])
        all_paths = []
        for paths in result.values():
            all_paths.extend(str(p) for p in paths)

        for dirname in ["node_modules", ".git", "dist", "build", "__pycache__",
                        ".pytest_cache", ".mypy_cache", ".ruff_cache",
                        ".tox", ".eggs", "htmlcov", ".idea", ".vscode"]:
            assert not any(dirname in p for p in all_paths), f"{dirname} should be excluded"

        assert any("real.py" in p for p in all_paths)

    def test_exclude_ds_store(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        """.DS_Store file excluded."""
        (tmp_path / ".DS_Store").write_text("binary junk")
        (tmp_path / "good.py").write_text("# good")

        result, _ = bundler.discover_files([str(tmp_path)])
        all_names = []
        for paths in result.values():
            all_names.extend(p.name for p in paths)
        assert ".DS_Store" not in all_names


class TestBundleFiles:
    def test_bundle_format(
        self, bundler: FileBundler, sample_project_dir: Path
    ) -> None:
        bundles, unmatched = bundler.bundle_files(
            [str(sample_project_dir / "src")],
            base_dir=sample_project_dir,
        )
        assert len(bundles) >= 1
        code_bundle = next(b for b in bundles if b.file_type == "code")
        assert "===== FILE:" in code_bundle.content
        assert "Relative Path:" in code_bundle.content

    def test_bundle_has_file_count(
        self, bundler: FileBundler, sample_project_dir: Path
    ) -> None:
        bundles, _ = bundler.bundle_files([str(sample_project_dir / "src")])
        code_bundle = next(b for b in bundles if b.file_type == "code")
        assert code_bundle.file_count == 2

    def test_bundle_per_type(
        self, bundler: FileBundler, sample_project_dir: Path
    ) -> None:
        bundles, _ = bundler.bundle_files([str(sample_project_dir)])
        types = {b.file_type for b in bundles}
        assert "code" in types
        assert "docs" in types

    def test_estimated_tokens(
        self, bundler: FileBundler, sample_project_dir: Path
    ) -> None:
        bundles, _ = bundler.bundle_files([str(sample_project_dir / "src")])
        code_bundle = next(b for b in bundles if b.file_type == "code")
        assert code_bundle.estimated_tokens > 0

    def test_notebook_cells(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        nb = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {},
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": "# Title",
                },
                {
                    "cell_type": "code",
                    "metadata": {},
                    "source": "x = 1",
                    "outputs": [{"text": "1", "output_type": "stream", "name": "stdout"}],
                    "execution_count": 1,
                },
            ],
        }
        nb_path = tmp_path / "test.ipynb"
        nb_path.write_text(json.dumps(nb))
        bundles, _ = bundler.bundle_files([str(nb_path)], base_dir=tmp_path)
        assert len(bundles) == 1
        assert bundles[0].file_type == "notebooks"
        assert "--- Cell 1 [markdown] ---" in bundles[0].content
        assert "--- Cell 2 [code] ---" in bundles[0].content
        assert "# Title" in bundles[0].content

    def test_bundle_unmatched(
        self, bundler: FileBundler, tmp_path: Path
    ) -> None:
        """bundle_files returns unmatched paths."""
        bundles, unmatched = bundler.bundle_files(
            [str(tmp_path / "nonexistent.py")]
        )
        assert len(bundles) == 0
        assert len(unmatched) == 1


class TestEstimateTokens:
    def test_estimate_short(self) -> None:
        tokens = FileBundler.estimate_tokens("hello world")
        assert tokens > 0

    def test_estimate_empty(self) -> None:
        tokens = FileBundler.estimate_tokens("")
        assert tokens == 0
