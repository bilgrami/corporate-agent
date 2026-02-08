# PRD: Corporate AI CLI Agent

**Version:** 1.0.0
**Date:** 2026-02-07
**Status:** Draft

---

## 1. Problem Statement

Developers within corporate environments have access to a powerful multi-model AI
chat platform via web browser, but lack a CLI-based workflow to:

- Submit code, docs, scripts, and notebooks for AI-assisted review and generation
- Get AI responses and **automatically apply changes** to local files
- Chain multiple AI interactions as an autonomous agent
- Integrate AI into existing development workflows (terminal, CI/CD, scripts)

The web UI requires manual copy-paste of code and manual application of suggested
changes. This tool eliminates that friction entirely.

**Constraint: This tool ONLY communicates with the corporate AI chat API. No
external APIs, services, or telemetry. All traffic stays on the corporate network.**

---

## 2. Goals

| # | Goal | Success Criteria |
|---|------|------------------|
| 1 | CLI-first experience | Interactive REPL with `/commands`, streaming responses |
| 2 | File submission (4 types) | Bundle and upload code, docs, scripts, notebooks separately |
| 3 | Agent mode | Parse responses and update local files with confirmation |
| 4 | Skills system | SKILL.md-compatible, progressive disclosure, per-folder agents |
| 5 | Multi-model support | Switch models via `/model`, YAML-defined limits |
| 6 | Session persistence | Resume conversations, track context tokens remaining |
| 7 | Cross-platform | macOS, Linux, Windows Git Bash via sh scripts |
| 8 | Multi-agent (roadmap) | Up to 4 parallel agents working on different tasks |

---

## 3. API Surface (Reverse-Engineered from Browser)

### 3.1 Base Configuration

All URLs are configurable via settings. No vendor domains are hardcoded.

```yaml
# settings.yaml
api_base_url: "https://api-genai.<domain>.com"
web_ui_url: "https://genai.<domain>.com"
```

### 3.2 Endpoints

| Endpoint | Method | Path | Content-Type |
|----------|--------|------|-------------|
| List History | GET | `/api/v1/chathistory/?skip={n}&limit={n}` | application/json |
| Get Conversation | GET | `/api/v1/chathistory/{session_id}` | application/json |
| Create Chat | POST | `/api/v1/chathistory/create?chat_type=unified&timestamp={ts}&session_id={uuid}` | application/json |
| Upload Document | PUT | `/api/v1/conversation/{id}/document/upload` | multipart/form-data |
| User Usage | GET | `/api/v1/user/usage` | application/json |
| Stream | GET | `/api/v1/chathistory/stream` | text/event-stream |
| Details | GET | `/api/v1/conversation/{id}/details` | application/json |
| Details All | GET | `/api/v1/conversation/{id}/details-all` | application/json |

### 3.3 Required Headers

```yaml
# headers.yaml (shipped as default, overridable)
accept: "*/*"
accept-language: "en-US,en;q=0.9"
ngrok-skip-browser-warning: "true"
priority: "u=1, i"
sec-fetch-dest: "empty"
sec-fetch-mode: "cors"
sec-fetch-site: "same-site"
user-agent: "Mozilla/5.0"
# origin and referer are derived from web_ui_url in settings
```

### 3.4 Authentication

Bearer JWT token, obtained from browser DevTools.

```
Authorization: Bearer eyJ0eXAiOi...
```

Stored in `~/.genai-cli/.env` with file permissions `0600`.

### 3.5 Upload Format

Each file type is uploaded as a **separate** PUT request. Multiple files of the
same type are concatenated into one blob:

```
===== FILE: /absolute/path/to/file.py =====
Relative Path: relative/path.py

<file content>
```

### 3.6 Response Schema

```json
{
  "SessionId": "uuid",
  "TableId": null,
  "UserOrBot": "user | assistant",
  "Message": "string",
  "TimestampUTC": "ISO-8601",
  "ModelName": "model-api-id",
  "DisplayName": "Model Display Name",
  "Vote": 0,
  "TokensConsumed": 2006,
  "TokenCost": 0.00276,
  "UploadContent": "string | null",
  "WebSearchInfo": "[] | null",
  "Images": null,
  "Audios": null,
  "Steps": [{"name": "assistant", "data": "text", "type": "agent"}],
  "UserEmail": "user@domain.com",
  "IsArchieved": false
}
```

---

## 4. Model Registry (YAML Config)

Models and their limits are defined in `config/models.yaml`. When new models
are approved or limits change, update this file only - no code changes needed.

