# Phase 4: Response Applier + Agent Loop — Agent Instructions

## Task
Create response parser, file applier, and multi-round agent loop.

## Purpose
Parse AI responses for code blocks and diffs, preview as colored diffs,
and apply changes to local files with confirmation. Agent loop orchestrates
multi-round interactions.

## Acceptance Criteria
- Parser detects 3 code formats (fenced, diff, FILE: marker)
- Path traversal rejected, blocked patterns enforced
- .bak backup before overwrite, git dirty warnings
- Confirm/auto/dry-run modes
- Agent loop: multi-round with stop conditions (no actions, max rounds, token limit)
- 206 tests passing

## Testing Criteria
- 26 applier tests: parse 3 formats, dedup, security, apply modes
- 9 agent tests: rounds, stop conditions, dry-run, files, prompt assembly
