"""Tests for response mapper module."""

from __future__ import annotations

import pytest

from genai_cli.mapper import ResponseMapper, _resolve_path


# ---- Default config matching config/api_format.yaml ----

DEFAULT_FORMAT: dict = {
    "endpoints": {
        "usage": "/api/v1/user/usage",
        "chat_history": "/api/v1/chathistory/",
        "chat_create": "/api/v1/chathistory/create",
        "conversation": "/api/v1/chathistory/{session_id}",
        "document_upload": "/api/v1/conversation/{session_id}/document/upload",
        "stream": "/api/v1/conversation/{session_id}/stream",
    },
    "endpoint_methods": {
        "chat_create": "GET",
        "stream": "POST",
        "document_upload": "PUT",
    },
    "endpoint_content_types": {
        "stream": "multipart/form-data",
    },
    "stream_request_fields": {
        "message": "user_input",
        "model_name": "model_name",
    },
    "stream_request_defaults": {
        "web_search": "true",
        "temperature": "0.5",
        "premium": "false",
    },
    "request_fields": {
        "session_id": "SessionId",
        "message": "Message",
        "model_name": "ModelName",
    },
    "message_fields": {
        "session_id": "SessionId",
        "role": "UserOrBot",
        "content": "Message",
        "timestamp": "TimestampUTC",
        "model_name": "ModelName",
        "display_name": "DisplayName",
        "tokens_consumed": "TokensConsumed",
        "token_cost": "TokenCost",
        "upload_content": "UploadContent",
    },
    "role_values": {"assistant": "assistant", "user": "user"},
    "history_fields": {
        "session_id": "SessionId",
        "chat_title": "ChatTitle",
        "timestamp": "Timestamp",
        "user_email": "UserEmail",
    },
    "usage_fields": {
        "input_tokens": "input_tokens",
        "output_tokens": "output_tokens",
        "amount_dollars": "amount_dollars",
    },
    "document_fields": {
        "document_id": "DocumentId",
        "tokens_consumed": "TokensConsumed",
        "token_cost": "TokenCost",
        "file_name": "FileName",
        "processing_status": "ProcessingStatus",
    },
    "stream": {
        "format": "jsonlines",
        "line_prefix": "",
        "done_signal": "[DONE]",
        "content_paths": ["Steps[0].data", "Message"],
        "task_field": "Task",
        "task_complete": "Complete",
        "final_chunk_fields": {
            "tokens_consumed": "TokensConsumed",
            "token_cost": "TokenCost",
            "session_id": "SessionId",
        },
    },
}


@pytest.fixture
def mapper() -> ResponseMapper:
    return ResponseMapper(DEFAULT_FORMAT)


# ---- _resolve_path tests ----


class TestResolvePath:
    def test_simple_key(self) -> None:
        assert _resolve_path({"a": 1}, "a") == 1

    def test_nested_key(self) -> None:
        assert _resolve_path({"a": {"b": 2}}, "a.b") == 2

    def test_array_index(self) -> None:
        data = {"Steps": [{"data": "hello"}]}
        assert _resolve_path(data, "Steps[0].data") == "hello"

    def test_missing_key(self) -> None:
        assert _resolve_path({}, "a.b") is None

    def test_out_of_bounds(self) -> None:
        assert _resolve_path({"a": []}, "a[5]") is None

    def test_none_data(self) -> None:
        assert _resolve_path(None, "a") is None

    def test_deep_nested(self) -> None:
        data = {"a": {"b": {"c": 42}}}
        assert _resolve_path(data, "a.b.c") == 42

    def test_array_in_middle(self) -> None:
        data = {"choices": [{"delta": {"content": "hi"}}]}
        assert _resolve_path(data, "choices[0].delta.content") == "hi"


# ---- ResponseMapper tests ----


class TestEndpoints:
    def test_simple_endpoint(self, mapper: ResponseMapper) -> None:
        assert mapper.endpoint("usage") == "/api/v1/user/usage"

    def test_endpoint_with_placeholder(self, mapper: ResponseMapper) -> None:
        result = mapper.endpoint("conversation", session_id="abc-123")
        assert result == "/api/v1/chathistory/abc-123"

    def test_unknown_endpoint(self, mapper: ResponseMapper) -> None:
        assert mapper.endpoint("nonexistent") == ""


class TestRequestPayload:
    def test_build_payload(self, mapper: ResponseMapper) -> None:
        payload = mapper.build_request_payload(
            session_id="abc", message="hello", model_name="gpt-5"
        )
        assert payload == {
            "SessionId": "abc",
            "Message": "hello",
            "ModelName": "gpt-5",
        }

    def test_unknown_field_passthrough(self, mapper: ResponseMapper) -> None:
        payload = mapper.build_request_payload(unknown_field="val")
        assert payload == {"unknown_field": "val"}


class TestMapMessage:
    def test_full_message(self, mapper: ResponseMapper) -> None:
        data = {
            "SessionId": "sess-1",
            "UserOrBot": "assistant",
            "Message": "Hello!",
            "TimestampUTC": "2026-02-08T00:00:00Z",
            "ModelName": "gpt-5-chat-global",
            "DisplayName": "GPT-5",
            "TokensConsumed": 150,
            "TokenCost": 0.003,
            "UploadContent": None,
        }
        msg = mapper.map_message(data)
        assert msg.session_id == "sess-1"
        assert msg.role == "assistant"
        assert msg.content == "Hello!"
        assert msg.tokens_consumed == 150
        assert msg.token_cost == pytest.approx(0.003)

    def test_user_role(self, mapper: ResponseMapper) -> None:
        msg = mapper.map_message({"UserOrBot": "user", "Message": "hi"})
        assert msg.role == "user"

    def test_defaults_on_missing(self, mapper: ResponseMapper) -> None:
        msg = mapper.map_message({})
        assert msg.session_id == ""
        assert msg.content == ""
        assert msg.tokens_consumed == 0
        assert msg.token_cost == 0.0


