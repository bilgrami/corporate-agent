# CHANGELOG

All notable changes to this project will be documented in this file.

---

## 2026-02-07 | feat: Phase 1 — Project scaffolding, config, auth, API client

### Summary
Set up project structure with CLI framework, YAML configuration system,
JWT-based authentication, HTTP API client, SSE streaming handler, and
rich terminal display. All 11 models registered in YAML config.

### Files Changed
- `pyproject.toml` — Project metadata, dependencies, tool config
- `Makefile` — Thin wrapper delegating to scripts/
- `scripts/*.sh` — POSIX shell scripts for setup, test, lint, format, build, clean
- `config/settings.yaml` — Default settings with file types, exclude patterns, security
- `config/models.yaml` — 11-model registry with context windows and costs
- `config/headers.yaml` — Default HTTP headers for API requests
- `config/system_prompt.yaml` — System prompt with agent_name substitution
- `src/genai_cli/__init__.py` — Package version
- `src/genai_cli/__main__.py` — Module entry point
- `src/genai_cli/models.py` — Data classes (ModelInfo, AppSettings, AuthToken, etc.)
- `src/genai_cli/config.py` — ConfigManager with 5-level precedence merging
- `src/genai_cli/auth.py` — AuthManager with JWT decode, token storage (chmod 600)
- `src/genai_cli/client.py` — GenAIClient for all API endpoints
- `src/genai_cli/streaming.py` — SSE stream parser with fallback
- `src/genai_cli/display.py` — Rich terminal output (tables, markdown, diffs, colors)
- `src/genai_cli/cli.py` — Click CLI: ask, auth login/verify, history, usage, models, config
- `tests/conftest.py` — Shared fixtures
- `tests/test_config.py` — Config loading, precedence, model lookup tests
- `tests/test_auth.py` — Token save/load, JWT decode, expiry, permissions tests
- `tests/test_client.py` — API endpoint tests with respx mocks
- `tests/test_display.py` — Display output verification
- `tests/test_cli.py` — CLI command integration tests

### Rationale
Establish foundation for iterative development with clean separation of concerns.
Each module has a single responsibility. No vendor names in .py files — only in
config YAML as data.

### Behavior / Compatibility Implications
- Requires Python 3.10+
- Requires network access to corporate AI chat API
- Token stored at ~/.genai-cli/.env with chmod 600

### Testing Recommendations
- Run `make setup && make test` to verify installation
- Run `genai auth verify` to confirm API connectivity
- Run `genai models` to verify model registry

### Follow-ups
- [ ] File bundler for code/docs/scripts/notebooks upload
- [ ] Interactive REPL with slash commands
- [ ] Session persistence and token tracking
- [ ] Response applier for automatic code changes
- [ ] Skills system with SKILL.md support
