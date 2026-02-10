"""Smart context chunker for fitting codebases into AI context windows."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path

from genai_cli.bundler import FileBundler
from genai_cli.config import ConfigManager
from genai_cli.display import Display


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FileSummary:
    """Summary of a single file."""

    path: str
    module_name: str
    signatures: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    docstring: str = ""
    line_count: int = 0
    estimated_tokens: int = 0


@dataclass
class Chunk:
    """A chunk of files that fits within a token budget."""

    chunk_id: int = 0
    files: list[str] = field(default_factory=list)
    content: str = ""
    estimated_tokens: int = 0
    relevance_score: float = 0.0


@dataclass
class ChunkPlan:
    """Plan for chunking a codebase."""

    total_files: int = 0
    total_tokens: int = 0
    token_budget: int = 0
    chunks: list[Chunk] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------


class ContextChunker:
    """Smart chunker that fits codebases into AI context windows."""

    def __init__(self, config: ConfigManager, display: Display) -> None:
        self._config = config
        self._display = display
        self._bundler = FileBundler(config)

    def summarize_file(self, file_path: Path) -> FileSummary:
        """Summarize a file using AST to extract signatures only."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return FileSummary(path=str(file_path), module_name="")

        module_name = file_path.stem
        line_count = len(source.splitlines())
        estimated_tokens = self._estimate_tokens(source)

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            return FileSummary(
                path=str(file_path),
                module_name=module_name,
                line_count=line_count,
                estimated_tokens=estimated_tokens,
            )

        signatures = self._extract_signatures(tree)
        imports = self._extract_import_strings(tree)
        docstring = ast.get_docstring(tree) or ""

        return FileSummary(
            path=str(file_path),
            module_name=module_name,
            signatures=signatures,
            imports=imports,
            docstring=docstring,
            line_count=line_count,
            estimated_tokens=estimated_tokens,
        )

    def summarize_codebase(
        self, paths: list[str], token_budget: int | None = None
    ) -> str:
        """Create a fits-in-one-shot overview of the codebase."""
        budget = token_budget or self._default_budget()
        py_files = self._discover_python_files(paths)

        summaries: list[FileSummary] = []
        for fpath in py_files:
            summaries.append(self.summarize_file(fpath))

        lines: list[str] = ["# Codebase Summary", ""]
        lines.append(f"**Files**: {len(summaries)}")
        total_lines = sum(s.line_count for s in summaries)
        lines.append(f"**Total lines**: {total_lines:,}")
        lines.append("")

        for summary in sorted(summaries, key=lambda s: s.path):
            lines.append(f"## {summary.path}")
            if summary.docstring:
                lines.append(
                    f"  {summary.docstring.split(chr(10))[0]}"
                )
            if summary.imports:
                lines.append(
                    f"  Imports: {', '.join(summary.imports[:5])}"
                )
            if summary.signatures:
                for sig in summary.signatures:
                    lines.append(f"  - {sig}")
            lines.append("")

        result = "\n".join(lines)

        if self._estimate_tokens(result) > budget:
            result = self._truncate_to_budget(result, budget)

        return result

    def chunk_codebase(
        self, paths: list[str], token_budget: int | None = None
    ) -> ChunkPlan:
        """Split codebase into chunks using greedy bin-packing."""
        budget = token_budget or self._default_budget()
        py_files = self._discover_python_files(paths)

        if not py_files:
            return ChunkPlan(token_budget=budget)

        root = Path(paths[0]).resolve() if paths else Path.cwd()
        scored = self.prioritize_files(
            [str(f) for f in py_files], root
        )

        chunks: list[Chunk] = []
        current_chunk = Chunk(chunk_id=0)

        for fpath_str, score in scored:
            fpath = Path(fpath_str)
            try:
                content = fpath.read_text(
                    encoding="utf-8", errors="replace"
                )
            except OSError:
                continue

            tokens = self._estimate_tokens(content)

            if current_chunk.estimated_tokens + tokens > budget:
                if current_chunk.files:
                    chunks.append(current_chunk)
                current_chunk = Chunk(chunk_id=len(chunks))

            current_chunk.files.append(fpath_str)
            current_chunk.content += (
                f"\n===== FILE: {fpath_str} =====\n{content}\n"
            )
            current_chunk.estimated_tokens += tokens
            current_chunk.relevance_score = max(
                current_chunk.relevance_score, score
            )

        if current_chunk.files:
            chunks.append(current_chunk)

        total_tokens = sum(c.estimated_tokens for c in chunks)

        return ChunkPlan(
            total_files=len(py_files),
            total_tokens=total_tokens,
            token_budget=budget,
            chunks=chunks,
            summary=f"{len(chunks)} chunks, {total_tokens:,} tokens total",
        )

    def prioritize_files(
        self, paths: list[str], root_dir: Path | str
    ) -> list[tuple[str, float]]:
        """Score files: 0.4*centrality + 0.3*recency + 0.3*(1-size)."""
        root = Path(root_dir).resolve()

        if not paths:
            return []

        stats: list[dict] = []
        for p in paths:
            fpath = Path(p)
            try:
                stat = fpath.stat()
                stats.append(
                    {"path": p, "mtime": stat.st_mtime, "size": stat.st_size}
                )
            except OSError:
                stats.append({"path": p, "mtime": 0.0, "size": 0})

        if not stats:
            return [(p, 0.5) for p in paths]

        mtimes = [s["mtime"] for s in stats]
        min_mt = min(mtimes) if mtimes else 0
        max_mt = max(mtimes) if mtimes else 1
        mt_range = max_mt - min_mt if max_mt > min_mt else 1.0

        sizes = [s["size"] for s in stats]
        max_size = max(sizes) if sizes else 1
        max_size = max_size or 1

        scored: list[tuple[str, float]] = []
        for s in stats:
            fpath = Path(s["path"])

            centrality = 0.5
            if fpath.name == "__init__.py":
                centrality = 1.0
            elif fpath.name in (
                "models.py",
                "config.py",
                "utils.py",
                "base.py",
            ):
                centrality = 0.8
            elif len(fpath.stem) < 8:
                centrality = 0.6

            recency = (s["mtime"] - min_mt) / mt_range
            size_score = 1.0 - (s["size"] / max_size)

            composite = 0.4 * centrality + 0.3 * recency + 0.3 * size_score
            scored.append((s["path"], composite))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _extract_signatures(self, tree: ast.AST) -> list[str]:
        """Extract function and class signatures without bodies."""
        signatures: list[str] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                bases = (
                    ", ".join(ast.unparse(b) for b in node.bases)
                    if node.bases
                    else ""
                )
                sig = (
                    f"class {node.name}({bases})"
                    if bases
                    else f"class {node.name}"
                )
                signatures.append(sig)
                for item in node.body:
                    if isinstance(
                        item, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ):
                        args = ast.unparse(item.args)
                        prefix = (
                            "async "
                            if isinstance(item, ast.AsyncFunctionDef)
                            else ""
                        )
                        signatures.append(
                            f"  {prefix}def {item.name}({args})"
                        )
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                args = ast.unparse(node.args)
                prefix = (
                    "async "
                    if isinstance(node, ast.AsyncFunctionDef)
                    else ""
                )
                ret = ""
                if node.returns:
                    ret = f" -> {ast.unparse(node.returns)}"
                signatures.append(f"{prefix}def {node.name}({args}){ret}")

        return signatures

    def _extract_import_strings(self, tree: ast.AST) -> list[str]:
        """Extract import module names as strings."""
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def _estimate_tokens(self, text: str) -> int:
        """Delegate to FileBundler's token estimation."""
        return FileBundler.estimate_tokens(text)

    def _default_budget(self) -> int:
        """Default token budget: 70% of current model's context window."""
        model = self._config.get_model(
            self._config.settings.default_model
        )
        if model:
            return int(model.context_window * 0.7)
        return 89600  # 128000 * 0.7

    def _discover_python_files(self, paths: list[str]) -> list[Path]:
        """Discover Python files from paths."""
        py_files: list[Path] = []
        for path_str in paths:
            path = Path(path_str)
            if path.is_file() and path.suffix == ".py":
                py_files.append(path.resolve())
            elif path.is_dir():
                for fpath in sorted(path.rglob("*.py")):
                    py_files.append(fpath.resolve())
        return py_files

    def _truncate_to_budget(self, text: str, budget: int) -> str:
        """Truncate text to fit within token budget."""
        lines = text.splitlines()
        result_lines: list[str] = []
        current_tokens = 0

        for line in lines:
            line_tokens = self._estimate_tokens(line)
            if current_tokens + line_tokens > budget:
                result_lines.append(
                    "... (truncated to fit token budget)"
                )
                break
            result_lines.append(line)
            current_tokens += line_tokens

        return "\n".join(result_lines)