```yaml
# config/models.yaml
models:
  gpt-5-chat-global:
    display_name: "GPT-5"
    provider: "openai"
    tier: "full"
    context_window: 128000
    max_output_tokens: 16384
    cost_per_1k_input: 0.005
    cost_per_1k_output: 0.015
    supports_streaming: true
    supports_file_upload: true

  gpt-5-mini-chat-global:
    display_name: "GPT-5 Mini"
    provider: "openai"
    tier: "mid"
    context_window: 128000
    max_output_tokens: 16384
    cost_per_1k_input: 0.0004
    cost_per_1k_output: 0.0016
    supports_streaming: true
    supports_file_upload: true

  gpt-5-nano-chat-global:
    display_name: "GPT-5 Nano"
    provider: "openai"
    tier: "light"
    context_window: 128000
    max_output_tokens: 16384
    cost_per_1k_input: 0.0001
    cost_per_1k_output: 0.0004
    supports_streaming: true
    supports_file_upload: true

  gpt-4.1-chat-global:
    display_name: "GPT-4.1"
    provider: "openai"
    tier: "full"
    context_window: 1048576
    max_output_tokens: 32768
    cost_per_1k_input: 0.002
    cost_per_1k_output: 0.008
    supports_streaming: true
    supports_file_upload: true

  gpt-4.1-mini-chat-global:
    display_name: "GPT-4.1 Mini"
    provider: "openai"
    tier: "mid"
    context_window: 1048576
    max_output_tokens: 32768
    cost_per_1k_input: 0.0004
    cost_per_1k_output: 0.0016
    supports_streaming: true
    supports_file_upload: true

  gpt-4.1-nano-chat-global:
    display_name: "GPT-4.1 Nano"
    provider: "openai"
    tier: "light"
    context_window: 1048576
    max_output_tokens: 32768
    cost_per_1k_input: 0.0001
    cost_per_1k_output: 0.0004
    supports_streaming: true
    supports_file_upload: true

  claude-3-opus-global:
    display_name: "Claude 3 Opus"
    provider: "anthropic"
    tier: "full"
    context_window: 200000
    max_output_tokens: 4096
    cost_per_1k_input: 0.015
    cost_per_1k_output: 0.075
    supports_streaming: true
    supports_file_upload: true

  claude-sonnet-4-5-global:
    display_name: "Claude Sonnet 4.5"
    provider: "anthropic"
    tier: "full"
    context_window: 200000
    max_output_tokens: 16384
    cost_per_1k_input: 0.003
    cost_per_1k_output: 0.015
    supports_streaming: true
    supports_file_upload: true

  gemini-2.5-pro-global:
    display_name: "Gemini 2.5 Pro"
    provider: "google"
    tier: "full"
    context_window: 1048576
    max_output_tokens: 65536
    cost_per_1k_input: 0.00125
    cost_per_1k_output: 0.01
    supports_streaming: true
    supports_file_upload: true

  gemini-2.5-flash-global:
    display_name: "Gemini 2.5 Flash"
    provider: "google"
    tier: "mid"
    context_window: 1048576
    max_output_tokens: 65536
    cost_per_1k_input: 0.00015
    cost_per_1k_output: 0.0006
    supports_streaming: true
    supports_file_upload: true

  gemini-2.5-flash-lite-global:
    display_name: "Gemini 2.5 Flash Lite"
    provider: "google"
    tier: "light"
    context_window: 1048576
    max_output_tokens: 65536
    cost_per_1k_input: 0.000075
    cost_per_1k_output: 0.0003
    supports_streaming: true
    supports_file_upload: true

# Default model used when none specified
default_model: "gpt-5-chat-global"
```

**Token tracking:** The CLI tracks cumulative `TokensConsumed` from API responses
and compares against `context_window` for the active model. When context usage
exceeds 80%, warn the user. At 95%, suggest `/clear` or `/compact`.

---

## 5. Architecture

### 5.1 Component Diagram

```
┌───────────────────────────────────────────────────────────┐
│                    genai-cli                               │
│                                                            │
│  ┌──────────┐   ┌────────────┐   ┌─────────────────────┐  │
│  │   CLI    │   │  Skills    │   │    Agent Loop        │  │
│  │  (click) │──►│  Engine    │──►│  prompt → response   │  │
│  │          │   │  (SKILL.md │   │  → parse → apply     │  │
│  │ /commands│   │   loader)  │   │  → re-prompt (opt)   │  │
│  └────┬─────┘   └─────┬──────┘   └──────────┬──────────┘  │
│       │               │                      │              │
│  ┌────▼─────┐   ┌─────▼──────┐   ┌──────────▼──────────┐  │
│  │ Session  │   │   File     │   │   Response Applier   │  │
│  │ Manager  │   │   Bundler  │   │   (code blocks,      │  │
│  │ (persist,│   │  (4 types, │   │    diffs, full files) │  │
│  │  tokens) │   │   markers) │   │                      │  │
│  └────┬─────┘   └─────┬──────┘   └──────────┬──────────┘  │
│       │               │                      │              │
│  ┌────▼─────┐   ┌─────▼──────┐   ┌──────────▼──────────┐  │
│  │  Config  │   │  Display   │   │    Auth              │  │
│  │  (YAML)  │   │  (rich)    │   │   (.env, JWT)       │  │
│  └────┬─────┘   └─────┬──────┘   └──────────┬──────────┘  │
│       │               │                      │              │
│  ┌────▼───────────────▼──────────────────────▼──────────┐  │
│  │              GenAI API Client                         │  │
│  │     (HTTP, headers, upload, chat, stream)             │  │
│  └───────────────────────┬───────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                  Corporate AI Chat API
                  (internal network only)
```

### 5.2 Module Responsibilities (SRP)

Each module has **exactly one reason to change**:

| Module | Responsibility | Does NOT do |
|--------|---------------|-------------|
| `cli.py` | Parse CLI args, dispatch to handlers | Business logic, HTTP |
| `client.py` | HTTP requests to corporate API | File I/O, display |
| `session.py` | Create/resume/list/clear conversations | HTTP, display |
| `bundler.py` | Discover files, format into upload blobs | HTTP, CLI |
| `applier.py` | Parse AI response, extract code, write files | HTTP, CLI |
| `agent.py` | Orchestrate upload → prompt → response → apply loop | HTTP directly |
| `streaming.py` | Parse SSE event stream, yield tokens | File I/O, CLI |
| `config.py` | Load/save/merge YAML config | HTTP, display |
| `auth.py` | Token load/validate/expiry check | HTTP, config |
| `models.py` | Data classes (no logic) | Everything else |
| `display.py` | Terminal rendering via rich | Business logic |
| `skills/loader.py` | Parse SKILL.md frontmatter + body | Skill execution |
| `skills/executor.py` | Invoke skill, inject prompt, handle response | Skill discovery |
| `skills/registry.py` | Discover and index available skills | Execution, parsing |

