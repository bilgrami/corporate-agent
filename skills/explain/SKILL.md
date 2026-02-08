---
name: explain
description: >
  Provide clear, comprehensive explanations of code logic, architecture, and behavior. Walks through execution flow, explains complex algorithms, clarifies design decisions, and makes code understandable for developers at any level.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: development
---

# Code Explanation

Provide a clear, comprehensive explanation of the specified code, its logic, and how it works.

## Instructions

1. **Read and Understand**:
   - Read all relevant files completely
   - Trace execution flow
   - Understand the purpose and context
   - Identify key components and their relationships

2. **Structure Your Explanation**:
   - Start with a high-level overview
   - Explain the main components
   - Walk through the execution flow
   - Detail complex or non-obvious parts
   - Explain design decisions and trade-offs

3. **Address Different Levels**:
   - **Beginner**: Explain basic concepts and terminology
   - **Intermediate**: Focus on architecture and patterns
   - **Advanced**: Discuss trade-offs, edge cases, and optimizations

4. **Use Multiple Approaches**:
   - **Narrative**: Tell the story of what the code does
   - **Structural**: Describe components and their relationships
   - **Sequential**: Walk through execution step-by-step
   - **Visual**: Use diagrams or ASCII art when helpful

## Output Format

```
## Code Explanation

### Overview
[High-level description of what this code does and why it exists]

### Architecture
[Description of main components and how they fit together]

### Key Components

#### [Component Name]
- **Purpose**: [What it does]
- **Location**: [File and line references]
- **Key Methods/Functions**: [Brief description of each]

### Execution Flow

1. **[Entry Point]**: [What happens first]
2. **[Next Step]**: [What happens next]
3. **[Continue...]**: [Step-by-step walkthrough]

### Detailed Walkthrough

[Line-by-line or section-by-section explanation of complex parts]

```python
# Code snippet
[relevant code]
```

[Explanation of what this code does and why]

### Important Concepts

**[Concept Name]**: [Explanation]

### Edge Cases and Error Handling
[How the code handles unusual situations]

### Design Decisions
[Why the code is structured this way, trade-offs made]

### Related Code
[References to other files or components that interact with this code]
```

## Example Explanation Style

```
This function implements a binary search algorithm to find a target value in a sorted array.

**How it works**:
1. Start with two pointers: `left` at index 0 and `right` at the last index
2. While `left <= right`:
   - Calculate the middle index: `mid = (left + right) // 2`
   - If the middle element equals the target, return its index
   - If the target is smaller, search the left half by setting `right = mid - 1`
   - If the target is larger, search the right half by setting `left = mid + 1`
3. If not found, return -1

**Why this approach**:
- Time complexity: O(log n) - much faster than linear search for large arrays
- Space complexity: O(1) - uses only a few variables
- Requires sorted input - this is a trade-off for the speed gain
```

## Guidelines

- **Be clear and concise**: Avoid jargon unless necessary
- **Use examples**: Show concrete examples when helpful
- **Reference code**: Always cite specific files and line numbers
- **Explain the why**: Don't just describe what the code does, explain why
- **Highlight complexity**: Spend more time on complex parts
- **Address common questions**: Anticipate what readers might wonder
- **Use analogies**: Compare to real-world concepts when appropriate
- **Show data flow**: Explain how data transforms through the code
- **Mention alternatives**: Discuss other approaches that could work
