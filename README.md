# GenAI CLI -- Corporate AI Chat Agent

A CLI tool that wraps your corporate multi-model AI chat platform, enabling
file uploads, streaming responses, automatic code changes, and repeatable
skills -- all from the terminal. All traffic stays on your corporate network.

## Prerequisites

- Python 3.10 or later
- Access to your corporate AI chat platform (network)
- A bearer token from the platform's web UI (see Authentication below)

## Installation

```bash
make setup
```

This creates a virtual environment, installs all dependencies, and makes the
`genai` command available.

## Authentication

### 1. Get Your Token

1. Open your corporate AI chat in the browser
2. Open DevTools (F12 or Cmd+Option+I)
3. Go to the **Network** tab
4. Send any message in the chat
5. Click any API request, find the `Authorization` header
6. Copy the token value (without the "Bearer " prefix)

### 2. Save Your Credentials

```bash
genai auth login
# Paste your bearer token when prompted
# Enter your API base URL (e.g. https://api-genai.example.com)
# Enter your Web UI URL (e.g. https://genai.example.com)
```

Your token is stored at `~/.genai-cli/.env` with permissions `0600`
(owner read/write only). It is never logged or included in session files.

### 3. Verify

```bash
genai auth verify
```

Shows your email, token expiry, and verifies API connectivity.

## Interactive REPL (Primary Interface)

Running `genai` with no arguments launches an interactive REPL:

```bash
genai
```

### Example Session

```
Welcome to GenAI CLI v0.1.0
Model: GPT-5 | Context: 128,000 tokens

You> /files src/main.py
  code: 1 files (~120 tokens)
You> find and fix any bugs in this code
Assistant> I found a potential issue...
  ```python:src/main.py
  ...fixed code...
  ```
  Apply changes? [Y]es / [n]o / [d]iff / [a]ll: y
  Applied: src/main.py
You> /model claude-sonnet-4-5-global
  Switched to Claude Sonnet 4.5 (200,000 context)
You> /usage
  Tokens: 1,234 / 128,000 (1.0%)
You> /quit
  Session saved: a1b2c3d4...
```

### REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/model [name]` | Show current model or switch model |
| `/models` | List all available models |
| `/files <paths>` | Queue files for next message |
| `/clear` | Clear session, start fresh |
| `/fresh` | Alias for `/clear` |
| `/compact` | Summarize conversation to reduce tokens |
| `/history` | List saved sessions |
| `/resume <id>` | Resume a saved session |
| `/usage` | Show token usage and cost |
| `/status` | Show session status (model, messages, tokens) |
| `/config [k] [v]` | View or update settings |
| `/auto-apply [on\|off]` | Toggle auto-apply mode |
| `/agent [rounds]` | Enable agent mode for next message |
| `/skill <name>` | Invoke a skill |
| `/skills` | List available skills |
| `/quit` | Save session and exit |

## One-Shot Commands

Send a single message without entering the REPL:

```bash
genai ask "explain this code" --files src/main.py
genai ask "review this" --files src/ --type code
genai ask "fix all bugs" --files src/ --agent --auto-apply
genai ask "refactor" --files src/ --dry-run
```

### Flags for `genai ask`

| Flag | Description |
|------|-------------|
| `--files, -f` | Files or directories to include |
| `--type, -t` | File type filter: `code\|docs\|scripts\|notebooks\|all` |
| `--no-stream` | Disable streaming (wait for full response) |
| `--auto-apply` | Automatically apply code changes without confirmation |
| `--agent` | Enable multi-round agent mode |
| `--max-rounds` | Max agent loop iterations (default: 5) |
| `--dry-run` | Show changes without applying |

## Skills System

Skills are pre-built AI workflows with consistent prompts for common tasks.

### List Available Skills

```bash
genai skill list       # CLI
/skills                # REPL
```

### Bundled Skills (14)

