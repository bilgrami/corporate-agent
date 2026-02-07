"""Tests for auth module."""

from __future__ import annotations

import os
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest

from genai_cli.auth import AuthError, AuthManager
from genai_cli.models import AuthToken


class TestAuthManager:
    def test_save_token(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".genai-cli" / ".env"
        mgr = AuthManager(env_path=env_path)
        mgr.save_token("test-token-123")
        assert env_path.is_file()
        assert "GENAI_AUTH_TOKEN=test-token-123" in env_path.read_text()

    def test_save_token_permissions(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".genai-cli" / ".env"
        mgr = AuthManager(env_path=env_path)
        mgr.save_token("test-token")
        mode = stat.S_IMODE(env_path.stat().st_mode)
        assert mode == 0o600

    def test_load_token_from_file(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        payload = {"email": "test@test.com", "exp": int(time.time()) + 3600}
        token = jwt.encode(payload, "secret", algorithm="HS256")
        env_path.write_text(f"GENAI_AUTH_TOKEN={token}\n")

        mgr = AuthManager(env_path=env_path)
        result = mgr.load_token()
        assert result is not None
        assert result.email == "test@test.com"

    def test_load_token_from_env(self, tmp_path: Path) -> None:
        env_path = tmp_path / "nonexistent" / ".env"
        payload = {"email": "env@test.com", "exp": int(time.time()) + 3600}
        token = jwt.encode(payload, "secret", algorithm="HS256")

        mgr = AuthManager(env_path=env_path)
        with patch.dict(os.environ, {"GENAI_AUTH_TOKEN": token}):
            result = mgr.load_token()
            assert result is not None
            assert result.email == "env@test.com"

    def test_load_token_missing(self, tmp_path: Path) -> None:
        env_path = tmp_path / "nonexistent" / ".env"
        mgr = AuthManager(env_path=env_path)
        result = mgr.load_token()
        assert result is None

    def test_jwt_decode(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        exp_time = int(time.time()) + 7200
        payload = {
            "email": "user@corp.com",
            "exp": exp_time,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        env_path.write_text(f"GENAI_AUTH_TOKEN={token}\n")

        mgr = AuthManager(env_path=env_path)
        result = mgr.load_token()
        assert result is not None
        assert result.email == "user@corp.com"
        assert result.expires_at is not None
        assert result.issued_at is not None

    def test_is_expired_false(self) -> None:
        mgr = AuthManager()
        token = AuthToken(
            token="x",
            expires_at=datetime.fromtimestamp(
                time.time() + 3600, tz=timezone.utc
            ),
        )
        assert mgr.is_expired(token) is False

    def test_is_expired_true(self) -> None:
        mgr = AuthManager()
        token = AuthToken(
            token="x",
            expires_at=datetime.fromtimestamp(
                time.time() - 3600, tz=timezone.utc
            ),
        )
        assert mgr.is_expired(token) is True

    def test_is_expired_no_expiry(self) -> None:
        mgr = AuthManager()
        token = AuthToken(token="x", expires_at=None)
        assert mgr.is_expired(token) is False

    def test_time_remaining(self) -> None:
        mgr = AuthManager()
        token = AuthToken(
            token="x",
            expires_at=datetime.fromtimestamp(
                time.time() + 7200, tz=timezone.utc
            ),
        )
        remaining = mgr.time_remaining(token)
        assert "h" in remaining or "m" in remaining

    def test_token_repr_no_secret(self, mock_auth_token: AuthToken) -> None:
        r = repr(mock_auth_token)
        assert mock_auth_token.token not in r
        assert "email=" in r

    def test_get_permissions(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        mgr = AuthManager(env_path=env_path)
        assert mgr.get_permissions() is None

        env_path.write_text("TOKEN=x\n")
        env_path.chmod(0o600)
        assert mgr.get_permissions() == 0o600

    def test_invalid_jwt(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        env_path.write_text("GENAI_AUTH_TOKEN=not-a-jwt\n")
        mgr = AuthManager(env_path=env_path)
        result = mgr.load_token()
        assert result is not None
        assert result.token == "not-a-jwt"
        assert result.email is None
