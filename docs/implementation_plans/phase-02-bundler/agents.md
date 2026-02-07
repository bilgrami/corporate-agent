# Phase 2: File Bundler + Upload Integration — Agent Instructions

## Task
Create the file bundler module, enhance client with bundle uploads,
add streaming tests, and add the `genai files` preview command.

## Purpose
Enable `genai ask "review this" --files src/ --type code` to bundle files,
upload them separately by type, and chat with file context.

## Acceptance Criteria
- All file extensions from PRD classified correctly (code/docs/scripts/notebooks)
- Makefile, Dockerfile classified as scripts (include_names)
- Exclusion patterns block .env, *.key, __pycache__/, .git/
- Bundle format: `===== FILE: /abs/path =====\nRelative Path: rel/path\n\n<content>`
- Notebook cells formatted as `--- Cell N [type] ---`
- Each file type uploaded as separate PUT request
- `genai files src/` previews bundles without uploading
- SSE streaming yields tokens in order; fallback works
- Tests pass with >80% coverage for bundler.py, streaming.py

## Testing Criteria
- 18-22 bundler tests: classify, exclude, size limits, binary, markers, notebooks
- 8-10 streaming tests: SSE parsing, [DONE], fallback, connection error
