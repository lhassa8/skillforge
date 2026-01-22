# SkillForge Roadmap

## Current Version: v1.0.0 (Production Release)

## v1.1.0 - Skill Sharing & Collaboration

**Theme: "Share and Discover"**

**Target:** Enable teams to share, discover, and collaborate on skills.

### New Features

#### 1. Skill Registry Hub

Public and private skill registries with search and discovery.

```bash
# Publish to public registry
skillforge publish ./my-skill --registry hub

# Search for skills
skillforge search "code review" --registry hub

# Pull from registry
skillforge pull @username/code-reviewer

# Create private team registry
skillforge registry create my-team --private
```

**Implementation:**
- `skillforge/hub/` - Hub client and API
- GitHub-backed registries with releases as versions
- Skill metadata indexing for search
- Download counts and ratings

#### 2. Skill Signing & Verification

Cryptographic signing for skill authenticity.

```bash
# Sign a skill
skillforge sign ./my-skill --key ~/.skillforge/key.pem

# Verify signature
skillforge verify ./my-skill

# Require signed skills
skillforge config set require_signatures true
```

**Implementation:**
- Ed25519 signatures
- Public key registry
- Chain of trust for organizations

#### 3. Skill Dependencies

Skills that depend on other skills.

```yaml
# SKILL.md frontmatter
---
name: full-stack-reviewer
dependencies:
  - code-reviewer: ^1.0.0
  - security-scanner: ^2.0.0
---
```

```bash
# Install with dependencies
skillforge install ./full-stack-reviewer --with-deps

# Update dependencies
skillforge update ./full-stack-reviewer
```

#### 4. Skill Variants & A/B Testing

Test different skill versions side-by-side.

```bash
# Create variant
skillforge variant create ./my-skill --name concise

# Run A/B test
skillforge test ./my-skill --variants concise,verbose --compare

# View comparison report
skillforge variant report ./my-skill
```

#### 5. Import from Other Formats

Convert existing prompts and GPTs to skills.

```bash
# Import OpenAI Custom GPT
skillforge import gpt --url https://chat.openai.com/g/g-xxx

# Import from prompt file
skillforge import prompt ./system-prompt.txt

# Import from LangChain hub
skillforge import langchain hub/owner/prompt-name
```

### CLI Additions

```
skillforge hub
├── publish              # Publish to registry
├── search               # Search skills
├── info                 # View skill details
└── trending             # Popular skills

skillforge sign          # Sign a skill
skillforge verify        # Verify signature

skillforge variant
├── create               # Create variant
├── list                 # List variants
├── compare              # Compare variants
└── report               # A/B test report

skillforge import
├── gpt                  # Import OpenAI GPT
├── prompt               # Import prompt file
└── langchain            # Import from LangChain
```

### Breaking Changes

None planned - v1.1.0 is backwards compatible.

---

## v1.2.0 - Enterprise Collaboration

**Theme: "Teams at Scale"**

### Planned Features

1. **Team Workspaces**
   - Shared skill libraries
   - Role-based permissions
   - Approval workflows

2. **Skill Templates Library**
   - Organization-specific templates
   - Template inheritance
   - Compliance templates

3. **Webhooks & Notifications**
   - Slack/Teams integration
   - Event subscriptions
   - Custom webhooks

4. **Usage Quotas & Billing**
   - Per-team quotas
   - Usage reports
   - Cost allocation

---

## v1.3.0 - Developer Experience

**Theme: "Build Faster"**

### Planned Features

1. **VS Code Extension**
   - Skill authoring with IntelliSense
   - Inline validation
   - Test runner integration
   - Preview pane

2. **Skill Playground**
   - Web-based skill editor
   - Live testing
   - Share links

3. **AI-Powered Improvements**
   - Auto-fix validation errors
   - Suggest examples
   - Optimize for clarity

4. **Skill Chaining**
   - Compose skills into workflows
   - Conditional routing
   - Parallel execution

---

## v2.0.0 - Platform

**Theme: "Skill Platform"**

### Vision

Transform SkillForge from a CLI tool into a complete platform for AI capability management.

### Potential Features

1. **Skill Marketplace**
   - Public skill store
   - Monetization options
   - Reviews and ratings

2. **Hosted Skill Execution**
   - Run skills as API endpoints
   - Serverless execution
   - Auto-scaling

3. **Analytics Dashboard**
   - Web UI for usage analytics
   - ROI visualization
   - Team insights

4. **Enterprise SSO**
   - SCIM provisioning
   - Directory sync
   - Audit log export

---

## Community Wishlist

Features requested by the community (not yet scheduled):

- [ ] Skill internationalization (i18n)
- [ ] Voice/audio skill support
- [ ] Image/multimodal skills
- [ ] Skill versioning UI
- [ ] GitHub Actions for skill CI
- [ ] Skill performance benchmarks
- [ ] Custom assertion types
- [ ] Skill documentation generator

---

## Contributing to the Roadmap

We welcome input on the roadmap!

1. **Feature Requests**: Open an issue with the `enhancement` label
2. **Discussions**: Join [GitHub Discussions](https://github.com/lhassa8/skillforge/discussions)
3. **Pull Requests**: Contributions welcome for any roadmap item

## Version History

| Version | Release | Theme |
|---------|---------|-------|
| v1.0.0 | Jan 2026 | Production Release |
| v0.12.0 | Jan 2026 | Multi-Platform & Analytics |
| v0.11.0 | Jan 2026 | Security & Governance |
| v0.10.0 | Jan 2026 | MCP Integration |
| v0.9.0 | Jan 2026 | Versioning & Lock Files |