---

## 6. Project Structure

```
corporate-agent/
├── Makefile                          # Thin wrapper → scripts/*.sh
├── pyproject.toml                    # Project metadata, dependencies
├── setup.cfg                         # Linter/formatter config
│
├── scripts/
│   ├── setup.sh                      # Create venv, install deps
│   ├── test.sh                       # Run pytest
│   ├── lint.sh                       # Run ruff + mypy
│   ├── format.sh                     # Run ruff format
│   ├── build.sh                      # Build wheel
│   ├── clean.sh                      # Remove artifacts
│   └── run.sh                        # Run the CLI
│
├── config/
│   ├── models.yaml                   # Model registry (limits, costs)
│   ├── settings.yaml                 # Default settings (overridable)
│   ├── headers.yaml                  # Default HTTP headers
│   └── system_prompt.yaml            # Default system prompt
│
├── docs/
│   ├── PRD.md                        # This file
│   ├── TDD.md                        # Technical design document
│   ├── Architecture.md               # Architecture decisions
│   └── implementation_plans/         # Per-phase plans + agents.md
│       ├── phase-01-foundation/
│       │   └── agents.md
│       ├── phase-02-agent-applier/
│       │   └── agents.md
│       ├── phase-03-skills/
│       │   └── agents.md
│       └── phase-04-multi-agent/
│           └── agents.md
│
├── src/
│   └── genai_cli/
│       ├── __init__.py
│       ├── __main__.py               # python -m genai_cli
│       ├── cli.py                    # Click command definitions
│       ├── client.py                 # Corporate API HTTP client
│       ├── session.py                # Session management
│       ├── bundler.py                # File bundler (4 types)
│       ├── applier.py                # Response → file changes
│       ├── agent.py                  # Agent loop orchestrator
│       ├── streaming.py              # SSE / stream handler
│       ├── config.py                 # YAML config manager
│       ├── auth.py                   # Token management
│       ├── models.py                 # Data classes
│       ├── display.py                # Rich terminal output
│       ├── token_tracker.py          # Context window tracking
│       └── skills/
│           ├── __init__.py
│           ├── registry.py           # Skill discovery & index
│           ├── loader.py             # SKILL.md parser
│           └── executor.py           # Skill invocation
│
├── skills/                           # Bundled skills (SKILL.md format)
│   ├── review/
│   │   └── SKILL.md
│   ├── fix/
│   │   └── SKILL.md
│   ├── refactor/
│   │   └── SKILL.md
│   ├── explain/
│   │   └── SKILL.md
│   ├── test-gen/
│   │   └── SKILL.md
│   ├── doc-gen/
│   │   └── SKILL.md
│   ├── commit-msg/
│   │   └── SKILL.md
│   ├── security-audit/
│   │   └── SKILL.md
│   ├── systematic-debugging/        # From obra/superpowers
│   │   └── SKILL.md
│   ├── test-driven-development/      # From obra/superpowers
│   │   └── SKILL.md
│   ├── writing-plans/                # From obra/superpowers
│   │   └── SKILL.md
│   ├── executing-plans/              # From obra/superpowers
│   │   └── SKILL.md
│   ├── requesting-code-review/       # From obra/superpowers
│   │   └── SKILL.md
│   └── brainstorming/                # From obra/superpowers
│       └── SKILL.md
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Shared fixtures
│   ├── test_client.py
│   ├── test_bundler.py
│   ├── test_applier.py
│   ├── test_agent.py
│   ├── test_session.py
│   ├── test_config.py
│   ├── test_auth.py
│   ├── test_token_tracker.py
│   ├── test_skill_loader.py
│   └── test_skill_executor.py
│
├── AGENTS.md                         # Agent instructions for this repo
├── CHANGELOG.md                      # Changelog (format in §12)
└── README.md                         # Usage guide
```

---

## 7. CLI Interface

### 7.1 Interactive REPL (Default)

```bash
$ genai

  Corporate AI CLI v1.0.0 | Model: GPT-5 | Session: new
  Context: 0 / 128,000 tokens
  Type /help for commands, Ctrl+C to exit

You> /files src/pipeline.py
  ✓ Queued 1 code file (245 lines, ~3,200 tokens)

You> find and fix bugs in this code

Assistant> I found 3 issues in your pipeline:

  1. **Line 42** - Missing null check on `data_source` ...
  2. **Line 87** - SQL injection vulnerability ...
  3. **Line 123** - Race condition in parallel processing ...

  ┌─ src/pipeline.py (3 edits) ─────────────────────────┐
  │ @@ -42,3 +42,5 @@                                    │
  │ -    result = query(data_source)                      │
  │ +    if data_source is None:                          │
  │ +        raise ValueError("data_source required")    │
  │ +    result = query(data_source)                      │
  └──────────────────────────────────────────────────────┘

  Apply changes? [Y]es / [n]o / [d]iff / [a]ll: y
  ✓ Applied 3 edits to src/pipeline.py
  Context: 5,247 / 128,000 tokens

You> /model claude-sonnet-4.5
  ✓ Switched to Claude Sonnet 4.5 (200K context)

You> /clear
  ✓ Session cleared. Starting fresh.

You> /quit
  Session saved: af86d528-2b12-4d68-a45f-09cafddc7e63
```

