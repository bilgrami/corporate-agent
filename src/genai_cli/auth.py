"""Token management: load, save, decode JWT, check expiry."""

from __future__ import annotations

import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import jwt
from dotenv import dotenv_values

from genai_cli.models import AuthToken


class AuthError(Exception):
    """Raised on authentication failures."""


def _env_path() -> Path:
    """Return the path to ~/.genai-cli/.env."""
    return Path.home() / ".genai-cli" / ".env"


class AuthManager:
    """Manages bearer token storage and validation."""

    def __init__(self, env_path: Path | None = None) -> None:
        self._env_path = env_path or _env_path()

    def load_token(self) -> AuthToken | None:
        """Load token from .env file or environment variable."""
        # Check env var first (highest priority)
        env_token = os.environ.get("GENAI_AUTH_TOKEN")
        if env_token:
            return self._decode_token(env_token)

        # Load from .env file
        if not self._env_path.is_file():
            return None

        values = dotenv_values(self._env_path)
        token = values.get("GENAI_AUTH_TOKEN", "")
        if not token:
            return None

        return self._decode_token(token)

    def save_token(self, token: str) -> None:
        """Save token to .env file with chmod 600."""
        self._env_path.parent.mkdir(parents=True, exist_ok=True)
        self._env_path.write_text(f"GENAI_AUTH_TOKEN={token}\n")
        self._env_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600

    def _decode_token(self, token: str) -> AuthToken:
        """Decode JWT without signature verification."""
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["HS256", "RS256"],
            )
        except jwt.DecodeError:
            return AuthToken(token=token)

        email = payload.get("email") or payload.get("unique_name") or payload.get(
            "preferred_username"
        )
        exp = payload.get("exp")
        iat = payload.get("iat")

        expires_at = (
            datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
        )
        issued_at = (
            datetime.fromtimestamp(iat, tz=timezone.utc) if iat else None
        )

        return AuthToken(
            token=token,
            email=email,
            expires_at=expires_at,
            issued_at=issued_at,
        )

    def is_expired(self, auth_token: AuthToken) -> bool:
        """Check if the token has expired."""
        if auth_token.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= auth_token.expires_at

    def time_remaining(self, auth_token: AuthToken) -> str:
        """Return human-readable time until expiry."""
        if auth_token.expires_at is None:
            return "unknown"
        delta = auth_token.expires_at - datetime.now(timezone.utc)
        if delta.total_seconds() <= 0:
            return "expired"
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def get_permissions(self) -> int | None:
        """Return the file permissions of the .env file, or None."""
        if not self._env_path.is_file():
            return None
        return stat.S_IMODE(self._env_path.stat().st_mode)
