---
name: doc-gen
description: >
  Generate comprehensive documentation including docstrings, README files, API documentation, and code comments. Follows language-specific conventions (Google, NumPy, JSDoc) and creates clear, maintainable documentation automatically.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: documentation
  auto_apply: true
---

# Documentation Generation

Generate comprehensive documentation for code including docstrings, README files, and inline comments.

## Instructions

1. **Analyze the Code**:
   - Read all relevant source files
   - Understand the purpose, inputs, outputs, and behavior
   - Identify public APIs, functions, classes, and modules
   - Note any complex logic that needs explanation

2. **Determine Documentation Type**:
   - **Docstrings**: For functions, classes, methods, modules
   - **README**: For projects, packages, or major components
   - **Inline Comments**: For complex algorithms or non-obvious logic
   - **API Documentation**: For public interfaces

3. **Follow Language Conventions**:
   - **Python**: Google-style or NumPy-style docstrings
   - **JavaScript/TypeScript**: JSDoc comments
   - **Java**: Javadoc comments
   - **Go**: Go doc comments
   - **Ruby**: RDoc comments

4. **Apply Documentation**:
   - Use Edit tool to add docstrings to existing functions
   - Use Write tool to create README files
   - Maintain existing style and formatting

## Python Docstring Format (Google Style)

```python
def function_name(param1: str, param2: int, optional_param: bool = False) -> dict:
    """Brief one-line description of the function.

    More detailed explanation of what the function does, its purpose,
    and any important details about its behavior or usage.

    Args:
        param1: Description of the first parameter
        param2: Description of the second parameter
        optional_param: Description of optional parameter. Defaults to False.

    Returns:
        Description of the return value and its type/structure

    Raises:
        ValueError: Description of when this error is raised
        TypeError: Description of when this error is raised

    Examples:
        >>> function_name("test", 42)
        {"result": "success"}

        >>> function_name("test", -1)
        Traceback (most recent call last):
        ValueError: param2 must be positive

    Note:
        Any important notes, warnings, or additional context
    """
    pass


class ClassName:
    """Brief description of the class.

    Detailed explanation of the class purpose, behavior, and usage.

    Attributes:
        attribute1: Description of first attribute
        attribute2: Description of second attribute

    Examples:
        >>> obj = ClassName(value=10)
        >>> obj.method()
        20
    """

    def __init__(self, param: int):
        """Initialize ClassName with given parameters.

        Args:
            param: Description of initialization parameter
        """
        pass
```

## README Format

```markdown
# Project Name

Brief description of what this project does and its purpose.

## Features

- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## Installation

```bash
pip install package-name
# or
npm install package-name
```

## Usage

```python
from package import ClassName

# Basic example
obj = ClassName(param=value)
result = obj.method()
```

## API Reference

### ClassName

Brief description of the class.

**Parameters:**
- `param1` (str): Description
- `param2` (int): Description

**Methods:**
- `method_name(arg)`: Description of what it does

**Example:**
```python
example code here
```

## Configuration

Description of configuration options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| option1 | str | "default" | What it does |
| option2 | int | 10 | What it does |

## Testing

```bash
pytest tests/
```

## Contributing

[Guidelines for contributing to the project]

## License

[License information]
```

## JavaScript/TypeScript JSDoc Format

```javascript
/**
 * Brief description of the function.
 *
 * More detailed explanation of what the function does and why.
 *
 * @param {string} param1 - Description of first parameter
 * @param {number} param2 - Description of second parameter
 * @param {Object} options - Optional configuration object
 * @param {boolean} options.flag - Description of flag option
 * @returns {Promise<Object>} Description of return value
 * @throws {Error} When invalid parameters are provided
 *
 * @example
 * const result = await functionName("test", 42);
 * console.log(result); // { status: "success" }
 */
async function functionName(param1, param2, options = {}) {
  // Implementation
}

/**
 * Class representing a component.
 *
 * @class
 * @param {Object} config - Configuration object
 */
class ClassName {
  /**
   * Create a ClassName instance.
   * @param {Object} config - Configuration options
   */
  constructor(config) {
    // Implementation
  }
}
```

## Inline Comments

```python
# Use inline comments for complex logic
def complex_algorithm(data):
    # Step 1: Preprocess data to handle edge cases
    # We need to remove None values as they break downstream processing
    cleaned_data = [x for x in data if x is not None]

    # Step 2: Apply transformation using dynamic programming
    # This approach has O(n) time complexity vs O(n²) for naive solution
    memo = {}
    for item in cleaned_data:
        # Cache results to avoid redundant calculations
        if item not in memo:
            memo[item] = expensive_operation(item)

    return memo
```

## Output Format

After generating documentation, provide:

```
## Documentation Summary

**Files Modified/Created**:
- [file path]: [type of documentation added]

**Documentation Added**:
- Docstrings: [count] functions/classes documented
- README: [Created/Updated]
- Inline comments: [count] sections clarified

**Coverage**:
- Public functions documented: [count]/[total]
- Classes documented: [count]/[total]
- Complex sections explained: [count]

**Style Used**: [Google/NumPy/JSDoc/etc.]
```

## Guidelines

- **Be clear and concise**: Avoid unnecessary verbosity
- **Document the why**: Explain purpose and rationale, not just what
- **Include examples**: Show typical usage
- **Document parameters thoroughly**: Types, constraints, defaults
- **Describe return values**: Type, structure, possible values
- **List exceptions**: What errors can be raised and why
- **Maintain consistency**: Follow existing documentation style
- **Update existing docs**: Keep documentation synchronized with code
- **Avoid obvious comments**: Don't document what's already clear from code
- **Focus on public APIs**: Prioritize user-facing functions and classes
- **Include edge cases**: Document special behavior or limitations
