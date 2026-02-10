"""Tests for git operations manager."""

from __future__ import annotations

import subprocess
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.git_ops import GitOperations, GitResult, GitStatus


@pytest.fixture
def display() -> Display:
    return Display(file=StringIO())


@pytest.fixture
def git_ops(mock_config: ConfigManager, display: Display, tmp_path: Path) -> GitOperations:
    return GitOperations(mock_config, display, work_dir=tmp_path)


def _init_repo(path: Path) -> None:
    """Initialize a git repo with an initial commit."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path, capture_output=True,
    )
    (path / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path, capture_output=True,
    )


class TestRunGit:
    def test_run_git_success(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        result = git_ops._run_git(["status"], tmp_path)
        assert result.success is True
        assert result.return_code == 0

    def test_run_git_failure(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        result = git_ops._run_git(
            ["log"], tmp_path  # not a repo
        )
        assert result.success is False


class TestStatus:
    def test_is_repo(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        assert git_ops.is_repo(tmp_path) is False
        _init_repo(tmp_path)
        assert git_ops.is_repo(tmp_path) is True

    def test_current_branch(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        branch = git_ops.current_branch(tmp_path)
        assert branch in ("main", "master")

    def test_is_clean(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        assert git_ops.is_clean(tmp_path) is True

        (tmp_path / "new.txt").write_text("dirty\n")
        assert git_ops.is_clean(tmp_path) is False

    def test_full_status(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        status = git_ops.status(tmp_path)
        assert status.is_repo is True
        assert status.clean is True

        (tmp_path / "untracked.txt").write_text("x\n")
        status = git_ops.status(tmp_path)
        assert status.clean is False
        assert "untracked.txt" in status.untracked


class TestRepoOps:
    def test_init(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        repo_path = tmp_path / "new_repo"
        result = git_ops.init(repo_path)
        assert result.success is True
        assert (repo_path / ".git").is_dir()

    def test_add_and_commit(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        (tmp_path / "file.txt").write_text("content\n")

        result = git_ops.add(["file.txt"], tmp_path)
        assert result.success is True

        result = git_ops.commit("add file", tmp_path)
        assert result.success is True

    def test_create_branch(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        result = git_ops.create_branch("feature", tmp_path)
        assert result.success is True

    def test_checkout(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        git_ops.create_branch("feature", tmp_path)
        result = git_ops.checkout("feature", tmp_path)
        assert result.success is True
        assert git_ops.current_branch(tmp_path) == "feature"


class TestFileOps:
    def test_mv(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        result = git_ops.mv("README.md", "DOCS.md", tmp_path)
        assert result.success is True
        assert (tmp_path / "DOCS.md").is_file()

    def test_rm(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        result = git_ops.rm(["README.md"], work_dir=tmp_path)
        assert result.success is True
        assert not (tmp_path / "README.md").is_file()


class TestSafety:
    def test_ensure_clean_true(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        assert git_ops.ensure_clean(tmp_path) is True

    def test_ensure_clean_false(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        (tmp_path / "dirty.txt").write_text("x\n")
        assert git_ops.ensure_clean(tmp_path) is False

    def test_create_checkpoint(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        (tmp_path / "data.txt").write_text("important\n")
        result = git_ops.create_checkpoint("before refactor", tmp_path)
        assert result.success is True
        assert git_ops.is_clean(tmp_path) is True

    def test_rollback_cancelled(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        with patch.object(git_ops._display, "confirm", return_value=False):
            result = git_ops.rollback_to("abc123", tmp_path)
        assert result.success is False
        assert "Cancelled" in result.stderr


class TestGitignore:
    def test_create_gitignore(
        self, git_ops: GitOperations, tmp_path: Path
    ) -> None:
        git_ops.create_gitignore(tmp_path, ["*.pyc", "__pycache__/"])
        gitignore = tmp_path / ".gitignore"
        assert gitignore.is_file()
        content = gitignore.read_text()
        assert "*.pyc" in content
        assert "__pycache__/" in content
