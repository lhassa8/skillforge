"""AI-powered skill generation using Claude or other LLMs."""

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal

from skillforge.skill import Skill, normalize_skill_name


Provider = Literal["anthropic", "openai", "ollama"]

# System prompt for skill generation
SYSTEM_PROMPT = """You are an expert at creating Anthropic Agent Skills. Your task is to generate high-quality SKILL.md files that extend Claude's capabilities.

A SKILL.md file has this structure:
1. YAML frontmatter with `name` and `description`
2. Markdown content with instructions for Claude

Requirements:
- name: lowercase letters, numbers, and hyphens only (max 64 chars). Cannot contain "anthropic" or "claude"
- description: Clearly explain WHEN to use this skill (max 1024 chars). Use phrases like "Use when..."

The content should include:
- Clear, actionable instructions
- Step-by-step guidance
- Multiple examples showing request/response patterns
- Edge cases and error handling
- Any relevant context or constraints

Write instructions as if you're teaching another AI assistant exactly how to handle these requests."""

GENERATION_PROMPT = """Create a complete SKILL.md file for this skill:

{description}

{context}

Generate the complete SKILL.md content including the YAML frontmatter (between --- markers) and comprehensive markdown instructions.

The skill should be:
- Immediately useful without modification
- Have at least 3 detailed examples
- Include clear step-by-step instructions
- Handle edge cases appropriately

Return ONLY the SKILL.md content, starting with --- and ending after the markdown content."""

IMPROVE_PROMPT = """Improve this existing SKILL.md to make it more effective:

```markdown
{current_content}
```

Improvement request: {request}

Make the skill more:
- Specific and actionable
- Well-structured with clear sections
- Rich with examples
- Comprehensive in edge case handling

Return the complete improved SKILL.md content, starting with --- and ending after the markdown content."""


@dataclass
class GenerationResult:
    """Result of AI skill generation."""

    success: bool
    skill: Optional[Skill] = None
    raw_content: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


def get_available_providers() -> list[dict]:
    """Check which AI providers are available.

    Returns:
        List of available provider info dicts
    """
    providers = []

    # Check Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            providers.append({
                "name": "anthropic",
                "available": True,
                "models": ["claude-sonnet-4-20250514", "claude-opus-4-1-20250219"],
                "default_model": "claude-sonnet-4-20250514",
            })
        except ImportError:
            providers.append({
                "name": "anthropic",
                "available": False,
                "reason": "anthropic package not installed (pip install anthropic)",
            })
    else:
        providers.append({
            "name": "anthropic",
            "available": False,
            "reason": "ANTHROPIC_API_KEY not set",
        })

    # Check OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        try:
            import openai
            providers.append({
                "name": "openai",
                "available": True,
                "models": ["gpt-4o", "gpt-4-turbo"],
                "default_model": "gpt-4o",
            })
        except ImportError:
            providers.append({
                "name": "openai",
                "available": False,
                "reason": "openai package not installed (pip install openai)",
            })
    else:
        providers.append({
            "name": "openai",
            "available": False,
            "reason": "OPENAI_API_KEY not set",
        })

    # Check Ollama
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            providers.append({
                "name": "ollama",
                "available": True,
                "models": models or ["llama3.2", "codellama"],
                "default_model": models[0] if models else "llama3.2",
            })
    except Exception:
        providers.append({
            "name": "ollama",
            "available": False,
            "reason": "Ollama not running (ollama serve)",
        })

    return providers


def get_default_provider() -> Optional[tuple[str, str]]:
    """Get the first available provider and its default model.

    Returns:
        Tuple of (provider_name, model_name) or None
    """
    for provider in get_available_providers():
        if provider.get("available"):
            return (provider["name"], provider["default_model"])
    return None


