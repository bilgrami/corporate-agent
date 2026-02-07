"""Terminal output rendering using rich."""

from __future__ import annotations

import sys
from io import StringIO
from typing import IO, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from genai_cli.models import ModelInfo, TokenUsage


class Display:
    """Terminal display helpers powered by rich."""

    def __init__(self, file: IO[str] | None = None) -> None:
        self._file = file or sys.stdout
        self._console = Console(file=self._file)

    def print_welcome(
        self,
        version: str,
        model: str,
        context_window: int,
    ) -> None:
        """Print the REPL welcome banner."""
        self._console.print(f"\n  Corporate AI CLI v{version} | Model: {model}")
        self._console.print(f"  Context: 0 / {context_window:,} tokens")
        self._console.print("  Type /help for commands, Ctrl+C to exit\n")

    def print_message(self, content: str, role: str = "assistant") -> None:
        """Print a chat message, rendering markdown for assistant."""
        if role == "assistant":
            self._console.print()
            self._console.print(Markdown(content))
            self._console.print()
        else:
            self._console.print(f"[bold]You>[/bold] {content}")

    def print_error(self, message: str) -> None:
        """Print an error message in red."""
        self._console.print(f"[bold red]Error:[/bold red] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message in yellow."""
        self._console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def print_success(self, message: str) -> None:
        """Print a success message in green."""
        self._console.print(f"[bold green]✓[/bold green] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message."""
        self._console.print(f"  {message}")

    def print_token_status(self, usage: TokenUsage) -> None:
        """Print token usage with color coding."""
        ratio = usage.usage_ratio
        if ratio >= 0.95:
            color = "bold red"
        elif ratio >= 0.80:
            color = "bold yellow"
        else:
            color = "green"

        pct = ratio * 100
        self._console.print(
            f"  Context: [{color}]{usage.consumed:,} / "
            f"{usage.context_window:,} tokens ({pct:.0f}%)[/{color}]"
        )

    def print_models_table(self, models: dict[str, ModelInfo]) -> None:
        """Print a table of available models."""
        table = Table(title="Available Models")
        table.add_column("Name", style="cyan")
        table.add_column("Display Name")
        table.add_column("Provider")
        table.add_column("Tier")
        table.add_column("Context", justify="right")
        table.add_column("Max Output", justify="right")
        table.add_column("Input $/1K", justify="right")
        table.add_column("Output $/1K", justify="right")

        for name, model in sorted(models.items()):
            table.add_row(
                name,
                model.display_name,
                model.provider,
                model.tier,
                f"{model.context_window:,}",
                f"{model.max_output_tokens:,}",
                f"${model.cost_per_1k_input:.4f}",
                f"${model.cost_per_1k_output:.4f}",
            )

        self._console.print(table)

    def print_diff(
        self, path: str, old_content: str, new_content: str
    ) -> None:
        """Print a colored diff between old and new content."""
        import difflib

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}"
        )
        for line in diff:
            line = line.rstrip("\n")
            if line.startswith("+") and not line.startswith("+++"):
                self._console.print(f"[green]{line}[/green]")
            elif line.startswith("-") and not line.startswith("---"):
                self._console.print(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                self._console.print(f"[cyan]{line}[/cyan]")
            else:
                self._console.print(line)

    def print_history(self, sessions: list[dict[str, Any]]) -> None:
        """Print a list of chat sessions."""
        table = Table(title="Recent Conversations")
        table.add_column("Session ID", style="cyan")
        table.add_column("Model")
        table.add_column("Messages", justify="right")
        table.add_column("Date")

        for session in sessions:
            sid = session.get("SessionId", "")
            model = session.get("ModelName", "")
            msg_count = str(len(session.get("Messages", []))) if "Messages" in session else "?"
            ts = session.get("TimestampUTC", "")
            table.add_row(sid[:12] + "...", model, msg_count, ts[:19])

        self._console.print(table)

    def print_usage(self, usage_data: dict[str, Any]) -> None:
        """Print user usage information."""
        table = Table(title="Token Usage")
        for key, value in usage_data.items():
            table.add_column(str(key))
        if usage_data:
            table.add_row(*[str(v) for v in usage_data.values()])
        self._console.print(table)

    def spinner(self, message: str = "Thinking...") -> Any:
        """Return a rich status context manager."""
        return self._console.status(message)

    def confirm(self, message: str) -> bool:
        """Ask for Y/n confirmation."""
        response = input(f"{message} [Y/n]: ").strip().lower()
        return response in ("", "y", "yes")

    def print_bundle_summary(
        self,
        file_type: str,
        count: int,
        estimated_tokens: int,
    ) -> None:
        """Print summary of a file bundle."""
        self._console.print(
            f"  [bold green]✓[/bold green] Queued {count} {file_type} "
            f"file{'s' if count != 1 else ''} (~{estimated_tokens:,} tokens)"
        )

    def print_file_list(self, paths: list[str]) -> None:
        """Print a list of file paths."""
        for path in paths:
            self._console.print(f"    {path}")
