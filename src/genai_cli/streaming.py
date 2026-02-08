"""Stream handler supporting both SSE and JSON-lines formats via ResponseMapper."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx

from genai_cli.auth import AuthError
from genai_cli.config import ConfigManager
from genai_cli.mapper import ResponseMapper
from genai_cli.models import ChatMessage


class StreamHandler:
    """Parse streaming responses using config-driven format detection."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._mapper = config.mapper

    def parse_stream_response(self, response: httpx.Response) -> Iterator[dict[str, Any]]:
        """Parse a streaming response into JSON chunks.

        Supports both SSE (``data: {...}``) and JSON-lines (one JSON per line)
        based on the ``stream.format`` setting in api_format.yaml.
        """
        prefix = self._mapper.stream_line_prefix
        done_signal = self._mapper.stream_done_signal

        for line in response.text.splitlines():
            line = line.strip()
            if not line:
                continue

            # SSE: skip comment lines
            if self._mapper.stream_format == "sse" and line.startswith(":"):
                continue

            # Strip format-specific prefix (e.g. "data: " for SSE, "" for jsonlines)
            if prefix and line.startswith(prefix):
                payload = line[len(prefix):]
            elif self._mapper.stream_format == "sse":
                # SSE lines without the expected prefix are non-data lines
                continue
            else:
                payload = line

            if payload == done_signal:
                return

            try:
                data = json.loads(payload)
                if isinstance(data, dict):
                    yield data
            except json.JSONDecodeError:
                continue

    def iter_stream_content(self, response: httpx.Response) -> Iterator[str]:
        """Yield text content from each stream chunk."""
        for chunk in self.parse_stream_response(response):
            text = self._mapper.extract_stream_content(chunk)
            if text:
                yield text

    def extract_final_metadata(self, response: httpx.Response) -> dict[str, Any] | None:
        """Parse the full response and return metadata from the final chunk, if any."""
        for chunk in self.parse_stream_response(response):
            if self._mapper.is_stream_complete(chunk):
                return self._mapper.map_stream_final(chunk)
        return None

    # ---- Legacy SSE methods (kept for backward compatibility) ----

    @staticmethod
    def parse_sse_lines(text: str) -> Iterator[str]:
        """Parse SSE text into data payloads, yielding each token."""
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                payload = line[6:]
                if payload == "[DONE]":
                    return
                try:
                    data = json.loads(payload)
                    if isinstance(data, dict):
                        token = data.get("token") or data.get("Message", "")
                        if token:
                            yield token
                    elif isinstance(data, str):
                        yield data
                except json.JSONDecodeError:
                    yield payload

    @staticmethod
    def parse_sse_response(response: httpx.Response) -> Iterator[str]:
        """Parse an httpx Response with SSE content, yielding tokens."""
        for line in response.text.splitlines():
            line = line.strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                payload = line[6:]
                if payload == "[DONE]":
                    return
                try:
                    data = json.loads(payload)
                    if isinstance(data, dict):
                        token = data.get("token") or data.get("Message", "")
                        if token:
                            yield token
                    elif isinstance(data, str):
                        yield data
                except json.JSONDecodeError:
                    yield payload


def stream_or_complete(
    client: Any,
    message: str,
    model: str,
    session_id: str | None,
    config: ConfigManager,
    use_streaming: bool = True,
) -> tuple[str, ChatMessage | None]:
    """Send a message and return (full_text, chat_message).

    If streaming is enabled, collects text from stream chunks and builds
    a ChatMessage from the final chunk's metadata (tokens, cost, session_id).
    Falls back to complete response on error.
    """
    if use_streaming:
        try:
            resp = client.stream_chat(message, model, session_id)
            handler = StreamHandler(config)
            mapper = config.mapper

            # Collect text and find the final chunk in a single pass
            text_parts: list[str] = []
            final_meta: dict[str, Any] | None = None

            for chunk in handler.parse_stream_response(resp):
                text = mapper.extract_stream_content(chunk)
                if text:
                    text_parts.append(text)
                if mapper.is_stream_complete(chunk):
                    final_meta = mapper.map_stream_final(chunk)

            full_text = "".join(text_parts)

            # Build a ChatMessage from final chunk metadata if available
            chat_msg: ChatMessage | None = None
            if final_meta:
                chat_msg = ChatMessage(
                    session_id=final_meta.get("session_id", ""),
                    role="assistant",
                    content=full_text,
                    tokens_consumed=final_meta.get("tokens_consumed", 0),
                    token_cost=final_meta.get("token_cost", 0.0),
                )

            return full_text, chat_msg
        except AuthError:
            raise
        except (httpx.HTTPError, Exception):
            pass

    # Fallback: two-step create + stream, parsed as a complete response
    try:
        resp = client.stream_chat(message, model, session_id)
        handler = StreamHandler(config)
        mapper = config.mapper

        text_parts: list[str] = []
        final_meta: dict[str, Any] | None = None
        for chunk in handler.parse_stream_response(resp):
            text = mapper.extract_stream_content(chunk)
            if text:
                text_parts.append(text)
            if mapper.is_stream_complete(chunk):
                final_meta = mapper.map_stream_final(chunk)

        full_text = "".join(text_parts)
        chat_msg: ChatMessage | None = None
        if final_meta:
            chat_msg = ChatMessage(
                session_id=final_meta.get("session_id", ""),
                role="assistant",
                content=full_text,
                tokens_consumed=final_meta.get("tokens_consumed", 0),
                token_cost=final_meta.get("token_cost", 0.0),
            )
        return full_text, chat_msg
    except AuthError:
        raise
    except (httpx.HTTPError, Exception):
        return "", None
