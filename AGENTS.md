# Agent Instructions

## Project Overview
This is `genai-cli`, a Python CLI tool that wraps a corporate multi-model AI
chat platform. It provides file uploads, streaming responses, automatic code
application, and a skills system.

## Architecture
- **src/genai_cli/** — Main package (models, config, auth, client, streaming,
  display, cli, bundler, applier, agent, session, token_tracker, skills/)
- **config/** — YAML configuration (settings, models, headers, system prompt)
- **scripts/** — POSIX shell scripts for make targets
- **skills/** — Bundled SKILL.md files
- **tests/** — pytest test suite with respx HTTP mocks

## Conventions
- Python 3.10+, type hints on all public functions
- No vendor names in .py files — only in config/models.yaml
- `ruff` for linting/formatting, `mypy --strict` for type checking
- All HTTP mocked with `respx` — no real network calls in tests
- POSIX `#!/bin/sh` scripts — no bash-isms
- Security: .env chmod 600, path traversal blocked, secrets never logged

## Testing
- `make test` runs pytest with coverage
- >80% coverage target per module
- Every source module has a corresponding test file

## Key Decisions
- Click for CLI framework (subcommands, flags, help generation)
- httpx for HTTP (sync client, HTTP/2 support)
- rich for terminal display (markdown, tables, progress)
- YAML for all configuration (human-editable, no code changes for model updates)
- JWT decoded without verification (no secret needed, just expiry check)
