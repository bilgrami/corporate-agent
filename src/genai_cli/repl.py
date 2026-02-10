"""Interactive REPL with slash commands and prompt_toolkit."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.completion import PathCompleter as _PathCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory

from genai_cli import __version__
from genai_cli.auth import AuthError, AuthManager
from genai_cli.bundler import FileBundler
from genai_cli.client import GenAIClient
from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.models import ChatMessage
from genai_cli.session import SessionManager
from genai_cli.streaming import stream_or_complete
from genai_cli.token_tracker import TokenTracker


class SlashCompleter(Completer):
    """Autocomplete for REPL slash commands and their arguments."""

    COMMANDS: dict[str, str] = {
        "/help": "Show available commands",
        "/model": "Show or switch model",
        "/models": "List all available models",
        "/files": "Queue files for next message",
        "/bundle": "Bundle files into a single .txt file",
        "/clear": "Clear session, start fresh",
        "/fresh": "Alias for /clear",
        "/compact": "Summarize to reduce tokens",
        "/history": "List saved sessions",
        "/resume": "Resume a saved session",
        "/usage": "Show token usage",
        "/session": "Show session ID and web link",
        "/status": "Show session status",
        "/config": "View or update settings",
        "/auto-apply": "Toggle auto-apply mode",
        "/agent": "Enable agent mode",
        "/prompt": "Show or switch system prompt profile",
        "/prompts": "List available prompt profiles",
        "/skill": "Invoke a skill",
        "/skills": "List available skills",
        "/rewind": "Undo last N turns",
        "/export": "Export session to file or clipboard",
        "/quit": "Save session and exit",
        "/exit": "Exit the REPL (alias for /quit)",
        "/q": "Alias for /quit",
    }

    def __init__(
        self,
        config: ConfigManager,
        session_mgr: SessionManager,
    ) -> None:
        self._config = config
        self._session_mgr = session_mgr
        self._path_completer = _PathCompleter()

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        # No space yet — complete the command name
        if " " not in text:
            for cmd, desc in self.COMMANDS.items():
                if cmd.startswith(text):
                    yield Completion(
                        cmd, start_position=-len(text), display_meta=desc
                    )
            return

        # Has a space — complete arguments for specific commands
        cmd, _, arg_text = text.partition(" ")
        cmd = cmd.lower()

        if cmd == "/model":
            for name in self._config.get_all_models():
                if name.startswith(arg_text):
                    yield Completion(name, start_position=-len(arg_text))

        elif cmd == "/auto-apply":
            for opt in ("on", "off"):
                if opt.startswith(arg_text):
                    yield Completion(opt, start_position=-len(arg_text))

        elif cmd == "/prompt":
            try:
                from genai_cli.prompts.registry import PromptRegistry

                registry = PromptRegistry(self._config)
                for p in registry.list_prompts():
                    if p.name.startswith(arg_text):
                        yield Completion(
                            p.name,
                            start_position=-len(arg_text),
                            display_meta=p.description.strip()[:40],
                        )
            except Exception:
                pass

        elif cmd == "/skill":
            try:
                from genai_cli.skills.registry import SkillRegistry

                registry = SkillRegistry(self._config)
                for s in registry.list_skills():
                    if s.name.startswith(arg_text):
                        yield Completion(
                            s.name,
                            start_position=-len(arg_text),
                            display_meta=s.description.strip()[:40],
                        )
            except Exception:
                pass

        elif cmd in ("/files", "/bundle"):
            sub_doc = Document(arg_text, len(arg_text))
            yield from self._path_completer.get_completions(
                sub_doc, complete_event
            )

        elif cmd == "/resume":
            try:
                for s in self._session_mgr.list_sessions():
                    sid = s["session_id"]
                    if sid.startswith(arg_text):
                        model = s.get("model_name", "")
                        yield Completion(
                            sid,
                            start_position=-len(arg_text),
                            display_meta=model,
                        )
            except Exception:
                pass


class ReplSession:
    """Interactive REPL session with slash commands."""

    def __init__(
        self,
        config: ConfigManager,
        display: Display,
        session_id: str | None = None,
    ) -> None:
        self._config = config
        self._display = display
        self._auth = AuthManager()
        self._client: GenAIClient | None = None
        self._session_mgr = SessionManager(config)
        self._token_tracker = TokenTracker(config)
        self._bundler = FileBundler(config)
        self._queued_files: list[str] = []
        self._auto_apply = config.settings.auto_apply
        self._model_name = config.settings.default_model
        self._agent_rounds: int = 0
        self._running = False

        # Session ID resolution priority:
        # 1. session_id arg (from --session-id or /resume)
        # 2. GENAI_SESSION_ID env var
        # 3. auto-generate UUID
        is_resume = False

        if session_id:
            # Check if this is a /resume (local session file exists)
            loaded = self._session_mgr.load_session(session_id)
            if loaded:
                is_resume = True
                self._session = loaded
                self._model_name = loaded.get("model_name", self._model_name)
                tracker_data = loaded.get("token_tracker")
                if tracker_data:
                    self._token_tracker = TokenTracker.from_dict(
                        tracker_data, config
                    )
            else:
                # session_id from --session-id flag (pre-existing web UI session)
                self._session = self._session_mgr.create_session(self._model_name)
                self._session["session_id"] = session_id
        else:
            env_sid = os.environ.get("GENAI_SESSION_ID")
            if env_sid:
                session_id = env_sid
                self._session = self._session_mgr.create_session(self._model_name)
                self._session["session_id"] = env_sid
            else:
                self._session = self._session_mgr.create_session(self._model_name)

        # If session_id was provided externally (not /resume), mark it as
        # already created on the API so create_chat() is skipped
        if session_id and not is_resume:
            client = self._get_client()
            client.mark_session_created(session_id)

    def _get_client(self) -> GenAIClient:
        """Lazily create the API client."""
        if self._client is None:
            self._client = GenAIClient(self._config, self._auth)
        return self._client

    def run(self) -> None:
        """Run the interactive REPL loop."""
        model_info = self._config.get_model(self._model_name)
        model_display = model_info.display_name if model_info else self._model_name
        context_window = model_info.context_window if model_info else 128000

        self._display.print_welcome(__version__, model_display, context_window)
        self._running = True

        completer = SlashCompleter(self._config, self._session_mgr)
        prompt_session: PromptSession[str] = PromptSession(
            history=InMemoryHistory(),
            completer=completer,
        )

        while self._running:
            try:
                text = prompt_session.prompt("You> ").strip()
                if not text:
                    continue
                if text.startswith("/"):
                    self._handle_command(text)
                else:
                    self._send_message(text)
            except KeyboardInterrupt:
                self._display.print_info("\nUse /quit to save and exit.")
            except EOFError:
                self._handle_quit()

    def _handle_command(self, text: str) -> None:
        """Dispatch slash commands."""
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        commands: dict[str, Any] = {
            "/help": self._handle_help,
            "/model": lambda: self._handle_model(arg),
            "/models": self._handle_models,
            "/files": lambda: self._handle_files(arg),
            "/bundle": lambda: self._handle_bundle(arg),
            "/clear": self._handle_clear,
            "/fresh": self._handle_clear,
            "/compact": self._handle_compact,
            "/history": self._handle_history,
            "/resume": lambda: self._handle_resume(arg),
            "/usage": self._handle_usage,
            "/session": self._handle_session,
            "/status": self._handle_status,
            "/config": lambda: self._handle_config(arg),
            "/auto-apply": lambda: self._handle_auto_apply(arg),
            "/agent": lambda: self._handle_agent(arg),
            "/prompt": lambda: self._handle_prompt(arg),
            "/prompts": self._handle_prompts,
            "/skill": lambda: self._handle_skill(arg),
            "/skills": self._handle_skills,
            "/rewind": lambda: self._handle_rewind(arg),
            "/export": lambda: self._handle_export(arg),
            "/quit": self._handle_quit,
            "/exit": self._handle_quit,
            "/q": self._handle_quit,
        }

        handler = commands.get(cmd)
        if handler:
            handler()
        else:
            self._display.print_error(f"Unknown command: {cmd}. Type /help.")

    def _handle_help(self) -> None:
        """Show available commands."""
        help_text = """Available commands:
  /help              Show this help
  /model [name]      List models or switch model
  /models            List all available models
  /files <paths>     Queue files for next message
  /bundle <paths>    Bundle files into bundle.txt
  /clear             Clear session, start fresh
  /fresh             Alias for /clear
  /compact           Summarize conversation to reduce tokens
  /history           List saved sessions
  /resume <id>       Resume a saved session
  /usage             Show token usage
  /session           Show session ID and web UI link
  /status            Show current session status
  /config [k] [v]    View or update settings
  /auto-apply [on|off]  Toggle auto-apply mode
  /agent [rounds]    Enable agent mode for next message
  /prompt [name]     Show or switch system prompt profile
  /prompts           List available prompt profiles
  /skill <name>      Invoke a skill
  /skills            List available skills
  /rewind [n]        Undo last N turns (default: 1)
  /export [file]     Export session to file or clipboard
  /quit              Save session and exit
  /exit              Alias for /quit"""
        self._display.print_info(help_text)

    def _handle_model(self, arg: str) -> None:
        """Switch model or list current."""
        if not arg:
            model_info = self._config.get_model(self._model_name)
            if model_info:
                self._display.print_info(
                    f"Current model: {model_info.display_name} "
                    f"({model_info.context_window:,} context)"
                )
            return

        model_info = self._config.get_model(arg)
        if model_info is None:
            self._display.print_error(f"Unknown model: {arg}")
            return

        self._model_name = arg
        self._token_tracker.switch_model(arg)
        self._session["model_name"] = arg
        self._display.print_success(
            f"Switched to {model_info.display_name} "
            f"({model_info.context_window:,} context)"
        )

    def _handle_models(self) -> None:
        """List all models."""
        self._display.print_models_table(self._config.get_all_models())

    def _handle_files(self, arg: str) -> None:
        """Upload files immediately to the current session."""
        if not arg:
            if self._queued_files:
                self._display.print_info(
                    f"Queued files: {', '.join(self._queued_files)}"
                )
            else:
                self._display.print_info("No files queued. Usage: /files <path>")
            return

        try:
            paths = shlex.split(arg)
        except ValueError:
            paths = arg.split()

        bundles, unmatched = self._bundler.bundle_files(paths)

        if unmatched:
            self._display.print_warning(
                f"No files found for: {', '.join(unmatched)}"
            )

        if not bundles:
            self._display.print_warning("No supported files found.")
            return

        for bundle in bundles:
            self._display.print_bundle_summary(
                bundle.file_type, bundle.file_count, bundle.estimated_tokens
            )

        # Upload immediately instead of queuing
        try:
            client = self._get_client()
        except AuthError as e:
            self._display.print_error(str(e))
            return

        session_id = self._session["session_id"]
        client.ensure_session(session_id, self._model_name)

        try:
            client.upload_bundles(session_id, bundles)
            self._display.print_success("Files uploaded")
        except Exception as e:
            self._display.print_error(f"Upload failed: {e}")
            return

        # Send system prompt so the AI knows about the uploaded files
        system_prompt = self._config.get_system_prompt()
        if system_prompt:
            try:
                full_text, chat_msg = stream_or_complete(
                    client, system_prompt, self._model_name,
                    session_id, self._config, self._config.settings.streaming,
                )
                self._display.print_message(full_text, role="assistant")
                if chat_msg and chat_msg.tokens_consumed:
                    self._token_tracker.add_consumed(
                        chat_msg.tokens_consumed, chat_msg.token_cost
                    )
                usage = self._token_tracker.to_usage()
                self._display.print_token_status(usage)
            except Exception as e:
                self._display.print_warning(
                    f"Context init failed (upload succeeded): {e}"
                )

    def _handle_bundle(self, arg: str) -> None:
        """Bundle files into a single .txt for upload."""
        if not arg:
            self._display.print_info("Usage: /bundle <paths>  (writes bundle.txt)")
            return

        try:
            paths = shlex.split(arg)
        except ValueError:
            paths = arg.split()

        output = Path.cwd() / "bundle.txt"
        file_count, total_bytes, unmatched = self._bundler.write_bundle(paths, output)

        if unmatched:
            self._display.print_warning(
                f"No files found for: {', '.join(unmatched)}"
            )

        if file_count == 0:
            self._display.print_warning("No supported files found.")
            return

        self._display.print_success(
            f"Bundled {file_count} file(s) ({total_bytes:,} bytes) → {output}"
        )

    def _handle_clear(self) -> None:
        """Clear session and start fresh with a new API session."""
        self._session = self._session_mgr.create_session(self._model_name)
        self._token_tracker.reset()
        self._queued_files.clear()

        # Create the new session on the API immediately
        try:
            client = self._get_client()
            new_id = self._session["session_id"]
            client.ensure_session(new_id, self._model_name)
        except AuthError:
            pass  # Session will be created on first message

        self._display.print_success("Session cleared. Starting fresh.")

    def _handle_compact(self) -> None:
        """Compact session."""
        self._session = self._session_mgr.compact_session(self._session)
        self._display.print_success("Session compacted.")

    def _handle_history(self) -> None:
        """List saved sessions."""
        sessions = self._session_mgr.list_sessions()
        if not sessions:
            self._display.print_info("No saved sessions.")
            return
        for s in sessions:
            sid = s["session_id"][:12]
            model = s.get("model_name", "")
            msgs = s.get("message_count", 0)
            date = s.get("updated_at", s.get("created_at", ""))[:19]
            self._display.print_info(f"  {sid}...  {model}  {msgs} msgs  {date}")

    def _handle_resume(self, arg: str) -> None:
        """Resume a saved session."""
        if not arg:
            self._display.print_error("Usage: /resume <session_id>")
            return

        loaded = self._session_mgr.load_session(arg)
        if loaded is None:
            self._display.print_error(f"Session not found: {arg}")
            return

        self._session = loaded
        self._model_name = loaded.get("model_name", self._model_name)
        tracker_data = loaded.get("token_tracker")
        if tracker_data:
            self._token_tracker = TokenTracker.from_dict(
                tracker_data, self._config
            )
        msgs = len(loaded.get("messages", []))
        self._display.print_success(
            f"Resumed session {arg[:12]}... ({msgs} messages)"
        )

    def _handle_usage(self) -> None:
        """Show token usage."""
        usage = self._token_tracker.to_usage()
        self._display.print_token_status(usage)
        if self._config.settings.show_cost:
            self._display.print_info(
                f"  Estimated cost: ${usage.estimated_cost:.4f}"
            )

    def _handle_session(self) -> None:
        """Show full session ID and web UI link."""
        sid = self._session["session_id"]
        self._display.print_info(f"  Session ID: {sid}")
        web_ui_url = self._config.settings.web_ui_url
        if web_ui_url:
            link = f"{web_ui_url.rstrip('/')}/chat/{sid}"
            self._display.print_info(f"  Web UI: {link}")

    def _handle_status(self) -> None:
        """Show current session status."""
        model_info = self._config.get_model(self._model_name)
        model_display = model_info.display_name if model_info else self._model_name
        sid = self._session["session_id"][:12]
        msgs = len(self._session.get("messages", []))

        self._display.print_info(f"  Session: {sid}...")
        self._display.print_info(f"  Model: {model_display}")
        self._display.print_info(f"  Messages: {msgs}")

        usage = self._token_tracker.to_usage()
        self._display.print_token_status(usage)

        if self._queued_files:
            self._display.print_info(
                f"  Queued files: {', '.join(self._queued_files)}"
            )
        self._display.print_info(
            f"  Auto-apply: {'on' if self._auto_apply else 'off'}"
        )

    def _handle_config(self, arg: str) -> None:
        """View or update config."""
        if not arg:
            self._display.print_info(f"  model: {self._model_name}")
            self._display.print_info(f"  auto_apply: {self._auto_apply}")
            self._display.print_info(
                f"  streaming: {self._config.settings.streaming}"
            )
            return

        parts = arg.split(maxsplit=1)
        if len(parts) == 1:
            val = self._config.get(parts[0])
            self._display.print_info(f"  {parts[0]} = {val}")
        else:
            self._config.set_override(parts[0], parts[1])
            self._display.print_success(f"Set {parts[0]} = {parts[1]}")

    def _handle_auto_apply(self, arg: str) -> None:
        """Toggle auto-apply."""
        if arg.lower() == "on":
            self._auto_apply = True
        elif arg.lower() == "off":
            self._auto_apply = False
        else:
            self._auto_apply = not self._auto_apply
        state = "on" if self._auto_apply else "off"
        self._display.print_success(f"Auto-apply: {state}")

    def _handle_agent(self, arg: str) -> None:
        """Enable agent mode for next message."""
        rounds = int(arg) if arg.isdigit() else 5
        self._agent_rounds = rounds
        self._display.print_info(
            f"Agent mode enabled for next message ({rounds} rounds). "
            "Type your message to start."
        )

    def _handle_prompt(self, arg: str) -> None:
        """Show or switch the active system prompt profile."""
        if not arg:
            self._display.print_info(
                f"Active prompt: {self._config.active_prompt_name}"
            )
            return

        from genai_cli.prompts.registry import PromptRegistry

        registry = PromptRegistry(self._config)
        prompt = registry.get_prompt(arg)
        if prompt is None:
            self._display.print_error(f"Unknown prompt: {arg}")
            return

        agent_name = self._config.settings.agent_name
        body = registry.load_prompt_body(arg, agent_name)
        if body is None:
            self._display.print_error(f"Failed to load prompt: {arg}")
            return

        self._config.set_active_prompt(arg, body)
        self._display.print_success(f"Switched to prompt: {arg}")

    def _handle_prompts(self) -> None:
        """List available prompt profiles."""
        from genai_cli.prompts.registry import PromptRegistry

        registry = PromptRegistry(self._config)
        prompts = registry.list_prompts()
        if not prompts:
            self._display.print_info("No prompts found.")
            return
        active = self._config.active_prompt_name
        self._display.print_info("Available prompts:")
        for p in prompts:
            marker = " *" if p.name == active else ""
            desc = p.description.strip()[:60]
            self._display.print_info(f"  {p.name:25s} {desc}{marker}")

    def _handle_skill(self, arg: str) -> None:
        """Invoke a skill."""
        if not arg:
            self._display.print_error("Usage: /skill <name>")
            return

        from genai_cli.skills.executor import SkillExecutor
        from genai_cli.skills.registry import SkillRegistry

        registry = SkillRegistry(self._config)
        executor = SkillExecutor(self._config, self._display, registry)

        files = list(self._queued_files) if self._queued_files else None
        self._queued_files.clear()

        result = executor.execute(
            arg,
            files=files,
            auto_apply=self._auto_apply,
        )
        if result:
            self._display.print_info(
                f"Skill completed: {len(result.rounds)} rounds"
            )

    def _handle_skills(self) -> None:
        """List available skills."""
        from genai_cli.skills.registry import SkillRegistry

        registry = SkillRegistry(self._config)
        skills = registry.list_skills()
        if not skills:
            self._display.print_info("No skills found.")
            return
        self._display.print_info("Available skills:")
        for s in skills:
            desc = s.description.strip()[:60]
            self._display.print_info(f"  {s.name:25s} {desc}")

    def _handle_rewind(self, arg: str) -> None:
        """Rewind conversation by removing the last N turns."""
        turns = 1
        if arg:
            if not arg.isdigit() or int(arg) < 1:
                self._display.print_error(
                    "Usage: /rewind [n]  (n = positive integer)"
                )
                return
            turns = int(arg)

        messages = self._session.get("messages", [])
        to_remove = turns * 2  # each turn = user + assistant

        if to_remove > len(messages):
            available = len(messages) // 2
            self._display.print_error(
                f"Cannot rewind {turns} turn(s). Only {available} available."
            )
            return

        removed = messages[-to_remove:]
        total_tokens = sum(m.get("tokens_consumed", 0) for m in removed)
        total_cost = sum(m.get("token_cost", 0.0) for m in removed)

        self._session["messages"] = messages[:-to_remove]
        self._token_tracker.subtract_consumed(total_tokens, total_cost)

        self._display.print_success(
            f"Rewound {turns} turn(s). Removed {total_tokens:,} tokens."
        )

    def _handle_export(self, arg: str) -> None:
        """Export session to a markdown file or system clipboard."""
        md = self._format_session_markdown()
        if not md:
            self._display.print_info("No messages to export.")
            return

        filename = arg.strip()
        if filename:
            Path(filename).write_text(md, encoding="utf-8")
            self._display.print_info(f"Session exported to {filename}")
        else:
            if self._copy_to_clipboard(md):
                self._display.print_info("Session copied to clipboard.")
            else:
                self._display.print_error(
                    "Clipboard not available. Specify a filename: /export chat.md"
                )

    def _format_session_markdown(self) -> str:
        """Format the current session messages as markdown."""
        messages = self._session.get("messages", [])
        if not messages:
            return ""

        model_info = self._config.get_model(self._model_name)
        model_display = model_info.display_name if model_info else self._model_name
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        lines = [
            "# GenAI CLI Session Export",
            f"**Date**: {now}",
            f"**Model**: {model_display}",
            f"**Messages**: {len(messages)}",
            "",
            "---",
        ]

        for msg in messages:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            lines.append("")
            lines.append(f"## {role}")
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")

        return "\n".join(lines) + "\n"

    def _copy_to_clipboard(self, text: str) -> bool:
        """Copy text to the system clipboard. Returns True on success."""
        if sys.platform == "darwin":
            cmd = ["pbcopy"]
        elif sys.platform == "win32":
            cmd = ["clip"]
        else:
            cmd = ["xclip", "-selection", "clipboard"]

        try:
            subprocess.run(cmd, input=text, text=True, check=True)  # noqa: S603
            return True
        except (FileNotFoundError, subprocess.SubprocessError):
            return False

    def _handle_quit(self) -> None:
        """Save session and exit."""
        # Save token tracker state
        self._session["token_tracker"] = self._token_tracker.to_dict()
        path = self._session_mgr.save_session(self._session)
        sid = self._session["session_id"]
        self._display.print_success(f"Session saved: {sid}")
        self._running = False
        if self._client:
            self._client.close()

    def _send_message(self, text: str) -> None:
        """Send a message to the AI, using agent loop if enabled."""
        try:
            client = self._get_client()
        except AuthError as e:
            self._display.print_error(str(e))
            return

        # Agent mode
        if self._agent_rounds > 0:
            from genai_cli.agent import AgentLoop

            agent = AgentLoop(
                self._config, client, self._display,
                self._token_tracker, self._session,
                auto_apply=self._auto_apply,
                max_rounds=self._agent_rounds,
            )
            files = list(self._queued_files) if self._queued_files else None
            self._queued_files.clear()
            agent.run(
                text, self._model_name, files=files,
                system_prompt=self._config.get_system_prompt(),
            )
            self._agent_rounds = 0
            return

        session_id = self._session["session_id"]

        # Upload queued files (ensure session exists on API first)
        if self._queued_files:
            bundles, _unmatched = self._bundler.bundle_files(self._queued_files)
            if bundles:
                try:
                    client.ensure_session(session_id, self._model_name)
                    client.upload_bundles(session_id, bundles)
                    self._display.print_success("Files uploaded")
                except Exception as e:
                    self._display.print_error(f"Upload failed: {e}")
            self._queued_files.clear()

        # Add user message to session
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=text,
        )
        self._session_mgr.add_message(self._session, user_msg)

        # Send and get response
        use_streaming = self._config.settings.streaming

        try:
            with self._display.spinner("Thinking..."):
                full_text, chat_msg = stream_or_complete(
                    client, text, self._model_name, session_id,
                    self._config, use_streaming,
                )
        except AuthError as e:
            self._display.print_error(str(e))
            return
        except Exception as e:
            self._display.print_error(f"Request failed: {e}")
            return

        self._display.print_message(full_text, role="assistant")

        # Parse and apply code blocks from response
        from genai_cli.applier import FileApplier, UnifiedParser

        parser = UnifiedParser()
        edits, legacy_blocks = parser.parse(full_text)
        applier = FileApplier(self._config, self._display)
        mode = "auto" if self._auto_apply else "confirm"

        if edits:
            results = applier.apply_edits(edits, mode)
            applied = [r for r in results if r.success]
            failed = [r for r in results if not r.success]
            if applied:
                self._display.print_success(
                    f"Applied {len(applied)} edit(s)"
                )
            for f in failed:
                self._display.print_error(
                    f"Failed: {f.file_path}: {f.error_message}"
                )
        elif legacy_blocks:
            applier.apply_all(legacy_blocks, mode)

        # Track tokens
        if chat_msg and chat_msg.tokens_consumed:
            self._token_tracker.add_consumed(
                chat_msg.tokens_consumed, chat_msg.token_cost
            )

            # Add assistant message to session
            self._session_mgr.add_message(self._session, chat_msg)

        # Show token status
        usage = self._token_tracker.to_usage()
        self._display.print_token_status(usage)

        # Check thresholds
        warning = self._token_tracker.check_thresholds()
        if warning:
            self._display.print_warning(warning)
