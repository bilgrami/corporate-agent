# CHANGELOG

All notable changes to this project will be documented in this file.

---

## 2026-02-08 | feat: Auto-configure from environment variables

### Summary
`scripts/run.sh` now detects `GENAI_AUTH_TOKEN` and `GENAI_API_BASE_URL`
environment variables and auto-saves them to `~/.genai-cli/` config files
before launching the CLI. This enables `source .env && make run` without
manually running `genai auth login`.

### Files Changed
- `scripts/run.sh` — Added env var detection and auto-save logic

---

## 2026-02-08 | fix: Configurable HTTP methods and multi-step request flows

### Summary
Made HTTP methods, content types, and request field mappings fully configurable
per endpoint in `api_format.yaml`. The client now supports multi-step request
flows (e.g. session creation followed by a separate streaming request) with
per-endpoint method and content type overrides. Previously all write operations
were hardcoded to POST with JSON bodies, which broke APIs that expect different
methods or content types.

### Files Changed
- `config/api_format.yaml` — Added `endpoint_methods`, `endpoint_content_types`, `stream_request_fields`, `stream_request_defaults`, and stream endpoint
- `src/genai_cli/mapper.py` — Added `endpoint_method()`, `endpoint_content_type()`, `build_stream_payload()`
- `src/genai_cli/client.py` — `create_chat()` uses configurable HTTP method; `stream_chat()` uses two-step create + stream flow
- `src/genai_cli/streaming.py` — Updated fallback path to use the same two-step flow; auth errors now propagate correctly
- `tests/test_mapper.py` — Tests for new mapper methods
- `tests/test_client.py` — Updated for configurable methods, added two-step flow test
- `tests/test_streaming.py` — Updated fallback tests
- `tests/test_agent.py` — Updated mocks for new stream-based flow
- `tests/test_cli.py` — Updated integration test mocks

### Rationale
Different API platforms use different HTTP methods and content types for the
same logical operations. Hardcoding POST/JSON made the client incompatible with
APIs that require GET for session creation or multipart/form-data for message
submission. All protocol details are now YAML-driven so a different platform
can be supported without code changes.

### Behavior / Compatibility Implications
- Endpoint HTTP methods are now read from `endpoint_methods` config (default: GET)
- `stream_chat()` performs two HTTP requests (session create + stream)
- Non-streaming fallback uses the same two-step flow
- Stream request fields are mapped through `stream_request_fields` config

### Testing Recommendations
- `make test` — 346 tests passing, 83% coverage
- Verify streaming and non-streaming chat modes work end-to-end

---

## 2026-02-07 | feat: YAML-driven ResponseMapper for API format decoupling

### Summary
Introduced a `ResponseMapper` class driven by `config/api_format.yaml` that
translates between any corporate GenAI API's field names and internal snake_case
representations. Supporting a different enterprise AI platform is now a YAML-only
change — no Python code edits needed.

### Files Changed
- `config/api_format.yaml` — New: field mappings, endpoint paths, stream config
- `src/genai_cli/mapper.py` — New: ResponseMapper class + `_resolve_path()` utility
- `src/genai_cli/config.py` — Loads api_format.yaml (3-level merge), adds `mapper` property
- `src/genai_cli/client.py` — Uses mapper for endpoints, payloads, and parse_message
- `src/genai_cli/streaming.py` — Mapper-driven stream parsing (JSON-lines + SSE), extracts
  token metadata from final chunk, returns ChatMessage with token counts
- `src/genai_cli/display.py` — `print_history()` now uses internal field names
- `src/genai_cli/cli.py` — History/usage commands map through mapper before display
- `tests/test_mapper.py` — New: 26 tests for all mapper methods
- `tests/test_streaming.py` — Rewritten: 20 tests for mapper-driven parsing + legacy SSE
- `tests/test_client.py` — Updated parse_message test for instance method
- `tests/test_display.py` — Added history/usage internal field tests

### Rationale
The code previously hardcoded PascalCase field names from one specific corporate API.
This made the tool unusable for any other enterprise AI platform. The ResponseMapper
pattern decouples field name translation into configuration, following the same
3-level precedence (package > user > project) as settings.yaml.

### Behavior / Compatibility Implications
- `parse_message` is now an instance method on GenAIClient (was static)
- Streaming now returns a `ChatMessage` with token counts from the final chunk
  (previously returned `None`, so token tracking was always 0 during streaming)
- `print_history()` expects internal field names; callers must map first
- Custom API formats can be defined in `~/.genai-cli/api_format.yaml` or
  `.genai-cli/api_format.yaml` to override the default

### Testing Recommendations
- `make test` — 335 tests passing, 83% coverage
- To test decoupling: edit field names in api_format.yaml, verify code still works
- With VPN + token: `genai history` shows chat titles and dates (not blank)

