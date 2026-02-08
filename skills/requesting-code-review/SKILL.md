---
name: requesting-code-review
description: >
  Prepare code for peer review by creating comprehensive pull requests with clear descriptions, self-review checklists, testing evidence, and context. Ensures reviewers have everything needed for effective review.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: workflow
---

# Requesting Code Review

Prepare comprehensive code review requests that make it easy for reviewers to provide effective feedback.

## Overview

A good code review request provides reviewers with all the context and information they need to understand, evaluate, and provide feedback on your changes efficiently.

## Instructions

### Phase 1: Pre-Review Preparation

Before requesting review, ensure your code is ready:

1. **Self-Review**:
   - Review every changed file
   - Look for obvious issues
   - Check for debug code or comments
   - Verify consistent style
   - Ensure tests pass

2. **Run Quality Checks**:
   ```bash
   # Run tests
   pytest

   # Run linter
   flake8 . --max-line-length=100

   # Check code coverage
   pytest --cov=src --cov-report=term-missing

   # Run type checker (if applicable)
   mypy src/

   # Run security checker
   bandit -r src/
   ```

3. **Clean Up Commits**:
   - Ensure commit messages are clear
   - Consider squashing WIP commits
   - Rebase on latest main/master if needed
   ```bash
   git rebase -i origin/main
   ```

4. **Update Documentation**:
   - README updates
   - API documentation
   - Inline comments
   - CHANGELOG entry

### Phase 2: Create Pull Request

#### PR Title

Follow conventional commit format:
```
<type>(<scope>): <brief description>

Examples:
feat(auth): add OAuth2 authentication
fix(api): handle null values in user endpoint
refactor(database): extract query builder
docs(readme): update installation instructions
```

#### PR Description Template

```markdown
## Summary

[2-3 sentence overview of what this PR does and why]

## Motivation

[Why is this change needed? What problem does it solve?]

Closes #[issue-number]

## Changes Made

### Added
- [Feature or functionality added]
- [Another addition]

### Changed
- [Modified behavior or implementation]
- [Another change]

### Fixed
- [Bug fixed]
- [Another fix]

### Removed
- [Deprecated or removed functionality]

## Technical Approach

[Explanation of how the change was implemented]

**Key Design Decisions**:
- [Decision 1 and rationale]
- [Decision 2 and rationale]

**Alternatives Considered**:
- [Alternative approach]: [Why not chosen]

## Testing

### Test Coverage
- Unit tests: [X new tests, Y modified]
- Integration tests: [X new tests]
- Coverage: [X%]

### Manual Testing Performed

- [ ] Tested happy path
- [ ] Tested edge cases
- [ ] Tested error conditions
- [ ] Tested with different data sets
- [ ] Verified in different environments

**Test Steps**:
1. [Step 1]
2. [Step 2]
3. Expected result: [what should happen]

### Test Results

```bash
$ pytest -v
======================== test session starts ========================
collected 45 items

tests/test_feature.py::test_function_happy_path PASSED        [ 2%]
tests/test_feature.py::test_function_edge_case PASSED         [ 4%]
[...]

======================== 45 passed in 2.34s =========================
```

## Screenshots/Demo

[If UI changes, include before/after screenshots]

**Before**:
[Image or description]

**After**:
[Image or description]

## Performance Impact

[Describe any performance implications]

**Benchmarks** (if applicable):
- [Metric]: [Before] → [After]
- [Load test results]

## Security Considerations

- [ ] No sensitive data exposed
- [ ] Input validation added
- [ ] Authentication/authorization checked
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Dependencies checked for vulnerabilities

## Database Changes

[If applicable]

**Migrations**:
- `migrations/001_add_user_table.sql`

**Rollback Plan**:
- Migration is reversible
- [Describe rollback steps]

## Breaking Changes

[If applicable]

⚠️ **BREAKING**: [Description of breaking change]

**Migration Guide**:
- [Instructions for users to update their code]

## Dependencies

**New Dependencies Added**:
- `library-name@version`: [Why needed]

**Updated Dependencies**:
- `library-name`: `old-version` → `new-version`

## Deployment Notes

[Any special considerations for deployment]

**Configuration Changes**:
- [New environment variable]: [Description]

**Deployment Steps**:
1. [Step 1]
2. [Step 2]

**Rollback Steps**:
1. [How to revert if issues arise]

## Review Focus Areas

Please pay special attention to:
- [ ] [Specific file or function]: [Concern or question]
- [ ] [Algorithm or logic]: [Want validation of approach]
- [ ] [Error handling]: [Want to ensure edge cases covered]

## Questions for Reviewers

1. [Question about design decision]
2. [Question about alternative approach]
3. [Question about best practice]

## Checklist

### Code Quality
- [ ] Code follows project style guidelines
- [ ] No commented-out code or debug statements
- [ ] Functions are focused and small
- [ ] Variable names are descriptive
- [ ] Complex logic is commented
- [ ] No code duplication

### Testing
- [ ] All tests pass locally
- [ ] New functionality has tests
- [ ] Edge cases are tested
- [ ] Error conditions are tested
- [ ] Test coverage is adequate

### Documentation
- [ ] Public APIs are documented
- [ ] README updated if needed
- [ ] CHANGELOG updated
- [ ] Inline comments added for complex logic
- [ ] Breaking changes documented

### Security
- [ ] No hardcoded secrets
- [ ] Input is validated
- [ ] Authentication is checked
- [ ] Authorization is enforced
- [ ] Dependencies are secure

### Performance
- [ ] No obvious performance issues
- [ ] Database queries are efficient
- [ ] Caching is used appropriately
- [ ] No memory leaks

## Related PRs/Issues

- Related to #[issue-number]
- Depends on #[pr-number]
- Follows up on #[pr-number]

## Post-Merge Tasks

- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Update user documentation
- [ ] Notify stakeholders

---

**How to Review This PR**:

1. Check out the branch: `git checkout feature/branch-name`
2. Install dependencies: `npm install` or `pip install -r requirements.txt`
3. Run tests: `pytest` or `npm test`
4. Test manually following steps in "Manual Testing Performed"
5. Review code focusing on areas mentioned in "Review Focus Areas"

**Estimated Review Time**: [X minutes/hours]
```

