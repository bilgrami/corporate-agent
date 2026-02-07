"""Shared test fixtures."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import jwt
import pytest
import yaml

from genai_cli.config import ConfigManager
from genai_cli.models import AuthToken, ModelInfo


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def config_dir(project_root: Path) -> Path:
    """Return the config directory."""
    return project_root / "config"


@pytest.fixture
def mock_config(tmp_path: Path, project_root: Path) -> ConfigManager:
    """Create a ConfigManager with test overrides."""
    # Create a temporary settings file pointing to real config
    settings = {
        "api_base_url": "https://api-genai.test.com",
        "web_ui_url": "https://genai.test.com",
        "default_model": "gpt-5-chat-global",
        "agent_name": "test-agent",
    }
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(yaml.dump(settings))

    return ConfigManager(config_path=str(settings_path))


@pytest.fixture
def mock_auth_token() -> AuthToken:
    """Create a mock valid auth token."""
    payload = {
        "email": "dev@test.com",
        "exp": int(time.time()) + 3600,  # 1 hour from now
        "iat": int(time.time()),
    }
    token_str = jwt.encode(payload, "secret", algorithm="HS256")
    from datetime import datetime, timezone

    return AuthToken(
        token=token_str,
        email="dev@test.com",
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
    )


@pytest.fixture
def expired_auth_token() -> AuthToken:
    """Create a mock expired auth token."""
    payload = {
        "email": "dev@test.com",
        "exp": int(time.time()) - 3600,  # 1 hour ago
        "iat": int(time.time()) - 7200,
    }
    token_str = jwt.encode(payload, "secret", algorithm="HS256")
    from datetime import datetime, timezone

    return AuthToken(
        token=token_str,
        email="dev@test.com",
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
    )


@pytest.fixture
def mock_chat_response() -> dict[str, Any]:
    """Return a mock API chat response."""
    return {
        "SessionId": "test-session-123",
        "TableId": None,
        "UserOrBot": "assistant",
        "Message": "Hello! How can I help you?",
        "TimestampUTC": "2026-02-07T12:00:00Z",
        "ModelName": "gpt-5-chat-global",
        "DisplayName": "GPT-5",
        "Vote": 0,
        "TokensConsumed": 150,
        "TokenCost": 0.00276,
        "UploadContent": None,
        "WebSearchInfo": None,
        "Images": None,
        "Audios": None,
        "Steps": [],
        "UserEmail": "dev@test.com",
        "IsArchieved": False,
    }


@pytest.fixture
def mock_models() -> dict[str, ModelInfo]:
    """Return mock model registry."""
    return {
        "gpt-5-chat-global": ModelInfo(
            name="gpt-5-chat-global",
            display_name="GPT-5",
            provider="openai",
            tier="full",
            context_window=128000,
            max_output_tokens=16384,
            cost_per_1k_input=0.005,
            cost_per_1k_output=0.015,
        ),
        "claude-sonnet-4-5-global": ModelInfo(
            name="claude-sonnet-4-5-global",
            display_name="Claude Sonnet 4.5",
            provider="anthropic",
            tier="full",
            context_window=200000,
            max_output_tokens=16384,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        ),
    }


@pytest.fixture
def sample_python_file(tmp_path: Path) -> Path:
    """Create a sample Python file for testing."""
    f = tmp_path / "sample.py"
    f.write_text('def hello():\n    return "hello"\n')
    return f


@pytest.fixture
def sample_project_dir(tmp_path: Path) -> Path:
    """Create a sample project directory structure."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text('print("hello")\n')
    (src / "utils.py").write_text('def add(a, b):\n    return a + b\n')

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Test Project\n")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text('def test_hello():\n    pass\n')

    # Files that should be excluded
    pycache = src / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-310.pyc").write_bytes(b"bytecode")

    (tmp_path / ".env").write_text("SECRET=value\n")

    return tmp_path
