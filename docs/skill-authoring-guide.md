# Skill Authoring Guide

This guide covers best practices for writing effective Claude skills that produce consistent, high-quality results.

## Skill Structure

Every skill consists of a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: my-skill-name
description: Use when the user asks for help with X. Provides Y.
---

# Skill Title

Instructions for Claude...
```

### Required Fields

| Field | Requirements | Example |
|-------|-------------|---------|
| `name` | Lowercase, hyphens, max 64 chars | `code-reviewer` |
| `description` | Explains **when** to use, max 1024 chars | `Use when asked to review code...` |

### Optional Fields

```yaml
---
name: my-skill
description: Use when...
version: 1.2.0
author: your-name
tags:
  - code-quality
  - python
---
```

## Writing Effective Descriptions

The description tells Claude **when** to activate the skill. Write it like a trigger condition.

### Good Descriptions

```yaml
# Clear trigger conditions
description: Use when asked to review code for bugs, security issues, or style improvements. Provides structured feedback with severity levels.

description: Use when the user needs help writing git commit messages. Follows conventional commit format.

description: Use when asked to explain code, algorithms, or technical concepts. Provides clear explanations with examples.
```

### Bad Descriptions

```yaml
# Too vague - when should Claude use this?
description: Helps with code stuff.

# Too narrow - misses valid use cases
description: Use only when user says "review my Python code".

# Describes what, not when
description: A code review tool that finds bugs.
```

## Structuring Instructions

Follow this proven structure for reliable results:

### 1. Role Statement

Start by establishing Claude's role:

```markdown
You are an expert code reviewer specializing in security and best practices.
```

### 2. Step-by-Step Instructions

Break down the task into clear steps:

```markdown
## Instructions

When reviewing code:

1. **Read the code** carefully and understand its purpose
2. **Identify issues** by category:
   - Critical: Security vulnerabilities, data loss risks
   - High: Bugs that will cause failures
   - Medium: Performance issues, code smells
   - Low: Style issues, minor improvements
3. **Provide fixes** with corrected code snippets
4. **Suggest improvements** for maintainability
```

### 3. Response Format

Specify the exact output format:

```markdown
## Response Format

Structure your review as:

\`\`\`
## Summary
One-line overview of code quality.

## Issues Found

### [Severity] Issue Title
- **Location**: file:line or function name
- **Problem**: What's wrong
- **Fix**: Code example showing the fix

## Recommendations
Prioritized list of improvements.
\`\`\`
```

### 4. Examples

Include realistic input/output examples:

```markdown
## Examples

### Example 1: SQL Injection

**User request**: "Review this database function"

\`\`\`python
def get_user(id):
    query = f"SELECT * FROM users WHERE id = {id}"
    return db.execute(query)
\`\`\`

**Response**:

## Summary
Critical SQL injection vulnerability found.

## Issues Found

### [Critical] SQL Injection
- **Location**: `get_user` function, line 2
- **Problem**: User input directly interpolated into SQL query
- **Fix**:
\`\`\`python
def get_user(id: int):
    query = "SELECT * FROM users WHERE id = %s"
    return db.execute(query, (id,))
\`\`\`

## Recommendations
1. Use parameterized queries for all database operations
2. Add input validation for the `id` parameter
```

## Best Practices

### Do

- **Be specific** about when the skill applies
- **Include 2-3 realistic examples** with actual input/output
- **Cover edge cases** (empty input, errors, ambiguous requests)
- **Use consistent formatting** throughout
- **Provide actionable guidance** Claude can follow
- **Test your skill** before deploying

### Don't

- Write vague or generic instructions
- Skip examples (they're essential for consistency)
- Assume context Claude won't have
- Include sensitive data (passwords, API keys, internal URLs)
- Make instructions overly complex
- Use ambiguous language

## Common Patterns

### Pattern 1: Analysis Skill

For skills that analyze input and provide feedback:

```markdown
---
name: code-analyzer
description: Use when asked to analyze code quality, complexity, or structure.
---

# Code Analyzer

You analyze code and provide metrics and insights.

## Instructions

1. Parse the provided code
2. Calculate metrics (lines, complexity, dependencies)
3. Identify patterns and anti-patterns
4. Provide actionable recommendations

## Response Format

| Metric | Value | Assessment |
|--------|-------|------------|
| Lines of Code | X | ... |
| Cyclomatic Complexity | X | ... |
| ...

## Findings
...

## Recommendations
...
```

### Pattern 2: Generator Skill

For skills that create content:

```markdown
---
name: test-generator
description: Use when asked to write unit tests for code.
---

# Test Generator

You write comprehensive unit tests.

## Instructions

1. Analyze the code to understand its behavior
2. Identify test cases:
   - Happy path (normal operation)
   - Edge cases (boundaries, empty inputs)
   - Error cases (invalid inputs, exceptions)
3. Generate tests with clear names and assertions
4. Include setup/teardown if needed

## Output Format

Generate tests in the appropriate framework for the language:
- Python: pytest
- JavaScript: Jest
- Go: testing package

## Example

**Input**: [function code]
**Output**: [complete test file]
```

### Pattern 3: Converter/Transformer Skill

For skills that transform input to output:

```markdown
---
name: json-to-yaml
description: Use when asked to convert JSON to YAML or vice versa.
---

# JSON/YAML Converter

You convert between JSON and YAML formats.

## Instructions

1. Detect the input format (JSON or YAML)
2. Parse and validate the input
3. Convert to the requested output format
4. Preserve comments where possible (YAML to YAML)

## Output

Return only the converted content, properly formatted.
No explanations unless there are errors.
```

## Handling Edge Cases

Always consider and document edge case behavior:

```markdown
## Edge Cases

- **Empty input**: Ask for clarification
- **Invalid syntax**: Point out the error with line number
- **Ambiguous request**: Ask which interpretation the user prefers
- **Multiple files**: Process each file separately, clearly labeled
```

## Adding Tests

Create a `tests.yml` file alongside your `SKILL.md`:

```yaml
version: "1.0"

tests:
  - name: "basic_review"
    description: "Should identify obvious issues"
    input: |
      Review this code:
      \`\`\`python
      def add(a, b):
          return a + b
      \`\`\`
    assertions:
      - type: contains
        value: "Summary"
      - type: regex
        pattern: "(clean|simple|good)"
        case_sensitive: false
    mock:
      response: |
        ## Summary
        Clean, simple function.

        ## Issues Found
        None.

        ## Recommendations
        - Add type hints
        - Add docstring

  - name: "detects_security_issue"
    input: |
      Review: `query = f"SELECT * FROM users WHERE id = {id}"`
    assertions:
      - type: contains
        value: "SQL injection"
        case_sensitive: false
      - type: contains
        value: "Critical"
    tags: ["security"]
```

## Validation Checklist

Before deploying, verify:

- [ ] `skillforge validate ./my-skill` passes
- [ ] `skillforge test ./my-skill` passes
- [ ] Description clearly states when to use the skill
- [ ] At least 2 realistic examples included
- [ ] Response format is clearly specified
- [ ] Edge cases are documented
- [ ] No sensitive data in skill content

## Next Steps

- [Testing Guide](testing-guide.md) - Write comprehensive tests
- [CLI Cheat Sheet](cli-cheatsheet.md) - Quick command reference
- [Hub Guide](hub-guide.md) - Share your skills with the community
