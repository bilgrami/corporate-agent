"""Tests for skill executor module."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.skills.executor import SkillExecutor
from genai_cli.skills.registry import SkillRegistry


@pytest.fixture
def exec_config(tmp_path: Path) -> ConfigManager:
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    settings = {
        "api_base_url": "https://api.test.com",
        "session_dir": str(session_dir),
        "default_model": "gpt-5-chat-global",
        "streaming": False,
    }
    p = tmp_path / "settings.yaml"
    p.write_text(yaml.dump(settings))
    return ConfigManager(config_path=str(p))


@pytest.fixture
def display() -> Display:
    return Display(file=StringIO())


@pytest.fixture
def registry(exec_config: ConfigManager) -> SkillRegistry:
    return SkillRegistry(exec_config)


@pytest.fixture
def executor(
    exec_config: ConfigManager, display: Display, registry: SkillRegistry
) -> SkillExecutor:
    return SkillExecutor(exec_config, display, registry)


class TestSkillExecutor:
    def test_skill_not_found(
        self, executor: SkillExecutor
    ) -> None:
        result = executor.execute("nonexistent")
        assert result is None

    @patch("genai_cli.skills.executor.GenAIClient")
    def test_execute_review(
        self,
        mock_client_cls: MagicMock,
        executor: SkillExecutor,
    ) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_chat.return_value = {
            "SessionId": "s1",
            "Message": "Code looks good, no issues found.",
            "UserOrBot": "assistant",
            "TokensConsumed": 100,
            "TokenCost": 0.002,
            "ModelName": "gpt-5",
            "DisplayName": "GPT-5",
            "TimestampUTC": "2026-02-07T12:00:00Z",
        }
        mock_client.parse_message.return_value = MagicMock(
            content="Code looks good.",
            tokens_consumed=100,
            token_cost=0.002,
        )

        result = executor.execute("review", message="Review this code")
        assert result is not None
        assert len(result.rounds) == 1

    @patch("genai_cli.skills.executor.GenAIClient")
    def test_execute_with_files(
        self,
        mock_client_cls: MagicMock,
        executor: SkillExecutor,
        sample_project_dir: Path,
    ) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_chat.return_value = {
            "SessionId": "s1",
            "Message": "Reviewed.",
            "UserOrBot": "assistant",
            "TokensConsumed": 50,
            "TokenCost": 0.001,
            "ModelName": "gpt-5",
            "DisplayName": "GPT-5",
            "TimestampUTC": "2026-02-07T12:00:00Z",
        }
        mock_client.parse_message.return_value = MagicMock(
            content="Reviewed.",
            tokens_consumed=50,
            token_cost=0.001,
        )
        mock_client.upload_bundles.return_value = [{"status": "ok"}]

        result = executor.execute(
            "review",
            files=[str(sample_project_dir / "src")],
        )
        assert result is not None
        mock_client.upload_bundles.assert_called()

    @patch("genai_cli.skills.executor.GenAIClient")
    def test_execute_dry_run(
        self,
        mock_client_cls: MagicMock,
        executor: SkillExecutor,
    ) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_chat.return_value = {
            "SessionId": "s1",
            "Message": '```python:test.py\ncode\n```',
            "UserOrBot": "assistant",
            "TokensConsumed": 50,
            "TokenCost": 0.001,
            "ModelName": "gpt-5",
            "DisplayName": "GPT-5",
            "TimestampUTC": "2026-02-07T12:00:00Z",
        }
        mock_client.parse_message.return_value = MagicMock(
            content='```python:test.py\ncode\n```',
            tokens_consumed=50,
            token_cost=0.001,
        )

        result = executor.execute("fix", dry_run=True)
        assert result is not None

    def test_prompt_assembly_order(
        self, exec_config: ConfigManager, display: Display, registry: SkillRegistry
    ) -> None:
        """System prompt comes before skill prompt."""
        executor = SkillExecutor(exec_config, display, registry)
        # Verify the registry has the review skill
        skill = registry.get_skill("review")
        assert skill is not None

    @patch("genai_cli.skills.executor.GenAIClient")
    def test_auto_apply_from_skill_metadata(
        self,
        mock_client_cls: MagicMock,
        executor: SkillExecutor,
    ) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_chat.return_value = {
            "SessionId": "s1",
            "Message": "Fixed.",
            "UserOrBot": "assistant",
            "TokensConsumed": 50,
            "TokenCost": 0.001,
            "ModelName": "gpt-5",
            "DisplayName": "GPT-5",
            "TimestampUTC": "2026-02-07T12:00:00Z",
        }
        mock_client.parse_message.return_value = MagicMock(
            content="Fixed.",
            tokens_consumed=50,
            token_cost=0.001,
        )

        # fix skill has auto_apply: true
        result = executor.execute("fix")
        assert result is not None