def generate_skill(
    description: str,
    name: Optional[str] = None,
    context_dir: Optional[Path] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> GenerationResult:
    """Generate a skill using AI.

    Args:
        description: Natural language description of what the skill should do
        name: Optional skill name (will be generated if not provided)
        context_dir: Optional directory to analyze for context
        provider: AI provider to use (anthropic, openai, ollama)
        model: Specific model to use

    Returns:
        GenerationResult with the generated skill
    """
    # Determine provider and model
    if provider is None:
        default = get_default_provider()
        if default is None:
            return GenerationResult(
                success=False,
                error="No AI provider available. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or run Ollama.",
            )
        provider, default_model = default
        if model is None:
            model = default_model

    # Build context from directory if provided
    context = ""
    if context_dir and context_dir.exists():
        context = _build_context(context_dir)

    # Generate the prompt
    prompt = GENERATION_PROMPT.format(
        description=description,
        context=f"\nProject context:\n{context}" if context else "",
    )

    # Call the appropriate provider
    try:
        if provider == "anthropic":
            raw_content = _call_anthropic(prompt, model or "claude-sonnet-4-20250514")
        elif provider == "openai":
            raw_content = _call_openai(prompt, model or "gpt-4o")
        elif provider == "ollama":
            raw_content = _call_ollama(prompt, model or "llama3.2")
        else:
            return GenerationResult(
                success=False,
                error=f"Unknown provider: {provider}",
            )
    except Exception as e:
        return GenerationResult(
            success=False,
            error=f"API call failed: {e}",
            provider=provider,
            model=model,
        )

    # Parse the generated content
    try:
        # Extract SKILL.md content (between first --- and end)
        content = _extract_skill_content(raw_content)
        skill = Skill.from_skill_md(content)

        # Override name if provided
        if name:
            skill.name = normalize_skill_name(name)

        return GenerationResult(
            success=True,
            skill=skill,
            raw_content=content,
            provider=provider,
            model=model,
        )
    except Exception as e:
        return GenerationResult(
            success=False,
            raw_content=raw_content,
            error=f"Failed to parse generated content: {e}",
            provider=provider,
            model=model,
        )


def improve_skill(
    skill_path: Path,
    request: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> GenerationResult:
    """Improve an existing skill using AI.

    Args:
        skill_path: Path to the skill directory
        request: What to improve about the skill
        provider: AI provider to use
        model: Specific model to use

    Returns:
        GenerationResult with the improved skill
    """
    # Load existing skill
    try:
        existing = Skill.from_directory(skill_path)
        current_content = existing.to_skill_md()
    except Exception as e:
        return GenerationResult(
            success=False,
            error=f"Failed to load skill: {e}",
        )

    # Determine provider and model
    if provider is None:
        default = get_default_provider()
        if default is None:
            return GenerationResult(
                success=False,
                error="No AI provider available.",
            )
        provider, default_model = default
        if model is None:
            model = default_model

    # Build the prompt
    prompt = IMPROVE_PROMPT.format(
        current_content=current_content,
        request=request,
    )

    # Call the appropriate provider
    try:
        if provider == "anthropic":
            raw_content = _call_anthropic(prompt, model or "claude-sonnet-4-20250514")
        elif provider == "openai":
            raw_content = _call_openai(prompt, model or "gpt-4o")
        elif provider == "ollama":
            raw_content = _call_ollama(prompt, model or "llama3.2")
        else:
            return GenerationResult(
                success=False,
                error=f"Unknown provider: {provider}",
            )
    except Exception as e:
        return GenerationResult(
            success=False,
            error=f"API call failed: {e}",
            provider=provider,
            model=model,
        )

    # Parse the improved content
    try:
        content = _extract_skill_content(raw_content)
        skill = Skill.from_skill_md(content)
        skill.path = skill_path

        return GenerationResult(
            success=True,
            skill=skill,
            raw_content=content,
            provider=provider,
            model=model,
        )
    except Exception as e:
        return GenerationResult(
            success=False,
            raw_content=raw_content,
            error=f"Failed to parse improved content: {e}",
            provider=provider,
            model=model,
        )


def _build_context(context_dir: Path, max_files: int = 10, max_size: int = 5000) -> str:
    """Build context string from a directory.

    Looks at key files to understand the project.
    """
    context_parts = []

    # Key files to look for
    key_files = [
        "README.md",
        "README",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "requirements.txt",
    ]

    for filename in key_files:
        filepath = context_dir / filename
        if filepath.exists() and filepath.is_file():
            try:
                content = filepath.read_text()[:max_size]
                context_parts.append(f"=== {filename} ===\n{content}\n")
            except Exception:
                pass

    # Look at directory structure
    try:
        items = list(context_dir.iterdir())[:20]
        structure = "\n".join(
            f"{'[dir]' if item.is_dir() else '[file]'} {item.name}"
            for item in items
        )
        context_parts.append(f"=== Directory Structure ===\n{structure}\n")
    except Exception:
        pass

    return "\n".join(context_parts)[:max_size * 2]


def _extract_skill_content(raw: str) -> str:
    """Extract SKILL.md content from raw AI response."""
    # Find the first --- marker
    lines = raw.strip().split("\n")

    # Skip any text before first ---
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            start_idx = i
            break

    # Find the second --- marker (end of frontmatter)
    end_frontmatter = start_idx + 1
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip() == "---":
            end_frontmatter = i
            break

    # Return from first --- to end
    return "\n".join(lines[start_idx:])


def _call_anthropic(prompt: str, model: str) -> str:
    """Call Anthropic API.

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set
        anthropic.APIError: If the API call fails
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Run: export ANTHROPIC_API_KEY=your-key"
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    return message.content[0].text


def _call_openai(prompt: str, model: str) -> str:
    """Call OpenAI API.

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Run: export OPENAI_API_KEY=your-key"
        )

    import openai

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content


def _call_ollama(prompt: str, model: str) -> str:
    """Call Ollama API."""
    import urllib.request
    import json

    data = json.dumps({
        "model": model,
        "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        return result["response"]
