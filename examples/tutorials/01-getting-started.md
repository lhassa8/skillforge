# Tutorial 1: Getting Started with SkillForge

Learn how to create, validate, and deploy your first skill in under 5 minutes.

## Prerequisites

```bash
pip install ai-skillforge[ai]
export ANTHROPIC_API_KEY=your-key  # Optional, for AI generation
```

## Option 1: Generate with AI (Fastest)

```bash
# Generate a skill from a description
skillforge generate "Help users write clear documentation for Python functions"

# Output:
# ✓ Generated skill: skills/python-documentation-writer
```

That's it! The AI creates a complete skill with instructions, examples, and proper formatting.

## Option 2: Use a Template

```bash
# List available templates
skillforge templates

# Create from template
skillforge new my-code-reviewer --template code-review

# Preview the template first
skillforge templates show code-review
```

## Option 3: Create Manually

```bash
# Create a skill scaffold
skillforge new my-first-skill -d "Help with task X"

# This creates:
# skills/my-first-skill/
# └── SKILL.md
```

Edit `skills/my-first-skill/SKILL.md`:

```markdown
---
name: my-first-skill
description: Use when the user asks for help with task X.
---

# My First Skill

You help users with task X.

## Instructions

1. First, understand what the user needs
2. Then, provide clear guidance
3. Include examples when helpful

## Examples

### Example 1

**User**: How do I do X?

**Response**: Here's how to do X...
```

## Validate Your Skill

```bash
skillforge validate ./skills/my-first-skill

# Output:
# ✓ SKILL.md exists
# ✓ Name format is valid
# ✓ Description is present
# ✓ All checks passed!
```

## Preview How Claude Sees It

```bash
skillforge preview ./skills/my-first-skill
```

## Deploy Your Skill

### To Claude Code (Recommended)

```bash
# Install to user directory (available everywhere)
skillforge install ./skills/my-first-skill

# Or install to current project only
skillforge install ./skills/my-first-skill --project
```

Your skill is now active in Claude Code!

### To claude.ai

```bash
# Create a zip bundle
skillforge bundle ./skills/my-first-skill

# Output: skills/my-first-skill.zip
```

Upload the zip at **claude.ai → Settings → Features → Custom Skills**.

## Next Steps

- [Tutorial 2: Testing Skills](./02-testing-skills.md) - Add tests to catch issues
- [Tutorial 3: Security & Governance](./03-security-governance.md) - Secure your skills
- [Tutorial 4: Multi-Platform Publishing](./04-multi-platform.md) - Deploy everywhere

## Quick Reference

| Command | Description |
|---------|-------------|
| `skillforge generate "..."` | AI-generate a skill |
| `skillforge new NAME` | Create skill scaffold |
| `skillforge validate PATH` | Validate skill |
| `skillforge preview PATH` | Preview skill |
| `skillforge install PATH` | Install to Claude Code |
| `skillforge bundle PATH` | Create zip for claude.ai |
