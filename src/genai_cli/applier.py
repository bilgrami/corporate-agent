"""Response parser and file applier: extract code blocks, diffs, and apply changes."""

from __future__ import annotations

import fnmatch
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from genai_cli.config import ConfigManager
from genai_cli.display import Display


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CodeBlock:
    """A parsed code block from an AI response (legacy formats)."""

    file_path: str
    content: str
    language: str = ""
    is_diff: bool = False
    original_text: str = ""


@dataclass
class EditBlock:
    """A single SEARCH/REPLACE edit parsed from an AI response."""

    file_path: str
    search_content: str
    replace_content: str
    original_text: str = ""

    @property
    def is_create(self) -> bool:
        """Empty SEARCH means create a new file."""
        return self.search_content == ""

    @property
    def is_delete(self) -> bool:
        """Empty REPLACE with non-empty SEARCH means delete matched content."""
        return self.replace_content == "" and self.search_content != ""


@dataclass
class ApplyResult:
    """Result of applying a single edit or code block."""

    file_path: str
    success: bool
    error_message: str = ""
    file_content_snippet: str = ""


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


class SearchReplaceParser:
    """Parse SEARCH/REPLACE blocks from AI responses.

    Format:
        path/to/file.py
        <<<<<<< SEARCH
        existing content
        =======
        replacement content
        >>>>>>> REPLACE
    """

    _SEARCH_MARKER = "<<<<<<< SEARCH"
    _DIVIDER = "======="
    _REPLACE_MARKER = ">>>>>>> REPLACE"

    def parse(self, response: str) -> list[EditBlock]:
        """Parse response for SEARCH/REPLACE blocks using a state machine."""
        blocks: list[EditBlock] = []
        lines = response.splitlines(keepends=True)
        total = len(lines)
        i = 0

        while i < total:
            # Look for a file path line followed by <<<<<<< SEARCH
            stripped = lines[i].rstrip("\n\r")

            if (
                i + 1 < total
                and lines[i + 1].rstrip("\n\r") == self._SEARCH_MARKER
                and stripped
                and not stripped.startswith(" ")
                and not stripped.startswith("\t")
                and stripped != self._SEARCH_MARKER
                and stripped != self._DIVIDER
                and stripped != self._REPLACE_MARKER
            ):
                file_path = stripped.strip()
                original_start = i
                i += 2  # skip path line and <<<<<<< SEARCH

                # Collect SEARCH content
                search_lines: list[str] = []
                while i < total:
                    sl = lines[i].rstrip("\n\r")
                    if sl == self._DIVIDER:
                        i += 1
                        break
                    search_lines.append(lines[i])
                    i += 1
                else:
                    # Incomplete block — no =======
                    continue

                # Collect REPLACE content
                replace_lines: list[str] = []
                found_end = False
                while i < total:
                    rl = lines[i].rstrip("\n\r")
                    if rl == self._REPLACE_MARKER:
                        found_end = True
                        i += 1
                        break
                    replace_lines.append(lines[i])
                    i += 1

                if not found_end:
                    # Incomplete block — no >>>>>>> REPLACE
                    continue

                search_content = "".join(search_lines)
                replace_content = "".join(replace_lines)

                # Strip a single trailing newline that comes from the
                # line break before the ======= / >>>>>>> marker
                if search_content.endswith("\n"):
                    search_content = search_content[:-1]
                if replace_content.endswith("\n"):
                    replace_content = replace_content[:-1]

                original_text = "".join(lines[original_start:i])

                blocks.append(EditBlock(
                    file_path=file_path,
                    search_content=search_content,
                    replace_content=replace_content,
                    original_text=original_text,
                ))
            else:
                i += 1

        return blocks


class ResponseParser:
    """Parse AI responses to extract code blocks and diffs (legacy formats)."""

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


class UnifiedParser:
    """Try SEARCH/REPLACE first, fall back to legacy patterns."""

    def __init__(self) -> None:
        self._sr_parser = SearchReplaceParser()
        self._legacy_parser = ResponseParser()

    def parse(
        self, response: str
    ) -> tuple[list[EditBlock], list[CodeBlock]]:
        """Parse response, preferring SEARCH/REPLACE over legacy.

        Returns (edit_blocks, legacy_blocks).
        If SEARCH/REPLACE blocks are found, legacy_blocks will be empty.
        """
        edits = self._sr_parser.parse(response)
        if edits:
            return edits, []
        legacy = self._legacy_parser.parse(response)
        return [], legacy


# ---------------------------------------------------------------------------
# File applier
# ---------------------------------------------------------------------------


def _truncate_content(content: str, max_lines: int = 200) -> str:
    """Truncate file content for error feedback."""
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content
    half = max_lines // 2
    head = lines[:half]
    tail = lines[-half:]
    omitted = len(lines) - max_lines
    return "\n".join(head + [f"... ({omitted} lines omitted) ..."] + tail)


def _normalize_trailing_ws(text: str) -> str:
    """Strip trailing whitespace from each line."""
    return "\n".join(line.rstrip() for line in text.splitlines())


def _normalize_indent(text: str) -> str:
    """Strip leading whitespace from each line."""
    return "\n".join(line.lstrip() for line in text.splitlines())


