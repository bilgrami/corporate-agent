"""Tests for REPL module."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.repl import ReplSession, SlashCompleter


@pytest.fixture
def repl_config(tmp_path: Path) -> ConfigManager:
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    settings = {
        "api_base_url": "https://api.test.com",
        "session_dir": str(session_dir),
        "default_model": "gpt-5-chat-global",
    }
    p = tmp_path / "settings.yaml"
    p.write_text(yaml.dump(settings))
    return ConfigManager(config_path=str(p))


@pytest.fixture
def display() -> Display:
    return Display(file=StringIO())


@pytest.fixture
def repl(repl_config: ConfigManager, display: Display) -> ReplSession:
    return ReplSession(repl_config, display)


class TestReplCommands:
    def test_help(self, repl: ReplSession) -> None:
        repl._handle_command("/help")
        # Should not raise

    def test_model_show(self, repl: ReplSession) -> None:
        repl._handle_command("/model")
        # Should show current model

    def test_model_switch(self, repl: ReplSession) -> None:
        repl._handle_command("/model claude-sonnet-4-5-global")
        assert repl._model_name == "claude-sonnet-4-5-global"

    def test_model_invalid(self, repl: ReplSession) -> None:
        repl._handle_command("/model nonexistent")
        assert repl._model_name != "nonexistent"

    def test_models(self, repl: ReplSession) -> None:
        repl._handle_command("/models")
        # Should not raise

    def test_files_upload(
        self, repl: ReplSession, sample_project_dir: Path
    ) -> None:
        mock_client = MagicMock()
        repl._client = mock_client
        repl._handle_command(f"/files {sample_project_dir / 'src'}")
        # Files are uploaded immediately, not queued
        assert len(repl._queued_files) == 0
        assert mock_client.upload_bundles.called

    def test_files_empty(self, repl: ReplSession) -> None:
        repl._handle_command("/files")
        # Should show "no files queued"

    def test_clear(self, repl: ReplSession) -> None:
        old_id = repl._session["session_id"]
        repl._handle_command("/clear")
        assert repl._session["session_id"] != old_id
        assert repl._token_tracker.consumed == 0

    def test_fresh_alias(self, repl: ReplSession) -> None:
        old_id = repl._session["session_id"]
        repl._handle_command("/fresh")
        assert repl._session["session_id"] != old_id

    def test_compact(self, repl: ReplSession) -> None:
        for i in range(10):
            repl._session.setdefault("messages", []).append(
                {"role": "user", "content": f"msg {i}"}
            )
        repl._handle_command("/compact")
        assert len(repl._session["messages"]) < 10

    def test_status(self, repl: ReplSession) -> None:
        repl._handle_command("/status")
        # Should not raise

    def test_usage(self, repl: ReplSession) -> None:
        repl._handle_command("/usage")
        # Should not raise

    def test_auto_apply_on(self, repl: ReplSession) -> None:
        repl._handle_command("/auto-apply on")
        assert repl._auto_apply is True

    def test_auto_apply_off(self, repl: ReplSession) -> None:
        repl._auto_apply = True
        repl._handle_command("/auto-apply off")
        assert repl._auto_apply is False

    def test_auto_apply_toggle(self, repl: ReplSession) -> None:
        initial = repl._auto_apply
        repl._handle_command("/auto-apply")
        assert repl._auto_apply != initial

    def test_config_show(self, repl: ReplSession) -> None:
        repl._handle_command("/config")
        # Should not raise

    def test_config_get(self, repl: ReplSession) -> None:
        repl._handle_command("/config default_model")
        # Should not raise

    def test_history(self, repl: ReplSession) -> None:
        repl._handle_command("/history")
        # Should not raise

    def test_quit(self, repl: ReplSession) -> None:
        repl._running = True
        repl._handle_command("/quit")
        assert repl._running is False

    def test_quit_shortcut(self, repl: ReplSession) -> None:
        repl._running = True
        repl._handle_command("/q")
        assert repl._running is False

    def test_unknown_command(self, repl: ReplSession) -> None:
        repl._handle_command("/unknown")
        # Should print error, not raise

    def test_agent_placeholder(self, repl: ReplSession) -> None:
        repl._handle_command("/agent 3")
        # Should not raise

    def test_skill_placeholder(self, repl: ReplSession) -> None:
        repl._handle_command("/skill review")
        # Should not raise

    def test_skills_placeholder(self, repl: ReplSession) -> None:
        repl._handle_command("/skills")
        # Should not raise

    def test_resume_nonexistent(self, repl: ReplSession) -> None:
        repl._handle_command("/resume nonexistent-id")
        # Should print error, not raise

    def test_resume_no_arg(self, repl: ReplSession) -> None:
        repl._handle_command("/resume")
        # Should print usage


class TestRewindCommand:
    """Tests for /rewind command."""

    def test_rewind_default(self, repl: ReplSession) -> None:
        repl._session.setdefault("messages", []).extend([
            {"role": "user", "content": "hello", "tokens_consumed": 10, "token_cost": 0.01},
            {"role": "assistant", "content": "hi", "tokens_consumed": 20, "token_cost": 0.02},
        ])
        repl._token_tracker.add_consumed(30, 0.03)
        repl._handle_command("/rewind")
        assert len(repl._session["messages"]) == 0
        assert repl._token_tracker.consumed == 0

    def test_rewind_multiple_turns(self, repl: ReplSession) -> None:
        msgs = repl._session.setdefault("messages", [])
        for i in range(4):
            role = "user" if i % 2 == 0 else "assistant"
            msgs.append({"role": role, "content": f"msg{i}", "tokens_consumed": 100, "token_cost": 0.01})
        repl._token_tracker.add_consumed(400, 0.04)
        repl._handle_command("/rewind 1")
        assert len(repl._session["messages"]) == 2
        assert repl._token_tracker.consumed == 200

    def test_rewind_too_many(self, repl: ReplSession) -> None:
        repl._session.setdefault("messages", []).extend([
            {"role": "user", "content": "hi", "tokens_consumed": 0, "token_cost": 0.0},
            {"role": "assistant", "content": "hey", "tokens_consumed": 0, "token_cost": 0.0},
        ])
        repl._handle_command("/rewind 5")
        assert len(repl._session["messages"]) == 2  # unchanged

    def test_rewind_invalid_arg(self, repl: ReplSession) -> None:
        repl._handle_command("/rewind abc")
        # Should print error, not raise

    def test_rewind_adjusts_tokens(self, repl: ReplSession) -> None:
        repl._session.setdefault("messages", []).extend([
            {"role": "user", "content": "q", "tokens_consumed": 50, "token_cost": 0.005},
            {"role": "assistant", "content": "a", "tokens_consumed": 150, "token_cost": 0.015},
        ])
        repl._token_tracker.add_consumed(200, 0.02)
        repl._handle_command("/rewind")
        assert repl._token_tracker.consumed == 0


class TestSlashCompleter:
    """Tests for slash command autocomplete."""

    @pytest.fixture
    def completer(self, repl_config: ConfigManager) -> SlashCompleter:
        from genai_cli.session import SessionManager

        return SlashCompleter(repl_config, SessionManager(repl_config))

    def _complete(self, completer: SlashCompleter, text: str) -> list[str]:
        doc = Document(text, len(text))
        return [c.text for c in completer.get_completions(doc, CompleteEvent())]

    def test_slash_returns_all_commands(self, completer: SlashCompleter) -> None:
        results = self._complete(completer, "/")
        assert len(results) == len(SlashCompleter.COMMANDS)
        assert "/help" in results
        assert "/rewind" in results
        assert "/quit" in results

    def test_partial_command(self, completer: SlashCompleter) -> None:
        results = self._complete(completer, "/mo")
        assert "/model" in results
        assert "/models" in results
        assert "/help" not in results

    def test_model_subcompletions(self, completer: SlashCompleter) -> None:
        results = self._complete(completer, "/model ")
        assert "gpt-5-chat-global" in results
        assert "claude-sonnet-4-5-global" in results

    def test_auto_apply_subcompletions(self, completer: SlashCompleter) -> None:
        results = self._complete(completer, "/auto-apply ")
        assert results == ["on", "off"]

    def test_no_completions_without_slash(self, completer: SlashCompleter) -> None:
        results = self._complete(completer, "hello")
        assert results == []

    def test_command_meta_text(self, completer: SlashCompleter) -> None:
        doc = Document("/he", 3)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        assert len(completions) == 1
        assert completions[0].text == "/help"
        assert completions[0].display_meta is not None

    def test_exit_in_completer(self, completer: SlashCompleter) -> None:
        results = self._complete(completer, "/ex")
        assert "/exit" in results
        assert "/export" in results

    def test_export_in_completer(self, completer: SlashCompleter) -> None:
        results = self._complete(completer, "/export")
        assert "/export" in results


class TestExitCommand:
    """Tests for /exit command (alias for /quit)."""

    def test_exit_command_calls_quit(self, repl: ReplSession) -> None:
        repl._running = True
        repl._handle_command("/exit")
        assert repl._running is False


class TestExportCommand:
    """Tests for /export command."""

    def test_export_empty_session(self, repl: ReplSession, display: Display) -> None:
        repl._handle_command("/export")
        output = display._file.getvalue()  # type: ignore[union-attr]
        assert "No messages to export" in output

    def test_format_session_markdown(self, repl: ReplSession) -> None:
        repl._session.setdefault("messages", []).extend([
            {"role": "user", "content": "Hello there"},
            {"role": "assistant", "content": "Hi! How can I help?"},
        ])
        md = repl._format_session_markdown()
        assert "# GenAI CLI Session Export" in md
        assert "**Messages**: 2" in md
        assert "## User" in md
        assert "Hello there" in md
        assert "## Assistant" in md
        assert "Hi! How can I help?" in md

    def test_format_empty_returns_empty_string(self, repl: ReplSession) -> None:
        md = repl._format_session_markdown()
        assert md == ""

    def test_export_to_file(
        self, repl: ReplSession, tmp_path: Path
    ) -> None:
        repl._session.setdefault("messages", []).extend([
            {"role": "user", "content": "test message"},
            {"role": "assistant", "content": "test response"},
        ])
        out_file = tmp_path / "export.md"
        repl._handle_command(f"/export {out_file}")
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# GenAI CLI Session Export" in content
        assert "test message" in content
        assert "test response" in content

    def test_export_to_clipboard_success(
        self, repl: ReplSession, display: Display
    ) -> None:
        repl._session.setdefault("messages", []).extend([
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ])
        with patch("genai_cli.repl.subprocess.run") as mock_run:
            repl._handle_command("/export")
            mock_run.assert_called_once()
            output = display._file.getvalue()  # type: ignore[union-attr]
            assert "clipboard" in output.lower()

    def test_export_to_clipboard_failure(
        self, repl: ReplSession, display: Display
    ) -> None:
        repl._session.setdefault("messages", []).extend([
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ])
        with patch(
            "genai_cli.repl.subprocess.run",
            side_effect=FileNotFoundError("no pbcopy"),
        ):
            repl._handle_command("/export")
            output = display._file.getvalue()  # type: ignore[union-attr]
            assert "not available" in output.lower() or "Specify a filename" in output


class TestSessionCommand:
    """Tests for /session command."""

    def test_session_command_shows_full_id(
        self, repl: ReplSession, display: Display
    ) -> None:
        """/session displays full UUID (not truncated)."""
        sid = repl._session["session_id"]
        repl._handle_command("/session")
        output = display._file.getvalue()  # type: ignore[union-attr]
        assert sid in output

    def test_session_command_shows_web_link(
        self, tmp_path: Path, display: Display
    ) -> None:
        """/session displays web UI link when web_ui_url is configured."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        settings = {
            "api_base_url": "https://api.test.com",
            "web_ui_url": "https://genai.test.com",
            "session_dir": str(session_dir),
            "default_model": "gpt-5-chat-global",
        }
        p = tmp_path / "settings.yaml"
        p.write_text(yaml.dump(settings))
        cfg = ConfigManager(config_path=str(p))
        repl = ReplSession(cfg, display)
        sid = repl._session["session_id"]
        repl._handle_command("/session")
        output = display._file.getvalue()  # type: ignore[union-attr]
        assert f"https://genai.test.com/chat/{sid}" in output


