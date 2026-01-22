"""Built-in skill templates for SkillForge."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SkillTemplate:
    """A built-in skill template.

    Attributes:
        name: Template identifier (e.g., "code-review")
        title: Human-readable title (e.g., "Code Review")
        description: Brief description of what the skill does
        category: Category for grouping (e.g., "Code Quality", "Git")
        content: The skill instructions (body of SKILL.md, without frontmatter)
        tags: Tags for categorization and search
    """

    name: str
    title: str
    description: str
    category: str
    content: str
    tags: list[str] = field(default_factory=list)


# =============================================================================
# Built-in Templates
# =============================================================================

TEMPLATE_CODE_REVIEW = SkillTemplate(
    name="code-review",
    title="Code Review",
    description="Review code for best practices, bugs, and security issues",
    category="Code Quality",
    tags=["code", "review", "quality", "security"],
    content="""# Instructions

When asked to review code, follow this systematic approach to provide thorough, actionable feedback.

## Review Checklist

Work through each area systematically:

1. **Correctness** - Does the code do what it's supposed to do?
   - Logic errors, off-by-one bugs, edge cases
   - Proper error handling
   - Correct return values and types

2. **Security** - Are there any vulnerabilities?
   - Injection vulnerabilities (SQL, command, XSS)
   - Authentication/authorization issues
   - Sensitive data exposure
   - Input validation

3. **Performance** - Any obvious inefficiencies?
   - Unnecessary loops or computations
   - Memory leaks or excessive allocation
   - N+1 queries or missing indexes
   - Blocking operations that should be async

4. **Maintainability** - Is the code readable and well-structured?
   - Clear naming and organization
   - Appropriate abstractions
   - DRY principle adherence
   - Code complexity

5. **Best Practices** - Does it follow conventions?
   - Language/framework idioms
   - Project coding standards
   - Documentation requirements

## Response Format

Structure your review as follows:

### Summary
1-2 sentences with overall assessment and recommendation (approve, request changes, etc.)

### Issues Found
List problems discovered, ordered by severity:

**High Severity**
- Issue description with line reference
- Why it's a problem
- Suggested fix with code example

**Medium Severity**
- (same format)

**Low Severity**
- (same format)

### Suggestions
Optional improvements that aren't critical but would enhance the code.

### What's Done Well
Note positive aspects - this reinforces good practices.

## Guidelines

- Be specific: reference line numbers, variable names, functions
- Be constructive: explain WHY something is an issue
- Provide solutions: include code examples for fixes
- Prioritize: focus on significant issues, not style nitpicks
- Be kind: review the code, not the person
""",
)

TEMPLATE_GIT_COMMIT = SkillTemplate(
    name="git-commit",
    title="Git Commit Messages",
    description="Write clear, conventional commit messages",
    category="Git",
    tags=["git", "commit", "conventional-commits"],
    content="""# Instructions

Help users write clear, well-structured commit messages following the Conventional Commits specification.

## Commit Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type (required)
- `feat`: New feature for the user
- `fix`: Bug fix for the user
- `docs`: Documentation only changes
- `style`: Formatting, missing semicolons, etc. (no code change)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or correcting tests
- `build`: Changes to build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

### Scope (optional)
The part of the codebase affected (e.g., `api`, `ui`, `auth`, `parser`)

### Subject (required)
- Use imperative mood: "add" not "added" or "adds"
- Don't capitalize first letter
- No period at the end
- Max 50 characters

### Body (optional)
- Explain WHAT and WHY, not HOW
- Wrap at 72 characters
- Separate from subject with blank line

### Footer (optional)
- Reference issues: `Fixes #123`, `Closes #456`
- Breaking changes: `BREAKING CHANGE: description`

## Examples

**Simple feature:**
```
feat(auth): add password reset functionality
```

**Bug fix with body:**
```
fix(api): prevent race condition in user creation

Multiple concurrent requests could create duplicate users
due to missing database-level unique constraint.

Fixes #234
```

**Breaking change:**
```
feat(api)!: change authentication to use JWT tokens

BREAKING CHANGE: API now requires Bearer token authentication.
Session-based auth is no longer supported.

Migration guide: https://docs.example.com/jwt-migration
```

## Guidelines

