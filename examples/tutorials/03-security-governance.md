# Tutorial 3: Security & Governance

Learn how to scan skills for security issues and implement enterprise governance.

## Security Scanning

### Basic Scan

```bash
skillforge security scan ./my-skill

# Output:
# Scanning my-skill...
#
# ✓ No critical issues found
# ⚠ 1 medium issue found
#
# [MEDIUM] Potential sensitive data pattern
#   Line 45: Contains pattern matching API keys
#   Suggestion: Ensure no real credentials are included
#
# Risk Score: 25/100
# Status: PASSED
```

### What It Detects

| Category | Examples |
|----------|----------|
| **Prompt Injection** | "Ignore previous instructions", jailbreak attempts |
| **Credential Exposure** | API keys, passwords, private keys |
| **Data Exfiltration** | Requests to send data externally |
| **Unsafe Operations** | Code execution, file system access |
| **PII Patterns** | SSN, credit cards, email addresses |

### Scan Options

```bash
# Filter by severity
skillforge security scan ./my-skill --min-severity medium

# JSON output for CI
skillforge security scan ./my-skill --format json

# Fail if issues found (for CI)
skillforge security scan ./my-skill --fail-on-issues
```

### View Security Patterns

```bash
# List all patterns
skillforge security patterns

# Filter by severity
skillforge security patterns --severity critical

# Filter by type
skillforge security patterns --type credential_exposure
```

## Trust Tiers

Classify skills by their verification status:

| Tier | Description | Use Case |
|------|-------------|----------|
| `untrusted` | Unknown source, not reviewed | Development only |
| `community` | Community-contributed, basic review | Internal testing |
| `verified` | Security scanned, code reviewed | Staging environments |
| `enterprise` | Full audit, approved by security | Production |

### Managing Trust

```bash
# View current trust level
skillforge governance trust ./my-skill

# Set trust tier
skillforge governance trust ./my-skill --set verified

# Set with notes
skillforge governance trust ./my-skill --set enterprise \
  --notes "Approved by security team on 2024-01-15"
```

## Governance Policies

Policies define requirements for different environments.

### Built-in Policies

```bash
# List policies
skillforge governance policy list

# View policy details
skillforge governance policy show production
```

| Policy | Min Trust | Max Risk | Approval |
|--------|-----------|----------|----------|
| `development` | untrusted | 100 | No |
| `staging` | community | 70 | No |
| `production` | verified | 30 | Yes |
| `enterprise` | enterprise | 10 | Yes |

### Check Against Policy

```bash
# Check if skill meets policy requirements
skillforge governance check ./my-skill --policy production

# Output:
# Checking my-skill against 'production' policy...
#
# ✓ Trust tier: verified (required: verified)
# ✓ Risk score: 25 (max: 30)
# ✗ Approval: Not approved (required: yes)
#
# Status: FAILED
# Action needed: Skill requires approval for production
```

### Create Custom Policy

```bash
skillforge governance policy create my-team-policy
```

Edit the generated policy file:

```yaml
name: my-team-policy
description: Policy for my team's skills
min_trust_tier: community
max_risk_score: 50
required_scans:
  - security
  - credentials
approval_required: false
allowed_tags:
  - internal
  - approved
```

## Audit Trail

Track all skill lifecycle events.

### View Audit Log

```bash
# Recent events
skillforge governance audit

# Filter by skill
skillforge governance audit --skill my-skill

# Filter by date
skillforge governance audit --from 2024-01-01 --to 2024-01-31

# Filter by event type
skillforge governance audit --type security_scan
```

### Event Types

| Type | Description |
|------|-------------|
| `created` | Skill was created |
| `modified` | Skill content changed |
| `security_scan` | Security scan performed |
| `trust_changed` | Trust tier modified |
| `policy_check` | Policy compliance checked |
| `approved` | Skill formally approved |

### Audit Summary

```bash
skillforge governance audit --summary

# Output:
# Audit Summary (Last 30 days)
#
# Total Events: 156
# Skills Modified: 12
# Security Scans: 45
# Policy Violations: 3
# Approvals: 8
```

## Approval Workflow

Formally approve skills for deployment:

```bash
# Approve for verified tier
skillforge governance approve ./my-skill --tier verified

# Approve with notes
skillforge governance approve ./my-skill --tier enterprise \
  --notes "Reviewed by @security-team, ticket SEC-1234"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Skill Security

on:
  pull_request:
    paths:
      - 'skills/**'

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install SkillForge
        run: pip install ai-skillforge

      - name: Security Scan
        run: |
          for skill in skills/*/; do
            skillforge security scan "$skill" --fail-on-issues
          done

      - name: Policy Check
        run: |
          for skill in skills/*/; do
            skillforge governance check "$skill" --policy staging
          done
```

## Best Practices

1. **Scan early**: Run security scans in CI before merge
2. **Use policies**: Define clear policies for each environment
3. **Require approval**: Production skills should require explicit approval
4. **Audit regularly**: Review audit logs for anomalies
5. **Least privilege**: Start with `untrusted` and upgrade as reviewed

## Next Steps

- [Tutorial 4: Multi-Platform Publishing](./04-multi-platform.md)
- [Tutorial 5: MCP Integration](./05-mcp-integration.md)
