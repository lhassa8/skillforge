"""SkillForge CLI - Create and manage Anthropic Agent Skills."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import typer

if TYPE_CHECKING:
    from skillforge.tester import TestSuiteResult
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

app = typer.Typer(
    name="skillforge",
    help="Create, validate, and bundle Anthropic Agent Skills.",
    no_args_is_help=True,
)
console = Console()


# Default skills directory
DEFAULT_SKILLS_DIR = Path("./skills")


@app.command()
def new(
    name: str = typer.Argument(..., help="Name for the skill"),
    description: str = typer.Option(
        "",
        "--description",
        "-d",
        help="Description of what the skill does and when to use it",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-T",
        help="Template to use (run 'skillforge templates' to see available)",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_SKILLS_DIR,
        "--out",
        "-o",
        help="Output directory for the skill",
    ),
    with_scripts: bool = typer.Option(
        False,
        "--with-scripts",
        "-s",
        help="Include a scripts/ directory with example",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing skill",
    ),
) -> None:
    """Create a new Anthropic Agent Skill.

    Creates a SKILL.md file with proper YAML frontmatter and a template
    for instructions that Claude will follow.

    Example:

    \b
        skillforge new pdf-processor -d "Extract text and data from PDF files"
        skillforge new code-reviewer --with-scripts
        skillforge new my-reviewer --template code-review
    """
    from skillforge.scaffold import create_skill_scaffold
    from skillforge.skill import normalize_skill_name

    # Show normalized name if different
    normalized = normalize_skill_name(name)
    if normalized != name:
        console.print(f"[dim]Normalizing name: {name} → {normalized}[/dim]")

    try:
        skill_dir, used_template = create_skill_scaffold(
            name=name,
            output_dir=output_dir,
            description=description,
            template=template,
            with_scripts=with_scripts,
            force=force,
        )

        console.print()
        console.print(f"[green]✓ Created skill:[/green] {skill_dir}")

        if used_template:
            console.print(f"[dim]Template: {used_template.name} ({used_template.category})[/dim]")

        console.print()

        # Show created files
        console.print("[bold]Created files:[/bold]")
        for item in sorted(skill_dir.rglob("*")):
            if item.is_file():
                rel_path = item.relative_to(skill_dir)
                console.print(f"  {rel_path}")

        console.print()
        console.print("[bold]Next steps:[/bold]")
        if used_template:
            console.print(f"  1. Customize [cyan]{skill_dir}/SKILL.md[/cyan] for your needs")
        else:
            console.print(f"  1. Edit [cyan]{skill_dir}/SKILL.md[/cyan] with your instructions")
        console.print(f"  2. Validate with: [cyan]skillforge validate {skill_dir}[/cyan]")
        console.print(f"  3. Bundle with: [cyan]skillforge bundle {skill_dir}[/cyan]")

    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Use --force to overwrite[/dim]")
        raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def validate(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Treat warnings as errors",
    ),
) -> None:
    """Validate an Anthropic Agent Skill.

    Checks that the skill has valid YAML frontmatter, meets Anthropic's
    requirements for name and description, and follows best practices.
    For composite skills, also validates that all includes exist.

    Example:

    \b
        skillforge validate ./skills/my-skill
        skillforge validate ./skills/my-skill --strict
    """
    from skillforge.validator import validate_skill_directory
    from skillforge.composer import validate_composition, has_includes

    skill_path = Path(skill_path)
    result = validate_skill_directory(skill_path)

    console.print()

    if result.skill:
        console.print(f"[bold]Skill:[/bold] {result.skill.name}")
        console.print(f"[bold]Description:[/bold] {result.skill.description[:60]}...")
        if result.skill.includes:
            console.print(f"[bold]Includes:[/bold] {len(result.skill.includes)} skill(s)")
        console.print()

    # Validate composition if skill has includes
    composition_errors: list[str] = []
    if has_includes(skill_path):
        composition_errors = validate_composition(skill_path)

    # Combine all errors
    all_errors = result.errors + composition_errors

    # Show errors
    if all_errors:
        console.print("[red bold]Errors:[/red bold]")
        for msg in all_errors:
            console.print(f"  [red]✗[/red] {msg}")
        console.print()

    # Show warnings
    if result.warnings:
        console.print("[yellow bold]Warnings:[/yellow bold]")
        for msg in result.warnings:
            console.print(f"  [yellow]![/yellow] {msg}")
        console.print()

    # Summary
    is_valid = result.valid and not composition_errors
    if is_valid and not (strict and result.warnings):
        console.print("[green]✓ Skill is valid[/green]")
    else:
        if strict and result.warnings:
            console.print("[red]✗ Validation failed (warnings in strict mode)[/red]")
        else:
            console.print("[red]✗ Validation failed[/red]")
        raise typer.Exit(code=1)


@app.command()
def bundle(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for the zip file",
    ),
    no_validate: bool = typer.Option(
        False,
        "--no-validate",
        help="Skip validation before bundling",
    ),
) -> None:
    """Bundle a skill into a zip file for upload.

    Creates a zip file that can be uploaded to claude.ai or via the API.
    For composite skills with includes, automatically composes before bundling.

    Example:

    \b
        skillforge bundle ./skills/my-skill
        skillforge bundle ./skills/my-skill -o my-skill.zip
    """
    import tempfile
    from skillforge.bundler import bundle_skill
    from skillforge.composer import compose_skill, has_includes

    skill_path = Path(skill_path)

    console.print(f"[dim]Bundling skill: {skill_path}[/dim]")

    # Check if skill has includes - if so, compose first
    bundle_path = skill_path
    temp_dir = None

    if has_includes(skill_path):
        console.print("[dim]Composing skill (resolving includes)...[/dim]")
        result = compose_skill(skill_path)

        if not result.success:
            console.print(f"[red]Error composing skill:[/red] {result.error}")
            raise typer.Exit(code=1)

        console.print(f"[dim]Included: {', '.join(result.included_skills)}[/dim]")

        # Write composed skill to temp directory
        temp_dir = tempfile.mkdtemp()
        bundle_path = Path(temp_dir)
        (bundle_path / "SKILL.md").write_text(result.composed_content)

    try:
        result = bundle_skill(
            skill_dir=bundle_path,
            output_path=output,
            validate=not no_validate,
        )

        if not result.success:
            console.print(f"[red]Error:[/red] {result.error_message}")

            if result.validation and result.validation.errors:
                console.print()
                console.print("[red]Validation errors:[/red]")
                for msg in result.validation.errors:
                    console.print(f"  [red]✗[/red] {msg}")

            raise typer.Exit(code=1)

        console.print()
        console.print(f"[green]✓ Bundle created:[/green] {result.output_path}")
        console.print(f"  Files: {result.file_count}")
        console.print(f"  Size: {result.total_size:,} bytes")
        console.print()
        console.print("[bold]Upload to:[/bold]")
        console.print("  • claude.ai: Settings → Features → Upload Skill")
        console.print("  • API: POST /v1/skills with the zip file")

    finally:
        # Cleanup temp directory
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.command()
def show(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
) -> None:
    """Show details of a skill.

    Displays the skill's metadata, structure, and a preview of the content.

    Example:

    \b
        skillforge show ./skills/my-skill
    """
    from skillforge.skill import Skill, SkillParseError

    skill_path = Path(skill_path)

    try:
        skill = Skill.from_directory(skill_path)
    except SkillParseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    # Show skill info
    console.print()
    console.print(Panel(
        f"[bold]{skill.name}[/bold]\n\n{skill.description}",
        title="Skill",
        border_style="blue",
    ))

    # Show structure
    console.print()
    console.print("[bold]Files:[/bold]")
    console.print("  SKILL.md")
    for f in skill.additional_files:
        console.print(f"  {f}")
    if skill.scripts:
        console.print("  scripts/")
        for s in skill.scripts:
            console.print(f"    {s}")

    # Show content preview
    console.print()
    console.print("[bold]Content preview:[/bold]")
    preview = skill.content[:500]
    if len(skill.content) > 500:
        preview += "..."
    console.print(Panel(preview, border_style="dim"))


@app.command()
def doctor() -> None:
    """Check your environment for skill development.

    Verifies that required tools are available and properly configured.
    """
    import shutil
    import sys

    console.print()
    console.print("[bold]SkillForge Environment Check[/bold]")
    console.print()

    checks = []

    # Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    checks.append(("Python >= 3.10", py_ok, py_version))

    # Required packages
    packages = [
        ("typer", "typer"),
        ("rich", "rich"),
        ("pyyaml", "yaml"),
    ]

    for name, import_name in packages:
        try:
            __import__(import_name)
            checks.append((f"Package: {name}", True, "installed"))
        except ImportError:
            checks.append((f"Package: {name}", False, "not installed"))

    # Optional tools
    optional_tools = [
        ("git", "Version control"),
        ("zip", "Creating bundles"),
    ]

    for tool, desc in optional_tools:
        if shutil.which(tool):
            checks.append((f"Tool: {tool}", True, desc))
        else:
            checks.append((f"Tool: {tool}", False, f"not found ({desc})"))

    # Display results
    table = Table(show_header=False, box=None)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Info", style="dim")

    all_ok = True
    for name, ok, info in checks:
        if ok is True:
            status = "[green]✓[/green]"
        elif ok is False:
            status = "[red]✗[/red]"
            all_ok = False
        else:
            status = "[yellow]?[/yellow]"

        table.add_row(name, status, info)

    console.print(table)
    console.print()

    if all_ok:
        console.print("[green]All checks passed![/green]")
    else:
        console.print("[yellow]Some checks failed. Install missing dependencies.[/yellow]")


@app.command()
def init(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to initialize",
    ),
) -> None:
    """Initialize a directory for skill development.

    Creates a skills/ subdirectory and a sample skill to get started.

    Example:

    \b
        skillforge init
        skillforge init ./my-project
    """
    from skillforge.scaffold import create_skill_scaffold

    skills_dir = directory / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]✓[/green] Created skills directory: {skills_dir}")

    # Create a sample skill
    try:
        sample_skill = create_skill_scaffold(
            name="example-skill",
            output_dir=skills_dir,
            description="An example skill to help you get started. Use when the user asks for help with examples.",
            with_scripts=True,
        )
        console.print(f"[green]✓[/green] Created sample skill: {sample_skill}")
    except FileExistsError:
        console.print("[dim]Sample skill already exists[/dim]")

    console.print()
    console.print("[bold]Getting started:[/bold]")
    console.print(f"  1. Explore the sample: [cyan]skillforge show {skills_dir}/example-skill[/cyan]")
    console.print("  2. Create a new skill: [cyan]skillforge new my-skill[/cyan]")
    console.print("  3. Read the docs: [cyan]https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills[/cyan]")


@app.command("list")
def list_skills(
    directory: Path = typer.Argument(
        DEFAULT_SKILLS_DIR,
        help="Directory containing skills",
    ),
) -> None:
    """List all skills in a directory.

    Example:

    \b
        skillforge list
        skillforge list ./my-skills
    """
    from skillforge.skill import Skill, SkillParseError

    if not directory.exists():
        console.print(f"[yellow]Directory not found:[/yellow] {directory}")
        console.print("[dim]Run 'skillforge init' to create it[/dim]")
        return

    skills = []
    for item in directory.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            try:
                skill = Skill.from_directory(item)
                skills.append((item.name, skill.name, skill.description[:50]))
            except SkillParseError:
                skills.append((item.name, "?", "[red]Invalid SKILL.md[/red]"))

    if not skills:
        console.print("[yellow]No skills found[/yellow]")
        console.print("[dim]Run 'skillforge new <name>' to create one[/dim]")
        return

    console.print()
    table = Table(title="Skills", show_header=True, header_style="bold")
    table.add_column("Directory")
    table.add_column("Name")
    table.add_column("Description")

    for dir_name, name, desc in skills:
        table.add_row(dir_name, name, desc + "..." if len(desc) == 50 else desc)

    console.print(table)
    console.print()
    console.print(f"[dim]Found {len(skills)} skill(s) in {directory}[/dim]")


@app.command()
def add(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
    item_type: str = typer.Argument(..., help="Type of item to add: 'doc' or 'script'"),
    name: str = typer.Argument(..., help="Name for the new file"),
    language: str = typer.Option(
        "python",
        "--language",
        "-l",
        help="Script language (python, bash, node)",
    ),
) -> None:
    """Add a reference document or script to a skill.

    Example:

    \b
        skillforge add ./skills/my-skill doc REFERENCE
        skillforge add ./skills/my-skill script helper --language python
        skillforge add ./skills/my-skill script build --language bash
    """
    from skillforge.scaffold import add_reference_doc, add_script

    skill_path = Path(skill_path)

    if not skill_path.exists():
        console.print(f"[red]Error:[/red] Skill not found: {skill_path}")
        raise typer.Exit(code=1)

    if item_type == "doc":
        file_path = add_reference_doc(skill_path, name)
        console.print(f"[green]✓[/green] Created document: {file_path}")

    elif item_type == "script":
        file_path = add_script(skill_path, name, language=language)
        console.print(f"[green]✓[/green] Created script: {file_path}")

    else:
        console.print(f"[red]Error:[/red] Unknown item type: {item_type}")
        console.print("[dim]Use 'doc' or 'script'[/dim]")
        raise typer.Exit(code=1)


@app.command()
def preview(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
) -> None:
    """Preview how a skill will appear to Claude.

    Shows the SKILL.md content as Claude would see it when the skill
    is triggered. For composite skills with includes, shows the composed version.

    Example:

    \b
        skillforge preview ./skills/my-skill
    """
    from skillforge.skill import Skill, SkillParseError
    from skillforge.composer import compose_skill, has_includes

    skill_path = Path(skill_path)

    try:
        skill = Skill.from_directory(skill_path)
    except SkillParseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    # Check if skill has includes
    is_composite = has_includes(skill_path)
    if is_composite:
        result = compose_skill(skill_path)
        if result.success and result.skill:
            skill = result.skill
            console.print()
            console.print(f"[yellow]Note:[/yellow] This skill includes {len(result.included_skills)} other skill(s)")
            console.print(f"[dim]Included: {', '.join(result.included_skills)}[/dim]")

    console.print()
    console.print("[bold]System Prompt Entry:[/bold]")
    console.print(Panel(
        f"{skill.name} - {skill.description}",
        border_style="blue",
    ))

    console.print()
    console.print("[bold]SKILL.md Content (loaded when triggered):[/bold]")
    console.print()

    # Show as syntax-highlighted markdown
    syntax = Syntax(
        skill.to_skill_md(),
        "markdown",
        theme="monokai",
        line_numbers=True,
    )
    console.print(syntax)


@app.command()
def compose(
    skill_path: Path = typer.Argument(..., help="Path to composite skill"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for composed skill",
    ),
    preview_only: bool = typer.Option(
        False,
        "--preview",
        "-p",
        help="Preview composed skill without writing",
    ),
) -> None:
    """Compose a skill by resolving includes.

    Takes a skill with `includes` in frontmatter and produces a single
    composed skill with all included content merged.

    Example:

    \b
        skillforge compose ./skills/full-stack-reviewer
        skillforge compose ./skills/my-composite --output ./skills/composed
        skillforge compose ./skills/my-skill --preview
    """
    from skillforge.composer import compose_skill, CompositionError, has_includes

    skill_path = Path(skill_path)

    if not skill_path.exists():
        console.print(f"[red]Error:[/red] Skill not found: {skill_path}")
        raise typer.Exit(code=1)

    # Check if skill has includes
    if not has_includes(skill_path):
        console.print(f"[yellow]Note:[/yellow] Skill has no includes")
        console.print("[dim]Nothing to compose - skill is already standalone[/dim]")
        raise typer.Exit(code=0)

    console.print(f"[dim]Composing skill: {skill_path.name}[/dim]")
    console.print()

    # Compose the skill
    result = compose_skill(
        skill_path,
        output_path=None if preview_only else output,
    )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(code=1)

    # Show resolved includes
    console.print("[bold]Resolved includes:[/bold]")
    for name in result.included_skills:
        console.print(f"  [green]✓[/green] {name}")

    console.print()

    if preview_only:
        # Show preview
        console.print("[bold]Composed Skill Preview:[/bold]")
        console.print()
        syntax = Syntax(
            result.composed_content,
            "markdown",
            theme="monokai",
            line_numbers=True,
        )
        console.print(syntax)
        console.print()
        console.print("[dim]Use --output to write composed skill[/dim]")
    else:
        # Write to output
        if output is None:
            # Default output path
            output = skill_path.parent / f"{skill_path.name}-composed"

        output.mkdir(parents=True, exist_ok=True)
        skill_md_path = output / "SKILL.md"
        skill_md_path.write_text(result.composed_content)

        console.print(f"[green]✓ Composed skill:[/green] {result.skill.name if result.skill else 'unknown'}")
        console.print(f"  Included: {len(result.included_skills)} skill(s)")
        console.print(f"  Output: {output}")
        console.print()
        console.print(f"[dim]Preview with: skillforge preview {output}[/dim]")


@app.command()
def generate(
    description: str = typer.Argument(..., help="Description of what the skill should do"),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Name for the skill (auto-generated if not provided)",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_SKILLS_DIR,
        "--out",
        "-o",
        help="Output directory for the skill",
    ),
    context: Optional[Path] = typer.Option(
        None,
        "--context",
        "-c",
        help="Directory to analyze for project context",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="AI provider (anthropic, openai, ollama)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Specific model to use",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing skill",
    ),
) -> None:
    """Generate a skill using AI.

    Creates a complete, high-quality SKILL.md from a natural language
    description. Requires an AI provider (Anthropic, OpenAI, or Ollama).

    Example:

    \b
        skillforge generate "Help users write clear git commit messages"
        skillforge generate "Review Python code for best practices" --name code-reviewer
        skillforge generate "Analyze CSV files" --context ./my-project --provider anthropic
    """
    from skillforge.ai import generate_skill, get_default_provider
    from skillforge.skill import normalize_skill_name

    console.print()
    console.print("[bold]Generating skill with AI...[/bold]")
    console.print(f"[dim]Description: {description[:80]}{'...' if len(description) > 80 else ''}[/dim]")

    # Check provider availability
    if provider is None:
        default = get_default_provider()
        if default:
            provider, model = default[0], model or default[1]
            console.print(f"[dim]Using provider: {provider} ({model})[/dim]")
        else:
            console.print("[red]Error:[/red] No AI provider available.")
            console.print()
            console.print("[bold]Setup options:[/bold]")
            console.print("  • Anthropic: [cyan]export ANTHROPIC_API_KEY=your-key[/cyan]")
            console.print("  • OpenAI: [cyan]export OPENAI_API_KEY=your-key[/cyan]")
            console.print("  • Ollama: [cyan]ollama serve[/cyan]")
            console.print()
            console.print("Run [cyan]skillforge providers[/cyan] to check status.")
            raise typer.Exit(code=1)
    else:
        console.print(f"[dim]Using provider: {provider}{f' ({model})' if model else ''}[/dim]")

    if context:
        console.print(f"[dim]Analyzing context: {context}[/dim]")

    console.print()

    with console.status("[bold green]Generating skill..."):
        result = generate_skill(
            description=description,
            name=name,
            context_dir=context,
            provider=provider,
            model=model,
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        if result.raw_content:
            console.print()
            console.print("[dim]Raw response (for debugging):[/dim]")
            console.print(result.raw_content[:500])
        raise typer.Exit(code=1)

    # Save the skill
    skill = result.skill
    skill_name = skill.name if skill else normalize_skill_name(name or "generated-skill")
    skill_dir = output_dir / skill_name

    if skill_dir.exists() and not force:
        console.print(f"[red]Error:[/red] Skill already exists: {skill_dir}")
        console.print("[dim]Use --force to overwrite[/dim]")
        raise typer.Exit(code=1)

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md_path = skill_dir / "SKILL.md"
    assert result.raw_content is not None  # Guaranteed by success check
    skill_md_path.write_text(result.raw_content)

    console.print(f"[green]✓ Generated skill:[/green] {skill_dir}")
    console.print(f"  Provider: {result.provider} ({result.model})")
    console.print()

    # Show preview (raw_content guaranteed by assertion above)
    console.print("[bold]Generated SKILL.md:[/bold]")
    content = result.raw_content
    syntax = Syntax(
        content[:1500] + ("..." if len(content) > 1500 else ""),
        "markdown",
        theme="monokai",
        line_numbers=True,
    )
    console.print(syntax)

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. Review and edit: [cyan]{skill_md_path}[/cyan]")
    console.print(f"  2. Validate: [cyan]skillforge validate {skill_dir}[/cyan]")
    console.print(f"  3. Bundle: [cyan]skillforge bundle {skill_dir}[/cyan]")


@app.command()
def improve(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
    request: str = typer.Argument(..., help="What to improve about the skill"),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="AI provider (anthropic, openai, ollama)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Specific model to use",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show changes without saving",
    ),
) -> None:
    """Improve an existing skill using AI.

    Uses AI to enhance the skill based on your request. Can add examples,
    improve instructions, handle edge cases, or refactor the content.

    Example:

    \b
        skillforge improve ./skills/my-skill "Add more examples"
        skillforge improve ./skills/my-skill "Make instructions clearer and more specific"
        skillforge improve ./skills/my-skill "Add error handling guidance" --dry-run
    """
    from skillforge.ai import improve_skill, get_default_provider

    skill_path = Path(skill_path)

    if not skill_path.exists():
        console.print(f"[red]Error:[/red] Skill not found: {skill_path}")
        raise typer.Exit(code=1)

    console.print()
    console.print("[bold]Improving skill with AI...[/bold]")
    console.print(f"[dim]Request: {request[:80]}{'...' if len(request) > 80 else ''}[/dim]")

    # Check provider availability
    if provider is None:
        default = get_default_provider()
        if default:
            provider, model = default[0], model or default[1]
            console.print(f"[dim]Using provider: {provider} ({model})[/dim]")
        else:
            console.print("[red]Error:[/red] No AI provider available.")
            console.print("Run [cyan]skillforge providers[/cyan] to check status.")
            raise typer.Exit(code=1)

    console.print()

    with console.status("[bold green]Improving skill..."):
        result = improve_skill(
            skill_path=skill_path,
            request=request,
            provider=provider,
            model=model,
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(code=1)

    assert result.raw_content is not None  # Guaranteed by success check

    # Show the improved content
    console.print("[bold]Improved SKILL.md:[/bold]")
    content = result.raw_content
    syntax = Syntax(
        content[:2000] + ("..." if len(content) > 2000 else ""),
        "markdown",
        theme="monokai",
        line_numbers=True,
    )
    console.print(syntax)

    if dry_run:
        console.print()
        console.print("[yellow]Dry run - changes not saved[/yellow]")
        console.print("[dim]Remove --dry-run to save changes[/dim]")
    else:
        # Save the improved skill
        skill_md_path = skill_path / "SKILL.md"
        skill_md_path.write_text(content)

        console.print()
        console.print(f"[green]✓ Skill improved and saved:[/green] {skill_md_path}")


@app.command()
def analyze(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="AI provider (anthropic, openai, ollama)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Specific model to use",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON",
    ),
) -> None:
    """Analyze a skill using AI for quality and improvement suggestions.

    Uses AI to evaluate the skill on clarity, completeness, examples,
    and actionability. Provides specific suggestions for improvement.

    Requires an AI provider (set ANTHROPIC_API_KEY or OPENAI_API_KEY,
    or run Ollama locally).

    Example:

    \b
        skillforge analyze ./skills/my-skill
        skillforge analyze ./skills/my-skill --provider anthropic
        skillforge analyze ./skills/my-skill --json
    """
    import json

    from skillforge.ai import analyze_skill, get_default_provider

    skill_path = Path(skill_path)

    if not skill_path.exists():
        console.print(f"[red]Error:[/red] Skill not found: {skill_path}")
        raise typer.Exit(code=1)

    # Check provider availability
    if provider is None:
        default = get_default_provider()
        if default:
            provider, model = default[0], model or default[1]
            if not json_output:
                console.print(f"[dim]Using provider: {provider} ({model})[/dim]")
        else:
            console.print("[red]Error:[/red] No AI provider available.")
            console.print()
            console.print("[bold]Setup options:[/bold]")
            console.print("  • Anthropic: [cyan]export ANTHROPIC_API_KEY=your-key[/cyan]")
            console.print("  • OpenAI: [cyan]export OPENAI_API_KEY=your-key[/cyan]")
            console.print("  • Ollama: [cyan]ollama serve[/cyan]")
            console.print()
            console.print("Run [cyan]skillforge providers[/cyan] to check status.")
            raise typer.Exit(code=1)
    elif not json_output:
        console.print(f"[dim]Using provider: {provider}{f' ({model})' if model else ''}[/dim]")

    if not json_output:
        console.print()

    with console.status("[bold green]Analyzing skill..."):
        result = analyze_skill(
            skill_path=skill_path,
            provider=provider,
            model=model,
        )

    if not result.success:
        if json_output:
            console.print(json.dumps({"success": False, "error": result.error}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(code=1)

    # Output as JSON
    if json_output:
        data = {
            "success": True,
            "skill_name": result.skill_name,
            "overall_score": result.overall_score,
            "clarity_score": result.clarity_score,
            "completeness_score": result.completeness_score,
            "examples_score": result.examples_score,
            "actionability_score": result.actionability_score,
            "strengths": result.strengths,
            "suggestions": result.suggestions,
            "issues": result.issues,
            "provider": result.provider,
            "model": result.model,
        }
        console.print(json.dumps(data, indent=2))
        return

    # Human-readable output
    console.print()
    console.print(Panel(
        f"[bold]Skill Analysis: {result.skill_name}[/bold]",
        border_style="blue",
    ))

    # Overall score
    console.print()
    score_color = "green" if (result.overall_score or 0) >= 70 else "yellow" if (result.overall_score or 0) >= 50 else "red"
    console.print(f"[bold]Overall Score:[/bold] [{score_color}]{result.overall_score}/100[/{score_color}]")

    # Scores table
    console.print()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Dimension")
    table.add_column("Score", justify="right")

    scores = [
        ("Clarity", result.clarity_score),
        ("Completeness", result.completeness_score),
        ("Examples", result.examples_score),
        ("Actionability", result.actionability_score),
    ]

    for name, score in scores:
        if score is not None:
            color = "green" if score >= 70 else "yellow" if score >= 50 else "red"
            table.add_row(name, f"[{color}]{score}/100[/{color}]")
        else:
            table.add_row(name, "[dim]N/A[/dim]")

    console.print(table)

    # Strengths
    if result.strengths:
        console.print()
        console.print("[bold green]Strengths:[/bold green]")
        for strength in result.strengths:
            console.print(f"  [green]•[/green] {strength}")

    # Suggestions
    if result.suggestions:
        console.print()
        console.print("[bold yellow]Suggestions:[/bold yellow]")
        for suggestion in result.suggestions:
            console.print(f"  [yellow]•[/yellow] {suggestion}")

    # Issues
    if result.issues:
        console.print()
        console.print("[bold red]Issues:[/bold red]")
        for issue in result.issues:
            console.print(f"  [red]•[/red] {issue}")

    console.print()
    console.print(f"[dim]Analyzed with: {result.provider}/{result.model}[/dim]")


@app.command()
def test(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
    mode: str = typer.Option(
        "mock",
        "--mode",
        "-m",
        help="Test mode: 'mock' (pattern matching) or 'live' (real API calls)",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="AI provider for live mode (anthropic, openai, ollama)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Model to use for live mode",
    ),
    tags: Optional[str] = typer.Option(
        None,
        "--tags",
        "-t",
        help="Run only tests with these tags (comma-separated)",
    ),
    names: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Run only tests matching these names (comma-separated)",
    ),
    output_format: str = typer.Option(
        "human",
        "--format",
        "-f",
        help="Output format: 'human', 'json', or 'junit'",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write results to file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output including responses",
    ),
    estimate_cost: bool = typer.Option(
        False,
        "--estimate-cost",
        help="Estimate cost for live mode without running tests",
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        help="Timeout in seconds for each test (live mode)",
    ),
    stop_on_failure: bool = typer.Option(
        False,
        "--stop",
        "-s",
        help="Stop at first failure",
    ),
    regression: bool = typer.Option(
        False,
        "--regression",
        help="Run regression tests against recorded baselines",
    ),
    record_baselines: bool = typer.Option(
        False,
        "--record-baselines",
        help="Record responses as baselines for regression testing",
    ),
    threshold: float = typer.Option(
        0.8,
        "--threshold",
        help="Similarity threshold for regression tests (0.0-1.0)",
    ),
) -> None:
    """Run tests for a skill.

    Tests are defined in YAML files within the skill directory:
    - <skill>/tests.yml
    - <skill>/tests/*.test.yml

    Mock mode (default) uses pattern matching and predefined responses.
    Live mode makes real API calls to validate skill behavior.
    Regression mode compares responses against recorded baselines.

    Example:

    \b
        skillforge test ./skills/my-skill
        skillforge test ./skills/my-skill --mode live
        skillforge test ./skills/my-skill --tags smoke,critical
        skillforge test ./skills/my-skill --format json -o results.json
        skillforge test ./skills/my-skill --mode live --estimate-cost
        skillforge test ./skills/my-skill --regression
        skillforge test ./skills/my-skill --record-baselines
    """
    from skillforge.tester import (
        discover_tests,
        estimate_live_cost,
        load_test_suite,
        run_test_suite,
        record_baselines as record_test_baselines,
        run_regression_tests,
        load_baselines,
        has_baselines,
        RegressionBaselineFile,
        TestDefinitionError,
        SkillTestError,
    )
    from skillforge.ai import get_default_provider

    skill_path = Path(skill_path)

    if not skill_path.exists():
        console.print(f"[red]Error:[/red] Skill not found: {skill_path}")
        raise typer.Exit(code=1)

    # Discover tests
    test_files = discover_tests(skill_path)
    if not test_files:
        console.print(f"[yellow]No tests found for skill:[/yellow] {skill_path}")
        console.print("[dim]Create tests.yml or tests/*.test.yml[/dim]")
        console.print()
        console.print("[bold]Example tests.yml:[/bold]")
        console.print("""[dim]
version: "1.0"
tests:
  - name: "basic_test"
    input: "Test input for the skill"
    assertions:
      - type: contains
        value: "expected text"
    mock:
      response: "Mocked response for testing"
[/dim]""")
        raise typer.Exit(code=0)

    console.print()
    console.print(f"[bold]Testing skill:[/bold] {skill_path.name}")
    console.print(f"[dim]Mode: {mode} | Tests found: {len(test_files)} file(s)[/dim]")

    # Load skill and tests
    try:
        skill, suite = load_test_suite(skill_path)
    except TestDefinitionError as e:
        console.print(f"[red]Error loading tests:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    # Handle live mode provider
    if mode == "live":
        if provider is None:
            default = get_default_provider()
            if default:
                provider, model = default[0], model or default[1]
            else:
                console.print("[red]Error:[/red] No AI provider available for live mode.")
                console.print("Run [cyan]skillforge providers[/cyan] to check status.")
                raise typer.Exit(code=1)
        console.print(f"[dim]Provider: {provider} ({model})[/dim]")

    # Handle cost estimation
    if estimate_cost:
        if mode != "live":
            console.print("[yellow]Cost estimation only applies to live mode[/yellow]")
            raise typer.Exit(code=0)

        estimate = estimate_live_cost(suite, model or "claude-sonnet-4-20250514")

        console.print()
        console.print("[bold]Cost Estimate:[/bold]")
        console.print(f"  Tests to run: {estimate['num_tests']}")
        console.print(f"  Est. input tokens: {estimate['estimated_input_tokens']:,}")
        console.print(f"  Est. output tokens: {estimate['estimated_output_tokens']:,}")
        console.print(f"  [bold]Est. total cost: ${estimate['estimated_total_cost']:.4f}[/bold]")
        console.print(f"  [dim]{estimate['note']}[/dim]")
        raise typer.Exit(code=0)

    # Handle baseline recording
    if record_baselines:
        console.print()
        console.print("[dim]Recording baselines...[/dim]")

        baselines = record_test_baselines(
            skill=skill,
            suite=suite,
            baselines_path=skill_path,
            mode=mode,  # type: ignore[arg-type]
            provider=provider,
            model=model,
            overwrite=True,
        )

        console.print()
        console.print(f"[green]✓ Recorded {len(baselines.baselines)} baseline(s)[/green]")
        console.print(f"  Saved to: {skill_path / 'baselines.yml'}")
        console.print()
        console.print("[dim]Run regression tests: skillforge test ./skill --regression[/dim]")
        raise typer.Exit(code=0)

    # Handle regression testing
    if regression:
        if not has_baselines(skill_path):
            console.print("[yellow]No baselines found for regression testing[/yellow]")
            console.print()
            console.print("[dim]Record baselines first:[/dim]")
            console.print(f"  skillforge test {skill_path} --record-baselines")
            raise typer.Exit(code=1)

        baselines = load_baselines(skill_path)
        console.print(f"[dim]Running regression tests (threshold: {threshold:.0%})...[/dim]")
        console.print()

        regression_result = run_regression_tests(
            skill=skill,
            suite=suite,
            baselines=baselines,
            mode=mode,  # type: ignore[arg-type]
            provider=provider,
            model=model,
            threshold=threshold,
            stop_on_failure=stop_on_failure,
        )

        # Display regression results
        table = Table(title="Regression Test Results", show_header=True, header_style="bold")
        table.add_column("Test", style="cyan")
        table.add_column("Status")
        table.add_column("Similarity", justify="right")
        table.add_column("Details", style="dim")

        for rr in regression_result.results:
            if rr.passed:
                status = "[green]PASS[/green]"
            else:
                status = "[red]FAIL[/red]"

            similarity = f"{rr.similarity:.1%}"
            details = rr.message

            table.add_row(rr.test_name, status, similarity, details)

        console.print(table)

        console.print()
        console.print(f"[bold]Summary:[/bold] [green]{regression_result.passed_tests} passed[/green]", end="")
        if regression_result.failed_tests:
            console.print(f", [red]{regression_result.failed_tests} failed[/red]", end="")
        if regression_result.missing_baselines:
            console.print(f", [yellow]{regression_result.missing_baselines} missing[/yellow]", end="")
        console.print()

        if regression_result.success:
            raise typer.Exit(code=0)
        else:
            raise typer.Exit(code=1)

    # Parse filters
    filter_tags = tags.split(",") if tags else None
    filter_names = names.split(",") if names else None

    # Run tests
    console.print()

    with console.status("[bold green]Running tests..."):
        result = run_test_suite(
            skill=skill,
            suite=suite,
            mode=mode,  # type: ignore[arg-type]
            provider=provider,
            model=model,
            filter_tags=filter_tags,
            filter_names=filter_names,
            stop_on_failure=stop_on_failure,
        )

    # Output results
    if output_format == "json":
        output = _format_results_json(result)
        if output_file:
            output_file.write_text(output)
            console.print(f"[green]Results written to:[/green] {output_file}")
        else:
            console.print(output)

    elif output_format == "junit":
        output = _format_results_junit(result)
        if output_file:
            output_file.write_text(output)
            console.print(f"[green]JUnit XML written to:[/green] {output_file}")
        else:
            console.print(output)

    else:  # human format
        _display_results_human(result, verbose)

    # Exit with appropriate code
    if result.success:
        raise typer.Exit(code=0)
    else:
        raise typer.Exit(code=1)


def _display_results_human(result: "TestSuiteResult", verbose: bool) -> None:
    """Display test results in human-readable format."""
    from skillforge.tester import TestStatus

    # Results table
    table = Table(title="Test Results", show_header=True, header_style="bold")
    table.add_column("Test", style="cyan")
    table.add_column("Status")
    table.add_column("Duration", justify="right")
    table.add_column("Details", style="dim")

    for tr in result.test_results:
        if tr.status == TestStatus.PASSED:
            status = "[green]PASS[/green]"
        elif tr.status == TestStatus.FAILED:
            status = "[red]FAIL[/red]"
        elif tr.status == TestStatus.SKIPPED:
            status = "[yellow]SKIP[/yellow]"
        else:
            status = "[red]ERROR[/red]"

        duration = f"{tr.duration_ms:.1f}ms"

        details = ""
        if tr.failed_assertions:
            details = f"{len(tr.failed_assertions)} assertion(s) failed"
        elif tr.error:
            details = tr.error[:40] + "..." if len(tr.error) > 40 else tr.error

        table.add_row(tr.test_case.name, status, duration, details)

    console.print(table)

    # Verbose output: show failures
    if verbose or result.failed_tests > 0:
        for tr in result.test_results:
            if tr.status == TestStatus.FAILED:
                console.print()
                console.print(f"[red bold]FAILED:[/red bold] {tr.test_case.name}")
                for ar in tr.failed_assertions:
                    console.print(f"  [red]✗[/red] {ar.message}")
                    if ar.actual_value:
                        console.print(f"    [dim]Got: {ar.actual_value}[/dim]")

                if verbose and tr.response:
                    console.print()
                    console.print("[dim]Response:[/dim]")
                    console.print(Panel(tr.response[:500], border_style="dim"))

    # Summary
    console.print()
    summary_parts = []
    summary_parts.append(f"[green]{result.passed_tests} passed[/green]")
    if result.failed_tests:
        summary_parts.append(f"[red]{result.failed_tests} failed[/red]")
    if result.skipped_tests:
        summary_parts.append(f"[yellow]{result.skipped_tests} skipped[/yellow]")
    if result.error_tests:
        summary_parts.append(f"[red]{result.error_tests} errors[/red]")

    console.print(f"[bold]Summary:[/bold] {', '.join(summary_parts)}")
    console.print(f"[dim]Total time: {result.duration_ms:.1f}ms | Mode: {result.mode}[/dim]")

    if result.mode == "live" and result.total_cost > 0:
        console.print(f"[dim]Estimated cost: ${result.total_cost:.4f}[/dim]")


def _format_results_json(result: "TestSuiteResult") -> str:
    """Format test results as JSON."""
    import json

    data = {
        "skill": result.skill.name,
        "mode": result.mode,
        "summary": {
            "total": result.total_tests,
            "passed": result.passed_tests,
            "failed": result.failed_tests,
            "skipped": result.skipped_tests,
            "errors": result.error_tests,
            "duration_ms": result.duration_ms,
            "cost_estimate": result.total_cost,
        },
        "tests": [
            {
                "name": tr.test_case.name,
                "description": tr.test_case.description,
                "status": tr.status.value,
                "duration_ms": tr.duration_ms,
                "assertions": [
                    {
                        "type": ar.assertion.type.value,
                        "passed": ar.passed,
                        "message": ar.message,
                        "actual": ar.actual_value,
                    }
                    for ar in tr.assertion_results
                ],
                "error": tr.error,
            }
            for tr in result.test_results
        ],
    }

    return json.dumps(data, indent=2)


def _format_results_junit(result: "TestSuiteResult") -> str:
    """Format test results as JUnit XML for CI integration."""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom
    from skillforge.tester import TestStatus

    testsuite = Element("testsuite")
    testsuite.set("name", result.skill.name)
    testsuite.set("tests", str(result.total_tests))
    testsuite.set("failures", str(result.failed_tests))
    testsuite.set("errors", str(result.error_tests))
    testsuite.set("skipped", str(result.skipped_tests))
    testsuite.set("time", f"{result.duration_ms / 1000:.3f}")

    for tr in result.test_results:
        testcase = SubElement(testsuite, "testcase")
        testcase.set("name", tr.test_case.name)
        testcase.set("classname", f"{result.skill.name}.{tr.test_case.name}")
        testcase.set("time", f"{tr.duration_ms / 1000:.3f}")

        if tr.status == TestStatus.FAILED:
            for ar in tr.failed_assertions:
                failure = SubElement(testcase, "failure")
                failure.set("message", ar.message)
                if ar.actual_value:
                    failure.text = f"Actual: {ar.actual_value}"

        elif tr.status == TestStatus.ERROR:
            error = SubElement(testcase, "error")
            error.set("message", tr.error or "Unknown error")

        elif tr.status == TestStatus.SKIPPED:
            skipped = SubElement(testcase, "skipped")
            if tr.error:
                skipped.set("message", tr.error)

    rough_string = tostring(testsuite, encoding="unicode")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


# =============================================================================
# Templates Commands
# =============================================================================

templates_app = typer.Typer(
    help="Manage skill templates",
    no_args_is_help=False,
)
app.add_typer(templates_app, name="templates")


@templates_app.callback(invoke_without_command=True)
def templates_list(ctx: typer.Context) -> None:
    """List available skill templates.

    Example:

    \b
        skillforge templates
    """
    if ctx.invoked_subcommand is not None:
        return

    from skillforge.templates import list_templates

    templates = list_templates()

    console.print()
    table = Table(title="Available Templates", show_header=True, header_style="bold")
    table.add_column("Template", style="cyan")
    table.add_column("Category")
    table.add_column("Description")

    for tmpl in templates:
        table.add_row(tmpl.name, tmpl.category, tmpl.description)

    console.print(table)
    console.print()
    console.print("[dim]Use: skillforge new my-skill --template <name>[/dim]")
    console.print("[dim]Preview: skillforge templates show <name>[/dim]")


@templates_app.command("show")
def templates_show(
    name: str = typer.Argument(..., help="Template name to show"),
) -> None:
    """Show details of a template.

    Displays the template's description and a preview of its content.

    Example:

    \b
        skillforge templates show code-review
        skillforge templates show git-commit
    """
    from skillforge.templates import get_template, get_template_names

    template = get_template(name)

    if not template:
        console.print(f"[red]Error:[/red] Unknown template: {name}")
        console.print()
        available = ", ".join(get_template_names())
        console.print(f"[dim]Available templates: {available}[/dim]")
        raise typer.Exit(code=1)

    console.print()
    console.print(Panel(
        f"[bold]{template.title}[/bold]\n\n"
        f"[dim]Category:[/dim] {template.category}\n"
        f"[dim]Tags:[/dim] {', '.join(template.tags)}\n\n"
        f"{template.description}",
        title=f"Template: {template.name}",
        border_style="blue",
    ))

    console.print()
    console.print("[bold]Content Preview:[/bold]")

    # Show preview of content (first ~60 lines or 2000 chars)
    content_preview = template.content
    lines = content_preview.split("\n")
    if len(lines) > 60:
        content_preview = "\n".join(lines[:60]) + "\n\n[...truncated...]"
    elif len(content_preview) > 2000:
        content_preview = content_preview[:2000] + "\n\n[...truncated...]"

    syntax = Syntax(
        content_preview,
        "markdown",
        theme="monokai",
        line_numbers=True,
    )
    console.print(syntax)

    console.print()
    console.print(f"[bold]Create skill:[/bold] [cyan]skillforge new my-skill --template {name}[/cyan]")


# =============================================================================
# Claude Code Integration Commands
# =============================================================================


@app.command("install")
def install_to_claude(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
    project: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Install to project (./.claude/skills/) instead of user (~/.claude/skills/)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite if already installed",
    ),
) -> None:
    """Install a skill to Claude Code.

    Copies the skill to Claude Code's skills directory so it's automatically
    available when using Claude Code.

    By default, installs to ~/.claude/skills/ (user-level, all projects).
    Use --project to install to ./.claude/skills/ (project-level only).

    Example:

    \b
        skillforge install ./skills/code-reviewer
        skillforge install ./skills/project-helper --project
        skillforge install ./skills/my-skill --force
    """
    from skillforge.claude_code import install_skill, get_skills_dir

    skill_path = Path(skill_path).resolve()
    scope = "project" if project else "user"

    console.print(f"[dim]Installing to: {get_skills_dir(scope)}[/dim]")

    try:
        result = install_skill(skill_path, scope=scope, force=force)

        console.print()
        if result.was_update:
            console.print(f"[green]✓ Updated:[/green] {result.skill_name}")
        else:
            console.print(f"[green]✓ Installed:[/green] {result.skill_name}")
        console.print(f"  [dim]Location: {result.installed_path}[/dim]")
        console.print()
        console.print("[dim]Skill is now available in Claude Code.[/dim]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    except FileExistsError as e:
        console.print(f"[yellow]Warning:[/yellow] {e}")
        raise typer.Exit(code=1)


@app.command("uninstall")
def uninstall_from_claude(
    skill_name: str = typer.Argument(..., help="Name of the skill to uninstall"),
    project: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Uninstall from project (./.claude/skills/)",
    ),
) -> None:
    """Uninstall a skill from Claude Code.

    Removes the skill from Claude Code's skills directory.

    Example:

    \b
        skillforge uninstall code-reviewer
        skillforge uninstall project-helper --project
    """
    from skillforge.claude_code import uninstall_skill

    scope = "project" if project else "user"

    removed_path = uninstall_skill(skill_name, scope=scope)

    if removed_path:
        console.print(f"[green]✓ Uninstalled:[/green] {skill_name}")
        console.print(f"  [dim]Removed from: {removed_path}[/dim]")
    else:
        console.print(f"[yellow]Not found:[/yellow] {skill_name}")
        console.print(f"[dim]Skill not installed in {scope} scope[/dim]")
        raise typer.Exit(code=1)


@app.command("sync")
def sync_to_claude(
    source_dir: Path = typer.Argument(
        Path("./skills"),
        help="Directory containing skills to sync",
    ),
    project: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Install to project (./.claude/skills/)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing installations",
    ),
) -> None:
    """Sync all skills from a directory to Claude Code.

    Finds all valid skills in the source directory and installs them
    to Claude Code's skills directory.

    Example:

    \b
        skillforge sync ./skills
        skillforge sync ./my-skills --project
        skillforge sync ./skills --force
    """
    from skillforge.claude_code import sync_skills, get_skills_dir

    source_dir = Path(source_dir).resolve()
    scope = "project" if project else "user"

    console.print(f"[dim]Syncing skills to: {get_skills_dir(scope)}[/dim]")
    console.print()

    try:
        installed, errors = sync_skills(source_dir, scope=scope, force=force)

        for result in installed:
            if result.was_update:
                console.print(f"[green]✓ Updated:[/green] {result.skill_name}")
            else:
                console.print(f"[green]✓ Installed:[/green] {result.skill_name}")

        for name, error in errors:
            console.print(f"[yellow]⚠ Skipped:[/yellow] {name} ({error})")

        console.print()
        if installed:
            console.print(f"[bold]Installed {len(installed)} skill(s)[/bold]")
        if errors:
            console.print(f"[dim]Skipped {len(errors)} skill(s)[/dim]")

        if not installed and not errors:
            console.print("[yellow]No skills found in source directory[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("installed")
def list_installed(
    project: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Show only project-level skills",
    ),
    user: bool = typer.Option(
        False,
        "--user",
        "-u",
        help="Show only user-level skills",
    ),
    paths: bool = typer.Option(
        False,
        "--paths",
        help="Show full installation paths",
    ),
) -> None:
    """List skills installed in Claude Code.

    Shows all skills that have been installed to Claude Code's
    skills directories.

    Example:

    \b
        skillforge installed
        skillforge installed --project
        skillforge installed --paths
    """
    from skillforge.claude_code import list_installed_skills, USER_SKILLS_DIR, PROJECT_SKILLS_DIR

    # Determine scope filter
    scope = None
    if project and not user:
        scope = "project"
    elif user and not project:
        scope = "user"

    skills = list_installed_skills(scope=scope)

    if not skills:
        console.print("[yellow]No skills installed[/yellow]")
        console.print()
        console.print("[dim]Install a skill with:[/dim]")
        console.print("  skillforge install ./skills/my-skill")
        return

    console.print()
    table = Table(title="Installed Skills", show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Scope")
    if paths:
        table.add_column("Path", style="dim")
    else:
        table.add_column("Description")

    for skill in skills:
        scope_display = "[blue]user[/blue]" if skill.scope == "user" else "[green]project[/green]"
        if paths:
            table.add_row(skill.name, scope_display, str(skill.path))
        else:
            desc = skill.description[:40] + "..." if len(skill.description) > 40 else skill.description
            table.add_row(skill.name, scope_display, desc)

    console.print(table)

    console.print()
    console.print(f"[dim]User skills: {USER_SKILLS_DIR}[/dim]")
    console.print(f"[dim]Project skills: {PROJECT_SKILLS_DIR.resolve()}[/dim]")


# =============================================================================
# AI Commands
# =============================================================================


@app.command()
def providers() -> None:
    """Show available AI providers.

    Checks which AI providers are configured and ready to use
    for skill generation.

    Example:

    \b
        skillforge providers
    """
    from skillforge.ai import get_available_providers

    console.print()
    console.print("[bold]AI Providers[/bold]")
    console.print()

    providers_list = get_available_providers()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Provider")
    table.add_column("Status")
    table.add_column("Models / Info")

    for p in providers_list:
        name = p["name"]
        if p.get("available"):
            status = "[green]✓ Available[/green]"
            models = ", ".join(p.get("models", [])[:3])
            if len(p.get("models", [])) > 3:
                models += ", ..."
            info = f"[dim]{models}[/dim]"
        else:
            status = "[red]✗ Not available[/red]"
            info = f"[dim]{p.get('reason', 'Unknown')}[/dim]"

        table.add_row(name.title(), status, info)

    console.print(table)
    console.print()

    # Show setup instructions if none available
    available = [p for p in providers_list if p.get("available")]
    if not available:
        console.print("[yellow]No providers available.[/yellow]")
        console.print()
        console.print("[bold]Setup options:[/bold]")
        console.print()
        console.print("  [bold]Anthropic (Recommended):[/bold]")
        console.print("    pip install anthropic")
        console.print("    export ANTHROPIC_API_KEY=your-key")
        console.print()
        console.print("  [bold]OpenAI:[/bold]")
        console.print("    pip install openai")
        console.print("    export OPENAI_API_KEY=your-key")
        console.print()
        console.print("  [bold]Ollama (Local, Free):[/bold]")
        console.print("    brew install ollama")
        console.print("    ollama serve")
        console.print("    ollama pull llama3.2")
    else:
        console.print("[green]Ready to generate skills![/green]")
        console.print("[dim]Run: skillforge generate \"your skill description\"[/dim]")


# =============================================================================
# Registry Commands
# =============================================================================

registry_app = typer.Typer(
    help="Manage skill registries",
    no_args_is_help=True,
)
app.add_typer(registry_app, name="registry")


@registry_app.command("add")
def registry_add(
    url: str = typer.Argument(..., help="GitHub repository URL for the registry"),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom name for the registry",
    ),
) -> None:
    """Add a skill registry.

    Registries are GitHub repositories containing an index.json file
    that lists available skills.

    Example:

    \b
        skillforge registry add https://github.com/skillforge/community-skills
        skillforge registry add https://github.com/mycompany/skills --name company
    """
    from skillforge.registry import add_registry, RegistryError

    console.print(f"[dim]Fetching registry index...[/dim]")

    try:
        registry = add_registry(url, name)

        console.print()
        console.print(f"[green]✓ Added registry:[/green] {registry.name}")
        console.print(f"  Skills: {len(registry.skills)}")
        console.print(f"  URL: {registry.url}")

    except RegistryError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@registry_app.command("list")
def registry_list_cmd() -> None:
    """List configured registries.

    Example:

    \b
        skillforge registry list
    """
    from skillforge.registry import list_registries

    registries = list_registries()

    if not registries:
        console.print("[yellow]No registries configured[/yellow]")
        console.print()
        console.print("[dim]Add a registry with:[/dim]")
        console.print("  skillforge registry add https://github.com/user/skills-registry")
        return

    console.print()
    table = Table(title="Configured Registries", show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Skills", justify="right")
    table.add_column("URL")

    for reg in registries:
        # Truncate URL if too long
        url_display = reg.url
        if len(url_display) > 45:
            url_display = url_display[:42] + "..."
        table.add_row(reg.name, str(len(reg.skills)), url_display)

    console.print(table)
    console.print()
    console.print(f"[dim]Update indexes: skillforge registry update[/dim]")


@registry_app.command("remove")
def registry_remove_cmd(
    name: str = typer.Argument(..., help="Name of the registry to remove"),
) -> None:
    """Remove a registry.

    Example:

    \b
        skillforge registry remove community-skills
    """
    from skillforge.registry import remove_registry

    if remove_registry(name):
        console.print(f"[green]✓ Removed registry:[/green] {name}")
    else:
        console.print(f"[yellow]Registry not found:[/yellow] {name}")
        raise typer.Exit(code=1)


@registry_app.command("update")
def registry_update_cmd() -> None:
    """Update all registry indexes.

    Refreshes the cached skill lists from all configured registries.

    Example:

    \b
        skillforge registry update
    """
    from skillforge.registry import update_registries, list_registries

    registries = list_registries()
    if not registries:
        console.print("[yellow]No registries configured[/yellow]")
        return

    console.print("[dim]Updating registry indexes...[/dim]")
    console.print()

    updated = update_registries()

    for reg in updated:
        console.print(f"[green]✓[/green] {reg.name}: {len(reg.skills)} skills")

    console.print()
    console.print(f"[dim]Updated {len(updated)} registry(ies)[/dim]")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    registry_name: Optional[str] = typer.Option(
        None,
        "--registry",
        "-r",
        help="Search only in this registry",
    ),
) -> None:
    """Search for skills in registries.

    Searches skill names, descriptions, and tags across all configured
    registries.

    Example:

    \b
        skillforge search "code review"
        skillforge search python --registry community-skills
    """
    from skillforge.registry import search_skills, list_registries

    registries = list_registries()
    if not registries:
        console.print("[yellow]No registries configured[/yellow]")
        console.print()
        console.print("[dim]Add a registry first:[/dim]")
        console.print("  skillforge registry add https://github.com/user/skills-registry")
        return

    results = search_skills(query, registry_name)

    if not results:
        console.print(f"[yellow]No skills found matching:[/yellow] \"{query}\"")
        console.print()
        console.print("[dim]Try a different search term or add more registries[/dim]")
        return

    console.print()
    table = Table(
        title=f'Search Results: "{query}"',
        show_header=True,
        header_style="bold",
    )
    table.add_column("Skill", style="cyan")
    table.add_column("Version")
    table.add_column("Registry", style="dim")
    table.add_column("Description")

    for skill in results[:20]:  # Limit to 20 results
        desc = skill.description[:40] + "..." if len(skill.description) > 40 else skill.description
        table.add_row(skill.name, skill.version, skill.registry, desc)

    console.print(table)

    if len(results) > 20:
        console.print(f"[dim]...and {len(results) - 20} more results[/dim]")

    console.print()
    console.print(f"[dim]Found {len(results)} skill(s) matching \"{query}\"[/dim]")
    console.print("[dim]Pull with: skillforge pull <skill-name>[/dim]")


@app.command()
def pull(
    skill_name: str = typer.Argument(..., help="Name of the skill to download"),
    output: Path = typer.Option(
        Path("./skills"),
        "--output",
        "-o",
        help="Output directory",
    ),
    registry_name: Optional[str] = typer.Option(
        None,
        "--registry",
        "-r",
        help="Pull from specific registry",
    ),
    version: Optional[str] = typer.Option(
        None,
        "--version",
        "-v",
        help="Version or constraint (e.g., '1.2.0', '^1.0.0', '>=2.0.0')",
    ),
    locked: bool = typer.Option(
        False,
        "--locked",
        help="Use versions from lock file",
    ),
) -> None:
    """Download a skill from a registry.

    Downloads the skill to the specified output directory (default: ./skills/).
    Can specify version constraints like '^1.0.0' or '>=2.0.0'.

    Example:

    \b
        skillforge pull code-reviewer
        skillforge pull my-skill --output ./my-skills
        skillforge pull company-skill --registry company
        skillforge pull code-reviewer --version "^1.0.0"
        skillforge pull code-reviewer --locked
    """
    from skillforge.registry import pull_skill, get_skill_info, list_skill_versions, RegistryError, SkillNotFoundError
    from skillforge.lockfile import SkillLockFile, LockFileError

    # Handle locked mode
    if locked:
        try:
            lock_file = SkillLockFile.load(output)
            locked_skill = lock_file.get_skill(skill_name)
            if locked_skill:
                version = locked_skill.version
                console.print(f"[dim]Using locked version: {version}[/dim]")
            else:
                console.print(f"[yellow]Warning:[/yellow] Skill '{skill_name}' not in lock file")
        except LockFileError:
            console.print(f"[yellow]Warning:[/yellow] No lock file found in {output}")

    # Get skill info first
    skill = get_skill_info(skill_name, registry_name)
    if not skill:
        console.print(f"[red]Error:[/red] Skill '{skill_name}' not found")
        console.print()
        console.print("[dim]Search for available skills:[/dim]")
        console.print(f"  skillforge search {skill_name}")
        raise typer.Exit(code=1)

    # Show available versions if version specified
    if version:
        versions = list_skill_versions(skill_name, registry_name)
        if versions:
            console.print(f"[dim]Available versions: {', '.join(str(v) for v in versions[:5])}{'...' if len(versions) > 5 else ''}[/dim]")

    console.print(f"[dim]Downloading {skill_name} from {skill.registry}...[/dim]")

    try:
        skill_dir = pull_skill(skill_name, output, registry_name, version=version)

        resolved_version = version or skill.version
        console.print()
        console.print(f"[green]✓ Downloaded:[/green] {skill_name} v{resolved_version}")
        console.print(f"  Location: {skill_dir}")
        console.print()
        console.print("[dim]Next steps:[/dim]")
        console.print(f"  Validate: skillforge validate {skill_dir}")
        console.print(f"  Install:  skillforge install {skill_dir}")

    except SkillNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    except RegistryError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# Version Commands
# =============================================================================

version_app = typer.Typer(
    help="Manage skill versions",
    no_args_is_help=True,
)
app.add_typer(version_app, name="version")


@version_app.command("show")
def version_show(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
) -> None:
    """Show the version of a skill.

    Example:

    \b
        skillforge version show ./skills/my-skill
    """
    from skillforge.skill import Skill, SkillParseError

    skill_path = Path(skill_path)

    try:
        skill = Skill.from_directory(skill_path)
    except SkillParseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    console.print()
    console.print(f"[bold]Skill:[/bold] {skill.name}")
    if skill.version:
        console.print(f"[bold]Version:[/bold] {skill.version}")
    else:
        console.print(f"[bold]Version:[/bold] [dim]not specified[/dim]")
        console.print()
        console.print("[dim]Add a version with: skillforge version bump ./skills/my-skill --set 1.0.0[/dim]")


@version_app.command("bump")
def version_bump(
    skill_path: Path = typer.Argument(..., help="Path to the skill directory"),
    major: bool = typer.Option(
        False,
        "--major",
        help="Bump major version (x.0.0)",
    ),
    minor: bool = typer.Option(
        False,
        "--minor",
        help="Bump minor version (0.x.0)",
    ),
    patch: bool = typer.Option(
        False,
        "--patch",
        help="Bump patch version (0.0.x) - default",
    ),
    set_version: Optional[str] = typer.Option(
        None,
        "--set",
        help="Set to a specific version (e.g., 1.0.0)",
    ),
) -> None:
    """Bump the version of a skill.

    By default bumps the patch version. Use --major, --minor, or --set
    for other version changes.

    Example:

    \b
        skillforge version bump ./skills/my-skill
        skillforge version bump ./skills/my-skill --minor
        skillforge version bump ./skills/my-skill --major
        skillforge version bump ./skills/my-skill --set 2.0.0
    """
    from skillforge.skill import Skill, SkillParseError
    from skillforge.versioning import SkillVersion, parse_version, VersionParseError

    skill_path = Path(skill_path)

    try:
        skill = Skill.from_directory(skill_path)
    except SkillParseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    old_version = skill.version

    if set_version:
        # Set to specific version
        try:
            parsed = parse_version(set_version)
            new_version = str(parsed)
        except VersionParseError as e:
            console.print(f"[red]Error:[/red] Invalid version format: {e}")
            raise typer.Exit(code=1)
    else:
        # Bump existing version
        if not old_version:
            old_version = "0.0.0"

        try:
            current = parse_version(old_version)
        except VersionParseError:
            console.print(f"[yellow]Warning:[/yellow] Current version '{old_version}' invalid, starting from 0.0.0")
            current = SkillVersion(0, 0, 0)

        if major:
            new_version = str(current.bump("major"))
        elif minor:
            new_version = str(current.bump("minor"))
        else:
            # Default to patch
            new_version = str(current.bump("patch"))

    # Update the skill
    skill.version = new_version

    # Write back to SKILL.md
    skill_md_path = skill_path / "SKILL.md"
    skill_md_path.write_text(skill.to_skill_md())

    console.print()
    if old_version:
        console.print(f"[green]✓ Version bumped:[/green] {old_version} → {new_version}")
    else:
        console.print(f"[green]✓ Version set:[/green] {new_version}")
    console.print(f"  Updated: {skill_md_path}")


@version_app.command("list")
def version_list(
    skill_name: str = typer.Argument(..., help="Skill name to look up in registries"),
    registry_name: Optional[str] = typer.Option(
        None,
        "--registry",
        "-r",
        help="Search only in this registry",
    ),
) -> None:
    """List available versions of a skill from registries.

    Example:

    \b
        skillforge version list code-reviewer
        skillforge version list my-skill --registry company
    """
    from skillforge.registry import list_skill_versions, get_skill_info

    skill = get_skill_info(skill_name, registry_name)
    if not skill:
        console.print(f"[red]Error:[/red] Skill '{skill_name}' not found in registries")
        raise typer.Exit(code=1)

    versions = list_skill_versions(skill_name, registry_name)

    console.print()
    console.print(f"[bold]Skill:[/bold] {skill_name}")
    console.print(f"[bold]Registry:[/bold] {skill.registry}")
    console.print()

    if versions:
        console.print("[bold]Available Versions:[/bold]")
        for v in versions:
            if str(v) == skill.version:
                console.print(f"  [green]{v}[/green] (latest)")
            else:
                console.print(f"  {v}")
    else:
        console.print(f"[dim]No version info available (latest: {skill.version})[/dim]")

    console.print()
    console.print(f"[dim]Pull specific version: skillforge pull {skill_name} --version <version>[/dim]")


# =============================================================================
# Lock File Commands
# =============================================================================


@app.command("lock")
def lock_cmd(
    skills_dir: Path = typer.Argument(
        Path("./skills"),
        help="Directory containing skills to lock",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Verify existing lock file instead of generating",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for lock file",
    ),
) -> None:
    """Generate or verify a lock file for reproducible installations.

    Creates a skillforge.lock file that pins exact versions and checksums
    for all skills, ensuring reproducible installations.

    Example:

    \b
        skillforge lock ./skills
        skillforge lock ./skills --check
        skillforge lock ./skills -o custom.lock
    """
    from skillforge.lockfile import (
        SkillLockFile,
        generate_lock_file,
        verify_against_lock,
        LockFileError,
        LOCK_FILE_NAME,
    )

    skills_dir = Path(skills_dir)

    if not skills_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {skills_dir}")
        raise typer.Exit(code=1)

    if check:
        # Verify mode
        lock_path = output or (skills_dir / LOCK_FILE_NAME)

        try:
            lock_file = SkillLockFile.load(lock_path)
        except LockFileError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

        console.print(f"[dim]Verifying against: {lock_path}[/dim]")
        console.print()

        result = verify_against_lock(skills_dir, lock_file)

        # Show results
        if result.matched:
            console.print("[bold]Matched:[/bold]")
            for name in result.matched:
                console.print(f"  [green]✓[/green] {name}")

        if result.mismatched:
            console.print()
            console.print("[bold red]Mismatched (content changed):[/bold red]")
            for name in result.mismatched:
                console.print(f"  [red]✗[/red] {name}")

        if result.missing:
            console.print()
            console.print("[bold yellow]Missing:[/bold yellow]")
            for name in result.missing:
                console.print(f"  [yellow]?[/yellow] {name}")

        if result.unlocked:
            console.print()
            console.print("[bold]Unlocked (not in lock file):[/bold]")
            for name in result.unlocked:
                console.print(f"  [dim]-[/dim] {name}")

        console.print()
        if result.verified:
            console.print("[green]✓ Lock file verified[/green]")
        else:
            console.print("[red]✗ Lock file verification failed[/red]")
            raise typer.Exit(code=1)

    else:
        # Generate mode
        console.print(f"[dim]Scanning skills in: {skills_dir}[/dim]")

        lock_file = generate_lock_file(skills_dir)

        if not lock_file.skills:
            console.print("[yellow]No skills found to lock[/yellow]")
            return

        # Save lock file
        lock_path = output or (skills_dir / LOCK_FILE_NAME)
        lock_file.save(lock_path)

        console.print()
        console.print(f"[green]✓ Lock file created:[/green] {lock_path}")
        console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("Skill", style="cyan")
        table.add_column("Version")
        table.add_column("Checksum", style="dim")

        for name, locked in sorted(lock_file.skills.items()):
            # Truncate checksum for display
            checksum_display = locked.checksum[:20] + "..."
            table.add_row(name, locked.version, checksum_display)

        console.print(table)
        console.print()
        console.print(f"[dim]Locked {len(lock_file.skills)} skill(s)[/dim]")
        console.print()
        console.print("[dim]Verify with: skillforge lock --check[/dim]")
        console.print("[dim]Install locked: skillforge pull <skill> --locked[/dim]")


# =============================================================================
# MCP Commands (v0.10.0)
# =============================================================================

mcp_app = typer.Typer(
    name="mcp",
    help="MCP (Model Context Protocol) integration commands.",
    no_args_is_help=True,
)
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("init")
def mcp_init(
    server_dir: Path = typer.Argument(..., help="Directory for the MCP server project"),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Server name (defaults to directory name)",
    ),
    description: str = typer.Option(
        "",
        "--description",
        "-d",
        help="Server description",
    ),
    port: int = typer.Option(
        8080,
        "--port",
        "-p",
        help="Port for the server",
    ),
) -> None:
    """Initialize a new MCP server project.

    Creates an MCP server project directory that can expose SkillForge
    skills as MCP tools for use with Claude Desktop and other MCP clients.

    Example:

    \b
        skillforge mcp init ./my-mcp-server
        skillforge mcp init ./server -n "my-skills" -d "Custom skills server"
    """
    from skillforge.mcp.server import init_server, MCPServerError

    try:
        project = init_server(
            server_dir=server_dir,
            name=name,
            description=description,
            port=port,
        )

        console.print()
        console.print(f"[green]✓ Created MCP server:[/green] {server_dir}")
        console.print()
        console.print("[dim]Structure:[/dim]")
        console.print(f"  {server_dir}/")
        console.print("  ├── mcp-server.yml   # Server configuration")
        console.print("  ├── tools/           # Tool definitions")
        console.print("  └── server.py        # Generated server script")
        console.print()
        console.print("[dim]Next steps:[/dim]")
        console.print(f"  skillforge mcp add {server_dir} ./skills/my-skill")
        console.print(f"  skillforge mcp serve {server_dir}")
        console.print()

        # Show MCP config snippet
        mcp_config = project.get_mcp_config()
        console.print("[dim]Add to Claude Desktop config:[/dim]")
        import json
        config_json = json.dumps(mcp_config, indent=2)
        from rich.syntax import Syntax
        console.print(Syntax(config_json, "json", theme="monokai"))

    except MCPServerError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@mcp_app.command("add")
def mcp_add(
    server_dir: Path = typer.Argument(..., help="Path to MCP server directory"),
    skill_path: Path = typer.Argument(..., help="Path to skill directory"),
) -> None:
    """Add a skill to an MCP server.

    Converts the skill to an MCP tool and adds it to the server.
    The server script is automatically regenerated.

    Example:

    \b
        skillforge mcp add ./my-server ./skills/code-reviewer
        skillforge mcp add ./my-server ./skills/doc-generator
    """
    from skillforge.mcp.server import add_skill_to_server, MCPServerError

    try:
        tool = add_skill_to_server(server_dir, skill_path)

        console.print()
        console.print(f"[green]✓ Added tool:[/green] {tool.name}")
        console.print(f"[dim]Description:[/dim] {tool.description}")
        console.print()
        console.print(f"[dim]Server updated: {server_dir}[/dim]")
        console.print()
        console.print(f"[dim]Run server: skillforge mcp serve {server_dir}[/dim]")

    except MCPServerError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@mcp_app.command("remove")
def mcp_remove(
    server_dir: Path = typer.Argument(..., help="Path to MCP server directory"),
    tool_name: str = typer.Argument(..., help="Name of tool to remove"),
) -> None:
    """Remove a tool from an MCP server.

    Example:

    \b
        skillforge mcp remove ./my-server code-reviewer
    """
    from skillforge.mcp.server import remove_tool_from_server, MCPServerError

    try:
        removed = remove_tool_from_server(server_dir, tool_name)

        if removed:
            console.print(f"[green]✓ Removed tool:[/green] {tool_name}")
        else:
            console.print(f"[yellow]Tool not found:[/yellow] {tool_name}")
            raise typer.Exit(code=1)

    except MCPServerError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@mcp_app.command("list")
def mcp_list(
    server_dir: Path = typer.Argument(..., help="Path to MCP server directory"),
) -> None:
    """List tools in an MCP server.

    Example:

    \b
        skillforge mcp list ./my-server
    """
    from skillforge.mcp.server import list_server_tools, MCPServerError

    try:
        tools = list_server_tools(server_dir)

        if not tools:
            console.print("[dim]No tools in server[/dim]")
            return

        console.print()
        console.print(f"[bold]Tools in {server_dir}:[/bold]")
        console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("Tool", style="cyan")
        table.add_column("Description")
        table.add_column("Parameters", style="dim")

        for tool in tools:
            param_count = len(tool.parameters)
            param_str = f"{param_count} param(s)"
            table.add_row(tool.name, tool.description[:50] + "..." if len(tool.description) > 50 else tool.description, param_str)

        console.print(table)
        console.print()
        console.print(f"[dim]Total: {len(tools)} tool(s)[/dim]")

    except MCPServerError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@mcp_app.command("serve")
def mcp_serve(
    server_dir: Path = typer.Argument(..., help="Path to MCP server directory"),
) -> None:
    """Run an MCP server.

    Starts the MCP server using stdio transport. This is typically
    called by MCP clients like Claude Desktop.

    Example:

    \b
        skillforge mcp serve ./my-server
    """
    from skillforge.mcp.server import run_server, MCPServerError

    try:
        console.print(f"[dim]Starting MCP server: {server_dir}[/dim]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        console.print()

        process = run_server(server_dir)

        try:
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            console.print()
            console.print("[dim]Server stopped[/dim]")

    except MCPServerError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@mcp_app.command("discover")
def mcp_discover(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to MCP config file (defaults to Claude Desktop config)",
    ),
    server_name: Optional[str] = typer.Option(
        None,
        "--server",
        "-s",
        help="Only query specific server",
    ),
) -> None:
    """Discover tools from configured MCP servers.

    Lists all tools available from MCP servers defined in a config file.
    By default, uses Claude Desktop's config file.

    Example:

    \b
        skillforge mcp discover
        skillforge mcp discover --config ./my-config.json
        skillforge mcp discover --server my-server
    """
    from skillforge.mcp.client import (
        discover_tools_from_config,
        get_claude_desktop_config_path,
        list_configured_servers,
        MCPClientError,
    )

    # Get config path
    if config_path is None:
        config_path = get_claude_desktop_config_path()
        if config_path is None:
            console.print("[yellow]Claude Desktop config not found[/yellow]")
            console.print("[dim]Specify config with --config[/dim]")
            raise typer.Exit(code=1)

    console.print(f"[dim]Using config: {config_path}[/dim]")
    console.print()

    # List servers
    servers = list_configured_servers(config_path)
    if not servers:
        console.print("[yellow]No MCP servers configured[/yellow]")
        return

    console.print(f"[bold]Configured servers:[/bold]")
    for server in servers:
        console.print(f"  • {server.name}")
    console.print()

    # Discover tools
    try:
        console.print("[dim]Querying servers for tools...[/dim]")
        tools = discover_tools_from_config(config_path, server_name)

        if not tools:
            console.print("[yellow]No tools found[/yellow]")
            return

        console.print()
        console.print(f"[bold]Discovered tools:[/bold]")
        console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("Tool", style="cyan")
        table.add_column("Server", style="dim")
        table.add_column("Description")

        for tool in tools:
            desc = tool.description[:40] + "..." if len(tool.description) > 40 else tool.description
            table.add_row(tool.name, tool.server_name, desc)

        console.print(table)
        console.print()
        console.print(f"[dim]Total: {len(tools)} tool(s)[/dim]")
        console.print()
        console.print("[dim]Import a tool: skillforge mcp import <tool-name> -o ./skills[/dim]")

    except MCPClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@mcp_app.command("import")
def mcp_import(
    tool_name: str = typer.Argument(..., help="Name of tool to import"),
    output_dir: Path = typer.Option(
        DEFAULT_SKILLS_DIR,
        "--out",
        "-o",
        help="Output directory for the skill",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to MCP config file",
    ),
    server_name: Optional[str] = typer.Option(
        None,
        "--server",
        "-s",
        help="Server to import from",
    ),
) -> None:
    """Import an MCP tool as a SkillForge skill.

    Converts an MCP tool definition to a skill and saves it locally.

    Example:

    \b
        skillforge mcp import read-file -o ./skills
        skillforge mcp import my-tool --server my-server
    """
    from skillforge.mcp.client import (
        import_tool_by_name,
        get_claude_desktop_config_path,
        MCPClientError,
    )

    # Get config path
    if config_path is None:
        config_path = get_claude_desktop_config_path()
        if config_path is None:
            console.print("[yellow]Claude Desktop config not found[/yellow]")
            console.print("[dim]Specify config with --config[/dim]")
            raise typer.Exit(code=1)

    try:
        console.print(f"[dim]Searching for tool: {tool_name}[/dim]")

        skill_dir = import_tool_by_name(
            tool_name=tool_name,
            config_path=config_path,
            output_dir=output_dir,
            server_name=server_name,
        )

        console.print()
        console.print(f"[green]✓ Imported skill:[/green] {skill_dir}")
        console.print()
        console.print("[dim]Next steps:[/dim]")
        console.print(f"  skillforge validate {skill_dir}")
        console.print(f"  skillforge install {skill_dir}")

    except MCPClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@mcp_app.command("config")
def mcp_config(
    server_dir: Path = typer.Argument(..., help="Path to MCP server directory"),
) -> None:
    """Show MCP client configuration for a server.

    Outputs the JSON configuration snippet that can be added to
    Claude Desktop's config file or other MCP clients.

    Example:

    \b
        skillforge mcp config ./my-server
    """
    from skillforge.mcp.server import load_server, MCPServerError
    import json

    try:
        project = load_server(server_dir)
        mcp_config = project.get_mcp_config()

        console.print()
        console.print("[bold]Add to Claude Desktop config:[/bold]")
        console.print()

        config_json = json.dumps(mcp_config, indent=2)
        from rich.syntax import Syntax
        console.print(Syntax(config_json, "json", theme="monokai"))

        console.print()
        console.print("[dim]Config location:[/dim]")
        console.print("  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json")
        console.print("  Windows: %APPDATA%/Claude/claude_desktop_config.json")
        console.print("  Linux: ~/.config/Claude/claude_desktop_config.json")

    except MCPServerError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# Security Commands (v0.11.0)
# =============================================================================

security_app = typer.Typer(
    name="security",
    help="Security scanning and vulnerability detection.",
    no_args_is_help=True,
)
app.add_typer(security_app, name="security")


@security_app.command("scan")
def security_scan(
    skill_path: Path = typer.Argument(..., help="Path to skill directory"),
    min_severity: str = typer.Option(
        "info",
        "--min-severity",
        "-s",
        help="Minimum severity to report (critical, high, medium, low, info)",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format (text, json)",
    ),
    exclude: Optional[list[str]] = typer.Option(
        None,
        "--exclude",
        "-e",
        help="Pattern names to exclude",
    ),
) -> None:
    """Scan a skill for security vulnerabilities.

    Checks skill content for prompt injection, credential exposure,
    data exfiltration risks, and other security issues.

    Example:

    \b
        skillforge security scan ./skills/my-skill
        skillforge security scan ./skills/my-skill --min-severity medium
        skillforge security scan ./skills/my-skill --format json
    """
    from skillforge.security import scan_skill, Severity, get_risk_level, SecurityScanError

    # Parse severity
    try:
        severity = Severity(min_severity.lower())
    except ValueError:
        console.print(f"[red]Invalid severity:[/red] {min_severity}")
        console.print("[dim]Valid options: critical, high, medium, low, info[/dim]")
        raise typer.Exit(code=1)

    try:
        result = scan_skill(
            skill_path,
            min_severity=severity,
            exclude_patterns=exclude or [],
        )

        if output_format == "json":
            console.print(result.to_json())
            raise typer.Exit(code=0 if result.passed else 1)

        # Text output
        console.print()
        console.print(f"[bold]Security Scan: {result.skill_name}[/bold]")
        console.print()

        # Summary
        risk_level = get_risk_level(result.risk_score)
        risk_color = {
            "none": "green",
            "low": "green",
            "medium": "yellow",
            "high": "red",
            "critical": "red bold",
        }.get(risk_level, "white")

        console.print(f"Risk Score: [{risk_color}]{result.risk_score}/100 ({risk_level})[/{risk_color}]")
        console.print(f"Scan Duration: {result.scan_duration_ms:.1f}ms")
        console.print()

        # Findings summary
        console.print("[bold]Summary:[/bold]")
        console.print(f"  Critical: {result.critical_count}")
        console.print(f"  High: {result.high_count}")
        console.print(f"  Medium: {result.medium_count}")
        console.print(f"  Low: {result.low_count}")
        console.print(f"  Info: {result.info_count}")
        console.print()

        # Findings details
        if result.findings:
            console.print("[bold]Findings:[/bold]")
            console.print()

            for finding in result.findings:
                severity_color = {
                    "critical": "red bold",
                    "high": "red",
                    "medium": "yellow",
                    "low": "blue",
                    "info": "dim",
                }.get(finding.severity.value, "white")

                console.print(f"  [{severity_color}]{finding.severity.value.upper()}[/{severity_color}] {finding.description}")
                console.print(f"    [dim]Pattern:[/dim] {finding.pattern_name}")
                if finding.line_number:
                    console.print(f"    [dim]Line:[/dim] {finding.line_number}")
                console.print(f"    [dim]Matched:[/dim] {finding.matched_text[:60]}{'...' if len(finding.matched_text) > 60 else ''}")
                console.print(f"    [dim]Fix:[/dim] {finding.recommendation}")
                console.print()

        # Result
        if result.passed:
            console.print("[green]✓ Security scan passed[/green]")
        else:
            console.print("[red]✗ Security scan failed[/red]")
            raise typer.Exit(code=1)

    except SecurityScanError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@security_app.command("patterns")
def security_patterns(
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        "-s",
        help="Filter by severity",
    ),
    issue_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by issue type",
    ),
) -> None:
    """List available security patterns.

    Shows all patterns used for security scanning.

    Example:

    \b
        skillforge security patterns
        skillforge security patterns --severity critical
        skillforge security patterns --type prompt_injection
    """
    from skillforge.security import SECURITY_PATTERNS, Severity, SecurityIssueType

    patterns = SECURITY_PATTERNS

    # Filter by severity
    if severity:
        try:
            sev = Severity(severity.lower())
            patterns = [p for p in patterns if p.severity == sev]
        except ValueError:
            console.print(f"[red]Invalid severity:[/red] {severity}")
            raise typer.Exit(code=1)

    # Filter by type
    if issue_type:
        try:
            itype = SecurityIssueType(issue_type.lower())
            patterns = [p for p in patterns if p.issue_type == itype]
        except ValueError:
            console.print(f"[red]Invalid issue type:[/red] {issue_type}")
            raise typer.Exit(code=1)

    if not patterns:
        console.print("[yellow]No patterns match the filters[/yellow]")
        return

    console.print()
    console.print(f"[bold]Security Patterns ({len(patterns)}):[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Severity")
    table.add_column("Type", style="dim")
    table.add_column("Description")

    for p in patterns:
        severity_color = {
            "critical": "red",
            "high": "red",
            "medium": "yellow",
            "low": "blue",
            "info": "dim",
        }.get(p.severity.value, "white")

        table.add_row(
            p.name,
            f"[{severity_color}]{p.severity.value}[/{severity_color}]",
            p.issue_type.value,
            p.description[:40] + "..." if len(p.description) > 40 else p.description,
        )

    console.print(table)


# =============================================================================
# Governance Commands (v0.11.0)
# =============================================================================

governance_app = typer.Typer(
    name="governance",
    help="Enterprise governance and policy management.",
    no_args_is_help=True,
)
app.add_typer(governance_app, name="governance")


@governance_app.command("trust")
def governance_trust(
    skill_path: Path = typer.Argument(..., help="Path to skill directory"),
    set_tier: Optional[str] = typer.Option(
        None,
        "--set",
        "-s",
        help="Set trust tier (untrusted, community, verified, enterprise)",
    ),
    verified_by: Optional[str] = typer.Option(
        None,
        "--by",
        "-b",
        help="Who is setting the trust tier",
    ),
) -> None:
    """View or set trust tier for a skill.

    Trust tiers indicate the level of verification and trust for a skill:
    - untrusted: Unknown source, not verified
    - community: Community-contributed, basic checks
    - verified: Verified publisher, security scanned
    - enterprise: Enterprise-approved, full audit

    Example:

    \b
        skillforge governance trust ./skills/my-skill
        skillforge governance trust ./skills/my-skill --set verified --by admin
    """
    from skillforge.governance import (
        TrustTier,
        get_trust_metadata,
        set_trust_tier,
        get_trust_tier_description,
        log_trust_changed,
    )

    skill_path = Path(skill_path)

    if not skill_path.exists():
        console.print(f"[red]Skill not found:[/red] {skill_path}")
        raise typer.Exit(code=1)

    if set_tier:
        # Set trust tier
        try:
            tier = TrustTier[set_tier.upper()]
        except KeyError:
            console.print(f"[red]Invalid trust tier:[/red] {set_tier}")
            console.print("[dim]Valid tiers: untrusted, community, verified, enterprise[/dim]")
            raise typer.Exit(code=1)

        old_metadata = get_trust_metadata(skill_path)
        old_tier = old_metadata.tier.name.lower()

        metadata = set_trust_tier(skill_path, tier, verified_by=verified_by)

        # Log the change
        log_trust_changed(
            skill_name=skill_path.name,
            old_tier=old_tier,
            new_tier=tier.name.lower(),
            actor=verified_by,
        )

        console.print()
        console.print(f"[green]✓ Trust tier set to:[/green] {tier.name.lower()}")
        if verified_by:
            console.print(f"[dim]Verified by: {verified_by}[/dim]")
    else:
        # Show trust tier
        metadata = get_trust_metadata(skill_path)

        console.print()
        console.print(f"[bold]Trust Status: {skill_path.name}[/bold]")
        console.print()

        tier_color = {
            TrustTier.UNTRUSTED: "red",
            TrustTier.COMMUNITY: "yellow",
            TrustTier.VERIFIED: "green",
            TrustTier.ENTERPRISE: "cyan bold",
        }.get(metadata.tier, "white")

        console.print(f"Tier: [{tier_color}]{metadata.tier.name.lower()}[/{tier_color}]")
        console.print(f"Description: {get_trust_tier_description(metadata.tier)}")

        if metadata.verified_at:
            console.print(f"Verified: {metadata.verified_at.strftime('%Y-%m-%d %H:%M')}")
        if metadata.verified_by:
            console.print(f"Verified by: {metadata.verified_by}")
        if metadata.security_scan_passed is not None:
            status = "[green]passed[/green]" if metadata.security_scan_passed else "[red]failed[/red]"
            console.print(f"Security scan: {status}")
        if metadata.approval_id:
            console.print(f"Approval ID: {metadata.approval_id}")


@governance_app.command("policy")
def governance_policy(
    action: str = typer.Argument(..., help="Action: list, show, create, delete"),
    name: Optional[str] = typer.Argument(None, help="Policy name"),
    description: str = typer.Option("", "--description", "-d", help="Policy description"),
    min_trust: str = typer.Option("untrusted", "--min-trust", help="Minimum trust tier"),
    max_risk: int = typer.Option(100, "--max-risk", help="Maximum risk score"),
    require_scan: bool = typer.Option(False, "--require-scan", help="Require security scan"),
    require_approval: bool = typer.Option(False, "--require-approval", help="Require approval"),
) -> None:
    """Manage governance policies.

    Policies control which skills can be used in different environments.

    Actions:
    - list: Show all policies
    - show <name>: Show policy details
    - create <name>: Create a new policy
    - delete <name>: Delete a custom policy

    Example:

    \b
        skillforge governance policy list
        skillforge governance policy show production
        skillforge governance policy create staging --min-trust community --max-risk 50
        skillforge governance policy delete my-policy
    """
    from skillforge.governance import (
        TrustTier,
        TrustPolicy,
        list_policies,
        load_policy,
        save_policy,
        delete_policy,
        PolicyError,
        BUILTIN_POLICIES,
    )

    if action == "list":
        policies = list_policies()

        console.print()
        console.print(f"[bold]Governance Policies ({len(policies)}):[/bold]")
        console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="dim")
        table.add_column("Min Trust")
        table.add_column("Max Risk")
        table.add_column("Scan")
        table.add_column("Approval")

        for p in policies:
            policy_type = "built-in" if p.name in BUILTIN_POLICIES else "custom"
            table.add_row(
                p.name,
                policy_type,
                p.min_trust_tier.name.lower(),
                str(p.max_risk_score),
                "yes" if p.require_security_scan else "no",
                "yes" if p.approval_required else "no",
            )

        console.print(table)

    elif action == "show":
        if not name:
            console.print("[red]Policy name required[/red]")
            raise typer.Exit(code=1)

        try:
            policy = load_policy(name)
        except PolicyError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

        console.print()
        console.print(f"[bold]Policy: {policy.name}[/bold]")
        console.print()
        console.print(f"Description: {policy.description or '(none)'}")
        console.print(f"Min Trust Tier: {policy.min_trust_tier.name.lower()}")
        console.print(f"Max Risk Score: {policy.max_risk_score}")
        console.print(f"Require Security Scan: {'yes' if policy.require_security_scan else 'no'}")
        console.print(f"Require Approval: {'yes' if policy.approval_required else 'no'}")

        if policy.min_severity_block:
            console.print(f"Block Severity: {policy.min_severity_block.value}+")
        if policy.blocked_patterns:
            console.print(f"Blocked Patterns: {', '.join(policy.blocked_patterns)}")
        if policy.allowed_sources:
            console.print(f"Allowed Sources: {', '.join(policy.allowed_sources)}")

    elif action == "create":
        if not name:
            console.print("[red]Policy name required[/red]")
            raise typer.Exit(code=1)

        if name in BUILTIN_POLICIES:
            console.print(f"[red]Cannot override built-in policy:[/red] {name}")
            raise typer.Exit(code=1)

        try:
            tier = TrustTier[min_trust.upper()]
        except KeyError:
            console.print(f"[red]Invalid trust tier:[/red] {min_trust}")
            raise typer.Exit(code=1)

        policy = TrustPolicy(
            name=name,
            description=description,
            min_trust_tier=tier,
            max_risk_score=max_risk,
            require_security_scan=require_scan,
            approval_required=require_approval,
        )

        save_policy(policy)
        console.print(f"[green]✓ Created policy:[/green] {name}")

    elif action == "delete":
        if not name:
            console.print("[red]Policy name required[/red]")
            raise typer.Exit(code=1)

        try:
            if delete_policy(name):
                console.print(f"[green]✓ Deleted policy:[/green] {name}")
            else:
                console.print(f"[yellow]Policy not found:[/yellow] {name}")
        except PolicyError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

    else:
        console.print(f"[red]Unknown action:[/red] {action}")
        console.print("[dim]Valid actions: list, show, create, delete[/dim]")
        raise typer.Exit(code=1)


@governance_app.command("check")
def governance_check(
    skill_path: Path = typer.Argument(..., help="Path to skill directory"),
    policy_name: str = typer.Option(
        "development",
        "--policy",
        "-p",
        help="Policy to check against",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format (text, json)",
    ),
) -> None:
    """Check a skill against a governance policy.

    Verifies that a skill meets the requirements of a policy.

    Example:

    \b
        skillforge governance check ./skills/my-skill
        skillforge governance check ./skills/my-skill --policy production
        skillforge governance check ./skills/my-skill --format json
    """
    from skillforge.governance import (
        check_policy,
        load_policy,
        log_policy_check,
        PolicyError,
    )
    import json

    try:
        policy = load_policy(policy_name)
    except PolicyError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    result = check_policy(skill_path, policy)

    # Log the check
    log_policy_check(
        skill_name=result.skill_name,
        policy_name=policy_name,
        passed=result.passed,
        violations=result.violations,
    )

    if output_format == "json":
        console.print(json.dumps(result.to_dict(), indent=2))
        raise typer.Exit(code=0 if result.passed else 1)

    console.print()
    console.print(f"[bold]Policy Check: {result.skill_name}[/bold]")
    console.print(f"Policy: {policy_name}")
    console.print()

    if result.violations:
        console.print("[red]Violations:[/red]")
        for v in result.violations:
            console.print(f"  [red]✗[/red] {v}")
        console.print()

    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]![/yellow] {w}")
        console.print()

    if result.passed:
        console.print("[green]✓ Skill meets policy requirements[/green]")
    else:
        console.print("[red]✗ Skill violates policy[/red]")
        raise typer.Exit(code=1)


@governance_app.command("audit")
def governance_audit(
    skill_name: Optional[str] = typer.Option(
        None,
        "--skill",
        "-s",
        help="Filter by skill name",
    ),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD)",
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD)",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum events to show",
    ),
    summary: bool = typer.Option(
        False,
        "--summary",
        help="Show summary instead of events",
    ),
) -> None:
    """View audit trail for skills.

    Shows the history of skill lifecycle events including creation,
    modification, security scans, and policy checks.

    Example:

    \b
        skillforge governance audit
        skillforge governance audit --skill my-skill
        skillforge governance audit --from 2026-01-01 --to 2026-01-31
        skillforge governance audit --summary
    """
    from datetime import datetime
    from skillforge.governance import (
        AuditQuery,
        query_events,
        get_audit_summary,
    )

    # Parse dates
    from_dt = None
    to_dt = None

    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        except ValueError:
            console.print(f"[red]Invalid date format:[/red] {from_date}")
            console.print("[dim]Use YYYY-MM-DD format[/dim]")
            raise typer.Exit(code=1)

    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            console.print(f"[red]Invalid date format:[/red] {to_date}")
            raise typer.Exit(code=1)

    if summary:
        # Show summary
        audit_summary = get_audit_summary(from_dt, to_dt)

        console.print()
        console.print("[bold]Audit Summary[/bold]")
        console.print()
        console.print(f"Total Events: {audit_summary.total_events}")

        if audit_summary.date_range[0]:
            console.print(f"Date Range: {audit_summary.date_range[0].strftime('%Y-%m-%d')} to {audit_summary.date_range[1].strftime('%Y-%m-%d')}")

        if audit_summary.events_by_type:
            console.print()
            console.print("[bold]By Event Type:[/bold]")
            for event_type, count in sorted(audit_summary.events_by_type.items(), key=lambda x: -x[1]):
                console.print(f"  {event_type}: {count}")

        if audit_summary.events_by_skill:
            console.print()
            console.print("[bold]By Skill:[/bold]")
            for name, count in sorted(audit_summary.events_by_skill.items(), key=lambda x: -x[1])[:10]:
                console.print(f"  {name}: {count}")

        return

    # Query events
    query = AuditQuery(
        skill_name=skill_name,
        from_date=from_dt,
        to_date=to_dt,
        limit=limit,
    )
    events = query_events(query)

    if not events:
        console.print("[dim]No audit events found[/dim]")
        return

    console.print()
    console.print(f"[bold]Audit Events ({len(events)}):[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Timestamp", style="dim")
    table.add_column("Event", style="cyan")
    table.add_column("Skill")
    table.add_column("Actor")
    table.add_column("Details", style="dim")

    for event in events:
        details = ""
        if event.details:
            detail_items = [f"{k}={v}" for k, v in list(event.details.items())[:2]]
            details = ", ".join(detail_items)[:30]

        table.add_row(
            event.timestamp.strftime("%Y-%m-%d %H:%M"),
            event.event_type.value,
            event.skill_name,
            event.actor,
            details,
        )

    console.print(table)


@governance_app.command("approve")
def governance_approve(
    skill_path: Path = typer.Argument(..., help="Path to skill directory"),
    tier: str = typer.Option(
        "enterprise",
        "--tier",
        "-t",
        help="Trust tier to approve for",
    ),
    approver: Optional[str] = typer.Option(
        None,
        "--by",
        "-b",
        help="Approver name",
    ),
    notes: str = typer.Option(
        "",
        "--notes",
        "-n",
        help="Approval notes",
    ),
) -> None:
    """Approve a skill for a trust tier.

    Records formal approval with audit trail.

    Example:

    \b
        skillforge governance approve ./skills/my-skill --tier enterprise --by admin
    """
    import uuid
    from skillforge.governance import (
        TrustTier,
        get_trust_metadata,
        set_trust_metadata,
        log_approval,
        get_current_actor,
    )
    from datetime import datetime

    skill_path = Path(skill_path)

    if not skill_path.exists():
        console.print(f"[red]Skill not found:[/red] {skill_path}")
        raise typer.Exit(code=1)

    try:
        trust_tier = TrustTier[tier.upper()]
    except KeyError:
        console.print(f"[red]Invalid trust tier:[/red] {tier}")
        raise typer.Exit(code=1)

    # Get current metadata
    metadata = get_trust_metadata(skill_path)

    # Generate approval ID
    approval_id = f"APR-{uuid.uuid4().hex[:8].upper()}"

    # Update metadata
    metadata.tier = trust_tier
    metadata.approval_id = approval_id
    metadata.verified_at = datetime.now()
    metadata.verified_by = approver or get_current_actor()
    metadata.notes = notes

    set_trust_metadata(skill_path, metadata)

    # Log the approval
    log_approval(
        skill_name=skill_path.name,
        approval_id=approval_id,
        tier=tier,
        actor=approver,
    )

    console.print()
    console.print(f"[green]✓ Skill approved[/green]")
    console.print(f"  Approval ID: {approval_id}")
    console.print(f"  Trust Tier: {trust_tier.name.lower()}")
    console.print(f"  Approved by: {metadata.verified_by}")
    if notes:
        console.print(f"  Notes: {notes}")


# =============================================================================
# Publish Commands (v0.12.0)
# =============================================================================

@app.command("publish")
def publish(
    skill_path: Path = typer.Argument(..., help="Path to skill directory"),
    platform: str = typer.Option(
        "claude",
        "--platform",
        "-p",
        help="Target platform (claude, openai, langchain)",
    ),
    mode: Optional[str] = typer.Option(
        None,
        "--mode",
        "-m",
        help="Publish mode (platform-specific)",
    ),
    output_dir: Path = typer.Option(
        Path("."),
        "--out",
        "-o",
        help="Output directory for generated files",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for platform (if required)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate without publishing",
    ),
    all_platforms: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Publish to all platforms",
    ),
) -> None:
    """Publish a skill to an AI platform.

    Transforms and publishes skills to various platforms:
    - claude: Claude.ai Projects, API, or Claude Code
    - openai: Custom GPTs, API, or Assistants
    - langchain: Prompt templates, Hub, or Python modules

    Example:

    \b
        skillforge publish ./skills/my-skill
        skillforge publish ./skills/my-skill --platform openai --mode gpt
        skillforge publish ./skills/my-skill --all --out ./published
        skillforge publish ./skills/my-skill --dry-run
    """
    from skillforge.platforms import (
        Platform,
        get_platform,
        publish_skill,
        publish_to_all,
        PublishError,
    )

    skill_path = Path(skill_path)

    if not skill_path.exists():
        console.print(f"[red]Skill not found:[/red] {skill_path}")
        raise typer.Exit(code=1)

    if all_platforms:
        # Publish to all platforms
        console.print(f"[dim]Publishing to all platforms...[/dim]")
        console.print()

        results = publish_to_all(skill_path, output_dir, dry_run)

        for plat, result in results.items():
            if result.published_id == "error":
                console.print(f"[red]✗ {plat.value}:[/red] {result.metadata.get('error')}")
            else:
                console.print(f"[green]✓ {plat.value}:[/green] {result.published_id}")
                if result.url:
                    console.print(f"  [dim]{result.url}[/dim]")

        return

    # Single platform publish
    try:
        plat = get_platform(platform)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    try:
        console.print(f"[dim]Publishing to {platform}...[/dim]")

        result = publish_skill(
            skill_path=skill_path,
            platform=plat,
            api_key=api_key,
            mode=mode,
            output_dir=output_dir,
            dry_run=dry_run,
        )

        console.print()
        if dry_run:
            console.print(f"[yellow]Dry run completed[/yellow]")
        else:
            console.print(f"[green]✓ Published to {platform}[/green]")

        console.print(f"  ID: {result.published_id}")
        if result.version:
            console.print(f"  Version: {result.version}")
        if result.url:
            console.print(f"  Location: {result.url}")

        # Show platform-specific instructions
        if "instructions" in result.metadata:
            console.print()
            console.print(f"[dim]{result.metadata['instructions']}[/dim]")

    except PublishError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("platforms")
def platforms_list() -> None:
    """List available publishing platforms.

    Shows all platforms that skills can be published to.
    """
    from skillforge.platforms import list_adapters

    console.print()
    console.print("[bold]Available Platforms:[/bold]")
    console.print()

    for adapter in list_adapters():
        console.print(f"[cyan]{adapter.platform.value}[/cyan]")
        console.print(f"  {adapter.platform_name}")
        console.print(f"  {adapter.platform_description}")
        console.print(f"  Features: {', '.join(adapter.supported_features[:4])}")
        console.print()


# =============================================================================
# Analytics Commands (v0.12.0)
# =============================================================================

analytics_app = typer.Typer(
    name="analytics",
    help="Usage tracking and analytics.",
    no_args_is_help=True,
)
app.add_typer(analytics_app, name="analytics")


@analytics_app.command("show")
def analytics_show(
    skill_name: str = typer.Argument(..., help="Name of skill to show analytics for"),
    period: int = typer.Option(
        30,
        "--period",
        "-p",
        help="Number of days to analyze",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format (text, json)",
    ),
) -> None:
    """Show analytics for a skill.

    Displays usage metrics including invocations, success rate,
    latency, and costs.

    Example:

    \b
        skillforge analytics show code-reviewer
        skillforge analytics show code-reviewer --period 7
        skillforge analytics show code-reviewer --format json
    """
    from skillforge.analytics import get_skill_metrics
    import json

    metrics = get_skill_metrics(skill_name, period_days=period)

    if output_format == "json":
        console.print(json.dumps(metrics.to_dict(), indent=2))
        return

    console.print()
    console.print(f"[bold]Analytics: {skill_name}[/bold]")
    console.print(f"[dim]Period: Last {period} days[/dim]")
    console.print()

    if metrics.total_invocations == 0:
        console.print("[yellow]No invocations recorded[/yellow]")
        return

    # Metrics table
    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    table.add_row("Total Invocations", str(metrics.total_invocations))
    table.add_row("Successful", f"{metrics.successful_invocations} ({metrics.success_rate:.1f}%)")
    table.add_row("Failed", str(metrics.failed_invocations))
    table.add_row("Avg Latency", f"{metrics.avg_latency_ms:.1f} ms")
    table.add_row("Total Tokens", f"{metrics.total_tokens:,}")
    table.add_row("Total Cost", f"${metrics.total_cost:.2f}")
    table.add_row("Avg Cost/Invocation", f"${metrics.avg_cost:.4f}")

    if metrics.first_invocation:
        table.add_row("First Invocation", metrics.first_invocation.strftime("%Y-%m-%d %H:%M"))
    if metrics.last_invocation:
        table.add_row("Last Invocation", metrics.last_invocation.strftime("%Y-%m-%d %H:%M"))

    console.print(table)


@analytics_app.command("roi")
def analytics_roi(
    skill_name: str = typer.Argument(..., help="Name of skill to calculate ROI for"),
    period: int = typer.Option(
        30,
        "--period",
        "-p",
        help="Number of days to analyze",
    ),
    time_saved: float = typer.Option(
        5.0,
        "--time-saved",
        "-t",
        help="Minutes saved per invocation",
    ),
    hourly_rate: float = typer.Option(
        50.0,
        "--rate",
        "-r",
        help="Hourly rate for value calculation (USD)",
    ),
) -> None:
    """Calculate ROI for a skill.

    Estimates return on investment based on time saved
    and API costs.

    Example:

    \b
        skillforge analytics roi code-reviewer
        skillforge analytics roi code-reviewer --time-saved 10 --rate 75
    """
    from skillforge.analytics import calculate_roi

    roi = calculate_roi(
        skill_name=skill_name,
        period_days=period,
        time_saved_minutes=time_saved,
        hourly_rate=hourly_rate,
    )

    console.print()
    console.print(f"[bold]ROI Analysis: {skill_name}[/bold]")
    console.print(f"[dim]Period: Last {period} days[/dim]")
    console.print()

    if roi.total_invocations == 0:
        console.print("[yellow]No invocations recorded[/yellow]")
        return

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    table.add_row("Total Invocations", str(roi.total_invocations))
    table.add_row("Time Saved", f"{roi.estimated_time_saved_hours:.1f} hours")
    table.add_row("Value of Time Saved", f"${roi.estimated_value:.2f}")
    table.add_row("API Costs", f"${roi.total_cost:.2f}")
    table.add_row("Net Value", f"${roi.net_value:.2f}")

    roi_str = f"{roi.roi_percentage:.1f}%" if roi.roi_percentage != float("inf") else "∞"
    roi_color = "green" if roi.roi_percentage > 0 else "red"
    table.add_row("ROI", f"[{roi_color}]{roi_str}[/{roi_color}]")

    console.print(table)
    console.print()
    console.print(f"[dim]Assumptions: {time_saved} min saved/invocation, ${hourly_rate}/hour[/dim]")


@analytics_app.command("report")
def analytics_report(
    period: int = typer.Option(
        30,
        "--period",
        "-p",
        help="Number of days to include",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format (text, json)",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Save report to file",
    ),
) -> None:
    """Generate a usage report for all skills.

    Shows aggregate metrics across all tracked skills.

    Example:

    \b
        skillforge analytics report
        skillforge analytics report --period 7
        skillforge analytics report --format json --out report.json
    """
    from skillforge.analytics import generate_usage_report
    import json

    report = generate_usage_report(period_days=period)

    if output_format == "json":
        json_output = report.to_json()
        if output_file:
            output_file.write_text(json_output)
            console.print(f"[green]✓ Report saved to:[/green] {output_file}")
        else:
            console.print(json_output)
        return

    console.print()
    console.print("[bold]Usage Report[/bold]")
    console.print(f"[dim]Period: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}[/dim]")
    console.print()

    # Summary
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Total Invocations: {report.total_invocations:,}")
    console.print(f"  Total Cost: ${report.total_cost:.2f}")
    console.print(f"  Total Tokens: {report.total_tokens:,}")
    console.print(f"  Skills Tracked: {len(report.skill_metrics)}")
    console.print()

    # Status breakdown
    if report.status_breakdown:
        console.print("[bold]By Status:[/bold]")
        for status, count in report.status_breakdown.items():
            pct = (count / report.total_invocations * 100) if report.total_invocations > 0 else 0
            console.print(f"  {status}: {count} ({pct:.1f}%)")
        console.print()

    # Top skills
    if report.top_skills:
        console.print("[bold]Top Skills:[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Skill", style="cyan")
        table.add_column("Invocations", justify="right")
        table.add_column("Success Rate", justify="right")
        table.add_column("Cost", justify="right")

        for name, count in report.top_skills[:5]:
            metrics = report.skill_metrics.get(name)
            if metrics:
                table.add_row(
                    name,
                    str(count),
                    f"{metrics.success_rate:.1f}%",
                    f"${metrics.total_cost:.2f}",
                )

        console.print(table)


@analytics_app.command("cost")
def analytics_cost(
    skill_name: Optional[str] = typer.Argument(None, help="Skill name (optional, for all skills if omitted)"),
    period: int = typer.Option(
        30,
        "--period",
        "-p",
        help="Number of days to analyze",
    ),
) -> None:
    """Show cost breakdown for skills.

    Displays detailed cost analysis including breakdown by model and day.

    Example:

    \b
        skillforge analytics cost
        skillforge analytics cost code-reviewer
        skillforge analytics cost --period 7
    """
    from skillforge.analytics import generate_cost_breakdown

    breakdown = generate_cost_breakdown(skill_name=skill_name, period_days=period)

    console.print()
    title = f"Cost Breakdown: {skill_name}" if skill_name else "Cost Breakdown: All Skills"
    console.print(f"[bold]{title}[/bold]")
    console.print(f"[dim]Period: Last {period} days[/dim]")
    console.print()

    if breakdown.total_cost == 0:
        console.print("[yellow]No costs recorded[/yellow]")
        return

    console.print(f"[bold]Total Cost:[/bold] ${breakdown.total_cost:.4f}")
    console.print(f"  Input Tokens: ${breakdown.input_cost:.4f}")
    console.print(f"  Output Tokens: ${breakdown.output_cost:.4f}")
    console.print(f"  Avg per Invocation: ${breakdown.avg_cost_per_invocation:.4f}")
    console.print()

    if breakdown.cost_by_model:
        console.print("[bold]By Model:[/bold]")
        for model, cost in sorted(breakdown.cost_by_model.items(), key=lambda x: -x[1]):
            console.print(f"  {model}: ${cost:.4f}")
        console.print()

    if breakdown.cost_by_day:
        console.print("[bold]Recent Days:[/bold]")
        recent_days = list(breakdown.cost_by_day.items())[-7:]
        for day, cost in recent_days:
            console.print(f"  {day}: ${cost:.4f}")


@analytics_app.command("estimate")
def analytics_estimate(
    skill_name: str = typer.Argument(..., help="Skill name"),
    daily_invocations: int = typer.Option(
        100,
        "--daily",
        "-d",
        help="Expected daily invocations",
    ),
    input_tokens: int = typer.Option(
        1000,
        "--input-tokens",
        "-i",
        help="Average input tokens per invocation",
    ),
    output_tokens: int = typer.Option(
        500,
        "--output-tokens",
        "-o",
        help="Average output tokens per invocation",
    ),
    model: str = typer.Option(
        "claude-sonnet-4-20250514",
        "--model",
        "-m",
        help="Model for cost estimation",
    ),
) -> None:
    """Estimate monthly costs for a skill.

    Projects future costs based on expected usage.

    Example:

    \b
        skillforge analytics estimate code-reviewer --daily 50
        skillforge analytics estimate my-skill --daily 200 --model gpt-4o
    """
    from skillforge.analytics import estimate_monthly_cost

    estimate = estimate_monthly_cost(
        skill_name=skill_name,
        expected_daily_invocations=daily_invocations,
        avg_input_tokens=input_tokens,
        avg_output_tokens=output_tokens,
        model=model,
    )

    console.print()
    console.print(f"[bold]Cost Estimate: {skill_name}[/bold]")
    console.print(f"[dim]Model: {model}[/dim]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Period", style="dim")
    table.add_column("Cost", justify="right")

    table.add_row("Per Invocation", f"${estimate['per_invocation']:.4f}")
    table.add_row("Daily", f"${estimate['daily_cost']:.2f}")
    table.add_row("Weekly", f"${estimate['weekly_cost']:.2f}")
    table.add_row("Monthly", f"${estimate['monthly_cost']:.2f}")

    console.print(table)
    console.print()
    console.print(f"[dim]Based on {daily_invocations} invocations/day, {input_tokens} input + {output_tokens} output tokens each[/dim]")


# =============================================================================
# Migration Commands
# =============================================================================

migrate_app = typer.Typer(help="Migrate skills between SkillForge versions")
app.add_typer(migrate_app, name="migrate")


@migrate_app.command("check")
def migrate_check(
    path: Path = typer.Argument(
        ...,
        help="Skill directory or parent directory to check",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Search recursively for skills",
    ),
) -> None:
    """Check which skills need migration.

    Scans for skills that are not at the latest format version.

    Example:

    \b
        skillforge migrate check ./skills
        skillforge migrate check ./my-skill
        skillforge migrate check . --recursive
    """
    from skillforge.migrate import (
        detect_format,
        list_migrations_needed,
        get_format_info,
        SkillFormat,
    )

    path = Path(path).resolve()

    # Single skill or directory?
    if (path / "SKILL.md").exists():
        # Single skill
        format = detect_format(path)
        format_info = get_format_info(format)

        console.print()
        console.print(f"[bold]Skill: {path.name}[/bold]")
        console.print(f"Format: {format_info['name']}")

        if format == SkillFormat.V1_0:
            console.print("[green]✓ Already at latest format[/green]")
        elif format == SkillFormat.UNKNOWN:
            console.print("[red]✗ Unknown or invalid format[/red]")
        else:
            console.print("[yellow]⚠ Migration available[/yellow]")
            console.print(f"Run: [cyan]skillforge migrate run {path}[/cyan]")
    else:
        # Directory of skills
        needs_migration = list_migrations_needed(path, recursive=recursive)

        console.print()
        if not needs_migration:
            console.print("[green]✓ All skills are at latest format[/green]")
            return

        console.print(f"[yellow]Found {len(needs_migration)} skill(s) needing migration:[/yellow]")
        console.print()

        table = Table()
        table.add_column("Skill", style="cyan")
        table.add_column("Current Format")
        table.add_column("Path", style="dim")

        for skill_path, format in needs_migration:
            format_info = get_format_info(format)
            table.add_row(skill_path.name, format_info["name"], str(skill_path))

        console.print(table)
        console.print()
        console.print(f"Run: [cyan]skillforge migrate run {path}[/cyan] to migrate all")


@migrate_app.command("run")
def migrate_run(
    path: Path = typer.Argument(
        ...,
        help="Skill directory or parent directory to migrate",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Search recursively for skills",
    ),
    no_backup: bool = typer.Option(
        False,
        "--no-backup",
        help="Skip creating backups",
    ),
    backup_dir: Optional[Path] = typer.Option(
        None,
        "--backup-dir",
        help="Directory for backups",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be changed without making changes",
    ),
) -> None:
    """Migrate skills to the latest format.

    Upgrades skill metadata to v1.0 format with full features.
    Creates backups by default (use --no-backup to skip).

    Example:

    \b
        skillforge migrate run ./my-skill
        skillforge migrate run ./skills --recursive
        skillforge migrate run ./skill --dry-run
    """
    from skillforge.migrate import (
        migrate_skill,
        migrate_directory,
        get_migration_preview,
        SkillFormat,
    )

    path = Path(path).resolve()

    # Dry run - just show preview
    if dry_run:
        if (path / "SKILL.md").exists():
            preview = get_migration_preview(path)
            console.print()
            console.print(f"[bold]Migration Preview: {path.name}[/bold]")
            console.print(f"Current: {preview['current_format']} → Target: {preview['target_format']}")
            console.print()
            if preview["planned_changes"]:
                console.print("[dim]Planned changes:[/dim]")
                for change in preview["planned_changes"]:
                    console.print(f"  • {change}")
        else:
            console.print("[yellow]Dry run for directories not yet implemented[/yellow]")
        return

    # Single skill or directory?
    if (path / "SKILL.md").exists():
        # Single skill
        result = migrate_skill(
            path,
            create_backup_flag=not no_backup,
            backup_dir=backup_dir,
        )

        console.print()
        if result.success:
            console.print(f"[green]✓ Migrated {result.skill_name}[/green]")
            if result.changes:
                console.print("[dim]Changes:[/dim]")
                for change in result.changes:
                    console.print(f"  • {change}")
            if result.backup_path:
                console.print(f"[dim]Backup: {result.backup_path}[/dim]")
        else:
            console.print(f"[red]✗ Migration failed: {result.error}[/red]")
            raise typer.Exit(1)
    else:
        # Directory of skills
        result = migrate_directory(
            path,
            create_backup_flag=not no_backup,
            backup_dir=backup_dir,
            recursive=recursive,
        )

        console.print()
        console.print(f"[bold]Migration Complete[/bold]")
        console.print(f"Total: {result.total}")
        console.print(f"[green]Successful: {result.successful}[/green]")
        console.print(f"[yellow]Skipped: {result.skipped}[/yellow]")
        console.print(f"[red]Failed: {result.failed}[/red]")

        if result.failed > 0:
            console.print()
            console.print("[red]Failed migrations:[/red]")
            for r in result.results:
                if not r.success:
                    console.print(f"  • {r.skill_name}: {r.error}")
            raise typer.Exit(1)


@migrate_app.command("preview")
def migrate_preview(
    path: Path = typer.Argument(
        ...,
        help="Skill directory to preview",
    ),
) -> None:
    """Preview migration changes for a skill.

    Shows what changes would be made without modifying files.

    Example:

    \b
        skillforge migrate preview ./my-skill
    """
    from skillforge.migrate import get_migration_preview, get_format_info, SkillFormat

    path = Path(path).resolve()

    if not (path / "SKILL.md").exists():
        console.print("[red]Error: Not a skill directory (no SKILL.md)[/red]")
        raise typer.Exit(1)

    preview = get_migration_preview(path)

    console.print()
    console.print(f"[bold]Migration Preview: {path.name}[/bold]")
    console.print()

    current_info = get_format_info(SkillFormat(preview["current_format"]))
    target_info = get_format_info(SkillFormat(preview["target_format"]))

    console.print(f"Current Format: {current_info['name']}")
    console.print(f"Target Format:  {target_info['name']}")
    console.print()

    if preview["needs_migration"]:
        console.print("[yellow]Planned Changes:[/yellow]")
        for change in preview["planned_changes"]:
            console.print(f"  • {change}")
    else:
        console.print("[green]✓ No migration needed[/green]")


# =============================================================================
# Config Commands
# =============================================================================

config_app = typer.Typer(help="Manage SkillForge configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    key: Optional[str] = typer.Argument(
        None,
        help="Configuration key to show (e.g., 'default_model')",
    ),
) -> None:
    """Show current configuration.

    Displays merged configuration from all sources.

    Example:

    \b
        skillforge config show
        skillforge config show default_model
        skillforge config show proxy
    """
    from skillforge.config import get_config

    config = get_config()
    config_dict = config.to_dict()

    console.print()

    if key:
        # Show specific key
        if key in config_dict:
            value = config_dict[key]
            if isinstance(value, dict):
                console.print(f"[bold]{key}:[/bold]")
                for k, v in value.items():
                    console.print(f"  {k}: {v}")
            else:
                console.print(f"{key}: {value}")
        else:
            console.print(f"[red]Unknown config key: {key}[/red]")
            console.print(f"[dim]Available: {', '.join(config_dict.keys())}[/dim]")
            raise typer.Exit(1)
    else:
        # Show all
        console.print("[bold]SkillForge Configuration[/bold]")
        console.print()

        for section, value in config_dict.items():
            if isinstance(value, dict):
                console.print(f"[cyan]{section}:[/cyan]")
                for k, v in value.items():
                    if v is not None:
                        console.print(f"  {k}: {v}")
            else:
                console.print(f"[cyan]{section}:[/cyan] {value}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(
        ...,
        help="Configuration key (e.g., 'default_model')",
    ),
    value: str = typer.Argument(
        ...,
        help="Value to set",
    ),
    scope: str = typer.Option(
        "user",
        "--scope",
        "-s",
        help="Config scope: user or project",
    ),
) -> None:
    """Set a configuration value.

    Example:

    \b
        skillforge config set default_model claude-opus-4
        skillforge config set color_output false
        skillforge config set default_model gpt-4o --scope project
    """
    from skillforge.config import (
        get_config,
        save_user_config,
        save_project_config,
        load_config_file,
        get_user_config_path,
        get_project_config_path,
    )

    # Load current config
    if scope == "user":
        config_path = get_user_config_path()
    elif scope == "project":
        config_path = get_project_config_path()
    else:
        console.print(f"[red]Invalid scope: {scope}. Use 'user' or 'project'[/red]")
        raise typer.Exit(1)

    config_dict = load_config_file(config_path)

    # Handle nested keys (e.g., proxy.http_proxy)
    if "." in key:
        parts = key.split(".")
        current = config_dict
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    else:
        # Parse value
        if value.lower() in ("true", "yes", "1"):
            value = True
        elif value.lower() in ("false", "no", "0"):
            value = False
        elif value.isdigit():
            value = int(value)

        config_dict[key] = value

    # Save
    from skillforge.config import save_config_file
    save_config_file(config_path, config_dict)

    console.print(f"[green]✓ Set {key} = {value} in {scope} config[/green]")


@config_app.command("path")
def config_path(
    scope: str = typer.Option(
        "all",
        "--scope",
        "-s",
        help="Config scope: user, project, or all",
    ),
) -> None:
    """Show configuration file paths.

    Example:

    \b
        skillforge config path
        skillforge config path --scope user
    """
    from skillforge.config import get_user_config_path, get_project_config_path

    console.print()

    if scope in ("all", "user"):
        user_path = get_user_config_path()
        exists = "[green]exists[/green]" if user_path.exists() else "[dim]not created[/dim]"
        console.print(f"User config:    {user_path} ({exists})")

    if scope in ("all", "project"):
        project_path = get_project_config_path()
        exists = "[green]exists[/green]" if project_path.exists() else "[dim]not created[/dim]"
        console.print(f"Project config: {project_path} ({exists})")


@config_app.command("init")
def config_init(
    scope: str = typer.Option(
        "user",
        "--scope",
        "-s",
        help="Config scope: user or project",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing config",
    ),
) -> None:
    """Initialize a configuration file with defaults.

    Example:

    \b
        skillforge config init
        skillforge config init --scope project
    """
    from skillforge.config import (
        SkillForgeConfig,
        save_user_config,
        save_project_config,
        get_user_config_path,
        get_project_config_path,
    )

    if scope == "user":
        config_path = get_user_config_path()
        save_func = save_user_config
    elif scope == "project":
        config_path = get_project_config_path()
        save_func = save_project_config
    else:
        console.print(f"[red]Invalid scope: {scope}[/red]")
        raise typer.Exit(1)

    if config_path.exists() and not force:
        console.print(f"[yellow]Config already exists: {config_path}[/yellow]")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    # Create default config
    config = SkillForgeConfig()
    save_func(config)

    console.print(f"[green]✓ Created {scope} config: {config_path}[/green]")


# =============================================================================
# Info Command
# =============================================================================


@app.command("info")
def info() -> None:
    """Show detailed SkillForge information.

    Displays version, paths, and configuration summary.

    Example:

    \b
        skillforge info
    """
    from skillforge import __version__
    from skillforge.config import get_config, get_skills_directory, get_cache_directory
    from skillforge.claude_code import USER_SKILLS_DIR

    console.print()
    console.print("[bold]SkillForge[/bold]")
    console.print(f"Version: {__version__}")
    console.print()

    console.print("[bold]Paths:[/bold]")
    console.print(f"  Skills:  {get_skills_directory()}")
    console.print(f"  Cache:   {get_cache_directory()}")
    console.print(f"  Claude:  {USER_SKILLS_DIR}")
    console.print()

    config = get_config()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Model:    {config.default_model}")
    console.print(f"  Provider: {config.default_provider}")
    console.print(f"  Auth:     {config.auth.provider.value}")
    console.print(f"  Storage:  {config.storage.backend.value}")


if __name__ == "__main__":
    app()
