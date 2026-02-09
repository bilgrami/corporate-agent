"""File bundler: discover, classify, and bundle files for upload."""

from __future__ import annotations

import fnmatch
import glob as glob_mod
import os
from pathlib import Path
from typing import Any

from genai_cli.config import ConfigManager
from genai_cli.models import FileBundle, FileTypeConfig


def _is_binary(path: Path, sample_size: int = 8192) -> bool:
    """Check if a file is binary by sampling bytes."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" in chunk
    except OSError:
        return True


def _matches_any(path: str, patterns: list[str]) -> bool:
    """Check if a path matches any of the glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        # Also check just the filename
        if fnmatch.fnmatch(Path(path).name, pattern):
            return True
    return False


class FileBundler:
    """Discovers, classifies, and bundles files for upload."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._settings = config.settings

    def classify_file(self, path: Path) -> str | None:
        """Classify a file into a type: code, docs, scripts, notebooks, or None."""
        name = path.name
        suffix = path.suffix.lower()

        for type_name, ft_config in self._settings.file_types.items():
            if suffix in ft_config.extensions:
                return type_name
            if name in ft_config.include_names:
                return type_name

        return None

    def discover_files(
        self,
        paths: list[str],
        file_type: str | None = None,
    ) -> tuple[dict[str, list[Path]], list[str]]:
        """Discover and classify files from given paths.

        Supports literal paths, directory paths, and glob patterns.

        Returns (dict of {type_name: [paths]}, list of unmatched path strings).
        """
        result: dict[str, list[Path]] = {}
        unmatched: list[str] = []
        exclude = self._settings.exclude_patterns

        for path_str in paths:
            # Try glob expansion first
            expanded = glob_mod.glob(path_str, recursive=True)
            if expanded:
                for match in expanded:
                    match_path = Path(match).resolve()
                    if match_path.is_file():
                        self._add_file(match_path, result, exclude, file_type)
                    elif match_path.is_dir():
                        self._walk_dir(match_path, result, exclude, file_type)
            else:
                # No glob match — try as literal path
                path = Path(path_str).resolve()
                if path.is_file():
                    self._add_file(path, result, exclude, file_type)
                elif path.is_dir():
                    self._walk_dir(path, result, exclude, file_type)
                else:
                    unmatched.append(path_str)

        return result, unmatched

    def _walk_dir(
        self,
        dir_path: Path,
        result: dict[str, list[Path]],
        exclude: list[str],
        file_type: str | None,
    ) -> None:
        """Walk a directory and add discovered files to result."""
        for root, dirs, files in os.walk(dir_path):
            root_path = Path(root)
            # Filter excluded directories
            rel_root = str(root_path)
            if _matches_any(rel_root, exclude):
                dirs.clear()
                continue

            # Prune excluded directory names in-place
            dirs[:] = [
                d for d in dirs
                if not _matches_any(str(root_path / d), exclude)
            ]

            for fname in files:
                fpath = root_path / fname
                self._add_file(fpath, result, exclude, file_type)

    def _add_file(
        self,
        fpath: Path,
        result: dict[str, list[Path]],
        exclude: list[str],
        file_type_filter: str | None,
    ) -> None:
        """Add a single file to the result dict if it passes filters."""
        rel_path = str(fpath)

        # Check exclusion
        if _matches_any(rel_path, exclude):
            return
        if _matches_any(fpath.name, exclude):
            return

        # Check binary
        if _is_binary(fpath):
            return

        # Classify
        ft = self.classify_file(fpath)
        if ft is None:
            return

        # Filter by requested type
        if file_type_filter and file_type_filter != "all" and ft != file_type_filter:
            return

        # Check size limit
        ft_config = self._settings.file_types.get(ft)
        if ft_config:
            max_bytes = ft_config.max_file_size_kb * 1024
            try:
                if fpath.stat().st_size > max_bytes:
                    return
            except OSError:
                return

        result.setdefault(ft, []).append(fpath)

    def bundle_files(
        self,
        paths: list[str],
        file_type: str | None = None,
        base_dir: Path | None = None,
    ) -> tuple[list[FileBundle], list[str]]:
        """Bundle discovered files into FileBundle objects per type.

        Returns (list of bundles, list of unmatched path strings).
        """
        discovered, unmatched = self.discover_files(paths, file_type)
        base = base_dir or Path.cwd()
        bundles: list[FileBundle] = []

        for ft_name, file_paths in discovered.items():
            if ft_name == "notebooks":
                content = self._bundle_notebooks(file_paths, base)
            else:
                content = self._bundle_regular(file_paths, base)

            bundle = FileBundle(
                file_type=ft_name,
                content=content,
                file_count=len(file_paths),
                file_paths=[str(p) for p in file_paths],
                estimated_tokens=self.estimate_tokens(content),
            )
            bundles.append(bundle)

        return bundles, unmatched

    def _bundle_regular(self, file_paths: list[Path], base: Path) -> str:
        """Bundle regular files with ===== FILE: markers."""
        parts: list[str] = []
        for fpath in sorted(file_paths):
            try:
                content = fpath.read_text(errors="replace")
            except OSError:
                continue

            try:
                rel = fpath.relative_to(base)
            except ValueError:
                rel = fpath

            parts.append(
                f"===== FILE: {fpath} =====\n"
                f"Relative Path: {rel}\n\n"
                f"{content}"
            )

        return "\n".join(parts)

    def _bundle_notebooks(self, file_paths: list[Path], base: Path) -> str:
        """Bundle notebook files with cell extraction."""
        import nbformat

        parts: list[str] = []
        for fpath in sorted(file_paths):
            try:
                nb = nbformat.read(str(fpath), as_version=4)
            except Exception:
                continue

            try:
                rel = fpath.relative_to(base)
            except ValueError:
                rel = fpath

            cells: list[str] = []
            for i, cell in enumerate(nb.cells, 1):
                cell_type = cell.get("cell_type", "code")
                cells.append(f"--- Cell {i} [{cell_type}] ---")
                cells.append(cell.get("source", ""))

                # Include outputs for code cells
                outputs = cell.get("outputs", [])
                for output in outputs:
                    text = output.get("text", "")
                    if text:
                        cells.append(f"--- Cell {i} [output] ---")
                        if isinstance(text, list):
                            cells.append("".join(text))
                        else:
                            cells.append(text)

            parts.append(
                f"===== NOTEBOOK: {fpath} =====\n"
                f"Relative Path: {rel}\n\n"
                + "\n".join(cells)
            )

        return "\n".join(parts)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count using tiktoken."""
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            # Fallback: ~4 chars per token
            return len(text) // 4
