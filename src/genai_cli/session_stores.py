"""Session storage backends: JSON, SQLite, and composite dual-write."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SessionStore(Protocol):
    """Interface for session persistence backends."""

    def save(self, session: dict[str, Any]) -> Path | None: ...

    def load(self, session_id: str) -> dict[str, Any] | None: ...

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]: ...

    def delete(self, session_id: str) -> bool: ...

    def clear(self) -> int: ...

    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# JSON store (extracted from existing SessionManager logic)
# ---------------------------------------------------------------------------


class JsonSessionStore:
    """Persists sessions as individual JSON files on disk."""

    def __init__(self, session_dir: Path) -> None:
        self._session_dir = session_dir
        self._session_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: dict[str, Any]) -> Path | None:
        sid = session["session_id"]
        path = self._session_dir / f"{sid}.json"
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(session, indent=2, default=str))
        return path

    def load(self, session_id: str) -> dict[str, Any] | None:
        # Exact match
        path = self._session_dir / f"{session_id}.json"
        if path.is_file():
            return json.loads(path.read_text())
        # Prefix match
        for p in self._session_dir.glob("*.json"):
            if p.stem.startswith(session_id):
                return json.loads(p.read_text())
        return None

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        for p in self._session_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                sessions.append({
                    "session_id": data.get("session_id", p.stem),
                    "model_name": data.get("model_name", ""),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                })
            except (json.JSONDecodeError, OSError):
                continue
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions[:limit]

    def delete(self, session_id: str) -> bool:
        path = self._session_dir / f"{session_id}.json"
        if path.is_file():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        count = 0
        for p in self._session_dir.glob("*.json"):
            p.unlink()
            count += 1
        return count

    def close(self) -> None:
        pass  # No resources to release


# ---------------------------------------------------------------------------
# SQLite store
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    model_name    TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL,
    updated_at    TEXT,
    token_tracker TEXT,
    title         TEXT DEFAULT '',
    tags          TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role          TEXT NOT NULL,
    content       TEXT NOT NULL,
    timestamp     TEXT DEFAULT '',
    model_name    TEXT DEFAULT '',
    tokens_consumed INTEGER DEFAULT 0,
    token_cost    REAL DEFAULT 0.0,
    position      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, position);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
"""


