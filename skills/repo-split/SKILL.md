---
name: repo-split
description: >
  Split a monorepo into two or more repositories. Analyzes dependencies,
  presents module clusters, plans the split, and executes file moves with
  import rewrites and backward-compatibility adapters.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: architecture
  auto_apply: false
---

# Repo Split

Split a monorepo into multiple repositories while maintaining working imports and backward compatibility.

## Instructions

1. **Analyze Dependencies**: Run the dependency analyzer on the source repository to understand the module graph.
   - Identify module clusters (groups of tightly-coupled modules)
   - Identify core modules (high fan-in) that may need to stay shared
   - Detect circular dependencies that must be resolved before splitting

2. **Present Clusters**: Show the user:
   - A visual dependency map of the codebase
   - Suggested split boundaries based on module clusters
   - Core modules that would need to be duplicated or made into a shared library
   - Any circular dependencies that block a clean split

3. **Plan the Split**: Based on user feedback:
   - Define which modules go to which repository
   - Plan import rewrites for all affected files
   - Plan backward-compatibility adapter modules (re-export shims)
   - Identify any __init__.py files that need creation
   - Create a workspace configuration for the new multi-repo setup

4. **Confirm**: Present the complete plan to the user:
   - Number of files to move
   - Number of import statements to rewrite
   - New files to create (adapters, __init__.py)
   - Risk assessment (circular deps, shared state, etc.)
   - Wait for explicit confirmation before proceeding

5. **Execute**:
   - Create the target repository (git init)
   - Move files to target repository
   - Update imports in both repositories
   - Generate adapter modules for backward compatibility
   - Create/update __init__.py files as needed
   - Run a verification pass (imports resolve, no broken references)

## Output Format

```
## Repo Split Plan

### Source Repository
- Name: <name>
- Modules staying: <count>

### Target Repository
- Name: <name>
- Modules moving: <count>

### Changes
- Files to move: <count>
- Import rewrites: <count>
- New files: <count>
- Adapter modules: <count>

### Risk Assessment
- Circular dependencies: <list>
- Shared state concerns: <list>

### Execution Steps
1. Create target repository
2. Move files (list)
3. Rewrite imports (list)
4. Generate adapters (list)
5. Verify
```

## Guidelines

- Always analyze before planning — never guess at dependencies
- Prefer breaking circular dependencies over creating adapters
- Core modules with high fan-in should stay in a shared library
- Generate backward-compatibility adapters only when necessary
- Always verify the split by checking that imports resolve
- Create a .genai-workspace.yaml for the new multi-repo setup
