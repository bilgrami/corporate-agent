# Provider Profiles — Test Plan

## 1. Overview

This test plan covers the provider profiles feature across three levels: unit tests, integration tests, and manual verification. All automated tests use `pytest` with `respx` for HTTP mocking (already in `dev` dependencies).

### Test File Layout

```
tests/
  test_profiles.py                  # ProfileManager CRUD
  providers/
    __init__.py
    test_openai_client.py           # OpenAI request/response/streaming
    test_anthropic_client.py        # Anthropic request/response/streaming
    test_gemini_client.py           # Gemini request/response/streaming
    test_corporate_client.py        # CorporateClient wrapper
    test_factory.py                 # Factory routing + error cases
  test_repl_profiles.py            # REPL profile switching integration
  test_cli_profiles.py             # CLI --profile flag + subcommands
```

---

## 2. Unit Tests

### 2.1 ProfileManager CRUD (`test_profiles.py`)

| Test | Description |
|------|-------------|
| `test_list_profiles_empty` | No `profiles.yaml` → returns only the implicit corporate profile |
| `test_list_profiles_with_file` | Reads profiles from YAML, returns correct `Profile` objects |
| `test_get_profile_exists` | `get_profile("openai")` returns the correct profile |
| `test_get_profile_not_found` | `get_profile("nonexistent")` returns `None` |
| `test_get_profile_corporate_implicit` | `get_profile("corporate")` works even without explicit entry in YAML |
| `test_create_profile` | Creates a new profile; YAML file is written with correct structure |
| `test_create_profile_creates_file` | `profiles.yaml` is created if it doesn't exist |
| `test_create_profile_duplicate_name` | Raises error when profile name already exists |
| `test_delete_profile` | Removes profile from YAML file |
| `test_delete_profile_not_found` | Returns `False` when deleting nonexistent profile |
| `test_delete_profile_corporate_blocked` | Cannot delete the implicit corporate profile |
| `test_get_default_profile` | Returns the profile marked as `default_profile` |
| `test_get_default_profile_fallback` | No `default_profile` key → returns corporate |
| `test_set_default_profile` | Updates `default_profile` in YAML |
| `test_set_default_profile_invalid` | Raises error for nonexistent profile name |
| `test_get_provider_defaults` | `get_provider_defaults("openai")` returns correct URL, env var, model |
| `test_check_api_key_present` | Returns `True` when env var is set |
| `test_check_api_key_missing` | Returns `False` when env var is not set |
| `test_check_api_key_corporate` | Returns `True` for corporate (uses bearer token, not env var) |

**Fixtures:**

```python
@pytest.fixture
def profiles_dir(tmp_path):
    """Create a temp ~/.genai-cli/ with profiles.yaml."""
    config_dir = tmp_path / ".genai-cli"
    config_dir.mkdir()
    profiles_yaml = config_dir / "profiles.yaml"
    profiles_yaml.write_text(yaml.dump({
        "default_profile": "corporate",
        "profiles": {
            "corporate": {"provider": "corporate", "default_model": "gpt-5-chat-global"},
            "openai": {
                "provider": "openai",
                "api_base_url": "https://api.openai.com/v1",
                "api_key_env": "OPENAI_API_KEY",
                "default_model": "gpt-4o",
                "models": ["gpt-4o", "gpt-4o-mini"],
            },
        },
    }))
    return config_dir

@pytest.fixture
def profile_mgr(profiles_dir, monkeypatch):
    """ProfileManager pointing at the temp directory."""
    monkeypatch.setattr(ProfileManager, "PROFILES_PATH", profiles_dir / "profiles.yaml")
    return ProfileManager()
```

### 2.2 Factory Routing (`test_factory.py`)

| Test | Description |
|------|-------------|
| `test_factory_corporate` | `provider="corporate"` → returns `CorporateClient` |
| `test_factory_openai` | `provider="openai"` + env var set → returns `OpenAIClient` |
| `test_factory_anthropic` | `provider="anthropic"` + env var set → returns `AnthropicClient` |
| `test_factory_gemini` | `provider="gemini"` + env var set → returns `GeminiClient` |
| `test_factory_missing_key` | `provider="openai"` + no env var → raises `AuthError` with message |
| `test_factory_unknown_provider` | `provider="azure"` → raises `ValueError` |

```python
def test_factory_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    profile = Profile(
        name="openai", provider="openai",
        api_base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
    )
    client = create_provider_client(profile, mock_config, mock_auth)
    assert isinstance(client, OpenAIClient)

def test_factory_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    profile = Profile(name="openai", provider="openai",
                      api_key_env="OPENAI_API_KEY", ...)
    with pytest.raises(AuthError, match="OPENAI_API_KEY"):
        create_provider_client(profile, mock_config, mock_auth)
```