---

## 2026-02-07 | feat: /exit and /export commands for REPL

### Summary
Added `/exit` as an alias for `/quit` and `/export [filename]` to export the
current conversation as markdown. When a filename is given the session is written
to that file; otherwise the markdown is copied to the system clipboard.

### Files Changed
- `src/genai_cli/repl.py` — Added `/exit` alias, `_handle_export`, `_format_session_markdown`, `_copy_to_clipboard`; updated command dispatch, completer, and help text
- `tests/test_repl.py` — 8 new tests for exit, export, completer entries

### Rationale
Claude CLI provides `/exit` and `/export` for convenience. `/exit` matches user
expectation for exiting a REPL. `/export` enables saving or sharing conversations
without manually copying terminal output.

### Testing Recommendations
- `make test` — all tests passing
- In REPL: `/exit` saves session and exits
- In REPL: `/export chat.md` writes markdown file
- In REPL: `/export` copies to clipboard (macOS/Linux/Windows)

---

## 2026-02-07 | feat: /rewind command for REPL

### Summary
Added `/rewind [n]` slash command that removes the last N conversation turns
(user + assistant message pairs) and adjusts token tracking accordingly.
Defaults to 1 turn if no argument given.

### Files Changed
- `src/genai_cli/token_tracker.py` — Added `subtract_consumed()` method
- `src/genai_cli/repl.py` — Added `/rewind` to completer, dispatch, help, and handler
- `tests/test_token_tracker.py` — 2 tests for subtract (normal + clamp to zero)
- `tests/test_repl.py` — 5 tests for rewind behavior

### Rationale
Previously the only options for a bad AI response were `/clear` (wipe entire session)
or `/compact` (summarize). `/rewind` gives fine-grained undo without losing earlier context.

### Testing Recommendations
- `make test` — 287 tests passing, 81% coverage
- In REPL: send a message, then `/rewind` to verify it's removed

---

## 2026-02-07 | feat: Phase 6 — SEARCH/REPLACE block parser with error feedback

### Summary
Replaced fragile regex-based ResponseParser with a robust SEARCH/REPLACE block
parser using Aider-style git-conflict markers. Old parsers kept as fallback.
Agent loop now feeds back actual file content when edits fail, enabling AI
self-correction. Three-tier matching (exact, whitespace-normalized,
indent-normalized) handles common LLM quoting errors.

### Files Changed
- `src/genai_cli/applier.py` -- Added SearchReplaceParser (state-machine),
  UnifiedParser (orchestrator), EditBlock, ApplyResult; kept ResponseParser as
  fallback; added apply_edits() with 3-tier matching
- `src/genai_cli/agent.py` -- Updated to use UnifiedParser, added error
  feedback in next-round messages via _build_feedback_message(), added
  failed_edits tracking to RoundResult/AgentResult
- `src/genai_cli/repl.py` -- Updated _send_message() to use UnifiedParser
- `config/system_prompt.yaml` -- Replaced code format instructions with
  SEARCH/REPLACE block specification
- `tests/test_search_replace.py` -- New: 36 tests for parser, matching, apply
- `tests/test_agent.py` -- Added 5 tests for error feedback and SR parsing
- `tests/test_applier.py` -- Updated for new ApplyResult return type
- `docs/PRD.md` -- Updated Sections 9.2 and 11.1
- `docs/TDD.md` -- New: technical design document for SEARCH/REPLACE system
- `docs/CONTRIBUTING.md` -- Added applier architecture section
- `docs/Architecture.md` -- Updated module responsibilities
- `AGENTS.md` -- Updated dependency graph

### Rationale
The regex-based parser was fragile: fenced patterns failed on nested code blocks,
unified diff parsing did not verify context lines, and the FILE: marker had
false-positive issues. SEARCH/REPLACE blocks use unambiguous git-conflict markers
that LLMs produce reliably, support surgical edits without repeating entire files,
and are self-validating (SEARCH content must exist in the file).

### Behavior / Compatibility Implications
- SEARCH/REPLACE is now the primary format; old formats still work as fallback
- Agent loop now provides error feedback when edits fail (previously silent)
- `apply_all()` return type changed from `list[str]` to `list[ApplyResult]`

### Testing Recommendations
- `make test` -- 280 tests passing, 81% coverage
- Test with AI responses containing SEARCH/REPLACE blocks
- Test fallback: send response with old fenced format, verify it still works
- Test error feedback: send SEARCH block with wrong content, verify AI gets
  actual file content in next round

### Follow-ups
- [ ] Diff preview for SEARCH/REPLACE blocks in confirm mode
- [ ] File rename/move operations
- [ ] Multi-agent parallel execution (Phase 7)

---

## 2026-02-07 | feat: Slash command autocomplete in REPL

