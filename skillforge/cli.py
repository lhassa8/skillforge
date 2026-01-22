"""SkillForge CLI - Create and manage Anthropic Agent Skills."""

from __future__ import annotations

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


if __name__ == "__main__":
    app()
