---
name: migrate-module
description: >
  Move a Python module or symbol to a new location and automatically
  rewrite all import statements across the codebase.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: refactoring
  auto_apply: true
---

# Migrate Module

Move a Python module (file) or individual symbol (function/class) to a new location, automatically updating all import statements across the codebase.

## Instructions

1. **Identify the Move**: Determine what needs to move:
   - **Module move**: An entire .py file to a new path
   - **Symbol move**: A single function or class from one file to another
   - **Cross-repo move**: A file from one repository to another (requires workspace)

2. **Analyze Impact**: Before moving:
   - Run dependency analysis to find all files that import the target
   - Compute the full list of import statements that need updating
   - Check for circular dependencies that the move might create
   - Identify if __init__.py files need creation

3. **Plan**: Generate a RefactorPlan that includes:
   - The move operation(s)
   - All import updates (old statement -> new statement)
   - Any new files needed (__init__.py, adapter modules)
   - List of all affected files

4. **Preview**: Show the user:
   - Source and destination paths
   - Number of import rewrites
   - The specific import changes per file
   - Any backward-compatibility adapter that will be generated

5. **Execute**: Apply the plan:
   - Move the file or extract the symbol
   - Rewrite all import statements using SEARCH/REPLACE
   - Create __init__.py files as needed
   - Optionally generate backward-compatibility adapter at old location

## Output Format

```
## Migration Plan

### Move
- Source: `old/path/module.py`
- Target: `new/path/module.py`
- Symbol: (all | specific_name)

### Import Updates (N files affected)
- `file_a.py:5`: `from old.path import module` -> `from new.path import module`
- `file_b.py:3`: `import old.path.module` -> `import new.path.module`

### New Files
- `new/path/__init__.py`

### Backward Compatibility
- Adapter at `old/path/module.py` re-exports moved symbols

## Execution Result
- Moves completed: N
- Imports updated: N
- Files created: N
```

## Guidelines

- Always analyze dependencies before moving — never blindly rename
- Prefer updating imports over generating adapters
- Generate adapters only when external consumers cannot be updated
- Verify that no imports are broken after the migration
- For symbol moves, ensure the target file has the necessary imports
- Create __init__.py files to maintain package structure
