"""Session management: create, resume, save, list, clear sessions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from genai_cli.config import ConfigManager
from genai_cli.models import ChatMessage
from genai_cli.token_tracker import TokenTracker


class SessionManager:
    """Manages persistent chat sessions."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        session_dir = config.settings.session_dir
        self._session_dir = Path(session_dir).expanduser()
        self._session_dir.mkdir(parents=True, exist_ok=True)

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

    def save_session(self, session: dict[str, Any]) -> Path:
        """Save session to disk."""
        sid = session["session_id"]
        path = self._session_dir / f"{sid}.json"
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(session, indent=2, default=str))
        return path

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        """Load a session by ID (full or prefix match)."""
        # Try exact match first
        path = self._session_dir / f"{session_id}.json"
        if path.is_file():
            return json.loads(path.read_text())

        # Try prefix match
        for p in self._session_dir.glob("*.json"):
            if p.stem.startswith(session_id):
                return json.loads(p.read_text())

        return None

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List saved sessions, sorted by most recent first."""
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

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file."""
        path = self._session_dir / f"{session_id}.json"
        if path.is_file():
            path.unlink()
            return True
        return False

    def clear_sessions(self) -> int:
        """Delete all session files. Returns count deleted."""
        count = 0
        for p in self._session_dir.glob("*.json"):
            p.unlink()
            count += 1
        return count

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
