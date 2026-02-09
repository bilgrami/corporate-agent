# Provider Profiles — Technical Design Document

## 1. Architecture Overview

The provider profiles feature introduces a **provider abstraction layer** between the CLI/REPL and HTTP transport. Today, all requests flow through `GenAIClient` which is tightly coupled to the corporate API's session-based flow. The new design introduces:

1. **`BaseProviderClient`** — Abstract base class defining the chat interface.
2. **Provider-specific clients** — `CorporateClient`, `OpenAIClient`, `AnthropicClient`, `GeminiClient`.
3. **`ProfileManager`** — CRUD for profile configs stored in `~/.genai-cli/profiles.yaml`.
4. **`create_provider_client()` factory** — Instantiates the correct client based on the active profile.

```
┌─────────────────────────────────────────────────────┐
│                   CLI / REPL                         │
│  (cli.py, repl.py)                                  │
│  --profile flag, /profile command                   │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│              ProfileManager                          │
│  profiles.yaml ←→ Profile dataclass                 │
│  load / save / list / create / delete / set_default │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│         create_provider_client(profile)              │
│  Factory: provider name → client class              │
└─────┬──────────┬──────────┬──────────┬──────────────┘
      │          │          │          │
      ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌──────────┐ ┌────────┐
│Corporate │ │ OpenAI │ │Anthropic │ │ Gemini │
│  Client  │ │ Client │ │  Client  │ │ Client │
│(existing)│ │  (new) │ │   (new)  │ │  (new) │
└──────────┘ └────────┘ └──────────┘ └────────┘
      │          │          │          │
      ▼          ▼          ▼          ▼
   Corporate   OpenAI    Anthropic  Google
   Gateway     API       API        Gemini API
```

## 2. Profile YAML Schema

### File Location

`~/.genai-cli/profiles.yaml`

### Schema

```yaml
# Default profile used when no --profile flag is given
default_profile: corporate

profiles:
  corporate:
    provider: corporate
    # No api_base_url or api_key_env — uses existing settings.yaml + auth token
    default_model: gpt-5-chat-global

  openai:
    provider: openai
    api_base_url: https://api.openai.com/v1
    api_key_env: OPENAI_API_KEY
    default_model: gpt-4o
    models:
      - gpt-4o
      - gpt-4o-mini
      - gpt-4.1
      - gpt-4.1-mini
      - o3
      - o4-mini

  anthropic:
    provider: anthropic
    api_base_url: https://api.anthropic.com
    api_key_env: ANTHROPIC_API_KEY
    default_model: claude-sonnet-4-5-20250514
    models:
      - claude-sonnet-4-5-20250514
      - claude-opus-4-20250514
      - claude-haiku-3-5-20241022

  gemini:
    provider: gemini
    api_base_url: https://generativelanguage.googleapis.com/v1beta
    api_key_env: GEMINI_API_KEY
    default_model: gemini-2.5-flash
    models:
      - gemini-2.5-pro
      - gemini-2.5-flash
      - gemini-2.0-flash
```

### Implicit Corporate Profile

If `profiles.yaml` does not exist or has no `corporate` entry, the system synthesizes one from the existing `settings.yaml` and `AuthManager` configuration. This ensures backward compatibility.

## 3. Data Model

### New Dataclasses (`src/genai_cli/models.py`)

```python
@dataclass
class Profile:
    """A provider profile configuration."""
    name: str
    provider: str                     # corporate | openai | anthropic | gemini
    api_base_url: str = ""
    api_key_env: str = ""             # env var name, NOT the key itself
    default_model: str = ""
    models: list[str] = field(default_factory=list)
```

## 4. Provider Client Design

### 4.1 Abstract Base Class

