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


if __name__ == "__main__":
    app()
