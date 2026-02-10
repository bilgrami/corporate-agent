"""AST-based dependency analyzer for Python codebases."""

from __future__ import annotations

import ast
import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

from genai_cli.config import ConfigManager
from genai_cli.display import Display


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ImportInfo:
    """A single import statement."""

    module_path: str
    names: list[str] = field(default_factory=list)
    is_from_import: bool = False
    line_number: int = 0
    source_file: str = ""


@dataclass
class ModuleNode:
    """A module in the dependency graph."""

    path: str
    module_name: str
    imports: list[ImportInfo] = field(default_factory=list)
    imported_by: list[str] = field(default_factory=list)
    is_package: bool = False
    symbols: list[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    """Complete dependency graph."""

    nodes: dict[str, ModuleNode] = field(default_factory=dict)
    edges: dict[str, list[str]] = field(default_factory=dict)
    reverse_edges: dict[str, list[str]] = field(default_factory=dict)
    cycles: list[list[str]] = field(default_factory=list)
    root_dir: str = ""


@dataclass
class AnalysisReport:
    """Summary of dependency analysis."""

    total_modules: int = 0
    total_imports: int = 0
    leaf_modules: list[str] = field(default_factory=list)
    core_modules: list[str] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    clusters: dict[str, list[str]] = field(default_factory=dict)
    graph: DependencyGraph = field(default_factory=DependencyGraph)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class DependencyAnalyzer:
    """Analyze Python codebases for module dependencies using AST parsing."""

    def __init__(self, config: ConfigManager, display: Display) -> None:
        self._config = config
        self._display = display

    def analyze(
        self, paths: list[str], root_dir: str | None = None
    ) -> AnalysisReport:
        """Main entry point: analyze Python files and produce a report."""
        root = Path(root_dir) if root_dir else Path.cwd()

        py_files = self._discover_files(paths, root)

        nodes: dict[str, ModuleNode] = {}
        for fpath in py_files:
            node = self._parse_file(fpath, root)
            if node:
                nodes[node.module_name] = node

        graph = self._build_graph(nodes, root)
        graph.cycles = self._detect_cycles(graph.edges)

        leaf_modules, core_modules = self._classify_modules(graph)
        clusters = self._cluster_modules(graph)

        total_imports = sum(len(n.imports) for n in nodes.values())

        return AnalysisReport(
            total_modules=len(nodes),
            total_imports=total_imports,
            leaf_modules=leaf_modules,
            core_modules=core_modules,
            cycles=graph.cycles,
            clusters=clusters,
            graph=graph,
        )

    def _discover_files(self, paths: list[str], root: Path) -> list[Path]:
        """Discover Python files from given paths."""
        exclude = self._config.settings.exclude_patterns
        py_files: list[Path] = []

        for path_str in paths:
            path = Path(path_str)
            if not path.is_absolute():
                path = root / path

            if path.is_file() and path.suffix == ".py":
                py_files.append(path.resolve())
            elif path.is_dir():
                for dirpath, dirnames, filenames in os.walk(path):
                    dirnames[:] = [
                        d
                        for d in dirnames
                        if not any(
                            fnmatch.fnmatch(d, p.strip("*/")) for p in exclude
                        )
                    ]
                    for fname in filenames:
                        if fname.endswith(".py"):
                            fpath = Path(dirpath) / fname
                            rel = str(fpath)
                            if not any(
                                fnmatch.fnmatch(rel, p) for p in exclude
                            ):
                                py_files.append(fpath.resolve())

        return py_files

    def _parse_file(
        self, file_path: Path, root_dir: Path
    ) -> ModuleNode | None:
        """Parse a Python file and extract module info."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            return None

        try:
            rel = file_path.resolve().relative_to(root_dir.resolve())
        except ValueError:
            rel = file_path

        module_name = self._path_to_module(rel)
        imports = self._extract_imports(tree, str(file_path))
        symbols = self._extract_symbols(tree)
        is_package = file_path.name == "__init__.py"

        return ModuleNode(
            path=str(file_path),
            module_name=module_name,
            imports=imports,
            is_package=is_package,
            symbols=symbols,
        )

    def _extract_imports(
        self, tree: ast.AST, source_file: str = ""
    ) -> list[ImportInfo]:
        """Walk AST for Import and ImportFrom nodes."""
        imports: list[ImportInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module_path=alias.name,
                            names=[alias.asname or alias.name],
                            is_from_import=False,
                            line_number=node.lineno,
                            source_file=source_file,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = (
                    [alias.name for alias in node.names] if node.names else []
                )
                imports.append(
                    ImportInfo(
                        module_path=module,
                        names=names,
                        is_from_import=True,
                        line_number=node.lineno,
                        source_file=source_file,
                    )
                )

        return imports

    def _extract_symbols(self, tree: ast.AST) -> list[str]:
        """Extract top-level function and class names."""
        symbols: list[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                symbols.append(node.name)
        return symbols

    def _build_graph(
        self, nodes: dict[str, ModuleNode], root_dir: Path
    ) -> DependencyGraph:
        """Build directed graph from parsed modules."""
        edges: dict[str, list[str]] = {}
        reverse_edges: dict[str, list[str]] = {}
        known_modules = set(nodes.keys())

        for mod_name, node in nodes.items():
            edges.setdefault(mod_name, [])
            for imp in node.imports:
                resolved = self._resolve_import_to_module(
                    imp.module_path, known_modules
                )
                if resolved and resolved != mod_name:
                    if resolved not in edges[mod_name]:
                        edges[mod_name].append(resolved)
                    reverse_edges.setdefault(resolved, [])
                    if mod_name not in reverse_edges[resolved]:
                        reverse_edges[resolved].append(mod_name)
                    if (
                        resolved in nodes
                        and mod_name not in nodes[resolved].imported_by
                    ):
                        nodes[resolved].imported_by.append(mod_name)

        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            reverse_edges=reverse_edges,
            root_dir=str(root_dir),
        )

    def _detect_cycles(
        self, edges: dict[str, list[str]]
    ) -> list[list[str]]:
        """Detect cycles using DFS with gray/black coloring."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in edges}
        cycles: list[list[str]] = []
        path: list[str] = []

        def dfs(node: str) -> None:
            color[node] = GRAY
            path.append(node)

            for neighbor in edges.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif color[neighbor] == WHITE:
                    dfs(neighbor)

            path.pop()
            color[node] = BLACK

        for node in edges:
            if color.get(node, WHITE) == WHITE:
                dfs(node)

        return cycles

    def _classify_modules(
        self, graph: DependencyGraph
    ) -> tuple[list[str], list[str]]:
        """Classify modules: leaf (0 reverse edges) vs core (top quartile)."""
        leaf_modules: list[str] = []
        rev_counts: dict[str, int] = {}

        for mod_name in graph.nodes:
            count = len(graph.reverse_edges.get(mod_name, []))
            rev_counts[mod_name] = count
            if count == 0:
                leaf_modules.append(mod_name)

        core_modules: list[str] = []
        if rev_counts:
            sorted_counts = sorted(rev_counts.values(), reverse=True)
            threshold_idx = max(1, len(sorted_counts) // 4)
            threshold = sorted_counts[
                min(threshold_idx, len(sorted_counts) - 1)
            ]
            core_modules = [
                mod
                for mod, count in rev_counts.items()
                if count >= threshold and count > 0
            ]

        return sorted(leaf_modules), sorted(core_modules)

    def _cluster_modules(
        self, graph: DependencyGraph
    ) -> dict[str, list[str]]:
        """Group modules into connected components."""
        adj: dict[str, set[str]] = {}
        for mod in graph.nodes:
            adj.setdefault(mod, set())
        for mod, deps in graph.edges.items():
            for dep in deps:
                if dep in adj:
                    adj[mod].add(dep)
                    adj[dep].add(mod)

        visited: set[str] = set()
        clusters: dict[str, list[str]] = {}
        cluster_id = 0

        for mod in sorted(adj.keys()):
            if mod in visited:
                continue
            component: list[str] = []
            queue = [mod]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                for neighbor in sorted(adj.get(current, set())):
                    if neighbor not in visited:
                        queue.append(neighbor)
            clusters[f"cluster_{cluster_id}"] = sorted(component)
            cluster_id += 1

        return clusters

    def _resolve_import_to_module(
        self, import_module: str, known_modules: set[str]
    ) -> str | None:
        """Resolve an import to a known module name."""
        if import_module in known_modules:
            return import_module

        parts = import_module.split(".")
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in known_modules:
                return candidate

        return None

    def _resolve_import_to_path(
        self, import_module: str, root_dir: Path
    ) -> str | None:
        """Resolve a dotted module name to a file path."""
        parts = import_module.split(".")

        pkg_path = root_dir / Path(*parts) / "__init__.py"
        if pkg_path.is_file():
            return str(pkg_path)

        mod_path = root_dir / Path(*parts).with_suffix(".py")
        if mod_path.is_file():
            return str(mod_path)

        return None

    @staticmethod
    def _path_to_module(rel_path: Path) -> str:
        """Convert a relative file path to a dotted module name."""
        parts = list(rel_path.parts)
        if parts and parts[-1] == "__init__.py":
            parts = parts[:-1]
        elif parts and parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)

    def to_dict(self, report: AnalysisReport) -> dict:
        """Convert report to JSON-serializable dict."""
        return {
            "total_modules": report.total_modules,
            "total_imports": report.total_imports,
            "leaf_modules": report.leaf_modules,
            "core_modules": report.core_modules,
            "cycles": report.cycles,
            "clusters": report.clusters,
            "modules": {
                name: {
                    "path": node.path,
                    "imports": [
                        {
                            "module": imp.module_path,
                            "names": imp.names,
                            "line": imp.line_number,
                        }
                        for imp in node.imports
                    ],
                    "imported_by": node.imported_by,
                    "symbols": node.symbols,
                    "is_package": node.is_package,
                }
                for name, node in report.graph.nodes.items()
            },
        }

    def format_report(self, report: AnalysisReport) -> str:
        """Format report as human-readable markdown."""
        lines: list[str] = []
        lines.append("# Dependency Analysis Report")
        lines.append("")
        lines.append(f"**Total modules**: {report.total_modules}")
        lines.append(f"**Total imports**: {report.total_imports}")
        lines.append(f"**Clusters**: {len(report.clusters)}")
        lines.append(f"**Cycles detected**: {len(report.cycles)}")
        lines.append("")

        if report.core_modules:
            lines.append("## Core Modules (most depended-on)")
            for mod in report.core_modules:
                rev_count = len(
                    report.graph.reverse_edges.get(mod, [])
                )
                lines.append(f"- `{mod}` ({rev_count} dependents)")
            lines.append("")

        if report.leaf_modules:
            lines.append("## Leaf Modules (no dependents)")
            for mod in report.leaf_modules:
                lines.append(f"- `{mod}`")
            lines.append("")

        if report.cycles:
            lines.append("## Circular Dependencies")
            for i, cycle in enumerate(report.cycles, 1):
                lines.append(f"{i}. {' -> '.join(cycle)}")
            lines.append("")

        if report.clusters:
            lines.append("## Module Clusters")
            for name, members in report.clusters.items():
                lines.append(f"\n### {name} ({len(members)} modules)")
                for mod in members:
                    deps = len(report.graph.edges.get(mod, []))
                    lines.append(f"  - `{mod}` ({deps} dependencies)")
            lines.append("")

        return "\n".join(lines)
