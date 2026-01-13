"""AI-powered skill generation for SkillForge.

This module provides natural language to skill conversion using LLMs.
Supports multiple providers: OpenAI, Anthropic, and local Ollama models.
"""

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from skillforge.linter import lint_skill


class AIGeneratorError(Exception):
    """Raised when AI generation fails."""
    pass


class ProviderNotConfiguredError(AIGeneratorError):
    """Raised when an AI provider is not properly configured."""
    pass


# =============================================================================
# Project Context Analysis
# =============================================================================

@dataclass
class ProjectContext:
    """Analyzed context of a target project."""

    project_type: Optional[str] = None  # python, node, go, rust, etc.
    framework: Optional[str] = None  # django, fastapi, react, etc.
    build_tool: Optional[str] = None  # pip, npm, cargo, make, etc.
    has_git: bool = False
    has_docker: bool = False
    has_ci: bool = False
    existing_files: list[str] = field(default_factory=list)
    config_files: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    scripts: dict[str, str] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Convert to a string suitable for LLM prompts."""
        lines = []

        if self.project_type:
            lines.append(f"Project type: {self.project_type}")
        if self.framework:
            lines.append(f"Framework: {self.framework}")
        if self.build_tool:
            lines.append(f"Build tool: {self.build_tool}")
        if self.has_git:
            lines.append("Version control: Git")
        if self.has_docker:
            lines.append("Containerization: Docker")
        if self.has_ci:
            lines.append("CI/CD: Configured")

        if self.dependencies:
            deps = self.dependencies[:10]  # Limit to avoid huge prompts
            lines.append(f"Key dependencies: {', '.join(deps)}")

        if self.scripts:
            scripts_str = ", ".join(f"{k}" for k in list(self.scripts.keys())[:5])
            lines.append(f"Available scripts: {scripts_str}")

        if self.existing_files:
            files = self.existing_files[:15]
            lines.append(f"Key files: {', '.join(files)}")

        return "\n".join(lines) if lines else "No project context detected"


def analyze_project(target_dir: Path) -> ProjectContext:
    """Analyze a project directory to understand its structure.

    Args:
        target_dir: Path to the project directory

    Returns:
        ProjectContext with detected information
    """
    ctx = ProjectContext()

    if not target_dir.exists():
        return ctx

    # Collect key files (limited depth)
    key_files = []
    for item in target_dir.iterdir():
        if item.name.startswith(".") and item.name not in [".github", ".gitlab-ci.yml"]:
            continue
        if item.is_file():
            key_files.append(item.name)
        elif item.is_dir() and item.name not in ["node_modules", "__pycache__", ".git", "venv", ".venv"]:
            key_files.append(f"{item.name}/")
    ctx.existing_files = sorted(key_files)[:20]

    # Detect Git
    ctx.has_git = (target_dir / ".git").is_dir()

    # Detect Docker
    ctx.has_docker = (target_dir / "Dockerfile").exists() or (target_dir / "docker-compose.yml").exists()

    # Detect CI
    ctx.has_ci = (
        (target_dir / ".github" / "workflows").is_dir() or
        (target_dir / ".gitlab-ci.yml").exists() or
        (target_dir / "Jenkinsfile").exists()
    )

    # Detect Python project
    if (target_dir / "pyproject.toml").exists():
        ctx.project_type = "python"
        ctx.build_tool = "pip/pyproject"
        _analyze_pyproject(target_dir / "pyproject.toml", ctx)
    elif (target_dir / "setup.py").exists():
        ctx.project_type = "python"
        ctx.build_tool = "pip/setup.py"
    elif (target_dir / "requirements.txt").exists():
        ctx.project_type = "python"
        ctx.build_tool = "pip"
        _analyze_requirements(target_dir / "requirements.txt", ctx)

    # Detect Node.js project
    elif (target_dir / "package.json").exists():
        ctx.project_type = "node"
        ctx.build_tool = "npm"
        _analyze_package_json(target_dir / "package.json", ctx)

    # Detect Go project
    elif (target_dir / "go.mod").exists():
        ctx.project_type = "go"
        ctx.build_tool = "go"

    # Detect Rust project
    elif (target_dir / "Cargo.toml").exists():
        ctx.project_type = "rust"
        ctx.build_tool = "cargo"

    # Detect framework from files/deps
    _detect_framework(target_dir, ctx)

    return ctx


def _analyze_pyproject(path: Path, ctx: ProjectContext) -> None:
    """Analyze pyproject.toml for dependencies and scripts."""
    try:
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Get dependencies
        deps = data.get("project", {}).get("dependencies", [])
        if deps:
            ctx.dependencies = [d.split("[")[0].split(">=")[0].split("==")[0].strip() for d in deps[:15]]

        # Get scripts
        scripts = data.get("project", {}).get("scripts", {})
        ctx.scripts = dict(list(scripts.items())[:5])

    except Exception:
        pass


def _analyze_requirements(path: Path, ctx: ProjectContext) -> None:
    """Analyze requirements.txt for dependencies."""
    try:
        content = path.read_text()
        deps = []
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Extract package name
                pkg = re.split(r"[>=<\[!]", line)[0].strip()
                if pkg:
                    deps.append(pkg)
        ctx.dependencies = deps[:15]
    except Exception:
        pass


def _analyze_package_json(path: Path, ctx: ProjectContext) -> None:
    """Analyze package.json for dependencies and scripts."""
    try:
        data = json.loads(path.read_text())

        # Get dependencies
        deps = list(data.get("dependencies", {}).keys())
        deps.extend(data.get("devDependencies", {}).keys())
        ctx.dependencies = deps[:15]

        # Get scripts
        ctx.scripts = dict(list(data.get("scripts", {}).items())[:5])

    except Exception:
        pass


def _detect_framework(target_dir: Path, ctx: ProjectContext) -> None:
    """Detect framework from project structure and dependencies."""
    deps_lower = [d.lower() for d in ctx.dependencies]

    # Python frameworks
    if ctx.project_type == "python":
        if "django" in deps_lower:
            ctx.framework = "django"
        elif "fastapi" in deps_lower:
            ctx.framework = "fastapi"
        elif "flask" in deps_lower:
            ctx.framework = "flask"
        elif "pytest" in deps_lower:
            ctx.framework = "pytest"

    # Node frameworks
    elif ctx.project_type == "node":
        if "react" in deps_lower:
            ctx.framework = "react"
        elif "vue" in deps_lower:
            ctx.framework = "vue"
        elif "next" in deps_lower:
            ctx.framework = "next.js"
        elif "express" in deps_lower:
            ctx.framework = "express"


# =============================================================================
# LLM Provider Abstraction
# =============================================================================

@dataclass
class GenerationResult:
    """Result of AI skill generation."""

    success: bool
    skill_yaml: Optional[str] = None
    skill_dir: Optional[Path] = None
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    tokens_used: int = 0
    model: str = ""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> tuple[str, int]:
        """Generate a response from the LLM.

        Args:
            prompt: User prompt
            system_prompt: System prompt with instructions

        Returns:
            Tuple of (response_text, tokens_used)

        Raises:
            AIGeneratorError: If generation fails
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model

        if not self._api_key:
            raise ProviderNotConfiguredError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str) -> tuple[str, int]:
        try:
            import anthropic
        except ImportError:
            raise AIGeneratorError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        client = anthropic.Anthropic(api_key=self._api_key)

        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return text, tokens

        except Exception as e:
            raise AIGeneratorError(f"Anthropic API error: {e}")


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._model = model

        if not self._api_key:
            raise ProviderNotConfiguredError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str) -> tuple[str, int]:
        try:
            import openai
        except ImportError:
            raise AIGeneratorError(
                "openai package not installed. Run: pip install openai"
            )

        client = openai.OpenAI(api_key=self._api_key)

        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
            )

            text = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            return text, tokens

        except Exception as e:
            raise AIGeneratorError(f"OpenAI API error: {e}")


