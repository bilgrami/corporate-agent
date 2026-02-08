---
name: refactor
description: >
  Refactor code to improve readability, maintainability, and structure without changing behavior. Applies DRY principles, improves naming, reduces complexity, and decomposes large functions. Changes are automatically applied to files.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: development
  auto_apply: true
---

# Code Refactoring

Refactor the specified code to improve its quality, maintainability, and readability without changing its external behavior.

## Instructions

1. **Analyze Current Code**:
   - Read all relevant files completely
   - Identify code smells and areas for improvement
   - Understand the current behavior that must be preserved

2. **Identify Refactoring Opportunities**:
   - **Duplication**: Look for repeated code that can be extracted
   - **Complexity**: Find long functions, deep nesting, or complex conditionals
   - **Naming**: Identify unclear variable/function names
   - **Structure**: Check for poor separation of concerns
   - **Dead Code**: Locate unused variables, functions, or imports

3. **Plan Refactoring**:
   - Prioritize high-impact improvements
   - Ensure each refactoring is behavior-preserving
   - Consider breaking large refactorings into steps

4. **Apply Refactorings**:
   Use the Edit tool to apply these common refactorings:

   - **Extract Method**: Pull out repeated or complex code into functions
   - **Rename**: Give clear, descriptive names to variables and functions
   - **Simplify Conditionals**: Reduce nested if statements, use early returns
   - **Remove Duplication**: Apply DRY principle
   - **Decompose Functions**: Break large functions into smaller, focused ones
   - **Improve Structure**: Organize code logically, group related functionality
   - **Remove Dead Code**: Delete unused imports, variables, functions

5. **Verify Behavior Preservation**:
   - Ensure external behavior remains unchanged
   - Document any assumptions made

## Refactoring Patterns

### Extract Function
```python
# Before
def process_order(order):
    total = 0
    for item in order.items:
        total += item.price * item.quantity
    tax = total * 0.08
    return total + tax

# After
def calculate_subtotal(items):
    return sum(item.price * item.quantity for item in items)

def calculate_tax(subtotal):
    return subtotal * 0.08

def process_order(order):
    subtotal = calculate_subtotal(order.items)
    tax = calculate_tax(subtotal)
    return subtotal + tax
```

### Simplify Conditionals
```python
# Before
def can_access(user):
    if user is not None:
        if user.is_active:
            if user.has_permission('read'):
                return True
    return False

# After
def can_access(user):
    if user is None:
        return False
    return user.is_active and user.has_permission('read')
```

### Improve Naming
```python
# Before
def calc(x, y):
    return x * y * 0.08

# After
def calculate_sales_tax(price, quantity):
    subtotal = price * quantity
    return subtotal * TAX_RATE
```

## Output Format

After refactoring, provide:

```
## Refactoring Summary

**Scope**: [What was refactored]

**Improvements Made**:
- [Category]: [Specific improvement]

**Files Modified**:
- [file path]: [summary of changes]

**Behavior Verification**:
[Explanation of how behavior was preserved]

**Testing Recommendations**:
- [Existing tests to run to verify no regressions]
```

## Guidelines

- **Preserve behavior**: Never change external functionality
- **One refactoring at a time**: Make focused, logical changes
- **Maintain style**: Follow existing code conventions
- **Don't over-engineer**: Keep it simple
- **Consider context**: Refactor appropriately for the codebase size and complexity
- **Test-friendly**: Make code easier to test
- **Document when needed**: Add comments for non-obvious logic