### 7.2 Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/model [name]` | List models or switch to specified model |
| `/models` | List all available models with limits |
| `/files <paths...>` | Queue files for next message |
| `/clear` | Clear session, start fresh conversation |
| `/fresh` | Alias for `/clear` |
| `/compact` | Summarize conversation to reduce token usage |
| `/history` | List recent conversations |
| `/resume <id>` | Resume a saved conversation |
| `/usage` | Show token usage and costs |
| `/status` | Show current session, model, token count |
| `/config [key] [value]` | View or update settings |
| `/skill <name>` | Invoke a skill |
| `/skills` | List available skills |
| `/auto-apply [on\|off]` | Toggle auto-apply mode |
| `/agent [rounds]` | Enable agent mode for next message |
| `/quit` | Save session and exit |

### 7.3 Non-Interactive Commands

```bash
# One-shot question with files
genai ask "find bugs" --files src/ --type code

# Invoke a skill directly
genai skill review --files src/
genai skill fix --files src/broken.py --auto-apply
genai skill explain --files src/complex.py

# Session management
genai history
genai resume af86d528

# Account info
genai usage
genai models

# Configuration
genai config set default_model gemini-2.5-pro-global
genai config set auto_apply true
genai auth login
genai auth verify
```

### 7.4 Global Flags

```
--model, -m       Override model for this invocation
--files, -f       Files/directories to include
--type, -t        File type filter: code|docs|scripts|notebooks|all
--auto-apply      Auto-apply file changes without confirmation
--agent           Enable agent mode (multi-round)
--max-rounds      Max agent loop iterations (default: 5)
--no-stream       Disable streaming, wait for complete response
--dry-run         Show what would happen without executing
--verbose, -v     Verbose output with debug info
--json            Output as JSON (for scripting)
--config, -c      Path to custom config file
```

---

## 8. File Bundler (4 Types)

### 8.1 Type Definitions

Stored in `config/settings.yaml`, fully customizable:

```yaml
file_types:
  code:
    extensions:
      - .py
      - .js
      - .ts
      - .tsx
      - .java
      - .go
      - .rs
      - .cpp
      - .c
      - .h
      - .rb
      - .sql
      - .scala
      - .kt
      - .swift
      - .r
      - .cs
    max_file_size_kb: 500

  docs:
    extensions:
      - .md
      - .txt
      - .rst
      - .yaml
      - .yml
      - .toml
      - .json
      - .xml
      - .csv
      - .cfg
      - .ini
      - .properties
    max_file_size_kb: 500

  scripts:
    extensions:
      - .sh
      - .bash
      - .zsh
      - .ps1
      - .bat
      - .cmd
    include_names:
      - Makefile
      - Dockerfile
      - Jenkinsfile
      - Vagrantfile
    max_file_size_kb: 200

  notebooks:
    extensions:
      - .ipynb
    max_file_size_kb: 1000

exclude_patterns:
  - "**/__pycache__/**"
  - "**/.git/**"
  - "**/node_modules/**"
  - "**/.venv/**"
  - "**/venv/**"
  - "**/.env"
  - "**/*.secret*"
  - "**/*.pem"
  - "**/*.key"
  - "**/dist/**"
  - "**/build/**"
  - "**/.pytest_cache/**"
  - "**/*.pyc"
```

### 8.2 Bundle Format

**Code, docs, scripts** - concatenated with markers:

```
===== FILE: /Users/dev/project/src/main.py =====
Relative Path: src/main.py

import os
from config import load
...
```

**Notebooks** - cells extracted and formatted:

```
===== NOTEBOOK: /Users/dev/project/notebooks/analysis.ipynb =====
Relative Path: notebooks/analysis.ipynb

--- Cell 1 [markdown] ---
# Data Analysis Pipeline

--- Cell 2 [code] ---
import pandas as pd
df = pd.read_csv("data.csv")

--- Cell 3 [output] ---
       count    mean
col1   1000    45.2
```

### 8.3 Upload Strategy

Each type is a **separate upload** to the conversation:

```
PUT /api/v1/conversation/{id}/document/upload  ← code bundle
PUT /api/v1/conversation/{id}/document/upload  ← docs bundle
PUT /api/v1/conversation/{id}/document/upload  ← scripts bundle
PUT /api/v1/conversation/{id}/document/upload  ← notebooks bundle
```

---

## 9. Agent Mode & Response Applier

### 9.1 Agent Loop

```
┌─────────────────────────────────────────────────┐
│                  Agent Loop                      │
│                                                  │
│  1. Bundle files by type                         │
│  2. Upload each bundle (4 separate uploads)      │
│  3. Send prompt (with system prompt prepended)   │
│  4. Receive response (streaming or complete)     │
│  5. Parse response for actionable items:         │
│     a. Code blocks with file paths → apply       │
│     b. Shell commands → show, confirm, execute   │
│     c. Follow-up needed → continue loop          │
│  6. If more rounds remain → go to step 3         │
│  7. Display summary of all changes               │
│                                                  │
│  Max rounds: configurable (default 5)            │
│  Stop conditions:                                │
│    - No actionable items in response             │
│    - Max rounds reached                          │
│    - User cancels (Ctrl+C)                       │
│    - Token limit approaching (>95%)              │
└─────────────────────────────────────────────────┘
```

### 9.2 Response Applier

The applier uses **SEARCH/REPLACE blocks** as the primary edit format, with
legacy formats as fallback.

**Primary Format: SEARCH/REPLACE blocks**

```
path/to/file.py
<<<<<<< SEARCH
exact existing content to find
=======
new content to replace with
>>>>>>> REPLACE
```

