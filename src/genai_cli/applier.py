"""Response parser and file applier: extract code blocks, diffs, and apply changes."""

from __future__ import annotations

import fnmatch
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from genai_cli.config import ConfigManager
from genai_cli.display import Display


@dataclass
class CodeBlock:
    """A parsed code block from an AI response."""

    file_path: str
    content: str
    language: str = ""
    is_diff: bool = False
    original_text: str = ""


class ResponseParser:
    """Parse AI responses to extract code blocks and diffs."""

    # Pattern 1: ```language:path/to/file
    _FENCED_PATTERN = re.compile(
        r"```(\w+):([^\n]+)\n(.*?)```",
        re.DOTALL,
    )

    # Pattern 2: --- a/path and +++ b/path (unified diff)
    _DIFF_PATTERN = re.compile(
        r"(---\s+a/([^\n]+)\n\+\+\+\s+b/([^\n]+)\n(?:@@[^\n]*\n(?:[+ \-].*\n?)*))",
        re.DOTALL,
    )

    # Pattern 3: FILE: path/to/file followed by content
    _FILE_MARKER_PATTERN = re.compile(
        r"FILE:\s*([^\n]+)\n(.*?)(?=\nFILE:\s|$)",
        re.DOTALL,
    )

    def parse(self, response: str) -> list[CodeBlock]:
        """Parse a response for code blocks in all 3 formats."""
        blocks: list[CodeBlock] = []
        seen_paths: set[str] = set()

        # Pattern 1: Fenced code blocks with file path
        for match in self._FENCED_PATTERN.finditer(response):
            lang = match.group(1)
            path = match.group(2).strip()
            content = match.group(3)
            if path and path not in seen_paths:
                blocks.append(CodeBlock(
                    file_path=path,
                    content=content,
                    language=lang,
                    is_diff=False,
                    original_text=match.group(0),
                ))
                seen_paths.add(path)

        # Pattern 2: Unified diffs
        for match in self._DIFF_PATTERN.finditer(response):
            diff_text = match.group(1)
            from_path = match.group(2).strip()
            to_path = match.group(3).strip()
            path = to_path or from_path
            if path and path not in seen_paths:
                blocks.append(CodeBlock(
                    file_path=path,
                    content=diff_text,
                    is_diff=True,
                    original_text=match.group(0),
                ))
                seen_paths.add(path)

        # Pattern 3: FILE: markers
        for match in self._FILE_MARKER_PATTERN.finditer(response):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if path and path not in seen_paths and content:
                blocks.append(CodeBlock(
                    file_path=path,
                    content=content,
                    is_diff=False,
                    original_text=match.group(0),
                ))
                seen_paths.add(path)

        return blocks


