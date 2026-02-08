"""Tests for streaming module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from genai_cli.config import ConfigManager
from genai_cli.streaming import StreamHandler, stream_or_complete


# ---- Legacy SSE tests (backward-compat static methods) ----


class TestStreamHandlerSSE:
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


# ---- Mapper-driven stream parsing tests ----


class TestParseStreamResponse:
    """Tests for parse_stream_response with mapper-driven format detection."""

    def test_jsonlines_basic(self, mock_config: ConfigManager) -> None:
        """Parse JSON-lines stream (the default corporate format)."""
        handler = StreamHandler(mock_config)
        lines = [
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "Hello "}], "Message": "Hello "}),
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "world"}], "Message": "world"}),
            "[DONE]",
        ]
        resp = MagicMock(spec=httpx.Response)
        resp.text = "\n".join(lines)

        chunks = list(handler.parse_stream_response(resp))
        assert len(chunks) == 2
        assert chunks[0]["Task"] == "Intermediate"
        assert chunks[1]["Steps"][0]["data"] == "world"

    def test_jsonlines_done_stops(self, mock_config: ConfigManager) -> None:
        handler = StreamHandler(mock_config)
        lines = [
            json.dumps({"Message": "A"}),
            "[DONE]",
            json.dumps({"Message": "B"}),  # should not be yielded
        ]
        resp = MagicMock(spec=httpx.Response)
        resp.text = "\n".join(lines)

        chunks = list(handler.parse_stream_response(resp))
        assert len(chunks) == 1
        assert chunks[0]["Message"] == "A"

    def test_jsonlines_skips_empty_lines(self, mock_config: ConfigManager) -> None:
        handler = StreamHandler(mock_config)
        resp = MagicMock(spec=httpx.Response)
        resp.text = f'\n\n{json.dumps({"Message": "hi"})}\n\n'

        chunks = list(handler.parse_stream_response(resp))
        assert len(chunks) == 1

    def test_jsonlines_skips_bad_json(self, mock_config: ConfigManager) -> None:
        handler = StreamHandler(mock_config)
        resp = MagicMock(spec=httpx.Response)
        resp.text = f'not json\n{json.dumps({"Message": "ok"})}\n'

        chunks = list(handler.parse_stream_response(resp))
        assert len(chunks) == 1
        assert chunks[0]["Message"] == "ok"


class TestIterStreamContent:
    def test_extracts_steps_data(self, mock_config: ConfigManager) -> None:
        """Extract text from Steps[0].data (primary content path)."""
        handler = StreamHandler(mock_config)
        lines = [
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "Hello "}], "Message": "Hello "}),
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "world"}], "Message": "world"}),
        ]
        resp = MagicMock(spec=httpx.Response)
        resp.text = "\n".join(lines)

        tokens = list(handler.iter_stream_content(resp))
        assert tokens == ["Hello ", "world"]

    def test_fallback_to_message(self, mock_config: ConfigManager) -> None:
        """Falls back to Message field when Steps is empty."""
        handler = StreamHandler(mock_config)
        resp = MagicMock(spec=httpx.Response)
        resp.text = json.dumps({"Task": "Intermediate", "Steps": [], "Message": "fallback"})

        tokens = list(handler.iter_stream_content(resp))
        assert tokens == ["fallback"]

    def test_empty_chunks(self, mock_config: ConfigManager) -> None:
        handler = StreamHandler(mock_config)
        resp = MagicMock(spec=httpx.Response)
        resp.text = json.dumps({"Task": "Intermediate", "Steps": [], "Message": ""})

        tokens = list(handler.iter_stream_content(resp))
        assert tokens == []


class TestExtractFinalMetadata:
    def test_extracts_final_chunk(self, mock_config: ConfigManager) -> None:
        handler = StreamHandler(mock_config)
        lines = [
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "hi"}], "Message": "hi"}),
            json.dumps({
                "Task": "Complete",
                "TokensConsumed": 3501,
                "TokenCost": 0.013,
                "SessionId": "sess-1",
                "Steps": [],
                "Message": "",
            }),
        ]
        resp = MagicMock(spec=httpx.Response)
        resp.text = "\n".join(lines)

        meta = handler.extract_final_metadata(resp)
        assert meta is not None
        assert meta["tokens_consumed"] == 3501
        assert meta["token_cost"] == pytest.approx(0.013)
        assert meta["session_id"] == "sess-1"

    def test_no_final_chunk(self, mock_config: ConfigManager) -> None:
        handler = StreamHandler(mock_config)
        resp = MagicMock(spec=httpx.Response)
        resp.text = json.dumps({"Task": "Intermediate", "Message": "partial"})

        meta = handler.extract_final_metadata(resp)
        assert meta is None


# ---- stream_or_complete tests ----


class TestStreamOrComplete:
    def test_streaming_with_final_metadata(self, mock_config: ConfigManager) -> None:
        """Streaming returns text + ChatMessage with token data from final chunk."""
        lines = [
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "Hello "}], "Message": "Hello "}),
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "world"}], "Message": "world"}),
            json.dumps({
                "Task": "Complete",
                "TokensConsumed": 200,
                "TokenCost": 0.005,
                "SessionId": "sess-42",
                "Steps": [],
                "Message": "",
            }),
        ]
        resp = MagicMock(spec=httpx.Response)
        resp.text = "\n".join(lines)

        client = MagicMock()
        client.stream_chat.return_value = resp

        text, msg = stream_or_complete(
            client, "hello", "gpt-5", None, mock_config, use_streaming=True
        )
        assert text == "Hello world"
        assert msg is not None
        assert msg.tokens_consumed == 200
        assert msg.token_cost == pytest.approx(0.005)
        assert msg.session_id == "sess-42"
        assert msg.role == "assistant"

    def test_streaming_without_final_chunk(self, mock_config: ConfigManager) -> None:
        """When stream has no final chunk, returns text with no ChatMessage."""
        resp = MagicMock(spec=httpx.Response)
        resp.text = json.dumps({"Task": "Intermediate", "Steps": [{"data": "partial"}], "Message": "partial"})

        client = MagicMock()
        client.stream_chat.return_value = resp

        text, msg = stream_or_complete(
            client, "hello", "gpt-5", None, mock_config, use_streaming=True
        )
        assert text == "partial"
        assert msg is None

    def test_fallback_on_stream_error(self, mock_config: ConfigManager) -> None:
        """When streaming fails with HTTPError, fallback also tries stream_chat."""
        lines = [
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "recovered"}], "Message": "recovered"}),
            json.dumps({"Task": "Complete", "TokensConsumed": 50, "TokenCost": 0.001, "SessionId": "s1", "Steps": [], "Message": ""}),
        ]
        fallback_resp = MagicMock(spec=httpx.Response)
        fallback_resp.text = "\n".join(lines)

        client = MagicMock()
        client.stream_chat.side_effect = [
            httpx.HTTPError("connection failed"),
            fallback_resp,
        ]
        text, msg = stream_or_complete(
            client, "hello", "gpt-5", None, mock_config, use_streaming=True
        )
        assert text == "recovered"
        assert msg is not None

    def test_both_paths_fail(self, mock_config: ConfigManager) -> None:
        """When both streaming and fallback fail, returns empty."""
        client = MagicMock()
        client.stream_chat.side_effect = httpx.HTTPError("connection failed")
        text, msg = stream_or_complete(
            client, "hello", "gpt-5", None, mock_config, use_streaming=True
        )
        assert text == ""
        assert msg is None

    def test_no_stream_mode(self, mock_config: ConfigManager) -> None:
        """Non-streaming mode uses two-step create+stream, parsed as complete response."""
        lines = [
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "direct "}], "Message": "direct "}),
            json.dumps({"Task": "Intermediate", "Steps": [{"data": "response"}], "Message": "response"}),
            json.dumps({
                "Task": "Complete",
                "TokensConsumed": 50,
                "TokenCost": 0.001,
                "SessionId": "s1",
                "Steps": [],
                "Message": "",
            }),
        ]
        resp = MagicMock(spec=httpx.Response)
        resp.text = "\n".join(lines)

        client = MagicMock()
        client.stream_chat.return_value = resp

        text, msg = stream_or_complete(
            client, "hello", "gpt-5", None, mock_config, use_streaming=False
        )
        assert text == "direct response"
        assert msg is not None
        assert msg.tokens_consumed == 50
        client.stream_chat.assert_called_once()