Operations:
- **Create file**: Empty SEARCH section (nothing between `<<<<<<< SEARCH` and `=======`)
- **Edit file**: SEARCH content must exist exactly in the file
- **Delete content**: Empty REPLACE section
- **Multiple edits**: Repeat blocks with the same file path

Why this format:
- Markers `<<<<<<< SEARCH`, `=======`, `>>>>>>> REPLACE` never appear in real code
- No escaping needed (unlike XML/JSON)
- LLMs know git conflict markers from training data
- Self-validating: SEARCH content must exist in the file
- Surgical edits without repeating entire files

**Error Feedback**: When a SEARCH block does not match the file content, the
agent loop feeds back the actual file content to the AI so it can self-correct
in the next round.

**Fallback Formats** (used only if no SEARCH/REPLACE blocks found):

1. Fenced code block with file path: `` ```language:path/to/file.ext ``
2. Unified diff format with `--- a/` and `+++ b/` headers
3. Complete file content with `FILE: path/to/file.ext` marker

See [TDD.md](TDD.md) for technical details on the parser and matching engine.

### 9.3 Apply Modes

Configurable globally in settings or per-invocation:

| Mode | Behavior | Flag |
|------|----------|------|
| `confirm` (default) | Show diff, ask Y/n/d/a for each file | (default) |
| `auto_apply` | Apply all changes, show summary after | `--auto-apply` |
| `dry_run` | Show what would change, apply nothing | `--dry-run` |

### 9.4 Safety

- Preview changes as colored diff before applying
- Warn if target file has uncommitted git changes
- Create `.bak` backup before overwriting (configurable)
- Validate file paths (no traversal attacks like `../../etc/passwd`)
- Refuse to write to paths outside project root
- Log all file modifications to session history

---

## 10. Skills System

### 10.1 Skill Format (SKILL.md Spec Compatible)

Each skill is a directory with a `SKILL.md` file:

```
skills/review/
├── SKILL.md              # Required: frontmatter + instructions
├── references/           # Optional: loaded on demand
│   └── checklist.md
├── scripts/              # Optional: executable helpers
│   └── format_report.py
└── assets/               # Optional: templates
    └── report_template.md
```

**SKILL.md format:**

```yaml
---
name: review
description: >
  Performs comprehensive code review for bugs, security issues,
  performance problems, and style violations. Use when reviewing
  code files or when the user asks for a code review.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: development
---

# Code Review

You are a senior code reviewer. Review the provided code files for:

1. **Bugs and logic errors** - incorrect behavior, off-by-one, null refs
2. **Security vulnerabilities** - injection, XSS, auth bypass, OWASP top 10
3. **Performance issues** - N+1 queries, unnecessary allocations, blocking I/O
4. **Code style** - naming, structure, DRY violations, complexity
5. **Missing error handling** - unhandled exceptions, missing validation

For each issue found:
- State the file path and line number
- Classify severity: CRITICAL / WARNING / INFO
- Describe the problem
- Provide the fix as a code block with the file path

Format fixes as:
```language:path/to/file.ext
<corrected code>
```
```

### 10.2 Bundled Skills

**Custom skills (built for this tool):**

| Skill | Purpose | Auto-apply |
|-------|---------|-----------|
| `review` | Comprehensive code review | No |
| `fix` | Find and fix bugs | Yes (confirm) |
| `refactor` | Improve code quality | Yes (confirm) |
| `explain` | Explain code logic | No |
| `test-gen` | Generate unit tests | Yes (confirm) |
| `doc-gen` | Generate documentation | Yes (confirm) |
| `commit-msg` | Generate commit message from diff | No |
| `security-audit` | Security-focused review | No |

**Adapted from obra/superpowers:**

| Skill | Purpose |
|-------|---------|
| `systematic-debugging` | 4-phase root cause analysis |
| `test-driven-development` | RED-GREEN-REFACTOR methodology |
| `writing-plans` | Implementation plan creation |
| `executing-plans` | Plan execution workflow |
| `requesting-code-review` | Pre-merge review process |
| `brainstorming` | Design ideation |

### 10.3 Skill Discovery (Progressive Disclosure)

```
Tier 1 - Always loaded (~100 tokens per skill):
  → name + description from SKILL.md frontmatter
  → Used for skill matching against user intent

Tier 2 - Loaded on activation (~5000 tokens):
  → Full SKILL.md body (instructions)

Tier 3 - Loaded on demand:
  → references/, scripts/, assets/
  → Only when skill instructions reference them
```

### 10.4 Per-Folder Agent Specialization

Projects can define specialized agents via `agents.md` in any directory:

```
project/
├── agents.md              # Global agents for this project
├── src/
│   ├── agents.md          # Developer agent
│   └── ...
├── tests/
│   ├── agents.md          # Tester agent
│   └── ...
├── docs/
│   ├── agents.md          # Documentation agent
│   └── ...
├── infra/
│   ├── agents.md          # Cloud/DevOps agent
│   └── ...
└── scripts/
    ├── agents.md          # Automation agent
    └── ...
```

**agents.md format:**

```markdown
# Agent: Developer

## Purpose
Write production-quality Python code following team conventions.

## System Prompt Extension
- Follow PEP 8 and use type hints for all public functions
- Use pathlib instead of os.path
- Prefer composition over inheritance
- All database queries use parameterized statements

## Skills
- fix
- refactor
- test-driven-development

## Constraints
- Never modify files outside src/
- Always run tests after changes
```

When the CLI operates on files in a directory, it discovers the nearest
`agents.md` and merges its instructions with the global system prompt.

### 10.5 Custom Skills

Users add custom skills to `~/.genai-cli/skills/` or project-level
`.genai-cli/skills/`. The loader scans all skill directories:

```
Priority (highest first):
  1. Project: .genai-cli/skills/
  2. User:    ~/.genai-cli/skills/
  3. Bundled: <package>/skills/
