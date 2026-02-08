---
name: test-gen
description: >
  Generate comprehensive test suites with pytest framework. Creates unit tests, integration tests, edge case coverage, mocks, fixtures, and parametrized tests. Automatically writes test files following best practices.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: testing
  auto_apply: true
---

# Test Generation

Generate comprehensive test suites for the specified code using pytest framework and best practices.

## Instructions

1. **Analyze the Code**:
   - Read the source code completely
   - Identify all functions, methods, and classes to test
   - Understand the expected behavior and edge cases
   - Note dependencies and external interactions

2. **Plan Test Coverage**:
   - **Happy Path**: Normal, expected usage
   - **Edge Cases**: Boundary conditions, empty inputs, maximum values
   - **Error Cases**: Invalid inputs, exceptions, error conditions
   - **Integration**: Interactions between components
   - **Mocking**: External dependencies (APIs, databases, file systems)

3. **Generate Tests**:
   - Create test files following naming convention: `test_[module_name].py`
   - Write clear, focused test functions
   - Use descriptive test names: `test_[function]_[scenario]_[expected_result]`
   - Include docstrings explaining what each test verifies
   - Use pytest fixtures for setup and teardown
   - Use parametrize for testing multiple inputs

4. **Write Test Files**:
   - Place tests in appropriate test directory
   - Use Write or Edit tool to create test files
   - Follow the project's existing test structure

## Test Structure

```python
import pytest
from module_name import function_to_test

class TestClassName:
    """Test suite for ClassName"""

    @pytest.fixture
    def setup_data(self):
        """Fixture providing test data"""
        return {"key": "value"}

    def test_function_happy_path(self, setup_data):
        """Test normal operation with valid inputs"""
        result = function_to_test(setup_data)
        assert result == expected_value

    def test_function_edge_case_empty_input(self):
        """Test handling of empty input"""
        result = function_to_test([])
        assert result == []

    def test_function_raises_error_on_invalid_input(self):
        """Test that appropriate error is raised for invalid input"""
        with pytest.raises(ValueError, match="Invalid input"):
            function_to_test(None)

    @pytest.mark.parametrize("input_val,expected", [
        (0, 0),
        (1, 1),
        (5, 25),
        (-3, 9),
    ])
    def test_function_multiple_inputs(self, input_val, expected):
        """Test function with various input values"""
        assert function_to_test(input_val) == expected

    @pytest.fixture
    def mock_external_service(self, mocker):
        """Mock external API calls"""
        mock = mocker.patch('module_name.external_service')
        mock.return_value = {"status": "success"}
        return mock

    def test_function_with_external_dependency(self, mock_external_service):
        """Test function that calls external service"""
        result = function_to_test()
        assert mock_external_service.called
        assert result["status"] == "success"
```

## Coverage Areas

### 1. Happy Path Tests
- Test normal, expected usage
- Verify correct outputs for valid inputs

### 2. Edge Cases
- Empty collections ([], {}, "")
- Boundary values (0, -1, MAX_INT)
- None/null values
- Single element collections
- Very large inputs

### 3. Error Handling
- Invalid input types
- Out-of-range values
- Missing required parameters
- Malformed data

### 4. State and Side Effects
- Database operations
- File I/O
- API calls
- State changes

### 5. Integration Tests
- Component interactions
- End-to-end workflows
- Data flow between modules

## Fixtures and Mocking

```python
@pytest.fixture
def sample_user():
    """Provide a sample user for testing"""
    return User(id=1, name="Test User", email="test@example.com")

@pytest.fixture
def mock_database(mocker):
    """Mock database connection"""
    mock_db = mocker.patch('app.database.connect')
    mock_db.return_value.query.return_value = [{"id": 1}]
    return mock_db

@pytest.fixture(scope="session")
def test_config():
    """Configuration used across all tests"""
    return {"api_url": "http://test.example.com"}
```

## Output Format

After generating tests, provide:

```
## Test Generation Summary

**Module Tested**: [module name]

**Test File Created**: [path to test file]

**Coverage**:
- Functions tested: [count]
- Test cases created: [count]
- Edge cases covered: [list]
- Mocked dependencies: [list]

**Test Categories**:
- Happy path: [count] tests
- Edge cases: [count] tests
- Error handling: [count] tests
- Integration: [count] tests

**Running the Tests**:
```bash
pytest [test_file_path] -v
pytest [test_file_path] --cov=[module_name]
```

**Additional Test Recommendations**:
- [Scenarios that might need manual testing]
- [Performance or load tests to consider]
```

## Guidelines

- **One assertion per test**: Keep tests focused
- **Clear test names**: Should describe what is being tested and expected outcome
- **Independent tests**: Tests should not depend on each other
- **Use fixtures**: For common setup and teardown
- **Mock external dependencies**: Don't call real APIs, databases in unit tests
- **Parametrize similar tests**: Reduce duplication
- **Test behavior, not implementation**: Focus on what the code does, not how
- **Include docstrings**: Explain what each test verifies
- **Arrange-Act-Assert**: Structure tests clearly (setup, execute, verify)