```python
# src/genai_cli/providers/base.py

from abc import ABC, abstractmethod
from typing import Any, Iterator
from genai_cli.models import ChatMessage

class BaseProviderClient(ABC):
    """Abstract interface for all provider clients."""

    @abstractmethod
    def stream_chat(
        self,
        message: str,
        model: str,
        session_id: str | None = None,
        conversation_history: list[ChatMessage] | None = None,
        system_prompt: str = "",
    ) -> Iterator[str]:
        """Stream a chat response, yielding text chunks."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close underlying HTTP connections."""
        ...
```

Key design decisions:
- **`conversation_history` parameter**: Direct API providers (OpenAI, Anthropic, Gemini) are stateless — they don't store conversation history server-side. The full conversation history must be sent with each request.
- **`system_prompt` parameter**: Each provider formats system prompts differently.
- **Returns `Iterator[str]`**: Simplifies the streaming interface — callers just iterate over text chunks.
- **No `create_chat()` or `ensure_session()`**: Session management is corporate-specific and stays in `CorporateClient`.

### 4.2 Corporate Client (Wrapper)

Wraps the existing `GenAIClient` to conform to `BaseProviderClient`:

```python
# src/genai_cli/providers/corporate.py

class CorporateClient(BaseProviderClient):
    """Wraps existing GenAIClient for the corporate gateway."""

    def __init__(self, config: ConfigManager, auth: AuthManager):
        self._inner = GenAIClient(config, auth)
        self._config = config

    def stream_chat(self, message, model, session_id=None,
                    conversation_history=None, system_prompt=""):
        # Corporate API manages history server-side,
        # so conversation_history is ignored.
        resp = self._inner.stream_chat(message, model, session_id)
        handler = StreamHandler(self._config)
        yield from handler.iter_stream_content(resp)

    def close(self):
        self._inner.close()
```

The existing `GenAIClient` is **not modified** — `CorporateClient` wraps it, preserving all existing behavior (session creation, document upload, etc.).

### 4.3 OpenAI Client

```python
# src/genai_cli/providers/openai.py

class OpenAIClient(BaseProviderClient):
    """Direct OpenAI API client using httpx."""

    def __init__(self, api_base_url: str, api_key: str):
        self._client = httpx.Client(
            base_url=api_base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    def stream_chat(self, message, model, session_id=None,
                    conversation_history=None, system_prompt=""):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        # POST /chat/completions with stream=true
        with self._client.stream(
            "POST",
            "/chat/completions",
            json={"model": model, "messages": messages, "stream": True},
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    return
                chunk = json.loads(payload)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                text = delta.get("content", "")
                if text:
                    yield text

    def close(self):
        self._client.close()
```

**API format**: `POST /v1/chat/completions` with `stream: true`. SSE format, `data: {...}` lines, `data: [DONE]` terminator. Response delta in `choices[0].delta.content`.

### 4.4 Anthropic Client

```python
# src/genai_cli/providers/anthropic.py

class AnthropicClient(BaseProviderClient):
    """Direct Anthropic Messages API client using httpx."""

    def __init__(self, api_base_url: str, api_key: str):
        self._client = httpx.Client(
            base_url=api_base_url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    def stream_chat(self, message, model, session_id=None,
                    conversation_history=None, system_prompt=""):
        messages = []
        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 8192,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        # POST /v1/messages with stream=true
        with self._client.stream("POST", "/v1/messages", json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload_str = line[6:]
                event = json.loads(payload_str)
                if event.get("type") == "content_block_delta":
                    text = event.get("delta", {}).get("text", "")
                    if text:
                        yield text
                elif event.get("type") == "message_stop":
                    return

    def close(self):
        self._client.close()
```

**API format**: `POST /v1/messages` with `stream: true`. SSE format. System prompt is a top-level `system` field (not in `messages` array). Content arrives in `content_block_delta` events with `delta.text`. Auth via `x-api-key` header (not Bearer).

### 4.5 Gemini Client

