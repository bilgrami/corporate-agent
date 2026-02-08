"""Response adapter: maps between API field names and internal snake_case names."""

from __future__ import annotations

import re
from typing import Any

from genai_cli.models import ChatMessage


def _resolve_path(data: Any, path: str) -> Any:
    """Resolve a dotted path with optional array indexing.

    Examples:
        _resolve_path({"a": {"b": 1}}, "a.b") -> 1
        _resolve_path({"Steps": [{"data": "hi"}]}, "Steps[0].data") -> "hi"
    """
    current: Any = data
    for segment in path.split("."):
        if current is None:
            return None
        match = re.match(r"^(\w+)\[(\d+)\]$", segment)
        if match:
            key, idx = match.group(1), int(match.group(2))
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return None
        else:
            if isinstance(current, dict):
                current = current.get(segment)
            else:
                return None
    return current


class ResponseMapper:
    """Maps between API-specific field names and internal representations.

    Loads field mappings from a parsed api_format config dict and provides
    methods to translate API responses into internal data structures.
    """

    def __init__(self, api_format: dict[str, Any]) -> None:
        self._endpoints = api_format.get("endpoints", {})
        self._request_fields = api_format.get("request_fields", {})
        self._message_fields = api_format.get("message_fields", {})
        self._role_values = api_format.get("role_values", {})
        self._history_fields = api_format.get("history_fields", {})
        self._usage_fields = api_format.get("usage_fields", {})
        self._document_fields = api_format.get("document_fields", {})
        self._stream = api_format.get("stream", {})
        self._endpoint_methods = api_format.get("endpoint_methods", {})
        self._endpoint_content_types = api_format.get("endpoint_content_types", {})
        self._stream_request_fields = api_format.get("stream_request_fields", {})
        self._stream_request_defaults = api_format.get("stream_request_defaults", {})

    # ---- Endpoints ----

    def endpoint(self, name: str, **kwargs: str) -> str:
        """Get an endpoint path, formatting placeholders like {session_id}."""
        template = self._endpoints.get(name, "")
        return template.format(**kwargs) if kwargs else template

    def endpoint_method(self, name: str) -> str:
        """Return the HTTP method for an endpoint (default GET)."""
        return self._endpoint_methods.get(name, "GET")

    def endpoint_content_type(self, name: str) -> str:
        """Return the content type for an endpoint (default application/json)."""
        return self._endpoint_content_types.get(name, "application/json")

    def build_stream_payload(self, **kwargs: str) -> dict[str, str]:
        """Build stream request payload, mapping internal names to API names and merging defaults."""
        payload = dict(self._stream_request_defaults)
        for internal_name, value in kwargs.items():
            api_name = self._stream_request_fields.get(internal_name, internal_name)
            payload[api_name] = value
        return payload

    # ---- Request building ----

    def build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        """Build an API request payload from internal field names."""
        return {
            self._request_fields.get(k, k): v
            for k, v in kwargs.items()
        }

    # ---- Response mapping ----

    def map_message(self, data: dict[str, Any]) -> ChatMessage:
        """Map an API response dict to a ChatMessage."""
        role_field = self._message_fields.get("role", "UserOrBot")
        assistant_val = self._role_values.get("assistant", "assistant")
        raw_role = data.get(role_field, "")
        role = "assistant" if raw_role == assistant_val else "user"

        return ChatMessage(
            session_id=self._get(data, "session_id", self._message_fields, ""),
            role=role,
            content=self._get(data, "content", self._message_fields, ""),
            timestamp=self._get(data, "timestamp", self._message_fields, ""),
            model_name=self._get(data, "model_name", self._message_fields, ""),
            display_name=self._get(data, "display_name", self._message_fields, ""),
            tokens_consumed=self._get(data, "tokens_consumed", self._message_fields, 0),
            token_cost=self._get(data, "token_cost", self._message_fields, 0.0),
            upload_content=self._get(data, "upload_content", self._message_fields, None),
        )

    def map_history_entry(self, data: dict[str, Any]) -> dict[str, Any]:
        """Map an API history entry to internal field names."""
        return {
            internal: data.get(self._history_fields.get(internal, internal), default)
            for internal, default in [
                ("session_id", ""),
                ("chat_title", ""),
                ("timestamp", ""),
                ("user_email", ""),
            ]
        }

    def map_usage(self, data: dict[str, Any]) -> dict[str, Any]:
        """Map API usage response to internal field names."""
        return {
            internal: data.get(api_name)
            for internal, api_name in self._usage_fields.items()
        }

    def map_document(self, data: dict[str, Any]) -> dict[str, Any]:
        """Map API document details to internal field names."""
        return {
            internal: data.get(api_name)
            for internal, api_name in self._document_fields.items()
        }

    # ---- Stream support ----

    @property
    def stream_format(self) -> str:
        return self._stream.get("format", "sse")

    @property
    def stream_line_prefix(self) -> str:
        return self._stream.get("line_prefix", "data: ")

    @property
    def stream_done_signal(self) -> str:
        return self._stream.get("done_signal", "[DONE]")

    @property
    def stream_content_paths(self) -> list[str]:
        return self._stream.get("content_paths", ["token", "Message"])

    def extract_stream_content(self, data: dict[str, Any]) -> str:
        """Extract text content from a stream chunk using configured paths."""
        for path in self.stream_content_paths:
            value = _resolve_path(data, path)
            if value:
                return str(value)
        return ""

    def is_stream_complete(self, data: dict[str, Any]) -> bool:
        """Check if a stream chunk is the final one."""
        task_field = self._stream.get("task_field", "")
        if not task_field:
            return False
        return data.get(task_field) == self._stream.get("task_complete", "Complete")

    def map_stream_final(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from the final stream chunk."""
        final_fields = self._stream.get("final_chunk_fields", {})
        return {
            internal: data.get(api_name)
            for internal, api_name in final_fields.items()
        }

    # ---- Internal helpers ----

    @staticmethod
    def _get(
        data: dict[str, Any],
        internal_name: str,
        field_map: dict[str, str],
        default: Any,
    ) -> Any:
        api_name = field_map.get(internal_name, internal_name)
        return data.get(api_name, default)
