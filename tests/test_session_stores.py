"""Tests for session storage backends (JSON, SQLite, Composite)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from genai_cli.session_stores import (
    CompositeSessionStore,
    JsonSessionStore,
    SqliteSessionStore,
)


def _make_session(sid: str = "test-id-001", model: str = "gpt-5") -> dict[str, Any]:
    return {
        "session_id": sid,
        "model_name": model,
        "created_at": "2026-02-10T00:00:00+00:00",
        "messages": [
            {
                "role": "user",
                "content": "hello",
                "timestamp": "",
                "model_name": "",
                "tokens_consumed": 10,
                "token_cost": 0.001,
            },
            {
                "role": "assistant",
                "content": "hi there",
                "timestamp": "",
                "model_name": "gpt-5",
                "tokens_consumed": 20,
                "token_cost": 0.002,
            },
        ],
        "token_tracker": {"consumed": 30, "context_window": 128000},
    }


# ── JsonSessionStore ──────────────────────────────────────────────────


class TestJsonSessionStore:
    @pytest.fixture
    def store(self, tmp_path: Path) -> JsonSessionStore:
        return JsonSessionStore(tmp_path / "sessions")

    def test_save_and_load(self, store: JsonSessionStore) -> None:
        session = _make_session()
        store.save(session)
        loaded = store.load("test-id-001")
        assert loaded is not None
        assert loaded["session_id"] == "test-id-001"
        assert len(loaded["messages"]) == 2

    def test_save_returns_path(self, store: JsonSessionStore) -> None:
        session = _make_session()
        result = store.save(session)
        assert result is not None
        assert result.suffix == ".json"

    def test_load_prefix(self, store: JsonSessionStore) -> None:
        session = _make_session()
        store.save(session)
        loaded = store.load("test-id")
        assert loaded is not None
        assert loaded["session_id"] == "test-id-001"

    def test_load_nonexistent(self, store: JsonSessionStore) -> None:
        assert store.load("nonexistent") is None

    def test_list_sessions(self, store: JsonSessionStore) -> None:
        for i in range(3):
            store.save(_make_session(f"id-{i}"))
        sessions = store.list_sessions()
        assert len(sessions) == 3

    def test_list_sessions_limit(self, store: JsonSessionStore) -> None:
        for i in range(5):
            store.save(_make_session(f"id-{i}"))
        sessions = store.list_sessions(limit=2)
        assert len(sessions) == 2

    def test_delete(self, store: JsonSessionStore) -> None:
        store.save(_make_session())
        assert store.delete("test-id-001") is True
        assert store.load("test-id-001") is None

    def test_delete_nonexistent(self, store: JsonSessionStore) -> None:
        assert store.delete("fake") is False

    def test_clear(self, store: JsonSessionStore) -> None:
        for i in range(3):
            store.save(_make_session(f"id-{i}"))
        count = store.clear()
        assert count == 3
        assert store.list_sessions() == []

    def test_close_noop(self, store: JsonSessionStore) -> None:
        store.close()  # Should not raise


# ── SqliteSessionStore ────────────────────────────────────────────────


class TestSqliteSessionStore:
    @pytest.fixture
    def store(self, tmp_path: Path) -> SqliteSessionStore:
        return SqliteSessionStore(tmp_path / "test.db")

    def test_save_and_load(self, store: SqliteSessionStore) -> None:
        session = _make_session()
        store.save(session)
        loaded = store.load("test-id-001")
        assert loaded is not None
        assert loaded["session_id"] == "test-id-001"
        assert len(loaded["messages"]) == 2
        assert loaded["messages"][0]["content"] == "hello"

    def test_save_returns_none(self, store: SqliteSessionStore) -> None:
        result = store.save(_make_session())
        assert result is None

    def test_load_prefix(self, store: SqliteSessionStore) -> None:
        store.save(_make_session())
        loaded = store.load("test-id")
        assert loaded is not None

    def test_load_nonexistent(self, store: SqliteSessionStore) -> None:
        assert store.load("nonexistent") is None

    def test_list_sessions(self, store: SqliteSessionStore) -> None:
        for i in range(3):
            store.save(_make_session(f"id-{i}"))
        sessions = store.list_sessions()
        assert len(sessions) == 3

    def test_list_sessions_limit(self, store: SqliteSessionStore) -> None:
        for i in range(5):
            store.save(_make_session(f"id-{i}"))
        sessions = store.list_sessions(limit=2)
        assert len(sessions) == 2

    def test_list_sessions_message_count(self, store: SqliteSessionStore) -> None:
        store.save(_make_session())
        sessions = store.list_sessions()
        assert sessions[0]["message_count"] == 2

    def test_delete(self, store: SqliteSessionStore) -> None:
        store.save(_make_session())
        assert store.delete("test-id-001") is True
        assert store.load("test-id-001") is None

    def test_delete_cascades_messages(self, store: SqliteSessionStore) -> None:
        store.save(_make_session())
        store.delete("test-id-001")
        cursor = store._conn.execute("SELECT COUNT(*) FROM messages")
        assert cursor.fetchone()[0] == 0

    def test_delete_nonexistent(self, store: SqliteSessionStore) -> None:
        assert store.delete("fake") is False

    def test_clear(self, store: SqliteSessionStore) -> None:
        for i in range(3):
            store.save(_make_session(f"id-{i}"))
        count = store.clear()
        assert count == 3
        assert store.list_sessions() == []

    def test_token_tracker_persistence(self, store: SqliteSessionStore) -> None:
        session = _make_session()
        session["token_tracker"] = {"consumed": 5000, "context_window": 128000}
        store.save(session)
        loaded = store.load("test-id-001")
        assert loaded is not None
        assert loaded["token_tracker"]["consumed"] == 5000

    def test_close(self, store: SqliteSessionStore) -> None:
        store.close()
        # Verify connection is closed (any operation should fail)
        with pytest.raises(Exception):
            store._conn.execute("SELECT 1")

    def test_save_updates_existing(self, store: SqliteSessionStore) -> None:
        session = _make_session()
        store.save(session)
        session["messages"].append({
            "role": "user",
            "content": "more",
            "timestamp": "",
            "model_name": "",
            "tokens_consumed": 5,
            "token_cost": 0.0,
        })
        store.save(session)
        loaded = store.load("test-id-001")
        assert loaded is not None
        assert len(loaded["messages"]) == 3


# ── SqliteSessionStore migration ──────────────────────────────────────


class TestSqliteMigration:
    def test_migrates_json_files(self, tmp_path: Path) -> None:
        json_dir = tmp_path / "sessions"
        json_dir.mkdir()
        session = _make_session("migrated-001")
        (json_dir / "migrated-001.json").write_text(
            json.dumps(session, indent=2)
        )

        store = SqliteSessionStore(tmp_path / "test.db", json_dir=json_dir)
        loaded = store.load("migrated-001")
        assert loaded is not None
        assert loaded["session_id"] == "migrated-001"
        assert len(loaded["messages"]) == 2
        store.close()

    def test_migration_idempotent(self, tmp_path: Path) -> None:
        json_dir = tmp_path / "sessions"
        json_dir.mkdir()
        session = _make_session("idempotent-001")
        (json_dir / "idempotent-001.json").write_text(
            json.dumps(session, indent=2)
        )

        store1 = SqliteSessionStore(tmp_path / "test.db", json_dir=json_dir)
        store1.close()

        # Second init should not duplicate
        store2 = SqliteSessionStore(tmp_path / "test.db", json_dir=json_dir)
        sessions = store2.list_sessions()
        assert len(sessions) == 1
        store2.close()

    def test_migration_skips_corrupt_json(self, tmp_path: Path) -> None:
        json_dir = tmp_path / "sessions"
        json_dir.mkdir()
        (json_dir / "corrupt.json").write_text("{invalid json")
        (json_dir / "good.json").write_text(
            json.dumps(_make_session("good-001"), indent=2)
        )

        store = SqliteSessionStore(tmp_path / "test.db", json_dir=json_dir)
        sessions = store.list_sessions()
        assert len(sessions) == 1
        store.close()


# ── SqliteSessionStore corrupt DB ─────────────────────────────────────


class TestSqliteCorruptDB:
    def test_corrupt_db_raises(self, tmp_path: Path) -> None:
        db_path = tmp_path / "corrupt.db"
        db_path.write_text("this is not a sqlite file")
        with pytest.raises(Exception):
            SqliteSessionStore(db_path)


# ── CompositeSessionStore ─────────────────────────────────────────────


class TestCompositeSessionStore:
    @pytest.fixture
    def stores(self, tmp_path: Path) -> tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]:
        json_store = JsonSessionStore(tmp_path / "sessions")
        sqlite_store = SqliteSessionStore(tmp_path / "test.db")
        composite = CompositeSessionStore(sqlite_store, json_store)
        return sqlite_store, json_store, composite

    def test_save_writes_both(
        self, stores: tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]
    ) -> None:
        sqlite_store, json_store, composite = stores
        session = _make_session()
        composite.save(session)

        # Both should have the data
        assert json_store.load("test-id-001") is not None
        assert sqlite_store.load("test-id-001") is not None

    def test_save_returns_json_path(
        self, stores: tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]
    ) -> None:
        _, _, composite = stores
        result = composite.save(_make_session())
        assert result is not None
        assert result.suffix == ".json"

    def test_load_prefers_primary(
        self, stores: tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]
    ) -> None:
        sqlite_store, json_store, composite = stores
        session = _make_session()
        # Only save to sqlite (primary)
        sqlite_store.save(session)
        loaded = composite.load("test-id-001")
        assert loaded is not None

    def test_load_falls_back_to_secondary(
        self, stores: tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]
    ) -> None:
        _, json_store, composite = stores
        session = _make_session()
        # Only save to json (secondary)
        json_store.save(session)
        loaded = composite.load("test-id-001")
        assert loaded is not None

    def test_delete_removes_from_both(
        self, stores: tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]
    ) -> None:
        sqlite_store, json_store, composite = stores
        session = _make_session()
        composite.save(session)
        assert composite.delete("test-id-001") is True
        assert sqlite_store.load("test-id-001") is None
        assert json_store.load("test-id-001") is None

    def test_clear_clears_both(
        self, stores: tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]
    ) -> None:
        _, _, composite = stores
        for i in range(3):
            composite.save(_make_session(f"id-{i}"))
        count = composite.clear()
        assert count == 3
        assert composite.list_sessions() == []

    def test_list_uses_primary(
        self, stores: tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]
    ) -> None:
        _, _, composite = stores
        for i in range(3):
            composite.save(_make_session(f"id-{i}"))
        sessions = composite.list_sessions()
        assert len(sessions) == 3

    def test_close_closes_both(
        self, stores: tuple[SqliteSessionStore, JsonSessionStore, CompositeSessionStore]
    ) -> None:
        _, _, composite = stores
        composite.close()  # Should not raise
