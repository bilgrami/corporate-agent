"""Refactoring operations engine for module and symbol moves."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from genai_cli.analyzer import DependencyAnalyzer
from genai_cli.applier import EditBlock, FileApplier
from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.workspace import WorkspaceManager


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class MoveOperation:
    """A single file/symbol move operation."""

    source_file: str
    target_file: str
    symbol_name: str = ""
    source_repo: str = ""
    target_repo: str = ""


@dataclass
class ImportUpdate:
    """An import statement that needs updating."""

    file_path: str
    old_import: str
    new_import: str
    line_number: int = 0


@dataclass
class RefactorPlan:
    """Complete plan for a refactoring operation."""

    moves: list[MoveOperation] = field(default_factory=list)
    import_updates: list[ImportUpdate] = field(default_factory=list)
    new_files: list[str] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    estimated_changes: int = 0


@dataclass
class RefactorResult:
    """Result of executing a refactor plan."""

    success: bool
    moves_completed: int = 0
    moves_failed: int = 0
    imports_updated: int = 0
    imports_failed: int = 0
    files_created: int = 0
    error_messages: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class RefactorEngine:
    """Engine for planning and executing code refactoring operations."""

    def __init__(
        self,
        config: ConfigManager,
        display: Display,
        workspace: WorkspaceManager | None = None,
    ) -> None:
        self._config = config
        self._display = display
        self._workspace = workspace
        self._analyzer = DependencyAnalyzer(config, display)
        self._applier = FileApplier(config, display)

    # --- Planning ---

    def plan_module_move(
        self, source: str, target: str, root: str | None = None
    ) -> RefactorPlan:
        """Plan moving an entire module file to a new location."""
        root_dir = Path(root) if root else Path.cwd()
        source_path = Path(source)
        target_path = Path(target)

        plan = RefactorPlan()
        plan.moves.append(
            MoveOperation(
                source_file=str(source_path),
                target_file=str(target_path),
            )
        )

        old_module = self._path_to_module(source_path, root_dir)
        new_module = self._path_to_module(target_path, root_dir)

        report = self._analyzer.analyze([str(root_dir)], str(root_dir))
        import_updates = self._compute_import_updates(
            old_module, new_module, report.graph, root_dir
        )
        plan.import_updates = import_updates
        plan.affected_files = list(
            {u.file_path for u in import_updates}
        )
        plan.estimated_changes = len(plan.moves) + len(import_updates)

        target_dir = target_path.parent
        init_file = target_dir / "__init__.py"
        if not init_file.exists() and str(target_dir) != ".":
            plan.new_files.append(str(init_file))

        return plan

    def plan_symbol_move(
        self,
        source_file: str,
        symbol: str,
        target_file: str,
    ) -> RefactorPlan:
        """Plan moving a single symbol (function/class) between files."""
        plan = RefactorPlan()
        plan.moves.append(
            MoveOperation(
                source_file=source_file,
                target_file=target_file,
                symbol_name=symbol,
            )
        )

        root_dir = Path.cwd()
        old_module = self._path_to_module(Path(source_file), root_dir)
        new_module = self._path_to_module(Path(target_file), root_dir)

        report = self._analyzer.analyze([str(root_dir)], str(root_dir))
        import_updates = self._compute_import_updates(
            old_module,
            new_module,
            report.graph,
            root_dir,
            symbol_name=symbol,
        )
        plan.import_updates = import_updates
        plan.affected_files = list(
            {u.file_path for u in import_updates}
            | {source_file, target_file}
        )
        plan.estimated_changes = len(plan.moves) + len(import_updates)

        return plan

    def plan_cross_repo_move(
        self,
        source_repo: str,
        source_path: str,
        target_repo: str,
        target_path: str,
    ) -> RefactorPlan:
        """Plan moving files between repos in a workspace."""
        plan = RefactorPlan()
        plan.moves.append(
            MoveOperation(
                source_file=source_path,
                target_file=target_path,
                source_repo=source_repo,
                target_repo=target_repo,
            )
        )
        plan.estimated_changes = 1
        return plan

    # --- Execution ---

    def execute_plan(
        self, plan: RefactorPlan, mode: str = "confirm"
    ) -> RefactorResult:
        """Execute a refactoring plan."""
        result = RefactorResult(success=True)

        # Create new files (e.g., __init__.py)
        for new_file in plan.new_files:
            self.create_init_files(Path(new_file).parent)
            result.files_created += 1

        # Execute moves
        for move in plan.moves:
            if move.source_repo and move.target_repo and self._workspace:
                ok = self._workspace.move_file(
                    move.source_repo,
                    move.source_file,
                    move.target_repo,
                    move.target_file,
                )
                if ok:
                    result.moves_completed += 1
                else:
                    result.moves_failed += 1
                    result.error_messages.append(
                        f"Failed to move {move.source_file}"
                    )
            elif move.symbol_name:
                ok = self._move_symbol(move, mode)
                if ok:
                    result.moves_completed += 1
                else:
                    result.moves_failed += 1
                    result.error_messages.append(
                        f"Failed to move symbol {move.symbol_name}"
                    )
            else:
                ok = self._move_file(move, mode)
                if ok:
                    result.moves_completed += 1
                else:
                    result.moves_failed += 1
                    result.error_messages.append(
                        f"Failed to move {move.source_file}"
                    )

        # Apply import updates
        root_dir = Path.cwd()
        for update in plan.import_updates:
            ok = self._apply_import_update(update, root_dir)
            if ok:
                result.imports_updated += 1
            else:
                result.imports_failed += 1
                result.error_messages.append(
                    f"Failed to update import in {update.file_path}"
                )

        result.success = (
            result.moves_failed == 0 and result.imports_failed == 0
        )
        return result

    def preview_plan(self, plan: RefactorPlan) -> str:
        """Format a plan for human review."""
        lines: list[str] = ["# Refactoring Plan", ""]

        if plan.moves:
            lines.append("## Moves")
            for move in plan.moves:
                if move.symbol_name:
                    lines.append(
                        f"- Move `{move.symbol_name}` from "
                        f"`{move.source_file}` to `{move.target_file}`"
                    )
                else:
                    src = move.source_file
                    if move.source_repo:
                        src = f"{move.source_repo}:{src}"
                    tgt = move.target_file
                    if move.target_repo:
                        tgt = f"{move.target_repo}:{tgt}"
                    lines.append(f"- Move `{src}` -> `{tgt}`")
            lines.append("")

        if plan.import_updates:
            lines.append("## Import Updates")
            for update in plan.import_updates:
                lines.append(
                    f"- `{update.file_path}`: "
                    f"`{update.old_import}` -> `{update.new_import}`"
                )
            lines.append("")

        if plan.new_files:
            lines.append("## New Files")
            for f in plan.new_files:
                lines.append(f"- `{f}`")
            lines.append("")

        lines.append(
            f"**Estimated changes**: {plan.estimated_changes}"
        )
        lines.append(
            f"**Affected files**: {len(plan.affected_files)}"
        )

        return "\n".join(lines)

    # --- Import rewriting ---

    def _compute_import_updates(
        self,
        old_module: str,
        new_module: str,
        graph,
        root_dir: Path,
        symbol_name: str = "",
    ) -> list[ImportUpdate]:
        """Compute all import updates needed for a module move."""
        updates: list[ImportUpdate] = []

        for mod_name, node in graph.nodes.items():
            for imp in node.imports:
                if imp.module_path == old_module or (
                    imp.module_path.startswith(old_module + ".")
                ):
                    if symbol_name and imp.names:
                        if symbol_name not in imp.names:
                            continue

                    new_import_path = imp.module_path.replace(
                        old_module, new_module, 1
                    )

                    if imp.is_from_import:
                        names_str = ", ".join(imp.names)
                        old_stmt = f"from {imp.module_path} import {names_str}"
                        new_stmt = f"from {new_import_path} import {names_str}"
                    else:
                        old_stmt = f"import {imp.module_path}"
                        new_stmt = f"import {new_import_path}"

                    updates.append(
                        ImportUpdate(
                            file_path=node.path,
                            old_import=old_stmt,
                            new_import=new_stmt,
                            line_number=imp.line_number,
                        )
                    )

        return updates

    def _apply_import_update(
        self, update: ImportUpdate, root_dir: Path
    ) -> bool:
        """Apply a single import update using EditBlock."""
        file_path = Path(update.file_path)
        if not file_path.is_file():
            return False

        try:
            rel = file_path.relative_to(root_dir)
        except ValueError:
            rel = file_path

        edit = EditBlock(
            file_path=str(rel),
            search_content=update.old_import,
            replace_content=update.new_import,
        )
        results = self._applier.apply_edits([edit], mode="auto")
        return bool(results and results[0].success)

    # --- File operations ---

    def _move_file(self, move: MoveOperation, mode: str) -> bool:
        """Move an entire file."""
        src = Path(move.source_file)
        tgt = Path(move.target_file)

        if not src.is_file():
            self._display.print_error(
                f"Source file not found: {move.source_file}"
            )
            return False

        if mode == "dry-run":
            self._display.print_info(
                f"Would move: {move.source_file} -> {move.target_file}"
            )
            return False

        if mode == "confirm":
            if not self._display.confirm(
                f"Move {move.source_file} -> {move.target_file}?"
            ):
                return False

        tgt.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.move(str(src), str(tgt))
        self._display.print_success(
            f"Moved: {move.source_file} -> {move.target_file}"
        )
        return True

    def _move_symbol(self, move: MoveOperation, mode: str) -> bool:
        """Move a single symbol between files."""
        src = Path(move.source_file)
        tgt = Path(move.target_file)

        if not src.is_file():
            self._display.print_error(
                f"Source file not found: {move.source_file}"
            )
            return False

        source_code = src.read_text()
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            self._display.print_error(
                f"Syntax error in {move.source_file}"
            )
            return False

        symbol_code = None
        for node in ast.iter_child_nodes(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ) and node.name == move.symbol_name:
                symbol_code = ast.get_source_segment(source_code, node)
                break

        if not symbol_code:
            self._display.print_error(
                f"Symbol '{move.symbol_name}' not found in "
                f"{move.source_file}"
            )
            return False

        if mode == "dry-run":
            self._display.print_info(
                f"Would move symbol '{move.symbol_name}' "
                f"from {move.source_file} to {move.target_file}"
            )
            return False

        if mode == "confirm":
            if not self._display.confirm(
                f"Move '{move.symbol_name}' from "
                f"{move.source_file} to {move.target_file}?"
            ):
                return False

        # Append to target
        tgt.parent.mkdir(parents=True, exist_ok=True)
        existing = tgt.read_text() if tgt.is_file() else ""
        separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
        tgt.write_text(existing + separator + symbol_code + "\n")

        # Remove from source
        new_source = source_code.replace(symbol_code, "").strip() + "\n"
        src.write_text(new_source)

        self._display.print_success(
            f"Moved symbol '{move.symbol_name}' to {move.target_file}"
        )
        return True

    # --- File generation ---

    def create_init_files(self, package_path: Path) -> None:
        """Create __init__.py files for a package path."""
        package_path.mkdir(parents=True, exist_ok=True)
        init_file = package_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")

    def generate_adapter_module(
        self,
        moved_symbols: list[str],
        old_location: str,
        new_location: str,
    ) -> str:
        """Generate backward-compat re-export shim."""
        lines: list[str] = [
            f'"""Backward-compatibility shim.',
            f"",
            f"Symbols have been moved to {new_location}.",
            f'"""',
            f"",
        ]

        for symbol in moved_symbols:
            lines.append(
                f"from {new_location} import {symbol}  # noqa: F401"
            )

        lines.append("")
        lines.append(
            f"__all__ = {moved_symbols!r}"
        )
        lines.append("")
        return "\n".join(lines)

    # --- Helpers ---

    @staticmethod
    def _path_to_module(file_path: Path, root_dir: Path) -> str:
        """Convert a file path to a dotted module name."""
        try:
            rel = file_path.relative_to(root_dir)
        except ValueError:
            rel = file_path

        parts = list(rel.parts)
        if parts and parts[-1] == "__init__.py":
            parts = parts[:-1]
        elif parts and parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)
