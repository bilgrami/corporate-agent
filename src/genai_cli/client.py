"""HTTP client for the corporate AI chat API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from genai_cli.auth import AuthError, AuthManager
from genai_cli.config import ConfigManager
from genai_cli.mapper import ResponseMapper
from genai_cli.models import ChatMessage


_MAX_UPLOAD_BYTES = 200_000


class GenAIClient:
    """Synchronous HTTP client for the corporate GenAI API."""

    def __init__(
        self,
        config: ConfigManager,
        auth: AuthManager,
    ) -> None:
        self._config = config
        self._auth = auth
        self._mapper = config.mapper
        self._client: httpx.Client | None = None
        self._created_sessions: set[str] = set()

    def _get_client(self) -> httpx.Client:
        """Lazily create and return an httpx.Client."""
        if self._client is None:
            base_url = self._config.settings.api_base_url
            if not base_url:
                raise AuthError("API base URL not configured. Run 'genai auth login'.")

            token_obj = self._auth.load_token()
            if token_obj is None:
                raise AuthError("No auth token found. Run 'genai auth login'.")

            headers = self._config.get_headers()
            headers["authorization"] = f"Bearer {token_obj.token}"

            self._client = httpx.Client(
                base_url=base_url,
                headers=headers,
                timeout=60.0,
            )
        return self._client

    def _handle_response(self, resp: httpx.Response) -> Any:
        """Handle response, raising AuthError on 401."""
        if resp.status_code == 401:
            raise AuthError("Token expired or invalid. Run 'genai auth login'.")
        resp.raise_for_status()
        return resp.json()

    def get_usage(self) -> dict[str, Any]:
        """GET usage endpoint."""
        client = self._get_client()
        resp = client.get(self._mapper.endpoint("usage"))
        result: dict[str, Any] = self._handle_response(resp)
        return result

    def list_history(
        self, skip: int = 0, limit: int = 20
    ) -> list[dict[str, Any]]:
        """GET chat history list."""
        client = self._get_client()
        resp = client.get(
            self._mapper.endpoint("chat_history"),
            params={"skip": skip, "limit": limit},
        )
        result: list[dict[str, Any]] = self._handle_response(resp)
        return result

    def get_conversation(self, session_id: str) -> list[dict[str, Any]]:
        """GET conversation messages."""
        client = self._get_client()
        resp = client.get(self._mapper.endpoint("conversation", session_id=session_id))
        result: list[dict[str, Any]] = self._handle_response(resp)
        return result

    def ensure_session(self, session_id: str, model: str = "") -> str:
        """Create session on the API if not already registered. Returns the session_id."""
        if session_id not in self._created_sessions:
            self.create_chat("", model, session_id)
            self._created_sessions.add(session_id)
        return session_id

    def mark_session_created(self, session_id: str) -> None:
        """Mark a session as already created (e.g., from web UI env var)."""
        self._created_sessions.add(session_id)

    def create_chat(
        self,
        message: str,
        model: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new chat session entry."""
        client = self._get_client()
        sid = session_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        ts = f"{now.month}/{now.day}/{now.year}, {now.strftime('%I:%M:%S %p')}"
        method = self._mapper.endpoint_method("chat_create")

        resp = client.request(
            method,
            self._mapper.endpoint("chat_create"),
            params={"chat_type": "unified", "timestamp": ts, "session_id": sid},
        )
        result: dict[str, Any] = self._handle_response(resp)
        return result

    def upload_document(
        self,
        session_id: str,
        content: str,
        filename: str = "blob.txt",
    ) -> dict[str, Any]:
        """PUT document upload."""
        client = self._get_client()
        resp = client.put(
            self._mapper.endpoint("document_upload", session_id=session_id),
            files={"file": (filename, content.encode(), "text/plain")},
        )
        result: dict[str, Any] = self._handle_response(resp)
        return result

    def _split_bundle_content(self, content: str) -> list[str]:
        """Split large content into uploadable chunks."""
        encoded = content.encode()
        if len(encoded) <= _MAX_UPLOAD_BYTES:
            return [content]

        # Try splitting at ===== FILE: boundaries
        marker = "===== FILE:"
        parts = content.split(marker)
        if len(parts) <= 1:
            # No markers — split at line boundaries
            return self._split_by_lines(content)

        chunks: list[str] = []
        current = parts[0]  # header before first marker
        for part in parts[1:]:
            candidate = current + marker + part
            if len(candidate.encode()) > _MAX_UPLOAD_BYTES and current.strip():
                chunks.append(current)
                current = marker + part
            else:
                current = candidate
        if current.strip():
            chunks.append(current)
        return chunks

    def _split_by_lines(self, content: str) -> list[str]:
        """Split content at line boundaries into chunks."""
        lines = content.split("\n")
        chunks: list[str] = []
        current: list[str] = []
        size = 0
        for line in lines:
            line_size = len(line.encode()) + 1
            if size + line_size > _MAX_UPLOAD_BYTES and current:
                chunks.append("\n".join(current))
                current = []
                size = 0
            current.append(line)
            size += line_size
        if current:
            chunks.append("\n".join(current))
        return chunks

    def upload_bundles(
        self,
        session_id: str,
        bundles: list[Any],
    ) -> list[dict[str, Any]]:
        """Upload multiple file bundles, splitting large ones into chunks."""
        results: list[dict[str, Any]] = []
        for bundle in bundles:
            chunks = self._split_bundle_content(bundle.content)
            for chunk in chunks:
                result = self.upload_document(session_id, chunk, "blob.txt")
                results.append(result)
        return results

    def get_conversation_details(self, session_id: str) -> dict[str, Any]:
        """GET conversation document details."""
        client = self._get_client()
        resp = client.get(
            self._mapper.endpoint("conversation_details", session_id=session_id)
        )
        result: dict[str, Any] = self._handle_response(resp)
        return result

    def stream_chat(
        self,
        message: str,
        model: str,
        session_id: str | None = None,
    ) -> httpx.Response:
        """Two-step flow: create session entry, then stream the response."""
        client = self._get_client()
        sid = session_id or str(uuid.uuid4())

        # Step 1: Create session entry (first message only)
        if sid not in self._created_sessions:
            self.create_chat(message, model, sid)
            self._created_sessions.add(sid)

        # Step 2: Stream from the stream endpoint
        content_type = self._mapper.endpoint_content_type("stream")
        payload = self._mapper.build_stream_payload(message=message, model_name=model)

        if content_type == "multipart/form-data":
            resp = client.post(
                self._mapper.endpoint("stream", session_id=sid),
                data=payload,
                headers={"accept": "*/*"},
            )
        else:
            resp = client.post(
                self._mapper.endpoint("stream", session_id=sid),
                json=payload,
                headers={"accept": "text/event-stream"},
            )
        if resp.status_code == 401:
            raise AuthError("Token expired or invalid. Run 'genai auth login'.")
        resp.raise_for_status()
        return resp

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def parse_message(self, data: dict[str, Any]) -> ChatMessage:
        """Parse an API response dict into a ChatMessage using the mapper."""
        return self._mapper.map_message(data)