```python
# src/genai_cli/providers/gemini.py

class GeminiClient(BaseProviderClient):
    """Direct Google Gemini API client using httpx."""

    def __init__(self, api_base_url: str, api_key: str):
        self._base_url = api_base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.Client(
            headers={"Content-Type": "application/json"},
            timeout=120.0,
        )

    def stream_chat(self, message, model, session_id=None,
                    conversation_history=None, system_prompt=""):
        contents = []
        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg.role == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}],
                })
        contents.append({
            "role": "user",
            "parts": [{"text": message}],
        })

        payload: dict = {"contents": contents}
        if system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }

        # POST models/{model}:streamGenerateContent?alt=sse&key={key}
        url = (
            f"{self._base_url}/models/{model}:streamGenerateContent"
            f"?alt=sse&key={self._api_key}"
        )

        with self._client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                chunk = json.loads(line[6:])
                candidates = chunk.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        text = part.get("text", "")
                        if text:
                            yield text

    def close(self):
        self._client.close()
```

**API format**: `POST /v1beta/models/{model}:streamGenerateContent?alt=sse&key={key}`. API key in query string (not header). Roles are `user`/`model` (not `user`/`assistant`). System prompt is a top-level `system_instruction` field.

### 4.6 API Format Comparison

| Aspect | Corporate | OpenAI | Anthropic | Gemini |
|--------|-----------|--------|-----------|--------|
| Auth | Bearer token (header) | Bearer token (header) | `x-api-key` header | API key in query string |
| Endpoint | Custom corporate paths | `/v1/chat/completions` | `/v1/messages` | `/v1beta/models/{model}:streamGenerateContent` |
| System prompt | Part of corporate flow | `messages[0].role=system` | Top-level `system` field | Top-level `system_instruction` |
| Stream format | SSE (configurable) | SSE `data: {...}` | SSE `data: {...}` | SSE `data: {...}` |
| Stream content path | `token` or `Message` | `choices[0].delta.content` | `delta.text` (in `content_block_delta`) | `candidates[0].content.parts[0].text` |
| Stream terminator | `[DONE]` | `data: [DONE]` | `message_stop` event | End of stream |
| Conversation state | Server-side (session_id) | Stateless (send full history) | Stateless (send full history) | Stateless (send full history) |
| Role names | Custom (via mapper) | `system`, `user`, `assistant` | `user`, `assistant` | `user`, `model` |

## 5. ProfileManager

```python
# src/genai_cli/profiles.py

class ProfileManager:
    """Manages provider profiles stored in ~/.genai-cli/profiles.yaml."""

    PROFILES_PATH = Path.home() / ".genai-cli" / "profiles.yaml"

    PROVIDER_DEFAULTS = {
        "openai": {
            "api_base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "default_model": "gpt-4o",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"],
        },
        "anthropic": {
            "api_base_url": "https://api.anthropic.com",
            "api_key_env": "ANTHROPIC_API_KEY",
            "default_model": "claude-sonnet-4-5-20250514",
            "models": ["claude-sonnet-4-5-20250514", "claude-opus-4-20250514",
                       "claude-haiku-3-5-20241022"],
        },
        "gemini": {
            "api_base_url": "https://generativelanguage.googleapis.com/v1beta",
            "api_key_env": "GEMINI_API_KEY",
            "default_model": "gemini-2.5-flash",
            "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
        },
    }

    def list_profiles(self) -> list[Profile]: ...
    def get_profile(self, name: str) -> Profile | None: ...
    def create_profile(self, profile: Profile) -> None: ...
    def delete_profile(self, name: str) -> bool: ...
    def get_default_profile(self) -> Profile: ...
    def set_default_profile(self, name: str) -> None: ...
    def get_provider_defaults(self, provider: str) -> dict: ...
    def check_api_key(self, profile: Profile) -> bool: ...
```

### Key behaviors:
- **`get_default_profile()`** returns the profile marked as `default_profile` in YAML, falling back to the implicit corporate profile.
- **`check_api_key(profile)`** checks whether the env var in `api_key_env` is set (non-empty). Returns `True` for corporate profiles (which use bearer tokens instead).
- **`create_profile()`** writes to `profiles.yaml`, creating the file if it doesn't exist.
- The implicit corporate profile is always available, even without `profiles.yaml`.

