# Adding Support for a Different Corporate GenAI API

GenAI CLI uses a YAML-driven field mapping system to translate between any
corporate AI platform's API and internal representations. Supporting a new
API requires **zero Python code changes** — you only edit a YAML config file.

## How It Works

The `ResponseMapper` class (`src/genai_cli/mapper.py`) reads field mappings
from `config/api_format.yaml` at startup. Every API interaction — endpoint
URLs, request payloads, response parsing, and stream handling — goes through
the mapper. The mapper translates between the API's field names (e.g.
`SessionId`, `UserOrBot`, `TokensConsumed`) and the internal snake_case
names used throughout the codebase (e.g. `session_id`, `role`,
`tokens_consumed`).

### Config Precedence

The API format config follows the same 3-level override chain as
`settings.yaml`:

| Priority | Location | Use Case |
|----------|----------|----------|
| 1 (highest) | `.genai-cli/api_format.yaml` | Project-specific override |
| 2 | `~/.genai-cli/api_format.yaml` | User-wide override |
| 3 (lowest) | `config/api_format.yaml` | Package defaults |

Higher-priority files are deep-merged on top of lower ones, so you only
need to specify the sections that differ from the default.

## Quick Start

1. Copy the default config as a starting point:

```bash
mkdir -p ~/.genai-cli
cp config/api_format.yaml ~/.genai-cli/api_format.yaml
```

2. Edit `~/.genai-cli/api_format.yaml` to match your API's field names
   and endpoint paths.

3. Run `genai auth login` to set your API base URL and token.

4. Verify with `genai usage` or `genai history`.

## Full Config Reference

Below is the complete `api_format.yaml` with annotations for every section.

```yaml
api_format:
  name: "my-platform-v1"       # Descriptive label (not used in code)

  # ──────────────────────────────────────────────
  # ENDPOINT PATHS
  # ──────────────────────────────────────────────
  # URL paths appended to the api_base_url from settings.yaml.
  # Use {session_id} as a placeholder — it gets substituted at runtime.
  endpoints:
    usage: "/api/v1/user/usage"
    chat_history: "/api/v1/chathistory/"
    chat_create: "/api/v1/chathistory/create"
    conversation: "/api/v1/chathistory/{session_id}"
    conversation_details: "/api/v1/conversation/{session_id}/details"
    document_upload: "/api/v1/conversation/{session_id}/document/upload"

  # ──────────────────────────────────────────────
  # REQUEST FIELDS (outbound)
  # ──────────────────────────────────────────────
  # Maps internal name (left) → API field name (right) for POST payloads.
  # When the CLI sends { session_id: "abc", message: "hi", model_name: "gpt-5" }
  # the mapper translates it to { "SessionId": "abc", "Message": "hi", "ModelName": "gpt-5" }.
  request_fields:
    session_id: "SessionId"
    message: "Message"
    model_name: "ModelName"

  # ──────────────────────────────────────────────
  # MESSAGE FIELDS (inbound — chat responses)
  # ──────────────────────────────────────────────
  # Maps internal name → API field name for parsing chat message responses.
  # The right side is the key name the API uses in its JSON response.
  message_fields:
    session_id: "SessionId"
    role: "UserOrBot"               # Field containing user/assistant indicator
    content: "Message"              # Field containing the message text
    timestamp: "TimestampUTC"
    model_name: "ModelName"
    display_name: "DisplayName"
    tokens_consumed: "TokensConsumed"
    token_cost: "TokenCost"
    upload_content: "UploadContent"

  # ──────────────────────────────────────────────
  # ROLE VALUES
  # ──────────────────────────────────────────────
  # What string values the API uses to represent each role.
  # The CLI normalizes these to "assistant" and "user" internally.
  role_values:
    assistant: "assistant"          # Some APIs use "bot", "ai", "system"
    user: "user"                    # Some APIs use "human", "customer"

  # ──────────────────────────────────────────────
  # HISTORY FIELDS (chat session list)
  # ──────────────────────────────────────────────
  # Maps internal name → API field name for the chat history listing endpoint.
  history_fields:
    session_id: "SessionId"
    chat_title: "ChatTitle"
    timestamp: "Timestamp"
    user_email: "UserEmail"

  # ──────────────────────────────────────────────
  # USAGE FIELDS
  # ──────────────────────────────────────────────
  # Maps internal name → API field name for the usage/billing endpoint.
  usage_fields:
    input_tokens: "input_tokens"
    output_tokens: "output_tokens"
    amount_dollars: "amount_dollars"

  # ──────────────────────────────────────────────
  # DOCUMENT FIELDS
  # ──────────────────────────────────────────────
  # Maps internal name → API field name for uploaded document details.
  document_fields:
    document_id: "DocumentId"
    tokens_consumed: "TokensConsumed"
    token_cost: "TokenCost"
    file_name: "FileName"
    processing_status: "ProcessingStatus"

  # ──────────────────────────────────────────────
  # STREAMING
  # ──────────────────────────────────────────────
  stream:
    # Format: "sse" or "jsonlines"
    #   sse       = lines prefixed with "data: " (OpenAI-style)
    #   jsonlines = one JSON object per line (no prefix)
    format: "jsonlines"

    # Prefix stripped from each line before JSON parsing.
    # Set to "data: " for SSE, "" for JSON-lines.
    line_prefix: ""

    # Sentinel value indicating end of stream.
    done_signal: "[DONE]"

    # Dotted paths to extract text content from each chunk.
    # Tried in order — first non-empty value wins.
    # Supports array indexing: "choices[0].delta.content"
    content_paths:
      - "Steps[0].data"
      - "Message"

    # Field that indicates whether a chunk is intermediate or final.
    # Set to "" if the API has no completion indicator.
    task_field: "Task"
    task_complete: "Complete"

    # Fields to extract from the final chunk (token counts, session ID).
    # These populate the ChatMessage returned after streaming finishes.
    final_chunk_fields:
      tokens_consumed: "TokensConsumed"
      token_cost: "TokenCost"
      session_id: "SessionId"
```

