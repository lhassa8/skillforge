# Skill Testing Guide

Test your skills before deployment to catch issues early and ensure consistent behavior.

## Why Test Skills?

- **Catch bugs** before users encounter them
- **Verify behavior** matches expectations
- **Document** expected input/output
- **Enable CI/CD** integration
- **Track regressions** when updating skills

## Quick Start

### 1. Create Test File

Create `tests.yml` in your skill directory:

```yaml
version: "1.0"

tests:
  - name: "basic_usage"
    description: "Test basic functionality"
    input: "Help me write a commit message for adding login"
    assertions:
      - type: contains
        value: "feat"
    mock:
      response: |
        feat: add user login functionality
```

### 2. Run Tests

```bash
# Mock mode (fast, free)
skillforge test ./skills/my-skill

# Live mode (real API calls)
skillforge test ./skills/my-skill --mode live
```

## Test File Structure

```
my-skill/
├── SKILL.md
├── tests.yml              # Single test file
└── tests/                 # OR multiple test files
    ├── smoke.test.yml
    └── full.test.yml
```

## Test Definition Format

```yaml
version: "1.0"

defaults:
  timeout: 30

tests:
  - name: "test_name"
    description: "What this test verifies"
    input: "User input to test"
    assertions:
      - type: contains
        value: "expected text"
    trigger:
      should_trigger: true
    mock:
      response: "Mock response for fast testing"
    tags: ["smoke", "basic"]
    timeout: 60
```

### Test Case Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique test identifier |
| `input` | Yes | User input to send |
| `description` | No | What this test verifies |
| `assertions` | No | Validation rules |
| `trigger` | No | Should skill activate? |
| `mock` | No | Mock response for mock mode |
| `tags` | No | Categories for filtering |
| `timeout` | No | Seconds before timeout |
| `context` | No | Previous conversation |

## Assertions

### contains

Check if text is present:

```yaml
assertions:
  - type: contains
    value: "SQL injection"
    case_sensitive: false  # Optional, default: true
```

### not_contains

Check if text is absent:

```yaml
assertions:
  - type: not_contains
    value: "error"
```

### regex

Match a pattern:

```yaml
assertions:
  - type: regex
    pattern: "(feat|fix|docs):"
    case_sensitive: false
```

### starts_with / ends_with

Check beginning or end:

```yaml
assertions:
  - type: starts_with
    value: "## Summary"
  - type: ends_with
    value: "---"
```

### length

Check response length:

```yaml
assertions:
  - type: length
    min: 50
    max: 500
```

### json_valid

Verify valid JSON:

```yaml
assertions:
  - type: json_valid
```

### json_path

Check JSON value:

```yaml
assertions:
  - type: json_path
    path: "$.status"
    value: "success"
```

### equals

Exact match:

```yaml
assertions:
  - type: equals
    value: "Expected exact output"
```

### similar_to

Fuzzy match for regression testing:

```yaml
assertions:
  - type: similar_to
    baseline: "Expected similar output"
    threshold: 0.8  # 80% similarity required
```

## Mock vs Live Mode

### Mock Mode (Default)

- **Fast**: No API calls
- **Free**: No token costs
- **Deterministic**: Same results every time
- **Best for**: Development, CI/CD

```bash
skillforge test ./skills/my-skill
```

Mock mode uses the `mock.response` from your test definition:

```yaml
tests:
  - name: "test_commit"
    input: "Write a commit message for adding auth"
    mock:
      response: |
        feat: add user authentication

        - Implement login/logout
        - Add session management
    assertions:
      - type: contains
        value: "feat"
```

### Live Mode

- **Real**: Actual API calls
- **Variable**: Responses may differ
- **Costly**: Uses tokens
- **Best for**: Final validation

```bash
# Check cost first
skillforge test ./skills/my-skill --mode live --estimate-cost

# Run live tests
skillforge test ./skills/my-skill --mode live
skillforge test ./skills/my-skill --mode live --provider anthropic
```

## Trigger Testing

Test whether your skill should activate for given input:

```yaml
tests:
  # Should trigger
  - name: "triggers_on_review_request"
    input: "Review this code for bugs"
    trigger:
      should_trigger: true

  # Should NOT trigger
  - name: "ignores_unrelated_request"
    input: "What's the weather today?"
    trigger:
      should_trigger: false
```

## Conversation Context

Test multi-turn conversations:

