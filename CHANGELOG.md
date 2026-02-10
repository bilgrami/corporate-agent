# CHANGELOG

All notable changes to this project will be documented in this file.

---

## 2026-02-10 | feat: Add prompt profile switching and bundled prompt registry

### Summary
Added active prompt profile switching to ConfigManager and a prompt registry/loader
system with 5 bundled prompt profiles (default, code-changes, reviewer, planner,
minimal). Users can switch system prompts via `/prompt <name>` in the REPL or
`--prompt` on the CLI.

### Files Changed

**New modules (3):**
- `src/genai_cli/prompts/__init__.py` — Prompt registry package exports
- `src/genai_cli/prompts/loader.py` — Prompt loader with YAML frontmatter parsing
- `src/genai_cli/prompts/registry.py` — Prompt registry with 3-location discovery (project > user > bundled)

**New prompt profiles (5):**
- `prompts/default/PROMPT.md` — Default general-purpose system prompt
- `prompts/code-changes/PROMPT.md` — Code changes focused prompt
- `prompts/reviewer/PROMPT.md` — Code review focused prompt
- `prompts/planner/PROMPT.md` — Planning and architecture prompt
- `prompts/minimal/PROMPT.md` — Minimal, concise prompt

**Modified files (2):**
- `src/genai_cli/config.py` — Added `_active_prompt_name`, `_active_prompt_body`, `set_active_prompt()`, `clear_active_prompt()`, `active_prompt_name` property, and updated `get_system_prompt()` to return active prompt if set
- `tests/test_config.py` — Added 4 tests for active prompt switching (set, clear, default fallback, property)

### Rationale
The prompt profiles system lets users tailor the AI's behavior for different tasks
(reviewing, planning, coding) without manually editing config files. The registry
uses the same 3-location discovery pattern as the skills system, and the config-level
switching integrates cleanly with the existing `get_system_prompt()` API.

### Behavior / Compatibility Implications
- `get_system_prompt()` now returns the active prompt body if one is set, otherwise falls back to the default system prompt from config
- `set_active_prompt(name, body)` and `clear_active_prompt()` are new methods on ConfigManager
- `active_prompt_name` is a new read-only property on ConfigManager
- No changes to existing behavior when no active prompt is set

### Testing Recommendations
- `make test` — 4 new tests for active prompt switching should pass alongside existing tests
- `genai prompt list` — shows all 5 bundled prompts
- `genai prompt show default` — renders full prompt body

### Follow-ups
- [ ] Add `/prompt` REPL command for interactive switching
- [ ] Add `--prompt` CLI flag to `genai ask`
- [ ] Prompt composition — combine multiple profiles

---

## 2026-02-10 | feat: Add repo-split and refactoring capabilities

### Summary
Added AST-based dependency analysis, git operations management, smart context
chunking, multi-repo workspace management, and a refactoring engine for module
and symbol moves with automatic import rewriting. Includes 3 new skills
(repo-split, dependency-map, migrate-module), new REPL commands (/analyze,
/workspace, /split), new CLI commands (genai analyze, genai workspace), and
full documentation of capabilities and limitations.

Zero new external dependencies — everything uses Python stdlib (ast, graphlib,
pathlib, subprocess).

### Files Changed

**New modules (5):**
- `src/genai_cli/analyzer.py` — AST-based dependency analyzer with cycle detection, module classification, and clustering
- `src/genai_cli/git_ops.py` — Safe git CLI wrapper (init, add, commit, branch, mv, rm, checkpoint, rollback)
- `src/genai_cli/chunker.py` — Smart context chunker with file prioritization and greedy bin-packing
- `src/genai_cli/workspace.py` — Multi-repo workspace manager with cross-repo file moves
- `src/genai_cli/refactor_ops.py` — Refactoring engine for module/symbol moves with import rewriting

**New tests (5):**
- `tests/test_analyzer.py` — 22 tests across 10 test classes
- `tests/test_git_ops.py` — 17 tests across 6 test classes
- `tests/test_chunker.py` — 11 tests across 5 test classes
- `tests/test_workspace.py` — 14 tests across 5 test classes
- `tests/test_refactor_ops.py` — 10 tests across 6 test classes

**New skills (3):**
- `skills/repo-split/SKILL.md` — Guided monorepo splitting workflow (category: architecture)
- `skills/dependency-map/SKILL.md` — Dependency analysis and visualization (category: analysis)
- `skills/migrate-module/SKILL.md` — Module/symbol migration with import rewriting (category: refactoring)

**New documentation (1):**
- `docs/capabilities.md` — Model support matrix, capabilities, limitations, and repo-split guide