### Summary
Added tab-completion for all 18 slash commands in the interactive REPL.
Typing `/` and pressing Tab shows all commands with descriptions. Commands
that accept arguments (`/model`, `/skill`, `/auto-apply`, `/files`, `/resume`)
provide context-aware sub-completions (model names, skill names, file paths, etc.).

### Files Changed
- `src/genai_cli/repl.py` — Added `SlashCompleter` class using prompt_toolkit's `Completer`; wired into `PromptSession`
- `tests/test_repl.py` — Added `TestSlashCompleter` with 6 tests

### Rationale
Users had to memorize commands or type `/help`. Autocomplete matches the
experience of Claude Code and other modern CLI tools.

### Testing Recommendations
- `make test` — 275 tests passing, 81% coverage
- Launch `genai` REPL, type `/` then Tab to verify completions appear

---

## 2026-02-07 | fix+docs: Code cleanup and documentation improvements

### Summary
Removed dead code, unused imports, stale placeholder labels, duplicate config key,
and orphan files. Rewrote README with full feature coverage (REPL, skills, agent mode,
sessions, file handling). Added Architecture.md and CONTRIBUTING.md. Enhanced AGENTS.md
with dependency graph and developer workflows.

### Files Changed
- `src/genai_cli/cli.py` -- Removed dead no-op statement in skill_list
- `src/genai_cli/applier.py` -- Removed unused imports (difflib, os, Any) and dead hunk-parsing loop
- `src/genai_cli/repl.py` -- Removed stale "(placeholder)" from skill help text
- `config/models.yaml` -- Removed duplicate default_model key
- `test_out.py` -- Deleted orphan debug file
- `README.md` -- Full rewrite: prerequisites, REPL guide, 14 skills, agent mode, sessions, troubleshooting
- `AGENTS.md` -- Enhanced: module dependency graph, skill development guide, dev workflows, test patterns
- `docs/Architecture.md` -- New: component diagram, data flows, design decisions, security architecture
- `docs/CONTRIBUTING.md` -- New: dev setup, testing conventions, feature guides, code style

### Rationale
The README was missing documentation for the primary interface (REPL), skills system,
agent mode, and session management. Code contained dead code and stale labels from
iterative development. Developer docs referenced by PRD did not exist.

### Testing Recommendations
- `make test` -- 233 tests passing, 81% coverage (unchanged)
- Review README for accuracy against actual CLI commands

---

## 2026-02-07 | feat: Phase 5 — Skills system

### Summary
Added SKILL.md-based skills system with 14 bundled skills, 3-location discovery
(project > user > bundled), progressive 3-tier loading, and full CLI/REPL integration.

### Files Changed
- `src/genai_cli/skills/__init__.py` — New: package exports
- `src/genai_cli/skills/loader.py` — New: SkillLoader with YAML frontmatter, Tier 1/2/3 loading
- `src/genai_cli/skills/registry.py` — New: SkillRegistry with 3-location discovery, agents.md walk-up
- `src/genai_cli/skills/executor.py` — New: SkillExecutor assembles prompt and runs AgentLoop
- `skills/` — 14 bundled SKILL.md files (review, fix, refactor, explain, test-gen, doc-gen, commit-msg, security-audit, systematic-debugging, test-driven-development, writing-plans, executing-plans, requesting-code-review, brainstorming)
- `src/genai_cli/cli.py` — Modified: added `skill list` and `skill invoke` commands
- `src/genai_cli/repl.py` — Modified: `/skill` and `/skills` now use real SkillRegistry/SkillExecutor
- `pyproject.toml` — Modified: added pythonpath for pytest (Python 3.14 compatibility)
- `tests/test_skill_loader.py` — 12 tests for frontmatter parsing, tiers, all 14 bundled skills
- `tests/test_skill_registry.py` — 10 tests for discovery, priority, agents.md walk-up
- `tests/test_skill_executor.py` — 6 tests for execution, prompt assembly, modes

### Rationale
Skills provide repeatable AI workflows with consistent prompts. The SKILL.md format
is human-readable and extensible. Progressive loading keeps token usage low until
a skill is actually invoked.

### Behavior / Compatibility Implications
- `genai skill list` shows all discovered skills
- `genai skill invoke <name> --files src/` executes a skill
- `/skills` and `/skill <name>` work in REPL
- Custom skills in `.genai-cli/skills/` or `~/.genai-cli/skills/` override bundled

### Testing Recommendations
- `genai skill list` to verify all 14 skills discovered
- `genai skill invoke review --files src/` to test execution
- `make test` — 233 tests passing, 81% coverage

### Follow-ups
- [ ] Multi-agent parallel execution (Phase 6)
- [ ] Shell completion for skill names
- [ ] Skill parameter validation

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
