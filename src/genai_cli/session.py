"""Session management: create, resume, save, list, clear sessions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from genai_cli.config import ConfigManager
from genai_cli.models import ChatMessage
from genai_cli.session_stores import (
    CompositeSessionStore,
    JsonSessionStore,
    SessionStore,
    SqliteSessionStore,
)
from genai_cli.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


def _build_store(config: ConfigManager) -> SessionStore:
    """Construct the appropriate session store based on config."""
    settings = config.settings
    backend = settings.session_backend
    session_dir = Path(settings.session_dir).expanduser()
    session_dir.mkdir(parents=True, exist_ok=True)

    if backend == "json":
        return JsonSessionStore(session_dir)

    db_path = Path(settings.session_db).expanduser()

    if backend == "sqlite":
        try:
            return SqliteSessionStore(db_path, json_dir=session_dir)
        except Exception:
            logger.warning("SQLite init failed, falling back to JSON")
            return JsonSessionStore(session_dir)

    # default: "both"
    json_store = JsonSessionStore(session_dir)
    try:
        sqlite_store = SqliteSessionStore(db_path, json_dir=session_dir)
        return CompositeSessionStore(sqlite_store, json_store)
    except Exception:
        logger.warning("SQLite init failed, falling back to JSON-only")
        return json_store


class SessionManager:
    """Manages persistent chat sessions."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._store = _build_store(config)

    def create_session(
        self, model_name: str | None = None
    ) -> dict[str, Any]:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        model = model_name or self._config.settings.default_model

        session: dict[str, Any] = {
            "session_id": session_id,
            "model_name": model,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "token_tracker": TokenTracker(self._config).to_dict(),
        }
        return session

    def save_session(self, session: dict[str, Any]) -> Path | None:
        """Save session to the configured store."""
        return self._store.save(session)

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        """Load a session by ID (full or prefix match)."""
        return self._store.load(session_id)

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List saved sessions, sorted by most recent first."""
        return self._store.list_sessions(limit)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self._store.delete(session_id)

    def clear_sessions(self) -> int:
        """Delete all sessions. Returns count deleted."""
        return self._store.clear()

    def close(self) -> None:
        """Release store resources (e.g. close SQLite connection)."""
        self._store.close()

    def compact_session(self, session: dict[str, Any]) -> dict[str, Any]:
        """Compact a session by keeping only a summary of messages."""
        messages = session.get("messages", [])
        if len(messages) <= 2:
            return session

        # Keep first message (for context) and last 2 exchanges
        summary_msgs = messages[:1] + messages[-4:]
        session["messages"] = summary_msgs
        return session

    def delete_old_sessions(self, max_keep: int | None = None) -> int:
        """Prune old sessions beyond the max limit."""
        limit = max_keep or self._config.settings.max_saved_sessions
        sessions = self.list_sessions(limit=9999)
        if len(sessions) <= limit:
            return 0

        to_delete = sessions[limit:]
        count = 0
        for s in to_delete:
            if self.delete_session(s["session_id"]):
                count += 1
        return count

    def add_message(
        self, session: dict[str, Any], message: ChatMessage
    ) -> None:
        """Add a message to a session."""
        session.setdefault("messages", []).append({
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp,
            "model_name": message.model_name,
            "tokens_consumed": message.tokens_consumed,
            "token_cost": message.token_cost,
        })