class SqliteSessionStore:
    """Persists sessions in a SQLite database."""

    def __init__(self, db_path: Path, json_dir: Path | None = None) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA_SQL)
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            logger.warning("SQLite DB corrupt or unreadable: %s", exc)
            raise

        # Migrate existing JSON sessions if needed
        if json_dir is not None:
            self._migrate_from_json(json_dir)

    def _migrate_from_json(self, json_dir: Path) -> None:
        """Import JSON session files that haven't been migrated yet."""
        cursor = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'migrated_from_json'"
        )
        if cursor.fetchone() is not None:
            return  # Already migrated

        if not json_dir.is_dir():
            return

        count = 0
        for p in json_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                self._insert_session(data)
                count += 1
            except (json.JSONDecodeError, OSError, sqlite3.Error):
                continue

        self._conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("migrated_from_json", datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()
        if count:
            logger.info("Migrated %d JSON sessions to SQLite", count)

    def _insert_session(self, session: dict[str, Any]) -> None:
        """Insert a full session dict (with messages) into the database."""
        sid = session["session_id"]
        tracker = session.get("token_tracker")
        tracker_json = json.dumps(tracker, default=str) if tracker else None

        self._conn.execute(
            "INSERT OR REPLACE INTO sessions "
            "(session_id, model_name, created_at, updated_at, token_tracker, title, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                sid,
                session.get("model_name", ""),
                session.get("created_at", ""),
                session.get("updated_at", ""),
                tracker_json,
                session.get("title", ""),
                session.get("tags", ""),
            ),
        )

        # Delete old messages for this session (idempotent re-insert)
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))

        for pos, msg in enumerate(session.get("messages", [])):
            self._conn.execute(
                "INSERT INTO messages "
                "(session_id, role, content, timestamp, model_name, "
                "tokens_consumed, token_cost, position) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sid,
                    msg.get("role", ""),
                    msg.get("content", ""),
                    msg.get("timestamp", ""),
                    msg.get("model_name", ""),
                    msg.get("tokens_consumed", 0),
                    msg.get("token_cost", 0.0),
                    pos,
                ),
            )

    def _load_session_dict(self, row: tuple[Any, ...]) -> dict[str, Any]:
        """Reconstruct a session dict from a sessions row + messages."""
        sid, model_name, created_at, updated_at, tracker_json, title, tags = row
        session: dict[str, Any] = {
            "session_id": sid,
            "model_name": model_name,
            "created_at": created_at,
            "updated_at": updated_at or "",
            "title": title or "",
            "tags": tags or "",
            "messages": [],
        }
        if tracker_json:
            try:
                session["token_tracker"] = json.loads(tracker_json)
            except json.JSONDecodeError:
                pass

        cursor = self._conn.execute(
            "SELECT role, content, timestamp, model_name, tokens_consumed, token_cost "
            "FROM messages WHERE session_id = ? ORDER BY position",
            (sid,),
        )
        for msg_row in cursor:
            session["messages"].append({
                "role": msg_row[0],
                "content": msg_row[1],
                "timestamp": msg_row[2],
                "model_name": msg_row[3],
                "tokens_consumed": msg_row[4],
                "token_cost": msg_row[5],
            })
        return session

    def save(self, session: dict[str, Any]) -> Path | None:
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._insert_session(session)
        self._conn.commit()
        return None  # No file path for SQLite

    def load(self, session_id: str) -> dict[str, Any] | None:
        # Exact match
        cursor = self._conn.execute(
            "SELECT session_id, model_name, created_at, updated_at, "
            "token_tracker, title, tags FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row:
            return self._load_session_dict(row)

        # Prefix match
        cursor = self._conn.execute(
            "SELECT session_id, model_name, created_at, updated_at, "
            "token_tracker, title, tags FROM sessions "
            "WHERE session_id LIKE ? || '%' LIMIT 1",
            (session_id,),
        )
        row = cursor.fetchone()
        if row:
            return self._load_session_dict(row)

        return None

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        cursor = self._conn.execute(
            "SELECT s.session_id, s.model_name, s.created_at, s.updated_at, "
            "COUNT(m.id) as message_count "
            "FROM sessions s LEFT JOIN messages m ON s.session_id = m.session_id "
            "GROUP BY s.session_id "
            "ORDER BY s.updated_at DESC LIMIT ?",
            (limit,),
        )
        return [
            {
                "session_id": row[0],
                "model_name": row[1],
                "created_at": row[2],
                "updated_at": row[3] or "",
                "message_count": row[4],
            }
            for row in cursor
        ]

    def delete(self, session_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM sessions WHERE session_id = ?", (session_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def clear(self) -> int:
        cursor = self._conn.execute("SELECT COUNT(*) FROM sessions")
        count = cursor.fetchone()[0]
        self._conn.execute("DELETE FROM messages")
        self._conn.execute("DELETE FROM sessions")
        self._conn.commit()
        return count

    def close(self) -> None:
        if self._conn:
            self._conn.close()


# ---------------------------------------------------------------------------
# Composite store (dual-write orchestrator)
# ---------------------------------------------------------------------------


class CompositeSessionStore:
    """Writes to both JSON and SQLite stores, reads from SQLite first."""

    def __init__(
        self, primary: SessionStore, secondary: SessionStore
    ) -> None:
        self._primary = primary  # SQLite (preferred for reads)
        self._secondary = secondary  # JSON (for portability)

    def save(self, session: dict[str, Any]) -> Path | None:
        result: Path | None = None
        # Write to primary first
        try:
            self._primary.save(session)
        except Exception:
            logger.warning("Primary store save failed", exc_info=True)

        # Write to secondary
        try:
            result = self._secondary.save(session)
        except Exception:
            logger.warning("Secondary store save failed", exc_info=True)

        return result  # Return JSON path for backward compat

    def load(self, session_id: str) -> dict[str, Any] | None:
        # Try primary (SQLite) first
        result = self._primary.load(session_id)
        if result is not None:
            return result
        # Fall back to secondary (JSON)
        return self._secondary.load(session_id)

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        # Use primary (SQLite) — faster with ORDER BY + LIMIT
        return self._primary.list_sessions(limit)

    def delete(self, session_id: str) -> bool:
        deleted_primary = self._primary.delete(session_id)
        deleted_secondary = self._secondary.delete(session_id)
        return deleted_primary or deleted_secondary

    def clear(self) -> int:
        count_primary = self._primary.clear()
        self._secondary.clear()
        return count_primary

    def close(self) -> None:
        self._primary.close()
        self._secondary.close()
