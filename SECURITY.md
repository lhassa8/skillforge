# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in SkillForge, please report it responsibly.

### How to Report

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email security concerns to the maintainers (see GitHub profile)
3. Or use [GitHub's private vulnerability reporting](https://github.com/lhassa8/skillforge/security/advisories/new)

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Resolution Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Next release

### Security Best Practices for Users

#### API Keys

- Store API keys in environment variables, not in code or skill files
- Never commit `.env` files or API keys to version control
- Use separate API keys for development and production

```bash
# Set API key for current session
export ANTHROPIC_API_KEY=your-key

# Or use a .env file (add to .gitignore)
echo "ANTHROPIC_API_KEY=your-key" >> .env
echo ".env" >> .gitignore
```

#### Skill Content

- **Review generated skills** before deploying — verify AI-generated content
- **Never include secrets** in SKILL.md files (passwords, tokens, internal URLs)
- **Use security scanning** before deployment:
  ```bash
  skillforge security scan ./skills/my-skill
  ```

#### Bundle Security

- SkillForge validates zip files to prevent path traversal attacks
- Symlinks are excluded from bundles
- Maximum recommended bundle size: 10MB

## Security Features

SkillForge includes built-in security tools:

```bash
# Scan for vulnerabilities
skillforge security scan ./skills/my-skill

# Check against governance policy
skillforge governance check ./skills/my-skill --policy production

# View audit trail
skillforge governance audit --skill my-skill
```

## Acknowledgments

We appreciate responsible disclosure and will acknowledge security researchers who report valid vulnerabilities (unless they prefer to remain anonymous).
