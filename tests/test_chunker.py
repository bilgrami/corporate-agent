"""Tests for the smart context chunker."""

from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path

import pytest

from genai_cli.chunker import (
    Chunk,
    ChunkPlan,
    ContextChunker,
    FileSummary,
)
from genai_cli.config import ConfigManager
from genai_cli.display import Display


@pytest.fixture
def display() -> Display:
    return Display(file=StringIO())


@pytest.fixture
def chunker(mock_config: ConfigManager, display: Display) -> ContextChunker:
    return ContextChunker(mock_config, display)


class TestSummarizeFile:
    def test_summarize_python(
        self, chunker: ContextChunker, tmp_path: Path
    ) -> None:
        f = tmp_path / "example.py"
        f.write_text(
            '"""Example module."""\n'
            "import os\n"
            "\ndef hello(name: str) -> str:\n"
            '    return f"Hello {name}"\n'
            "\nclass Greeter:\n"
            "    def greet(self): pass\n"
        )
        summary = chunker.summarize_file(f)
        assert summary.module_name == "example"
        assert summary.line_count > 0
        assert summary.estimated_tokens > 0
        assert any("hello" in s for s in summary.signatures)
        assert any("Greeter" in s for s in summary.signatures)
        assert "os" in summary.imports
        assert "Example module." in summary.docstring

    def test_summarize_syntax_error(
        self, chunker: ContextChunker, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n")
        summary = chunker.summarize_file(f)
        assert summary.module_name == "bad"
        assert summary.signatures == []

    def test_summarize_missing_file(
        self, chunker: ContextChunker, tmp_path: Path
    ) -> None:
        f = tmp_path / "missing.py"
        summary = chunker.summarize_file(f)
        assert summary.path == str(f)


class TestExtractSignatures:
    def test_function_with_return_type(
        self, chunker: ContextChunker
    ) -> None:
        source = "def add(a: int, b: int) -> int:\n    return a + b\n"
        tree = ast.parse(source)
        sigs = chunker._extract_signatures(tree)
        assert len(sigs) == 1
        assert "add" in sigs[0]
        assert "-> int" in sigs[0]

    def test_class_with_methods(self, chunker: ContextChunker) -> None:
        source = (
            "class Foo(Base):\n"
            "    def bar(self): pass\n"
            "    async def baz(self): pass\n"
        )
        tree = ast.parse(source)
        sigs = chunker._extract_signatures(tree)
        assert any("Foo" in s for s in sigs)
        assert any("bar" in s for s in sigs)
        assert any("async" in s for s in sigs)


class TestChunkCodebase:
    def test_single_chunk(
        self, chunker: ContextChunker, tmp_path: Path
    ) -> None:
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")

        plan = chunker.chunk_codebase(
            [str(tmp_path)], token_budget=100000
        )
        assert plan.total_files == 2
        assert len(plan.chunks) >= 1

    def test_small_budget_splits(
        self, chunker: ContextChunker, tmp_path: Path
    ) -> None:
        (tmp_path / "big1.py").write_text("x = 1\n" * 500)
        (tmp_path / "big2.py").write_text("y = 2\n" * 500)

        plan = chunker.chunk_codebase(
            [str(tmp_path)], token_budget=100
        )
        # With a tiny budget, files should be in separate chunks
        assert len(plan.chunks) >= 2

    def test_empty_paths(self, chunker: ContextChunker) -> None:
        plan = chunker.chunk_codebase(
            ["/nonexistent"], token_budget=100000
        )
        assert plan.total_files == 0
        assert plan.chunks == []


class TestPrioritizeFiles:
    def test_init_gets_high_score(
        self, chunker: ContextChunker, tmp_path: Path
    ) -> None:
        init = tmp_path / "__init__.py"
        init.write_text("")
        other = tmp_path / "something_long_name.py"
        other.write_text("x = 1\n")

        scored = chunker.prioritize_files(
            [str(init), str(other)], tmp_path
        )
        # __init__.py should score higher
        assert scored[0][0] == str(init) or scored[0][1] >= scored[1][1]

    def test_empty_list(self, chunker: ContextChunker) -> None:
        scored = chunker.prioritize_files([], Path("."))
        assert scored == []


class TestSummarizeCodebase:
    def test_basic_summary(
        self, chunker: ContextChunker, tmp_path: Path
    ) -> None:
        (tmp_path / "mod.py").write_text(
            '"""A module."""\ndef func(): pass\n'
        )
        result = chunker.summarize_codebase(
            [str(tmp_path)], token_budget=100000
        )
        assert "Codebase Summary" in result
        assert "func" in result
