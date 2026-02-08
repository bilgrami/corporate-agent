# Agent Instructions

## Project Overview

This is `genai-cli`, a Python CLI tool that wraps a corporate multi-model AI
chat platform. It provides file uploads, streaming responses, automatic code
application, and a skills system -- all from the terminal.

## Architecture

- **src/genai_cli/** -- Main package
- **config/** -- YAML configuration (settings, models, headers, system prompt)
- **scripts/** -- POSIX shell scripts for make targets
- **skills/** -- 14 bundled SKILL.md files
- **tests/** -- pytest test suite with respx HTTP mocks

## Module Dependency Graph

```
cli.py
  -> repl.py (default, no subcommand)
  -> client.py, auth.py, config.py, display.py, streaming.py
  -> bundler.py (file commands)
  -> skills/registry.py, skills/executor.py (skill commands)

repl.py
  -> client.py, auth.py, config.py, display.py, streaming.py
  -> bundler.py, session.py, token_tracker.py
  -> applier.py (response parsing)
  -> agent.py (/agent mode)
  -> skills/registry.py, skills/executor.py (/skill, /skills)

agent.py
  -> client.py, config.py, display.py, streaming.py
  -> bundler.py, session.py, token_tracker.py
  -> applier.py (ResponseParser, FileApplier)

skills/executor.py -> agent.py, auth.py, client.py, config.py, display.py
skills/registry.py -> skills/loader.py, config.py
skills/loader.py   -> (standalone: yaml + re only)

config.py          -> models.py
client.py          -> config.py, auth.py, models.py
session.py         -> config.py, models.py
token_tracker.py   -> config.py, models.py
bundler.py         -> config.py, models.py
applier.py         -> config.py, display.py
  Classes: SearchReplaceParser, UnifiedParser, ResponseParser, FileApplier
  Data: EditBlock, CodeBlock, ApplyResult
display.py         -> models.py
streaming.py       -> client.py, config.py, models.py, display.py
models.py          -> (no internal deps, pure data classes)
```

## Conventions

- Python 3.10+, type hints on all public functions
- No vendor names in .py files -- only in `config/models.yaml`
- `ruff` for linting/formatting, `mypy --strict` for type checking
- All HTTP mocked with `respx` -- no real network calls in tests
- POSIX `#!/bin/sh` scripts -- no bash-isms
- Security: `.env` chmod 600, path traversal blocked, secrets never logged

## Testing

- `make test` runs pytest with coverage
- >80% coverage target per module
- Every source module has a corresponding `tests/test_<module>.py`
- 233 tests currently passing

### Test Fixtures (tests/conftest.py)

| Fixture | Description |
|---------|-------------|
| `project_root` | Path to the actual project root |
| `config_dir` | Path to config/ directory |
| `mock_config` | ConfigManager with test overrides using tmp_path |
| `mock_auth_token` | Valid JWT with 1-hour expiry |
| `expired_auth_token` | Expired JWT |
| `mock_chat_response` | Standard API response dict |
| `mock_models` | Dict of ModelInfo objects |
| `sample_python_file` | Single .py file in tmp_path |
| `sample_project_dir` | Full project structure in tmp_path |

### Testing Patterns

- **HTTP mocking**: Use `respx` (not requests-mock). See `tests/test_client.py`
- **Display capture**: Pass `Display(file=StringIO())` to capture output
- **CLI integration**: Use `click.testing.CliRunner` for CLI commands
- **File operations**: Use `tmp_path` fixture for safe file creation/modification
- **Auth context**: Use `patch.dict("os.environ", {...})` for token injection

## Key Decisions

- Click for CLI framework (subcommands, flags, help generation)
- httpx for HTTP (sync client, HTTP/2 support)
- rich for terminal display (markdown, tables, progress)
- YAML for all configuration (human-editable, no code changes for model updates)
- JWT decoded without verification (no secret needed, just expiry check)
- SKILL.md format for skills (markdown with YAML frontmatter)

## How to Add a New Skill

1. Create directory: `skills/<skill-name>/`
2. Create `SKILL.md` with YAML frontmatter:
   ```markdown
   ---
   name: skill-name
   description: >
     One-line description of what the skill does.
   metadata:
     author: your-name
     version: "1.0"
     category: development
   ---

   # Skill Title

   Instructions for the AI go here in markdown.
   ```
3. Optional: add `references/` directory for supplementary files
4. Test: `genai skill list` (should show new skill)
5. Test: `genai skill invoke <name> --files <path> --dry-run`

Priority: project `.genai-cli/skills/` > user `~/.genai-cli/skills/` > bundled `skills/`

## Common Development Workflows

### Adding a new CLI command

1. Add Click command in `src/genai_cli/cli.py`
2. Add REPL slash command handler in `src/genai_cli/repl.py`
3. Update `_handle_help()` text in `repl.py`
4. Add tests in `tests/test_cli.py` and `tests/test_repl.py`
5. Update README.md command tables

### Adding a new config setting

1. Add field to `AppSettings` in `src/genai_cli/models.py`
2. Add default in `config/settings.yaml`
3. Add merge logic in `ConfigManager.settings` property (`config.py`)
4. Add test in `tests/test_config.py`

### Adding a new API endpoint

1. Add method to `GenAIClient` in `src/genai_cli/client.py`
2. Mock with respx in `tests/test_client.py`
3. Wire into CLI/REPL as needed
