---
name: git-commit-message-writer
description: Use when users need help writing clear, conventional git commit messages that follow best practices. Assists with proper formatting, type selection, scope definition, and descriptive summaries for version control, including monorepo and squash merge scenarios.
---

# Git Commit Message Writer

Help users create clear, conventional git commit messages that follow industry best practices and improve project maintainability. Supports both single-repo and monorepo workflows, including guidance for squash merges and complex change scenarios.

## Core Instructions

When a user requests help with git commit messages, follow this systematic approach:

1. **Analyze the changes** - Understand what was modified, added, or removed
2. **Determine the context** - Single repo, monorepo, squash merge, or regular commit
3. **Select the commit type** - Choose from conventional commit standards
4. **Define the scope** - Identify affected components, packages, or modules
5. **Craft the summary** - Write clear, imperative description under 50 characters
6. **Add body content** - Explain what and why for complex changes
7. **Include footers** - Add breaking changes, issue references, co-authors

## Conventional Commit Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Commit Types Reference

| Type | Purpose | Examples |
|------|---------|----------|
| `feat` | New features for users | Add search functionality, implement payment flow |
| `fix` | Bug fixes | Resolve memory leak, fix validation error |
| `docs` | Documentation only | Update README, add API docs, fix typos in comments |
| `style` | Code formatting/style | Fix indentation, remove trailing spaces, organize imports |
| `refactor` | Code restructuring | Extract utility functions, rename variables, simplify logic |
| `perf` | Performance improvements | Optimize database queries, reduce bundle size, cache API calls |
| `test` | Testing changes | Add unit tests, update test fixtures, mock external services |
| `chore` | Maintenance tasks | Update dependencies, configure linters, clean up files |
| `ci` | CI/CD changes | Update GitHub Actions, modify build scripts, add deployment steps |
| `build` | Build system changes | Update webpack config, modify package.json, change build tools |
| `revert` | Revert previous commit | Revert "feat: add user dashboard" |

## Scope Guidelines

### Single Repository Scopes
- Component names: `button`, `navbar`, `auth`
- Feature areas: `api`, `ui`, `database`, `config`
- File types: `tests`, `docs`, `scripts`

### Monorepo Scopes
- Package names: `@company/core`, `web-app`, `mobile-app`
- Workspace areas: `packages/auth`, `apps/dashboard`, `libs/utils`
- Cross-cutting: `deps` (dependencies), `config` (shared config), `ci` (affects multiple packages)

## Message Structure Best Practices

### Summary Line (≤50 characters)
- Use imperative mood: "add", "fix", "update" (not "added", "fixing", "updates")
- Start with lowercase letter after type
- No period at the end
- Be specific and actionable

### Body (wrapped at 72 characters)
- Explain **what** changed and **why**
- Separate from summary with blank line
- Use bullet points for multiple changes
- Include context for future maintainers

### Footer
- **Breaking changes**: `BREAKING CHANGE: description`
- **Issue references**: `Fixes #123`, `Closes #456`, `Refs #789`
- **Co-authors**: `Co-authored-by: Name <email@example.com>`
- **Reviewers**: `Reviewed-by: Name <email@example.com>`

## Comprehensive Examples

### Example 1: Basic Feature Addition
**User request**: "I added a dark mode toggle to the settings page"

**Response**:
```
feat(settings): add dark mode toggle

Implement theme switching functionality in user settings
with persistent storage and system preference detection.

- Add toggle component with smooth transition
- Store preference in localStorage
- Detect system dark mode preference
- Apply theme classes to root element

Closes #234
```

### Example 2: Monorepo Package Update
**User request**: "I updated the authentication library in our monorepo to support OAuth providers"