## 6. Factory Function

```python
# src/genai_cli/providers/factory.py

def create_provider_client(
    profile: Profile,
    config: ConfigManager,
    auth: AuthManager,
) -> BaseProviderClient:
    """Create the appropriate provider client for a profile."""
    if profile.provider == "corporate":
        return CorporateClient(config, auth)

    # Resolve API key from environment
    api_key = os.environ.get(profile.api_key_env, "")
    if not api_key:
        raise AuthError(
            f"API key not found. Set the {profile.api_key_env} environment variable."
        )

    clients = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "gemini": GeminiClient,
    }
    client_cls = clients.get(profile.provider)
    if client_cls is None:
        raise ValueError(f"Unknown provider: {profile.provider}")

    return client_cls(api_base_url=profile.api_base_url, api_key=api_key)
```

## 7. Integration Points

### 7.1 ConfigManager (`config.py`)

Minimal changes:

- Add `active_profile` property that returns the profile name from CLI overrides or the default.
- The `ProfileManager` is instantiated lazily (only when profiles are actually used).
- Model registry (`config/models.yaml`) remains the source of truth for corporate models. Direct API profiles define their own model lists in `profiles.yaml`.

### 7.2 CLI (`cli.py`)

Changes to the `main` group:

```python
@click.group(invoke_without_command=True)
@click.option("--profile", "-p", default=None, help="Provider profile to use")
@click.option("--model", "-m", default=None, help="Override model")
# ... existing options ...
def main(ctx, profile, model, ...):
    # Store profile name in context for subcommands
    ctx.obj["profile_name"] = profile
    ...
```

New `profile` subcommand group:

```python
@main.group("profile")
def profile_cmd():
    """Manage provider profiles."""

@profile_cmd.command("list")
@profile_cmd.command("use")
@profile_cmd.command("create")
@profile_cmd.command("setup")
@profile_cmd.command("delete")
```

### 7.3 REPL (`repl.py`)

Changes to `ReplSession`:

```python
class ReplSession:
    def __init__(self, config, display, session_id=None, profile_name=None):
        self._profile_mgr = ProfileManager()
        self._active_profile = self._resolve_profile(profile_name)
        self._provider_client = create_provider_client(
            self._active_profile, config, self._auth
        )
        self._conversation_history: list[ChatMessage] = []
        ...
```

New slash command handlers:

```python
def _handle_profile(self, arg: str) -> None:
    """Show or switch profile."""
    if not arg:
        # Show active profile info
        ...
    else:
        # Switch to named profile
        profile = self._profile_mgr.get_profile(arg)
        if profile is None:
            self._display.print_error(f"Profile not found: {arg}")
            return
        self._active_profile = profile
        self._provider_client = create_provider_client(profile, ...)
        self._conversation_history.clear()
        ...

def _handle_profiles(self) -> None:
    """List all profiles."""
    ...
```

### 7.4 Streaming (`streaming.py`)

The `stream_or_complete()` function needs a provider-aware path:

```python
def stream_or_complete(
    client: BaseProviderClient,    # Changed from Any
    message: str,
    model: str,
    session_id: str | None,
    config: ConfigManager,
    use_streaming: bool = True,
    conversation_history: list[ChatMessage] | None = None,
    system_prompt: str = "",
) -> tuple[str, ChatMessage | None]:
    """Send a message and return (full_text, chat_message)."""
    if isinstance(client, CorporateClient):
        # Existing corporate flow (unchanged)
        ...
    else:
        # Direct API flow — client.stream_chat() returns Iterator[str]
        text_parts = list(client.stream_chat(
            message, model, session_id,
            conversation_history, system_prompt,
        ))
        full_text = "".join(text_parts)
        chat_msg = ChatMessage(
            session_id=session_id or "",
            role="assistant",
            content=full_text,
        )
        return full_text, chat_msg
```