### 2.3 OpenAI Client (`test_openai_client.py`)

| Test | Description |
|------|-------------|
| `test_stream_chat_basic` | Sends correct request, yields text from SSE chunks |
| `test_stream_chat_with_history` | Conversation history is included in `messages` array |
| `test_stream_chat_with_system_prompt` | System prompt is `messages[0]` with `role: system` |
| `test_stream_chat_request_format` | Validates request body: `model`, `messages`, `stream: true` |
| `test_stream_chat_auth_header` | Request has `Authorization: Bearer sk-...` header |
| `test_stream_chat_handles_done` | Stops iteration when `data: [DONE]` is received |
| `test_stream_chat_skips_empty_deltas` | Chunks with empty `content` are not yielded |
| `test_stream_chat_http_error` | 401/429/500 errors raise appropriate exceptions |
| `test_close` | Underlying httpx client is closed |

**Mock setup using `respx`:**

```python
@pytest.fixture
def openai_client():
    return OpenAIClient(
        api_base_url="https://api.openai.com/v1",
        api_key="sk-test-key",
    )

def make_sse_response(chunks: list[str]) -> str:
    """Build a mock SSE response body."""
    lines = []
    for text in chunks:
        chunk = {
            "choices": [{"delta": {"content": text}, "index": 0}]
        }
        lines.append(f"data: {json.dumps(chunk)}")
    lines.append("data: [DONE]")
    return "\n".join(lines)

@respx.mock
def test_stream_chat_basic(openai_client):
    sse_body = make_sse_response(["Hello", " world", "!"])
    respx.post("https://api.openai.com/v1/chat/completions").respond(
        200, text=sse_body, headers={"content-type": "text/event-stream"}
    )
    chunks = list(openai_client.stream_chat("hi", "gpt-4o"))
    assert chunks == ["Hello", " world", "!"]
```

### 2.4 Anthropic Client (`test_anthropic_client.py`)

| Test | Description |
|------|-------------|
| `test_stream_chat_basic` | Sends correct request, yields text from `content_block_delta` events |
| `test_stream_chat_with_history` | History included in `messages` array |
| `test_stream_chat_system_prompt` | System prompt sent as top-level `system` field (not in messages) |
| `test_stream_chat_request_format` | Validates: `model`, `messages`, `max_tokens`, `stream: true` |
| `test_stream_chat_auth_header` | Request has `x-api-key` header (not Bearer) |
| `test_stream_chat_anthropic_version` | Request has `anthropic-version: 2023-06-01` header |
| `test_stream_chat_handles_message_stop` | Stops at `message_stop` event type |
| `test_stream_chat_ignores_non_delta_events` | `message_start`, `content_block_start` events are skipped |
| `test_stream_chat_http_error` | 401/429/500 errors raise appropriate exceptions |

**Mock SSE helper:**

```python
def make_anthropic_sse(chunks: list[str]) -> str:
    lines = []
    lines.append('event: message_start')
    lines.append(f'data: {json.dumps({"type": "message_start"})}')
    lines.append('event: content_block_start')
    lines.append(f'data: {json.dumps({"type": "content_block_start"})}')
    for text in chunks:
        event = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": text},
        }
        lines.append('event: content_block_delta')
        lines.append(f'data: {json.dumps(event)}')
    lines.append('event: message_stop')
    lines.append(f'data: {json.dumps({"type": "message_stop"})}')
    return "\n".join(lines)
```

### 2.5 Gemini Client (`test_gemini_client.py`)

| Test | Description |
|------|-------------|
| `test_stream_chat_basic` | Sends correct request, yields text from `candidates[0].content.parts` |
| `test_stream_chat_with_history` | History uses `user`/`model` role names (not `assistant`) |
| `test_stream_chat_system_instruction` | System prompt sent as `system_instruction.parts[0].text` |
| `test_stream_chat_request_format` | URL includes model name and `?alt=sse&key=...` |
| `test_stream_chat_api_key_in_query` | API key is in query string, not headers |
| `test_stream_chat_content_format` | Each message has `parts: [{text: "..."}]` structure |
| `test_stream_chat_http_error` | 401/429/500 errors raise appropriate exceptions |
| `test_stream_chat_multiple_parts` | Multiple parts in a single candidate are all yielded |

**Mock SSE helper:**