**Response**:
```
feat(@company/auth): add OAuth provider support

Extend authentication library to support Google, GitHub,
and Microsoft OAuth flows with configurable providers.

- Add OAuth provider interface and implementations
- Update AuthService to handle OAuth flows
- Add provider configuration options
- Include OAuth callback handling
- Update type definitions

BREAKING CHANGE: AuthConfig now requires 'providers' array.
Replace 'authType: "basic"' with 'providers: ["basic"]'.

Affects: web-app, mobile-app, admin-dashboard
Closes #567
```

### Example 3: Critical Bug Fix
**User request**: "Fixed a security vulnerability where user data was being logged in production"

**Response**:
```
fix(security): prevent user data logging in production

Remove sensitive user information from debug logs that
were inadvertently enabled in production environment.

- Strip PII from log messages
- Add environment check for debug logging
- Update logging middleware configuration
- Add data sanitization utility

Security impact: Prevents exposure of user emails,
phone numbers, and session tokens in application logs.

Fixes CVE-2024-XXXX
Closes #urgent-892
```

### Example 4: Squash Merge Summary
**User request**: "I'm squashing a PR that added user profiles, fixed some bugs, and updated tests"

**Response**:
```
feat(user): implement user profile management

Complete user profile feature implementation with full
CRUD operations, validation, and comprehensive testing.

Features added:
- User profile creation and editing forms
- Profile picture upload with image optimization
- Privacy settings and visibility controls
- Profile validation and error handling

Bug fixes:
- Resolve avatar upload memory leak
- Fix profile form validation edge cases
- Correct timezone handling in profile dates

Testing:
- Add comprehensive unit tests for ProfileService
- Include integration tests for profile API endpoints
- Add E2E tests for profile management workflows

Closes #123, #124, #125
```

### Example 5: Documentation Update
**User request**: "Updated the API documentation to reflect the new pagination parameters"

**Response**:
```
docs(api): update pagination parameter documentation

Revise API docs to include new cursor-based pagination
options and deprecation notice for offset pagination.

- Document cursor, limit, and direction parameters
- Add pagination examples for common use cases
- Mark offset/page parameters as deprecated
- Update OpenAPI specification
- Include migration guide for existing clients

Refs #345
```

### Example 6: Performance Optimization
**User request**: "Optimized the product search to reduce database queries from 50 to 3 per search"

**Response**:
```
perf(search): optimize product search query performance

Reduce database queries by implementing eager loading
and query consolidation for product search results.

Performance improvements:
- Consolidate related data fetching into single queries
- Add database indexes for search columns
- Implement result caching for popular searches
- Use connection pooling for concurrent requests

Results: Search response time reduced from 2.1s to 0.3s
with 94% fewer database queries per search operation.

Closes #perf-789
```

## Advanced Scenarios

### Monorepo Multi-Package Changes
**User request**: "I updated the shared utility library and updated all packages that use it"

**Response**:
```
feat(libs/utils): add date formatting utilities

Add comprehensive date formatting functions with
internationalization support for use across all apps.

Changes:
- Add formatDate, formatRelative, and formatDuration functions
- Include locale support for 15 languages
- Add timezone handling utilities
- Export new functions from main utils package

Package updates:
- @company/web-app: integrate new date formatters
- @company/mobile-app: replace moment.js with utils
- @company/admin: update reporting date displays

BREAKING CHANGE: Removes deprecated formatTimestamp function.
Use formatDate(date, 'timestamp') instead.

Affects: all packages using date utilities
Closes #456
```

### Squash Merge with Breaking Changes
**User request**: "Squashing a PR that refactored our API structure and updated the client libraries"

**Response**:
```
feat(api): restructure REST API with versioning support

Major API restructuring to support versioning and improve
consistency across endpoints with updated client libraries.

API changes:
- Add /v2 prefix to all endpoints
- Standardize response format with meta wrapper
- Implement consistent error response structure
- Add request/response validation middleware

Client updates:
- Update JavaScript client for v2 API format
- Add TypeScript definitions for new responses
- Include migration utilities for v1 to v2
- Add backward compatibility layer

Documentation:
- Complete API v2 documentation
- Migration guide from v1 to v2
- Update code examples and tutorials

BREAKING CHANGE: API response format changed from direct data
return to wrapped format: { data: {...}, meta: {...} }.
All client applications must update to use response.data.

Migration: Use included client library v2.0+ or manually
wrap existing API calls to handle new response structure.

Closes #major-refactor-123
```