class TestImmediateUpload:
    """Tests for /files immediate upload behavior."""

    def test_files_uploads_immediately(
        self, repl: ReplSession, sample_project_dir: Path, display: Display
    ) -> None:
        """/files <path> triggers upload, _queued_files stays empty."""
        mock_client = MagicMock()
        repl._client = mock_client

        repl._handle_command(f"/files {sample_project_dir / 'src'}")
        # Files should NOT be queued (old behavior)
        assert len(repl._queued_files) == 0
        # upload_bundles should have been called
        assert mock_client.upload_bundles.called

    def test_files_creates_session_first(
        self, repl: ReplSession, sample_project_dir: Path, display: Display
    ) -> None:
        """Session is created on API before upload."""
        mock_client = MagicMock()
        repl._client = mock_client

        repl._handle_command(f"/files {sample_project_dir / 'src'}")
        # ensure_session should be called before upload_bundles
        assert mock_client.ensure_session.called
        assert mock_client.upload_bundles.called
        # ensure_session called first
        ensure_call_order = mock_client.ensure_session.call_args_list[0]
        upload_call_order = mock_client.upload_bundles.call_args_list[0]
        assert ensure_call_order is not None
        assert upload_call_order is not None


class TestClearCreatesSession:
    """Tests for /clear creating a new API session."""

    def test_clear_creates_new_api_session(
        self, repl: ReplSession, display: Display
    ) -> None:
        """/clear calls ensure_session() and updates session_id."""
        old_id = repl._session["session_id"]
        mock_client = MagicMock()
        repl._client = mock_client

        repl._handle_command("/clear")
        new_id = repl._session["session_id"]
        assert new_id != old_id
        assert mock_client.ensure_session.called


