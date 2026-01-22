# Tutorial 2: Testing Your Skills

Learn how to write tests for your skills to catch issues before deployment.

## Why Test Skills?

- Catch regressions when updating skills
- Verify skills respond appropriately
- Document expected behavior
- Enable CI/CD pipelines

## Creating Tests

Create a `tests.yml` file in your skill directory:

```
my-skill/
├── SKILL.md
└── tests.yml    # Add this file
```

## Basic Test Structure

```yaml
version: "1.0"

defaults:
  timeout: 30

tests:
  - name: "basic_request"
    description: "Should handle a simple request"
    input: "Help me with X"
    assertions:
      - type: contains
        value: "expected text"
    mock:
      response: "Mocked response with expected text"
```

## Running Tests

```bash
# Run in mock mode (fast, free)
skillforge test ./my-skill

# Run with real API calls
skillforge test ./my-skill --mode live

# Verbose output
skillforge test ./my-skill -v
```

## Assertion Types

### Text Assertions

```yaml
assertions:
  # Text contains
  - type: contains
    value: "error"
    case_sensitive: false  # Optional

  # Text doesn't contain
  - type: not_contains
    value: "exception"

  # Starts/ends with
  - type: starts_with
    value: "Here's"
  - type: ends_with
    value: "."

  # Exact match
  - type: equals
    value: "exact response"
```

### Pattern Assertions

```yaml
assertions:
  # Regular expression
  - type: regex
    pattern: "(feat|fix|docs):"

  # Length constraints
  - type: length
    min: 10
    max: 500
```

### JSON Assertions

```yaml
assertions:
  # Valid JSON
  - type: json_valid

  # JSON path value
  - type: json_path
    path: "$.status"
    value: "success"
```

## Complete Example

```yaml
version: "1.0"

defaults:
  timeout: 30

tests:
  - name: "handles_python_code"
    description: "Should review Python code correctly"
    input: |
      Review this code:
      ```python
      def add(a, b):
          return a + b
      ```
    assertions:
      - type: contains
        value: "type hint"
        case_sensitive: false
      - type: not_contains
        value: "error"
      - type: length
        min: 50
    mock:
      response: |
        The code looks good! Consider adding type hints:
        ```python
        def add(a: int, b: int) -> int:
            return a + b
        ```
    tags: ["python", "basic"]

  - name: "detects_security_issue"
    description: "Should catch SQL injection"
    input: |
      Review: query = f"SELECT * FROM users WHERE id = {user_id}"
    assertions:
      - type: contains
        value: "SQL injection"
        case_sensitive: false
      - type: regex
        pattern: "(critical|security|vulnerability)"
    mock:
      response: |
        Critical security issue: SQL injection vulnerability.
        Use parameterized queries instead.
    tags: ["security", "critical"]
```

## Filtering Tests

```bash
# Run only tests with specific tags
skillforge test ./my-skill --tags security,critical

# Run tests matching a name pattern
skillforge test ./my-skill --name "handles_*"

# Stop at first failure
skillforge test ./my-skill --stop
```

## CI/CD Integration

### JUnit Output

```bash
skillforge test ./my-skill --format junit -o results.xml
```

### GitHub Actions

```yaml
- name: Test skills
  run: skillforge test ./skills/my-skill --format junit -o results.xml

- name: Upload results
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: results.xml
```

## Regression Testing

Record baselines and compare future responses:

```bash
# Record baseline responses
skillforge test ./my-skill --record-baselines

# Run regression tests
skillforge test ./my-skill --regression

# Adjust similarity threshold
skillforge test ./my-skill --regression --threshold 0.9
```

## Live Mode

Test with real API calls:

```bash
# Estimate cost first
skillforge test ./my-skill --mode live --estimate-cost

# Run live tests
skillforge test ./my-skill --mode live --provider anthropic
```

## Next Steps

- [Tutorial 3: Security & Governance](./03-security-governance.md)
- [Tutorial 4: Multi-Platform Publishing](./04-multi-platform.md)
