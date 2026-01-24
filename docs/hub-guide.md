# SkillForge Hub Guide

The [SkillForge Hub](https://lhassa8.github.io/skillforge-hub/) is a community repository where developers share pre-built skills. Browse, install, and contribute skills to extend Claude's capabilities.

## Browsing Skills

### Web Interface

Visit [lhassa8.github.io/skillforge-hub](https://lhassa8.github.io/skillforge-hub/) to:

- Browse all available skills
- Filter by category (Code Quality, Documentation, Productivity, Data)
- Sort by stars, downloads, or name
- View skill details and documentation
- Star your favorite skills

### CLI

```bash
# List all skills
skillforge hub list

# Search for skills
skillforge hub search "code review"
skillforge hub search react
skillforge hub search kubernetes

# Get detailed information
skillforge hub info code-reviewer
```

## Installing Skills

### Install to User Directory (Global)

Skills installed to `~/.claude/skills/` are available in all your projects:

```bash
skillforge hub install code-reviewer
skillforge hub install docker-helper
skillforge hub install git-commit
```

### Install to Project Directory (Local)

Skills installed to `./.claude/skills/` are only available in the current project:

```bash
skillforge hub install code-reviewer --project
```

### Verify Installation

```bash
# List installed skills
skillforge installed

# Test the installed skill
skillforge test ~/.claude/skills/code-reviewer
```

## Popular Skills

### Code Quality

| Skill | Description |
|-------|-------------|
| `code-reviewer` | Review code for bugs, security, and style |
| `refactorer` | Refactor code for better structure |
| `performance-optimizer` | Identify performance improvements |
| `security-auditor` | Audit code for vulnerabilities |
| `naming-helper` | Suggest better variable/function names |

### Development

| Skill | Description |
|-------|-------------|
| `test-writer` | Generate unit tests |
| `debugger` | Systematic debugging assistance |
| `error-handler` | Add proper error handling |
| `docker-helper` | Write Dockerfiles and compose configs |
| `kubernetes-helper` | Create K8s manifests |

### Documentation

| Skill | Description |
|-------|-------------|
| `api-documenter` | Generate API documentation |
| `readme-writer` | Create comprehensive READMEs |
| `code-commenter` | Add comments and docstrings |
| `changelog-writer` | Write changelog entries |

### Productivity

| Skill | Description |
|-------|-------------|
| `git-commit` | Write conventional commit messages |
| `pr-reviewer` | Review pull requests |
| `bash-scripter` | Write shell scripts |
| `regex-helper` | Build and explain regex patterns |

## Publishing Skills

Share your skills with the community by publishing to the hub.

### Prerequisites

1. **GitHub CLI** - Install from [cli.github.com](https://cli.github.com)
2. **Authenticated** - Run `gh auth login`
3. **Valid skill** - Must pass validation

### Prepare Your Skill

```bash
# Validate
skillforge validate ./skills/my-skill --strict

# Test
skillforge test ./skills/my-skill

# Security scan
skillforge security scan ./skills/my-skill --fail-on-issues
```

### Publish

```bash
# Basic publish
skillforge hub publish ./skills/my-skill

# With a message
skillforge hub publish ./skills/my-skill -m "Adds support for TypeScript"
```

### What Happens

1. SkillForge validates your skill
2. Forks the hub repository (if needed)
3. Creates a branch with your skill
4. Opens a pull request

### Pull Request Review

Your PR will be reviewed for:

- **Quality**: Clear instructions, good examples
- **Usefulness**: Solves a real problem
- **Security**: No malicious content
- **Uniqueness**: Doesn't duplicate existing skills

## Skill Requirements

### Required Files

```
my-skill/
├── SKILL.md      # Required: Main skill definition
└── README.md     # Recommended: User documentation
```

### SKILL.md Requirements

```yaml
---
name: my-skill-name          # Lowercase, hyphens only
description: Use when...     # When should Claude use this?
version: 1.0.0              # Semantic version
author: your-github-name    # Your identifier
tags:                       # Categories for discovery
  - code-quality
  - python
---

# My Skill

Instructions, examples, etc.
```

### README.md Template

```markdown
# My Skill Name

Brief description of what this skill does.

## Installation

\`\`\`bash
skillforge hub install my-skill-name
\`\`\`

## What It Does

- Feature 1
- Feature 2
- Feature 3

## Usage Examples

\`\`\`
Example user request and what to expect
\`\`\`

## License

MIT
```

## Star System

Skills can be starred to show appreciation and help others discover quality skills.

### How Stars Work

1. Each skill has a GitHub Issue for stars
2. Users add reactions (thumbs up) to star
3. A GitHub Action syncs star counts to `index.json`
4. The website displays star counts

### Star a Skill

1. Go to the skill's page on the hub
2. Click the "Star" button
3. Add a thumbs-up reaction on GitHub

## Updating Published Skills

To update a skill you've published:

```bash
# Make your changes locally
# ...

# Bump version
skillforge version bump ./skills/my-skill --minor

# Publish again (creates new PR)
skillforge hub publish ./skills/my-skill -m "Version 1.1.0: Added X"
```

## Best Practices

### For Publishers

- **Write clear descriptions** - Help users find your skill
- **Include examples** - Show what your skill can do
- **Add tests** - Prove your skill works
- **Keep it focused** - One skill, one purpose
- **Document edge cases** - What happens with unusual input?

### For Users

- **Check the description** - Make sure it fits your use case
- **Read the README** - Understand what you're installing
- **Test locally first** - Verify it works for you
- **Report issues** - Help improve the skill

## Troubleshooting

### "GitHub CLI not installed"

```bash
# macOS
brew install gh

# Ubuntu
sudo apt install gh

# Then authenticate
gh auth login
```

### "Skill validation failed"

```bash
# Check what's wrong
skillforge validate ./skills/my-skill

# Common fixes:
# - Name must be lowercase with hyphens
# - Description must explain when to use
# - SKILL.md must have valid frontmatter
```

### "PR already exists"

Your previous PR is still open. Either:
- Wait for it to be merged
- Close it and try again
- Update the existing PR manually

## Hub Repository

The hub is open source: [github.com/lhassa8/skillforge-hub](https://github.com/lhassa8/skillforge-hub)

### Structure

```
skillforge-hub/
├── index.json           # Skill index (auto-generated)
├── skills/              # All skills
│   ├── code-reviewer/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── tests.yml
│   └── ...
├── index.html           # Website
├── app.js               # Website logic
└── .github/
    └── workflows/       # Automation
```

### Contributing to the Hub

Beyond adding skills, you can:

- Improve the website
- Add new categories
- Enhance the search
- Fix bugs

See the [Contributing Guide](https://github.com/lhassa8/skillforge-hub/blob/main/CONTRIBUTING.md).
