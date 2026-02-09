"""Tests for client module."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import jwt
import pytest
import respx
import yaml

from genai_cli.auth import AuthError, AuthManager
from genai_cli.client import GenAIClient
from genai_cli.config import ConfigManager


@pytest.fixture
def auth_mgr(tmp_path: Path) -> AuthManager:
    """Create an AuthManager with a valid token."""
    env_path = tmp_path / ".env"
    payload = {"email": "test@test.com", "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, "secret", algorithm="HS256")
    env_path.write_text(f"GENAI_AUTH_TOKEN={token}\n")
    return AuthManager(env_path=env_path)


@pytest.fixture
def cfg(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager for testing."""
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        yaml.dump(
            {
                "api_base_url": "https://api-genai.test.com",
                "web_ui_url": "https://genai.test.com",
            }
        )
    )
    return ConfigManager(config_path=str(settings_path))


@pytest.fixture
def client(cfg: ConfigManager, auth_mgr: AuthManager) -> GenAIClient:
    return GenAIClient(cfg, auth_mgr)


class TestGenAIClient:
    @respx.mock
    def test_get_usage(self, client: GenAIClient) -> None:
        respx.get("https://api-genai.test.com/api/v1/user/usage").mock(
            return_value=httpx.Response(200, json={"tokens_used": 1000})
        )
        result = client.get_usage()
        assert result["tokens_used"] == 1000

    @respx.mock
    def test_list_history(self, client: GenAIClient) -> None:
        respx.get("https://api-genai.test.com/api/v1/chathistory/").mock(
            return_value=httpx.Response(
                200, json=[{"SessionId": "s1"}, {"SessionId": "s2"}]
            )
        )
        result = client.list_history(skip=0, limit=10)
        assert len(result) == 2
        assert result[0]["SessionId"] == "s1"

    @respx.mock
    def test_get_conversation(self, client: GenAIClient) -> None:
        respx.get("https://api-genai.test.com/api/v1/chathistory/test-123").mock(
            return_value=httpx.Response(
                200, json=[{"Message": "hello", "UserOrBot": "user"}]
            )
        )
        result = client.get_conversation("test-123")
        assert len(result) == 1

    @respx.mock
    def test_create_chat(self, client: GenAIClient) -> None:
        route = respx.get("https://api-genai.test.com/api/v1/chathistory/create").mock(
            return_value=httpx.Response(200, json={"status": "created"})
        )
        result = client.create_chat("hello", "gpt-5-chat-global")
        assert result["status"] == "created"
        assert route.called
        request = route.calls[0].request
        assert request.method == "GET"
        assert "session_id" in str(request.url)
        assert "chat_type=unified" in str(request.url)

    @respx.mock
    def test_stream_chat_two_step(self, client: GenAIClient) -> None:
        """stream_chat does create (GET) then stream (POST form-data)."""
        import json

        # Step 1: create session entry
        respx.get("https://api-genai.test.com/api/v1/chathistory/create").mock(
            return_value=httpx.Response(200, json={"status": "created"})
        )
        # Step 2: stream endpoint
        stream_body = "\n".join([
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "Hi"}], "Message": "Hi"}),
            json.dumps({"Task": "Complete", "TokensConsumed": 100, "TokenCost": 0.01, "SessionId": "s1", "Steps": [], "Message": ""}),
        ])
        stream_route = respx.post(url__regex=r".*/api/v1/conversation/.*/stream").mock(
            return_value=httpx.Response(200, text=stream_body)
        )
        resp = client.stream_chat("hello", "gpt-5-chat-global", session_id="s1")
        assert resp.status_code == 200
        assert stream_route.called
        request = stream_route.calls[0].request
        assert request.method == "POST"

    @respx.mock
    def test_stream_chat_skips_create_on_followup(self, client: GenAIClient) -> None:
        """Second stream_chat call with same session_id skips create."""
        import json

        create_route = respx.get("https://api-genai.test.com/api/v1/chathistory/create").mock(
            return_value=httpx.Response(200, json={"status": "created"})
        )
        stream_body = json.dumps({"Task": "Intermediate", "Steps": [{"data": "Hi"}], "Message": "Hi"})
        respx.post(url__regex=r".*/api/v1/conversation/.*/stream").mock(
            return_value=httpx.Response(200, text=stream_body)
        )

        # First call — creates session
        client.stream_chat("hello", "gpt-5-chat-global", session_id="s1")
        assert create_route.call_count == 1

        # Second call — skips create
        client.stream_chat("follow up", "gpt-5-chat-global", session_id="s1")
        assert create_route.call_count == 1  # still 1, not 2

    @respx.mock
    def test_upload_document(self, client: GenAIClient) -> None:
        respx.put(
            "https://api-genai.test.com/api/v1/conversation/s1/document/upload"
        ).mock(return_value=httpx.Response(200, json={"status": "ok"}))
        result = client.upload_document("s1", "file content", "code.py")
        assert result["status"] == "ok"

    @respx.mock
    def test_get_conversation_details(self, client: GenAIClient) -> None:
        respx.get(
            "https://api-genai.test.com/api/v1/conversation/s1/details"
        ).mock(return_value=httpx.Response(200, json={"details": "info"}))
        result = client.get_conversation_details("s1")
        assert result["details"] == "info"

    @respx.mock
    def test_401_raises_auth_error(self, client: GenAIClient) -> None:
        respx.get("https://api-genai.test.com/api/v1/user/usage").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        with pytest.raises(AuthError):
            client.get_usage()

    @respx.mock
    def test_headers_include_auth(self, client: GenAIClient) -> None:
        route = respx.get("https://api-genai.test.com/api/v1/user/usage").mock(
            return_value=httpx.Response(200, json={})
        )
        client.get_usage()
        assert route.called
        request = route.calls[0].request
        assert "Bearer" in request.headers.get("authorization", "")

    @respx.mock
    def test_headers_from_config(self, client: GenAIClient) -> None:
        route = respx.get("https://api-genai.test.com/api/v1/user/usage").mock(
            return_value=httpx.Response(200, json={})
        )
        client.get_usage()
        request = route.calls[0].request
        assert request.headers.get("ngrok-skip-browser-warning") == "true"

    def test_no_base_url_raises(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "s.yaml"
        settings_path.write_text(yaml.dump({"api_base_url": ""}))
        cfg = ConfigManager(config_path=str(settings_path))
        env_path = tmp_path / ".env"
        env_path.write_text("GENAI_AUTH_TOKEN=abc\n")
        auth = AuthManager(env_path=env_path)
        c = GenAIClient(cfg, auth)
        with pytest.raises(AuthError, match="API base URL"):
            c.get_usage()

    def test_no_token_raises(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "s.yaml"
        settings_path.write_text(
            yaml.dump({"api_base_url": "https://api.test.com"})
        )
        cfg = ConfigManager(config_path=str(settings_path))
        auth = AuthManager(env_path=tmp_path / "nonexistent" / ".env")
        c = GenAIClient(cfg, auth)
        with pytest.raises(AuthError, match="No auth token"):
            c.get_usage()

    def test_parse_message(
        self, client: GenAIClient, mock_chat_response: dict[str, Any]
    ) -> None:
        msg = client.parse_message(mock_chat_response)
        assert msg.role == "assistant"
        assert msg.content == "Hello! How can I help you?"
        assert msg.tokens_consumed == 150
        assert msg.session_id == "test-session-123"

    @respx.mock
    def test_ensure_session_creates_once(self, client: GenAIClient) -> None:
        """ensure_session() calls create_chat only on first call for a session."""
        create_route = respx.get("https://api-genai.test.com/api/v1/chathistory/create").mock(
            return_value=httpx.Response(200, json={"status": "created"})
        )
        client.ensure_session("sid-1", "gpt-5-chat-global")
        assert create_route.call_count == 1

        # Second call with same session — skips create
        client.ensure_session("sid-1", "gpt-5-chat-global")
        assert create_route.call_count == 1

    @respx.mock
    def test_ensure_session_returns_session_id(self, client: GenAIClient) -> None:
        """ensure_session() returns the session_id passed in."""
        respx.get("https://api-genai.test.com/api/v1/chathistory/create").mock(
            return_value=httpx.Response(200, json={"status": "created"})
        )
        result = client.ensure_session("my-sid", "gpt-5-chat-global")
        assert result == "my-sid"

    def test_mark_session_created(self, client: GenAIClient) -> None:
        """mark_session_created() prevents ensure_session from calling create."""
        client.mark_session_created("pre-existing-sid")
        # No HTTP mock needed — ensure_session should not make any call
        result = client.ensure_session("pre-existing-sid", "gpt-5-chat-global")
        assert result == "pre-existing-sid"

    @respx.mock
    def test_create_chat_timestamp_locale_format(self, client: GenAIClient) -> None:
        """create_chat() uses locale-style timestamp matching browser format."""
        route = respx.get("https://api-genai.test.com/api/v1/chathistory/create").mock(
            return_value=httpx.Response(200, json={"status": "created"})
        )
        client.create_chat("hello", "gpt-5-chat-global")
        request = route.calls[0].request
        ts = str(request.url.params.get("timestamp", ""))
        # Should be like "2/8/2026, 07:41:45 PM" not ISO format
        assert "T" not in ts
        assert "," in ts

    def test_close(self, client: GenAIClient) -> None:
        # Should not raise even if client not initialized
        client.close()
