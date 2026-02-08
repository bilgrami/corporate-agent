# Architecture

## Component Overview

```
+------------------+     +------------------+     +------------------+
|     cli.py       |     |     repl.py      |     |    agent.py      |
|   (Click CLI)    |---->| (prompt_toolkit)  |---->|  (AgentLoop)     |
+------------------+     +------------------+     +------------------+
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
|   config.py      |     |   client.py      |     |   applier.py     |
| (ConfigManager)  |     |  (GenAIClient)   |     | (Parser+Applier) |
+------------------+     +------------------+     +------------------+
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
|   models.py      |     |    auth.py       |     |   display.py     |
|  (data classes)  |     | (AuthManager)    |     |    (Rich)        |
+------------------+     +------------------+     +------------------+
                                  |
                          +------------------+
                          |  streaming.py    |
                          |  (SSE handler)   |
                          +------------------+

+------------------+     +------------------+     +------------------+
|  bundler.py      |     |   session.py     |     | token_tracker.py |
| (FileBundler)    |     | (SessionManager) |     | (TokenTracker)   |
+------------------+     +------------------+     +------------------+

+------------------+     +------------------+     +------------------+
| skills/loader.py |     |skills/registry.py|     |skills/executor.py|
| (SkillLoader)    |     | (SkillRegistry)  |     | (SkillExecutor)  |
+------------------+     +------------------+     +------------------+
```

## Module Responsibilities

| Module | Class | Responsibility |
|--------|-------|---------------|
| `models.py` | Data classes | ModelInfo, AppSettings, AuthToken, ChatMessage, FileBundle, TokenUsage |
| `config.py` | ConfigManager | Load/merge YAML with 5-level precedence, model lookup, system prompt |
| `auth.py` | AuthManager | JWT token load/save, decode (no verification), expiry check |
| `client.py` | GenAIClient | httpx sync client for all API endpoints, 401 handling |
| `streaming.py` | StreamHandler | SSE parsing, token yielding, fallback to non-streaming |
| `display.py` | Display | Rich console output: markdown, tables, diffs, spinners, colors |
| `bundler.py` | FileBundler | File discovery, classification by type, bundling with markers |
| `session.py` | SessionManager | Create/save/load/list/compact sessions as JSON |
| `token_tracker.py` | TokenTracker | Track consumed tokens, thresholds, model switching |
| `applier.py` | ResponseParser, FileApplier | Parse 3 code formats, validate paths, apply with safety |
| `agent.py` | AgentLoop | Multi-round: upload, prompt, parse, apply, repeat |
| `skills/loader.py` | SkillLoader | Parse SKILL.md frontmatter + body, 3-tier loading |
| `skills/registry.py` | SkillRegistry | Discover skills from 3 locations, priority override |
| `skills/executor.py` | SkillExecutor | Assemble prompt, run AgentLoop with skill context |
| `cli.py` | Click commands | CLI entry point, all subcommands |
| `repl.py` | ReplSession | Interactive REPL with slash commands |

## Data Flows

### One-Shot Ask

```
User runs: genai ask "review this" --files src/ --type code

1. cli.py parses Click arguments
2. AuthManager loads JWT from ~/.genai-cli/.env
3. GenAIClient created with config + auth
4. FileBundler discovers files, classifies by type, bundles
5. Client uploads each bundle (one PUT per file type)
6. stream_or_complete() sends prompt, streams SSE response
7. Display renders markdown response
8. ResponseParser extracts code blocks (if any)
9. FileApplier applies with confirm/auto/dry-run mode
```

### Interactive REPL

```
User runs: genai (no subcommand)

1. cli.py creates ReplSession
2. ReplSession creates SessionManager + TokenTracker
3. prompt_toolkit loop reads input
4. Slash commands (/help, /model, etc.) -> direct handlers
5. Chat messages -> GenAIClient -> stream -> display
6. Responses scanned for code blocks -> apply if found
7. Token usage tracked and displayed after each message
8. /quit saves session to ~/.genai-cli/sessions/<id>.json
```

