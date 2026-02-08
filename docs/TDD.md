# Technical Design Document: SEARCH/REPLACE Parser

**Version:** 1.0.0
**Date:** 2026-02-07
**Status:** Implemented

---

## 1. Overview

The SEARCH/REPLACE block parser replaces the regex-based `ResponseParser` as the
primary mechanism for applying AI-generated code changes to local files. It uses
Aider-style git-conflict markers that are unambiguous, require no escaping, and
are reliably produced by LLMs.

### Problem

The original parser had three fragile regex patterns:
1. Fenced blocks (`\`\`\`lang:path`) — broke on nested backticks, required language prefix
2. Unified diffs — toy `_simple_patch` didn't verify context lines
3. `FILE:` markers — high false-positive rate on prose

All three supported only full-file replacement or fragile diffs. No surgical
edit capability existed.

### Solution

SEARCH/REPLACE blocks where the AI quotes the exact content to find and provides
the replacement. The markers `<<<<<<< SEARCH`, `=======`, `>>>>>>> REPLACE` are
git-conflict-style markers that never appear in real code and are well-known to
LLMs from training data.

---

## 2. Architecture

### 2.1 Class Diagram

```
applier.py
├── Data structures
│   ├── EditBlock        — SEARCH/REPLACE operation
│   ├── CodeBlock        — Legacy format block (unchanged)
│   └── ApplyResult      — Success/failure + error details
├── Parsers
│   ├── SearchReplaceParser  — State-machine parser (primary)
│   ├── ResponseParser       — Regex parser (legacy fallback)
│   └── UnifiedParser        — Orchestrator: SR first, legacy fallback
└── Applier
    └── FileApplier
        ├── apply_edits()              — Apply SEARCH/REPLACE EditBlocks
        ├── _apply_search_replace()    — Single edit with 3-tier matching
        ├── _find_search_content()     — 3-tier matching engine
        ├── apply_all()                — Apply legacy CodeBlocks
        └── (existing safety methods)  — validate_path, backup, git dirty
```

### 2.2 Parser State Machine

```
                        ┌─────────────┐
                        │  SCANNING   │◄────────────────────────┐
                        └──────┬──────┘                         │
                               │                                │
                  filepath + <<<<<<< SEARCH                     │
                               │                                │
                        ┌──────▼──────┐                         │
                        │  IN_SEARCH  │                         │
                        └──────┬──────┘                         │
                               │                                │
                           =======                              │
                               │                                │
                        ┌──────▼──────┐                         │
                        │ IN_REPLACE  │                         │
                        └──────┬──────┘                         │
                               │                                │
                      >>>>>>> REPLACE ──► emit EditBlock ───────┘
```

**Path detection:** A line is treated as a file path only when it:
- Is not blank
- Does not start with whitespace
- Is not a marker itself
- Is immediately followed by `<<<<<<< SEARCH` on the next line

The look-ahead for `<<<<<<< SEARCH` prevents false positives on prose.

### 2.3 Three-Tier Matching

When applying a SEARCH/REPLACE edit, the SEARCH content must be found in the
target file. Three matching tiers are tried in order:

| Tier | Method | Handles |
|------|--------|---------|
| 1 | Exact string match | Perfect SEARCH content |
| 2 | Trailing whitespace normalized | LLM strips trailing spaces/tabs |
| 3 | Leading indent normalized | LLM uses wrong indentation level |

If all three tiers fail, an error is returned with a snippet of the actual file
content (truncated to 200 lines) so the AI can self-correct.

**Why not fuzzy matching?** Fuzzy matching (e.g., difflib) introduces ambiguity
and false positives. The three-tier approach handles the two most common LLM
errors without risking misapplication.

### 2.4 Error Feedback Loop

```
Round N:
  AI response → parse → apply edits
    ├── Success: "Applied changes to: a.py, b.py"
    └── Failure: "FAILED to apply edit to c.py: SEARCH block not found.
                  Current content of c.py:
                  ```
                  <actual file content>
                  ```
                  Please retry with corrected SEARCH content."

Round N+1:
  AI receives feedback → generates corrected SEARCH/REPLACE → applies
```