### 7.5 Agent Loop

The agent loop (`agent.py`) passes messages to `stream_or_complete()`. The same `conversation_history` parameter flows through, allowing multi-turn agent interactions with direct API providers.

## 8. Conversation History Handling

### Corporate API (Server-Side State)

The corporate API maintains conversation history server-side, keyed by `session_id`. The client sends only the new message; the server appends it to the session and returns the response in context.

**No change needed.** `CorporateClient.stream_chat()` ignores the `conversation_history` parameter.

### Direct APIs (Stateless)

OpenAI, Anthropic, and Gemini APIs are stateless — each request must include the full conversation history.

**Client-side history management:**

```python
class ReplSession:
    _conversation_history: list[ChatMessage]

    def _send_message(self, text):
        ...
        if isinstance(self._provider_client, CorporateClient):
            # Corporate: server manages history
            full_text, chat_msg = stream_or_complete(
                self._provider_client, text, model, session_id, config, ...
            )
        else:
            # Direct API: send full history
            full_text, chat_msg = stream_or_complete(
                self._provider_client, text, model, session_id, config,
                conversation_history=self._conversation_history,
                system_prompt=self._config.get_system_prompt(),
            )
            # Append both user and assistant messages to history
            self._conversation_history.append(
                ChatMessage(session_id="", role="user", content=text)
            )
            self._conversation_history.append(
                ChatMessage(session_id="", role="assistant", content=full_text)
            )
```

When the user switches profiles (`/profile <name>`), `_conversation_history` is cleared — conversation context does not transfer between providers.

When `/clear` is called, `_conversation_history` is also cleared.

The `/rewind` command removes entries from both the session messages and `_conversation_history`.

## 9. File Layout

### New Files

```
src/genai_cli/
  providers/
    __init__.py
    base.py              # BaseProviderClient ABC
    corporate.py         # CorporateClient (wraps existing GenAIClient)
    openai.py            # OpenAIClient
    anthropic.py         # AnthropicClient
    gemini.py            # GeminiClient
    factory.py           # create_provider_client()
  profiles.py            # ProfileManager + Profile dataclass

tests/
  providers/
    __init__.py
    test_openai_client.py
    test_anthropic_client.py
    test_gemini_client.py
    test_corporate_client.py
    test_factory.py
  test_profiles.py
```

### Modified Files

```
src/genai_cli/
  models.py              # Add Profile dataclass
  cli.py                 # Add --profile flag, profile subcommand group
  repl.py                # Add /profile, /profiles commands; conversation history
  streaming.py           # Add conversation_history param to stream_or_complete
  config.py              # Add active_profile property (optional)
```

### Unchanged Files

```
src/genai_cli/
  client.py              # GenAIClient stays as-is (wrapped by CorporateClient)
  mapper.py              # ResponseMapper stays as-is (corporate-only)
  auth.py                # AuthManager stays as-is (corporate-only)
  display.py             # Minor additions for profile display
config/
  models.yaml            # Corporate model registry stays as-is
  settings.yaml          # No changes
  api_format.yaml        # No changes
```

## 10. Data Flow Diagrams

### 10.1 Profile Switching (REPL)

```
User types: /profile openai
       │
       ▼
ReplSession._handle_profile("openai")
       │
       ├─► ProfileManager.get_profile("openai")
       │         │
       │         ▼
       │   Read ~/.genai-cli/profiles.yaml
       │         │
       │         ▼
       │   Return Profile(provider="openai", api_key_env="OPENAI_API_KEY", ...)
       │
       ├─► create_provider_client(profile, config, auth)
       │         │
       │         ├─► os.environ.get("OPENAI_API_KEY")
       │         │
       │         ▼
       │   Return OpenAIClient(base_url, api_key)
       │
       ├─► self._provider_client = new_client
       ├─► self._conversation_history.clear()
       └─► Display: "Switched to profile: openai (gpt-4o)"
```