When helping users:
1. Ask what changed if not clear from context
2. Determine the appropriate type
3. Suggest a clear, concise subject line
4. Add body only when the change needs explanation
5. Include issue references when mentioned
""",
)

TEMPLATE_GIT_PR = SkillTemplate(
    name="git-pr",
    title="Pull Request Descriptions",
    description="Create comprehensive pull request descriptions",
    category="Git",
    tags=["git", "pull-request", "pr", "code-review"],
    content="""# Instructions

Help users create clear, comprehensive pull request descriptions that make code review efficient.

## PR Description Template

```markdown
## Summary
Brief description of what this PR does (1-3 sentences).

## Changes
- Bullet point list of specific changes
- Be concrete and specific
- Group related changes together

## Why
Explain the motivation behind these changes. Link to relevant issues, discussions, or documentation.

## Testing
- How was this tested?
- What scenarios were covered?
- Any manual testing steps reviewers should follow?

## Screenshots (if applicable)
Before/after screenshots for UI changes.

## Checklist
- [ ] Tests pass locally
- [ ] Code follows project style guidelines
- [ ] Documentation updated (if applicable)
- [ ] No breaking changes (or documented in description)
```

## Guidelines

### Summary Section
- Lead with the user impact or business value
- Use imperative mood: "Add feature" not "Added feature"
- Keep it scannable - reviewers should understand the PR in 10 seconds

### Changes Section
- Be specific: "Add validation for email format" not "Fix bug"
- Reference relevant code: "Update `UserService.create()` to validate input"
- Separate functional changes from refactoring

### Why Section
- Link to issues: "Fixes #123" or "Part of #456"
- Explain context that isn't obvious from code
- Mention alternatives considered and why this approach was chosen

### Testing Section
- List test scenarios covered
- Include steps for manual testing if applicable
- Note any edge cases or limitations

## Examples

**Feature PR:**
```markdown
## Summary
Add email notifications when users receive new messages.

## Changes
- Add `NotificationService` for sending emails
- Create email templates for new message notifications
- Add user preference for notification frequency
- Update message creation to trigger notifications

## Why
Users frequently miss important messages. This addresses feedback from #234
and aligns with our Q1 engagement goals.

## Testing
- Unit tests for NotificationService
- Integration test for end-to-end notification flow
- Manual testing with different notification preferences

Fixes #234
```

**Bug Fix PR:**
```markdown
## Summary
Fix crash when uploading files larger than 10MB.

## Changes
- Increase multipart upload size limit in nginx config
- Add client-side file size validation with clear error message
- Add server-side validation with proper error response

## Why
Users reported crashes (see #567). Root cause was nginx
rejecting requests before our application code ran.

## Testing
- Tested with files: 5MB (pass), 10MB (pass), 15MB (proper error)
- Verified error message appears correctly in UI

Fixes #567
```
""",
)

TEMPLATE_API_DOCS = SkillTemplate(
    name="api-docs",
    title="API Documentation",
    description="Generate API documentation from code",
    category="Documentation",
    tags=["api", "documentation", "openapi", "rest"],
    content="""# Instructions

Help users create clear, comprehensive API documentation from their code.

## Documentation Format

For each endpoint, document:

### Endpoint Overview
```markdown
## Endpoint Name

Brief description of what this endpoint does.

**Method:** GET/POST/PUT/PATCH/DELETE
**Path:** `/api/v1/resource/{id}`
**Auth:** Required/Optional (type: Bearer, API Key, etc.)
```

### Request

```markdown
### Parameters

| Name | Type | Location | Required | Description |
|------|------|----------|----------|-------------|
| id | string | path | yes | Resource identifier |
| limit | integer | query | no | Max results (default: 20) |

### Request Body

```json
{
  "name": "string (required)",
  "email": "string (required, email format)",
  "settings": {
    "notifications": "boolean (default: true)"
  }
}
```
```

### Response

