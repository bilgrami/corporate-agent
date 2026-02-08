"""Tests for CLI commands."""

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
from click.testing import CliRunner

from genai_cli.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_env(tmp_path: Path) -> dict[str, str]:
    """Set up mock auth environment."""
    payload = {"email": "test@test.com", "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, "secret", algorithm="HS256")
    env_path = tmp_path / ".genai-cli" / ".env"
    env_path.parent.mkdir(parents=True)
    env_path.write_text(f"GENAI_AUTH_TOKEN={token}\n")

    settings_path = tmp_path / ".genai-cli" / "settings.yaml"
    settings_path.write_text(
        yaml.dump(
            {
                "api_base_url": "https://api-genai.test.com",
                "web_ui_url": "https://genai.test.com",
            }
        )
    )

    return {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}


class TestCLI:
    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Corporate AI CLI Agent" in result.output

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_no_subcommand_launches_repl(self, runner: CliRunner) -> None:
        # With no subcommand, REPL launches (and exits on EOF from CliRunner)
        result = runner.invoke(main)
        assert result.exit_code == 0
        assert "Corporate AI CLI" in result.output

    def test_models(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["models"])
        assert result.exit_code == 0
        assert "GPT-5" in result.output

    @respx.mock
    def test_ask_no_stream(
        self, runner: CliRunner, mock_env: dict[str, str]
    ) -> None:
        respx.post("https://api-genai.test.com/api/v1/chathistory/create").mock(
            return_value=httpx.Response(
                200,
                json={
                    "SessionId": "s1",
                    "Message": "Hello back!",
                    "UserOrBot": "assistant",
                    "TokensConsumed": 50,
                    "TokenCost": 0.001,
                    "ModelName": "gpt-5-chat-global",
                    "DisplayName": "GPT-5",
                    "TimestampUTC": "2026-02-07T12:00:00Z",
                },
            )
        )
        with patch.dict("os.environ", mock_env):
            result = runner.invoke(main, ["ask", "hello", "--no-stream"])
        assert result.exit_code == 0
        assert "Hello back!" in result.output

    def test_ask_no_auth(self, runner: CliRunner, tmp_path: Path) -> None:
        env = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
        with patch.dict("os.environ", env):
            result = runner.invoke(main, ["ask", "hello", "--no-stream"])
        assert result.exit_code != 0

    @respx.mock
    def test_history(
        self, runner: CliRunner, mock_env: dict[str, str]
    ) -> None:
        respx.get("https://api-genai.test.com/api/v1/chathistory/").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"SessionId": "s1", "ModelName": "gpt-5", "TimestampUTC": "2026-02-07T12:00:00Z"},
                ],
            )
        )
        with patch.dict("os.environ", mock_env):
            result = runner.invoke(main, ["history"])
        assert result.exit_code == 0

    @respx.mock
    def test_usage(
        self, runner: CliRunner, mock_env: dict[str, str]
    ) -> None:
        respx.get("https://api-genai.test.com/api/v1/user/usage").mock(
            return_value=httpx.Response(200, json={"total_tokens": 5000})
        )
        with patch.dict("os.environ", mock_env):
            result = runner.invoke(main, ["usage"])
        assert result.exit_code == 0

    def test_config_get(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["config", "get", "default_model"])
        assert result.exit_code == 0
        assert "default_model" in result.output

    def test_config_set(self, runner: CliRunner, tmp_path: Path) -> None:
        env = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
        with patch.dict("os.environ", env):
            result = runner.invoke(
                main, ["config", "set", "auto_apply", "true"]
            )
        assert result.exit_code == 0
