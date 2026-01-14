"""SkillForge CLI - Create and manage Anthropic Agent Skills."""

from pathlib import Path
from typing import Optional

import typer
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
    """
    from skillforge.scaffold import create_skill_scaffold
    from skillforge.skill import normalize_skill_name

    # Show normalized name if different
    normalized = normalize_skill_name(name)
    if normalized != name:
        console.print(f"[dim]Normalizing name: {name} → {normalized}[/dim]")

    try:
        skill_dir = create_skill_scaffold(
            name=name,
            output_dir=output_dir,
            description=description,
            with_scripts=with_scripts,
            force=force,
        )

        console.print()
        console.print(f"[green]✓ Created skill:[/green] {skill_dir}")
        console.print()

        # Show created files
        console.print("[bold]Created files:[/bold]")
        for item in sorted(skill_dir.rglob("*")):
            if item.is_file():
                rel_path = item.relative_to(skill_dir)
                console.print(f"  {rel_path}")

        console.print()
        console.print("[bold]Next steps:[/bold]")
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

    Example:

    \b
        skillforge validate ./skills/my-skill
        skillforge validate ./skills/my-skill --strict
    """
    from skillforge.validator import validate_skill_directory

    skill_path = Path(skill_path)
    result = validate_skill_directory(skill_path)

    console.print()

    if result.skill:
        console.print(f"[bold]Skill:[/bold] {result.skill.name}")
        console.print(f"[bold]Description:[/bold] {result.skill.description[:60]}...")
        console.print()

    # Show errors
    if result.errors:
        console.print("[red bold]Errors:[/red bold]")
        for msg in result.errors:
            console.print(f"  [red]✗[/red] {msg}")
        console.print()

    # Show warnings
    if result.warnings:
        console.print("[yellow bold]Warnings:[/yellow bold]")
        for msg in result.warnings:
            console.print(f"  [yellow]![/yellow] {msg}")
        console.print()

    # Summary
    if result.valid and not (strict and result.warnings):
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

    Example:

    \b
        skillforge bundle ./skills/my-skill
        skillforge bundle ./skills/my-skill -o my-skill.zip
    """
    from skillforge.bundler import bundle_skill

    skill_path = Path(skill_path)

    console.print(f"[dim]Bundling skill: {skill_path}[/dim]")

    result = bundle_skill(
        skill_dir=skill_path,
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
    console.print(f"  SKILL.md")
    for f in skill.additional_files:
        console.print(f"  {f}")
    if skill.scripts:
        console.print(f"  scripts/")
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
            checks.append((f"Tool: {tool}", None, f"not found ({desc})"))

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
    console.print(f"  2. Create a new skill: [cyan]skillforge new my-skill[/cyan]")
    console.print(f"  3. Read the docs: [cyan]https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills[/cyan]")


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
    is triggered.

    Example:

    \b
        skillforge preview ./skills/my-skill
    """
    from skillforge.skill import Skill, SkillParseError

    skill_path = Path(skill_path)

    try:
        skill = Skill.from_directory(skill_path)
    except SkillParseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

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
    skill_md_path.write_text(result.raw_content)

    console.print(f"[green]✓ Generated skill:[/green] {skill_dir}")
    console.print(f"  Provider: {result.provider} ({result.model})")
    console.print()

    # Show preview
    console.print("[bold]Generated SKILL.md:[/bold]")
    syntax = Syntax(
        result.raw_content[:1500] + ("..." if len(result.raw_content) > 1500 else ""),
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

    # Show the improved content
    console.print("[bold]Improved SKILL.md:[/bold]")
    syntax = Syntax(
        result.raw_content[:2000] + ("..." if len(result.raw_content) > 2000 else ""),
        "markdown",
        theme="monokai",
        line_numbers=True,
    )
    console.print(syntax)

    if dry_run:
        console.print()
        console.print("[yellow]Dry run - changes not saved[/yellow]")
        console.print(f"[dim]Remove --dry-run to save changes[/dim]")
    else:
        # Save the improved skill
        skill_md_path = skill_path / "SKILL.md"
        skill_md_path.write_text(result.raw_content)

        console.print()
        console.print(f"[green]✓ Skill improved and saved:[/green] {skill_md_path}")


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
        console.print(f"[green]Ready to generate skills![/green]")
        console.print(f"[dim]Run: skillforge generate \"your skill description\"[/dim]")


if __name__ == "__main__":
    app()