## Examples for Common API Styles

### OpenAI-Compatible API

```yaml
api_format:
  name: "openai-compatible"

  endpoints:
    chat_create: "/v1/chat/completions"

  request_fields:
    message: "messages"
    model_name: "model"

  message_fields:
    content: "choices[0].message.content"
    role: "choices[0].message.role"
    tokens_consumed: "usage.total_tokens"

  role_values:
    assistant: "assistant"
    user: "user"

  stream:
    format: "sse"
    line_prefix: "data: "
    done_signal: "[DONE]"
    content_paths:
      - "choices[0].delta.content"
    task_field: ""
```

### Azure OpenAI Service

```yaml
api_format:
  name: "azure-openai"

  endpoints:
    chat_create: "/openai/deployments/{model_name}/chat/completions?api-version=2024-02-01"

  message_fields:
    content: "choices[0].message.content"
    role: "choices[0].message.role"
    tokens_consumed: "usage.total_tokens"

  role_values:
    assistant: "assistant"
    user: "user"

  stream:
    format: "sse"
    line_prefix: "data: "
    done_signal: "[DONE]"
    content_paths:
      - "choices[0].delta.content"
    task_field: ""
```

### API with camelCase Fields

```yaml
api_format:
  name: "camel-case-api"

  message_fields:
    session_id: "sessionId"
    role: "senderType"
    content: "messageBody"
    timestamp: "createdAt"
    tokens_consumed: "tokensUsed"
    token_cost: "costUsd"

  role_values:
    assistant: "bot"
    user: "human"

  history_fields:
    session_id: "conversationId"
    chat_title: "title"
    timestamp: "lastUpdated"
    user_email: "ownerEmail"

  stream:
    format: "jsonlines"
    line_prefix: ""
    done_signal: ""
    content_paths:
      - "text"
      - "delta"
    task_field: "status"
    task_complete: "done"
    final_chunk_fields:
      tokens_consumed: "tokensUsed"
      token_cost: "costUsd"
      session_id: "conversationId"
```

## Content Path Syntax

The `content_paths` and `message_fields` values support a dotted-path
syntax with optional array indexing. This lets you reach into nested
API responses without writing any code.

| Path | Resolves To |
|------|-------------|
| `Message` | `data["Message"]` |
| `choices[0].delta.content` | `data["choices"][0]["delta"]["content"]` |
| `Steps[0].data` | `data["Steps"][0]["data"]` |
| `result.text` | `data["result"]["text"]` |
| `a.b.c` | `data["a"]["b"]["c"]` |

If a path resolves to `None` or the key is missing, the mapper moves to
the next path in the list. This lets you define a fallback chain (e.g. try
`Steps[0].data` first, then fall back to `Message`).

## Partial Overrides

Because configs are deep-merged, you don't need to copy the entire file.
If your API uses the same endpoints and streaming format but different
field names, you can override just the sections that differ:

```yaml
# ~/.genai-cli/api_format.yaml
api_format:
  name: "my-corp-v2"

  message_fields:
    role: "SenderRole"
    content: "ResponseText"
    timestamp: "CreatedDate"

  role_values:
    assistant: "AI"
    user: "Human"
```

All other sections (`endpoints`, `request_fields`, `stream`, etc.) will
inherit from the package defaults.

## Verifying Your Config

After creating your custom `api_format.yaml`:

```bash
# Check that the CLI loads your config (shows merged settings)
genai config get default_model

# Test API connectivity
genai auth verify

# Test history display (verifies history_fields mapping)
genai history

# Test usage display (verifies usage_fields mapping)
genai usage

# Test streaming (verifies stream config + content_paths)
genai
> hello
```

If fields show as blank or `None`, the field mapping doesn't match what
the API actually returns. Inspect the raw API response with your browser's
DevTools Network tab and adjust the YAML accordingly.

## Architecture

```
config/api_format.yaml          <-- package defaults (checked into repo)
~/.genai-cli/api_format.yaml    <-- user override (not checked in)
.genai-cli/api_format.yaml      <-- project override (optional)
        |
        v  (3-level deep merge)
   ConfigManager._load()
        |
        v
   ConfigManager.mapper  -->  ResponseMapper(api_format)
        |
        +---> client.py    (endpoints, payloads, parse_message)
        +---> streaming.py (stream format, content extraction)
        +---> cli.py       (map history/usage before display)
```

### Key Source Files

| File | Role |
|------|------|
| `src/genai_cli/mapper.py` | `ResponseMapper` class and `_resolve_path()` utility |
| `src/genai_cli/config.py` | Loads and merges `api_format.yaml`, exposes `mapper` property |
| `src/genai_cli/client.py` | Uses mapper for all API endpoint URLs and request/response translation |
| `src/genai_cli/streaming.py` | Uses mapper for stream format detection and content extraction |
| `config/api_format.yaml` | Default field mappings shipped with the package |
| `tests/test_mapper.py` | 26 tests covering all mapper methods |
