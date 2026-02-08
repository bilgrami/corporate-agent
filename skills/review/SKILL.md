---
name: review
description: >
  Perform comprehensive code review analyzing bugs, security vulnerabilities, performance issues, and style violations. Provides actionable feedback with severity ratings and specific recommendations for improvement.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: development
---

# Code Review

Perform a thorough code review of the specified files or codebase, focusing on four key areas: bugs, security, performance, and style.

## Instructions

1. **Read and Analyze**: Carefully read all provided code files or the specified directory structure.

2. **Bug Analysis**:
   - Identify logical errors, edge cases not handled, off-by-one errors, null/undefined handling issues
   - Check for improper error handling and exception cases
   - Look for race conditions, deadlocks, or concurrency issues

3. **Security Review**:
   - Check for injection vulnerabilities (SQL, command, XSS)
   - Identify hardcoded credentials, API keys, or sensitive data
   - Review authentication and authorization logic
   - Check for insecure cryptographic practices
   - Look for improper input validation and sanitization

4. **Performance Analysis**:
   - Identify inefficient algorithms (O(n²) where O(n) would work)
   - Check for unnecessary loops, redundant operations, or repeated calculations
   - Look for memory leaks or excessive memory usage
   - Identify missing database indexes or inefficient queries
   - Check for blocking I/O operations

5. **Style and Best Practices**:
   - Verify adherence to language-specific conventions
   - Check naming conventions (variables, functions, classes)
   - Review code organization and modularity
   - Identify code smells (long functions, deep nesting, duplicated code)
   - Check for proper documentation and comments

## Output Format

Structure your review as follows:

```
## Code Review Summary

**Overall Assessment**: [Brief 2-3 sentence summary]

### Bugs
- [CRITICAL/HIGH/MEDIUM/LOW] [File:Line] Description
  - Recommendation: ...

### Security
- [CRITICAL/HIGH/MEDIUM/LOW] [File:Line] Description
  - Recommendation: ...

### Performance
- [HIGH/MEDIUM/LOW] [File:Line] Description
  - Recommendation: ...

### Style & Best Practices
- [File:Line] Description
  - Recommendation: ...

## Positive Observations
- [Things done well that should be highlighted]
```

## Severity Levels

- **CRITICAL**: Must fix immediately (security vulnerability, data loss risk)
- **HIGH**: Should fix before merge (bugs, major performance issues)
- **MEDIUM**: Should fix soon (minor bugs, moderate technical debt)
- **LOW**: Nice to have (style improvements, minor optimizations)

## Guidelines

- Be specific: Always reference file names and line numbers
- Be constructive: Explain why something is an issue and how to fix it
- Be thorough: Don't just focus on obvious issues
- Be balanced: Acknowledge good practices alongside issues
- Prioritize: Focus on high-impact issues first
