---
name: executing-plans
description: >
  Execute implementation plans systematically by working through tasks in order, tracking progress, handling blockers, and validating completion. Ensures plans are followed accurately and efficiently.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: planning
---

# Executing Implementation Plans

Systematically execute implementation plans by working through tasks in order, tracking progress, and ensuring quality.

## Overview

This skill helps you execute implementation plans methodically, ensuring nothing is missed and the plan is followed accurately. It emphasizes breaking down work into small steps, validating each step, and maintaining focus.

## Instructions

1. **Load the Plan**:
   - Read the implementation plan document
   - Understand the overall goal and approach
   - Review all tasks and their dependencies
   - Note any questions or unclear areas

2. **Prepare for Execution**:
   - Set up development environment
   - Create a feature branch
   - Ensure you have access to required resources
   - Review related code and documentation

3. **Work Through Tasks Systematically**:
   - Start with the first task
   - Complete it fully before moving to the next
   - Check off tasks as you complete them
   - Update the plan if you discover new tasks

4. **Validate Each Step**:
   - Run tests after each change
   - Verify functionality works as expected
   - Review code quality
   - Commit working code frequently

5. **Handle Blockers**:
   - Document blockers when encountered
   - Seek help if needed
   - Work on non-blocked tasks while waiting
   - Update plan with resolution

6. **Final Validation**:
   - Run full test suite
   - Manual testing of the feature
   - Code review checklist
   - Update documentation

## Execution Workflow

### Phase 1: Setup

```bash
# Create feature branch
git checkout -b feature/[feature-name]

# Verify development environment
# Run existing tests to ensure baseline
pytest
```

**Checklist**:
- [ ] Feature branch created
- [ ] Development environment ready
- [ ] Existing tests pass
- [ ] Plan reviewed and understood

### Phase 2: Execute Tasks in Order

For each task in the plan:

#### Step 1: Read the Task Thoroughly
- Understand what needs to be done
- Note the files that need to be modified
- Check for dependencies on previous tasks
- Estimate actual time vs planned time

#### Step 2: Implement the Task
- Make focused, incremental changes
- Follow the plan's technical design
- Write clean, readable code
- Add comments for complex logic

#### Step 3: Test the Implementation
```python
# Write or update tests for this task
def test_new_functionality():
    """Test the feature implemented in this task"""
    result = new_function(test_input)
    assert result == expected_output
```

Run tests:
```bash
pytest tests/test_new_feature.py -v
```

#### Step 4: Commit the Work
```bash
git add [files-modified]
git commit -m "feat: [task description]

Implements task X.Y from implementation plan.
[Brief description of changes]"
```

#### Step 5: Update the Plan
Mark the task as complete in the plan:
```markdown
- [x] **Task 1.1**: Setup database migrations
  - Status: ✅ Complete
  - Actual time: 1.5 hours
  - Notes: Added additional index for performance
```

#### Step 6: Move to Next Task
Repeat for each task.

### Phase 3: Integration Testing

After completing all tasks:

```bash
# Run full test suite
pytest

# Run linter
flake8 .

# Check code coverage
pytest --cov=src --cov-report=html
```

**Validation Checklist**:
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Code coverage meets standards
- [ ] No linter errors
- [ ] Manual testing completed

### Phase 4: Final Review

1. **Self Code Review**:
   - Review all changed files
   - Check for code smells
   - Verify error handling
   - Ensure consistent style

2. **Documentation Update**:
   - Update API documentation
   - Update README if needed
   - Add inline comments for complex code
   - Update changelog

3. **Prepare for Review**:
   - Clean up commit history if needed
   - Write clear PR description
   - List testing performed
   - Note any deviations from plan

## Handling Common Situations

### When You Encounter a Blocker

1. **Document the Blocker**:
   ```markdown
   ## Blockers

   **Blocker 1**: Cannot integrate with Service X API
   - Status: 🔴 Blocked
   - Reason: API credentials not available
   - Impact: Tasks 3.1 and 3.2 blocked
   - Action: Requested credentials from team lead
   - Workaround: Created mock for testing
   ```

2. **Find Alternative Work**:
   - Work on tasks that don't depend on the blocker
   - Write tests with mocks
   - Improve documentation
   - Refactor related code

3. **Update the Plan**:
   - Reorder tasks if needed
   - Add notes about the blocker
   - Document workarounds

### When the Plan Needs Adjustment

Plans are not set in stone. Adjust when needed:

```markdown
## Plan Adjustments

**Change 1**: Added Task 2.3 - Implement caching
- Reason: Performance testing revealed slow queries
- Impact: +2 hours
- Priority: High

**Change 2**: Removed Task 4.3 - Add feature Y
- Reason: Requirement changed, now out of scope
- Impact: -3 hours

**Updated Timeline**: Original 18 hours → Adjusted 17 hours
```

