# Contributing to GenAI CLI

## Development Environment Setup

### Prerequisites

- Python 3.10 or later
- make (standard on macOS/Linux)
- git

### Initial Setup

```bash
git clone <repo-url>
cd corporate-agent
make setup
```

This creates `.venv/`, installs all dependencies (including dev tools), and
makes `genai` available on PATH within the venv.

### Activate the Environment

```bash
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

## Running Tests

```bash
make test                                    # Full suite with coverage
pytest tests/test_cli.py -v                  # Single test file
pytest tests/test_cli.py::TestCLI::test_help # Single test
```

Currently: 233 tests, 81% overall coverage. Target: >80% per module.

## Linting and Formatting

```bash
make lint     # ruff check + mypy --strict
make format   # ruff format (auto-fix)
```

Configuration in `pyproject.toml`:
- ruff: target-version py310, line-length 88
- mypy: strict mode, all public functions typed

Always run `make lint && make test` before submitting changes.

## Project Architecture

See [Architecture.md](Architecture.md) for component diagrams and data flow.
See [PRD.md](PRD.md) for full requirements and API documentation.

## Adding Features

### Adding a New CLI Command

1. Define Click command in `src/genai_cli/cli.py`
2. Add REPL slash command handler in `src/genai_cli/repl.py` (if applicable)
3. Update `_handle_help()` text in `repl.py`
4. Write tests in `tests/test_cli.py` (use `CliRunner`)
5. Write tests in `tests/test_repl.py` (test handler directly)
6. Update README.md command tables

### Adding a New Skill

1. Create `skills/<name>/SKILL.md` with YAML frontmatter
2. Verify with `genai skill list` and `genai skill invoke <name> --dry-run`
3. Add parse test in `tests/test_skill_loader.py`
4. Update the skill count in `tests/test_skill_registry.py::test_discovers_all_14_skills`

### Adding a New Config Setting

1. Add field to `AppSettings` in `src/genai_cli/models.py`
2. Add default in `config/settings.yaml`
3. Add merge logic in `ConfigManager.settings` property (`src/genai_cli/config.py`)
4. Add test in `tests/test_config.py`

### Adding a New API Endpoint

1. Add method to `GenAIClient` in `src/genai_cli/client.py`
2. Add respx mock in `tests/test_client.py`
3. Wire into CLI command or REPL handler as needed

## Testing Conventions

- **HTTP calls**: Always mock with `respx`. No real network calls in tests.
- **File operations**: Use `tmp_path` fixture for safe file creation/modification.
- **Display output**: Use `Display(file=StringIO())` to capture and assert output.
- **CLI integration**: Use `click.testing.CliRunner` for invoking CLI commands.
- **Auth context**: Use `patch.dict("os.environ", {...})` for token injection.
- **Fixtures**: Shared fixtures are defined in `tests/conftest.py`.

Each source module should have a corresponding `tests/test_<module>.py`.

## Applier Architecture

The response applier system lives in `src/genai_cli/applier.py` and handles
converting AI responses into file changes.

**Key classes:**

| Class | Purpose |
|-------|---------|
| `SearchReplaceParser` | Parses SEARCH/REPLACE blocks (primary format) |
| `ResponseParser` | Legacy regex parser (fenced, diff, FILE: formats) |
| `UnifiedParser` | Tries SEARCH/REPLACE first, falls back to legacy |
| `FileApplier` | Applies edits with safety checks (path validation, backups, git dirty) |
| `EditBlock` | Dataclass for SEARCH/REPLACE operations |
| `CodeBlock` | Dataclass for legacy format operations |
| `ApplyResult` | Result of applying one edit (success/failure + error message) |

**Adding a new response format:**

1. Create a parser class with a `parse(response: str) -> list[...]` method
2. Add it to `UnifiedParser` with appropriate priority
3. Add an apply method to `FileApplier`
4. Add tests in `tests/test_search_replace.py` or a new test file
5. Update the system prompt in `config/system_prompt.yaml`

**How matching works:**

SEARCH content is matched against file content using three tiers:
1. Exact match
2. Whitespace-normalized (trailing whitespace stripped per line)
3. Indent-normalized (leading whitespace stripped per line)

If all three fail, an error is returned with actual file content for AI
self-correction in the next agent round. See [TDD.md](TDD.md) for details.

## Code Style

- Type hints on all public functions
- No vendor names in `.py` files (only in `config/models.yaml`)
- Single responsibility per module
- Import order: stdlib, third-party, local (enforced by ruff)
- POSIX `#!/bin/sh` for all shell scripts (no bash-isms)
- No `shell=True` in subprocess calls

## Commit Messages

Follow the format: `<category>: <description>`

Categories: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`

Update `CHANGELOG.md` at the top with a new entry for each change.
See existing entries for the expected format (Summary, Files Changed,
Rationale, Testing Recommendations).