class OllamaProvider(LLMProvider):
    """Ollama local model provider."""

    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434"):
        self._model = model
        self._host = host

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str) -> tuple[str, int]:
        try:
            import httpx
        except ImportError:
            raise AIGeneratorError(
                "httpx package not installed. Run: pip install httpx"
            )

        try:
            response = httpx.post(
                f"{self._host}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            text = data.get("response", "")
            # Ollama doesn't always return token counts
            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
            return text, tokens

        except Exception as e:
            raise AIGeneratorError(f"Ollama API error: {e}")


def get_provider(
    provider_name: str = "anthropic",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Get an LLM provider instance.

    Args:
        provider_name: One of "anthropic", "openai", "ollama"
        api_key: Optional API key (falls back to environment variable)
        model: Optional model override

    Returns:
        LLMProvider instance

    Raises:
        ProviderNotConfiguredError: If provider cannot be configured
    """
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model or "claude-sonnet-4-20250514")
    elif provider_name == "openai":
        return OpenAIProvider(api_key=api_key, model=model or "gpt-4o")
    elif provider_name == "ollama":
        return OllamaProvider(model=model or "llama3.2")
    else:
        raise ProviderNotConfiguredError(f"Unknown provider: {provider_name}")


# =============================================================================
# Prompt Engineering
# =============================================================================

SYSTEM_PROMPT = """You are SkillForge AI, an expert at creating deterministic automation skills.

A Skill is a reproducible, automated task defined in YAML that can:
- Execute shell commands
- Create files from templates
- Modify existing files
- Validate results with checks

SKILL YAML STRUCTURE:
```yaml
name: skill_name
version: "0.1.0"
description: "What this skill does"

inputs:
  - name: input_name
    type: string|int|bool|path|enum
    description: "What this input is for"
    required: true|false
    default: "optional default value"

preconditions:
  - "Human-readable precondition"

steps:
  - id: step1
    type: shell|file.template|file.replace|python
    name: "Human-readable step name"
    command: "shell command with {placeholders}"  # for shell type
    path: "{sandbox_dir}/path/to/file"  # for file types
    template: "file content with {placeholders}"  # for file.template

checks:
  - id: check1
    type: file_exists|file_contains|exit_code|stdout_contains|git_clean
    path: "{sandbox_dir}/path"  # for file checks
    contains: "text to find"  # for file_contains
```

PLACEHOLDERS:
- {sandbox_dir} - The isolated execution directory (use for file paths)
- {target_dir} - Original target directory path (rarely needed)
- {input_name} - Any input value by name

STEP TYPES:
1. shell - Execute commands: command, cwd, env, timeout_sec
2. file.template - Create files: path, template (inline content)
3. file.replace - Modify files: path, pattern (regex), replace_with
4. python - Run Python: module, function, args

CHECK TYPES:
1. file_exists - Verify file exists: path
2. file_contains - Verify content: path, contains (or regex)
3. exit_code - Verify step exit: step_id, equals
4. stdout_contains - Verify output: step_id, contains (or regex)
5. git_clean - Verify no uncommitted changes

RULES:
1. Always use {sandbox_dir} prefix for file paths in steps and checks
2. Use meaningful step IDs (create_config, run_tests, etc.)
3. Include appropriate checks to verify the skill worked
4. Make skills idempotent when possible
5. Use inputs for any values that might vary
6. Output ONLY valid YAML between ```yaml and ``` markers
7. Do not use non-deterministic commands (date, random, uuid) without good reason
8. Prefer file.template for creating new files, shell for commands
"""


def build_generation_prompt(
    description: str,
    context: Optional[ProjectContext] = None,
    additional_requirements: Optional[str] = None,
) -> str:
    """Build a prompt for skill generation.

    Args:
        description: Natural language description of desired skill
        context: Optional project context for better generation
        additional_requirements: Optional additional requirements

    Returns:
        Formatted prompt string
    """
    parts = [f"Create a SkillForge skill that: {description}"]

    if context and context.project_type:
        parts.append(f"\nProject context:\n{context.to_prompt_context()}")

    if additional_requirements:
        parts.append(f"\nAdditional requirements:\n{additional_requirements}")

    parts.append("""
Generate a complete skill.yaml. Output ONLY the YAML content between ```yaml and ``` markers.
Include:
1. Appropriate inputs for any variable values
2. Clear step names and IDs
3. Checks to verify success
""")

    return "\n".join(parts)


def build_refinement_prompt(
    skill_yaml: str,
    feedback: str,
    lint_errors: Optional[list[str]] = None,
) -> str:
    """Build a prompt for skill refinement.

    Args:
        skill_yaml: Current skill YAML content
        feedback: User feedback for refinement
        lint_errors: Optional lint errors to fix

    Returns:
        Formatted prompt string
    """
    parts = [
        "Refine this SkillForge skill based on feedback.",
        f"\nCurrent skill:\n```yaml\n{skill_yaml}\n```",
        f"\nFeedback: {feedback}",
    ]

    if lint_errors:
        parts.append(f"\nLint errors to fix:\n" + "\n".join(f"- {e}" for e in lint_errors))

    parts.append("\nOutput the improved YAML between ```yaml and ``` markers.")

    return "\n".join(parts)


def build_explanation_prompt(skill_yaml: str) -> str:
    """Build a prompt to explain a skill.

    Args:
        skill_yaml: Skill YAML content

    Returns:
        Formatted prompt string
    """
    return f"""Explain what this SkillForge skill does in plain English.
Include:
1. Overall purpose
2. What inputs it expects
3. What each step does
4. What it verifies/checks

Skill:
```yaml
{skill_yaml}
```

Provide a clear, concise explanation suitable for documentation."""


# =============================================================================
# Skill Generation
# =============================================================================

def extract_yaml_from_response(response: str) -> str:
    """Extract YAML content from LLM response.

    Args:
        response: Raw LLM response

    Returns:
        Extracted YAML string

    Raises:
        AIGeneratorError: If no YAML block found
    """
    # Look for ```yaml ... ``` blocks
    yaml_pattern = r"```(?:yaml|yml)?\s*\n(.*?)```"
    matches = re.findall(yaml_pattern, response, re.DOTALL)

    if matches:
        return matches[0].strip()

    # Try to find YAML-like content (starts with name:)
    if "name:" in response:
        # Find the start of YAML
        start = response.find("name:")
        # Try to find where it ends (next prose or end)
        lines = response[start:].split("\n")
        yaml_lines = []
        for line in lines:
            # Stop at blank line followed by prose
            if not line.strip() and yaml_lines and not yaml_lines[-1].strip().endswith(":"):
                break
            yaml_lines.append(line)
        return "\n".join(yaml_lines).strip()

    raise AIGeneratorError("No valid YAML found in response")


def validate_generated_yaml(yaml_content: str) -> tuple[bool, list[str]]:
    """Validate generated YAML content.

    Args:
        yaml_content: YAML string to validate

    Returns:
        Tuple of (is_valid, list of errors/warnings)
    """
    errors = []

    # Try to parse YAML
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return False, [f"Invalid YAML syntax: {e}"]

    if not isinstance(data, dict):
        return False, ["YAML must be a dictionary"]

    # Check required fields
    if "name" not in data:
        errors.append("Missing required field: name")

    if "steps" not in data or not data["steps"]:
        errors.append("Skill must have at least one step")

    # Validate steps
    if "steps" in data:
        for i, step in enumerate(data["steps"]):
            if not isinstance(step, dict):
                errors.append(f"Step {i+1} must be a dictionary")
                continue
            if "id" not in step:
                errors.append(f"Step {i+1} missing 'id' field")
            if "type" not in step:
                errors.append(f"Step {i+1} missing 'type' field")

    # Validate checks
    if "checks" in data:
        for i, check in enumerate(data["checks"]):
            if not isinstance(check, dict):
                errors.append(f"Check {i+1} must be a dictionary")
                continue
            if "id" not in check:
                errors.append(f"Check {i+1} missing 'id' field")
            if "type" not in check:
                errors.append(f"Check {i+1} missing 'type' field")

    return len(errors) == 0, errors


def generate_skill(
    description: str,
    output_dir: Path,
    provider: Optional[LLMProvider] = None,
    target_dir: Optional[Path] = None,
    additional_requirements: Optional[str] = None,
    auto_fix: bool = True,
    max_retries: int = 2,
) -> GenerationResult:
    """Generate a skill from natural language description.

    Args:
        description: Natural language description of desired skill
        output_dir: Directory to create skill in
        provider: LLM provider to use (defaults to Anthropic)
        target_dir: Optional target directory to analyze for context
        additional_requirements: Optional additional requirements
        auto_fix: Whether to automatically fix validation errors
        max_retries: Maximum retries for fixing errors

    Returns:
        GenerationResult with success status and paths
    """
    # Get provider
    if provider is None:
        try:
            provider = get_provider("anthropic")
        except ProviderNotConfiguredError:
            try:
                provider = get_provider("openai")
            except ProviderNotConfiguredError:
                try:
                    provider = get_provider("ollama")
                except Exception:
                    raise ProviderNotConfiguredError(
                        "No AI provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
                        "or ensure Ollama is running locally."
                    )

    # Analyze project context
    context = None
    if target_dir and target_dir.exists():
        context = analyze_project(target_dir)

    # Build and send prompt
    prompt = build_generation_prompt(description, context, additional_requirements)

    total_tokens = 0
    last_error = None
    yaml_content = None
    errors: list[str] = []

    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                response, tokens = provider.generate(prompt, SYSTEM_PROMPT)
            else:
                # Refinement attempt with error feedback
                refine_prompt = build_refinement_prompt(
                    yaml_content or "",
                    f"Fix these errors: {', '.join(errors)}" if errors else "Please fix the skill",
                    errors if errors else None,
                )
                response, tokens = provider.generate(refine_prompt, SYSTEM_PROMPT)

            total_tokens += tokens

            # Extract YAML
            yaml_content = extract_yaml_from_response(response)

            # Validate
            is_valid, errors = validate_generated_yaml(yaml_content)

            if is_valid or not auto_fix:
                break

            last_error = errors[0] if errors else "Unknown validation error"

        except AIGeneratorError as e:
            last_error = str(e)
            if not auto_fix or attempt >= max_retries:
                return GenerationResult(
                    success=False,
                    error=str(e),
                    tokens_used=total_tokens,
                    model=provider.model,
                )

    if yaml_content is None:
        return GenerationResult(
            success=False,
            error=last_error or "Failed to generate skill",
            tokens_used=total_tokens,
            model=provider.model,
        )

    # Final validation
    is_valid, errors = validate_generated_yaml(yaml_content)

    if not is_valid:
        return GenerationResult(
            success=False,
            skill_yaml=yaml_content,
            error=f"Generated skill has errors: {', '.join(errors)}",
            warnings=errors,
            tokens_used=total_tokens,
            model=provider.model,
        )

    # Parse and create skill directory
    try:
        data = yaml.safe_load(yaml_content)
        skill_name = data.get("name", "generated_skill")

        # Normalize skill name for directory
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in skill_name)
        safe_name = safe_name.strip("_").lower()

        skill_dir = output_dir / safe_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (skill_dir / "fixtures" / "happy_path" / "input").mkdir(parents=True, exist_ok=True)
        (skill_dir / "fixtures" / "happy_path" / "expected").mkdir(parents=True, exist_ok=True)
        (skill_dir / "reports").mkdir(parents=True, exist_ok=True)
        (skill_dir / "cassettes").mkdir(parents=True, exist_ok=True)

        # Write skill.yaml
        skill_yaml_path = skill_dir / "skill.yaml"
        skill_yaml_path.write_text(yaml_content)

        # Generate SKILL.txt
        skill_txt = _generate_skill_txt_from_yaml(data)
        (skill_dir / "SKILL.txt").write_text(skill_txt)

        # Generate checks.py
        checks_py = _generate_checks_py(skill_name)
        (skill_dir / "checks.py").write_text(checks_py)

        # Generate fixture.yaml
        fixture_yaml = """# Fixture configuration
# Override skill inputs for this fixture

# inputs:
#   input_name: "value"

# allow_extra_files: false
"""
        (skill_dir / "fixtures" / "happy_path" / "fixture.yaml").write_text(fixture_yaml)

        # Create .gitkeep files
        for gitkeep_dir in [
            skill_dir / "fixtures" / "happy_path" / "input",
            skill_dir / "fixtures" / "happy_path" / "expected",
            skill_dir / "reports",
            skill_dir / "cassettes",
        ]:
            (gitkeep_dir / ".gitkeep").write_text("")

        # Run linter to get warnings
        warnings = []
        try:
            lint_results = lint_skill(skill_dir)
            warnings = [r.message for r in lint_results if r.severity == "warning"]
        except Exception:
            pass

        return GenerationResult(
            success=True,
            skill_yaml=yaml_content,
            skill_dir=skill_dir,
            warnings=warnings,
            tokens_used=total_tokens,
            model=provider.model,
        )

    except Exception as e:
        return GenerationResult(
            success=False,
            skill_yaml=yaml_content,
            error=f"Failed to create skill directory: {e}",
            tokens_used=total_tokens,
            model=provider.model,
        )


def refine_skill(
    skill_dir: Path,
    feedback: str,
    provider: Optional[LLMProvider] = None,
) -> GenerationResult:
    """Refine an existing skill based on feedback.

    Args:
        skill_dir: Path to existing skill directory
        feedback: User feedback for refinement
        provider: LLM provider to use

    Returns:
        GenerationResult with refined skill
    """
    skill_yaml_path = skill_dir / "skill.yaml"

    if not skill_yaml_path.exists():
        return GenerationResult(
            success=False,
            error=f"No skill.yaml found in {skill_dir}",
        )

    current_yaml = skill_yaml_path.read_text()

    # Get lint errors
    lint_errors = []
    try:
        lint_results = lint_skill(skill_dir)
        lint_errors = [r.message for r in lint_results if r.severity == "error"]
    except Exception:
        pass

    # Get provider
    if provider is None:
        provider = get_provider("anthropic")

    # Build and send prompt
    prompt = build_refinement_prompt(current_yaml, feedback, lint_errors)

    try:
        response, tokens = provider.generate(prompt, SYSTEM_PROMPT)
        yaml_content = extract_yaml_from_response(response)

        # Validate
        is_valid, errors = validate_generated_yaml(yaml_content)

        if not is_valid:
            return GenerationResult(
                success=False,
                skill_yaml=yaml_content,
                error=f"Refined skill has errors: {', '.join(errors)}",
                warnings=errors,
                tokens_used=tokens,
                model=provider.model,
            )

        # Update skill.yaml
        skill_yaml_path.write_text(yaml_content)

        # Update SKILL.txt
        data = yaml.safe_load(yaml_content)
        skill_txt = _generate_skill_txt_from_yaml(data)
        (skill_dir / "SKILL.txt").write_text(skill_txt)

        return GenerationResult(
            success=True,
            skill_yaml=yaml_content,
            skill_dir=skill_dir,
            tokens_used=tokens,
            model=provider.model,
        )

    except AIGeneratorError as e:
        return GenerationResult(
            success=False,
            error=str(e),
        )


def explain_skill(
    skill_dir: Path,
    provider: Optional[LLMProvider] = None,
) -> tuple[str, int]:
    """Generate a plain-English explanation of a skill.

    Args:
        skill_dir: Path to skill directory
        provider: LLM provider to use

    Returns:
        Tuple of (explanation, tokens_used)
    """
    skill_yaml_path = skill_dir / "skill.yaml"

    if not skill_yaml_path.exists():
        raise AIGeneratorError(f"No skill.yaml found in {skill_dir}")

    yaml_content = skill_yaml_path.read_text()

    if provider is None:
        provider = get_provider("anthropic")

    prompt = build_explanation_prompt(yaml_content)

    response, tokens = provider.generate(prompt, SYSTEM_PROMPT)
    return response.strip(), tokens


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_skill_txt_from_yaml(data: dict[str, Any]) -> str:
    """Generate SKILL.txt content from parsed YAML data."""
    name = data.get("name", "unnamed_skill")
    description = data.get("description", "")

    lines = [
        f"SKILL: {name}",
        "=" * (7 + len(name)),
        "",
        "DESCRIPTION",
        "-----------",
        description or "AI-generated skill",
        "",
    ]

    # Preconditions
    preconditions = data.get("preconditions", [])
    if preconditions:
        lines.extend([
            "PRECONDITIONS",
            "-------------",
        ])
        for pre in preconditions:
            lines.append(f"- {pre}")
        lines.append("")

    # Inputs
    inputs = data.get("inputs", [])
    if inputs:
        lines.extend([
            "INPUTS",
            "------",
        ])
        for inp in inputs:
            name = inp.get("name", "unnamed")
            typ = inp.get("type", "string")
            req = "required" if inp.get("required", True) else "optional"
            default = inp.get("default")
            desc = inp.get("description", "")

            default_str = f", default: {default}" if default else ""
            desc_str = f" - {desc}" if desc else ""
            lines.append(f"- {name}: {typ} ({req}{default_str}){desc_str}")
        lines.append("")

    # Steps
    steps = data.get("steps", [])
    if steps:
        lines.extend([
            "STEPS",
            "-----",
        ])
        for i, step in enumerate(steps, 1):
            step_name = step.get("name", step.get("id", f"Step {i}"))
            lines.append(f"{i}. {step_name}")

            step_type = step.get("type", "shell")
            if step_type == "shell":
                cmd = step.get("command", "")
                if cmd:
                    lines.append(f"   - Run: {cmd}")
            elif step_type == "file.template":
                path = step.get("path", "")
                lines.append(f"   - Create file: {path}")
            elif step_type == "file.replace":
                path = step.get("path", "")
                lines.append(f"   - Modify file: {path}")
        lines.append("")

    # Checks
    checks = data.get("checks", [])
    if checks:
        lines.extend([
            "CHECKS",
            "------",
        ])
        for check in checks:
            check_type = check.get("type", "")
            if check_type == "file_exists":
                lines.append(f"- File exists: {check.get('path', '')}")
            elif check_type == "file_contains":
                lines.append(f"- File {check.get('path', '')} contains: {check.get('contains', check.get('regex', ''))}")
            elif check_type == "exit_code":
                lines.append(f"- Step {check.get('step_id', '')} exits with code {check.get('equals', 0)}")
            elif check_type == "stdout_contains":
                lines.append(f"- Step {check.get('step_id', '')} output contains: {check.get('contains', check.get('regex', ''))}")
            elif check_type == "git_clean":
                lines.append("- Git working directory is clean")
        lines.append("")

    return "\n".join(lines)


def _generate_checks_py(skill_name: str) -> str:
    """Generate checks.py content."""
    return f'''"""Custom checks for the {skill_name} skill."""

from pathlib import Path
from typing import Any


def custom_check(context: dict[str, Any]) -> tuple[bool, str]:
    """Example custom check function.

    Args:
        context: Dictionary containing:
            - target_dir: Path to the target directory
            - sandbox_dir: Path to the sandbox directory
            - inputs: Resolved input values
            - step_results: Results from executed steps

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Placeholder - always passes
    return True, "Custom check passed"


# Add more custom check functions as needed
'''
