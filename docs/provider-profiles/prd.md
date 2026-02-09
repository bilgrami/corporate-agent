# Provider Profiles — Product Requirements Document

## 1. Problem Statement

The `genai-cli` tool currently works exclusively through a corporate AI gateway API. All models (OpenAI, Anthropic, Google) are accessed via a single corporate endpoint that requires a corporate bearer token obtained through browser DevTools.

Users want the ability to:

1. **Use their own API keys** to call providers directly (OpenAI, Anthropic, Google Gemini) — bypassing the corporate gateway for personal projects, after-hours work, or when the corporate API is down.
2. **Switch between providers seamlessly** — within a single REPL session or across CLI invocations — without restarting or editing config files.
3. **Keep the corporate profile as the default** — existing workflows must not break.

## 2. User Stories

### US-1: Personal API Key Setup
> As a developer, I want to add my personal OpenAI API key so I can use GPT models directly without going through the corporate gateway.

### US-2: Profile Switching in REPL
> As a developer in a REPL session, I want to type `/profile openai` to switch to my personal OpenAI profile without restarting the CLI.

### US-3: Profile Switching via CLI Flag
> As a developer, I want to run `genai --profile anthropic ask "explain this code"` to use my Anthropic key for a one-shot query.

### US-4: List Available Profiles
> As a developer, I want to run `/profiles` in the REPL (or `genai profile list` from the CLI) to see all configured profiles and which one is active.

### US-5: Profile Creation Wizard
> As a developer, I want `genai profile create` to walk me through setting up a new provider profile with guided prompts.

### US-6: Default Provider Unchanged
> As a developer who hasn't configured any profiles, I want the CLI to behave exactly as it does today — corporate gateway, bearer token, no changes required.

## 3. Feature Requirements

### 3.1 Profiles

A **profile** is a named configuration that specifies:

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Unique identifier | `openai`, `anthropic`, `my-work` |
| `provider` | Provider type | `corporate`, `openai`, `anthropic`, `gemini` |
| `api_base_url` | API endpoint | `https://api.openai.com/v1` |
| `api_key_env` | Env var holding the API key | `OPENAI_API_KEY` |
| `default_model` | Default model for this profile | `gpt-4o` |
| `models` | List of available model names | `[gpt-4o, gpt-4o-mini]` |

Profiles are stored in `~/.genai-cli/profiles.yaml`. API keys are **never** stored in the YAML file — only the name of the environment variable that holds the key.

### 3.2 Slash Commands (REPL)

| Command | Description |
|---------|-------------|
| `/profile` | Show the currently active profile |
| `/profile <name>` | Switch to a named profile |
| `/profiles` | List all configured profiles |

These commands integrate with the existing `SlashCompleter` for tab completion.

### 3.3 CLI Flags and Subcommands

| Interface | Description |
|-----------|-------------|
| `--profile <name>` | Global flag on the `genai` root command, sets the active profile for the invocation |
| `genai profile list` | List all configured profiles |
| `genai profile use <name>` | Set the default profile persistently |
| `genai profile create` | Interactive wizard to create a new profile |
| `genai profile setup <provider>` | Shortcut: create a profile for a known provider with sensible defaults |
| `genai profile delete <name>` | Delete a profile (with confirmation) |

### 3.4 API Key Management

- API keys are read from environment variables at runtime.
- The profile YAML stores only the env var name (e.g., `api_key_env: OPENAI_API_KEY`).
- The `genai profile setup` wizard tells the user which env var to set and how (e.g., `export OPENAI_API_KEY=sk-...` in their shell profile).
- The corporate profile uses the existing bearer token flow (`AuthManager`) and does not require an `api_key_env`.

### 3.5 Provider Defaults

When running `genai profile setup <provider>`, the CLI pre-fills sensible defaults:

| Provider | `api_base_url` | `api_key_env` | `default_model` |
|----------|---------------|---------------|-----------------|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o` |
| `anthropic` | `https://api.anthropic.com` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5-20250514` |
| `gemini` | `https://generativelanguage.googleapis.com/v1beta` | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| `corporate` | *(from existing config)* | *(bearer token)* | `gpt-5-chat-global` |

## 4. UX Flows

### 4.1 REPL Profile Switching

```
You> /profiles
  * corporate    (default) — gpt-5-chat-global
    openai                 — gpt-4o
    anthropic              — claude-sonnet-4-5-20250514

You> /profile openai
  Switched to profile: openai (gpt-4o)

You> /profile
  Active profile: openai
  Provider: openai
  Model: gpt-4o
  API: https://api.openai.com/v1

You> explain closures in Python
  [response from OpenAI directly]

You> /profile corporate
  Switched to profile: corporate (GPT-5)
```

### 4.2 CLI One-Shot with Profile