```python
def make_gemini_sse(chunks: list[str]) -> str:
    lines = []
    for text in chunks:
        chunk = {
            "candidates": [{
                "content": {"parts": [{"text": text}], "role": "model"},
            }]
        }
        lines.append(f"data: {json.dumps(chunk)}")
    return "\n".join(lines)
```

### 2.6 CorporateClient Wrapper (`test_corporate_client.py`)

| Test | Description |
|------|-------------|
| `test_wraps_genai_client` | `CorporateClient.stream_chat()` delegates to `GenAIClient.stream_chat()` |
| `test_ignores_conversation_history` | The `conversation_history` parameter is not passed to `GenAIClient` |
| `test_close_delegates` | `close()` calls `GenAIClient.close()` |
| `test_existing_session_flow` | Session creation and streaming work through the wrapper |

---

## 3. Integration Tests

### 3.1 REPL Profile Switching (`test_repl_profiles.py`)

| Test | Description |
|------|-------------|
| `test_profile_command_show` | `/profile` with no args shows active profile info |
| `test_profile_command_switch` | `/profile openai` switches the active provider client |
| `test_profile_switch_clears_history` | After `/profile openai`, conversation history is empty |
| `test_profiles_command_lists_all` | `/profiles` lists all profiles with active indicator |
| `test_profile_switch_and_message` | After switching, next message uses the new provider's API |
| `test_profile_tab_completion` | Tab completion for `/profile` suggests available profile names |
| `test_model_command_after_switch` | `/models` shows models for the active profile |
| `test_model_switch_within_profile` | `/model gpt-4o-mini` works within the openai profile |
| `test_clear_after_profile_switch` | `/clear` resets both session and conversation history |
| `test_status_shows_profile` | `/status` includes active profile name |

**Test strategy**: Use `monkeypatch` to inject a mock `ProfileManager` and `respx` to mock the HTTP calls. Simulate user input sequences and verify display output.

```python
def test_profile_command_switch(repl_session, mock_profiles):
    """Switching profile instantiates the correct client."""
    repl_session._handle_command("/profile openai")
    assert repl_session._active_profile.name == "openai"
    assert isinstance(repl_session._provider_client, OpenAIClient)
```

### 3.2 CLI Profile Flag (`test_cli_profiles.py`)

| Test | Description |
|------|-------------|
| `test_profile_flag_sets_context` | `--profile openai` stores profile name in Click context |
| `test_ask_with_profile` | `genai --profile openai ask "hello"` routes to OpenAI API |
| `test_ask_without_profile` | `genai ask "hello"` uses corporate API (backward compat) |
| `test_profile_and_model_flags` | `--profile openai --model gpt-4o-mini` uses profile but overrides model |
| `test_profile_list_subcommand` | `genai profile list` outputs all profiles |
| `test_profile_use_subcommand` | `genai profile use openai` updates default in profiles.yaml |
| `test_profile_setup_subcommand` | `genai profile setup openai` creates profile with defaults |
| `test_profile_delete_subcommand` | `genai profile delete openai` removes profile |
| `test_invalid_profile_flag` | `--profile nonexistent` exits with error message |

**Test strategy**: Use Click's `CliRunner` to invoke commands, `respx` for HTTP mocking, and `tmp_path` for isolated config files.

```python
from click.testing import CliRunner

def test_ask_with_profile(tmp_path, monkeypatch):
    """--profile flag routes to the correct provider."""
    # Set up profiles.yaml in tmp dir
    setup_profiles(tmp_path, ...)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    runner = CliRunner()
    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").respond(
            200, text=make_sse_response(["Hello!"]),
        )
        result = runner.invoke(main, ["--profile", "openai", "ask", "hi"])
        assert result.exit_code == 0
        assert "Hello!" in result.output
```

### 3.3 Config Precedence with Profiles

| Test | Description |
|------|-------------|
| `test_default_model_from_profile` | Profile's `default_model` is used when no `--model` flag |
| `test_model_flag_overrides_profile` | `--model gpt-4o-mini --profile openai` uses `gpt-4o-mini` |
| `test_env_var_does_not_override_profile_model` | `GENAI_MODEL` env var does not override profile's model choice |
| `test_no_profile_uses_settings_yaml` | Without `--profile`, model comes from `settings.yaml` as before |

---

## 4. Edge Cases

### 4.1 Missing API Key

| Test | Description |
|------|-------------|
| `test_switch_to_profile_missing_key_repl` | `/profile openai` when `OPENAI_API_KEY` is unset → error shown, stays on current profile |
| `test_cli_profile_missing_key` | `--profile openai` when key is unset → error + nonzero exit |
| `test_profile_list_shows_missing_key_status` | `genai profile list` shows "missing key" for unconfigured profiles |