```

---

## 11. System Prompt

### 11.1 Default System Prompt

Stored in `config/system_prompt.yaml` and prepended to every conversation:

```yaml
# config/system_prompt.yaml
system_prompt: |
  You are an AI coding assistant accessed via a CLI tool.

  ## Rules
  - Never mention {agent_name} in code, commit messages, or changelogs
  - Always read PRD.md and TDD.md (typically under docs/) before starting work
  - Always create CHANGELOG.md before finishing work
  - Always analyze CHANGELOG.md before starting work, especially in plan mode
  - If there is a drift in PRD.md, TDD.md, or Architecture.md due to your
    changes, report back and keep the docs updated
  - Always create a phased implementation plan; each phase must be
    self-contained with clear steps and acceptance criteria
  - Ask clarifying questions when requirements are ambiguous
  - Focus on planning and organized implementation
  - If unit tests are present, run them after each phase
  - When creating an implementation plan, document it under
    docs/implementation_plans/ folder
  - For each phase, create an agents.md file containing: task, purpose,
    description, acceptance criteria, assumptions, rationale, testing criteria
  - Keep implementation plans and agents.md up to date and self-contained
  - Inside README.md, update the FAQ and troubleshooting section if the
    implementation affects it. Organize by personas and roles.

  ## CHANGELOG Format
  All notable changes will be documented in CHANGELOG.md.

  Rules:
  - Reverse chronological order (newest at top)
  - Header format: `YYYY-MM-DD | <category>: <title>`
  - Categories: feat, fix, docs, chore
  - Every entry must include:
    - Summary
    - Files Changed
    - Rationale
    - Behavior / Compatibility Implications
    - Testing Recommendations
    - Follow-ups

  ## Response Format for Code Changes
  When you need to create or edit files, use SEARCH/REPLACE blocks.

  Every SEARCH/REPLACE block must start with the relative file path on its own
  line, followed by the markers:

  path/to/file.py
  <<<<<<< SEARCH
  exact existing content to find in the file
  =======
  new content to replace it with
  >>>>>>> REPLACE

  Rules:
  - The SEARCH section must contain an EXACT copy of the existing file content
    you want to change. Copy it character-for-character including whitespace.
  - To CREATE a new file, use an empty SEARCH section.
  - To DELETE content, use an empty REPLACE section.
  - For multiple edits to the same file, use multiple SEARCH/REPLACE blocks.
  - Always include the relative file path so changes can be applied automatically.
  - Keep SEARCH blocks as small as possible — just enough context for a unique match.
  - Order SEARCH/REPLACE blocks from top of file to bottom for multiple edits.

# The agent_name is substituted from settings.yaml at runtime
# This name must never appear in generated code, commits, or changelogs
agent_name_placeholder: "{agent_name}"
```

### 11.2 Prompt Assembly Order

```
1. System prompt (config/system_prompt.yaml)
2. Per-folder agents.md (nearest ancestor)
3. Active skill instructions (SKILL.md body)
4. Uploaded file contents (via API upload)
5. User message
```

---

## 12. Configuration

### 12.1 Settings File

```yaml
# config/settings.yaml (defaults, shipped with package)
# Override at: ~/.genai-cli/settings.yaml (user) or .genai-cli/settings.yaml (project)

# Agent identity (never appears in generated output)
agent_name: "ai-assistant"

# API configuration
api_base_url: ""        # REQUIRED - set during 'genai auth login'
web_ui_url: ""          # REQUIRED - set during 'genai auth login'

# Defaults
default_model: "gpt-5-chat-global"
auto_apply: false
streaming: true
max_agent_rounds: 5
create_backups: true

# Token management
token_warning_threshold: 0.80    # Warn at 80% context usage
token_critical_threshold: 0.95   # Suggest /clear at 95%

# Session
session_dir: "~/.genai-cli/sessions"
max_saved_sessions: 50

# Display
show_token_count: true
show_cost: true
markdown_rendering: true
color_theme: "auto"    # auto | dark | light

# Security
allowed_write_paths: ["."]           # Relative to project root
blocked_write_patterns:
  - "**/.env"
  - "**/*.pem"
  - "**/*.key"
  - "**/*.secret*"
  - "**/credentials*"
```

### 12.2 Config Precedence

```
Highest priority:
  1. CLI flags (--model, --auto-apply, etc.)
  2. Environment variables (GENAI_AUTH_TOKEN, GENAI_MODEL, etc.)
  3. Project config: .genai-cli/settings.yaml
  4. User config: ~/.genai-cli/settings.yaml
  5. Package defaults: config/settings.yaml
Lowest priority
```

### 12.3 Environment Variables

```bash
GENAI_AUTH_TOKEN       # Bearer token (highest priority for auth)
GENAI_API_BASE_URL     # API base URL override
GENAI_MODEL            # Default model override
GENAI_AUTO_APPLY       # true/false
GENAI_VERBOSE          # true/false
```

---

## 13. Authentication

### 13.1 Token Flow

```
genai auth login
  → Prompts: "Paste your Bearer token from browser DevTools"
  → Prompts: "Enter API base URL (e.g. https://api-genai.example.com)"
  → Validates token by calling GET /api/v1/user/usage
  → Stores token in ~/.genai-cli/.env (chmod 600)
  → Stores API URL in ~/.genai-cli/settings.yaml

