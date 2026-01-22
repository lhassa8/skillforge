---
schema_version: "1.0"
name: git-commit
description: Use when asked to write git commit messages. Follows conventional commit format with clear, descriptive messages.
version: 1.0.0
min_skillforge_version: 1.0.0
tags:
  - git
  - productivity
---

# Git Commit Message Writer

Help users write clear, conventional commit messages that describe changes effectively.

## Conventional Commit Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | When to Use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change, no new feature or fix |
| `perf` | Performance improvement |
| `test` | Adding/updating tests |
| `chore` | Build, CI, dependencies |

### Rules

1. **Subject line**: Max 50 characters, imperative mood ("Add" not "Added")
2. **Body**: Wrap at 72 characters, explain what and why
3. **Scope**: Optional, indicates area of codebase
4. **Breaking changes**: Add `!` after type or `BREAKING CHANGE:` in footer

## Examples

### Example 1: Simple Feature

**User**: I added a dark mode toggle to the settings page

**Response**:
```
feat(settings): add dark mode toggle

Add toggle switch to settings page that allows users to switch
between light and dark themes. Preference is saved to localStorage.
```

### Example 2: Bug Fix

**User**: Fixed a crash when users submit empty forms

**Response**:
```
fix(forms): prevent crash on empty form submission

Add validation check before processing form data. Return early
with error message if required fields are empty.

Fixes #234
```

### Example 3: Breaking Change

**User**: Changed the API response format from array to object

**Response**:
```
feat(api)!: change response format to object wrapper

Wrap all API responses in an object with `data` and `meta` fields
for consistency and to support pagination metadata.

BREAKING CHANGE: API responses are now wrapped in an object.
Clients must access data via `response.data` instead of directly.
```

### Example 4: Multiple Changes

**User**: I refactored the auth module and fixed a token refresh bug

**Response**:
For multiple distinct changes, suggest separate commits:

```
refactor(auth): extract token handling to separate module

Move token storage, validation, and refresh logic from auth.js
to dedicated token.js module for better separation of concerns.
```

```
fix(auth): handle expired refresh tokens correctly

Check refresh token expiry before attempting refresh. Redirect
to login if refresh token is also expired.

Fixes #456
```

## Tips

- If unsure about the scope of changes, ask for clarification
- Suggest splitting large changes into multiple commits
- Reference issue numbers when fixing bugs
- Mention breaking changes prominently
