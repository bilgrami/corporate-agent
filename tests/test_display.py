"""Tests for display module."""

from __future__ import annotations

from io import StringIO

import pytest

from genai_cli.display import Display
from genai_cli.models import ModelInfo, TokenUsage


class TestDisplay:
    def test_print_welcome(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_welcome("0.1.0", "GPT-5", 128000)
        text = out.getvalue()
        assert "0.1.0" in text
        assert "GPT-5" in text
        assert "128,000" in text

    def test_print_message_assistant(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_message("Hello world", role="assistant")
        text = out.getvalue()
        assert "Hello world" in text

    def test_print_message_user(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_message("my question", role="user")
        text = out.getvalue()
        assert "my question" in text

    def test_print_error(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_error("something broke")
        text = out.getvalue()
        assert "something broke" in text

    def test_print_warning(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_warning("watch out")
        text = out.getvalue()
        assert "watch out" in text

    def test_print_success(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_success("done!")
        text = out.getvalue()
        assert "done!" in text

    def test_print_token_status_normal(self) -> None:
        out = StringIO()
        d = Display(file=out)
        usage = TokenUsage(consumed=10000, context_window=128000)
        d.print_token_status(usage)
        text = out.getvalue()
        assert "10,000" in text
        assert "128,000" in text

    def test_print_token_status_warning(self) -> None:
        out = StringIO()
        d = Display(file=out)
        usage = TokenUsage(consumed=108800, context_window=128000)  # 85%
        d.print_token_status(usage)
        text = out.getvalue()
        assert "108,800" in text

    def test_print_token_status_critical(self) -> None:
        out = StringIO()
        d = Display(file=out)
        usage = TokenUsage(consumed=124000, context_window=128000)  # 97%
        d.print_token_status(usage)
        text = out.getvalue()
        assert "124,000" in text

    def test_print_models_table(self, mock_models: dict[str, ModelInfo]) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_models_table(mock_models)
        text = out.getvalue()
        assert "GPT-5" in text
        # Rich may wrap text across lines, so check individual words
        assert "Claude" in text
        assert "Sonnet" in text

    def test_print_diff(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_diff("test.py", "line1\nline2\n", "line1\nline2_changed\n")
        text = out.getvalue()
        assert "test.py" in text

    def test_print_bundle_summary(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_bundle_summary("code", 5, 3200)
        text = out.getvalue()
        assert "5" in text
        assert "code" in text
        assert "3,200" in text

    def test_print_file_list(self) -> None:
        out = StringIO()
        d = Display(file=out)
        d.print_file_list(["src/a.py", "src/b.py"])
        text = out.getvalue()
        assert "src/a.py" in text
        assert "src/b.py" in text
