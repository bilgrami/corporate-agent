---
name: writing-plans
description: >
  Create detailed implementation plans for features and projects. Breaks down complex tasks into manageable steps, identifies dependencies, estimates effort, and provides clear specifications for implementation.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: planning
---

# Writing Implementation Plans

Create comprehensive, actionable implementation plans for features, projects, or complex tasks.

## Overview

A good implementation plan bridges the gap between requirements and code. It breaks down complex work into manageable pieces, identifies risks early, and provides a roadmap for execution.

## Instructions

1. **Understand the Requirement**:
   - What problem does this solve?
   - Who are the users/stakeholders?
   - What are the success criteria?
   - What are the constraints (time, budget, technical)?

2. **Analyze the Current System**:
   - Read relevant existing code
   - Understand current architecture
   - Identify components that will be affected
   - Note any technical debt or blockers

3. **Design the Solution**:
   - Propose the high-level approach
   - Consider alternative approaches
   - Identify major components and their interactions
   - Define data models and APIs

4. **Break Down into Tasks**:
   - Decompose into small, concrete tasks
   - Each task should be completable in 1-4 hours
   - Order tasks by dependencies
   - Identify what can be done in parallel

5. **Identify Risks and Mitigations**:
   - Technical risks
   - Integration points
   - Performance concerns
   - Security considerations

6. **Write the Plan**:
   - Use clear, actionable language
   - Include code examples where helpful
   - Reference specific files and functions
   - Provide enough detail for another developer to execute

## Implementation Plan Template

```markdown
# Implementation Plan: [Feature Name]

## Overview

**Goal**: [What we're building and why]

**User Story**: As a [user type], I want to [action] so that [benefit]

**Success Criteria**:
- [ ] [Measurable criterion 1]
- [ ] [Measurable criterion 2]
- [ ] [Measurable criterion 3]

---

## Current State Analysis

**Existing Components**:
- `[file/path.py]`: [Description of relevant existing code]
- `[other/file.py]`: [Description]

**Dependencies**:
- [External library or service]
- [Database tables or models]

**Known Issues/Constraints**:
- [Limitation or constraint to work around]

---

## Proposed Solution

### High-Level Approach
[Paragraph describing the overall approach and architecture]

### Architecture Diagram
```
[ASCII diagram or description of component interactions]
┌─────────────┐      ┌──────────────┐      ┌──────────┐
│   Client    │─────▶│   API Layer  │─────▶│ Database │
└─────────────┘      └──────────────┘      └──────────┘
```

### Alternative Approaches Considered

**Option 1**: [Alternative approach]
- Pros: [Benefits]
- Cons: [Drawbacks]
- Decision: [Why not chosen]

**Option 2**: [Selected approach]
- Pros: [Benefits]
- Cons: [Drawbacks]
- Decision: ✓ Selected because [reason]

---

## Technical Design

### Data Models

```python
class NewModel:
    """[Description of what this represents]"""
    id: int
    field1: str
    field2: datetime
    # [Additional fields]
```

### API Endpoints

**POST /api/resource**
- Request: `{"field": "value"}`
- Response: `{"id": 1, "status": "success"}`
- Authentication: Required
- Validation: [Rules]

### Key Functions/Methods

```python
def key_function(param1: str, param2: int) -> dict:
    """
    [Description of what this function does]

    Args:
        param1: [Description]
        param2: [Description]

    Returns:
        [Description of return value]
    """
    pass