### Emergency Hotfix
**User request**: "Quick fix for production issue where payments were failing due to API timeout"

**Response**:
```
fix(payments): increase API timeout for payment processing

Emergency fix for payment failures caused by insufficient
timeout values during high-traffic periods.

- Increase payment API timeout from 5s to 15s
- Add retry logic with exponential backoff
- Implement circuit breaker for payment service
- Add enhanced logging for payment failures

Impact: Resolves 95% of payment timeout failures
observed during peak hours.

Hotfix for production issue reported at 14:30 UTC.
Fixes #critical-payment-001
```

## Edge Cases and Special Situations

### Multiple Unrelated Changes
**When user describes several unrelated changes:**
1. Recommend separate commits for better git history
2. Provide individual commit messages for each change
3. Explain the benefits of atomic commits

**Example response:**
"I recommend splitting this into separate commits for better traceability:

1. `feat(auth): add password reset functionality`
2. `fix(ui): resolve mobile navigation overlap`
3. `docs: update deployment instructions`

This makes it easier to review, revert, and understand each change independently."

### Unclear or Vague Descriptions
**When user provides insufficient detail:**
Ask targeted questions:
- "What specific functionality was added/changed?"
- "What was the behavior before and after?"
- "Which files or components were affected?"
- "Was this fixing a bug or adding something new?"

### Dependency Updates
**User request**: "Updated all npm packages to latest versions"

**Response**:
```
chore(deps): update npm packages to latest versions

Update all project dependencies to resolve security
vulnerabilities and improve compatibility.

Major updates:
- react: 17.0.2 → 18.2.0
- typescript: 4.5.4 → 5.1.6
- webpack: 5.74.0 → 5.88.2

Security fixes:
- lodash: fix prototype pollution vulnerability
- axios: resolve SSRF vulnerability

Breaking changes addressed:
- Update React component lifecycle methods
- Fix TypeScript strict mode compatibility
- Adjust webpack configuration for v5 changes

Tested: All existing functionality verified
Fixes: 7 security vulnerabilities
Refs #maintenance-456
```

### Revert Commits
**User request**: "I need to revert the commit that added the experimental chat feature"

**Response**:
```
revert: feat(chat): add experimental real-time chat

This reverts commit a1b2c3d4e5f6789012345678901234567890abcd.

Reverting due to performance issues in production that
caused 40% increase in server response times.

- Removes WebSocket chat functionality
- Restores previous messaging system
- Removes chat-related database tables
- Removes chat UI components

Will be reimplemented with performance optimizations
after further testing in staging environment.

Refs #performance-issue-789
```

## Quality Checklist

Before finalizing any commit message, verify:

- ✅ **Type** is appropriate for the change
- ✅ **Scope** accurately represents affected area
- ✅ **Summary** is under 50 characters and imperative
- ✅ **Body** explains what and why (if needed)
- ✅ **Breaking changes** are clearly documented
- ✅ **Issue references** are included
- ✅ **Format** follows conventional commit standard
- ✅ **Context** is sufficient for future maintainers

## Pro Tips

1. **For monorepos**: Always include package/workspace in scope
2. **For squash merges**: Summarize the overall feature, not individual commits
3. **For breaking changes**: Always include migration guidance
4. **For performance changes**: Include metrics when available
5. **For security fixes**: Mention impact without exposing vulnerabilities
6. **For emergency fixes**: Include timestamp and urgency context

Always offer to refine the commit message or provide alternatives if the user has specific team conventions or preferences.