### 10.2 Chat Message Flow (Direct API)

```
User types: "explain closures"
       │
       ▼
ReplSession._send_message("explain closures")
       │
       ├─► Build conversation_history = [prev_user, prev_assistant, ...]
       │
       ├─► stream_or_complete(provider_client, "explain closures", model,
       │       session_id, config, conversation_history, system_prompt)
       │         │
       │         ▼
       │   provider_client.stream_chat(...)
       │         │
       │         ├─► Build messages array: [system, ...history, user_msg]
       │         ├─► POST https://api.openai.com/v1/chat/completions
       │         │   {"model": "gpt-4o", "messages": [...], "stream": true}
       │         │
       │         ▼
       │   ◄── SSE stream: data: {"choices":[{"delta":{"content":"A closure..."}}]}
       │         │
       │         ▼
       │   Yield "A closure..."  (text chunks via Iterator[str])
       │
       ├─► full_text = "".join(chunks)
       ├─► Append user msg to _conversation_history
       ├─► Append assistant msg to _conversation_history
       └─► Display response
```

### 10.3 Chat Message Flow (Corporate API — Unchanged)

```
User types: "explain closures"
       │
       ▼
ReplSession._send_message("explain closures")
       │
       ├─► CorporateClient.stream_chat("explain closures", model, session_id)
       │         │
       │         ├─► GenAIClient.ensure_session(session_id)
       │         ├─► GenAIClient.stream_chat("explain closures", model, session_id)
       │         │     │
       │         │     ├─► POST corporate_api/stream/{session_id}
       │         │     │   (message + model only; history is server-side)
       │         │     │
       │         │     ▼
       │         │   SSE stream via ResponseMapper
       │         │
       │         ▼
       │   Yield text chunks via StreamHandler
       │
       ├─► full_text, chat_msg (with tokens/cost from final chunk)
       └─► Display response + token usage
```

## 11. Migration & Backward Compatibility

### Zero-Migration Path

- If `~/.genai-cli/profiles.yaml` does not exist, the CLI behaves exactly as today.
- The implicit `corporate` profile is synthesized at runtime from `settings.yaml` + `AuthManager`.
- No existing config files are modified during installation or upgrade.

### Graceful Feature Discovery

- Running `genai profile list` when no profiles exist shows only the implicit corporate profile with a hint:
  ```
  Name          Provider    Model               Status
  corporate*    corporate   gpt-5-chat-global   active

  Tip: Run 'genai profile setup openai' to add a provider profile.
  ```

### Config Precedence with Profiles

The existing 5-level config precedence is extended:

```
1. CLI --profile flag           (new, highest)
2. CLI --model flag             (existing)
3. Profile's default_model      (new)
4. Environment variables        (existing)
5. Project config               (existing)
6. User config                  (existing)
7. Package defaults             (existing, lowest)
```

The `--model` flag always wins over the profile's `default_model`. The `--profile` flag selects the profile, but `--model` can still override the model within that profile.

## 12. Error Handling

| Scenario | Error Message |
|----------|--------------|
| Missing API key | `API key not found. Set the OPENAI_API_KEY environment variable.` |
| Unknown profile | `Profile not found: 'foo'. Available: corporate, openai, anthropic` |
| Unknown provider | `Unknown provider: 'azure'. Supported: corporate, openai, anthropic, gemini` |
| API auth failure (OpenAI) | `OpenAI API error (401): Invalid API key. Check your OPENAI_API_KEY.` |
| API auth failure (Anthropic) | `Anthropic API error (401): Invalid API key. Check your ANTHROPIC_API_KEY.` |
| Rate limit | `OpenAI API error (429): Rate limit exceeded. Try again in a few seconds.` |
| Network error | `Could not connect to api.openai.com. Check your internet connection.` |
