---
name: commit-msg
description: >
  Generate well-crafted commit messages from git diffs following conventional commit format. Analyzes changes to create clear, informative messages with proper type, scope, and description following best practices.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: workflow
---

# Commit Message Generation

Generate a well-crafted commit message from the current git diff following conventional commit format and best practices.

## Instructions

1. **Analyze the Changes**:
   - Run `git diff --staged` to see staged changes
   - Run `git diff` to see unstaged changes if no staged changes exist
   - Understand what was modified, added, or deleted
   - Identify the primary purpose of the changes

2. **Determine Commit Type**:
   - `feat`: New feature or functionality
   - `fix`: Bug fix
   - `docs`: Documentation changes only
   - `style`: Code style changes (formatting, missing semicolons, etc.)
   - `refactor`: Code refactoring without changing behavior
   - `perf`: Performance improvements
   - `test`: Adding or updating tests
   - `build`: Build system or dependency changes
   - `ci`: CI/CD configuration changes
   - `chore`: Maintenance tasks, tooling, etc.

3. **Identify Scope** (optional):
   - Module, component, or area affected
   - Examples: `auth`, `api`, `ui`, `database`, `parser`

4. **Write Message**:
   - **Subject**: Clear, concise description (50 chars or less)
   - **Body** (optional): Detailed explanation of what and why
   - **Footer** (optional): Breaking changes, issue references

## Conventional Commit Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Examples

### Simple Feature
```
feat(auth): add OAuth2 authentication support
```

### Bug Fix with Details
```
fix(parser): handle null values in JSON parsing

Previously, null values caused the parser to crash. This fix adds
proper null checking and returns None for null JSON values.

Fixes #123
```

### Breaking Change
```
feat(api): redesign user endpoint response structure

Changed the response format to be more consistent with REST standards.
Users array is now under 'data' key, and metadata is in 'meta' key.

BREAKING CHANGE: Response format changed from {users: [...]} to
{data: [...], meta: {...}}
```

### Refactoring
```
refactor(database): extract query builder into separate class

Improves code organization and testability by separating query
building logic from database connection management.
```

### Multiple Files
```
chore: update dependencies and fix deprecation warnings

- Upgraded axios to v1.4.0
- Replaced deprecated moment.js with date-fns
- Updated test mocks to match new API
```

## Guidelines

### Subject Line
- Use imperative mood: "add" not "added" or "adds"
- Don't capitalize first letter (unless it's a proper noun)
- No period at the end
- Keep under 50 characters
- Be specific: "fix login validation" not "fix bug"

### Body
- Wrap at 72 characters
- Explain WHAT and WHY, not HOW
- Separate from subject with blank line
- Can use bullet points for multiple changes
- Reference issue numbers if applicable

### When to Include Body
- Complex changes that need explanation
- Breaking changes
- Multiple related changes
- Important context or rationale

### When to Keep it Simple
- Obvious, self-explanatory changes
- Single-purpose commits
- Documentation-only changes

## Output Format

Provide the commit message in a code block:

```
[The generated commit message in proper format]
```

Then explain your reasoning:

```
## Commit Message Analysis

**Type**: [chosen type and why]

**Scope**: [chosen scope and why, or "none" if not applicable]

**Summary**: [Brief explanation of what changed]

**Key Changes**:
- [List main changes from the diff]

**Rationale**: [Why this commit message accurately represents the changes]
```

## Common Patterns

### Adding New Feature
```
feat(module): add [feature name]

Implements [what it does] by [brief technical approach].
This enables users to [user benefit].
```

### Fixing Bug
```
fix(module): correct [specific issue]

[Description of the bug and its impact]
[How the fix addresses it]

Fixes #[issue-number]
```

### Refactoring
```
refactor(module): [improvement description]

[Why the refactoring was needed]
[What benefits it provides]
```

## Guidelines

- **Read the diff carefully**: Understand all changes before writing
- **Be accurate**: Message must reflect actual changes
- **Be specific**: Avoid vague descriptions like "update files"
- **Group related changes**: If changes span multiple areas, consider if they should be separate commits
- **Follow project conventions**: Check recent commits for project-specific patterns
- **Include context**: If the change relates to an issue or discussion, reference it
