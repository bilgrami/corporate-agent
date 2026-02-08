# Phase 6: SEARCH/REPLACE Block Parser

## Task
Replace the fragile regex-based `ResponseParser` with a robust SEARCH/REPLACE
block parser using Aider-style git-conflict markers.

## Purpose
Enable reliable surgical file edits from AI responses without full-file
replacement or fragile unified diffs. Add error feedback so the AI can
self-correct when edits fail.

## Description
- State-machine parser for `<<<<<<< SEARCH` / `=======` / `>>>>>>> REPLACE` blocks
- Three-tier matching: exact, whitespace-normalized, indent-normalized
- `UnifiedParser` orchestrator: SEARCH/REPLACE first, legacy fallback
- Error feedback loop: when SEARCH not found, send actual file content to AI
- Legacy parsers (fenced, diff, FILE:) preserved as fallback

## Acceptance Criteria
- [x] `SearchReplaceParser` correctly parses single/multi edit blocks
- [x] `UnifiedParser` prefers SEARCH/REPLACE, falls back to legacy
- [x] `FileApplier.apply_edits()` handles create, edit, delete operations
- [x] Three-tier matching handles trailing whitespace and indent differences
- [x] Failed edits return `ApplyResult` with error message and file content
- [x] `AgentLoop` builds feedback message including failures
- [x] System prompt instructs AI to use SEARCH/REPLACE format
- [x] All existing tests pass (backward compatibility)
- [x] 36+ new tests for parser, matching, and application
- [x] 280 total tests passing, 81% coverage

## Assumptions
- LLMs reliably produce git-conflict-style markers when instructed
- Three-tier matching handles the two most common LLM errors
- Legacy formats are rarely needed after system prompt update

## Rationale
- Git conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) are unambiguous
- No escaping needed — code content is literal between markers
- Self-validating: SEARCH content must exist in the file
- Battle-tested by Aider across millions of real-world edits

## Testing Criteria
- `make test` — 280 tests passing
- Parser handles edge cases: nested fences, incomplete blocks, Windows line endings
- Matching handles: exact, trailing whitespace, indent differences
- Error feedback includes file content for AI self-correction
- Legacy fallback works when no SEARCH/REPLACE blocks found
