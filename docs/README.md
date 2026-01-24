# SkillForge Documentation

Welcome to the SkillForge documentation. This guide covers everything you need to create, test, secure, and deploy skills for Claude.

## Quick Links

| Document | Description |
|----------|-------------|
| [Skill Authoring Guide](skill-authoring-guide.md) | Best practices for writing effective skills |
| [CLI Cheat Sheet](cli-cheatsheet.md) | Quick reference for all commands |
| [Testing Guide](testing-guide.md) | Write and run tests for your skills |
| [Hub Guide](hub-guide.md) | Browse, install, and publish skills |

## Getting Started

### 1. Install SkillForge

```bash
pip install ai-skillforge[ai]
```

### 2. Create Your First Skill

```bash
# Option A: Generate with AI (fastest)
export ANTHROPIC_API_KEY=your-key
skillforge generate "Help users write clear git commit messages"

# Option B: Use a template
skillforge new my-skill --template code-review

# Option C: Start from scratch
skillforge new my-skill -d "Help with task X"
```

### 3. Validate and Test

```bash
skillforge validate ./skills/my-skill
skillforge test ./skills/my-skill
```

### 4. Deploy

```bash
# To Claude Code (instant)
skillforge install ./skills/my-skill

# To claude.ai (upload zip)
skillforge bundle ./skills/my-skill
```

## Documentation Structure

```
docs/
├── README.md                 # This file
├── skill-authoring-guide.md  # How to write effective skills
├── cli-cheatsheet.md         # Command quick reference
├── testing-guide.md          # Testing skills
└── hub-guide.md              # Community hub
```

## Tutorials

Step-by-step guides in the [examples/tutorials/](../examples/tutorials/) directory:

1. [Getting Started](../examples/tutorials/01-getting-started.md) - Create your first skill
2. [Testing Skills](../examples/tutorials/02-testing-skills.md) - Write and run tests
3. [Security & Governance](../examples/tutorials/03-security-governance.md) - Secure your skills
4. [Multi-Platform Publishing](../examples/tutorials/04-multi-platform.md) - Deploy everywhere
5. [MCP Integration](../examples/tutorials/05-mcp-integration.md) - Expose skills as MCP tools

## Example Skills

See [examples/skills/](../examples/skills/) for complete working examples:

| Skill | Features Demonstrated |
|-------|----------------------|
| code-reviewer | Basic skill structure, tests |
| git-commit | Templates, multiple examples |
| api-documenter | Composite skills with includes |
| data-analyst | Versioning, metadata |

## Need Help?

- [GitHub Discussions](https://github.com/lhassa8/skillforge/discussions) - Ask questions
- [Issue Tracker](https://github.com/lhassa8/skillforge/issues) - Report bugs
- [SkillForge Hub](https://lhassa8.github.io/skillforge-hub/) - Browse community skills
