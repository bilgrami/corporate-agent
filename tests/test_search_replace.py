"""Tests for SEARCH/REPLACE parser and application."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
import yaml

from genai_cli.applier import (
    ApplyResult,
    EditBlock,
    FileApplier,
    SearchReplaceParser,
    UnifiedParser,
)
from genai_cli.config import ConfigManager
from genai_cli.display import Display


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> SearchReplaceParser:
    return SearchReplaceParser()


@pytest.fixture
def unified() -> UnifiedParser:
    return UnifiedParser()


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


# ---------------------------------------------------------------------------
# SearchReplaceParser Tests
# ---------------------------------------------------------------------------


class TestSearchReplaceParser:
    def test_parse_single_edit(self, parser: SearchReplaceParser) -> None:
        response = (
            "Here is the fix:\n\n"
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "def hello():\n"
            "    pass\n"
            "=======\n"
            "def hello():\n"
            "    return 'hi'\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert edits[0].file_path == "src/main.py"
        assert "pass" in edits[0].search_content
        assert "'hi'" in edits[0].replace_content
        assert not edits[0].is_create
        assert not edits[0].is_delete

    def test_parse_create_file(self, parser: SearchReplaceParser) -> None:
        response = (
            "src/new_file.py\n"
            "<<<<<<< SEARCH\n"
            "=======\n"
            "def new_function():\n"
            "    return True\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert edits[0].file_path == "src/new_file.py"
        assert edits[0].is_create
        assert "new_function" in edits[0].replace_content

    def test_parse_delete_content(self, parser: SearchReplaceParser) -> None:
        response = (
            "src/utils.py\n"
            "<<<<<<< SEARCH\n"
            "def deprecated():\n"
            "    pass\n"
            "=======\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert edits[0].is_delete
        assert "deprecated" in edits[0].search_content
        assert edits[0].replace_content == ""

    def test_parse_multiple_edits_same_file(
        self, parser: SearchReplaceParser
    ) -> None:
        response = (
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "import os\n"
            "=======\n"
            "import os\n"
            "import sys\n"
            ">>>>>>> REPLACE\n"
            "\n"
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "    return None\n"
            "=======\n"
            "    return default\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 2
        assert edits[0].file_path == "src/main.py"
        assert edits[1].file_path == "src/main.py"

    def test_parse_multiple_files(self, parser: SearchReplaceParser) -> None:
        response = (
            "src/a.py\n"
            "<<<<<<< SEARCH\n"
            "code_a\n"
            "=======\n"
            "new_a\n"
            ">>>>>>> REPLACE\n"
            "\n"
            "src/b.py\n"
            "<<<<<<< SEARCH\n"
            "code_b\n"
            "=======\n"
            "new_b\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 2
        assert edits[0].file_path == "src/a.py"
        assert edits[1].file_path == "src/b.py"

    def test_parse_mixed_with_prose(
        self, parser: SearchReplaceParser
    ) -> None:
        response = (
            "I found a bug in the code. Here is the fix:\n\n"
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "old\n"
            "=======\n"
            "new\n"
            ">>>>>>> REPLACE\n"
            "\nThis should resolve the issue. Let me know if you need "
            "anything else.\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert edits[0].file_path == "src/main.py"

    def test_parse_no_blocks(self, parser: SearchReplaceParser) -> None:
        response = "Just a normal response with no code changes."
        edits = parser.parse(response)
        assert len(edits) == 0

    def test_parse_incomplete_block_no_divider(
        self, parser: SearchReplaceParser
    ) -> None:
        response = (
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "def hello():\n"
            "    pass\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 0

    def test_parse_incomplete_block_no_end(
        self, parser: SearchReplaceParser
    ) -> None:
        response = (
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "def hello():\n"
            "    pass\n"
            "=======\n"
            "def hello():\n"
            "    return 'hi'\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 0

    def test_parse_empty_response(self, parser: SearchReplaceParser) -> None:
        edits = parser.parse("")
        assert len(edits) == 0

    def test_parse_block_at_end_of_response(
        self, parser: SearchReplaceParser
    ) -> None:
        response = (
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "old\n"
            "=======\n"
            "new\n"
            ">>>>>>> REPLACE"
        )
        edits = parser.parse(response)
        assert len(edits) == 1

    def test_parse_preserves_original_text(
        self, parser: SearchReplaceParser
    ) -> None:
        response = (
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "old\n"
            "=======\n"
            "new\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert "<<<<<<< SEARCH" in edits[0].original_text
        assert ">>>>>>> REPLACE" in edits[0].original_text

    def test_parse_windows_line_endings(
        self, parser: SearchReplaceParser
    ) -> None:
        response = (
            "src/main.py\r\n"
            "<<<<<<< SEARCH\r\n"
            "old\r\n"
            "=======\r\n"
            "new\r\n"
            ">>>>>>> REPLACE\r\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert edits[0].file_path == "src/main.py"

    def test_parse_trailing_whitespace_in_path(
        self, parser: SearchReplaceParser
    ) -> None:
        response = (
            "src/main.py  \n"
            "<<<<<<< SEARCH\n"
            "old\n"
            "=======\n"
            "new\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert edits[0].file_path == "src/main.py"

    def test_path_with_spaces_not_matched(
        self, parser: SearchReplaceParser
    ) -> None:
        """Lines that start with whitespace should not be treated as paths."""
        response = (
            "  indented line\n"
            "<<<<<<< SEARCH\n"
            "old\n"
            "=======\n"
            "new\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 0

    def test_parse_nested_code_fences(
        self, parser: SearchReplaceParser
    ) -> None:
        """SEARCH/REPLACE containing triple backticks should work."""
        response = (
            "README.md\n"
            "<<<<<<< SEARCH\n"
            "```python\n"
            "old_code()\n"
            "```\n"
            "=======\n"
            "```python\n"
            "new_code()\n"
            "```\n"
            ">>>>>>> REPLACE\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert "```python" in edits[0].search_content
        assert "new_code()" in edits[0].replace_content


    def test_parse_code_fence_wrapped_block(
        self, parser: SearchReplaceParser
    ) -> None:
        """When AI wraps SEARCH/REPLACE in a code fence, extract the path from the line before the fence."""
        response = (
            "Here is the new file:\n\n"
            "`docs/troubleshooting.md`\n"
            "```markdown\n"
            "<<<<<<< SEARCH\n"
            "=======\n"
            "# Troubleshooting Guide\n"
            "Common issues.\n"
            ">>>>>>> REPLACE\n"
            "```\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert edits[0].file_path == "docs/troubleshooting.md"
        assert edits[0].is_create
        assert "Troubleshooting Guide" in edits[0].replace_content

    def test_parse_code_fence_wrapped_edit(
        self, parser: SearchReplaceParser
    ) -> None:
        """Code fence wrapping with an edit (non-empty SEARCH)."""
        response = (
            "`src/main.py`\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            "def old():\n"
            "    pass\n"
            "=======\n"
            "def new():\n"
            "    return True\n"
            ">>>>>>> REPLACE\n"
            "```\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 1
        assert edits[0].file_path == "src/main.py"
        assert "old" in edits[0].search_content
        assert "new" in edits[0].replace_content

    def test_parse_code_fence_no_valid_path_skipped(
        self, parser: SearchReplaceParser
    ) -> None:
        """Code fence with no valid path on previous line is skipped."""
        response = (
            "Here is some text\n"
            "```markdown\n"
            "<<<<<<< SEARCH\n"
            "=======\n"
            "# Content\n"
            ">>>>>>> REPLACE\n"
            "```\n"
        )
        edits = parser.parse(response)
        assert len(edits) == 0


# ---------------------------------------------------------------------------
# UnifiedParser Tests
# ---------------------------------------------------------------------------


class TestUnifiedParser:
    def test_prefers_search_replace_over_legacy(
        self, unified: UnifiedParser
    ) -> None:
        response = (
            "src/main.py\n"
            "<<<<<<< SEARCH\n"
            "old\n"
            "=======\n"
            "new\n"
            ">>>>>>> REPLACE\n"
            "\n"
            "```python:src/main.py\n"
            "legacy content\n"
            "```\n"
        )
        edits, legacy = unified.parse(response)
        assert len(edits) == 1
        assert len(legacy) == 0

    def test_fallback_to_fenced(self, unified: UnifiedParser) -> None:
        response = "```python:src/main.py\ndef hello():\n    pass\n```"
        edits, legacy = unified.parse(response)
        assert len(edits) == 0
        assert len(legacy) == 1
        assert legacy[0].file_path == "src/main.py"

    def test_fallback_to_diff(self, unified: UnifiedParser) -> None:
        response = (
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,4 @@\n"
            " def hello():\n"
            "-    pass\n"
            "+    return 'hi'\n"
        )
        edits, legacy = unified.parse(response)
        assert len(edits) == 0
        assert len(legacy) == 1
        assert legacy[0].is_diff

    def test_fallback_to_file_marker(self, unified: UnifiedParser) -> None:
        response = "FILE: src/new.py\ndef new():\n    pass\n"
        edits, legacy = unified.parse(response)
        assert len(edits) == 0
        assert len(legacy) == 1

    def test_empty_response_no_blocks(self, unified: UnifiedParser) -> None:
        edits, legacy = unified.parse("No code here.")
        assert len(edits) == 0
        assert len(legacy) == 0


# ---------------------------------------------------------------------------
# SEARCH/REPLACE Application Tests
# ---------------------------------------------------------------------------


class TestSearchReplaceApply:
    def test_exact_match_replace(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "target.py"
        target.write_text("def hello():\n    pass\n")

        edit = EditBlock(
            file_path="target.py",
            search_content="def hello():\n    pass",
            replace_content="def hello():\n    return 'hi'",
        )
        result = applier.apply_edits([edit], mode="auto")
        assert len(result) == 1
        assert result[0].success
        assert "return 'hi'" in target.read_text()

    def test_create_new_file(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        edit = EditBlock(
            file_path="brand_new.py",
            search_content="",
            replace_content="print('hello')\n",
        )
        result = applier.apply_edits([edit], mode="auto")
        assert result[0].success
        assert (tmp_path / "brand_new.py").is_file()
        assert "print('hello')" in (tmp_path / "brand_new.py").read_text()

    def test_create_with_nested_dirs(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        edit = EditBlock(
            file_path="deep/nested/file.py",
            search_content="",
            replace_content="content\n",
        )
        result = applier.apply_edits([edit], mode="auto")
        assert result[0].success
        assert (tmp_path / "deep" / "nested" / "file.py").is_file()

    def test_delete_content(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "target.py"
        target.write_text("keep\ndelete_me\nkeep_too\n")

        edit = EditBlock(
            file_path="target.py",
            search_content="delete_me\n",
            replace_content="",
        )
        result = applier.apply_edits([edit], mode="auto")
        assert result[0].success
        content = target.read_text()
        assert "delete_me" not in content
        assert "keep" in content

    def test_multiple_edits_same_file(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "target.py"
        target.write_text("import os\n\ndef hello():\n    return None\n")

        edits = [
            EditBlock(
                file_path="target.py",
                search_content="import os",
                replace_content="import os\nimport sys",
            ),
            EditBlock(
                file_path="target.py",
                search_content="return None",
                replace_content="return 'hello'",
            ),
        ]
        results = applier.apply_edits(edits, mode="auto")
        assert all(r.success for r in results)
        content = target.read_text()
        assert "import sys" in content
        assert "return 'hello'" in content

    def test_search_not_found_returns_error(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "target.py"
        target.write_text("def hello():\n    return 'hi'\n")

        edit = EditBlock(
            file_path="target.py",
            search_content="def goodbye():\n    pass",
            replace_content="def goodbye():\n    return 'bye'",
        )
        results = applier.apply_edits([edit], mode="auto")
        assert not results[0].success
        assert "not found" in results[0].error_message.lower()
        assert "def hello" in results[0].file_content_snippet

    def test_whitespace_normalized_match(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        # File has trailing spaces, SEARCH content does not
        target = tmp_path / "target.py"
        target.write_text("def hello():   \n    pass   \n")

        edit = EditBlock(
            file_path="target.py",
            search_content="def hello():\n    pass",
            replace_content="def hello():\n    return 'hi'",
        )
        results = applier.apply_edits([edit], mode="auto")
        assert results[0].success
        assert "return 'hi'" in target.read_text()

    def test_indent_normalized_match(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        # File has 4-space indent, SEARCH has 2-space indent
        target = tmp_path / "target.py"
        target.write_text("def hello():\n    pass\n")

        edit = EditBlock(
            file_path="target.py",
            search_content="def hello():\n  pass",
            replace_content="def hello():\n    return 'hi'",
        )
        results = applier.apply_edits([edit], mode="auto")
        assert results[0].success

    def test_path_validation_blocks_traversal(
        self, applier: FileApplier
    ) -> None:
        edit = EditBlock(
            file_path="../../etc/passwd",
            search_content="",
            replace_content="bad content",
        )
        results = applier.apply_edits([edit], mode="auto")
        assert not results[0].success
        assert "Path validation failed" in results[0].error_message

    def test_path_validation_blocks_env(self, applier: FileApplier) -> None:
        edit = EditBlock(
            file_path=".env",
            search_content="",
            replace_content="SECRET=bad",
        )
        results = applier.apply_edits([edit], mode="auto")
        assert not results[0].success

    def test_backup_created_before_edit(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "backup_test.py"
        target.write_text("original content\n")

        edit = EditBlock(
            file_path="backup_test.py",
            search_content="original content",
            replace_content="new content",
        )
        applier.apply_edits([edit], mode="auto")
        assert (tmp_path / "backup_test.py.bak").is_file()
        assert "original" in (tmp_path / "backup_test.py.bak").read_text()

    def test_dry_run_no_write(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "dry.py"
        target.write_text("original\n")

        edit = EditBlock(
            file_path="dry.py",
            search_content="original",
            replace_content="changed",
        )
        results = applier.apply_edits([edit], mode="dry-run")
        assert not results[0].success
        assert target.read_text() == "original\n"

    def test_file_not_found_for_edit(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        edit = EditBlock(
            file_path="nonexistent.py",
            search_content="something",
            replace_content="else",
        )
        results = applier.apply_edits([edit], mode="auto")
        assert not results[0].success
        assert "not found" in results[0].error_message.lower()

    def test_apply_result_fields(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "test.py"
        target.write_text("content\n")

        edit = EditBlock(
            file_path="test.py",
            search_content="content",
            replace_content="new_content",
        )
        results = applier.apply_edits([edit], mode="auto")
        assert results[0].file_path == "test.py"
        assert results[0].success is True
        assert results[0].error_message == ""

    def test_git_dirty_does_not_crash(
        self, applier: FileApplier, tmp_path: Path
    ) -> None:
        target = tmp_path / "dirty.py"
        target.write_text("old\n")

        edit = EditBlock(
            file_path="dirty.py",
            search_content="old",
            replace_content="new",
        )
        # Should not crash even without git
        results = applier.apply_edits([edit], mode="auto")
        assert results[0].success


# ---------------------------------------------------------------------------
# Legacy ResponseParser Path Validation Tests
# ---------------------------------------------------------------------------


class TestLegacyPathValidation:
    """Tests that ResponseParser rejects invalid paths from fenced blocks."""

    def test_rejects_bare_language_name(self) -> None:
        """```python:markdown should not extract 'markdown' as a file path."""
        from genai_cli.applier import ResponseParser

        parser = ResponseParser()
        response = "```python:markdown\nprint('hello')\n```"
        blocks = parser.parse(response)
        assert len(blocks) == 0

    def test_rejects_bare_word_no_dot_or_slash(self) -> None:
        """Paths without '.' or '/' are rejected (e.g. 'javascript')."""
        from genai_cli.applier import ResponseParser

        parser = ResponseParser()
        response = "```js:javascript\nconsole.log('hi');\n```"
        blocks = parser.parse(response)
        assert len(blocks) == 0

    def test_rejects_code_fence_artifact(self) -> None:
        """Paths starting with ``` are rejected."""
        from genai_cli.applier import ResponseParser

        parser = ResponseParser()
        response = "```python:```nested\ncode\n```"
        blocks = parser.parse(response)
        assert len(blocks) == 0

    def test_accepts_valid_path_with_dot(self) -> None:
        """Paths like 'main.py' (with a dot) are accepted."""
        from genai_cli.applier import ResponseParser

        parser = ResponseParser()
        response = "```python:main.py\ndef hello(): pass\n```"
        blocks = parser.parse(response)
        assert len(blocks) == 1
        assert blocks[0].file_path == "main.py"

    def test_accepts_valid_path_with_slash(self) -> None:
        """Paths like 'src/utils' (with a slash) are accepted."""
        from genai_cli.applier import ResponseParser

        parser = ResponseParser()
        response = "```python:src/utils\ndef add(a,b): return a+b\n```"
        blocks = parser.parse(response)
        assert len(blocks) == 1
        assert blocks[0].file_path == "src/utils"