### 4.2 Invalid Profile

| Test | Description |
|------|-------------|
| `test_switch_to_nonexistent_profile` | `/profile foo` → "Profile not found" error |
| `test_cli_nonexistent_profile` | `--profile foo` → error listing available profiles |
| `test_profile_yaml_malformed` | Corrupted YAML → falls back to corporate-only |
| `test_profile_missing_required_fields` | Profile without `provider` field → error during load |

### 4.3 Switching Mid-Conversation

| Test | Description |
|------|-------------|
| `test_switch_clears_conversation_history` | After 3 messages on corporate, switch to openai → history is empty |
| `test_switch_back_restores_nothing` | Switch corporate→openai→corporate → history is not restored |
| `test_session_save_includes_profile` | `/quit` after profile switch saves the active profile name |
| `test_resume_restores_profile` | `/resume <id>` restores the profile that was active when saved |

### 4.4 Corporate Default Behavior

| Test | Description |
|------|-------------|
| `test_no_profiles_yaml_is_ok` | CLI works normally when `~/.genai-cli/profiles.yaml` doesn't exist |
| `test_empty_profiles_yaml_is_ok` | Empty file → implicit corporate profile works |
| `test_existing_auth_flow_unchanged` | `genai auth login` and bearer token flow are unaffected |
| `test_corporate_session_management_unchanged` | Session creation, document upload, history all work as before |

### 4.5 Provider-Specific Edge Cases

| Test | Description |
|------|-------------|
| `test_anthropic_max_tokens_required` | Anthropic requests always include `max_tokens` |
| `test_gemini_role_mapping` | Gemini uses `model` not `assistant` for AI messages |
| `test_gemini_api_key_in_url` | API key is in query string, not leaked to headers |
| `test_openai_system_message_first` | System prompt is always the first message |
| `test_long_conversation_history` | Large history (100+ messages) is sent correctly |

---

## 5. Test Fixtures and Mocking Strategy

### 5.1 HTTP Mocking with `respx`

All provider client tests use `respx` (already in `dev` dependencies) to mock HTTP requests. This ensures:
- No real API calls are made during tests
- Response formats can be precisely controlled
- Error scenarios can be simulated

```python
import respx

@pytest.fixture
def mock_openai_api():
    """Mock the OpenAI chat completions endpoint."""
    with respx.mock(assert_all_called=False) as mock:
        yield mock

def test_stream_chat(mock_openai_api, openai_client):
    mock_openai_api.post(
        "https://api.openai.com/v1/chat/completions"
    ).respond(200, text=make_sse_response(["Hello"]))
    chunks = list(openai_client.stream_chat("hi", "gpt-4o"))
    assert chunks == ["Hello"]
```

### 5.2 Config and Profile Fixtures

```python
@pytest.fixture
def mock_config(tmp_path):
    """ConfigManager with temp config directory."""
    settings = tmp_path / "config" / "settings.yaml"
    settings.parent.mkdir(parents=True)
    settings.write_text(yaml.dump({"default_model": "gpt-5-chat-global"}))
    return ConfigManager(config_path=str(settings))

@pytest.fixture
def sample_profiles():
    """Sample profiles for testing."""
    return {
        "corporate": Profile(
            name="corporate", provider="corporate",
            default_model="gpt-5-chat-global",
        ),
        "openai": Profile(
            name="openai", provider="openai",
            api_base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            default_model="gpt-4o",
            models=["gpt-4o", "gpt-4o-mini"],
        ),
        "anthropic": Profile(
            name="anthropic", provider="anthropic",
            api_base_url="https://api.anthropic.com",
            api_key_env="ANTHROPIC_API_KEY",
            default_model="claude-sonnet-4-5-20250514",
            models=["claude-sonnet-4-5-20250514", "claude-opus-4-20250514"],
        ),
        "gemini": Profile(
            name="gemini", provider="gemini",
            api_base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key_env="GEMINI_API_KEY",
            default_model="gemini-2.5-flash",
            models=["gemini-2.5-pro", "gemini-2.5-flash"],
        ),
    }
```

### 5.3 SSE Response Helpers

Shared helper functions for building mock SSE responses:

