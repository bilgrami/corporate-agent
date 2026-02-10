"""Tests for the refactoring operations engine."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.refactor_ops import (
    ImportUpdate,
    MoveOperation,
    RefactorEngine,
    RefactorPlan,
    RefactorResult,
)


@pytest.fixture
def display() -> Display:
    return Display(file=StringIO())


@pytest.fixture
def engine(mock_config: ConfigManager, display: Display) -> RefactorEngine:
    return RefactorEngine(mock_config, display)


class TestPlanModuleMove:
    def test_plan_simple_move(
        self, engine: RefactorEngine, tmp_path: Path
    ) -> None:
        (tmp_path / "old.py").write_text("def foo(): pass\n")
        (tmp_path / "other.py").write_text("from old import foo\n")

        with patch.object(engine, "_analyzer") as mock_analyzer:
            mock_graph = MagicMock()
            mock_graph.nodes = {}
            mock_report = MagicMock()
            mock_report.graph = mock_graph
            mock_analyzer.analyze.return_value = mock_report

            plan = engine.plan_module_move(
                "old.py", "new_dir/old.py", str(tmp_path)
            )

        assert len(plan.moves) == 1
        assert plan.moves[0].source_file == "old.py"
        assert plan.moves[0].target_file == "new_dir/old.py"

    def test_plan_creates_init(
        self, engine: RefactorEngine, tmp_path: Path
    ) -> None:
        (tmp_path / "mod.py").write_text("x = 1\n")

        with patch.object(engine, "_analyzer") as mock_analyzer:
            mock_graph = MagicMock()
            mock_graph.nodes = {}
            mock_report = MagicMock()
            mock_report.graph = mock_graph
            mock_analyzer.analyze.return_value = mock_report

            plan = engine.plan_module_move(
                "mod.py", "pkg/mod.py", str(tmp_path)
            )

        # Should plan to create __init__.py
        assert any("__init__.py" in f for f in plan.new_files)


class TestPlanSymbolMove:
    def test_plan_symbol(self, engine: RefactorEngine) -> None:
        with patch.object(engine, "_analyzer") as mock_analyzer:
            mock_graph = MagicMock()
            mock_graph.nodes = {}
            mock_report = MagicMock()
            mock_report.graph = mock_graph
            mock_analyzer.analyze.return_value = mock_report

            plan = engine.plan_symbol_move(
                "source.py", "MyClass", "target.py"
            )

        assert len(plan.moves) == 1
        assert plan.moves[0].symbol_name == "MyClass"


class TestPreviewPlan:
    def test_preview_moves(self, engine: RefactorEngine) -> None:
        plan = RefactorPlan(
            moves=[
                MoveOperation(
                    source_file="a.py",
                    target_file="b.py",
                ),
            ],
            import_updates=[
                ImportUpdate(
                    file_path="c.py",
                    old_import="from a import x",
                    new_import="from b import x",
                ),
            ],
            estimated_changes=2,
        )
        text = engine.preview_plan(plan)
        assert "Refactoring Plan" in text
        assert "a.py" in text
        assert "b.py" in text
        assert "Import Updates" in text

    def test_preview_symbol_move(self, engine: RefactorEngine) -> None:
        plan = RefactorPlan(
            moves=[
                MoveOperation(
                    source_file="src.py",
                    target_file="dst.py",
                    symbol_name="func",
                ),
            ],
            estimated_changes=1,
        )
        text = engine.preview_plan(plan)
        assert "func" in text

    def test_preview_cross_repo(self, engine: RefactorEngine) -> None:
        plan = RefactorPlan(
            moves=[
                MoveOperation(
                    source_file="mod.py",
                    target_file="mod.py",
                    source_repo="repo-a",
                    target_repo="repo-b",
                ),
            ],
            estimated_changes=1,
        )
        text = engine.preview_plan(plan)
        assert "repo-a" in text
        assert "repo-b" in text


class TestExecutePlan:
    def test_dry_run(
        self, engine: RefactorEngine, tmp_path: Path
    ) -> None:
        (tmp_path / "src.py").write_text("x = 1\n")
        plan = RefactorPlan(
            moves=[
                MoveOperation(
                    source_file=str(tmp_path / "src.py"),
                    target_file=str(tmp_path / "dst.py"),
                ),
            ],
        )
        result = engine.execute_plan(plan, mode="dry-run")
        # dry-run doesn't actually move
        assert (tmp_path / "src.py").is_file()


class TestCreateInitFiles:
    def test_creates_init(
        self, engine: RefactorEngine, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "newpkg"
        engine.create_init_files(pkg_path)
        assert (pkg_path / "__init__.py").is_file()

    def test_does_not_overwrite(
        self, engine: RefactorEngine, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "pkg"
        pkg_path.mkdir()
        init = pkg_path / "__init__.py"
        init.write_text("# existing\n")
        engine.create_init_files(pkg_path)
        assert init.read_text() == "# existing\n"


class TestGenerateAdapter:
    def test_adapter_content(self, engine: RefactorEngine) -> None:
        code = engine.generate_adapter_module(
            ["MyClass", "helper"],
            "old.module",
            "new.module",
        )
        assert "from new.module import MyClass" in code
        assert "from new.module import helper" in code
        assert "__all__" in code
        assert "backward-compat" in code.lower()