```

---

## Implementation Tasks

### Phase 1: Foundation
- [ ] **Task 1.1**: Setup database migrations
  - Create migration file for new tables
  - Add indexes for performance
  - Files: `migrations/`, `models/`
  - Estimate: 1 hour

- [ ] **Task 1.2**: Create data models
  - Implement `NewModel` class
  - Add validation methods
  - Files: `models/new_model.py`
  - Estimate: 2 hours

### Phase 2: Core Logic
- [ ] **Task 2.1**: Implement core business logic
  - Create `process_data()` function
  - Handle edge cases
  - Files: `services/processor.py`
  - Estimate: 3 hours
  - Depends on: Task 1.2

- [ ] **Task 2.2**: Add error handling
  - Define custom exceptions
  - Add try/catch blocks
  - Files: `exceptions.py`, `services/processor.py`
  - Estimate: 1 hour

### Phase 3: API Layer
- [ ] **Task 3.1**: Create API endpoints
  - Implement POST /api/resource
  - Add request validation
  - Files: `api/routes.py`
  - Estimate: 2 hours
  - Depends on: Task 2.1

- [ ] **Task 3.2**: Add authentication/authorization
  - Verify user permissions
  - Add rate limiting
  - Files: `api/auth.py`
  - Estimate: 2 hours

### Phase 4: Testing
- [ ] **Task 4.1**: Write unit tests
  - Test business logic functions
  - Test edge cases
  - Files: `tests/test_processor.py`
  - Estimate: 3 hours

- [ ] **Task 4.2**: Write integration tests
  - Test API endpoints
  - Test database operations
  - Files: `tests/test_api.py`
  - Estimate: 2 hours

### Phase 5: Documentation & Deployment
- [ ] **Task 5.1**: Update documentation
  - API documentation
  - README updates
  - Files: `docs/`
  - Estimate: 1 hour

- [ ] **Task 5.2**: Deploy to staging
  - Run migrations
  - Deploy code
  - Verify functionality
  - Estimate: 1 hour

**Total Estimated Time**: 18 hours (2-3 days)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Database migration fails in production | Low | High | Test migration on staging first, have rollback plan |
| API performance issues with large data | Medium | Medium | Add pagination, implement caching |
| Integration with Service X fails | Medium | High | Create mock for testing, coordinate with Service X team |

---

## Testing Strategy

**Unit Tests**:
- Test all business logic functions
- Mock external dependencies
- Cover edge cases and error conditions

**Integration Tests**:
- Test API endpoints end-to-end
- Test database operations
- Verify authentication/authorization

**Manual Testing Checklist**:
- [ ] Test happy path
- [ ] Test with invalid input
- [ ] Test with edge case data
- [ ] Test error scenarios
- [ ] Verify performance with large datasets

---

## Performance Considerations

- Expected load: [X requests/second]
- Database indexes needed: [list]
- Caching strategy: [description]
- Optimization opportunities: [list]

---

## Security Considerations

- [ ] Input validation and sanitization
- [ ] Authentication required on all endpoints
- [ ] Authorization checks for sensitive operations
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output escaping)
- [ ] Rate limiting to prevent abuse

---

## Rollout Plan

1. **Development**: Implement tasks in order
2. **Code Review**: Submit PR for review
3. **Staging Deployment**: Deploy to staging environment
4. **Testing**: Run all tests, perform manual QA
5. **Production Deployment**: Deploy during low-traffic window
6. **Monitoring**: Watch metrics for anomalies
7. **Rollback Plan**: If issues arise, revert deployment

---

## Monitoring & Observability

**Metrics to Track**:
- Request count and response times
- Error rates
- Database query performance
- [Feature-specific metrics]

**Logs to Add**:
- Log all API requests
- Log errors with context
- Log key business events

**Alerts to Configure**:
- Alert on error rate > 5%
- Alert on response time > 2s
- Alert on [specific condition]

---

## Future Enhancements

[Features that are out of scope for this iteration but should be considered later]
- [Enhancement 1]
- [Enhancement 2]

---

## Questions & Decisions Needed

- [ ] **Question 1**: [Question that needs answering]
  - Decision: [Answer when decided]

- [ ] **Question 2**: [Another question]
  - Decision: [Answer when decided]

---

## References

- [Link to requirements document]
- [Link to design doc]
- [Link to related code]
- [Link to API documentation]
```

## Output Format

Save the implementation plan to:
```
docs/implementation_plans/[feature-name]-plan.md
```

Provide a summary:
```
## Implementation Plan Created

**Feature**: [Name]
**Estimated Effort**: [X hours/days]
**Number of Tasks**: [count]
**Key Risks**: [Brief list]
**Ready for Implementation**: [Yes/No and why]

**Next Steps**:
1. [First action to take]
2. [Second action]
```

## Guidelines

- **Be specific**: Avoid vague descriptions like "update the code"
- **Be realistic**: Don't underestimate complexity
- **Be thorough**: Consider edge cases, errors, testing
- **Be practical**: Focus on actionable tasks
- **Include examples**: Show code snippets for clarity
- **Think ahead**: Consider maintenance, monitoring, scaling
- **Collaborate**: Identify points where you need input from others
- **Stay flexible**: Plans may need adjustment as you learn more

## Types of Plans

### Feature Plan
Focus on user-facing functionality and value delivery

### Refactoring Plan
Focus on code quality improvements without changing behavior

### Migration Plan
Focus on moving from old system to new system safely

### Bug Fix Plan
Focus on understanding root cause and preventing recurrence

### Architecture Change Plan
Focus on system-wide changes and their ripple effects

## Tips for Success

- **Start with why**: Clearly articulate the problem being solved
- **Think in layers**: UI, API, business logic, data
- **Consider the user**: How will they experience this?
- **Plan for failure**: What could go wrong? How will you handle it?
- **Review existing code**: Don't plan in a vacuum
- **Get feedback early**: Share the plan before implementation
- **Update the plan**: As you learn, adjust the plan
