"""Agent loop: orchestrate bundle -> upload -> prompt -> response -> apply -> repeat."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from genai_cli.applier import ApplyResult, FileApplier, UnifiedParser
from genai_cli.auth import AuthError
from genai_cli.bundler import FileBundler
from genai_cli.client import GenAIClient
from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.models import ChatMessage
from genai_cli.session import SessionManager
from genai_cli.streaming import stream_or_complete
from genai_cli.token_tracker import TokenTracker


@dataclass
class RoundResult:
    """Result of a single agent round."""

    round_number: int
    response: str = ""
    files_applied: list[str] = field(default_factory=list)
    failed_edits: list[ApplyResult] = field(default_factory=list)
    tokens_consumed: int = 0
    had_actions: bool = False


@dataclass
class AgentResult:
    """Result of the complete agent loop."""

    rounds: list[RoundResult] = field(default_factory=list)
    total_files_applied: list[str] = field(default_factory=list)
    total_tokens: int = 0
    total_failed_edits: int = 0
    stop_reason: str = ""


class AgentLoop:
    """Multi-round agent: prompt -> response -> parse -> apply -> repeat."""

    def __init__(
        self,
        config: ConfigManager,
        client: GenAIClient,
        display: Display,
        token_tracker: TokenTracker,
        session: dict[str, Any],
        *,
        auto_apply: bool = False,
        dry_run: bool = False,
        max_rounds: int = 5,
    ) -> None:
        self._config = config
        self._client = client
        self._display = display
        self._tracker = token_tracker
        self._session = session
        self._auto_apply = auto_apply
        self._dry_run = dry_run
        self._max_rounds = max_rounds
        self._parser = UnifiedParser()
        self._applier = FileApplier(config, display)
        self._bundler = FileBundler(config)
        self._session_mgr = SessionManager(config)
        self._stopped = False

    def run(
        self,
        message: str,
        model: str,
        files: list[str] | None = None,
        system_prompt: str = "",
        skill_prompt: str = "",
    ) -> AgentResult:
        """Run the agent loop.

        Returns AgentResult with all round results.
        """
        result = AgentResult()
        session_id = self._session["session_id"]

        # Upload files if provided
        if files:
            bundles, _unmatched = self._bundler.bundle_files(files)
            for bundle in bundles:
                self._display.print_bundle_summary(
                    bundle.file_type, bundle.file_count, bundle.estimated_tokens
                )
            if bundles:
                try:
                    self._client.upload_bundles(session_id, bundles)
                    self._display.print_success("Files uploaded")
                except Exception as e:
                    self._display.print_error(f"Upload failed: {e}")

        # Build full prompt
        full_prompt = self._build_full_prompt(
            message, system_prompt, skill_prompt
        )

        current_message = full_prompt

        for round_num in range(1, self._max_rounds + 1):
            if self._stopped:
                result.stop_reason = "user_cancelled"
                break

            if self._should_stop_tokens():
                result.stop_reason = "token_limit"
                self._display.print_warning(
                    "Token limit approaching (>95%). Stopping agent."
                )
                break

            self._display.print_info(
                f"\n--- Agent Round {round_num}/{self._max_rounds} ---"
            )

            round_result = self._run_round(
                round_num, current_message, model, session_id
            )
            result.rounds.append(round_result)
            result.total_tokens += round_result.tokens_consumed
            result.total_files_applied.extend(round_result.files_applied)
            result.total_failed_edits += len(round_result.failed_edits)

            if not round_result.had_actions:
                result.stop_reason = "no_actions"
                break

            if round_num >= self._max_rounds:
                result.stop_reason = "max_rounds"
                break

            # Prepare next round message with error feedback
            current_message = self._build_feedback_message(round_result)

        # Summary
        total_files = len(set(result.total_files_applied))
        total_rounds = len(result.rounds)
        self._display.print_info(
            f"\nAgent completed: {total_rounds} rounds, "
            f"{total_files} files modified"
        )
        if result.total_failed_edits:
            self._display.print_warning(
                f"{result.total_failed_edits} edit(s) failed"
            )
        self._display.print_info(f"Stop reason: {result.stop_reason}")

        return result

    def _run_round(
        self,
        round_num: int,
        message: str,
        model: str,
        session_id: str,
    ) -> RoundResult:
        """Execute a single agent round."""
        rr = RoundResult(round_number=round_num)

        # Send message
        use_streaming = self._config.settings.streaming
        try:
            full_text, chat_msg = stream_or_complete(
                self._client, message, model, session_id,
                self._config, use_streaming,
            )
        except (AuthError, Exception) as e:
            self._display.print_error(f"Request failed: {e}")
            return rr

        rr.response = full_text
        self._display.print_message(full_text, role="assistant")

        if chat_msg:
            rr.tokens_consumed = chat_msg.tokens_consumed
            self._tracker.add_consumed(
                chat_msg.tokens_consumed, chat_msg.token_cost
            )
            self._session_mgr.add_message(self._session, chat_msg)

        # Parse for SEARCH/REPLACE blocks (preferred) or legacy blocks
        edits, legacy_blocks = self._parser.parse(full_text)

        if edits:
            rr.had_actions = True
            mode = self._get_apply_mode()
            results = self._applier.apply_edits(edits, mode)
            rr.files_applied = [r.file_path for r in results if r.success]
            rr.failed_edits = [r for r in results if not r.success]
        elif legacy_blocks:
            rr.had_actions = True
            mode = self._get_apply_mode()
            results = self._applier.apply_all(legacy_blocks, mode)
            rr.files_applied = [r.file_path for r in results if r.success]
            rr.failed_edits = [r for r in results if not r.success]

        # Show token status
        usage = self._tracker.to_usage()
        self._display.print_token_status(usage)

        return rr

    def _build_feedback_message(self, round_result: RoundResult) -> str:
        """Build the next-round message with success/failure feedback."""
        parts: list[str] = []

        applied = round_result.files_applied
        failed = round_result.failed_edits

        if applied:
            parts.append(
                f"Successfully applied changes to: {', '.join(applied)}."
            )

        if failed:
            for f in failed:
                parts.append(
                    f"FAILED to apply edit to {f.file_path}: {f.error_message}"
                )
                if f.file_content_snippet:
                    parts.append(
                        f"Current content of {f.file_path}:\n"
                        f"```\n{f.file_content_snippet}\n```"
                    )
            parts.append(
                "Please retry the failed edits with corrected SEARCH content "
                "that exactly matches the current file content shown above."
            )

        if not applied and not failed:
            parts.append("Continue with next steps.")

        if applied and not failed:
            parts.append("Continue with any remaining tasks.")

        return "\n\n".join(parts)

    def _build_full_prompt(
        self,
        user_message: str,
        system_prompt: str = "",
        skill_prompt: str = "",
    ) -> str:
        """Build the full prompt with system -> skill -> user message."""
        parts: list[str] = []
        if system_prompt:
            parts.append(system_prompt)
        if skill_prompt:
            parts.append(skill_prompt)
        parts.append(user_message)
        return "\n\n".join(parts)

    def _get_apply_mode(self) -> str:
        """Get the current apply mode."""
        if self._dry_run:
            return "dry-run"
        if self._auto_apply:
            return "auto"
        return "confirm"

    def _should_stop_tokens(self) -> bool:
        """Check if token usage exceeds critical threshold."""
        return self._tracker.status == "critical"

    def stop(self) -> None:
        """Stop the agent loop."""
        self._stopped = True