```python
# tests/conftest.py or tests/helpers.py

def make_openai_sse(chunks: list[str], include_done: bool = True) -> str:
    """Build a mock OpenAI SSE response body."""
    lines = []
    for i, text in enumerate(chunks):
        chunk = {
            "id": f"chatcmpl-{i}",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"content": text}}],
        }
        lines.append(f"data: {json.dumps(chunk)}")
        lines.append("")  # blank line between SSE events
    if include_done:
        lines.append("data: [DONE]")
        lines.append("")
    return "\n".join(lines)

def make_anthropic_sse(chunks: list[str]) -> str:
    """Build a mock Anthropic SSE response body."""
    lines = [
        'event: message_start',
        f'data: {json.dumps({"type": "message_start", "message": {"id": "msg_test"}})}',
        '',
        'event: content_block_start',
        f'data: {json.dumps({"type": "content_block_start", "index": 0})}',
        '',
    ]
    for text in chunks:
        event = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": text},
        }
        lines.append('event: content_block_delta')
        lines.append(f'data: {json.dumps(event)}')
        lines.append('')
    lines.append('event: message_stop')
    lines.append(f'data: {json.dumps({"type": "message_stop"})}')
    lines.append('')
    return "\n".join(lines)

def make_gemini_sse(chunks: list[str]) -> str:
    """Build a mock Gemini SSE response body."""
    lines = []
    for text in chunks:
        chunk = {
            "candidates": [{
                "content": {"parts": [{"text": text}], "role": "model"},
                "finishReason": "STOP" if text == chunks[-1] else None,
            }]
        }
        lines.append(f"data: {json.dumps(chunk)}")
        lines.append("")
    return "\n".join(lines)
```

### 5.4 Environment Variable Management

All tests that depend on API keys use `monkeypatch` to control environment variables:

```python
def test_with_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
    ...

def test_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ...
```

---

## 6. Manual Verification Checklist

### Setup

- [ ] Install genai-cli in a fresh environment
- [ ] Verify `genai --version` works
- [ ] Verify existing corporate login flow: `genai auth login` → `genai ask "hello"`

### Profile Management

- [ ] `genai profile list` — shows only corporate profile (no profiles.yaml yet)
- [ ] `genai profile setup openai` — creates `~/.genai-cli/profiles.yaml` with correct defaults
- [ ] `genai profile setup anthropic` — adds anthropic profile to existing file
- [ ] `genai profile setup gemini` — adds gemini profile
- [ ] `genai profile list` — shows all 4 profiles with correct status
- [ ] `genai profile create` — interactive wizard creates a custom profile
- [ ] `genai profile use openai` — sets default to openai
- [ ] `genai profile delete <custom-profile>` — removes profile after confirmation
- [ ] Verify `~/.genai-cli/profiles.yaml` contains no API keys (only env var names)

### CLI Flag

- [ ] `genai ask "hello"` — uses corporate API (default)
- [ ] `genai --profile openai ask "hello"` — uses OpenAI API directly
- [ ] `genai --profile anthropic ask "hello"` — uses Anthropic API directly
- [ ] `genai --profile gemini ask "hello"` — uses Gemini API directly
- [ ] `genai --profile openai --model gpt-4o-mini ask "hello"` — profile + model override
- [ ] `genai --profile nonexistent ask "hello"` — shows error with available profiles

### REPL

- [ ] Launch REPL: `genai` → `/profiles` — shows all profiles
- [ ] `/profile` — shows active profile info
- [ ] `/profile openai` — switches to openai, shows confirmation
- [ ] Send a message — response comes from OpenAI API
- [ ] `/profile anthropic` — switches to anthropic
- [ ] Send a message — response comes from Anthropic API
- [ ] `/profile corporate` — switches back to corporate
- [ ] Send a message — response comes from corporate gateway
- [ ] `/profile <TAB>` — tab completion shows available profiles
- [ ] `/models` — shows models for the active profile
- [ ] `/model gpt-4o-mini` — switches model within the active profile

### Streaming

- [ ] OpenAI streaming: response appears incrementally (word by word)
- [ ] Anthropic streaming: response appears incrementally
- [ ] Gemini streaming: response appears incrementally
- [ ] Corporate streaming: unchanged from current behavior

### Error Handling

- [ ] Unset `OPENAI_API_KEY` → `/profile openai` → clear error message
- [ ] Set invalid API key → send message → clear auth error from provider
- [ ] Disconnect network → send message → connection error with provider name

### Backward Compatibility

- [ ] Delete `~/.genai-cli/profiles.yaml` → CLI works exactly as before
- [ ] Existing `settings.yaml` and `auth` token are not modified
- [ ] All existing slash commands work: `/help`, `/model`, `/clear`, `/history`, `/usage`, etc.
- [ ] `--session-id` flag still works with corporate profile
- [ ] File upload (`/files`) still works with corporate profile
