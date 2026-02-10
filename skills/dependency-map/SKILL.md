---
name: dependency-map
description: >
  Analyze and visualize Python module dependencies. Produces a dependency
  graph with cycle detection, module classification, and cluster analysis.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: analysis
  auto_apply: false
---

# Dependency Map

Analyze the Python codebase and produce a comprehensive dependency report with visualization.

## Instructions

1. **Parse**: Use the AST dependency analyzer to parse all Python files in the target directory.

2. **Analyze**: Build the dependency graph and compute:
   - Module-to-module import edges
   - Reverse edges (who depends on each module)
   - Circular dependencies (cycles in the graph)
   - Module classification: core (most depended-on) vs leaf (no dependents)
   - Module clusters (connected components)

3. **Visualize**: Present the results as:
   - An ASCII dependency graph showing import relationships
   - A summary table of modules with import/dependent counts
   - Highlighted circular dependencies
   - Cluster groupings with suggested boundaries

4. **Recommend**: Based on the analysis:
   - Flag modules with excessive coupling (too many dependencies)
   - Suggest refactoring opportunities (break cycles, extract interfaces)
   - Identify candidates for extraction into separate packages
   - Note leaf modules that could be removed or consolidated

## Output Format

```
## Dependency Analysis Report

**Total modules**: N
**Total imports**: N
**Clusters**: N
**Cycles detected**: N

### Core Modules (most depended-on)
- `module_name` (N dependents)

### Leaf Modules (no dependents)
- `module_name`

### Circular Dependencies
1. module_a -> module_b -> module_a

### Module Clusters

#### cluster_0 (N modules)
  - `module_a` (N dependencies)
  - `module_b` (N dependencies)

### Dependency Graph
  config ──> models
  display ──> models
  repl ──> config, display, bundler
  ...

### Recommendations
- [HIGH] Break cycle between X and Y by extracting shared interface
- [MEDIUM] Module Z has 15 dependents — consider interface extraction
- [LOW] Leaf module W is unused — consider removal
```

## Guidelines

- Parse all .py files, skip __pycache__ and other excluded patterns
- Report cycles prominently — they block clean architecture
- Sort core modules by dependent count (highest first)
- Group related modules into clusters for easier comprehension
- Keep the ASCII graph readable (max ~30 nodes inline, summarize larger codebases)