### Skill Execution

```
User runs: genai skill invoke review --files src/

1. SkillRegistry discovers skills from 3 locations
2. SkillLoader parses SKILL.md frontmatter (Tier 1: ~100 tokens)
3. SkillLoader.load_full() reads body + references (Tier 2/3)
4. SkillExecutor assembles prompt:
   system_prompt + agents.md + skill_body + user_message
5. AgentLoop runs with assembled prompt
6. Each round: upload -> prompt -> response -> parse -> apply
```

## Key Design Decisions

### YAML for All Configuration
All settings, model definitions, headers, and system prompts live in YAML.
New models are added by editing `config/models.yaml` -- no code changes needed.

### No Vendor Names in .py Files
Model names (GPT-5, Claude, Gemini) appear only in `config/models.yaml` as data.
Source code references models by their config key (e.g., `gpt-5-chat-global`).

### JWT Decode Without Verification
The tool decodes JWT tokens using `pyjwt` with `options={"verify_signature": False}`.
No secret key is needed. Only the `exp` (expiry) and `email` claims are used.
The API server validates the token on each request.

### SKILL.md Format
Skills use markdown files with YAML frontmatter, compatible with the
obra/superpowers SKILL.md specification. This keeps skill definitions
human-readable and version-controllable.

### 5-Level Config Precedence
CLI flags > environment variables > project config > user config > package defaults.
This allows team-level settings (project `.genai-cli/settings.yaml`) while
individual developers can override with their own preferences.

### Separate Upload Per File Type
Files are bundled by type (code/docs/scripts/notebooks) and uploaded as
separate PUT requests. This matches the corporate API's expected format.
Each bundle uses `===== FILE: /path =====` markers to delimit files.

### Single-Threaded Agent Loop
The agent loop runs synchronously for correctness. Multi-agent parallel
execution is planned for Phase 6 but not yet implemented.

## Security Architecture

- **Token storage**: `~/.genai-cli/.env` with `chmod 600` (owner-only)
- **Path validation**: `applier.py` rejects `..` traversal and paths outside project root
- **Write restrictions**: `blocked_write_patterns` prevents writes to `.env`, `*.pem`, `*.key`, credentials
- **File exclusions**: Sensitive files excluded from bundling via `exclude_patterns`
- **Network scope**: Only `api_base_url` is contacted; no external APIs or telemetry
- **No shell injection**: No `shell=True` in subprocess calls
- **Secrets never logged**: `AuthToken.__repr__` masks the token value

## Directory Structure

```
corporate-agent/
  config/
    settings.yaml          # Default settings
    models.yaml            # Model registry (11 models)
    headers.yaml           # Default HTTP headers
    system_prompt.yaml     # System prompt template
  docs/
    PRD.md                 # Product requirements
    Architecture.md        # This file
    CONTRIBUTING.md        # Developer guide
    implementation_plans/  # Per-phase planning docs
  scripts/
    setup.sh, test.sh, lint.sh, format.sh, build.sh, clean.sh, run.sh, help.sh
  skills/
    review/, fix/, refactor/, explain/, test-gen/, doc-gen/,
    commit-msg/, security-audit/, systematic-debugging/,
    test-driven-development/, writing-plans/, executing-plans/,
    requesting-code-review/, brainstorming/
  src/genai_cli/
    __init__.py, __main__.py, models.py, config.py, auth.py,
    client.py, streaming.py, display.py, cli.py, bundler.py,
    repl.py, session.py, token_tracker.py, applier.py, agent.py,
    skills/__init__.py, skills/loader.py, skills/registry.py, skills/executor.py
  tests/
    conftest.py, test_config.py, test_auth.py, test_client.py,
    test_display.py, test_cli.py, test_bundler.py, test_streaming.py,
    test_token_tracker.py, test_session.py, test_repl.py,
    test_applier.py, test_agent.py, test_skill_loader.py,
    test_skill_registry.py, test_skill_executor.py
  Makefile
  pyproject.toml
  README.md
  AGENTS.md
  CHANGELOG.md
```