class FileApplier:
    """Apply code blocks and SEARCH/REPLACE edits to local files."""

    def __init__(
        self,
        config: ConfigManager,
        display: Display,
        project_root: Path | None = None,
    ) -> None:
        self._config = config
        self._display = display
        self._project_root = project_root or Path.cwd()

    # --- Path validation ---

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

    # --- Helpers ---

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

    # --- SEARCH/REPLACE application ---

    def _find_search_content(
        self, file_content: str, search_content: str
    ) -> tuple[int, int] | None:
        """Find SEARCH content in file using three-tier matching.

        Returns (start, end) character offsets or None if not found.
        """
        # Tier 1: Exact match
        idx = file_content.find(search_content)
        if idx != -1:
            return idx, idx + len(search_content)

        # Tier 2: Whitespace-normalized (trailing whitespace stripped)
        norm_file = _normalize_trailing_ws(file_content)
        norm_search = _normalize_trailing_ws(search_content)
        idx = norm_file.find(norm_search)
        if idx != -1:
            # Map back to original offsets.  Build a mapping from
            # normalized char positions to original line boundaries.
            file_lines = file_content.splitlines(keepends=True)
            norm_lines = norm_file.splitlines(keepends=True)
            # Find which normalized line the match starts on
            char_count = 0
            start_line = 0
            for li, nl in enumerate(norm_lines):
                if char_count + len(nl) > idx:
                    start_line = li
                    break
                char_count += len(nl)
            # Count how many lines the search spans
            search_line_count = len(norm_search.splitlines())
            end_line = start_line + search_line_count
            # Map back to original char offsets
            orig_start = sum(len(fl) for fl in file_lines[:start_line])
            orig_end = sum(len(fl) for fl in file_lines[:end_line])
            return orig_start, orig_end

        # Tier 3: Indent-normalized (leading whitespace stripped)
        indent_file = _normalize_indent(file_content)
        indent_search = _normalize_indent(search_content)
        idx = indent_file.find(indent_search)
        if idx != -1:
            file_lines = file_content.splitlines(keepends=True)
            indent_lines = indent_file.splitlines(keepends=True)
            char_count = 0
            start_line = 0
            for li, il in enumerate(indent_lines):
                if char_count + len(il) > idx:
                    start_line = li
                    break
                char_count += len(il)
            search_line_count = len(indent_search.splitlines())
            end_line = start_line + search_line_count
            orig_start = sum(len(fl) for fl in file_lines[:start_line])
            orig_end = sum(len(fl) for fl in file_lines[:end_line])
            return orig_start, orig_end

        return None

    def _apply_search_replace(
        self, path: Path, edit: EditBlock, mode: str
    ) -> ApplyResult:
        """Apply a single SEARCH/REPLACE edit to a file."""
        file_path_str = edit.file_path

        # CREATE: empty SEARCH means create/overwrite
        if edit.is_create:
            if mode == "dry-run":
                self._display.print_info(f"Would create: {file_path_str}")
                return ApplyResult(file_path=file_path_str, success=False)

            if mode == "confirm":
                self._display.print_info(f"New file: {file_path_str}")
                if not self._display.confirm("Create this file?"):
                    return ApplyResult(file_path=file_path_str, success=False)

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(edit.replace_content)
            self._display.print_success(f"Created: {file_path_str}")
            return ApplyResult(file_path=file_path_str, success=True)

        # EDIT / DELETE: file must exist
        if not path.is_file():
            return ApplyResult(
                file_path=file_path_str,
                success=False,
                error_message=f"File not found: {file_path_str}",
            )

        file_content = path.read_text()

        # Find SEARCH content in file
        match = self._find_search_content(file_content, edit.search_content)
        if match is None:
            snippet = _truncate_content(file_content)
            return ApplyResult(
                file_path=file_path_str,
                success=False,
                error_message=(
                    f"SEARCH block not found in {file_path_str}. "
                    "The content does not match the file."
                ),
                file_content_snippet=snippet,
            )

        start, end = match
        new_content = file_content[:start] + edit.replace_content + file_content[end:]

        if mode == "dry-run":
            self._display.print_info(f"Would edit: {file_path_str}")
            self._display.print_diff(file_path_str, file_content, new_content)
            return ApplyResult(file_path=file_path_str, success=False)

        if mode == "confirm":
            self._display.print_diff(file_path_str, file_content, new_content)
            if not self._display.confirm("Apply this edit?"):
                return ApplyResult(file_path=file_path_str, success=False)

        # Create backup
        if self._config.settings.create_backups:
            self._create_backup(path)

        path.write_text(new_content)
        action = "Deleted content from" if edit.is_delete else "Edited"
        self._display.print_success(f"{action}: {file_path_str}")
        return ApplyResult(file_path=file_path_str, success=True)

    def apply_edits(
        self,
        edits: list[EditBlock],
        mode: str = "confirm",
    ) -> list[ApplyResult]:
        """Apply all SEARCH/REPLACE edits. Returns list of ApplyResult."""
        results: list[ApplyResult] = []
        for edit in edits:
            validated = self.validate_path(edit.file_path)
            if validated is None:
                results.append(ApplyResult(
                    file_path=edit.file_path,
                    success=False,
                    error_message=f"Path validation failed: {edit.file_path}",
                ))
                continue

            # Check git dirty
            if validated.is_file() and self._check_git_dirty(validated):
                self._display.print_warning(
                    f"File has uncommitted changes: {edit.file_path}"
                )

            result = self._apply_search_replace(validated, edit, mode)
            results.append(result)
        return results

    # --- Legacy code block application ---

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
    ) -> list[ApplyResult]:
        """Apply all code blocks. Returns list of ApplyResult."""
        results: list[ApplyResult] = []
        for block in blocks:
            success = self.apply_block(block, mode)
            results.append(ApplyResult(
                file_path=block.file_path,
                success=success,
                error_message="" if success else f"Failed to apply: {block.file_path}",
            ))
        return results

    def preview_changes(self, blocks: list[CodeBlock]) -> None:
        """Preview all changes without applying."""
        self.apply_all(blocks, mode="dry-run")
