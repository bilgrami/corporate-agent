"""Tests for streaming module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from genai_cli.config import ConfigManager
from genai_cli.streaming import StreamHandler, stream_or_complete


class TestStreamHandler:
    def test_parse_sse_basic(self) -> None:
        text = 'data: {"token": "Hello"}\ndata: {"token": " world"}\ndata: [DONE]\n'
        tokens = list(StreamHandler.parse_sse_lines(text))
        assert tokens == ["Hello", " world"]

    def test_parse_sse_done_stops(self) -> None:
        text = 'data: {"token": "A"}\ndata: [DONE]\ndata: {"token": "B"}\n'
        tokens = list(StreamHandler.parse_sse_lines(text))
        assert tokens == ["A"]

    def test_parse_sse_string_data(self) -> None:
        text = 'data: "hello"\n'
        tokens = list(StreamHandler.parse_sse_lines(text))
        assert tokens == ["hello"]

    def test_parse_sse_plain_text(self) -> None:
        text = "data: plain text\n"
        tokens = list(StreamHandler.parse_sse_lines(text))
        assert tokens == ["plain text"]

    def test_parse_sse_skips_comments(self) -> None:
        text = ': comment\ndata: {"token": "Hi"}\n'
        tokens = list(StreamHandler.parse_sse_lines(text))
        assert tokens == ["Hi"]

    def test_parse_sse_skips_empty(self) -> None:
        text = '\n\ndata: {"token": "Hi"}\n\n'
        tokens = list(StreamHandler.parse_sse_lines(text))
        assert tokens == ["Hi"]

    def test_parse_sse_message_field(self) -> None:
        text = 'data: {"Message": "response"}\n'
        tokens = list(StreamHandler.parse_sse_lines(text))
        assert tokens == ["response"]

    def test_parse_sse_response(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.text = 'data: {"token": "A"}\ndata: {"token": "B"}\ndata: [DONE]\n'
        tokens = list(StreamHandler.parse_sse_response(resp))
        assert tokens == ["A", "B"]


class TestStreamOrComplete:
    def test_fallback_to_complete(self, mock_config: ConfigManager) -> None:
        client = MagicMock()
        client.stream_chat.side_effect = httpx.HTTPError("connection failed")
        client.create_chat.return_value = {
            "SessionId": "s1",
            "UserOrBot": "assistant",
            "Message": "fallback response",
            "TokensConsumed": 50,
            "TokenCost": 0.001,
            "ModelName": "gpt-5",
            "DisplayName": "GPT-5",
            "TimestampUTC": "2026-02-07T12:00:00Z",
        }
        client.parse_message = MagicMock(
            return_value=MagicMock(content="fallback response")
        )

        text, msg = stream_or_complete(
            client, "hello", "gpt-5", None, mock_config, use_streaming=True
        )
        assert text == "fallback response"

    def test_no_stream_mode(self, mock_config: ConfigManager) -> None:
        client = MagicMock()
        client.create_chat.return_value = {
            "SessionId": "s1",
            "Message": "direct response",
        }
        client.parse_message.return_value = MagicMock(content="direct response")

        text, msg = stream_or_complete(
            client, "hello", "gpt-5", None, mock_config, use_streaming=False
        )
        assert text == "direct response"
        client.stream_chat.assert_not_called()
