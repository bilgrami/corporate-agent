# CHANGELOG

All notable changes to this project will be documented in this file.

---

## 2026-02-07 | feat: Phase 4 — Response applier and agent loop

### Summary
Added response parser (detects 3 code formats), file applier with safety checks,
and multi-round agent loop with auto-apply, dry-run, and stop conditions.

### Files Changed
- `src/genai_cli/applier.py` — New: ResponseParser (fenced/diff/FILE:), FileApplier (validate, backup, apply)
- `src/genai_cli/agent.py` — New: AgentLoop with multi-round orchestration
- `src/genai_cli/repl.py` — Modified: agent mode integration, code block parsing on responses
- `src/genai_cli/cli.py` — Modified: --auto-apply, --agent, --max-rounds, --dry-run flags
- `tests/test_applier.py` — 26 tests for parser, applier, security
- `tests/test_agent.py` — 9 tests for agent loop
- `docs/implementation_plans/phase-04-applier-agent/agents.md` — Phase 4 agent doc

### Rationale
Automatic code application is the key value proposition. The parser handles
the 3 most common AI response formats. Safety checks prevent accidental writes
to sensitive files or paths outside the project.

### Behavior / Compatibility Implications
- Responses are now scanned for code blocks in REPL mode
- --auto-apply flag skips confirmation prompts
- --dry-run shows changes without writing files
- .bak backups created before overwrite (configurable)

### Testing Recommendations
- `genai ask "fix" --files src/ --agent --auto-apply` for auto mode
- `genai ask "review" --files src/ --dry-run` for dry run
- `make test` — 206 tests passing

### Follow-ups
- [ ] Skills system with SKILL.md support
- [ ] Multi-agent parallel execution (Phase 6)

---

## 2026-02-07 | feat: Phase 3 — Session management, REPL, and token tracking

### Summary
Added interactive REPL with all slash commands, persistent session management,
and token tracking with color-coded context window status.

### Files Changed
- `src/genai_cli/token_tracker.py` — New: TokenTracker with thresholds, model switching, serialization
- `src/genai_cli/session.py` — New: SessionManager for create/save/load/list/clear/compact sessions
- `src/genai_cli/repl.py` — New: ReplSession with prompt_toolkit, all slash commands
- `src/genai_cli/cli.py` — Modified: default (no subcommand) launches REPL, added `resume` command
- `tests/test_token_tracker.py` — 17 tests for tracking, thresholds, serialization
- `tests/test_session.py` — 16 tests for session CRUD, persistence, pruning
- `tests/test_repl.py` — 26 tests for all slash commands
- `tests/test_cli.py` — Updated for REPL launch behavior
- `docs/implementation_plans/phase-03-session-repl/agents.md` — Phase 3 agent doc

### Rationale
Interactive REPL is the primary interface for developers. Session persistence
enables resuming conversations. Token tracking prevents context window overflow.

### Behavior / Compatibility Implications
- `genai` with no subcommand now launches REPL (previously showed help)
- Sessions saved to ~/.genai-cli/sessions/ as JSON
- Token status: green (<80%), yellow (80-95%), red (>95%)

### Testing Recommendations
- `genai` to launch REPL, try /help, /status, /model, /clear, /quit
- `genai resume <id>` to verify session persistence
- `make test` — 171 tests passing

### Follow-ups
- [ ] Response applier for automatic code changes
- [ ] Agent loop for multi-round interactions
- [ ] Skills system with SKILL.md support

---

## 2026-02-07 | feat: Phase 2 — File bundler and upload integration

### Summary
Added file bundler that discovers, classifies, and bundles files by type
(code/docs/scripts/notebooks) for separate upload to the API. Added
`genai files` preview command and `--files` flag on `genai ask`.

### Files Changed
- `src/genai_cli/bundler.py` — New: FileBundler with classify, discover, bundle, notebook extraction, token estimation
- `src/genai_cli/client.py` — Modified: added upload_bundles() for multi-type upload
- `src/genai_cli/cli.py` — Modified: enhanced `ask` with file bundling/upload, added `files` preview command
- `tests/test_bundler.py` — New: 35 tests for classify, discover, bundle, notebooks, tokens
- `tests/test_streaming.py` — New: 10 tests for SSE parsing, fallback, connection error
- `docs/implementation_plans/phase-02-bundler/agents.md` — Phase 2 agent doc

### Rationale
File context is essential for code review, bug fixing, and all AI-assisted
coding tasks. Bundling per type matches the API's upload format (one PUT per type).

### Behavior / Compatibility Implications
- Files exceeding max_file_size_kb per type are silently skipped
- Binary files auto-detected and excluded
- Exclude patterns from settings.yaml honored
- Notebook cells extracted via nbformat

### Testing Recommendations
- `genai files src/` to preview bundle contents
- `genai ask "review" --files src/ --type code` for upload + chat
- `make test` — 114 tests passing

### Follow-ups
- [ ] Interactive REPL with slash commands
- [ ] Session persistence and token tracking
- [ ] Response applier for automatic code changes
- [ ] Skills system with SKILL.md support

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
