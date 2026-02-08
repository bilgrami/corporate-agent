"""Tests for response parser and file applier."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from genai_cli.applier import ApplyResult, CodeBlock, FileApplier, ResponseParser
from genai_cli.config import ConfigManager
from genai_cli.display import Display


@pytest.fixture
def parser() -> ResponseParser:
    return ResponseParser()


@pytest.fixture
def applier_config(tmp_path: Path) -> ConfigManager:
    settings = {
        "api_base_url": "https://api.test.com",
        "create_backups": True,
        "blocked_write_patterns": [
            "**/.env",
            "**/*.pem",
            "**/*.key",
            "**/*.secret*",
        ],
    }
    p = tmp_path / "settings.yaml"
    p.write_text(yaml.dump(settings))
    return ConfigManager(config_path=str(p))


@pytest.fixture
def display() -> Display:
    return Display(file=StringIO())


@pytest.fixture
def applier(
    applier_config: ConfigManager, display: Display, tmp_path: Path
) -> FileApplier:
    return FileApplier(applier_config, display, project_root=tmp_path)


# --- ResponseParser Tests ---


class TestParserFenced:
    def test_parse_fenced_python(self, parser: ResponseParser) -> None:
        response = '```python:src/main.py\ndef hello():\n    pass\n```'
        blocks = parser.parse(response)
        assert len(blocks) == 1
        assert blocks[0].file_path == "src/main.py"
        assert blocks[0].language == "python"
        assert "def hello" in blocks[0].content
        assert blocks[0].is_diff is False

    def test_parse_fenced_js(self, parser: ResponseParser) -> None:
        response = '```javascript:app.js\nconsole.log("hi");\n```'
        blocks = parser.parse(response)
        assert len(blocks) == 1
        assert blocks[0].file_path == "app.js"

    def test_parse_multiple_fenced(self, parser: ResponseParser) -> None:
        response = (
            '```python:a.py\ncode_a\n```\n'
            'Some text\n'
            '```python:b.py\ncode_b\n```'
        )
        blocks = parser.parse(response)
        assert len(blocks) == 2

    def test_parse_no_blocks(self, parser: ResponseParser) -> None:
        response = "Just a normal response with no code."
        blocks = parser.parse(response)
        assert len(blocks) == 0


class TestParserDiff:
    def test_parse_unified_diff(self, parser: ResponseParser) -> None:
        response = (
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,4 @@\n"
            " def hello():\n"
            "-    pass\n"
            "+    return 'hi'\n"
            "+    # new line\n"
        )
        blocks = parser.parse(response)
        assert len(blocks) == 1
        assert blocks[0].file_path == "src/main.py"
        assert blocks[0].is_diff is True

    def test_parse_diff_with_context(self, parser: ResponseParser) -> None:
        response = (
            "Here are the changes:\n\n"
            "--- a/utils.py\n"
            "+++ b/utils.py\n"
            "@@ -10,3 +10,4 @@\n"
            " def add(a, b):\n"
            "-    return a+b\n"
            "+    return a + b\n"
        )
        blocks = parser.parse(response)
        assert len(blocks) == 1


class TestParserFileMarker:
    def test_parse_file_marker(self, parser: ResponseParser) -> None:
        response = (
            "FILE: src/new.py\n"
            "def new_function():\n"
            "    return True\n"
        )
        blocks = parser.parse(response)
        assert len(blocks) == 1
        assert blocks[0].file_path == "src/new.py"
        assert "def new_function" in blocks[0].content

    def test_parse_multiple_file_markers(self, parser: ResponseParser) -> None:
        response = (
            "FILE: a.py\n"
            "code_a\n"
            "\nFILE: b.py\n"
            "code_b\n"
        )
        blocks = parser.parse(response)
        assert len(blocks) == 2


class TestParserMixed:
    def test_dedup_same_path(self, parser: ResponseParser) -> None:
        response = (
            '```python:src/main.py\ncode\n```\n'
            'FILE: src/main.py\nother code\n'
        )
        blocks = parser.parse(response)
        # Should only get the first occurrence
        assert len(blocks) == 1

    def test_mixed_formats(self, parser: ResponseParser) -> None:
        response = (
            '```python:a.py\ncode_a\n```\n'
            "--- a/b.py\n+++ b/b.py\n@@ -1 +1 @@\n-old\n+new\n"
            "\nFILE: c.py\ncode_c\n"
        )
        blocks = parser.parse(response)
        assert len(blocks) == 3


# --- FileApplier Tests ---


class TestValidatePath:
    def test_valid_path(self, applier: FileApplier) -> None:
        result = applier.validate_path("src/main.py")
        assert result is not None

    def test_path_traversal_rejected(self, applier: FileApplier) -> None:
        result = applier.validate_path("../../etc/passwd")
        assert result is None

    def test_dotdot_in_middle(self, applier: FileApplier) -> None:
        result = applier.validate_path("src/../../../etc/passwd")
        assert result is None

    def test_blocked_env(self, applier: FileApplier) -> None:
        result = applier.validate_path(".env")
        assert result is None

    def test_blocked_pem(self, applier: FileApplier) -> None:
        result = applier.validate_path("certs/server.pem")
        assert result is None

    def test_blocked_key(self, applier: FileApplier) -> None:
        result = applier.validate_path("secrets/private.key")
        assert result is None


class TestApplyBlock:
    def test_apply_new_file(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        block = CodeBlock(
            file_path="new_file.py",
            content='print("hello")\n',
        )
        result = applier.apply_block(block, mode="auto")
        assert result is True
        assert (tmp_path / "new_file.py").is_file()
        assert 'print("hello")' in (tmp_path / "new_file.py").read_text()

    def test_apply_existing_file(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "existing.py"
        target.write_text("old content\n")

        block = CodeBlock(
            file_path="existing.py",
            content="new content\n",
        )
        result = applier.apply_block(block, mode="auto")
        assert result is True
        assert target.read_text() == "new content\n"

    def test_backup_created(
        self,
        applier: FileApplier,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "backup_test.py"
        target.write_text("original\n")

        block = CodeBlock(file_path="backup_test.py", content="updated\n")
        applier.apply_block(block, mode="auto")
        assert (tmp_path / "backup_test.py.bak").is_file()

    def test_parent_dir_created(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        block = CodeBlock(
            file_path="deep/nested/dir/file.py",
            content="content\n",
        )
        result = applier.apply_block(block, mode="auto")
        assert result is True
        assert (tmp_path / "deep" / "nested" / "dir" / "file.py").is_file()

    def test_dry_run_no_write(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        block = CodeBlock(file_path="dry.py", content="content\n")
        result = applier.apply_block(block, mode="dry-run")
        assert result is False
        assert not (tmp_path / "dry.py").is_file()

    def test_path_traversal_rejected_in_apply(
        self, applier: FileApplier
    ) -> None:
        block = CodeBlock(
            file_path="../../etc/passwd",
            content="bad content\n",
        )
        result = applier.apply_block(block, mode="auto")
        assert result is False


class TestApplyAll:
    def test_apply_multiple(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        blocks = [
            CodeBlock(file_path="a.py", content="a content\n"),
            CodeBlock(file_path="b.py", content="b content\n"),
        ]
        results = applier.apply_all(blocks, mode="auto")
        assert len(results) == 2
        assert all(r.success for r in results)
        assert (tmp_path / "a.py").is_file()
        assert (tmp_path / "b.py").is_file()

    def test_apply_with_invalid_skipped(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        blocks = [
            CodeBlock(file_path="good.py", content="good\n"),
            CodeBlock(file_path="../../bad.py", content="bad\n"),
        ]
        results = applier.apply_all(blocks, mode="auto")
        succeeded = [r.file_path for r in results if r.success]
        assert succeeded == ["good.py"]


class TestPreviewChanges:
    def test_preview(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        blocks = [CodeBlock(file_path="preview.py", content="code\n")]
        applier.preview_changes(blocks)
        # Should not create file
        assert not (tmp_path / "preview.py").is_file()


class TestApplyDiff:
    def test_diff_apply(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "diff_target.py"
        target.write_text("line1\nline2\nline3\n")

        block = CodeBlock(
            file_path="diff_target.py",
            content=(
                "--- a/diff_target.py\n"
                "+++ b/diff_target.py\n"
                "@@ -1,3 +1,3 @@\n"
                " line1\n"
                "-line2\n"
                "+line2_modified\n"
                " line3\n"
            ),
            is_diff=True,
        )
        result = applier.apply_block(block, mode="auto")
        assert result is True
        content = target.read_text()
        assert "line2_modified" in content

    def test_git_dirty_warning(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "dirty.py"
        target.write_text("content\n")
        block = CodeBlock(file_path="dirty.py", content="new\n")
        # This should not crash even without git
        result = applier.apply_block(block, mode="auto")
        assert result is True