```bash
# Use default (corporate) profile
$ genai ask "summarize this file" -f main.py

# Use personal OpenAI profile
$ genai --profile openai ask "summarize this file" -f main.py

# Use Anthropic profile
$ genai --profile anthropic ask "review this code" -f main.py
```

### 4.3 Profile Setup Wizard

```bash
$ genai profile setup openai

  Setting up OpenAI profile...
  API Key env var: OPENAI_API_KEY
  Default model [gpt-4o]:
  API base URL [https://api.openai.com/v1]:

  Profile 'openai' created.

  To complete setup, add your API key to your shell:
    export OPENAI_API_KEY=sk-...

  Verify with:
    genai --profile openai ask "hello"
```

### 4.4 Profile Management

```bash
$ genai profile list
  Name          Provider    Default Model             Status
  corporate*    corporate   gpt-5-chat-global         active
  openai        openai      gpt-4o                    ready
  anthropic     anthropic   claude-sonnet-4-5-20250514  missing key

$ genai profile use openai
  Default profile set to: openai

$ genai profile delete anthropic
  Delete profile 'anthropic'? [y/N]: y
  Profile deleted.
```

## 5. Success Criteria

| # | Criterion | Metric |
|---|-----------|--------|
| SC-1 | Profile switching works in REPL | `/profile openai` → next message routes to OpenAI API |
| SC-2 | Profile switching works via CLI | `--profile anthropic` → one-shot uses Anthropic API |
| SC-3 | Corporate default is preserved | No profile flag → behaves identically to current behavior |
| SC-4 | API keys are secure | `profiles.yaml` contains zero secrets; keys come from env vars only |
| SC-5 | Streaming works for all providers | SSE streaming functions correctly for OpenAI, Anthropic, and Gemini |
| SC-6 | Tab completion includes profiles | `/profile <TAB>` shows available profile names |
| SC-7 | Setup wizard is self-contained | `genai profile setup openai` requires no manual YAML editing |

## 6. Acceptance Criteria

### Functional

- [ ] `genai profile list` shows all profiles with status (active, ready, missing key)
- [ ] `genai profile create` creates a valid profile entry in `~/.genai-cli/profiles.yaml`
- [ ] `genai profile setup openai|anthropic|gemini` pre-fills known defaults
- [ ] `genai profile use <name>` updates the default profile persistently
- [ ] `genai profile delete <name>` removes a profile with confirmation
- [ ] `--profile <name>` flag works on all CLI commands (`ask`, `models`, etc.)
- [ ] `/profile <name>` switches the active profile mid-session in the REPL
- [ ] `/profiles` lists all profiles with an indicator for the active one
- [ ] Messages sent after a profile switch route to the correct provider API
- [ ] Streaming responses work for all four providers (corporate, OpenAI, Anthropic, Gemini)
- [ ] Conversation history is maintained locally when using direct API profiles
- [ ] `/model` and `/models` show models relevant to the active profile

### Error Handling

- [ ] Switching to a profile with a missing API key shows a clear error message
- [ ] Switching to a nonexistent profile shows "profile not found" with suggestions
- [ ] Network errors from direct APIs show provider-specific troubleshooting hints
- [ ] Invalid API key errors are distinguishable from other auth errors

## 7. Non-Functional Requirements

### 7.1 Backward Compatibility

- The `corporate` profile is always present, even if `profiles.yaml` doesn't exist.
- If no `--profile` flag is given and no default is set, the CLI uses the corporate profile.
- Existing `~/.genai-cli/settings.yaml`, `auth login` flow, and bearer token management are unchanged.
- All existing slash commands (`/model`, `/clear`, `/history`, etc.) continue to work.

### 7.2 Security

- API keys are **never** stored in `profiles.yaml` or any YAML/JSON config file.
- Keys are read from environment variables at runtime only.
- The `profiles.yaml` file stores only the env var name (e.g., `api_key_env: OPENAI_API_KEY`).
- The `genai profile setup` wizard does not prompt for the actual key value.
- File permissions on `~/.genai-cli/` should be `700` (user-only).

### 7.3 Performance

- Profile switching is instantaneous (no network calls during switch).
- The first message after a profile switch may have a cold-start delay for HTTP client creation.
- No additional startup latency when using the default corporate profile.

### 7.4 Dependencies

- No new runtime dependencies. Direct API calls use the existing `httpx` library.
- No provider-specific SDKs (`openai`, `anthropic`, `google-genai`) are required.
- All provider API calls are made using raw HTTP via `httpx`.

## 8. Out of Scope (v1)

- Multi-provider routing within a single conversation (e.g., "ask OpenAI then ask Claude")
- API key rotation or refresh token flows for direct providers
- Provider-specific features (function calling, tool use, vision) beyond basic chat completion
- Billing dashboard or cross-provider cost comparison
- Profile import/export between machines
- Team-shared profile configurations
