---
name: security-audit
description: >
  Perform comprehensive security audit of code against OWASP Top 10 and common vulnerabilities. Identifies injection flaws, authentication issues, sensitive data exposure, XSS, insecure dependencies, and provides remediation guidance.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: security
---

# Security Audit

Perform a comprehensive security review of the codebase, focusing on OWASP Top 10 vulnerabilities and common security issues.

## Instructions

1. **Scope the Audit**:
   - Identify all files to review
   - Understand the application architecture
   - Note external dependencies and integrations
   - Identify security-critical components (auth, data handling, etc.)

2. **Systematic Review**:
   Analyze the code against each major security category:
   - Injection vulnerabilities
   - Authentication and authorization
   - Sensitive data exposure
   - Security misconfiguration
   - Cross-Site Scripting (XSS)
   - Insecure dependencies
   - Insufficient logging and monitoring
   - API security issues

3. **Document Findings**:
   - Categorize by OWASP classification
   - Assign severity levels
   - Provide specific file and line references
   - Include proof of concept if applicable
   - Recommend remediation steps

## OWASP Top 10 Checklist

### 1. Injection Flaws

**Check for:**
- SQL injection: Unsanitized user input in queries
- Command injection: User input passed to system commands
- LDAP injection: Unsafe LDAP queries
- NoSQL injection: Unsafe database queries
- XML injection: Unsafe XML processing

**Look for patterns:**
```python
# BAD: SQL Injection vulnerability
query = f"SELECT * FROM users WHERE username = '{username}'"

# BAD: Command injection
os.system(f"ping {user_input}")

# GOOD: Use parameterized queries
cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
```

### 2. Broken Authentication

**Check for:**
- Weak password requirements
- Missing rate limiting on login
- Predictable session tokens
- Session fixation vulnerabilities
- Plaintext password storage
- Missing account lockout
- Exposed credentials in code or config

**Look for patterns:**
```python
# BAD: Plaintext password storage
user.password = request.form['password']

# BAD: Weak session token
session_id = str(random.randint(1000, 9999))

# GOOD: Hash passwords
user.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

### 3. Sensitive Data Exposure

**Check for:**
- Unencrypted sensitive data transmission (no HTTPS)
- Sensitive data in logs
- Hardcoded secrets (API keys, passwords)
- Insufficient encryption
- Missing HSTS headers
- Sensitive data in URLs or GET parameters

**Look for patterns:**
```python
# BAD: Hardcoded credentials
API_KEY = "sk_live_abc123xyz"
DB_PASSWORD = "admin123"

# BAD: Sensitive data in logs
logger.info(f"User password: {password}")

# GOOD: Use environment variables
API_KEY = os.environ.get('API_KEY')
```

### 4. XML External Entities (XXE)

**Check for:**
- Unsafe XML parsing
- External entity processing enabled
- Unvalidated XML input

### 5. Broken Access Control

**Check for:**
- Missing authorization checks
- Insecure direct object references (IDOR)
- Path traversal vulnerabilities
- Missing function-level access control
- CORS misconfiguration

**Look for patterns:**
```python
# BAD: No authorization check
def delete_user(user_id):
    User.objects.filter(id=user_id).delete()

# BAD: IDOR vulnerability
file_path = f"/files/{request.GET['filename']}"

# GOOD: Check ownership/permissions
if current_user.id == user.id or current_user.is_admin:
    user.delete()
```

### 6. Security Misconfiguration

**Check for:**
- Debug mode enabled in production
- Default credentials
- Verbose error messages
- Unnecessary features enabled
- Missing security headers
- Outdated software versions

**Look for patterns:**
```python
# BAD: Debug mode in production
DEBUG = True

# BAD: Verbose error messages
except Exception as e:
    return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()})

# GOOD: Generic error messages
except Exception:
    logger.exception("Error processing request")
    return JsonResponse({'error': 'An error occurred'}, status=500)
```

### 7. Cross-Site Scripting (XSS)

**Check for:**
- Unescaped user input in HTML
- Unsafe use of innerHTML
- Missing Content-Security-Policy headers
- Improper output encoding

**Look for patterns:**
```javascript
// BAD: XSS vulnerability
element.innerHTML = userInput;

// BAD: Unescaped output
return f"<div>Hello {username}</div>"

// GOOD: Escape output
return f"<div>Hello {escape(username)}</div>"
```

### 8. Insecure Deserialization

**Check for:**
- Unsafe deserialization of user input
- Use of pickle with untrusted data
- Unsafe JSON parsing

### 9. Using Components with Known Vulnerabilities

**Check for:**
- Outdated dependencies
- Vulnerable library versions
- Missing security patches

**Actions:**
```bash
# Check for vulnerabilities
npm audit
pip-audit
snyk test
```

### 10. Insufficient Logging & Monitoring

**Check for:**
- Missing audit logs for security events
- No alerting for suspicious activity
- Insufficient log retention
- Logging sensitive data

## Output Format

```
# Security Audit Report

## Executive Summary
[Brief overview of findings and overall security posture]

**Findings Summary:**
- Critical: [count]
- High: [count]
- Medium: [count]
- Low: [count]

---

## Critical Severity Findings

### [Finding Title]
**Category**: [OWASP Category]
**Severity**: Critical
**File**: [path:line]

**Description**: [What the vulnerability is]

**Impact**: [What an attacker could do]

**Proof of Concept**:
```
[Example of how to exploit]
```

**Remediation**:
```
[Code showing the fix]
```

---

## High Severity Findings

[Same format as Critical]

---

## Medium Severity Findings

[Same format]

---

## Low Severity Findings

[Same format]

---

## Recommendations

### Immediate Actions (Critical/High)
1. [Action item]
2. [Action item]

### Short-term Improvements (Medium)
1. [Action item]
2. [Action item]

### Long-term Enhancements (Low)
1. [Action item]
2. [Action item]

### Security Best Practices
- [General security improvement]
- [General security improvement]

---

## Positive Security Practices Observed
- [Good security practice found in code]
- [Good security practice found in code]
```

## Severity Levels

- **Critical**: Directly exploitable, high impact (remote code execution, data breach)
- **High**: Exploitable with moderate effort, significant impact
- **Medium**: Requires specific conditions, moderate impact
- **Low**: Difficult to exploit or minimal impact

## Guidelines

- **Be thorough**: Check all input points and data flows
- **Be specific**: Always include file paths and line numbers
- **Be practical**: Focus on realistic threats and exploitable issues
- **Provide context**: Explain why something is a vulnerability
- **Suggest fixes**: Provide concrete remediation code
- **Consider defense in depth**: Look for multiple security layers
- **Check dependencies**: Review third-party libraries and frameworks
- **Validate everywhere**: All user input should be validated and sanitized
- **Principle of least privilege**: Check if components have minimal required permissions