```yaml
tests:
  - name: "follows_up_correctly"
    context:
      - role: user
        content: "Review this function"
      - role: assistant
        content: "I found a potential issue..."
    input: "Can you show me how to fix it?"
    assertions:
      - type: contains
        value: "```"  # Should include code
```

## Filtering Tests

### By Tags

```yaml
tests:
  - name: "smoke_test"
    tags: ["smoke", "fast"]
    # ...

  - name: "comprehensive_test"
    tags: ["full", "slow"]
    # ...
```

```bash
# Run only smoke tests
skillforge test ./skills/my-skill --tags smoke

# Run multiple tag groups
skillforge test ./skills/my-skill --tags smoke,critical
```

### By Name

```bash
# Run specific test
skillforge test ./skills/my-skill --name basic_commit

# Pattern matching
skillforge test ./skills/my-skill --name "security_*"
```

## Output Formats

### Human (Default)

```bash
skillforge test ./skills/my-skill
```

```
Testing skill: my-skill
Mode: mock | Tests found: 1 file(s)

┏━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Test            ┃ Status ┃ Duration ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ basic_commit    │ PASS   │    0.1ms │
│ handles_empty   │ PASS   │    0.1ms │
└─────────────────┴────────┴──────────┘

Summary: 2 passed
```

### JSON

```bash
skillforge test ./skills/my-skill --format json -o results.json
```

### JUnit XML (for CI)

```bash
skillforge test ./skills/my-skill --format junit -o results.xml
```

## Regression Testing

Compare responses against recorded baselines:

### Record Baselines

```bash
skillforge test ./skills/my-skill --record-baselines
```

This creates `baselines.yml` with responses.

### Run Regression Tests

```bash
# Compare against baselines
skillforge test ./skills/my-skill --regression

# Adjust similarity threshold
skillforge test ./skills/my-skill --regression --threshold 0.9
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Test Skills

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install SkillForge
        run: pip install ai-skillforge

      - name: Test Skills
        run: |
          skillforge test ./skills/my-skill --format junit -o results.xml

      - name: Upload Results
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: results.xml
```

### Fail on Issues

```bash
# Exit with error code if tests fail
skillforge test ./skills/my-skill || exit 1
```

## Best Practices

### Write Meaningful Tests

```yaml
# Good: Tests specific behavior
tests:
  - name: "detects_sql_injection"
    description: "Should identify SQL injection in string interpolation"
    input: 'Review: query = f"SELECT * FROM users WHERE id = {id}"'
    assertions:
      - type: contains
        value: "SQL injection"
        case_sensitive: false
      - type: contains
        value: "parameterized"

# Bad: Vague test
tests:
  - name: "test1"
    input: "review code"
    assertions:
      - type: length
        min: 1
```

### Cover Edge Cases

```yaml
tests:
  # Happy path
  - name: "reviews_python_code"
    input: "Review this Python function..."

  # Edge cases
  - name: "handles_empty_input"
    input: "Review this code:"
    assertions:
      - type: contains
        value: "provide"  # Should ask for code

  - name: "handles_multiple_files"
    input: "Review these files: file1.py, file2.py"

  - name: "handles_unknown_language"
    input: "Review this Brainfuck code: ++++++++"
```

### Use Tags Strategically

```yaml
tests:
  - name: "smoke_test"
    tags: ["smoke", "fast"]  # Run in CI on every commit

  - name: "full_validation"
    tags: ["full", "slow"]   # Run before release

  - name: "security_check"
    tags: ["security", "critical"]  # Run on security-related PRs
```

## Troubleshooting

### "Expected trigger=True, got False"

The skill didn't activate for the input. Check:
- Does the input contain keywords from your skill name/description?
- Is the description clear about when to trigger?

### Tests Pass in Mock, Fail in Live

Mock responses are deterministic; live responses vary. Use:
- Flexible assertions (regex, contains vs equals)
- Lower similarity thresholds for similar_to
- Multiple valid patterns

### Slow Tests

- Use mock mode for development
- Tag slow tests and run separately
- Reduce live mode test count

## Programmatic Testing

```python
from pathlib import Path
from skillforge import load_test_suite, run_test_suite

# Load skill and tests
skill, suite = load_test_suite(Path("./skills/my-skill"))

# Run tests
result = run_test_suite(skill, suite, mode="mock")

# Check results
print(f"Passed: {result.passed_tests}/{result.total_tests}")

for test_result in result.test_results:
    if not test_result.passed:
        print(f"FAILED: {test_result.test_case.name}")
        for assertion in test_result.failed_assertions:
            print(f"  - {assertion.message}")
```