### When You Discover Issues

1. **Fix Critical Issues Immediately**:
   - Security vulnerabilities
   - Data corruption risks
   - Major bugs

2. **Log Non-Critical Issues**:
   ```markdown
   ## Issues Discovered

   - **Issue 1**: Related function has inefficient algorithm
     - Severity: Low
     - Action: Created ticket #123 for future improvement

   - **Issue 2**: Missing error handling in auth module
     - Severity: Medium
     - Action: Will fix after current plan completes
   ```

## Progress Tracking

### Daily Progress Report

At end of each work session:

```markdown
## Progress Report - [Date]

**Completed Today**:
- [x] Task 2.1: Implemented core business logic
- [x] Task 2.2: Added error handling

**In Progress**:
- [ ] Task 3.1: Creating API endpoints (60% complete)

**Blockers**:
- None

**Tomorrow's Plan**:
- Complete Task 3.1
- Start Task 3.2

**Notes**:
- Task 2.1 took longer than estimated due to edge cases
- Discovered need for additional validation (added Task 2.3)

**Time Spent**: 6 hours
**Remaining Estimate**: 8 hours
```

### Overall Progress Tracker

```markdown
## Implementation Progress

**Overall Status**: 🟡 In Progress

**Phase Completion**:
- [x] Phase 1: Foundation (100%)
- [x] Phase 2: Core Logic (100%)
- [ ] Phase 3: API Layer (50%)
- [ ] Phase 4: Testing (0%)
- [ ] Phase 5: Documentation & Deployment (0%)

**Metrics**:
- Tasks completed: 8/20 (40%)
- Time spent: 12 hours
- Time remaining: ~10 hours
- Original estimate: 18 hours
- Revised estimate: 22 hours

**On Track**: No - Additional requirements added
```

## Quality Checks

Before marking a task complete:

- [ ] Code works as intended
- [ ] Tests written and passing
- [ ] No obvious bugs or edge cases missed
- [ ] Code is readable and well-organized
- [ ] Follows project style guidelines
- [ ] Error handling implemented
- [ ] Changes committed with clear message
- [ ] Documentation updated if needed

## Output Format

As you execute, maintain an execution log:

```markdown
# Execution Log: [Feature Name]

**Plan**: [Link to implementation plan]
**Branch**: feature/[name]
**Start Date**: [Date]
**Target Completion**: [Date]

---

## Execution Timeline

### [Date] - Phase 1: Foundation

**Tasks Completed**:
- ✅ Task 1.1: Setup database migrations (1h 30m)
  - Files modified: `migrations/001_create_tables.sql`
  - Tests: All migrations run successfully
  - Commit: abc123f

- ✅ Task 1.2: Create data models (2h)
  - Files created: `models/new_model.py`
  - Tests: `tests/test_models.py` - 8 tests passing
  - Commit: def456a

**Issues Encountered**: None

**Deviations from Plan**: Added additional index for performance

---

### [Date] - Phase 2: Core Logic

[Continue logging each phase]

---

## Final Summary

**Status**: ✅ Complete / 🟡 In Progress / 🔴 Blocked

**Completion Date**: [Date]

**Results**:
- All tasks completed
- All tests passing (95% coverage)
- Feature deployed to staging
- Documentation updated

**Metrics**:
- Planned time: 18 hours
- Actual time: 22 hours
- Tasks completed: 20/20
- Bugs found during testing: 3 (all fixed)

**Lessons Learned**:
- [What went well]
- [What could be improved]
- [Unexpected challenges]

**Next Steps**:
- [ ] Code review
- [ ] Deploy to production
- [ ] Monitor metrics
```

## Guidelines

- **Follow the plan**: Don't skip steps or tasks
- **Stay focused**: Complete one task fully before moving to next
- **Test continuously**: Don't accumulate untested code
- **Commit frequently**: Small, working commits are better than large ones
- **Document as you go**: Don't leave documentation for the end
- **Communicate progress**: Keep stakeholders informed
- **Be flexible**: Adjust plan when you learn new information
- **Maintain quality**: Speed is not worth sacrificing quality
- **Ask for help**: Don't struggle in silence if blocked

## Tips for Success

- **Time-box tasks**: If a task takes much longer than estimated, reassess
- **Take breaks**: Regular breaks maintain focus and quality
- **Review your work**: Self-review before considering task complete
- **Keep the end goal in mind**: Don't get lost in details
- **Celebrate progress**: Acknowledge completed milestones
- **Learn from deviations**: Note what caused estimates to be off