class FileApplier:
    """Apply code blocks to local files with safety checks."""

    def __init__(
        self,
        config: ConfigManager,
        display: Display,
        project_root: Path | None = None,
    ) -> None:
        self._config = config
        self._display = display
        self._project_root = project_root or Path.cwd()

    def validate_path(self, file_path: str) -> Path | None:
        """Validate a file path is safe to write to.

        Returns resolved Path if safe, None if rejected.
        """
        # Reject path traversal
        if ".." in file_path:
            self._display.print_error(
                f"Path traversal rejected: {file_path}"
            )
            return None

        resolved = (self._project_root / file_path).resolve()

        # Must be within project root
        try:
            resolved.relative_to(self._project_root.resolve())
        except ValueError:
            self._display.print_error(
                f"Path outside project root: {file_path}"
            )
            return None

        # Check blocked patterns
        settings = self._config.settings
        for pattern in settings.blocked_write_patterns:
            if fnmatch.fnmatch(str(resolved), pattern):
                self._display.print_error(
                    f"Blocked write pattern: {file_path}"
                )
                return None
            if fnmatch.fnmatch(resolved.name, pattern.split("/")[-1]):
                self._display.print_error(
                    f"Blocked write pattern: {file_path}"
                )
                return None

        return resolved

    def _create_backup(self, path: Path) -> Path | None:
        """Create a .bak backup of a file."""
        if not path.is_file():
            return None
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        return backup

    def _check_git_dirty(self, path: Path) -> bool:
        """Check if a file has uncommitted git changes."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", str(path)],
                capture_output=True,
                text=True,
                cwd=self._project_root,
                timeout=5,
            )
            return bool(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _apply_diff(self, path: Path, diff_content: str) -> bool:
        """Apply a unified diff to a file."""
        if not path.is_file():
            self._display.print_error(f"File not found for diff: {path}")
            return False

        original = path.read_text()
        original_lines = original.splitlines(keepends=True)

        try:
            patched = self._simple_patch(original_lines, diff_content)
            path.write_text("".join(patched))
            return True
        except Exception:
            self._display.print_error(f"Failed to apply diff to {path}")
            return False

    def _simple_patch(
        self, original_lines: list[str], diff_content: str
    ) -> list[str]:
        """Simple patch: apply +/- lines from diff."""
        result = list(original_lines)
        diff_lines = diff_content.splitlines()
        idx = 0
        offset = 0

        for dline in diff_lines:
            if dline.startswith("@@"):
                match = re.match(r"@@ -(\d+)", dline)
                if match:
                    idx = int(match.group(1)) - 1 + offset
            elif dline.startswith("-") and not dline.startswith("---"):
                if 0 <= idx < len(result):
                    result.pop(idx)
                    offset -= 1
            elif dline.startswith("+") and not dline.startswith("+++"):
                result.insert(idx, dline[1:] + "\n")
                idx += 1
                offset += 1
            elif not dline.startswith("---") and not dline.startswith("+++"):
                idx += 1

        return result

    def apply_block(
        self,
        block: CodeBlock,
        mode: str = "confirm",
    ) -> bool:
        """Apply a single code block. Returns True if applied."""
        validated = self.validate_path(block.file_path)
        if validated is None:
            return False

        # Check git dirty
        if validated.is_file() and self._check_git_dirty(validated):
            self._display.print_warning(
                f"File has uncommitted changes: {block.file_path}"
            )

        if block.is_diff:
            return self._apply_diff_block(validated, block, mode)
        else:
            return self._apply_full_block(validated, block, mode)

    def _apply_diff_block(
        self, path: Path, block: CodeBlock, mode: str
    ) -> bool:
        """Apply a diff block."""
        if mode == "dry-run":
            self._display.print_info(f"Would apply diff to: {block.file_path}")
            for line in block.content.splitlines()[:20]:
                self._display.print_info(f"  {line}")
            return False

        if mode == "confirm":
            self._display.print_info(f"\nDiff for {block.file_path}:")
            for line in block.content.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    self._display.print_info(f"  [green]{line}[/green]")
                elif line.startswith("-") and not line.startswith("---"):
                    self._display.print_info(f"  [red]{line}[/red]")
                else:
                    self._display.print_info(f"  {line}")
            if not self._display.confirm("Apply this diff?"):
                return False

        # Create backup
        if self._config.settings.create_backups:
            self._create_backup(path)

        return self._apply_diff(path, block.content)

    def _apply_full_block(
        self, path: Path, block: CodeBlock, mode: str
    ) -> bool:
        """Apply a full file replacement."""
        old_content = ""
        if path.is_file():
            old_content = path.read_text()

        if mode == "dry-run":
            self._display.print_info(f"Would write: {block.file_path}")
            if old_content:
                self._display.print_diff(
                    block.file_path, old_content, block.content
                )
            return False

        if mode == "confirm":
            if old_content:
                self._display.print_diff(
                    block.file_path, old_content, block.content
                )
            else:
                self._display.print_info(f"New file: {block.file_path}")
            if not self._display.confirm("Apply changes?"):
                return False

        # Create backup
        if path.is_file() and self._config.settings.create_backups:
            self._create_backup(path)

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        path.write_text(block.content)
        self._display.print_success(f"Applied: {block.file_path}")
        return True

    def apply_all(
        self,
        blocks: list[CodeBlock],
        mode: str = "confirm",
    ) -> list[str]:
        """Apply all code blocks. Returns list of applied file paths."""
        applied: list[str] = []
        for block in blocks:
            if self.apply_block(block, mode):
                applied.append(block.file_path)
        return applied

    def preview_changes(self, blocks: list[CodeBlock]) -> None:
        """Preview all changes without applying."""
        self.apply_all(blocks, mode="dry-run")
