# Tutorial 4: Multi-Platform Publishing

Deploy your skills to Claude, OpenAI, and LangChain from a single source.

## Overview

SkillForge can publish skills to multiple AI platforms:

| Platform | Modes | Use Case |
|----------|-------|----------|
| **Claude** | code, api, project | Claude Code, Claude API, claude.ai |
| **OpenAI** | gpt, assistant, api | Custom GPTs, Assistants API |
| **LangChain** | hub, module, json | LangChain Hub, Python code |

## Publishing to Claude

### Claude Code (Default)

```bash
# Install directly to Claude Code
skillforge publish ./my-skill --platform claude

# Same as: skillforge install ./my-skill
```

### Claude API

```bash
# Generate API-ready system prompt
skillforge publish ./my-skill --platform claude --mode api

# Output: claude_system_prompt.txt
```

### claude.ai Project

```bash
# Generate project knowledge format
skillforge publish ./my-skill --platform claude --mode project

# Output: project_knowledge.md
```

## Publishing to OpenAI

### Custom GPT

```bash
skillforge publish ./my-skill --platform openai --mode gpt

# Output:
# gpt_config.json - GPT configuration
# gpt_instructions.txt - System instructions
# conversation_starters.json - Suggested prompts
```

Upload these to [chat.openai.com/gpts/editor](https://chat.openai.com/gpts/editor).

### Assistants API

```bash
skillforge publish ./my-skill --platform openai --mode assistant

# Output: assistant_config.json
```

Use with the OpenAI Assistants API:

```python
from openai import OpenAI
import json

client = OpenAI()

with open("assistant_config.json") as f:
    config = json.load(f)

assistant = client.beta.assistants.create(**config)
```

## Publishing to LangChain

### LangChain Hub

```bash
# Push to LangChain Hub (requires langchain-hub)
skillforge publish ./my-skill --platform langchain --mode hub

# Requires: pip install langchain-hub
# And: export LANGCHAIN_API_KEY=...
```

### Python Module

```bash
skillforge publish ./my-skill --platform langchain --mode module

# Output: my_skill_prompt.py
```

Generated module:

```python
from langchain_core.prompts import ChatPromptTemplate

my_skill_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert..."""),
    ("human", "{input}")
])

# Usage:
# chain = my_skill_prompt | llm
# result = chain.invoke({"input": "user message"})
```

### JSON Config

```bash
skillforge publish ./my-skill --platform langchain --mode json

# Output: langchain_prompt.json
```

## Dry Run Mode

Preview publishing without making changes:

```bash
skillforge publish ./my-skill --platform openai --mode gpt --dry-run

# Shows what would be generated without writing files
```

## Publish to All Platforms

```bash
skillforge publish ./my-skill --all

# Generates output for all platforms:
# - claude/
# - openai/
# - langchain/
```

## Platform-Specific Considerations

### Claude

- Supports rich markdown formatting
- Can include reference documents
- Best for complex, nuanced instructions

### OpenAI GPTs

- Conversation starters are auto-generated from examples
- Consider enabling Code Interpreter for technical skills
- 8,000 character limit for instructions

### LangChain

- Template variables use `{variable}` syntax
- Consider adding input/output parsers
- Works with any LangChain-compatible LLM

## Example Workflow

```bash
# 1. Create and test your skill
skillforge generate "Review pull requests for code quality"
skillforge test ./skills/pr-reviewer

# 2. Security scan
skillforge security scan ./skills/pr-reviewer

# 3. Preview for each platform
skillforge publish ./skills/pr-reviewer --platform claude --dry-run
skillforge publish ./skills/pr-reviewer --platform openai --mode gpt --dry-run

# 4. Publish
skillforge publish ./skills/pr-reviewer --platform claude
skillforge publish ./skills/pr-reviewer --platform openai --mode gpt
```

## Viewing Available Platforms

```bash
skillforge platforms

# Output:
# Available Platforms:
#
# claude
#   Modes: code, api, project
#   Description: Anthropic Claude integration
#
# openai
#   Modes: gpt, assistant, api
#   Description: OpenAI GPT and Assistants
#
# langchain
#   Modes: hub, module, json
#   Description: LangChain prompt templates
```

## Next Steps

- [Tutorial 5: MCP Integration](./05-mcp-integration.md)