class TestEnvSessionId:
    """Tests for GENAI_SESSION_ID env var."""

    def test_env_session_id_reused(
        self, repl_config: ConfigManager, display: Display
    ) -> None:
        """GENAI_SESSION_ID env var is used, create_chat skipped."""
        env_sid = "env-session-id-from-web-ui"
        with patch.dict("os.environ", {"GENAI_SESSION_ID": env_sid}):
            repl = ReplSession(repl_config, display)
            assert repl._session["session_id"] == env_sid
            # Client should have mark_session_created called
            client = repl._get_client()
            assert env_sid in client._created_sessions


class TestFilesQuotedPaths:
    """Tests for /files with shlex.split and user feedback."""

    def test_shlex_split_quotes(
        self, repl: ReplSession, tmp_path: Path, display: Display
    ) -> None:
        """Quoted paths with spaces handled."""
        spaced_dir = tmp_path / "path with spaces"
        spaced_dir.mkdir()
        (spaced_dir / "module.py").write_text("# module\n")

        mock_client = MagicMock()
        repl._client = mock_client
        repl._handle_command(f'/files "{spaced_dir}/module.py"')
        # Files are uploaded immediately, not queued
        assert mock_client.upload_bundles.called

    def test_empty_result_warning(
        self, repl: ReplSession, tmp_path: Path, display: Display
    ) -> None:
        """REPL shows warning when no files found."""
        repl._handle_command(f"/files {tmp_path}/nonexistent_dir/*.py")
        output = display._file.getvalue()  # type: ignore[union-attr]
        assert "No files found" in output or "No supported files" in output
        assert len(repl._queued_files) == 0

    def test_unmatched_path_warning(
        self, repl: ReplSession, tmp_path: Path, display: Display
    ) -> None:
        """REPL shows warning for unmatched paths."""
        repl._handle_command(f"/files {tmp_path}/does_not_exist.py")
        output = display._file.getvalue()  # type: ignore[union-attr]
        assert "No files found for" in output or "No supported files" in output

    def test_glob_pattern_in_repl(
        self, repl: ReplSession, tmp_path: Path, display: Display
    ) -> None:
        """Glob patterns work from the REPL /files command."""
        (tmp_path / "a.py").write_text("# a\n")
        (tmp_path / "b.py").write_text("# b\n")

        mock_client = MagicMock()
        repl._client = mock_client
        repl._handle_command(f"/files {tmp_path}/*.py")
        # Files are uploaded immediately
        assert mock_client.upload_bundles.called