genai auth verify
  → Loads token from .env
  → Decodes JWT to check expiry (without verification - no secret needed)
  → Calls GET /api/v1/user/usage to confirm validity
  → Shows: email, expiry time, remaining quota
```

### 13.2 Token Storage

```bash
# ~/.genai-cli/.env (permissions: 0600)
GENAI_AUTH_TOKEN=eyJ0eXAiOi...
```

### 13.3 Expiry Handling

- On startup: decode JWT `exp` claim, warn if < 1 hour remaining
- On 401 response: prompt user to refresh token
- Never log or display the token value
- Never include token in error reports or session files

---

## 14. Token Tracking & Context Management

### 14.1 How It Works

```python
# Tracked per session:
# - Cumulative TokensConsumed from API responses
# - Estimated tokens for queued files (via tiktoken)
# - Context window from models.yaml for active model

# Display in REPL status line:
# Context: 12,847 / 128,000 tokens (10%)
```

### 14.2 Context Management Commands

| Threshold | Action |
|-----------|--------|
| < 80% | Normal operation |
| 80-95% | Yellow warning in status bar |
| > 95% | Red warning, suggest `/clear` or `/compact` |
| 100% | Refuse to send, require `/clear` |

`/compact` summarizes the conversation history into a shorter form and
starts a fresh API session with the summary as context.

---

## 15. Makefile & Scripts

### 15.1 Makefile (Thin Wrapper)

```makefile
# All targets delegate to scripts/ for cross-platform compatibility.
# Scripts use /bin/sh (POSIX) - no bash-isms.

.PHONY: help setup test lint format build clean run

help:            ## Show this help
	@sh scripts/help.sh

setup:           ## Create venv and install dependencies
	@sh scripts/setup.sh

test:            ## Run tests
	@sh scripts/test.sh

lint:            ## Run linter (ruff + mypy)
	@sh scripts/lint.sh

format:          ## Format code (ruff format)
	@sh scripts/format.sh

build:           ## Build distribution
	@sh scripts/build.sh

clean:           ## Remove build artifacts
	@sh scripts/clean.sh

run:             ## Run the CLI
	@sh scripts/run.sh
```

### 15.2 Shell Scripts (POSIX sh)

All scripts in `scripts/` use `#!/bin/sh` (not bash) for maximum portability.
They handle venv detection for macOS/Linux (bin/) vs Windows Git Bash (Scripts/).

```sh
#!/bin/sh
# scripts/setup.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Cross-platform venv python detection
if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
else
    VENV_PY="$VENV_DIR/bin/python"
fi

"$VENV_PY" -m pip install --upgrade pip setuptools wheel
"$VENV_PY" -m pip install -e "$PROJECT_ROOT[dev]"
echo "Setup complete. Activate with: source $VENV_DIR/bin/activate"
```

---

## 16. Dependencies

```toml
# pyproject.toml
[project]
name = "genai-cli"
version = "0.1.0"
description = "CLI agent for corporate AI chat"
requires-python = ">=3.10"
dependencies = [
    "click>=8.1",              # CLI framework
    "httpx>=0.27",             # HTTP client (async + sync, HTTP/2)
    "rich>=13.0",              # Terminal formatting, markdown, progress
    "pyyaml>=6.0",             # YAML config and skill definitions
    "python-dotenv>=1.0",      # .env file loading
    "tiktoken>=0.7",           # Token counting (context tracking)
    "jinja2>=3.1",             # Prompt templating
    "nbformat>=5.9",           # Jupyter notebook cell extraction
    "pyjwt>=2.8",              # JWT decode for token expiry check
    "prompt-toolkit>=3.0",     # Interactive REPL with history
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",               # Linter + formatter
    "mypy>=1.10",              # Type checking
    "respx>=0.21",             # httpx mocking for tests
]

[project.scripts]
genai = "genai_cli.cli:main"

[tool.ruff]
target-version = "py310"
line-length = 88
select = ["E", "F", "W", "I", "N", "UP", "S", "B", "A", "C4", "SIM", "TCH"]

[tool.mypy]
python_version = "3.10"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src/genai_cli --cov-report=term-missing"
```

---

## 17. Security

| Concern | Mitigation |
|---------|-----------|
| Token exposure | `.env` file with chmod 600; never logged; never in session files |
| Path traversal | `applier.py` validates all paths are within project root |
| Arbitrary write | `blocked_write_patterns` prevents writing to `.env`, `*.key`, etc. |
| File size | `max_file_size_kb` per type prevents accidental large uploads |
| Network scope | Only `api_base_url` is contacted; no other outbound connections |
| Secrets in bundles | `exclude_patterns` skips `.env`, `*.secret*`, `*.pem`, `*.key` |
| Shell injection | No `os.system()` or `subprocess.run(shell=True)` anywhere |
| Dependency supply chain | Pin exact versions in lock file; minimal dependency set |

---

## 18. Implementation Phases

### Phase 1: Foundation (MVP)

**Goal:** Basic chat works end-to-end from CLI.

| Task | Description | Acceptance Criteria |
|------|-------------|-------------------|
| Project scaffolding | pyproject.toml, src layout, Makefile, scripts/ | `make setup` creates working venv |
| Config module | Load/merge YAML config with precedence | Config loads from all 3 levels |
| Auth module | Token from .env, JWT expiry check | `genai auth login` + `genai auth verify` work |
| API client | HTTP calls to all endpoints | Can list history, get usage |
| File bundler | Bundle 4 file types with markers | Bundles match API upload format |
| Basic CLI | `genai ask`, `genai history`, `genai usage`, `genai models` | One-shot chat works with file upload |
| Display module | Rich markdown rendering, spinners | Responses render cleanly in terminal |
| Streaming | SSE handler with fallback to complete | Tokens stream in real-time |
| Tests | Unit tests for client, bundler, config, auth | `make test` passes, >80% coverage |

