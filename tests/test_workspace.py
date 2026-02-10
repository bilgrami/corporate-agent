"""Tests for multi-repo workspace manager."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.workspace import RepoConfig, WorkspaceConfig, WorkspaceManager


@pytest.fixture
def display() -> Display:
    return Display(file=StringIO())


@pytest.fixture
def ws_mgr(mock_config: ConfigManager, display: Display) -> WorkspaceManager:
    return WorkspaceManager(mock_config, display)


class TestCreateWorkspace:
    def test_create_new(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws = ws_mgr.create_workspace("test-ws", tmp_path / "workspace")
        assert ws.name == "test-ws"
        assert (
            tmp_path / "workspace" / ".genai-workspace.yaml"
        ).is_file()

    def test_create_idempotent(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        root = tmp_path / "workspace"
        ws_mgr.create_workspace("ws1", root)
        ws_mgr.create_workspace("ws2", root)
        # Should overwrite without error
        ws = ws_mgr.load_workspace(root)
        assert ws is not None
        assert ws.name == "ws2"


class TestSaveLoadWorkspace:
    def test_save_and_load(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("my-ws", tmp_path)
        ws_mgr.add_repo("repo-a", tmp_path / "a")
        ws_mgr.add_repo("repo-b", tmp_path / "b")

        # Create new manager to load
        mgr2 = WorkspaceManager(ws_mgr._config, ws_mgr._display)
        loaded = mgr2.load_workspace(tmp_path)
        assert loaded is not None
        assert loaded.name == "my-ws"
        assert len(loaded.repos) == 2

    def test_load_missing(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        result = ws_mgr.load_workspace(tmp_path / "nonexistent")
        assert result is None


class TestRepoManagement:
    def test_add_repo(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        repo = ws_mgr.add_repo("main", tmp_path / "main")
        assert repo.name == "main"
        assert repo.is_active is True  # first repo is active

    def test_add_second_repo(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        ws_mgr.add_repo("first", tmp_path / "first")
        repo2 = ws_mgr.add_repo("second", tmp_path / "second")
        assert repo2.is_active is False  # only first is auto-active

    def test_remove_repo(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        ws_mgr.add_repo("a", tmp_path / "a")
        ws_mgr.add_repo("b", tmp_path / "b")
        assert ws_mgr.remove_repo("a") is True
        assert len(ws_mgr.list_repos()) == 1
        assert ws_mgr.list_repos()[0].name == "b"

    def test_remove_nonexistent(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        assert ws_mgr.remove_repo("nope") is False

    def test_list_repos(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        ws_mgr.add_repo("x", tmp_path / "x")
        repos = ws_mgr.list_repos()
        assert len(repos) == 1

    def test_switch_repo(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        ws_mgr.add_repo("a", tmp_path / "a")
        ws_mgr.add_repo("b", tmp_path / "b")
        ws_mgr.switch_repo("b")
        active = ws_mgr.get_active_repo()
        assert active is not None
        assert active.name == "b"

    def test_switch_nonexistent(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        assert ws_mgr.switch_repo("nope") is False


class TestMoveFile:
    def test_move_between_repos(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        repo_a.mkdir()
        repo_b.mkdir()
        ws_mgr.add_repo("a", repo_a)
        ws_mgr.add_repo("b", repo_b)

        # Create source file
        (repo_a / "module.py").write_text("x = 1\n")

        # Mock git operations to avoid needing real repos
        with patch("genai_cli.workspace.GitOperations") as MockGit:
            mock_git = MockGit.return_value
            mock_git.add.return_value = None
            mock_git.rm.return_value = None

            ok = ws_mgr.move_file("a", "module.py", "b", "module.py")

        assert ok is True
        assert (repo_b / "module.py").is_file()

    def test_move_missing_source(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        repo_a.mkdir()
        repo_b.mkdir()
        ws_mgr.add_repo("a", repo_a)
        ws_mgr.add_repo("b", repo_b)
        ok = ws_mgr.move_file("a", "nope.py", "b", "nope.py")
        assert ok is False


class TestFindFile:
    def test_find_across_repos(
        self, ws_mgr: WorkspaceManager, tmp_path: Path
    ) -> None:
        ws_mgr.create_workspace("ws", tmp_path)
        r1 = tmp_path / "r1"
        r2 = tmp_path / "r2"
        r1.mkdir()
        r2.mkdir()
        ws_mgr.add_repo("r1", r1)
        ws_mgr.add_repo("r2", r2)

        (r1 / "config.py").write_text("")
        (r2 / "config.py").write_text("")

        results = ws_mgr.find_file("config.py")
        assert len(results) == 2
        repo_names = [r[0] for r in results]
        assert "r1" in repo_names
        assert "r2" in repo_names