This self-correction loop means transient LLM errors (wrong quoting, stale
content) are automatically recovered in the next agent round.

---

## 3. Data Flow

```
AI Response (text)
    │
    ▼
UnifiedParser.parse()
    ├── SearchReplaceParser.parse()  → list[EditBlock]  (if found)
    └── ResponseParser.parse()       → list[CodeBlock]  (fallback)
    │
    ▼
FileApplier
    ├── apply_edits(EditBlock[])   → list[ApplyResult]
    │   ├── validate_path()
    │   ├── _find_search_content()  (3-tier match)
    │   ├── backup if enabled
    │   └── write modified content
    │
    └── apply_all(CodeBlock[])     → list[ApplyResult]
        └── (legacy: full-file replacement or diff)
    │
    ▼
AgentLoop._run_round()
    ├── files_applied: [paths that succeeded]
    ├── failed_edits:  [ApplyResult with error details]
    └── _build_feedback_message() → next round prompt
```

---

## 4. SEARCH/REPLACE Format Specification

```
path/to/file.py
<<<<<<< SEARCH
exact content to find in the file
=======
replacement content
>>>>>>> REPLACE
```

### Operations

| Operation | SEARCH | REPLACE |
|-----------|--------|---------|
| Create file | Empty | Full file content |
| Edit content | Exact match | New content |
| Delete content | Content to remove | Empty |
| Multiple edits | Repeat blocks | Same file path |

### Rules
- File path must be on its own line immediately before `<<<<<<< SEARCH`
- SEARCH content must be an exact character-for-character copy
- Multiple edits to the same file: use separate blocks, ordered top-to-bottom
- Edits are applied sequentially; each edit sees the result of the previous one

---

## 5. Security Considerations

All existing safety checks are preserved:

| Check | Location | Behavior |
|-------|----------|----------|
| Path traversal | `validate_path()` | Reject paths with `..` |
| Project root | `validate_path()` | Reject paths outside project |
| Blocked patterns | `validate_path()` | Reject `.env`, `*.pem`, `*.key`, etc. |
| Git dirty | `_check_git_dirty()` | Warn if file has uncommitted changes |
| Backup | `_create_backup()` | Create `.bak` before modifying |
| Confirm mode | `apply_edits()` | Ask user before each edit |
| Dry-run mode | `apply_edits()` | Show changes without writing |

File content snippets in error feedback are truncated to 200 lines to prevent
context window overflow.

---

## 6. Testing Strategy

### Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_search_replace.py` | 36 | Parser, matching, application |
| `tests/test_applier.py` | 26 | Legacy parser, applier (updated for ApplyResult) |
| `tests/test_agent.py` | 13 | Agent loop, error feedback |

### Key Test Categories

**Parser tests:** Single edit, create, delete, multi-edit same file, multi-file,
prose mixed, incomplete blocks, nested fences, Windows line endings.

**Matching tests:** Exact match, whitespace-normalized, indent-normalized,
search-not-found with error details.

**Application tests:** Create file, edit existing, delete content, backup,
dry-run, path validation, git dirty.

**Feedback tests:** Success message, failure with file content, mixed results,
no-action fallback.

---

## 7. Migration

The transition is non-breaking:

1. **System prompt updated** to instruct AI to use SEARCH/REPLACE format
2. **Legacy parsers kept** as fallback — old fenced, diff, and FILE: formats
   still work if no SEARCH/REPLACE blocks are found
3. **`UnifiedParser`** automatically selects the right parser
4. **No config changes needed** — the parser selection is automatic

Old AI responses (from before the system prompt update) will seamlessly fall
back to the legacy parser. New responses will use SEARCH/REPLACE.

---

## 8. Future Enhancements

- [ ] Diff preview for SEARCH/REPLACE edits in confirm mode (show only changed lines)
- [ ] Binary file detection (skip SEARCH/REPLACE for non-text files)
- [ ] File rename/move operations via a `<<<<<<< RENAME` marker
- [ ] Conflict detection when multiple edits overlap in the same file
- [ ] Metrics: track match-tier usage (exact vs normalized) for prompt tuning
