---
name: fix
description: >
  Find and fix bugs in code automatically. Analyzes the issue, identifies root cause, implements the fix, and outputs corrected code in ready-to-apply code blocks. Handles logical errors, edge cases, type issues, and runtime errors.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: development
  auto_apply: true
---

# Bug Fix

Automatically identify and fix bugs in the specified code. The fix will be applied directly to the files.

## Instructions

1. **Understand the Bug**:
   - If the user describes the bug, understand the expected vs actual behavior
   - If given error messages or stack traces, analyze them thoroughly
   - If no bug is specified, scan the code for common issues

2. **Locate the Issue**:
   - Read the relevant files completely
   - Trace the execution path to identify where the bug occurs
   - Check for related code that might be affected

3. **Analyze Root Cause**:
   - Determine why the bug exists (logical error, typo, wrong assumption, etc.)
   - Consider edge cases that might not be handled
   - Check for off-by-one errors, null/undefined issues, type mismatches

4. **Implement the Fix**:
   - Make the minimal necessary changes to fix the bug
   - Ensure the fix doesn't introduce new bugs
   - Handle edge cases properly
   - Add defensive checks if needed

5. **Apply Changes**:
   - Use the Edit tool to apply fixes directly to files
   - Make precise, targeted edits
   - Preserve existing code style and formatting

## Common Bug Types to Check

- **Logical Errors**: Wrong conditions, incorrect operators, flawed algorithm
- **Type Errors**: Mismatched types, incorrect type conversions
- **Null/Undefined**: Missing null checks, accessing properties on null/undefined
- **Off-by-One**: Array index errors, loop boundary issues
- **Async Issues**: Missing await, unhandled promises, race conditions
- **Edge Cases**: Empty arrays, zero values, negative numbers, boundary conditions
- **Resource Leaks**: Unclosed files, database connections, event listeners

## Output Format

After applying fixes, provide:

```
## Bug Fix Summary

**Issue**: [Brief description of the bug]

**Root Cause**: [Explanation of why the bug occurred]

**Fix Applied**: [Description of the changes made]

**Files Modified**:
- [file path]: [summary of changes]

**Testing Recommendations**:
- [Specific test cases to verify the fix]
```

## Guidelines

- Read files completely before making changes
- Make surgical, precise edits
- Don't refactor unnecessarily - focus on fixing the bug
- Preserve code style and existing patterns
- If the fix is complex, break it into logical steps
- Add comments if the fix requires explanation
- Consider backward compatibility