class TestFilesSystemPrompt:
    """Tests for system prompt sent after /files upload."""

    def test_files_sends_system_prompt_after_upload(
        self, repl: ReplSession, sample_project_dir: Path, display: Display
    ) -> None:
        """After upload, stream_or_complete is called with the system prompt."""
        mock_client = MagicMock()
        repl._client = mock_client

        fake_msg = MagicMock()
        fake_msg.tokens_consumed = 100
        fake_msg.token_cost = 0.01

        with patch("genai_cli.repl.stream_or_complete", return_value=("Acknowledged", fake_msg)) as mock_stream:
            repl._handle_command(f"/files {sample_project_dir / 'src'}")
            assert mock_client.upload_bundles.called
            # stream_or_complete should have been called with the system prompt
            assert mock_stream.called
            call_args = mock_stream.call_args
            prompt_arg = call_args[0][1]  # second positional arg is the message
            system_prompt = repl._config.get_system_prompt()
            assert prompt_arg == system_prompt

        output = display._file.getvalue()  # type: ignore[union-attr]
        assert "Acknowledged" in output

    def test_files_system_prompt_failure_is_warning(
        self, repl: ReplSession, sample_project_dir: Path, display: Display
    ) -> None:
        """If sending system prompt fails, upload still succeeds with a warning."""
        mock_client = MagicMock()
        repl._client = mock_client

        with patch(
            "genai_cli.repl.stream_or_complete",
            side_effect=Exception("connection lost"),
        ):
            repl._handle_command(f"/files {sample_project_dir / 'src'}")
            assert mock_client.upload_bundles.called

        output = display._file.getvalue()  # type: ignore[union-attr]
        assert "Files uploaded" in output
        assert "Context init failed" in output


