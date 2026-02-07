"""HTTP client for the corporate AI chat API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from genai_cli.auth import AuthError, AuthManager
from genai_cli.config import ConfigManager
from genai_cli.models import ChatMessage


class GenAIClient:
    """Synchronous HTTP client for the corporate GenAI API."""

    def __init__(
        self,
        config: ConfigManager,
        auth: AuthManager,
    ) -> None:
        self._config = config
        self._auth = auth
        self._client: httpx.Client | None = None

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
        """GET /api/v1/user/usage."""
        client = self._get_client()
        resp = client.get("/api/v1/user/usage")
        result: dict[str, Any] = self._handle_response(resp)
        return result

    def list_history(
        self, skip: int = 0, limit: int = 20
    ) -> list[dict[str, Any]]:
        """GET /api/v1/chathistory/?skip={n}&limit={n}."""
        client = self._get_client()
        resp = client.get(
            "/api/v1/chathistory/",
            params={"skip": skip, "limit": limit},
        )
        result: list[dict[str, Any]] = self._handle_response(resp)
        return result

    def get_conversation(self, session_id: str) -> list[dict[str, Any]]:
        """GET /api/v1/chathistory/{session_id}."""
        client = self._get_client()
        resp = client.get(f"/api/v1/chathistory/{session_id}")
        result: list[dict[str, Any]] = self._handle_response(resp)
        return result

    def create_chat(
        self,
        message: str,
        model: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/chathistory/create."""
        client = self._get_client()
        sid = session_id or str(uuid.uuid4())
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {
            "SessionId": sid,
            "Message": message,
            "ModelName": model,
        }

        resp = client.post(
            "/api/v1/chathistory/create",
            params={
                "chat_type": "unified",
                "timestamp": ts,
                "session_id": sid,
            },
            json=payload,
        )
        result: dict[str, Any] = self._handle_response(resp)
        return result

    def upload_document(
        self,
        session_id: str,
        content: str,
        filename: str = "upload.txt",
    ) -> dict[str, Any]:
        """PUT /api/v1/conversation/{id}/document/upload."""
        client = self._get_client()
        resp = client.put(
            f"/api/v1/conversation/{session_id}/document/upload",
            files={"file": (filename, content.encode(), "text/plain")},
        )
        result: dict[str, Any] = self._handle_response(resp)
        return result

    def get_conversation_details(self, session_id: str) -> dict[str, Any]:
        """GET /api/v1/conversation/{id}/details."""
        client = self._get_client()
        resp = client.get(f"/api/v1/conversation/{session_id}/details")
        result: dict[str, Any] = self._handle_response(resp)
        return result

    def stream_chat(
        self,
        message: str,
        model: str,
        session_id: str | None = None,
    ) -> httpx.Response:
        """POST to create chat and return streaming response."""
        client = self._get_client()
        sid = session_id or str(uuid.uuid4())
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {
            "SessionId": sid,
            "Message": message,
            "ModelName": model,
        }

        resp = client.post(
            "/api/v1/chathistory/create",
            params={
                "chat_type": "unified",
                "timestamp": ts,
                "session_id": sid,
            },
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

    @staticmethod
    def parse_message(data: dict[str, Any]) -> ChatMessage:
        """Parse an API response dict into a ChatMessage."""
        return ChatMessage(
            session_id=data.get("SessionId", ""),
            role="assistant" if data.get("UserOrBot") == "assistant" else "user",
            content=data.get("Message", ""),
            timestamp=data.get("TimestampUTC", ""),
            model_name=data.get("ModelName", ""),
            display_name=data.get("DisplayName", ""),
            tokens_consumed=data.get("TokensConsumed", 0),
            token_cost=data.get("TokenCost", 0.0),
            upload_content=data.get("UploadContent"),
        )