```markdown
### Success Response (200 OK)

```json
{
  "id": "abc123",
  "name": "Example",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_INPUT | Request body validation failed |
| 401 | UNAUTHORIZED | Missing or invalid authentication |
| 404 | NOT_FOUND | Resource does not exist |
```

## Guidelines

### When documenting existing code:
1. Identify all endpoints in the file/module
2. Extract parameter types and validation rules
3. Document request/response schemas
4. Note authentication requirements
5. Include realistic example values

### Best practices:
- Use consistent terminology throughout
- Include curl examples for complex requests
- Document rate limits if applicable
- Note deprecation warnings
- Link related endpoints

## Example Output

```markdown
## Create User

Creates a new user account.

**Method:** POST
**Path:** `/api/v1/users`
**Auth:** Required (API Key)

### Request Body

```json
{
  "email": "user@example.com",
  "name": "Jane Doe",
  "role": "member"
}
```

### Success Response (201 Created)

```json
{
  "id": "usr_abc123",
  "email": "user@example.com",
  "name": "Jane Doe",
  "role": "member",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Errors

| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_EMAIL | Email format is invalid |
| 409 | EMAIL_EXISTS | User with this email already exists |

### Example

```bash
curl -X POST https://api.example.com/v1/users \\
  -H "Authorization: Bearer $API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"email": "user@example.com", "name": "Jane Doe"}'
```
```
""",
)

TEMPLATE_DEBUGGING = SkillTemplate(
    name="debugging",
    title="Debugging Assistant",
    description="Systematic debugging assistance",
    category="Troubleshooting",
    tags=["debugging", "errors", "troubleshooting"],
    content="""# Instructions

Help users debug issues systematically by gathering information, forming hypotheses, and guiding them to solutions.

## Debugging Process

### 1. Understand the Problem
Ask clarifying questions:
- What is the expected behavior?
- What is the actual behavior?
- When did it start happening?
- What changed recently?
- Is it reproducible? How consistently?

### 2. Gather Information
Request relevant details:
- Error messages (exact text, full stack trace)
- Relevant code snippets
- Environment details (OS, versions, configuration)
- Steps to reproduce
- Logs from the relevant timeframe

### 3. Form Hypotheses
Based on the evidence, list possible causes ranked by likelihood:
1. Most likely cause and why
2. Second possibility
3. Less likely but worth checking

### 4. Guide Investigation
For each hypothesis, suggest:
- How to verify/disprove it
- Specific commands or code to run
- What to look for in the output

### 5. Provide Solutions
Once cause is identified:
- Explain the root cause clearly
- Provide the fix with code/commands
- Explain why this fixes it
- Suggest how to prevent it in the future

## Response Format

```markdown
## Understanding

Based on your description, the issue is: [summary]

## Initial Analysis

Looking at the error/behavior, the most likely causes are:

1. **[Most likely]** - [explanation]
2. **[Second possibility]** - [explanation]

## Next Steps

Let's verify hypothesis #1 first:

1. Run this command: `[command]`
2. Check the output for: [what to look for]
3. Share the results

## [After investigation]

## Root Cause

The issue is caused by: [explanation]

## Solution

[Code/steps to fix]

## Prevention

To prevent this in the future: [recommendations]
```

## Guidelines

- Don't jump to solutions - gather information first
- Ask for specific evidence (logs, errors, code)
- Explain your reasoning so users learn
- When suggesting fixes, explain WHY they work
- Consider edge cases in solutions
- Suggest preventive measures (tests, validation, monitoring)

## Common Debugging Techniques

Reference these when appropriate:
- Binary search (narrow down where the bug is)
- Rubber duck debugging (explain the code step by step)
- Print/log debugging (add strategic logging)
- Minimal reproduction (simplify to isolate the bug)
- Git bisect (find which commit introduced the bug)
- Compare with working state (diff against when it worked)
""",
)

TEMPLATE_SQL_HELPER = SkillTemplate(
    name="sql-helper",
    title="SQL Query Helper",
    description="Write and optimize SQL queries",
    category="Database",
    tags=["sql", "database", "queries", "optimization"],
    content="""# Instructions

Help users write correct, efficient SQL queries and optimize existing ones.

## Query Writing Process

### 1. Understand Requirements
Before writing, clarify:
- What data is needed? (columns, aggregations)
- What are the filter conditions?
- What's the expected result shape?
- Are there performance requirements?

### 2. Write the Query
Structure queries clearly:
```sql
SELECT
    column1,
    column2,
    aggregate_function(column3) AS alias
FROM table_name
JOIN other_table ON condition
WHERE filter_conditions
GROUP BY grouping_columns
HAVING aggregate_conditions
ORDER BY sort_columns
LIMIT n;
```

### 3. Explain the Query
For complex queries, break down:
- What each section does
- Why certain approaches were chosen
- Any assumptions made

## Query Optimization

When optimizing, check:

### Index Usage
- Are WHERE clause columns indexed?
- Are JOIN columns indexed?
- Is the ORDER BY using an index?

### Query Structure
- Avoid SELECT * (specify needed columns)
- Use EXISTS instead of IN for subqueries
- Avoid functions on indexed columns in WHERE
- Consider query rewriting for better plans

### Common Optimizations
```sql
-- Instead of
SELECT * FROM orders WHERE YEAR(created_at) = 2024;

-- Use
SELECT * FROM orders
WHERE created_at >= '2024-01-01'
  AND created_at < '2025-01-01';
```

## Response Format

```markdown
## Query

```sql
[The SQL query]
```

## Explanation

[What the query does, section by section]

## Performance Notes

[Index suggestions, potential issues, optimization tips]

## Example Output

[Sample of what results would look like]
```

## Guidelines

- Always use parameterized queries in application code
- Use meaningful table aliases
- Format queries for readability
- Consider NULL handling explicitly
- Test with representative data volumes
- Explain EXPLAIN output when analyzing performance

## Dialect Awareness

Ask about or note the SQL dialect:
- PostgreSQL, MySQL, SQLite, SQL Server, Oracle
- Syntax differences (LIMIT vs TOP, string functions)
- Available features (window functions, CTEs, JSON)
""",
)

TEMPLATE_TEST_WRITER = SkillTemplate(
    name="test-writer",
    title="Test Writer",
    description="Generate unit tests for code",
    category="Code Quality",
    tags=["testing", "unit-tests", "tdd", "coverage"],
    content="""# Instructions

Help users write comprehensive, maintainable unit tests for their code.

## Test Writing Process

### 1. Analyze the Code
Before writing tests, understand:
- What does the function/class do?
- What are the inputs and outputs?
- What are the edge cases?
- What dependencies does it have?

### 2. Plan Test Cases
Identify scenarios to cover:
- **Happy path**: Normal, expected usage
- **Edge cases**: Boundary values, empty inputs, nulls
- **Error cases**: Invalid inputs, exceptions
- **State changes**: If the code modifies state

### 3. Write Tests
Follow the AAA pattern:
```python
def test_descriptive_name():
    # Arrange - Set up test data and dependencies
    input_data = create_test_data()

    # Act - Execute the code under test
    result = function_under_test(input_data)

    # Assert - Verify the outcome
    assert result == expected_value
```

## Test Naming Convention

Use descriptive names that explain:
- What is being tested
- Under what conditions
- What the expected outcome is

Examples:
- `test_create_user_with_valid_email_returns_user_id`
- `test_create_user_with_invalid_email_raises_validation_error`
- `test_get_user_when_not_found_returns_none`

## Testing Patterns

### Parameterized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("valid@email.com", True),
    ("invalid", False),
    ("", False),
])
def test_validate_email(input, expected):
    assert validate_email(input) == expected