**Modified files (4):**
- `src/genai_cli/models.py` — Added `workspace_dir` field to AppSettings
- `src/genai_cli/repl.py` — Added /analyze, /workspace, /split commands with handlers and tab completion
- `src/genai_cli/cli.py` — Added `genai analyze` command and `genai workspace` command group (init, add, list, switch)
- `README.md` — Added new commands to tables, 3 new skills, Capabilities & Limitations section, Code Analysis & Refactoring section, Multi-Repo Workspaces section

### Rationale
Users need to split monorepos and refactor code across repositories. This
requires understanding dependency graphs, managing git operations safely,
fitting large codebases into AI context windows, and tracking multiple repos
as a unified workspace. All five modules are designed with clear dependency
layering: analyzer and git_ops have no internal deps, chunker depends on
analyzer and bundler, workspace depends on analyzer and git_ops, and
refactor_ops depends on all above plus applier.

### Behavior / Compatibility Implications
- `workspace_dir` is a new optional field on AppSettings (default: empty string)
- `/analyze`, `/workspace`, `/split` are new REPL commands — no impact on existing commands
- `genai analyze` and `genai workspace` are new CLI commands — no impact on existing commands
- 3 new bundled skills are auto-discovered alongside existing 14 skills
- No new external dependencies

### Testing Recommendations
- `make test` — 74 new tests across 5 test files should pass alongside existing tests
- `genai analyze src/` — should print dependency report
- `/analyze src/genai_cli/` in REPL — same via REPL command
- `genai analyze src/ --format json --output /tmp/deps.json` — JSON output
- `/workspace add main .` then `/workspace list` — workspace management
- `/skills` should list 3 new skills (repo-split, dependency-map, migrate-module)

### Follow-ups
- [ ] Add cross-language dependency analysis (JavaScript/TypeScript)
- [ ] Add merge/rebase support to git_ops
- [ ] Add test verification step after refactoring

---

## 2026-02-09 | feat: Add /bundle command and SEARCH/REPLACE to missing prompts

### Summary
Added a new `/bundle` command (REPL + CLI) that bundles source files into a single
`bundle.txt` file for manual review or upload. The bundle uses relative paths and
a self-documenting header. Also added the full SEARCH/REPLACE format specification
to the `debugger` and `project-manager` prompts, which were missing it. Added a
"File Bundle Format" section to the system prompt so the AI can parse uploaded bundles.

### Files Changed
- `src/genai_cli/bundler.py` — Added `write_bundle()` method and `_read_notebook()` helper
- `src/genai_cli/repl.py` — Added `/bundle` slash command (completer, dispatch, handler, help text)
- `src/genai_cli/cli.py` — Added `genai bundle` CLI subcommand with `--output` and `--type` options
- `config/system_prompt.yaml` — Added "Uploaded File Bundles" section after SEARCH/REPLACE
- `prompts/debugger/PROMPT.md` — Added full SEARCH/REPLACE format section before CHANGELOG
- `prompts/project-manager/PROMPT.md` — Added full SEARCH/REPLACE format section before CHANGELOG
- `tests/test_bundler.py` — Added 6 tests for `write_bundle()` (TestWriteBundle)
- `tests/test_repl.py` — Added 5 tests for `/bundle` command (TestBundleCommand)
- `tests/test_cli.py` — Added 4 tests for `genai bundle` CLI (TestBundleCLI)
- `CHANGELOG.md` — This entry

### Rationale
Users need a save-to-disk step before uploading bundles so they can review or
manually upload. The debugger and project-manager prompts produce code changes
but lacked the SEARCH/REPLACE format spec, causing inconsistent output.

### Behavior / Compatibility Implications
- `/bundle` is a new command — no impact on existing commands
- `genai bundle` is a new CLI subcommand — no impact on existing subcommands
- Debugger and project-manager prompts now include SEARCH/REPLACE instructions
- No changes to existing bundle_files() or upload behavior

### Testing Recommendations
- `pytest tests/test_bundler.py tests/test_repl.py tests/test_cli.py -v --no-cov` — 126 tests passing
- `pytest tests/test_prompt_loader.py tests/test_prompt_registry.py -v --no-cov` — 21 tests passing
- `genai bundle src/` — creates `bundle.txt` in cwd
- `genai prompt show debugger` — shows SEARCH/REPLACE section

### Follow-ups
- [ ] Add `--exclude` option to bundle command for custom exclusion patterns
- [ ] Support unbundling (extracting files from a bundle.txt)

---

## 2026-02-09 | feat: Add 5 new bundled system prompt profiles

### Summary
Added 5 new persona-focused prompt profiles to the bundled prompt library:
`project-manager`, `debugger`, `tester`, `refactorer`, and `system-architect`.
Each profile includes structured output formats tailored to its role and the
standard emoji-style CHANGELOG format section. Total bundled prompts: 10.