### Phase 3: Request Reviews

1. **Assign Reviewers**:
   - Choose reviewers familiar with the code area
   - Request at least one senior engineer for significant changes
   - Tag domain experts if applicable

2. **Add Labels**:
   - Priority: `priority: high`, `priority: medium`, `priority: low`
   - Type: `bug`, `feature`, `refactor`, `docs`
   - Status: `needs review`, `work in progress`
   - Size: `size: small`, `size: medium`, `size: large`

3. **Notify Reviewers**:
   - Post in relevant Slack channel
   - @mention reviewers if urgent
   - Provide context in notification

### Phase 4: Respond to Feedback

When reviewers provide feedback:

1. **Acknowledge Feedback**:
   ```markdown
   > Reviewer: Should this function handle null values?

   Good catch! Added null check in commit abc123f.
   ```

2. **Make Requested Changes**:
   - Address all comments
   - Push new commits or force-push if squashing
   - Mark conversations as resolved

3. **Explain Decisions**:
   ```markdown
   > Reviewer: Why not use approach X?

   I considered approach X, but went with Y because:
   - Reason 1
   - Reason 2

   Open to changing if you feel strongly!
   ```

4. **Request Re-Review**:
   ```markdown
   @reviewer Changes made based on your feedback:
   - Fixed null handling in `process_data()`
   - Added test for edge case
   - Refactored for readability

   Please take another look when you have time. Thanks!
   ```

## Self-Review Checklist

Before requesting review, check:

### Code Quality
- [ ] All functions have clear purpose
- [ ] No duplicate code
- [ ] No magic numbers or strings
- [ ] Error handling is comprehensive
- [ ] Code is readable without comments, comments explain why not what
- [ ] No TODOs or FIXMEs (or they're documented with tickets)

### Testing
- [ ] All tests pass
- [ ] New code is tested
- [ ] Tests are meaningful, not just for coverage
- [ ] Edge cases are covered
- [ ] Error conditions are tested

### Security
- [ ] No secrets in code
- [ ] User input is validated
- [ ] SQL queries are parameterized
- [ ] Authentication/authorization is checked

### Performance
- [ ] No N+1 query problems
- [ ] Efficient algorithms used
- [ ] Large data sets handled appropriately
- [ ] No obvious memory leaks

### Compatibility
- [ ] Backward compatible (or breaking changes documented)
- [ ] Works in all supported environments
- [ ] Database migrations are safe

## Tips for Effective Review Requests

### Make it Easy for Reviewers

- **Keep PRs small**: <400 lines of changes is ideal
- **One concern per PR**: Don't mix refactoring with new features
- **Provide context**: Explain why, not just what
- **Include test results**: Show that it works
- **Highlight important areas**: Point out complex or risky changes

### Good vs Bad PR Descriptions

**Bad**:
```
fix: update code

Made some changes to fix the issue.
```

**Good**:
```
fix(auth): prevent session fixation vulnerability

Previously, session IDs were not regenerated on login, allowing session
fixation attacks. This fix regenerates the session ID on authentication.

Changes:
- Regenerate session on login
- Add test for session fixation
- Update session configuration

Security: Fixes CVE-2024-XXXX
```

### Writing for Your Audience

**For Junior Reviewers**:
- Explain design decisions
- Link to relevant documentation
- Describe the "why" in detail

**For Senior Reviewers**:
- Focus on architecture and trade-offs
- Ask for guidance on approach
- Highlight areas where you need expertise

**For Product/PM Reviewers**:
- Explain user-facing changes
- Include screenshots/demos
- Describe impact on users

## Output Format

After creating the PR, provide a summary:

```
## Code Review Request Created

**PR Number**: #[number]
**Branch**: [branch-name]
**Reviewers**: [@reviewer1, @reviewer2]

**Summary**: [Brief description]

**Changes**:
- Files changed: [count]
- Lines added: [count]
- Lines removed: [count]

**Testing**:
- Tests passing: ✅
- Coverage: [X%]
- Manual testing: ✅

**Next Steps**:
- Awaiting review from [@reviewers]
- Will address feedback promptly
- Target merge: [date]

**PR Link**: [URL]
```

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| PR too large | Split into multiple smaller PRs |
| Unclear purpose | Improve description with more context |
| Missing tests | Add comprehensive test coverage |
| Merge conflicts | Rebase on main/master |
| Failing CI checks | Fix issues before requesting review |
| No description | Use the template above |

## Guidelines

- **Respect reviewer's time**: Make PRs easy to review
- **Be responsive**: Address feedback promptly
- **Be open to feedback**: Don't be defensive
- **Learn from reviews**: Reviews are learning opportunities
- **Say thank you**: Appreciate the reviewer's time
- **Return the favor**: Review others' PRs
