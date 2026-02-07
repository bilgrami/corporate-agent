"""SSE (Server-Sent Events) stream handler."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx

from genai_cli.config import ConfigManager
from genai_cli.models import ChatMessage


class StreamHandler:
    """Parse SSE event streams from the corporate API."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config

    @staticmethod
    def parse_sse_lines(text: str) -> Iterator[str]:
        """Parse SSE text into data payloads, yielding each token.

        SSE format:
            data: {"token": "hello"}
            data: [DONE]
        """
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

    If streaming is enabled, collects tokens into full text.
    Falls back to complete response on error.
    """
    if use_streaming:
        try:
            resp = client.stream_chat(message, model, session_id)
            handler = StreamHandler(config)
            tokens: list[str] = []
            for token in handler.parse_sse_response(resp):
                tokens.append(token)
            full_text = "".join(tokens)
            return full_text, None
        except (httpx.HTTPError, Exception):
            pass

    # Fallback to complete response
    result = client.create_chat(message, model, session_id)
    msg = client.parse_message(result)
    return msg.content, msg