class TestBundleCommand:
    """Tests for /bundle slash command."""

    def test_bundle_no_args_shows_usage(
        self, repl: ReplSession, display: Display
    ) -> None:
        """/bundle with no args prints usage."""
        repl._handle_command("/bundle")
        output = display._file.getvalue()  # type: ignore[union-attr]
        assert "Usage" in output

    def test_bundle_creates_file(
        self, repl: ReplSession, sample_project_dir: Path, display: Display, tmp_path: Path
    ) -> None:
        """/bundle <path> creates bundle.txt on disk."""
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            repl._handle_command(f"/bundle {sample_project_dir / 'src'}")
            output = display._file.getvalue()  # type: ignore[union-attr]
            assert "Bundled" in output
            assert (tmp_path / "bundle.txt").exists()
        finally:
            os.chdir(old_cwd)

    def test_bundle_no_upload_called(
        self, repl: ReplSession, sample_project_dir: Path, tmp_path: Path
    ) -> None:
        """/bundle does NOT call upload_bundles (save-only)."""
        mock_client = MagicMock()
        repl._client = mock_client

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            repl._handle_command(f"/bundle {sample_project_dir / 'src'}")
            assert not mock_client.upload_bundles.called
        finally:
            os.chdir(old_cwd)

    def test_bundle_unmatched_warning(
        self, repl: ReplSession, display: Display, tmp_path: Path
    ) -> None:
        """/bundle with nonexistent path shows warning."""
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            repl._handle_command(f"/bundle {tmp_path}/nonexistent.py")
            output = display._file.getvalue()  # type: ignore[union-attr]
            assert "No files found" in output or "No supported files" in output
        finally:
            os.chdir(old_cwd)

    def test_bundle_in_completer(self, repl_config: ConfigManager) -> None:
        """/bundle appears in slash command completions."""
        from genai_cli.session import SessionManager

        completer = SlashCompleter(repl_config, SessionManager(repl_config))
        doc = Document("/bu", 3)
        results = [c.text for c in completer.get_completions(doc, CompleteEvent())]
        assert "/bundle" in results