### Files Changed
- `prompts/project-manager/PROMPT.md` — Doc-driven development lead with PRD/TDD rules, agents.md, and README FAQ updates
- `prompts/debugger/PROMPT.md` — Systematic debugger with hypothesis-driven reproduce/isolate/root-cause/fix workflow
- `prompts/tester/PROMPT.md` — Test engineer generating pytest-style unit/integration tests with edge cases and fixtures
- `prompts/refactorer/PROMPT.md` — Refactoring specialist using SEARCH/REPLACE for extract method, dedup, simplify
- `prompts/system-architect/PROMPT.md` — High-level system designer producing Architecture Decision Records (ADR)
- `tests/test_prompt_loader.py` — Updated bundled prompt count assertion from 5 to 10
- `tests/test_prompt_registry.py` — Updated prompt discovery count assertion from 5 to 10
- `CHANGELOG.md` — This entry

### Rationale
The existing 5 prompts (default, code-changes, reviewer, planner, minimal) covered
general use cases. These 5 additions provide specialized personas for project
management, debugging, testing, refactoring, and architecture — the most common
software engineering workflows.

### Behavior / Compatibility Implications
- `genai prompt list` now shows 10 prompts instead of 5
- All new prompts follow the same frontmatter schema and are auto-discovered
- No changes to existing prompts or prompt system internals

### Testing Recommendations
- `pytest tests/test_prompt_loader.py tests/test_prompt_registry.py -v` — 21 tests passing
- `pytest tests/ -v` — full suite (398 tests) passing
- `genai prompt list` — shows all 10 prompts
- `genai prompt show debugger` — renders full body

### Follow-ups
- [ ] Add more domain-specific prompts (e.g., devops, data-engineer, security)
- [ ] Prompt composition — combine multiple profiles

---

## 2026-02-08 | fix: 415 upload error and send system prompt after /files

### Summary
Fixed two issues with `/files`: (1) uploads returned 415 Unsupported Media Type
because the CLI sent a descriptive filename while the server expects `"blob"`;
(2) after uploading files no system prompt was sent, so the model had no context
for SEARCH/REPLACE format. Now the upload uses `filename="blob"` and the system
prompt is sent automatically after a successful upload, with the model's response
displayed to the user.

### Files Changed
- `src/genai_cli/client.py` — Changed default filename to `"blob"` in `upload_document()` and `upload_bundles()`
- `src/genai_cli/repl.py` — Send system prompt after successful upload in `_handle_files()`; display response and track tokens
- `config/api_format.yaml` — Added `document_upload: "multipart/form-data"` to `endpoint_content_types`
- `tests/test_client.py` — Added tests for blob filename
- `tests/test_repl.py` — Added tests for system prompt after upload and graceful failure handling
- `CHANGELOG.md` — This entry

### Rationale
The web client sends `filename="blob"` in multipart uploads; the server validates
this and rejects other filenames with 415. Without a system prompt after upload,
follow-up messages produced unformatted responses.

### Behavior / Compatibility Implications
- `upload_document()` default filename changed from `"upload.txt"` to `"blob"`
- `upload_bundles()` now passes `"blob"` instead of `"{type}_bundle.txt"`
- After `/files` upload, the system prompt is sent and the model's response is shown
- If the system prompt send fails, a warning is shown but the upload is preserved

### Testing Recommendations
- `pytest tests/test_client.py tests/test_repl.py -v` — new + existing tests pass
- Full `pytest` — no regressions
- Manual: `/files src/*.py` → files uploaded without 415 → model responds with acknowledgment

---

## 2026-02-08 | feat: Immediate file upload, session reuse, and web UI visibility

### Summary
CLI conversations now appear in the web UI. `/files` uploads immediately instead
of queuing. Users can reuse a web UI session via `GENAI_SESSION_ID` env var or
`--session-id` flag. Upload ordering fixed so sessions always exist before file
uploads. Timestamp format matches the browser's locale format. New `/session`
command shows full session ID and web UI link. `/clear` now creates a new API
session.

### Files Changed
- `src/genai_cli/client.py` — Added `ensure_session()`, `mark_session_created()`; fixed timestamp format in `create_chat()`
- `src/genai_cli/repl.py` — Session ID from env/flag; `/files` uploads immediately; `/clear` creates API session; added `/session` command; fixed upload ordering
- `src/genai_cli/agent.py` — `ensure_session()` before `upload_bundles()`
- `src/genai_cli/cli.py` — Added `--session-id` flag; `ensure_session()` before `upload_bundles()` in `ask`
- `tests/test_client.py` — Tests for `ensure_session()`, `mark_session_created()`, timestamp format
- `tests/test_repl.py` — Tests for immediate upload, session reuse, `/clear`, `/session`, env var
- `docs/PRD.md` — Updated §7.2 (`/session`), §7.4 (`--session-id`), §8.1 (immediate upload), §12.3 (`GENAI_SESSION_ID`)
- `docs/TDD.md` — Added §10: Session Reuse & Immediate Upload
- `CHANGELOG.md` — This entry

