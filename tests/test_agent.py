"""Tests for agent loop module."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from genai_cli.agent import AgentLoop, AgentResult, RoundResult
from genai_cli.applier import ApplyResult
from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.session import SessionManager
from genai_cli.token_tracker import TokenTracker


def _make_stream_response(content: str, session_id: str = "s1") -> MagicMock:
    """Build a mock httpx.Response whose .text is a JSON-lines stream body."""
    import httpx
    lines = [
        json.dumps({"Task": "Intermediate", "Steps": [{"data": content}], "Message": content}),
        json.dumps({
            "Task": "Complete", "TokensConsumed": 50, "TokenCost": 0.001,
            "SessionId": session_id, "Steps": [], "Message": "",
        }),
    ]
    resp = MagicMock(spec=httpx.Response)
    resp.text = "\n".join(lines)
    return resp


@pytest.fixture
def agent_config(tmp_path: Path) -> ConfigManager:
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
def tracker(agent_config: ConfigManager) -> TokenTracker:
    return TokenTracker(agent_config)


@pytest.fixture
def session(agent_config: ConfigManager) -> dict:
    mgr = SessionManager(agent_config)
    return mgr.create_session()


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.upload_bundles.return_value = [{"status": "ok"}]
    return client


class TestAgentLoop:
    def test_single_round_no_actions(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        mock_client.stream_chat.return_value = _make_stream_response(
            "No code changes needed.", session["session_id"],
        )

        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
            max_rounds=3,
        )
        result = agent.run("fix bugs", "gpt-5")
        assert result.stop_reason == "no_actions"
        assert len(result.rounds) == 1

    def test_max_rounds_reached(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
        tmp_path: Path,
    ) -> None:
        # Response with code block so it always has actions
        mock_client.stream_chat.return_value = _make_stream_response(
            '```python:test_out.py\nprint("hi")\n```', session["session_id"],
        )

        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
            auto_apply=True, max_rounds=2,
        )
        result = agent.run("fix bugs", "gpt-5")
        assert result.stop_reason == "max_rounds"
        assert len(result.rounds) == 2

    def test_token_limit_stops(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        # Push tracker to critical
        tracker.add_consumed(125000)  # >95% of 128000

        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
            max_rounds=5,
        )
        result = agent.run("fix bugs", "gpt-5")
        assert result.stop_reason == "token_limit"

    def test_dry_run(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        mock_client.stream_chat.return_value = _make_stream_response(
            '```python:dry.py\ncode\n```', session["session_id"],
        )

        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
            dry_run=True, max_rounds=1,
        )
        result = agent.run("fix", "gpt-5")
        # Dry run: blocks are parsed but files not applied
        assert len(result.rounds) == 1

    def test_stop(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
        )
        agent.stop()
        result = agent.run("fix", "gpt-5")
        assert result.stop_reason == "user_cancelled"

    def test_api_error_handled(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        mock_client.create_chat.side_effect = Exception("API error")
        mock_client.stream_chat.side_effect = Exception("API error")

        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
            max_rounds=1,
        )
        result = agent.run("fix", "gpt-5")
        assert len(result.rounds) == 1

    def test_with_files(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
        sample_project_dir: Path,
    ) -> None:
        mock_client.stream_chat.return_value = _make_stream_response(
            "Reviewed the code. Looks good!", session["session_id"],
        )

        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
            max_rounds=1,
        )
        result = agent.run(
            "review", "gpt-5",
            files=[str(sample_project_dir / "src")],
        )
        assert len(result.rounds) == 1
        mock_client.upload_bundles.assert_called_once()

    def test_build_full_prompt(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
        )
        prompt = agent._build_full_prompt(
            "fix bugs",
            system_prompt="You are helpful.",
            skill_prompt="Review for bugs.",
        )
        assert "You are helpful." in prompt
        assert "Review for bugs." in prompt
        assert "fix bugs" in prompt

    def test_search_replace_parsed_and_applied(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
        tmp_path: Path,
    ) -> None:
        """Agent should parse SEARCH/REPLACE blocks from AI response."""
        # Create a file for the edit to target
        target = tmp_path / "fix_me.py"
        target.write_text("def broken():\n    pass\n")

        sr_response = (
            "Here is the fix:\n\n"
            "fix_me.py\n"
            "<<<<<<< SEARCH\n"
            "def broken():\n"
            "    pass\n"
            "=======\n"
            "def fixed():\n"
            "    return True\n"
            ">>>>>>> REPLACE\n"
        )
        mock_client.stream_chat.return_value = _make_stream_response(
            sr_response, session["session_id"],
        )

        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
            auto_apply=True, max_rounds=1,
        )
        # Override project root so the applier finds the file
        agent._applier._project_root = tmp_path
        result = agent.run("fix the bug", "gpt-5")
        assert len(result.rounds) == 1
        assert result.rounds[0].had_actions


class TestAgentFeedback:
    def test_feedback_message_with_failures(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
        )
        rr = RoundResult(
            round_number=1,
            files_applied=["a.py"],
            failed_edits=[
                ApplyResult(
                    file_path="b.py",
                    success=False,
                    error_message="SEARCH block not found",
                    file_content_snippet="def hello():\n    pass",
                )
            ],
        )
        msg = agent._build_feedback_message(rr)
        assert "Successfully applied" in msg
        assert "a.py" in msg
        assert "FAILED" in msg
        assert "b.py" in msg
        assert "def hello" in msg
        assert "retry" in msg.lower()

    def test_feedback_message_all_success(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
        )
        rr = RoundResult(
            round_number=1,
            files_applied=["a.py", "b.py"],
            failed_edits=[],
        )
        msg = agent._build_feedback_message(rr)
        assert "Successfully applied" in msg
        assert "remaining tasks" in msg.lower()
        assert "FAILED" not in msg

    def test_feedback_message_no_actions(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
        )
        rr = RoundResult(round_number=1)
        msg = agent._build_feedback_message(rr)
        assert "Continue with next steps" in msg

    def test_agent_result_tracks_failed_edits(
        self,
        agent_config: ConfigManager,
        mock_client: MagicMock,
        display: Display,
        tracker: TokenTracker,
        session: dict,
    ) -> None:
        """Agent should track failed edits when SEARCH doesn't match."""
        sr_response = (
            "nonexistent.py\n"
            "<<<<<<< SEARCH\n"
            "this does not exist\n"
            "=======\n"
            "replacement\n"
            ">>>>>>> REPLACE\n"
        )
        mock_client.stream_chat.return_value = _make_stream_response(
            sr_response, session["session_id"],
        )

        agent = AgentLoop(
            agent_config, mock_client, display, tracker, session,
            auto_apply=True, max_rounds=1,
        )
        result = agent.run("fix", "gpt-5")
        assert result.total_failed_edits > 0
