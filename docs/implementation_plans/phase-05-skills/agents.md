# Phase 5: Skills System

## Task
Implement SKILL.md-based skills system with loader, registry, executor, 14 bundled skills, and CLI/REPL integration.

## Purpose
Provide repeatable AI workflows with consistent prompts. Skills are human-readable markdown files with YAML frontmatter, discoverable from 3 locations with priority override.

## Acceptance Criteria
- All 14 bundled SKILL.md files parse without error
- Skills discovered from project > user > bundled (priority order)
- Tier 1 metadata loads ~100 tokens per skill
- `genai skill list` shows all 14 skills
- `genai skill invoke review --files src/` executes end-to-end
- `/skills` and `/skill <name>` work in REPL
- `agents.md` discovered from nearest ancestor directory
- Custom skills override bundled by name
- 233 tests passing, 81% coverage

## Architecture
- `SkillLoader`: Parses SKILL.md YAML frontmatter + markdown body, 3-tier loading
- `SkillRegistry`: Discovers skills from 3 locations, deduplicates by name
- `SkillExecutor`: Assembles prompt (system -> agents.md -> skill -> user) and runs AgentLoop
- 14 SKILL.md files in `skills/` directory at project root

## Testing
- `tests/test_skill_loader.py` — 12 tests
- `tests/test_skill_registry.py` — 10 tests
- `tests/test_skill_executor.py` — 6 tests
