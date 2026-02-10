"""Tests for the AST dependency analyzer."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from genai_cli.analyzer import (
    AnalysisReport,
    DependencyAnalyzer,
    DependencyGraph,
    ImportInfo,
    ModuleNode,
)
from genai_cli.config import ConfigManager
from genai_cli.display import Display


@pytest.fixture
def display() -> Display:
    from io import StringIO

    return Display(file=StringIO())


@pytest.fixture
def analyzer(mock_config: ConfigManager, display: Display) -> DependencyAnalyzer:
    return DependencyAnalyzer(mock_config, display)


class TestExtractImports:
    def test_import_statement(self, analyzer: DependencyAnalyzer) -> None:
        source = "import os\nimport sys\n"
        tree = ast.parse(source)
        imports = analyzer._extract_imports(tree)
        assert len(imports) == 2
        assert imports[0].module_path == "os"
        assert imports[0].is_from_import is False

    def test_from_import(self, analyzer: DependencyAnalyzer) -> None:
        source = "from os.path import join, exists\n"
        tree = ast.parse(source)
        imports = analyzer._extract_imports(tree)
        assert len(imports) == 1
        assert imports[0].module_path == "os.path"
        assert imports[0].is_from_import is True
        assert "join" in imports[0].names
        assert "exists" in imports[0].names

    def test_no_imports(self, analyzer: DependencyAnalyzer) -> None:
        source = "x = 1\n"
        tree = ast.parse(source)
        imports = analyzer._extract_imports(tree)
        assert imports == []


class TestExtractSymbols:
    def test_function_and_class(self, analyzer: DependencyAnalyzer) -> None:
        source = "def foo(): pass\nclass Bar: pass\n"
        tree = ast.parse(source)
        symbols = analyzer._extract_symbols(tree)
        assert "foo" in symbols
        assert "Bar" in symbols

    def test_async_function(self, analyzer: DependencyAnalyzer) -> None:
        source = "async def run(): pass\n"
        tree = ast.parse(source)
        symbols = analyzer._extract_symbols(tree)
        assert "run" in symbols

    def test_nested_not_included(self, analyzer: DependencyAnalyzer) -> None:
        source = "class A:\n    def method(self): pass\n"
        tree = ast.parse(source)
        symbols = analyzer._extract_symbols(tree)
        assert "A" in symbols
        assert "method" not in symbols


class TestParseFile:
    def test_parse_valid_file(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        f = tmp_path / "module.py"
        f.write_text("import os\ndef hello(): pass\n")
        node = analyzer._parse_file(f, tmp_path)
        assert node is not None
        assert node.module_name == "module"
        assert len(node.imports) == 1
        assert "hello" in node.symbols

    def test_parse_syntax_error(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n")
        node = analyzer._parse_file(f, tmp_path)
        assert node is None

    def test_parse_init_file(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        init = pkg / "__init__.py"
        init.write_text("# package init\n")
        node = analyzer._parse_file(init, tmp_path)
        assert node is not None
        assert node.is_package is True
        assert node.module_name == "mypackage"


class TestBuildGraph:
    def test_simple_graph(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        (tmp_path / "a.py").write_text("from b import foo\n")
        (tmp_path / "b.py").write_text("def foo(): pass\n")

        node_a = analyzer._parse_file(tmp_path / "a.py", tmp_path)
        node_b = analyzer._parse_file(tmp_path / "b.py", tmp_path)
        assert node_a and node_b

        nodes = {node_a.module_name: node_a, node_b.module_name: node_b}
        graph = analyzer._build_graph(nodes, tmp_path)
        assert "b" in graph.edges.get("a", [])
        assert "a" in graph.reverse_edges.get("b", [])


class TestDetectCycles:
    def test_no_cycles(self, analyzer: DependencyAnalyzer) -> None:
        edges = {"a": ["b"], "b": ["c"], "c": []}
        cycles = analyzer._detect_cycles(edges)
        assert cycles == []

    def test_simple_cycle(self, analyzer: DependencyAnalyzer) -> None:
        edges = {"a": ["b"], "b": ["a"]}
        cycles = analyzer._detect_cycles(edges)
        assert len(cycles) > 0

    def test_self_cycle(self, analyzer: DependencyAnalyzer) -> None:
        edges = {"a": ["a"]}
        cycles = analyzer._detect_cycles(edges)
        assert len(cycles) == 1


class TestClassifyModules:
    def test_leaf_modules(self, analyzer: DependencyAnalyzer) -> None:
        graph = DependencyGraph(
            nodes={
                "a": ModuleNode(path="a.py", module_name="a"),
                "b": ModuleNode(path="b.py", module_name="b"),
                "c": ModuleNode(path="c.py", module_name="c"),
            },
            edges={"a": ["b"], "b": ["c"], "c": []},
            reverse_edges={"b": ["a"], "c": ["b"]},
        )
        leaf, core = analyzer._classify_modules(graph)
        assert "a" in leaf  # a has no reverse edges


class TestClusterModules:
    def test_two_clusters(self, analyzer: DependencyAnalyzer) -> None:
        graph = DependencyGraph(
            nodes={
                "a": ModuleNode(path="a.py", module_name="a"),
                "b": ModuleNode(path="b.py", module_name="b"),
                "c": ModuleNode(path="c.py", module_name="c"),
            },
            edges={"a": ["b"], "b": [], "c": []},
            reverse_edges={"b": ["a"]},
        )
        clusters = analyzer._cluster_modules(graph)
        # a and b should be in one cluster, c in another
        assert len(clusters) == 2


class TestResolveImportToPath:
    def test_resolve_module(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        (tmp_path / "mymod.py").write_text("")
        result = analyzer._resolve_import_to_path("mymod", tmp_path)
        assert result is not None
        assert "mymod.py" in result

    def test_resolve_package(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        result = analyzer._resolve_import_to_path("mypkg", tmp_path)
        assert result is not None
        assert "__init__.py" in result

    def test_resolve_not_found(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        result = analyzer._resolve_import_to_path("nonexistent", tmp_path)
        assert result is None


class TestAnalyze:
    def test_full_analysis(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        (tmp_path / "main.py").write_text(
            "from utils import helper\ndef run(): pass\n"
        )
        (tmp_path / "utils.py").write_text("def helper(): pass\n")

        report = analyzer.analyze([str(tmp_path)], str(tmp_path))
        assert report.total_modules == 2
        assert report.total_imports >= 1

    def test_exclude_patterns(
        self, analyzer: DependencyAnalyzer, tmp_path: Path
    ) -> None:
        (tmp_path / "good.py").write_text("x = 1\n")
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "bad.py").write_text("x = 1\n")

        report = analyzer.analyze([str(tmp_path)], str(tmp_path))
        module_names = list(report.graph.nodes.keys())
        assert all("__pycache__" not in m for m in module_names)


class TestFormatAndDict:
    def test_to_dict(self, analyzer: DependencyAnalyzer) -> None:
        report = AnalysisReport(total_modules=2, total_imports=3)
        d = analyzer.to_dict(report)
        assert d["total_modules"] == 2
        assert d["total_imports"] == 3

    def test_format_report(self, analyzer: DependencyAnalyzer) -> None:
        report = AnalysisReport(
            total_modules=5,
            total_imports=10,
            core_modules=["config"],
            leaf_modules=["utils"],
            cycles=[["a", "b", "a"]],
            clusters={"cluster_0": ["a", "b"]},
            graph=DependencyGraph(
                edges={"a": ["b"], "b": []},
                reverse_edges={"b": ["a"]},
            ),
        )
        text = analyzer.format_report(report)
        assert "Dependency Analysis Report" in text
        assert "config" in text
        assert "Circular Dependencies" in text
