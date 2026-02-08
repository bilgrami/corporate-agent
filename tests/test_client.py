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
        respx.post("https://api-genai.test.com/api/v1/chathistory/create").mock(
            return_value=httpx.Response(
                200,
                json={
                    "SessionId": "new-session",
                    "Message": "Hi!",
                    "UserOrBot": "assistant",
                    "TokensConsumed": 100,
                },
            )
        )
        result = client.create_chat("hello", "gpt-5-chat-global")
        assert result["Message"] == "Hi!"

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

    def test_close(self, client: GenAIClient) -> None:
        # Should not raise even if client not initialized
        client.close()
