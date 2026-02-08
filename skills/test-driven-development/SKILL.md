---
name: test-driven-development
description: >
  Implement features using RED-GREEN-REFACTOR test-driven development methodology. Writes failing tests first, implements minimal code to pass, then refactors. Ensures high test coverage and well-designed code.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: testing
---

# Test-Driven Development (TDD)

Implement features using the RED-GREEN-REFACTOR cycle of test-driven development.

## Overview

Test-Driven Development is a software development methodology where you write tests before writing the implementation code. This ensures high test coverage, better design, and confidence in your code.

## The RED-GREEN-REFACTOR Cycle

```
RED → Write a failing test
  ↓
GREEN → Write minimal code to make it pass
  ↓
REFACTOR → Improve the code while keeping tests passing
  ↓
(Repeat)
```

## Phase 1: RED - Write a Failing Test

**Goal**: Write a test for the next piece of functionality you want to add.

**Steps**:

1. **Understand the Requirement**:
   - What should the code do?
   - What are the inputs and expected outputs?
   - What edge cases need handling?

2. **Write the Test First**:
   - Test should be clear and focused on one behavior
   - Use descriptive test names
   - Test should fail because the feature doesn't exist yet

3. **Run the Test and Watch it Fail**:
   - Verify it fails for the right reason
   - The failure confirms the test is actually testing something

**Example**:
```python
# test_calculator.py
import pytest
from calculator import Calculator

def test_add_two_positive_numbers():
    """Test that calculator can add two positive numbers"""
    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5

# Running this test will fail because Calculator and add() don't exist yet
# This is expected and good!
```

## Phase 2: GREEN - Make the Test Pass

**Goal**: Write the simplest code that makes the test pass.

**Steps**:

1. **Implement Minimal Code**:
   - Don't worry about perfection
   - Don't implement features not covered by tests
   - Focus only on making this specific test pass

2. **Run the Test**:
   - Verify the test now passes
   - Run all tests to ensure no regression

3. **Resist the Urge to Refactor**:
   - Save improvements for the refactor phase
   - First priority is getting to green

**Example**:
```python
# calculator.py
class Calculator:
    def add(self, a, b):
        return a + b

# This is the simplest implementation that makes the test pass
# Even if you know you'll need more features later, don't add them yet
```

## Phase 3: REFACTOR - Improve the Code

**Goal**: Clean up the code while keeping all tests passing.

**Steps**:

1. **Identify Improvements**:
   - Remove duplication
   - Improve naming
   - Simplify logic
   - Improve structure

2. **Refactor Incrementally**:
   - Make one small change at a time
   - Run tests after each change
   - If tests fail, revert and try a different approach

3. **Refactor Test Code Too**:
   - Extract common setup into fixtures
   - Remove duplication in tests
   - Improve test readability

**Example**:
```python
# After adding more operations, you might refactor:

class Calculator:
    """A simple calculator for basic arithmetic operations."""

    def add(self, a: float, b: float) -> float:
        """Add two numbers and return the result."""
        return self._validate_and_compute(a, b, lambda x, y: x + y)

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a and return the result."""
        return self._validate_and_compute(a, b, lambda x, y: x - y)

    def _validate_and_compute(self, a: float, b: float, operation):
        """Validate inputs and perform operation."""
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise TypeError("Arguments must be numbers")
        return operation(a, b)
```

## Complete TDD Workflow

### Step-by-Step Process

1. **Write a List of Test Cases**:
   ```
   - Add two positive numbers
   - Add positive and negative numbers
   - Add with zero
   - Add with floats
   - Subtract two numbers
   - Handle invalid input types
   ```

2. **For Each Test Case**:

   **RED**:
   ```python
   def test_add_positive_and_negative():
       calc = Calculator()
       result = calc.add(5, -3)
       assert result == 2
   ```

   Run test → It fails ✓

   **GREEN**:
   ```python
   # Implementation already works for this case
   # Run test → It passes ✓
   ```

   **REFACTOR**:
   ```python
   # No refactoring needed yet
   ```

   **Next test - RED**:
   ```python
   def test_add_with_invalid_type_raises_error():
       calc = Calculator()
       with pytest.raises(TypeError):
           calc.add("5", 3)
   ```

   Run test → It fails ✓

   **GREEN**:
   ```python
   class Calculator:
       def add(self, a, b):
           if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
               raise TypeError("Arguments must be numbers")
           return a + b
   ```

   Run test → It passes ✓

   **REFACTOR**:
   ```python
   # Extract validation to helper method (shown above)
   ```

## TDD Best Practices

### The Three Laws of TDD

1. **Don't write production code** until you have a failing test
2. **Don't write more test** than is sufficient to fail
3. **Don't write more production code** than is sufficient to pass the test

### What to Test

- **Test behavior, not implementation**: Focus on what the code does, not how
- **Test one thing per test**: Each test should verify one specific behavior
- **Test edge cases**: Empty inputs, null values, boundary conditions
- **Test error conditions**: Invalid inputs, exceptional situations

### What Not to Do

- Don't write all tests at once
- Don't skip the failing test step
- Don't implement features not covered by tests
- Don't skip refactoring
- Don't refactor without green tests

## Benefits of TDD

1. **High Test Coverage**: Every feature has tests by definition
2. **Better Design**: Writing tests first leads to more modular, testable code
3. **Confidence**: You know the code works and can refactor safely
4. **Documentation**: Tests serve as executable examples
5. **Faster Debugging**: Failing tests pinpoint the problem immediately
6. **Reduced Bugs**: Issues are caught early

## TDD with Different Test Types

### Unit Tests (Most Common)
```python
def test_user_full_name():
    """Test that User.full_name returns first + last name"""
    user = User(first_name="John", last_name="Doe")
    assert user.full_name == "John Doe"
```

### Integration Tests
```python
def test_user_can_be_saved_to_database():
    """Test that User can be persisted and retrieved"""
    user = User(first_name="John", last_name="Doe")
    user.save()
    retrieved = User.get(user.id)
    assert retrieved.first_name == "John"
```

### Acceptance Tests
```python
def test_user_registration_flow():
    """Test complete user registration process"""
    response = client.post('/register', data={
        'email': 'user@example.com',
        'password': 'secure123'
    })
    assert response.status_code == 302
    assert User.exists(email='user@example.com')
```

## Output Format

When using this skill, document your TDD process:

```
# TDD Implementation: [Feature Name]

## Feature Requirements
[What needs to be implemented]

## Test Cases Identified
1. [Test case 1]
2. [Test case 2]
3. [Test case 3]

---

## Cycle 1: [Test Name]

### RED
```python
[Failing test code]
```
**Status**: ❌ Test fails (expected)

### GREEN
```python
[Minimal implementation]
```
**Status**: ✅ Test passes

### REFACTOR
[Description of refactoring done, or "No refactoring needed"]
**Status**: ✅ All tests still pass

---

## Cycle 2: [Next Test Name]
[Repeat the process]

---

## Final Result

**Files Created/Modified**:
- [file path]: [description]

**Test Coverage**: [percentage or description]

**Test Summary**:
- Total tests: [count]
- Passing: [count]
- Failed: [count]

**Run Tests**:
```bash
pytest [test_file_path] -v
```
```

## Tips for Success

- **Start small**: Begin with the simplest test case
- **Baby steps**: Add one tiny piece of functionality at a time
- **Keep tests fast**: Fast tests encourage running them frequently
- **Listen to the tests**: If tests are hard to write, the design might be wrong
- **Don't skip steps**: The discipline of the cycle is important
- **Refactor regularly**: Don't let technical debt accumulate