| Skill | Description |
|-------|-------------|
| `review` | Code review for bugs, security, performance, style |
| `fix` | Find and fix bugs, output as code blocks |
| `refactor` | Improve readability, DRY, decomposition |
| `explain` | Walk through code logic step by step |
| `test-gen` | Generate pytest tests with edge cases |
| `doc-gen` | Generate documentation and docstrings |
| `commit-msg` | Generate commit message from diff |
| `security-audit` | Security-focused review (OWASP top 10) |
| `systematic-debugging` | 4-phase root cause analysis |
| `test-driven-development` | RED-GREEN-REFACTOR methodology |
| `writing-plans` | Create implementation plans |
| `executing-plans` | Execute plans step by step |
| `requesting-code-review` | Pre-merge review process |
| `brainstorming` | Design ideation methodology |

### Invoke a Skill

```bash
# CLI
genai skill invoke review --files src/
genai skill invoke fix --files src/broken.py --auto-apply
genai skill invoke explain --files src/complex.py

# REPL
/files src/
/skill review
```

### Custom Skills

Place custom skills in either location (higher priority first):

1. `.genai-cli/skills/<name>/SKILL.md` (project-level)
2. `~/.genai-cli/skills/<name>/SKILL.md` (user-level)

A custom skill with the same name as a bundled skill overrides it.

## Agent Mode

Agent mode runs multi-round interactions: the AI reads your code, suggests
changes, applies them, then re-reads to verify -- repeating until done.

```bash
# CLI
genai ask "fix all bugs" --files src/ --agent --auto-apply --max-rounds 5

# REPL
/agent 5
fix all bugs in this codebase
```

### Apply Modes

- **Confirm** (default): shows diff, prompts `[Y]es / [n]o / [d]iff / [a]ll` per file
- **Auto-apply** (`--auto-apply`): applies all changes, shows summary
- **Dry-run** (`--dry-run`): shows diffs without modifying any files

### Stop Conditions

- No actionable items in response
- Max rounds reached
- Token usage exceeds 95% of context window
- User cancels (Ctrl+C)

## File Handling

### Bundling and Upload

Files are classified into 4 types and uploaded separately:

| Type | Extensions | Max Size |
|------|-----------|----------|
| code | `.py .js .ts .tsx .java .go .rs .cpp .c .h .rb .sql .scala .kt .swift .r .cs` | 500 KB |
| docs | `.md .txt .rst .yaml .yml .toml .json .xml .csv .cfg .ini .properties` | 500 KB |
| scripts | `.sh .bash .zsh .ps1 .bat .cmd` + `Makefile`, `Dockerfile`, `Jenkinsfile` | 200 KB |
| notebooks | `.ipynb` | 1000 KB |

### Preview Before Upload

```bash
genai files src/ docs/
```

### Automatic Exclusions

These patterns are excluded from bundling: `__pycache__/`, `.git/`,
`node_modules/`, `.venv/`, `.env`, `*.secret*`, `*.pem`, `*.key`,
`dist/`, `build/`, `.pytest_cache/`, `*.pyc`

## Session Management

Sessions persist automatically so you can resume conversations.

```bash
# Save and exit (in REPL)
/quit

# List saved sessions
genai history --limit 10
/history                     # in REPL

# Resume a session
genai resume <session_id>
/resume <session_id>         # in REPL

# Start fresh
/clear                       # in REPL

# Compact (summarize to save tokens)
/compact                     # in REPL
```

Sessions are stored in `~/.genai-cli/sessions/` as JSON files.

## Token Tracking

Token usage is displayed after each message with color-coded status:

- **Green** (<80%): normal usage
- **Yellow** (80-95%): approaching context limit
- **Red** (>95%): near limit, consider `/compact` or `/clear`

```
/usage    # Show current token usage and estimated cost
/status   # Show session info including tokens
```

## All CLI Commands

| Command | Description |
|---------|-------------|
| `genai` | Launch interactive REPL |
| `genai ask "message"` | Send a one-shot message |
| `genai auth login` | Save bearer token and API URL |
| `genai auth verify` | Check token validity and API connection |
| `genai models` | List all available models |
| `genai history` | List recent conversations |
| `genai usage` | Show token usage |
| `genai config get <key>` | View a config value |
| `genai config set <key> <value>` | Update a config value |
| `genai files <paths>` | Preview file bundles |
| `genai resume <session_id>` | Resume a saved conversation |
| `genai skill list` | List all available skills |
| `genai skill invoke <name>` | Invoke a skill by name |

