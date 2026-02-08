# Phase 3: Session Management + REPL + Token Tracking — Agent Instructions

## Task
Create token tracker, session manager, interactive REPL with all slash
commands, and integrate with CLI.

## Purpose
Enable persistent sessions, interactive conversational mode, model switching,
and visual token tracking so users can manage context window usage.

## Acceptance Criteria
- `genai` (no args) launches REPL with welcome banner
- All slash commands from PRD 7.2 functional
- `/model <name>` switches model, updates context window
- `/files src/` queues files; next message uploads them
- `/clear` creates new session, resets tokens
- `/quit` saves session to ~/.genai-cli/sessions/
- `genai resume <id>` restores session
- Token status: green (<80%), yellow (80-95%), red (>95%)
- Tests pass with >80% coverage for token_tracker, session, repl

## Testing Criteria
- 17 token tracker tests: accumulation, thresholds, model switch, serialization
- 16 session tests: CRUD, persistence, compact, pruning
- 26 REPL tests: all slash commands, state management
