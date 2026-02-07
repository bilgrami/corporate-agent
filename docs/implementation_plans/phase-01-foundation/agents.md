# Phase 1: Foundation — Agent Instructions

## Task
Build the project scaffolding, configuration system, authentication,
API client, streaming handler, terminal display, and CLI commands.

## Purpose
Establish a working foundation where `make setup && make test` passes
and `genai ask "hello"` sends a message to the corporate API.

## Description
Phase 1 creates ~35 files covering:
- Package setup (pyproject.toml, src layout, entry points)
- Build tooling (Makefile, scripts/*.sh)
- Configuration (4 YAML files, ConfigManager with 5-level precedence)
- Authentication (JWT decode, token storage with chmod 600)
- HTTP client (all API endpoints from PRD section 3.2)
- SSE streaming (parse data lines, handle [DONE], fallback)
- Terminal display (rich markdown, tables, colored diffs, spinners)
- CLI commands (ask, auth login/verify, history, usage, models, config)
- Tests (conftest fixtures, test files for each module)

## Acceptance Criteria
- `make setup` creates .venv, installs all deps, exits 0
- `make test` runs pytest, all pass, >80% coverage on config/auth/client/display
- `genai --help` shows all commands
- `genai models` prints table of all 11 models
- `genai auth login` prompts for token + URL, saves to ~/.genai-cli/.env
- `genai auth verify` decodes JWT, shows email/expiry
- `genai ask "hello" --no-stream` sends message, prints AI response
- No vendor names in any .py file
- Config precedence: CLI > env > project > user > package

## Assumptions
- Python 3.10+ available
- No real API access needed for tests (all mocked with respx)
- Corporate AI chat API follows the schema in PRD section 3

## Rationale
Starting with config + auth + client gives a solid foundation. Every
subsequent phase (bundler, session, applier, skills) depends on these
modules being correct and well-tested.

## Testing Criteria
- 12-15 config tests: load, merge, precedence, model lookup, system prompt
- 10-12 auth tests: save/load, permissions, JWT decode, expiry
- 12-15 client tests: all endpoints mocked, 401 handling, headers
- 8-10 display tests: output capture, markdown, tables, colors
- 8-10 CLI tests: all commands via CliRunner