## Global Flags

| Flag | Description |
|------|-------------|
| `--model, -m` | Override model for this invocation |
| `--verbose, -v` | Verbose output |
| `--config, -c` | Custom config file path |
| `--json-output` | Output as JSON |
| `--version` | Show version |

## Configuration

Settings are loaded with 5-level precedence (highest first):

1. CLI flags (`--model`, `--auto-apply`, etc.)
2. Environment variables (`GENAI_AUTH_TOKEN`, `GENAI_API_BASE_URL`, etc.)
3. Project config: `.genai-cli/settings.yaml`
4. User config: `~/.genai-cli/settings.yaml`
5. Package defaults: `config/settings.yaml`

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `default_model` | `gpt-5-chat-global` | Model to use |
| `auto_apply` | `false` | Auto-apply code changes |
| `streaming` | `true` | Stream responses |
| `max_agent_rounds` | `5` | Max agent loop iterations |
| `create_backups` | `true` | Create `.bak` before overwrite |
| `token_warning_threshold` | `0.80` | Yellow warning at 80% |
| `token_critical_threshold` | `0.95` | Red warning at 95% |
| `show_cost` | `true` | Show estimated costs |

## Development

```bash
make setup    # Create venv, install deps
make test     # Run tests with coverage (233 tests, 81% coverage)
make lint     # Run ruff + mypy
make format   # Auto-format code
make clean    # Remove build artifacts
```

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed development workflow.

## FAQ

### For Developers

**Q: How do I get my bearer token?**
A: Open your corporate AI chat in the browser, open DevTools (F12),
go to Network tab, find any API request, and copy the `Authorization`
header value (without the "Bearer " prefix).

**Q: My token expired -- what do I do?**
A: Run `genai auth login` again with a fresh token from DevTools.

**Q: How do I switch models?**
A: Use `--model` flag: `genai ask "message" --model claude-sonnet-4-5-global`,
or in REPL: `/model claude-sonnet-4-5-global`,
or permanently: `genai config set default_model claude-sonnet-4-5-global`.

**Q: How do I use agent mode?**
A: Add `--agent` to auto-iterate: `genai ask "fix bugs" --files src/ --agent`.
In REPL: `/agent 5` then type your message.

**Q: How do I add custom skills?**
A: Create `.genai-cli/skills/<name>/SKILL.md` in your project with YAML
frontmatter and markdown instructions. See `skills/review/SKILL.md` for format.

**Q: How do I resume a conversation?**
A: Run `genai history` to see saved sessions, then `genai resume <id>`.

### For Team Leads

**Q: Can I share settings across the team?**
A: Yes, commit a `.genai-cli/settings.yaml` to your project repo.
It will be picked up automatically (project-level config, priority 3).

**Q: Can I share custom skills?**
A: Yes, commit a `.genai-cli/skills/` directory in your project repo.
Team members get them automatically.

**Q: Is my token safe?**
A: Tokens are stored in `~/.genai-cli/.env` with permissions `0600`
(owner read/write only). Tokens are never logged or included in
session files.

### For Security Teams

**Q: What network calls does this tool make?**
A: Only to the configured `api_base_url` (your corporate AI chat API).
No external APIs, telemetry, or analytics.

**Q: What files can the agent write to?**
A: Constrained by `allowed_write_paths` and `blocked_write_patterns`
in settings. By default, only the current project directory, and
never to `.env`, `*.pem`, `*.key`, or credential files. Path traversal
(`../`) is rejected.

## Troubleshooting

**Token expired**: Run `genai auth login` with a fresh token from DevTools.

**Connection refused**: Verify `api_base_url` is correct. Check VPN connection.
Run `genai auth verify` to test connectivity.

**No skills found**: Ensure the `skills/` directory exists at the project root
with SKILL.md files inside subdirectories.

**Context window full**: Use `/compact` to summarize the conversation, or
`/clear` to start fresh.

**File not bundled**: Check `exclude_patterns` in settings. Verify the file
is under the size limit for its type. Binary files are automatically excluded.

**Changes not applied**: Ensure the file path in the AI response matches a
real path relative to your project root. Check `blocked_write_patterns`.
