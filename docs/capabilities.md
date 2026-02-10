# GenAI CLI — Capabilities & Limitations

## Model Support Matrix

| Model | Provider | Context Window | Max Output | Streaming | File Upload |
|-------|----------|---------------|------------|-----------|-------------|
| GPT-5 | OpenAI | 128,000 | 16,384 | Yes | Yes |
| GPT-5 Mini | OpenAI | 128,000 | 16,384 | Yes | Yes |
| Gemini 2.5 Pro | Google | 1,000,000 | 8,192 | Yes | Yes |
| Gemini 2.5 Flash | Google | 1,000,000 | 8,192 | Yes | Yes |
| Claude Sonnet 4.5 | Anthropic | 200,000 | 16,384 | Yes | Yes |

All models are accessed through the corporate AI chat platform — no direct API
keys are required. Context windows and output limits are enforced by the
platform.

## Current Capabilities

### Core Features
- **Multi-model chat**: Switch between GPT-5, Gemini 2.5, and Claude models
- **File upload**: Bundle and upload code, docs, scripts, and notebooks
- **Code application**: Parse AI responses and apply SEARCH/REPLACE edits
- **Agent mode**: Multi-round conversations with automatic code changes
- **Session persistence**: Save, resume, and export conversations
- **Token tracking**: Real-time usage monitoring with color-coded warnings
- **Skills system**: Pre-built AI workflows for common tasks (14 bundled)
- **Prompt profiles**: Switchable system prompts for different workflows

### Code Analysis & Refactoring
- **Dependency analysis**: AST-based import graph with cycle detection
- **Module classification**: Core modules (high fan-in) vs leaf modules
- **Cluster detection**: Connected component analysis for split boundaries
- **Module migration**: Move files/symbols with automatic import rewriting
- **Repo splitting**: Guided workflow to split monorepos
- **Smart chunking**: Fit large codebases into model context windows

### Multi-Repo Workspaces
- **Workspace management**: Track multiple repos as a single workspace
- **Cross-repo file moves**: Move files between repos with git tracking
- **Cross-repo analysis**: Analyze dependencies across all workspace repos
- **File search**: Find files across all repos in the workspace

### Git Operations
- **Status tracking**: Branch, staged, unstaged, untracked files
- **Safe operations**: Init, add, commit, branch, checkout
- **File tracking**: Git mv, rm with staging
- **Checkpoints**: Create checkpoint commits before risky operations
- **Rollback**: Restore to previous state with confirmation

## Limitations

### Model Limitations
- **Context windows are fixed**: Cannot exceed the platform's limit per model
- **No function calling**: Models are accessed via chat, not function-call API
- **No image/audio input**: Only text-based file uploads are supported
- **Rate limits**: Subject to corporate platform rate limits
- **Token estimation**: Approximate (~4 chars per token fallback)

### Code Analysis Limitations
- **Python only**: AST analysis works only for Python (.py) files
- **Static analysis**: No runtime dependency detection (dynamic imports,
  `importlib`, `__import__()` are not tracked)
- **No type inference**: Import resolution is name-based, not type-based
- **Relative imports**: Partially supported (resolved relative to root_dir)

### Refactoring Limitations
- **No semantic analysis**: Moves are structural, not semantic — renaming a
  symbol won't update string references or config files
- **Single-language**: Import rewriting is Python-specific
- **No test verification**: The engine doesn't automatically run tests after
  refactoring — you should run `make test` manually

### Git Limitations
- **No merge/rebase**: Only basic operations (init, add, commit, branch)
- **No conflict resolution**: Merge conflicts must be resolved manually
- **Local only**: No push/pull/fetch — those require auth configuration

## Repo-Split Workflow Guide

### Overview

Splitting a monorepo into two repos is a multi-step process:

1. **Analyze** — Understand the dependency graph
2. **Plan** — Decide which modules go where
3. **Execute** — Move files and rewrite imports
4. **Verify** — Ensure nothing is broken

### Step 1: Analyze

```bash
# CLI
genai analyze src/ --format text

# REPL
/analyze src/
```

This produces a dependency report showing:
- Core modules (shared by many others)
- Leaf modules (independent, easy to move)
- Clusters (groups of tightly-coupled modules)
- Circular dependencies (must resolve before splitting)

### Step 2: Plan the Split

Use the `repo-split` skill:

```bash
# Queue the codebase and invoke the skill
/files src/
/skill repo-split
```

The AI will:
- Review the dependency analysis
- Suggest split boundaries
- Identify modules that need to stay shared
- Generate a migration plan

### Step 3: Execute

Once you approve the plan:

```bash
# Set up a workspace
/workspace add source .
/workspace add target ../new-repo

# The skill will execute moves and import rewrites
```

### Step 4: Verify

```bash
# Run tests in both repos
make test

# Check for broken imports
genai analyze src/ --format text
```

## What to Expect from Each Model

### GPT-5
- Best for: General coding, code review, debugging
- Context: 128K tokens — handles medium codebases
- Strengths: Strong reasoning, good at SEARCH/REPLACE format

### Gemini 2.5 Pro
- Best for: Large codebase analysis (1M context window)
- Context: 1M tokens — can ingest entire repos
- Strengths: Massive context, good at pattern recognition

### Claude Sonnet 4.5
- Best for: Detailed analysis, nuanced explanations
- Context: 200K tokens — handles large codebases
- Strengths: Careful reasoning, thorough code review