### Rationale
The CLI created a fresh UUID per session and never associated it with the web UI.
File uploads ran before session creation on the API, causing 400 errors or orphaned
files. Users needed a way to continue web UI conversations in the CLI and vice versa.

### Behavior / Compatibility Implications
- `/files` no longer queues files — they are uploaded immediately
- `_queued_files` is no longer populated by `/files` (only agent/skill code paths)
- `GENAI_SESSION_ID` env var is a new way to set session ID
- `--session-id` is a new global CLI flag
- `create_chat()` timestamp format changed from ISO-8601 to locale-style
- `/session` is a new slash command
- `/clear` now creates a new session on the API (in addition to local reset)

### Testing Recommendations
- `pytest tests/test_client.py tests/test_repl.py -v` — new tests pass
- Full `pytest` — no regressions
- Manual: set `GENAI_SESSION_ID=<uuid>` in `.env`, run CLI, `/files src/*.py` → files uploaded → check web UI
- Manual: `/session` → shows full session ID + web UI link
- Manual: `/clear` → new session created

---

## 2026-02-08 | feat: Glob patterns, absolute paths, and exclusions for /files command

### Summary
The `/files` command now supports glob patterns (e.g., `*.py`, `**/*.ts`),
absolute paths (e.g., `/c/reportfolder/main.py`), and quoted paths with spaces.
Unmatched paths produce a warning instead of being silently ignored. The
exclude_patterns list in `settings.yaml` has been expanded to cover all standard
`.gitignore` entries (`.mypy_cache`, `.ruff_cache`, `.tox`, `.eggs`, `htmlcov`,
`.coverage`, `.bak`, `.DS_Store`, `.idea`, `.vscode`, `*.egg-info`).

### Files Changed
- `config/settings.yaml` — Expanded exclude_patterns with 11 new entries
- `src/genai_cli/bundler.py` — Added `glob.glob` expansion, `_walk_dir()` helper, `discover_files()` and `bundle_files()` now return `(result, unmatched)` tuples
- `src/genai_cli/repl.py` — Added `shlex.split()` for quoted path parsing, warnings for unmatched/empty results
- `src/genai_cli/agent.py` — Updated for `bundle_files()` tuple return
- `src/genai_cli/cli.py` — Updated for `bundle_files()` tuple return
- `tests/test_bundler.py` — Added 8 new tests: glob expansion, absolute paths, unmatched paths, recursive glob, venv exclusion, gitignore dirs, DS_Store, bundle unmatched
- `tests/test_repl.py` — Added 4 new tests: shlex quotes, empty result warning, unmatched warning, glob in REPL
- `docs/PRD.md` — Updated endpoints (§3.2), /files command (§7.2), path resolution (§8.1), exclude_patterns (§8.1), auto-login (§13.1), open questions (§20)
- `docs/TDD.md` — Added Section 9: File Bundler glob & external path support

### Rationale
The `/files` command previously only accepted literal file paths and directory
paths. Users needed to point it at external repos with glob patterns and get
feedback when paths didn't match. The expanded exclude patterns prevent
accidentally bundling build artifacts, cache directories, and IDE config files.

### Behavior / Compatibility Implications
- `discover_files()` return type changed from `dict` to `tuple[dict, list[str]]`
- `bundle_files()` return type changed from `list[FileBundle]` to `tuple[list[FileBundle], list[str]]`
- All callers updated (bundler, repl, agent, cli)

### Testing Recommendations
- `pytest tests/test_bundler.py tests/test_repl.py -v` — 93 tests passing
- Manual: `/files /tmp/testfolder/*.py` → files discovered, bundled, uploaded
- Manual: `/files "/path with spaces/file.py"` → handles quoted paths

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

## 2026-02-08 | fix: Session creation tracking for multi-message conversations

### Summary
Fixed empty responses on follow-up messages and 400 errors on file uploads.
The client now tracks which sessions have been registered with the API backend.
The first message in a conversation creates the session; subsequent messages
skip the creation step and go directly to the stream endpoint.

### Files Changed
- `src/genai_cli/client.py` — Added `_created_sessions` set to track registered sessions; `stream_chat()` creates session only on first use
- `tests/test_client.py` — Added test verifying create is called once, skipped on follow-ups

### Behavior / Compatibility Implications
- First message in a session triggers session creation + stream
- Follow-up messages skip creation, go straight to stream
- File uploads now work because the session exists on the backend before upload

### Testing Recommendations
- `make test` — 347 tests passing, 83% coverage
- REPL: send first message (creates session), then follow-up (skips create)
- `/files path` then message — upload succeeds after session is created

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