```

### Testing Exceptions
```python
def test_divide_by_zero_raises_error():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)
```

### Mocking Dependencies
```python
def test_get_user_calls_database(mocker):
    mock_db = mocker.patch('module.database')
    mock_db.query.return_value = User(id=1)

    result = get_user(1)

    mock_db.query.assert_called_once_with("SELECT * FROM users WHERE id = ?", 1)
```

## Response Format

```markdown
## Test Plan

Testing `[function/class name]`:
- Happy path: [scenarios]
- Edge cases: [scenarios]
- Error cases: [scenarios]

## Tests

```python
[Test code with clear names and comments]
```

## Coverage Notes

These tests cover:
- [What's covered]

Consider also testing:
- [Additional scenarios to consider]
```

## Guidelines

- One assertion per test (when practical)
- Tests should be independent and isolated
- Use fixtures for common setup
- Mock external dependencies
- Test behavior, not implementation details
- Keep tests fast and deterministic
""",
)

TEMPLATE_EXPLAINER = SkillTemplate(
    name="explainer",
    title="Code Explainer",
    description="Explain complex code or concepts clearly",
    category="Documentation",
    tags=["explanation", "learning", "documentation", "teaching"],
    content="""# Instructions

Help users understand code, concepts, or technical topics by providing clear, layered explanations.

## Explanation Approach

### 1. Start with the Big Picture
- What is the overall purpose?
- Where does this fit in the larger system?
- Why does this exist?

### 2. Progressive Detail
Layer your explanation:
1. **High-level summary** (1-2 sentences)
2. **Key concepts** (what you need to know first)
3. **Detailed walkthrough** (step by step)
4. **Nuances and edge cases** (when they ask)

### 3. Use Analogies
Connect new concepts to familiar ones:
- "This is like a..."
- "Think of it as..."
- "Similar to how..."

### 4. Provide Examples
Concrete examples make abstract concepts clear:
- Simple example first
- Then more realistic/complex
- Show common variations

## Explaining Code

When walking through code:

```
1. State what this code does (one sentence)
2. Identify the main components/sections
3. Explain each section's purpose
4. Trace through with example data
5. Note any tricky or non-obvious parts
```

### Example Format
```markdown
## Overview

This code [does X] by [approach Y].

## Key Concepts

Before diving in, understand:
- **Concept 1**: [brief explanation]
- **Concept 2**: [brief explanation]

## Walkthrough

### Section 1: [Purpose]
```code
[relevant code snippet]
```
This section [explanation]. It works by [how].

### Section 2: [Purpose]
...

## Example Execution

Given input: [example]
1. First, [step 1 happens]
2. Then, [step 2 happens]
3. Result: [output]

## Key Takeaways

- [Main point 1]
- [Main point 2]
```

## Guidelines

- Match the explanation depth to the user's level
- Ask clarifying questions if their background is unclear
- Avoid jargon, or define it when first used
- Use visual structure (headers, lists, code blocks)
- Check understanding: "Does this make sense so far?"
- Encourage questions

## Response to "Explain this code"

1. Read through the code completely first
2. Identify the language, framework, patterns used
3. Determine the code's purpose
4. Start with one-sentence summary
5. Break into logical sections
6. Explain each section with context
7. Trace through with concrete example
8. Highlight clever/tricky/important parts
""",
)


# =============================================================================
# Template Registry
# =============================================================================

BUILTIN_TEMPLATES: dict[str, SkillTemplate] = {
    "code-review": TEMPLATE_CODE_REVIEW,
    "git-commit": TEMPLATE_GIT_COMMIT,
    "git-pr": TEMPLATE_GIT_PR,
    "api-docs": TEMPLATE_API_DOCS,
    "debugging": TEMPLATE_DEBUGGING,
    "sql-helper": TEMPLATE_SQL_HELPER,
    "test-writer": TEMPLATE_TEST_WRITER,
    "explainer": TEMPLATE_EXPLAINER,
}


# =============================================================================
# Public API
# =============================================================================


def get_template(name: str) -> Optional[SkillTemplate]:
    """Get a template by name.

    Args:
        name: Template name (e.g., "code-review")

    Returns:
        SkillTemplate if found, None otherwise
    """
    return BUILTIN_TEMPLATES.get(name)


def list_templates() -> list[SkillTemplate]:
    """Get all available templates.

    Returns:
        List of all built-in templates, sorted by category then name
    """
    return sorted(
        BUILTIN_TEMPLATES.values(),
        key=lambda t: (t.category, t.name),
    )


def get_templates_by_category() -> dict[str, list[SkillTemplate]]:
    """Get templates grouped by category.

    Returns:
        Dict mapping category names to lists of templates
    """
    by_category: dict[str, list[SkillTemplate]] = {}
    for template in BUILTIN_TEMPLATES.values():
        if template.category not in by_category:
            by_category[template.category] = []
        by_category[template.category].append(template)

    # Sort templates within each category
    for templates in by_category.values():
        templates.sort(key=lambda t: t.name)

    return by_category


def get_template_names() -> list[str]:
    """Get all template names.

    Returns:
        Sorted list of template names
    """
    return sorted(BUILTIN_TEMPLATES.keys())
