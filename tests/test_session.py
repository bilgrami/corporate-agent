"""Tests for session management module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from genai_cli.config import ConfigManager
from genai_cli.models import ChatMessage
from genai_cli.session import SessionManager


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sessions"
    d.mkdir()
    return d


@pytest.fixture
def session_config(tmp_path: Path, session_dir: Path) -> ConfigManager:
    settings = {
        "api_base_url": "https://api.test.com",
        "session_dir": str(session_dir),
        "max_saved_sessions": 5,
    }
    p = tmp_path / "settings.yaml"
    p.write_text(yaml.dump(settings))
    return ConfigManager(config_path=str(p))


@pytest.fixture
def mgr(session_config: ConfigManager) -> SessionManager:
    return SessionManager(session_config)


class TestSessionManager:
    def test_create_session(self, mgr: SessionManager) -> None:
        session = mgr.create_session()
        assert "session_id" in session
        assert session["messages"] == []
        assert "token_tracker" in session

    def test_create_session_with_model(self, mgr: SessionManager) -> None:
        session = mgr.create_session("claude-sonnet-4-5-global")
        assert session["model_name"] == "claude-sonnet-4-5-global"

    def test_save_and_load(self, mgr: SessionManager) -> None:
        session = mgr.create_session()
        mgr.save_session(session)

        loaded = mgr.load_session(session["session_id"])
        assert loaded is not None
        assert loaded["session_id"] == session["session_id"]

    def test_load_prefix_match(self, mgr: SessionManager) -> None:
        session = mgr.create_session()
        mgr.save_session(session)

        prefix = session["session_id"][:8]
        loaded = mgr.load_session(prefix)
        assert loaded is not None
        assert loaded["session_id"] == session["session_id"]

    def test_load_nonexistent(self, mgr: SessionManager) -> None:
        loaded = mgr.load_session("nonexistent-id")
        assert loaded is None

    def test_list_sessions(self, mgr: SessionManager) -> None:
        for _ in range(3):
            session = mgr.create_session()
            mgr.save_session(session)

        sessions = mgr.list_sessions()
        assert len(sessions) == 3

    def test_list_sessions_sorted(self, mgr: SessionManager) -> None:
        for _ in range(3):
            session = mgr.create_session()
            mgr.save_session(session)

        sessions = mgr.list_sessions()
        dates = [s.get("updated_at", "") for s in sessions]
        assert dates == sorted(dates, reverse=True)

    def test_delete_session(self, mgr: SessionManager) -> None:
        session = mgr.create_session()
        mgr.save_session(session)
        assert mgr.delete_session(session["session_id"]) is True
        assert mgr.load_session(session["session_id"]) is None

    def test_delete_nonexistent(self, mgr: SessionManager) -> None:
        assert mgr.delete_session("fake-id") is False

    def test_clear_sessions(self, mgr: SessionManager) -> None:
        for _ in range(3):
            mgr.save_session(mgr.create_session())
        count = mgr.clear_sessions()
        assert count == 3
        assert mgr.list_sessions() == []

    def test_compact_session(self, mgr: SessionManager) -> None:
        session = mgr.create_session()
        for i in range(10):
            session["messages"].append({"role": "user", "content": f"msg {i}"})
        compacted = mgr.compact_session(session)
        assert len(compacted["messages"]) < 10

    def test_compact_short_session(self, mgr: SessionManager) -> None:
        session = mgr.create_session()
        session["messages"] = [{"role": "user", "content": "hi"}]
        compacted = mgr.compact_session(session)
        assert len(compacted["messages"]) == 1

    def test_add_message(self, mgr: SessionManager) -> None:
        session = mgr.create_session()
        msg = ChatMessage(
            session_id=session["session_id"],
            role="user",
            content="hello",
            tokens_consumed=50,
        )
        mgr.add_message(session, msg)
        assert len(session["messages"]) == 1
        assert session["messages"][0]["content"] == "hello"

    def test_token_state_persistence(
        self, mgr: SessionManager, session_config: ConfigManager
    ) -> None:
        session = mgr.create_session()
        session["token_tracker"] = {"consumed": 5000, "context_window": 128000}
        mgr.save_session(session)

        loaded = mgr.load_session(session["session_id"])
        assert loaded is not None
        assert loaded["token_tracker"]["consumed"] == 5000

    def test_delete_old_sessions(self, mgr: SessionManager) -> None:
        for _ in range(8):
            mgr.save_session(mgr.create_session())
        deleted = mgr.delete_old_sessions(max_keep=5)
        assert deleted == 3
        assert len(mgr.list_sessions()) == 5