### Phase 2: Session & Interactive REPL

**Goal:** Persistent sessions, interactive mode, token tracking.

| Task | Description | Acceptance Criteria |
|------|-------------|-------------------|
| Session manager | Create/resume/list/clear sessions | `/resume`, `/clear`, `/history` work |
| Token tracker | Track context usage per model | Status bar shows token count |
| Interactive REPL | prompt_toolkit-based REPL with /commands | All slash commands work |
| Model switching | `/model` command, YAML model registry | Can switch models mid-conversation |
| `/compact` | Summarize conversation to reduce context | Context usage drops after compact |
| Tests | Session, token tracker, REPL tests | `make test` passes |

### Phase 3: Agent Mode & Applier

**Goal:** AI responses automatically update local files.

| Task | Description | Acceptance Criteria |
|------|-------------|-------------------|
| Response parser | Detect code blocks, diffs, full files | All 3 formats detected correctly |
| File applier | Write/patch files with confirmation | Changes applied, backups created |
| Diff preview | Show colored diff before applying | User sees exact changes |
| Agent loop | Multi-round: upload → prompt → apply → repeat | Agent completes 3-round fix cycle |
| Safety checks | Path validation, git dirty warnings | Blocked paths rejected, dirty warned |
| Tests | Applier, agent loop tests | `make test` passes |

### Phase 4: Skills System

**Goal:** SKILL.md-compatible skills with progressive disclosure.

| Task | Description | Acceptance Criteria |
|------|-------------|-------------------|
| SKILL.md loader | Parse YAML frontmatter + markdown body | All bundled skills load correctly |
| Skill registry | Discover skills from 3 locations | Priority order works |
| Skill executor | Inject skill prompt, handle response | `genai skill review --files src/` works |
| Bundled skills | Ship 14 skills (8 custom + 6 superpowers) | All skills functional |
| Per-folder agents | Discover and merge agents.md | Nearest agents.md applies |
| Custom skills | User skills in ~/.genai-cli/skills/ | Custom skills discoverable |
| `/skill` command | Invoke skills from REPL | `/skill review` works |
| Tests | Loader, registry, executor tests | `make test` passes |

### Phase 5: Multi-Agent (Roadmap)

**Goal:** Up to 4 parallel agents working on different tasks.

| Task | Description | Acceptance Criteria |
|------|-------------|-------------------|
| Agent spawner | Fork N agent loops (threading/asyncio) | 4 agents run concurrently |
| Task splitter | Divide work across agents by directory/skill | Each agent gets distinct scope |
| Result merger | Collect and merge results, resolve conflicts | No conflicting file writes |
| Progress display | Show all agent statuses simultaneously | Rich multi-panel display |
| Orchestrator | Coordinate agents, handle dependencies | Dependent tasks run in order |
| Tests | Multi-agent orchestration tests | `make test` passes |

### Phase 6: Polish

**Goal:** Production-ready CLI experience.

| Task | Description |
|------|-------------|
| Shell completion | Tab completion for bash/zsh/fish |
| Error recovery | Retry with backoff on transient failures |
| Logging | Structured logging to `~/.genai-cli/logs/` |
| Packaging | `pip install genai-cli` from internal PyPI |
| Documentation | README, usage guide, troubleshooting by persona |

---

## 19. CHANGELOG Format

```markdown
# CHANGELOG

All notable changes to this project will be documented in this file.

---

## 2026-02-07 | feat: Initial project scaffolding

### Summary
Set up project structure with CLI framework, API client, and configuration system.

### Files Changed
- `pyproject.toml` - Project metadata and dependencies
- `src/genai_cli/cli.py` - Click CLI entry point
- `src/genai_cli/client.py` - API client
- `src/genai_cli/config.py` - YAML config manager
- `Makefile` - Build commands
- `scripts/setup.sh` - Environment setup

### Rationale
Establish foundation for iterative development with clean separation of concerns.

### Behavior / Compatibility Implications
- Requires Python 3.10+
- Requires network access to corporate AI chat API

### Testing Recommendations
- Run `make setup && make test` to verify installation
- Run `genai auth verify` to confirm API connectivity

### Follow-ups
- [ ] Add streaming support
- [ ] Add file bundler
```

---

## 20. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Exact JSON body for POST create chat | Needed for Phase 1 | Need to capture from browser |
| 2 | Does streaming use SSE or WebSocket | Streaming implementation | Test with curl |
| 3 | API rate limits | Retry/backoff strategy | Test empirically |
| 4 | JWT token lifetime | Expiry warning threshold | Check token `exp` claim |
| 5 | Multi-file upload: one PUT per file or concatenated | Upload strategy | Confirmed: separate per type |
| 6 | Exact model API names | Model registry accuracy | Verify via `/api/v1/user/usage` or history |
| 7 | Steps/agent field in response | Native agent support | Investigate |

---

## 21. Glossary

| Term | Definition |
|------|-----------|
| **Bundle** | Concatenated file contents with `===== FILE: ... =====` markers |
| **Skill** | A SKILL.md-defined capability with prompt template and optional scripts |
| **Agent mode** | Multi-round loop: prompt → response → apply files → re-prompt |
| **Applier** | Module that parses AI responses and writes changes to local files |
| **Session** | A persistent conversation with a unique ID and token history |
| **Context window** | Maximum tokens a model can process (defined in models.yaml) |

---

*End of PRD*