class TestMapHistory:
    def test_map_entry(self, mapper: ResponseMapper) -> None:
        data = {
            "SessionId": "abc-123",
            "ChatTitle": "My Chat",
            "Timestamp": "2026-02-03T18:24:15",
            "UserEmail": "user@corp.com",
        }
        result = mapper.map_history_entry(data)
        assert result["session_id"] == "abc-123"
        assert result["chat_title"] == "My Chat"
        assert result["timestamp"] == "2026-02-03T18:24:15"

    def test_defaults(self, mapper: ResponseMapper) -> None:
        result = mapper.map_history_entry({})
        assert result["session_id"] == ""
        assert result["chat_title"] == ""


class TestMapUsage:
    def test_map_usage(self, mapper: ResponseMapper) -> None:
        data = {
            "amount_dollars": 5.04,
            "input_tokens": 1192796,
            "output_tokens": 67420,
        }
        result = mapper.map_usage(data)
        assert result["input_tokens"] == 1192796
        assert result["output_tokens"] == 67420
        assert result["amount_dollars"] == pytest.approx(5.04)


class TestStreamSupport:
    def test_extract_steps_data(self, mapper: ResponseMapper) -> None:
        chunk = {"Steps": [{"data": "hello world", "type": "agent"}], "Message": "hello world"}
        assert mapper.extract_stream_content(chunk) == "hello world"

    def test_fallback_to_message(self, mapper: ResponseMapper) -> None:
        chunk = {"Message": "fallback text", "Steps": []}
        assert mapper.extract_stream_content(chunk) == "fallback text"

    def test_empty_chunk(self, mapper: ResponseMapper) -> None:
        assert mapper.extract_stream_content({}) == ""

    def test_is_complete(self, mapper: ResponseMapper) -> None:
        assert mapper.is_stream_complete({"Task": "Complete"}) is True
        assert mapper.is_stream_complete({"Task": "Intermediate"}) is False
        assert mapper.is_stream_complete({}) is False

    def test_map_final(self, mapper: ResponseMapper) -> None:
        chunk = {
            "Task": "Complete",
            "TokensConsumed": 3501,
            "TokenCost": 0.013,
            "SessionId": "sess-1",
        }
        result = mapper.map_stream_final(chunk)
        assert result["tokens_consumed"] == 3501
        assert result["token_cost"] == pytest.approx(0.013)
        assert result["session_id"] == "sess-1"

    def test_stream_properties(self, mapper: ResponseMapper) -> None:
        assert mapper.stream_format == "jsonlines"
        assert mapper.stream_line_prefix == ""
        assert mapper.stream_done_signal == "[DONE]"
        assert mapper.stream_content_paths == ["Steps[0].data", "Message"]


class TestEndpointMethod:
    def test_configured_method(self, mapper: ResponseMapper) -> None:
        assert mapper.endpoint_method("chat_create") == "GET"
        assert mapper.endpoint_method("stream") == "POST"
        assert mapper.endpoint_method("document_upload") == "PUT"

    def test_default_method(self, mapper: ResponseMapper) -> None:
        assert mapper.endpoint_method("usage") == "GET"
        assert mapper.endpoint_method("nonexistent") == "GET"


class TestEndpointContentType:
    def test_configured_content_type(self, mapper: ResponseMapper) -> None:
        assert mapper.endpoint_content_type("stream") == "multipart/form-data"

    def test_default_content_type(self, mapper: ResponseMapper) -> None:
        assert mapper.endpoint_content_type("chat_create") == "application/json"
        assert mapper.endpoint_content_type("nonexistent") == "application/json"


class TestBuildStreamPayload:
    def test_maps_fields_and_merges_defaults(self, mapper: ResponseMapper) -> None:
        payload = mapper.build_stream_payload(message="hello", model_name="gpt-5")
        assert payload == {
            "user_input": "hello",
            "model_name": "gpt-5",
            "web_search": "true",
            "temperature": "0.5",
            "premium": "false",
        }

    def test_overrides_defaults(self, mapper: ResponseMapper) -> None:
        payload = mapper.build_stream_payload(
            message="hi", model_name="gpt-5", temperature="0.9"
        )
        assert payload["temperature"] == "0.9"

    def test_empty_kwargs(self, mapper: ResponseMapper) -> None:
        payload = mapper.build_stream_payload()
        assert payload == {
            "web_search": "true",
            "temperature": "0.5",
            "premium": "false",
        }

    def test_no_config(self) -> None:
        m = ResponseMapper({})
        payload = m.build_stream_payload(message="hi")
        assert payload == {"message": "hi"}


class TestStreamEndpoint:
    def test_stream_endpoint(self, mapper: ResponseMapper) -> None:
        result = mapper.endpoint("stream", session_id="abc-123")
        assert result == "/api/v1/conversation/abc-123/stream"


class TestCustomFormat:
    """Test with an OpenAI-compatible config."""

    def test_openai_style(self) -> None:
        openai_format = {
            "message_fields": {
                "content": "choices[0].message.content",
                "role": "choices[0].message.role",
            },
            "stream": {
                "format": "sse",
                "line_prefix": "data: ",
                "done_signal": "[DONE]",
                "content_paths": ["choices[0].delta.content"],
                "task_field": "",
            },
        }
        m = ResponseMapper(openai_format)
        assert m.stream_format == "sse"
        assert m.stream_line_prefix == "data: "
        chunk = {"choices": [{"delta": {"content": "hi"}}]}
        assert m.extract_stream_content(chunk) == "hi"
        assert m.is_stream_complete({}) is False
