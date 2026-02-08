---
name: systematic-debugging
description: >
  Four-phase root cause analysis methodology for debugging complex issues. Systematically reproduces bugs, forms hypotheses, conducts experiments, and validates fixes. Adapted from obra/superpowers for thorough problem investigation.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: debugging
---

# Systematic Debugging

A rigorous four-phase methodology for debugging complex issues through systematic root cause analysis.

## Overview

This skill implements a structured approach to debugging that ensures thorough investigation and prevents jumping to conclusions. It is especially valuable for complex, hard-to-reproduce, or system-spanning bugs.

## The Four Phases

### Phase 1: Reproduce the Issue

**Goal**: Consistently reproduce the bug to understand its behavior.

**Steps**:
1. **Gather Information**:
   - What is the expected behavior?
   - What is the actual behavior?
   - When did the issue first appear?
   - Can you provide an example or screenshot?
   - What are the exact steps to reproduce?

2. **Attempt Reproduction**:
   - Follow the reported steps exactly
   - Try variations of the steps
   - Note any environmental factors (OS, browser, time of day, data state)
   - Document success rate if intermittent

3. **Minimize the Reproduction Case**:
   - Remove unnecessary steps
   - Simplify the input data
   - Isolate the minimal code path that triggers the issue
   - Create a minimal reproducible example

4. **Document Reproduction Steps**:
   ```
   ## Reproduction Steps
   1. [Step 1]
   2. [Step 2]
   3. [Step 3]

   **Expected**: [Expected result]
   **Actual**: [Actual result]
   **Frequency**: [Always/Intermittent/Rare]
   **Environment**: [Relevant details]
   ```

### Phase 2: Form Hypotheses

**Goal**: Generate possible explanations for the bug.

**Steps**:
1. **Analyze the Failure Point**:
   - Where exactly does the code fail?
   - What is the state at the failure point?
   - What assumptions might be violated?

2. **Work Backwards**:
   - What code executes immediately before the failure?
   - What data flows into the failure point?
   - What external factors could affect behavior?

3. **Generate Multiple Hypotheses**:
   - Don't stop at the first explanation
   - Consider both code and environmental factors
   - Think about timing, state, concurrency issues

4. **Rank Hypotheses**:
   - Most likely explanations first
   - Consider what would be easiest to test

**Example Hypotheses**:
```
## Hypotheses

1. **Null Pointer Exception** (HIGH PROBABILITY)
   - The user object might be null when accessed
   - Could happen if session expires mid-request
   - Would explain intermittent nature

2. **Race Condition** (MEDIUM PROBABILITY)
   - Two threads might be modifying shared state
   - Explains why it happens occasionally
   - More common under high load

3. **Off-by-One Error** (LOW PROBABILITY)
   - Array index might exceed bounds
   - Would only happen with specific data
   - Doesn't explain intermittent nature well
```

### Phase 3: Conduct Experiments

**Goal**: Test each hypothesis systematically to identify the root cause.

**Steps**:
1. **Design Experiments**:
   - What would prove or disprove each hypothesis?
   - What data would you need to see?
   - What modifications could isolate the issue?

2. **Test One Hypothesis at a Time**:
   - Don't change multiple things simultaneously
   - Make changes that are easy to revert
   - Keep detailed notes of what you try

3. **Gather Evidence**:
   - Add logging at critical points
   - Use debugger to inspect state
   - Add assertions to validate assumptions
   - Instrument code to measure timing

4. **Document Results**:
   ```
   ## Experiment Log

   ### Experiment 1: Test null pointer hypothesis
   - **Method**: Added null check and logging before user access
   - **Result**: Log showed user was null in 3/10 reproduction attempts
   - **Conclusion**: Hypothesis confirmed - user can be null

   ### Experiment 2: Investigate why user is null
   - **Method**: Added logging at session creation and destruction
   - **Result**: Session expires 30 seconds into long-running request
   - **Conclusion**: Root cause found - session timeout too short
   ```

5. **Iterate**:
   - If hypothesis is disproven, move to the next
   - If partially proven, refine the hypothesis
   - If proven, investigate why that condition occurs

### Phase 4: Validate the Fix

**Goal**: Ensure the fix solves the problem without introducing new issues.

**Steps**:
1. **Implement the Fix**:
   - Make minimal necessary changes
   - Consider side effects
   - Think about edge cases

2. **Verify the Original Issue is Resolved**:
   - Test the exact reproduction case
   - Test variations and edge cases
   - Verify the fix works consistently

3. **Regression Testing**:
   - Run existing test suite
   - Test related functionality
   - Look for new issues introduced by the fix

4. **Expand Test Coverage**:
   - Add test cases for the bug
   - Add tests for related edge cases
   - Ensure the bug can't reoccur silently

5. **Document the Fix**:
   ```
   ## Fix Validation

   **Root Cause**: Session timeout (30s) shorter than max request time (60s)

   **Fix Applied**: Increased session timeout to 300s and added session refresh mechanism

   **Validation Results**:
   - Original reproduction case: 0/100 failures ✓
   - Edge case (concurrent requests): 0/50 failures ✓
   - Regression tests: All pass ✓
   - New test added: test_session_refresh_during_long_request ✓

   **Monitoring**: Added metric for session expirations during active requests
   ```

## Output Format

When using this skill, provide a structured report:

```
# Systematic Debugging Report

## Issue Summary
[Brief description of the problem]

---

## Phase 1: Reproduction
[Reproduction steps and results]

---

## Phase 2: Hypotheses
[List of hypotheses with probability rankings]

---

## Phase 3: Experiments
[Detailed experiment log with results]

---

## Phase 4: Validation
[Fix implementation and validation results]

---

## Summary
- **Root Cause**: [The actual cause]
- **Fix**: [What was changed]
- **Confidence**: [High/Medium/Low]
- **Monitoring**: [How to detect if it happens again]
```

## When to Use This Skill

Use systematic debugging when:
- The bug is intermittent or hard to reproduce
- Quick fixes haven't worked
- The root cause is not obvious
- The issue affects critical functionality
- Multiple developers have investigated without success
- The issue spans multiple systems or components

## Tips for Success

- **Don't skip phases**: Each phase builds on the previous one
- **Document everything**: Future you will thank present you
- **Be patient**: Systematic debugging takes time but finds the real issue
- **Challenge assumptions**: The bug might not be where you think it is
- **Collaborate**: Share your hypotheses and experiments with others
- **Use tools**: Debuggers, profilers, log analyzers are your friends
- **Think scientifically**: Form hypotheses, test them, draw conclusions

## Common Pitfalls to Avoid

- Jumping to a fix without understanding root cause
- Testing multiple hypotheses simultaneously
- Making changes without documenting them
- Assuming you know the cause without evidence
- Fixing symptoms instead of root causes
- Not validating that the fix actually works
