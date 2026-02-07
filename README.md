# GenAI CLI — Corporate AI Chat Agent

A CLI tool that wraps your corporate multi-model AI chat platform, enabling
file uploads, streaming responses, automatic code changes, and repeatable
skills — all from the terminal.

## Quick Start

```bash
# 1. Install
make setup

# 2. Authenticate
genai auth login
# Paste your Bearer token from browser DevTools
# Enter your API base URL

# 3. Verify
genai auth verify

# 4. Chat
genai ask "explain this code" --files src/
```

## Commands

| Command | Description |
|---------|-------------|
| `genai ask "message"` | Send a one-shot message |
| `genai auth login` | Save your bearer token and API URL |
| `genai auth verify` | Check token validity and API connectivity |
| `genai models` | List all available models |
| `genai history` | List recent conversations |
| `genai usage` | Show token usage |
| `genai config get <key>` | View a config value |
| `genai config set <key> <value>` | Update a config value |

## Global Flags

```
--model, -m       Override model for this invocation
--verbose, -v     Verbose output
--config, -c      Custom config file path
--json-output     Output as JSON
--no-stream       Disable streaming
--version         Show version
```

## Configuration

Settings are loaded with 5-level precedence (highest first):

1. CLI flags (`--model`, `--auto-apply`, etc.)
2. Environment variables (`GENAI_MODEL`, `GENAI_AUTO_APPLY`, etc.)
3. Project config: `.genai-cli/settings.yaml`
4. User config: `~/.genai-cli/settings.yaml`
5. Package defaults: `config/settings.yaml`

## Development

```bash
make setup    # Create venv, install deps
make test     # Run tests with coverage
make lint     # Run ruff + mypy
make format   # Auto-format code
make clean    # Remove build artifacts
```

## FAQ

### For Developers

**Q: How do I get my bearer token?**
A: Open your corporate AI chat in the browser, open DevTools (F12),
go to Network tab, find any API request, and copy the `Authorization`
header value (without the "Bearer " prefix).

**Q: My token expired — what do I do?**
A: Run `genai auth login` again with a fresh token from DevTools.

**Q: How do I switch models?**
A: Use `genai ask "message" --model claude-sonnet-4-5-global` or
`genai config set default_model claude-sonnet-4-5-global`.

### For Team Leads

**Q: Can I share settings across the team?**
A: Yes, commit a `.genai-cli/settings.yaml` to your project repo.
It will be picked up automatically (project-level config, priority 3).

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
never to `.env`, `*.pem`, `*.key`, or credential files.
