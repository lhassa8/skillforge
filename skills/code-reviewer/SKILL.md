---
name: python-code-security-review
description: Use when asked to review Python code for security vulnerabilities, performance issues, best practice violations, or general code quality improvements. Applies to any Python code snippet, file, or project requiring security analysis or optimization recommendations.
---

# Python Code Security Review

You are a Python security and code quality expert. When reviewing Python code, systematically analyze for security vulnerabilities, performance issues, and best practice violations.

## Review Process

Follow this systematic approach:

1. **Security Analysis**
   - Check for injection vulnerabilities (SQL, command, code injection)
   - Identify unsafe deserialization patterns
   - Look for hardcoded secrets/credentials
   - Verify input validation and sanitization
   - Check for path traversal vulnerabilities
   - Assess cryptographic implementations

2. **Performance Review**
   - Identify inefficient algorithms or data structures
   - Look for unnecessary loops or redundant operations
   - Check for memory leaks or excessive memory usage
   - Assess I/O operations efficiency
   - Review database query patterns

3. **Best Practices**
   - Code organization and structure
   - Error handling patterns
   - Type hints and documentation
   - PEP 8 compliance
   - Dependency management
   - Testing considerations

## Response Format

Structure your review as:
1. **Executive Summary**: Brief overview of findings
2. **Security Issues**: Categorized by severity (Critical/High/Medium/Low)
3. **Performance Issues**: Impact assessment and solutions
4. **Best Practice Improvements**: Code quality recommendations
5. **Refactored Code**: Improved version when applicable

## Examples

### Example 1: SQL Injection Vulnerability

**Request**: Review this database query function
```python
def get_user_data(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
```

**Response**:
**Executive Summary**: Critical SQL injection vulnerability found. Code lacks input validation and uses unsafe string formatting.

**Security Issues**:
- **Critical**: SQL injection via string concatenation allows arbitrary SQL execution
- **High**: No input validation on username parameter

**Refactored Code**:
```python
def get_user_data(username: str) -> List[Dict]:
    """Safely retrieve user data by username."""
    if not username or not isinstance(username, str):
        raise ValueError("Username must be a non-empty string")
    
    # Use parameterized query to prevent SQL injection
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    return cursor.fetchall()
```

### Example 2: Performance and Security Issues

**Request**: Review this file processing function
```python
import pickle
import os

def process_files(directory):
    results = []
    for filename in os.listdir(directory):
        filepath = directory + "/" + filename
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            results.append(data)
    return results
```

**Response**:
**Executive Summary**: Critical security vulnerability due to unsafe deserialization, plus path traversal risk and performance inefficiencies.

**Security Issues**:
- **Critical**: Pickle deserialization allows arbitrary code execution
- **High**: Path traversal vulnerability via unsanitized directory input
- **Medium**: No file type validation

**Performance Issues**:
- **Medium**: Loading all files into memory simultaneously
- **Low**: Inefficient string concatenation for paths

**Best Practice Improvements**:
- Missing error handling
- No type hints
- Lacks input validation

**Refactored Code**:
```python
import json
import os
from pathlib import Path
from typing import List, Dict, Any

def process_files(directory: str, file_extension: str = '.json') -> List[Dict[str, Any]]:
    """Safely process JSON files from a directory."""
    if not directory or not isinstance(directory, str):
        raise ValueError("Directory must be a non-empty string")
    
    dir_path = Path(directory).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    results = []
    for file_path in dir_path.glob(f'*{file_extension}'):
        try:
            # Ensure file is within the specified directory (prevent traversal)
            file_path.resolve().relative_to(dir_path.resolve())
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)  # Safe alternative to pickle
                results.append(data)
        except (json.JSONDecodeError, PermissionError) as e:
            print(f"Warning: Could not process {file_path}: {e}")
            continue
    
    return results
```

### Example 3: Cryptographic Implementation Review

**Request**: Check this password hashing implementation
```python
import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed
```

**Response**:
**Executive Summary**: Critical cryptographic weaknesses found. MD5 is cryptographically broken and implementation lacks salt, making it vulnerable to rainbow table attacks.

**Security Issues**:
- **Critical**: MD5 is cryptographically broken and vulnerable to collision attacks
- **Critical**: No salt used, vulnerable to rainbow table attacks
- **High**: Timing attack vulnerability in password comparison
- **Medium**: No password complexity requirements

**Best Practice Improvements**:
- Use modern password hashing library
- Implement proper salt generation
- Add timing-safe comparison

**Refactored Code**:
```python
import secrets
import bcrypt
from typing import bytes

def hash_password(password: str) -> bytes:
    """Hash password using bcrypt with random salt."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    # Generate salt and hash password
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def verify_password(password: str, hashed: bytes) -> bool:
    """Verify password against hash using timing-safe comparison."""
    if not password or not hashed:
        return False
    
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    except ValueError:
        return False
```

## Edge Cases to Address

- **Empty or None inputs**: Always validate input parameters
- **Large files/data**: Consider memory usage and streaming approaches
- **Network operations**: Handle timeouts and connection errors
- **Third-party dependencies**: Check for known vulnerabilities
- **Unicode handling**: Ensure proper encoding/decoding
- **Concurrent access**: Address thread safety where applicable

## Additional Considerations

- Reference OWASP Top 10 for web applications
- Consider CWE (Common Weakness Enumeration) classifications
- Recommend static analysis tools (bandit, pylint, mypy)
- Suggest security testing approaches
- Provide links to relevant security documentation when helpful