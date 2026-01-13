"""SkillForge CLI - Main entry point using Typer."""

from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console

app = typer.Typer(
    name="skillforge",
    help="A local-first developer tool to create, test, and run deterministic Skills.",
    no_args_is_help=True,
)

console = Console()

# Subcommand groups
cassette_app = typer.Typer(help="Record and replay external command outputs for deterministic tests.")
app.add_typer(cassette_app, name="cassette")

import_app = typer.Typer(help="Import skills from external sources.")
app.add_typer(import_app, name="import")


@app.command()
def init() -> None:
    """Create ~/.skillforge/ with default configuration."""
    from skillforge.config import config_exists, init_config_dir, get_config_file

    if config_exists():
        console.print(f"[yellow]Config already exists at {get_config_file()}[/yellow]")
        console.print("Use [bold]--force[/bold] to reinitialize (not implemented yet)")
        return

    config_dir = init_config_dir()
    console.print(f"[green]Initialized SkillForge configuration[/green]")
    console.print(f"  Config directory: [bold]{config_dir}[/bold]")
    console.print(f"  Config file:      [bold]{get_config_file()}[/bold]")
    console.print()
    console.print("Run [bold]skillforge doctor[/bold] to verify your environment.")


@app.command()
def doctor() -> None:
    """Verify environment: Python version, git, rsync availability."""
    from rich.table import Table

    from skillforge.doctor import CheckStatus, run_all_checks, has_errors, has_warnings

    console.print("[bold]SkillForge Environment Check[/bold]")
    console.print()

    results = run_all_checks()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    status_styles = {
        CheckStatus.OK: "[green]OK[/green]",
        CheckStatus.WARNING: "[yellow]WARNING[/yellow]",
        CheckStatus.ERROR: "[red]ERROR[/red]",
    }

    for result in results:
        table.add_row(
            result.name,
            status_styles[result.status],
            result.message,
        )

    console.print(table)
    console.print()

    if has_errors(results):
        console.print("[red]Some checks failed. Please fix the errors above.[/red]")
        raise typer.Exit(code=1)
    elif has_warnings(results):
        console.print("[yellow]Some warnings detected. SkillForge may work with reduced functionality.[/yellow]")
    else:
        console.print("[green]All checks passed. SkillForge is ready to use.[/green]")


@app.command()
def new(
    name: str = typer.Argument(..., help="Name of the new skill"),
    out: Path = typer.Option(
        Path("skills"),
        "--out",
        "-o",
        help="Output directory for the skill folder",
    ),
    description: str = typer.Option(
        "",
        "--description",
        "-d",
        help="Description of the skill",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing skill directory",
    ),
) -> None:
    """Create a new skill scaffold."""
    from skillforge.scaffold import create_skill_scaffold, validate_skill_name

    # Validate skill name
    is_valid, error_msg = validate_skill_name(name)
    if not is_valid:
        console.print(f"[red]Invalid skill name: {error_msg}[/red]")
        raise typer.Exit(code=1)

    # Resolve output directory to absolute path
    output_dir = out.resolve()

    try:
        skill_dir = create_skill_scaffold(
            name=name,
            output_dir=output_dir,
            description=description,
            force=force,
        )
    except FileExistsError as e:
        console.print(f"[red]{e}[/red]")
        console.print("Use [bold]--force[/bold] to overwrite.")
        raise typer.Exit(code=1)

    console.print(f"[green]Created skill scaffold:[/green] {skill_dir}")
    console.print()
    console.print("Files created:")
    console.print(f"  [cyan]skill.yaml[/cyan]    - Skill definition (steps, inputs, checks)")
    console.print(f"  [cyan]SKILL.txt[/cyan]     - Human-readable procedure")
    console.print(f"  [cyan]checks.py[/cyan]     - Custom check functions")
    console.print(f"  [cyan]fixtures/[/cyan]     - Test fixtures")
    console.print(f"  [cyan]cassettes/[/cyan]    - Recorded command outputs")
    console.print(f"  [cyan]reports/[/cyan]      - Run reports")
    console.print()
    console.print("Next steps:")
    console.print(f"  1. Edit [bold]{skill_dir}/skill.yaml[/bold] to define your skill")
    console.print(f"  2. Add test fixtures in [bold]{skill_dir}/fixtures/[/bold]")
    console.print(f"  3. Run [bold]skillforge test {skill_dir}[/bold] to test your skill")


@app.command()
def generate(
    from_spec: Path = typer.Option(
        ...,
        "--from",
        help="Path to the spec.txt file",
    ),
    out: Path = typer.Option(
        Path("skills"),
        "--out",
        "-o",
        help="Output directory for the generated skill",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing skill directory",
    ),
) -> None:
    """Generate a skill from a structured spec file.

    The spec file format is a human-readable text format:

    \b
    SKILL: my_skill
    DESCRIPTION: What the skill does
    VERSION: 0.1.0

    \b
    INPUTS:
    - target_dir: path (required) - Target directory
    - message: string (default: "hello") - Message

    \b
    PRECONDITIONS:
    - Git must be installed
    - Target directory must exist

    \b
    STEPS:
    1. Initialize project
       shell: npm init -y
       cwd: {target_dir}

    \b
    2. Create config
       template: {sandbox_dir}/config.json
       content: |
           {"name": "example"}

    \b
    CHECKS:
    - file_exists: {sandbox_dir}/package.json
    - exit_code: step1 equals 0
    """
    from skillforge.generator import (
        parse_spec_file,
        generate_skill_from_spec,
        SpecParseError,
    )

    # Resolve paths
    spec_path = from_spec.resolve()
    output_dir = out.resolve()

    console.print(f"[bold]Generating skill from:[/bold] {spec_path}")
    console.print()

    # Check spec file exists
    if not spec_path.exists():
        console.print(f"[red]Spec file not found: {spec_path}[/red]")
        raise typer.Exit(code=1)

    # Parse spec
    try:
        spec = parse_spec_file(spec_path)
    except SpecParseError as e:
        console.print(f"[red]Failed to parse spec: {e}[/red]")
        raise typer.Exit(code=1)

    console.print(f"  Name: {spec.name}")
    console.print(f"  Description: {spec.description or '(none)'}")
    console.print(f"  Inputs: {len(spec.inputs)}")
    console.print(f"  Steps: {len(spec.steps)}")
    console.print(f"  Checks: {len(spec.checks)}")
    console.print()

    # Check if skill already exists
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in spec.name)
    safe_name = safe_name.strip("_").lower()
    skill_dir = output_dir / safe_name

    if skill_dir.exists() and not force:
        console.print(f"[yellow]Skill directory already exists: {skill_dir}[/yellow]")
        console.print("Use [bold]--force[/bold] to overwrite.")
        raise typer.Exit(code=1)

    # Generate skill
    try:
        skill_dir = generate_skill_from_spec(spec, output_dir)
    except Exception as e:
        console.print(f"[red]Failed to generate skill: {e}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Skill generated successfully:[/green] {skill_dir}")
    console.print()
    console.print("Files created:")
    console.print(f"  [cyan]skill.yaml[/cyan]    - Skill definition")
    console.print(f"  [cyan]SKILL.txt[/cyan]     - Human-readable procedure")
    console.print(f"  [cyan]checks.py[/cyan]     - Custom check functions")
    console.print(f"  [cyan]fixtures/[/cyan]     - Test fixtures")
    console.print()
    console.print("Next steps:")
    console.print(f"  1. Review [bold]{skill_dir}/skill.yaml[/bold]")
    console.print(f"  2. Add test fixtures in [bold]{skill_dir}/fixtures/[/bold]")
    console.print(f"  3. Run [bold]skillforge lint {skill_dir}[/bold] to validate")
    console.print(f"  4. Run [bold]skillforge test {skill_dir}[/bold] to test")


@import_app.command("github-action")
def import_github_action(
    workflow_file: Path = typer.Argument(..., help="Path to the GitHub Actions workflow YAML"),
    out: Path = typer.Option(
        Path("skills"),
        "--out",
        "-o",
        help="Output directory for the imported skill",
    ),
    job: Optional[str] = typer.Option(
        None,
        "--job",
        "-j",
        help="Specific job to import (default: first job)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing skill directory",
    ),
) -> None:
    """Import a GitHub Actions workflow as a skill.

    Converts shell steps (run:) to SkillForge steps. Action steps (uses:)
    are added as placeholders that require manual conversion.

    GitHub Actions variables are converted where possible:
    - ${{ github.workspace }} -> {sandbox_dir}
    - $GITHUB_WORKSPACE -> {sandbox_dir}
    """
    from rich.table import Table

    from skillforge.importer import (
        import_github_workflow,
        parse_github_workflow,
        WorkflowParseError,
    )

    # Resolve paths
    workflow_path = workflow_file.resolve()
    output_dir = out.resolve()

    console.print(f"[bold]Importing workflow:[/bold] {workflow_path}")
    console.print()

    # Check workflow file exists
    if not workflow_path.exists():
        console.print(f"[red]Workflow file not found: {workflow_path}[/red]")
        raise typer.Exit(code=1)

    # Parse workflow first to show info
    try:
        workflow = parse_github_workflow(workflow_path)
    except WorkflowParseError as e:
        console.print(f"[red]Failed to parse workflow: {e}[/red]")
        raise typer.Exit(code=1)

    # Show workflow info
    console.print(f"  Name: {workflow.name}")
    console.print(f"  Jobs: {len(workflow.jobs)}")
    console.print()

    # Show jobs table
    if workflow.jobs:
        console.print("[bold]Jobs in workflow:[/bold]")
        jobs_table = Table(show_header=True, header_style="bold")
        jobs_table.add_column("Job ID", style="cyan")
        jobs_table.add_column("Name")
        jobs_table.add_column("Runs On")
        jobs_table.add_column("Steps")
        jobs_table.add_column("Convertible")

        for wf_job in workflow.jobs:
            convertible = sum(1 for s in wf_job.steps if s.supported)
            total = len(wf_job.steps)
            jobs_table.add_row(
                wf_job.id,
                wf_job.name,
                wf_job.runs_on or "-",
                str(total),
                f"{convertible}/{total}",
            )

        console.print(jobs_table)
        console.print()

    # Determine which job to import
    if job:
        target_job = next((j for j in workflow.jobs if j.id == job), None)
        if not target_job:
            console.print(f"[red]Job '{job}' not found in workflow[/red]")
            console.print(f"Available jobs: {', '.join(j.id for j in workflow.jobs)}")
            raise typer.Exit(code=1)
    else:
        target_job = workflow.jobs[0] if workflow.jobs else None

    if not target_job:
        console.print("[red]No jobs found in workflow[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Importing job:[/bold] {target_job.id}")
    console.print()

    # Check if skill already exists
    from skillforge.importer import _normalize_name
    skill_name = _normalize_name(workflow.name)
    skill_dir = output_dir / skill_name

    if skill_dir.exists() and not force:
        console.print(f"[yellow]Skill directory already exists: {skill_dir}[/yellow]")
        console.print("Use [bold]--force[/bold] to overwrite.")
        raise typer.Exit(code=1)

    # Import
    result = import_github_workflow(workflow_path, output_dir, job)

    if not result.success:
        console.print(f"[red]Import failed: {result.error_message}[/red]")
        raise typer.Exit(code=1)

    # Display results
    console.print(f"[green]Workflow imported successfully:[/green] {result.skill_dir}")
    console.print()
    console.print(f"  Steps imported: {result.steps_imported}")
    console.print(f"  Steps skipped: {result.steps_skipped} (require manual conversion)")
    console.print()

    # Show warnings
    if result.workflow and result.workflow.warnings:
        console.print("[yellow]Conversion warnings:[/yellow]")
        for warning in result.workflow.warnings[:5]:
            console.print(f"  - {warning}")
        if len(result.workflow.warnings) > 5:
            console.print(f"  ... and {len(result.workflow.warnings) - 5} more")
        console.print()

    console.print("Files created:")
    console.print(f"  [cyan]skill.yaml[/cyan]    - Skill definition")
    console.print(f"  [cyan]SKILL.txt[/cyan]     - Human-readable procedure")
    console.print(f"  [cyan]checks.py[/cyan]     - Custom check functions")
    console.print(f"  [cyan]fixtures/[/cyan]     - Test fixtures")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. Review [bold]{result.skill_dir}/skill.yaml[/bold]")
    console.print("  2. Replace any TODO placeholders for GitHub Actions")
    console.print(f"  3. Run [bold]skillforge lint {result.skill_dir}[/bold] to validate")
    console.print(f"  4. Add test fixtures and run [bold]skillforge test {result.skill_dir}[/bold]")


@app.command()
def wrap(
    script_path: Path = typer.Argument(..., help="Path to the script to wrap"),
    out: Path = typer.Option(
        Path("skills"),
        "--out",
        "-o",
        help="Output directory for the wrapped skill",
    ),
    script_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Script type (bash, python, node, ruby, perl). Auto-detected if not specified.",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom skill name (default: script filename)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing skill directory",
    ),
) -> None:
    """Wrap an existing script as a skill.

    Supported script types: bash, shell, python, node, ruby, perl.
    The script type is auto-detected from the file extension or shebang.

    The script is copied into the skill's scripts/ directory and a wrapper
    skill.yaml is generated to execute it.

    \b
    Examples:
        skillforge wrap ./deploy.sh
        skillforge wrap ./build.py --type python --name my_build
    """
    from skillforge.wrapper import (
        wrap_script_command,
        analyze_script,
        detect_script_type,
        WrapError,
        SCRIPT_TYPES,
        _normalize_name,
    )

    # Resolve paths
    script_file = script_path.resolve()
    output_dir = out.resolve()

    console.print(f"[bold]Wrapping script:[/bold] {script_file}")
    console.print()

    # Check script exists
    if not script_file.exists():
        console.print(f"[red]Script not found: {script_file}[/red]")
        raise typer.Exit(code=1)

    if not script_file.is_file():
        console.print(f"[red]Not a file: {script_file}[/red]")
        raise typer.Exit(code=1)

    # Validate script type if provided
    if script_type and script_type not in SCRIPT_TYPES:
        console.print(f"[red]Unknown script type: {script_type}[/red]")
        console.print(f"Supported types: {', '.join(SCRIPT_TYPES.keys())}")
        raise typer.Exit(code=1)

    # Detect script type if not provided
    detected_type = script_type or detect_script_type(script_file)

    # Analyze script
    try:
        info = analyze_script(script_file, detected_type)
    except WrapError as e:
        console.print(f"[red]Failed to analyze script: {e}[/red]")
        raise typer.Exit(code=1)

    # Show script info
    console.print(f"  Type: {info.type}")
    console.print(f"  Name: {info.name}")
    if info.description:
        desc = info.description[:60] + "..." if len(info.description) > 60 else info.description
        console.print(f"  Description: {desc}")
    if info.shebang:
        console.print(f"  Shebang: {info.shebang}")
    console.print(f"  Executable: {'Yes' if info.executable else 'No'}")
    console.print()

    if info.arguments:
        console.print(f"[bold]Detected arguments:[/bold] {', '.join(info.arguments[:5])}")
    if info.env_vars:
        console.print(f"[bold]Environment vars:[/bold] {', '.join(info.env_vars[:5])}")
    if info.arguments or info.env_vars:
        console.print()

    # Check if skill already exists
    skill_name = _normalize_name(name or info.name)
    skill_dir = output_dir / skill_name

    if skill_dir.exists() and not force:
        console.print(f"[yellow]Skill directory already exists: {skill_dir}[/yellow]")
        console.print("Use [bold]--force[/bold] to overwrite.")
        raise typer.Exit(code=1)

    # Wrap the script
    result = wrap_script_command(script_file, output_dir, detected_type, name)

    if not result.success:
        console.print(f"[red]Wrap failed: {result.error_message}[/red]")
        raise typer.Exit(code=1)

    # Display results
    console.print(f"[green]Script wrapped successfully:[/green] {result.skill_dir}")
    console.print()
    console.print("Files created:")
    console.print(f"  [cyan]skill.yaml[/cyan]       - Skill definition")
    console.print(f"  [cyan]SKILL.txt[/cyan]        - Human-readable procedure")
    console.print(f"  [cyan]checks.py[/cyan]        - Custom check functions")
    console.print(f"  [cyan]scripts/[/cyan]         - Wrapped script")
    console.print(f"  [cyan]fixtures/[/cyan]        - Test fixtures")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. Review [bold]{result.skill_dir}/skill.yaml[/bold]")
    console.print("  2. Adjust inputs and environment variables as needed")
    console.print(f"  3. Run [bold]skillforge lint {result.skill_dir}[/bold] to validate")
    console.print(f"  4. Add test fixtures and run [bold]skillforge test {result.skill_dir}[/bold]")


# Recording subcommand group
recording_app = typer.Typer(help="Manage recording sessions.")
app.add_typer(recording_app, name="recording")


@app.command()
def record(
    name: str = typer.Option(..., "--name", "-n", help="Name for the recording session"),
    workdir: Path = typer.Option(..., "--workdir", "-w", help="Working directory to record in"),
    mode: str = typer.Option("git", "--mode", "-m", help="Recording mode (git)"),
    shell: str = typer.Option("bash", "--shell", "-s", help="Shell to use (bash or zsh)"),
) -> None:
    """Start a recording session.

    This command starts an interactive shell session where all commands
    are recorded. When you're done, type 'exit' or run 'skillforge stop'
    to end the recording.

    The recording can then be compiled into a skill using 'skillforge compile'.

    \b
    Examples:
        skillforge record --name deploy --workdir ./my-project
        skillforge record -n setup -w . --shell zsh
    """
    import subprocess

    from skillforge.recorder import (
        start_recording,
        get_active_session,
    )

    # Check for active session
    active = get_active_session()
    if active:
        console.print(f"[yellow]Recording session already active:[/yellow] {active.name}")
        console.print(f"  Session ID: {active.session_id}")
        console.print(f"  Started: {active.started_at}")
        console.print()
        console.print("Run [bold]skillforge stop[/bold] to end the current session first.")
        raise typer.Exit(code=1)

    # Resolve workdir
    work_path = workdir.resolve()

    console.print(f"[bold]Starting recording session:[/bold] {name}")
    console.print(f"  Working directory: {work_path}")
    console.print(f"  Shell: {shell}")
    console.print()

    # Start recording
    result = start_recording(
        name=name,
        workdir=work_path,
        mode=mode,
        shell=shell,
    )

    if not result.success:
        console.print(f"[red]Failed to start recording: {result.error_message}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Recording session created:[/green] {result.session_id}")
    console.print()
    console.print("Launching recording shell...")
    console.print("[dim]Type 'exit' when done to end the recording.[/dim]")
    console.print()

    # Launch the recording shell
    try:
        subprocess.run(result.shell_command, shell=True)
    except KeyboardInterrupt:
        pass

    # After shell exits, check if session was stopped
    from skillforge.recorder import load_session
    session = load_session(result.session_id)

    if session and session.status == "active":
        # Auto-stop the session
        from skillforge.recorder import stop_recording
        stop_result = stop_recording(result.session_id)

        console.print()
        if stop_result.success:
            console.print("[green]Recording session ended.[/green]")
            console.print(f"  Commands recorded: {stop_result.commands_recorded}")
            console.print(f"  Files changed: {stop_result.files_changed}")
            console.print()
            console.print(f"Run [bold]skillforge compile {result.session_id}[/bold] to create a skill.")
        else:
            console.print(f"[yellow]Warning: Failed to save recording: {stop_result.error_message}[/yellow]")


@app.command()
def stop() -> None:
    """Stop the current recording session.

    This command stops the active recording session and saves all
    recorded commands. Use this if you're in a separate terminal
    from the recording shell.
    """
    from skillforge.recorder import get_active_session, stop_recording

    # Find active session
    session = get_active_session()
    if not session:
        console.print("[yellow]No active recording session found.[/yellow]")
        console.print()
        console.print("Use [bold]skillforge recording list[/bold] to see all recordings.")
        raise typer.Exit(code=0)

    console.print(f"[bold]Stopping recording:[/bold] {session.name}")
    console.print(f"  Session ID: {session.session_id}")
    console.print()

    # Stop recording
    result = stop_recording(session.session_id)

    if not result.success:
        console.print(f"[red]Failed to stop recording: {result.error_message}[/red]")
        raise typer.Exit(code=1)

    console.print("[green]Recording session stopped.[/green]")
    console.print(f"  Commands recorded: {result.commands_recorded}")
    console.print(f"  Files changed: {result.files_changed}")
    console.print()
    console.print(f"Run [bold]skillforge compile {result.session_id}[/bold] to create a skill.")


@app.command("compile")
def compile_recording(
    recording_id: str = typer.Argument(..., help="ID of the recording to compile"),
    out: Path = typer.Option(
        Path("skills"),
        "--out",
        "-o",
        help="Output directory for the compiled skill",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom skill name (default: recording name)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing skill directory",
    ),
) -> None:
    """Compile a recording into a skill.

    Takes a stopped recording session and converts all recorded commands
    into skill steps. The resulting skill can be run against any target
    directory.

    \b
    Examples:
        skillforge compile rec_20240115_143022
        skillforge compile rec_20240115_143022 --out ./my-skills --name deploy
    """
    from skillforge.recorder import (
        compile_recording as do_compile,
        load_session,
        get_recording_info,
        _normalize_name,
    )

    # Resolve output directory
    output_dir = out.resolve()

    console.print(f"[bold]Compiling recording:[/bold] {recording_id}")
    console.print()

    # Load session info
    info = get_recording_info(recording_id)
    if not info:
        console.print(f"[red]Recording not found: {recording_id}[/red]")
        console.print()
        console.print("Use [bold]skillforge recording list[/bold] to see all recordings.")
        raise typer.Exit(code=1)

    # Show recording info
    console.print(f"  Name: {info['name']}")
    console.print(f"  Status: {info['status']}")
    console.print(f"  Commands: {len(info.get('commands', []))}")
    console.print(f"  Recorded at: {info['started_at']}")
    console.print()

    if info['status'] == 'active':
        console.print("[red]Recording is still active.[/red]")
        console.print("Run [bold]skillforge stop[/bold] first.")
        raise typer.Exit(code=1)

    if info['status'] == 'compiled':
        console.print("[yellow]Recording was already compiled.[/yellow]")
        if not force:
            console.print("Use [bold]--force[/bold] to compile again.")
            raise typer.Exit(code=0)

    # Check if skill already exists
    skill_name = _normalize_name(name or info['name'])
    skill_dir = output_dir / skill_name

    if skill_dir.exists() and not force:
        console.print(f"[yellow]Skill directory already exists: {skill_dir}[/yellow]")
        console.print("Use [bold]--force[/bold] to overwrite.")
        raise typer.Exit(code=1)

    # Compile
    result = do_compile(recording_id, output_dir, name)

    if not result.success:
        console.print(f"[red]Compilation failed: {result.error_message}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Recording compiled successfully:[/green] {result.skill_dir}")
    console.print()
    console.print(f"  Steps created: {result.steps_created}")
    console.print()
    console.print("Files created:")
    console.print(f"  [cyan]skill.yaml[/cyan]    - Skill definition")
    console.print(f"  [cyan]SKILL.txt[/cyan]     - Human-readable procedure")
    console.print(f"  [cyan]checks.py[/cyan]     - Custom check functions")
    console.print(f"  [cyan]fixtures/[/cyan]     - Test fixtures")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. Review [bold]{result.skill_dir}/skill.yaml[/bold]")
    console.print("  2. Adjust commands and working directories as needed")
    console.print(f"  3. Run [bold]skillforge lint {result.skill_dir}[/bold] to validate")
    console.print(f"  4. Add test fixtures and run [bold]skillforge test {result.skill_dir}[/bold]")


@recording_app.command("list")
def recording_list() -> None:
    """List all recording sessions."""
    from rich.table import Table

    from skillforge.recorder import list_recordings

    recordings = list_recordings()

    if not recordings:
        console.print("[yellow]No recordings found.[/yellow]")
        console.print()
        console.print("Use [bold]skillforge record[/bold] to start a new recording.")
        raise typer.Exit(code=0)

    console.print("[bold]Recording sessions:[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Session ID", style="cyan")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Commands")
    table.add_column("Started")

    for rec in recordings:
        status_style = {
            "active": "[green]active[/green]",
            "stopped": "[yellow]stopped[/yellow]",
            "compiled": "[dim]compiled[/dim]",
        }.get(rec["status"], rec["status"])

        started = rec.get("started_at", "")[:16].replace("T", " ")

        table.add_row(
            rec["session_id"],
            rec["name"],
            status_style,
            str(rec.get("commands_count", 0)),
            started,
        )

    console.print(table)


@recording_app.command("show")
def recording_show(
    recording_id: str = typer.Argument(..., help="ID of the recording to show"),
) -> None:
    """Show details of a recording session."""
    from rich.table import Table

    from skillforge.recorder import get_recording_info

    info = get_recording_info(recording_id)

    if not info:
        console.print(f"[red]Recording not found: {recording_id}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Recording:[/bold] {info['name']}")
    console.print()
    console.print(f"  Session ID: {info['session_id']}")
    console.print(f"  Status: {info['status']}")
    console.print(f"  Workdir: {info['workdir']}")
    console.print(f"  Shell: {info['shell']}")
    console.print(f"  Started: {info['started_at']}")
    if info.get('stopped_at'):
        console.print(f"  Stopped: {info['stopped_at']}")
    console.print()

    commands = info.get("commands", [])
    if commands:
        console.print(f"[bold]Recorded commands ({len(commands)}):[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="dim")
        table.add_column("Command")
        table.add_column("Directory", style="dim")

        for i, cmd in enumerate(commands[:20], 1):
            cmd_display = cmd["command"]
            if len(cmd_display) > 50:
                cmd_display = cmd_display[:47] + "..."

            cwd_display = cmd.get("cwd", "")
            if len(cwd_display) > 30:
                cwd_display = "..." + cwd_display[-27:]

            table.add_row(str(i), cmd_display, cwd_display)

        console.print(table)

        if len(commands) > 20:
            console.print(f"  [dim]... and {len(commands) - 20} more commands[/dim]")
    else:
        console.print("[yellow]No commands recorded yet.[/yellow]")


@recording_app.command("delete")
def recording_delete(
    recording_id: str = typer.Argument(..., help="ID of the recording to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation"),
) -> None:
    """Delete a recording session."""
    from skillforge.recorder import get_recording_info, delete_recording, get_active_session

    info = get_recording_info(recording_id)

    if not info:
        console.print(f"[red]Recording not found: {recording_id}[/red]")
        raise typer.Exit(code=1)

    # Check if it's the active session
    active = get_active_session()
    if active and active.session_id == recording_id:
        console.print("[red]Cannot delete the active recording session.[/red]")
        console.print("Run [bold]skillforge stop[/bold] first.")
        raise typer.Exit(code=1)

    console.print(f"[bold]Delete recording:[/bold] {info['name']}")
    console.print(f"  Session ID: {recording_id}")
    console.print(f"  Commands: {len(info.get('commands', []))}")
    console.print()

    if not force:
        confirm = typer.confirm("Are you sure you want to delete this recording?", default=False)
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit(code=0)

    if delete_recording(recording_id):
        console.print("[green]Recording deleted.[/green]")
    else:
        console.print("[red]Failed to delete recording.[/red]")
        raise typer.Exit(code=1)


@app.command()
def run(
    skill_dir: Path = typer.Argument(..., help="Path to the skill directory"),
    target: Path = typer.Option(..., "--target", "-t", help="Target directory to run against"),
    sandbox: Optional[Path] = typer.Option(None, "--sandbox", help="Custom sandbox directory"),
    no_sandbox: bool = typer.Option(False, "--no-sandbox", help="Run directly in target (dangerous)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print plan without executing"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode on failures"),
    env: Optional[List[str]] = typer.Option(None, "--env", "-e", help="Environment variables (KEY=VAL)"),
) -> None:
    """Execute a skill against a target directory."""
    from rich.table import Table

    from skillforge.runner import run_skill, get_run_summary, RunError

    # Resolve paths
    skill_path = skill_dir.resolve()
    target_path = target.resolve()
    sandbox_path = sandbox.resolve() if sandbox else None

    # Parse environment variables
    env_vars = {}
    if env:
        for e in env:
            if "=" in e:
                key, value = e.split("=", 1)
                env_vars[key] = value

    # Warn about no-sandbox mode
    if no_sandbox:
        console.print("[yellow]WARNING: Running without sandbox - changes will be made directly to target![/yellow]")
        if not dry_run:
            confirm = typer.confirm("Are you sure you want to continue?", default=False)
            if not confirm:
                raise typer.Exit(code=0)

    # Show what we're doing
    if dry_run:
        console.print(f"[bold]Dry run:[/bold] {skill_path.name}")
    else:
        console.print(f"[bold]Running skill:[/bold] {skill_path.name}")
    console.print(f"  Target: {target_path}")
    if not no_sandbox:
        console.print(f"  Sandbox: {'custom' if sandbox_path else 'auto-generated'}")
    console.print()

    try:
        report = run_skill(
            skill_dir=skill_path,
            target_dir=target_path,
            sandbox_dir=sandbox_path,
            no_sandbox=no_sandbox,
            dry_run=dry_run,
            env_vars=env_vars if env_vars else None,
        )
    except RunError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

    # Display results
    summary = get_run_summary(report)

    # Steps table
    if report.steps:
        console.print("[bold]Steps:[/bold]")
        steps_table = Table(show_header=True, header_style="bold")
        steps_table.add_column("Step", style="cyan")
        steps_table.add_column("Type")
        steps_table.add_column("Status")
        steps_table.add_column("Duration")
        steps_table.add_column("Details", style="dim")

        for step in report.steps:
            status_style = {
                "success": "[green]OK[/green]",
                "failed": "[red]FAILED[/red]",
                "skipped": "[yellow]SKIPPED[/yellow]",
            }.get(step["status"], step["status"])

            duration = f"{step.get('duration_ms', 0)}ms"
            details = step.get("error_message", "") or step.get("command", "")[:50]

            steps_table.add_row(
                step["id"],
                step["type"],
                status_style,
                duration,
                details,
            )

        console.print(steps_table)
        console.print()

    # Checks table
    if report.checks:
        console.print("[bold]Checks:[/bold]")
        checks_table = Table(show_header=True, header_style="bold")
        checks_table.add_column("Check", style="cyan")
        checks_table.add_column("Type")
        checks_table.add_column("Status")
        checks_table.add_column("Message", style="dim")

        for check in report.checks:
            status_style = {
                "passed": "[green]PASSED[/green]",
                "failed": "[red]FAILED[/red]",
            }.get(check["status"], check["status"])

            checks_table.add_row(
                check["id"],
                check["type"],
                status_style,
                check.get("message", ""),
            )

        console.print(checks_table)
        console.print()

    # Summary
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Run ID: {report.run_id}")
    console.print(f"  Steps: {summary['steps_passed']}/{summary['steps_total']} passed")
    console.print(f"  Checks: {summary['checks_passed']}/{summary['checks_total']} passed")
    console.print(f"  Duration: {summary['duration_ms']}ms")

    if not dry_run:
        console.print(f"  Report: {skill_path}/reports/run_{report.run_id}/")

    console.print()

    if report.success:
        console.print("[green]Skill completed successfully.[/green]")
    else:
        console.print(f"[red]Skill failed: {report.error_message}[/red]")
        raise typer.Exit(code=1)


@app.command()
def test(
    skill_dir: Path = typer.Argument(..., help="Path to the skill directory to test"),
    fixture: Optional[str] = typer.Option(None, "--fixture", "-f", help="Run only specific fixture"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Run fixture tests for a skill."""
    from rich.table import Table

    from skillforge.testing import (
        discover_fixtures,
        run_all_fixtures,
        run_fixture_test,
        load_fixture_config,
    )
    from skillforge.sandbox import generate_run_id

    # Resolve to absolute path
    skill_path = skill_dir.resolve()

    console.print(f"[bold]Testing skill:[/bold] {skill_path.name}")
    console.print()

    # Discover fixtures
    fixtures = discover_fixtures(skill_path)

    if not fixtures:
        console.print("[yellow]No fixtures found.[/yellow]")
        console.print(f"Add test fixtures in [bold]{skill_path}/fixtures/[/bold]")
        raise typer.Exit(code=0)

    # Filter by specific fixture if requested
    if fixture:
        fixtures = [f for f in fixtures if f.name == fixture]
        if not fixtures:
            console.print(f"[red]Fixture not found: {fixture}[/red]")
            raise typer.Exit(code=1)

    console.print(f"Found {len(fixtures)} fixture(s)")
    console.print()

    # Run tests
    report = run_all_fixtures(skill_path)

    # Display results table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Fixture", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Details", style="dim")

    for result in report.fixtures:
        status_style = (
            "[green]PASSED[/green]" if result.passed else "[red]FAILED[/red]"
        )
        duration = f"{result.duration_ms}ms"
        details = result.error_message[:60] if result.error_message else ""

        table.add_row(
            result.fixture_name,
            status_style,
            duration,
            details,
        )

        # Show verbose output for failures
        if verbose and not result.passed:
            if result.comparison:
                if result.comparison.missing_files:
                    console.print(f"  [dim]Missing: {', '.join(result.comparison.missing_files)}[/dim]")
                if result.comparison.extra_files:
                    console.print(f"  [dim]Extra: {', '.join(result.comparison.extra_files)}[/dim]")
                if result.comparison.different_files:
                    console.print(f"  [dim]Different: {', '.join(result.comparison.different_files)}[/dim]")

    console.print(table)
    console.print()

    # Summary
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Passed: {report.total_passed}")
    console.print(f"  Failed: {report.total_failed}")
    if report.total_skipped > 0:
        console.print(f"  Skipped: {report.total_skipped}")
    console.print()

    if report.all_passed:
        console.print("[green]All tests passed.[/green]")
    else:
        console.print("[red]Some tests failed.[/red]")
        raise typer.Exit(code=1)


@app.command()
def bless(
    skill_dir: Path = typer.Argument(..., help="Path to the skill directory"),
    fixture: str = typer.Option(..., "--fixture", "-f", help="Name of the fixture to bless"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing golden artifacts"),
) -> None:
    """Run skill on fixture and store golden regression artifacts.

    Golden artifacts are used to detect unexpected changes in skill output.
    They include:
    - expected_changed_files.json: List of files the skill should create/modify
    - expected_hashes.json: SHA256 hashes of expected file contents
    - bless_metadata.json: Metadata about when the fixture was blessed
    """
    from skillforge.bless import bless_fixture, get_golden_info

    # Resolve to absolute path
    skill_path = skill_dir.resolve()

    console.print(f"[bold]Blessing fixture:[/bold] {fixture}")
    console.print(f"  Skill: {skill_path.name}")
    console.print()

    # Check for existing golden artifacts
    existing = get_golden_info(skill_path, fixture)
    if existing.get("exists") and not force:
        console.print("[yellow]Golden artifacts already exist for this fixture.[/yellow]")
        if "metadata" in existing:
            blessed_at = existing["metadata"].get("blessed_at", "unknown")
            console.print(f"  Blessed at: {blessed_at}")
        if "file_count" in existing:
            console.print(f"  Files: {existing['file_count']}")
        console.print()
        console.print("Use [bold]--force[/bold] to overwrite existing artifacts.")
        raise typer.Exit(code=0)

    # Run bless
    result = bless_fixture(skill_path, fixture)

    if not result.success:
        console.print(f"[red]Bless failed: {result.error_message}[/red]")
        raise typer.Exit(code=1)

    # Display results
    console.print("[green]Fixture blessed successfully.[/green]")
    console.print()
    console.print("[bold]Golden artifacts created:[/bold]")
    console.print(f"  Directory: {result.golden_dir}")
    console.print(f"  Files tracked: {len(result.changed_files)}")
    console.print()

    if result.changed_files:
        console.print("[bold]Tracked files:[/bold]")
        for f in result.changed_files[:10]:
            console.print(f"  - {f}")
        if len(result.changed_files) > 10:
            console.print(f"  ... and {len(result.changed_files) - 10} more")
        console.print()

    console.print("Run [bold]skillforge test[/bold] to verify against these golden artifacts.")


@cassette_app.command("record")
def cassette_record(
    skill_dir: Path = typer.Argument(..., help="Path to the skill directory"),
    fixture: str = typer.Option(..., "--fixture", "-f", help="Name of the fixture"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing cassette"),
) -> None:
    """Record external command outputs for a fixture.

    Cassettes capture the outputs of shell commands during skill execution,
    enabling deterministic replay during testing. This is useful for:

    - Commands that depend on network (curl, git clone, etc.)
    - Commands with non-deterministic output (timestamps, random values)
    - Expensive commands you don't want to run every time
    """
    from skillforge.cassette import record_cassette, get_cassette_info

    # Resolve to absolute path
    skill_path = skill_dir.resolve()

    console.print(f"[bold]Recording cassette:[/bold] {fixture}")
    console.print(f"  Skill: {skill_path.name}")
    console.print()

    # Check for existing cassette
    existing = get_cassette_info(skill_path, fixture)
    if existing.get("exists") and not force:
        console.print("[yellow]Cassette already exists for this fixture.[/yellow]")
        console.print(f"  Recorded at: {existing.get('recorded_at', 'unknown')}")
        console.print(f"  Commands: {existing.get('commands_count', 0)}")
        console.print()
        console.print("Use [bold]--force[/bold] to overwrite the existing cassette.")
        raise typer.Exit(code=0)

    # Record cassette
    result = record_cassette(skill_path, fixture)

    if not result.success:
        console.print(f"[red]Recording failed: {result.error_message}[/red]")
        raise typer.Exit(code=1)

    # Display results
    console.print("[green]Cassette recorded successfully.[/green]")
    console.print()
    console.print(f"  File: {result.cassette_path}")
    console.print(f"  Commands recorded: {result.commands_recorded}")
    console.print()
    console.print("Use [bold]skillforge cassette replay[/bold] to test with this cassette.")


@cassette_app.command("replay")
def cassette_replay(
    skill_dir: Path = typer.Argument(..., help="Path to the skill directory"),
    fixture: str = typer.Option(..., "--fixture", "-f", help="Name of the fixture"),
) -> None:
    """Replay recorded command outputs for deterministic testing.

    Runs the skill using recorded command outputs from a cassette instead of
    actually executing the commands. This ensures deterministic behavior.
    """
    from rich.table import Table

    from skillforge.cassette import load_cassette, get_cassette_path
    from skillforge.runner import run_skill, get_run_summary
    from skillforge.sandbox import generate_run_id

    # Resolve to absolute path
    skill_path = skill_dir.resolve()

    console.print(f"[bold]Replaying cassette:[/bold] {fixture}")
    console.print(f"  Skill: {skill_path.name}")
    console.print()

    # Load cassette
    cassette = load_cassette(skill_path, fixture)
    if not cassette:
        console.print(f"[red]Cassette not found for fixture: {fixture}[/red]")
        console.print(f"  Expected: {get_cassette_path(skill_path, fixture)}")
        console.print()
        console.print("Run [bold]skillforge cassette record[/bold] first to create a cassette.")
        raise typer.Exit(code=1)

    console.print(f"  Cassette recorded at: {cassette.recorded_at}")
    console.print(f"  Commands in cassette: {len(cassette.commands)}")
    console.print()

    # Get fixture input directory
    fixture_dir = skill_path / "fixtures" / fixture
    input_dir = fixture_dir / "input"

    if not input_dir.is_dir():
        console.print(f"[red]Fixture input directory not found: {input_dir}[/red]")
        raise typer.Exit(code=1)

    # Run with cassette replay
    run_id = generate_run_id()
    sandbox_dir = skill_path / "reports" / f"replay_{run_id}" / fixture / "sandbox"

    report = run_skill(
        skill_dir=skill_path,
        target_dir=input_dir,
        sandbox_dir=sandbox_dir,
        no_sandbox=False,
        cassette=cassette,
    )

    # Display results
    summary = get_run_summary(report)

    if report.steps:
        console.print("[bold]Steps (replayed):[/bold]")
        steps_table = Table(show_header=True, header_style="bold")
        steps_table.add_column("Step", style="cyan")
        steps_table.add_column("Status")
        steps_table.add_column("Source")

        for step in report.steps:
            status_style = {
                "success": "[green]OK[/green]",
                "failed": "[red]FAILED[/red]",
            }.get(step["status"], step["status"])

            # Check if this was from cassette
            source = "cassette" if step["type"] == "shell" else "executed"

            steps_table.add_row(
                step["id"],
                status_style,
                source,
            )

        console.print(steps_table)
        console.print()

    # Summary
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Mode: cassette replay")
    console.print(f"  Steps: {summary['steps_passed']}/{summary['steps_total']} passed")
    console.print(f"  Checks: {summary['checks_passed']}/{summary['checks_total']} passed")
    console.print()

    if report.success:
        console.print("[green]Replay completed successfully.[/green]")
    else:
        console.print(f"[red]Replay failed: {report.error_message}[/red]")
        raise typer.Exit(code=1)


@cassette_app.command("list")
def cassette_list(
    skill_dir: Path = typer.Argument(..., help="Path to the skill directory"),
) -> None:
    """List all cassettes for a skill."""
    from rich.table import Table

    from skillforge.cassette import list_cassettes

    # Resolve to absolute path
    skill_path = skill_dir.resolve()

    cassettes = list_cassettes(skill_path)

    if not cassettes:
        console.print("[yellow]No cassettes found.[/yellow]")
        console.print(f"  Cassettes directory: {skill_path / 'cassettes'}")
        console.print()
        console.print("Use [bold]skillforge cassette record[/bold] to create a cassette.")
        raise typer.Exit(code=0)

    console.print(f"[bold]Cassettes for skill:[/bold] {skill_path.name}")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Fixture", style="cyan")
    table.add_column("Commands")
    table.add_column("Recorded At")

    for cassette in cassettes:
        table.add_row(
            cassette["fixture_name"],
            str(cassette["commands_count"]),
            cassette.get("recorded_at", "unknown")[:19],  # Truncate ISO timestamp
        )

    console.print(table)


@cassette_app.command("show")
def cassette_show(
    skill_dir: Path = typer.Argument(..., help="Path to the skill directory"),
    fixture: str = typer.Option(..., "--fixture", "-f", help="Name of the fixture"),
) -> None:
    """Show details of a cassette."""
    from rich.table import Table

    from skillforge.cassette import get_cassette_info

    # Resolve to absolute path
    skill_path = skill_dir.resolve()

    info = get_cassette_info(skill_path, fixture)

    if not info:
        console.print(f"[red]Cassette not found for fixture: {fixture}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Cassette:[/bold] {fixture}")
    console.print()
    console.print(f"  Path: {info['path']}")
    console.print(f"  Skill: {info.get('skill_name', 'unknown')}")
    console.print(f"  Recorded at: {info.get('recorded_at', 'unknown')}")
    console.print(f"  Commands: {info.get('commands_count', 0)}")
    console.print()

    if info.get("commands"):
        console.print("[bold]Recorded commands:[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Step ID", style="cyan")
        table.add_column("Command")

        for cmd in info["commands"]:
            table.add_row(cmd["step_id"], cmd["command"])

        console.print(table)


@app.command()
def lint(
    skill_dir: Path = typer.Argument(..., help="Path to the skill directory to lint"),
) -> None:
    """Validate skill structure and check for issues."""
    from rich.table import Table

    from skillforge.linter import lint_skill, LintSeverity

    # Resolve to absolute path
    skill_path = skill_dir.resolve()

    console.print(f"[bold]Linting skill:[/bold] {skill_path}")
    console.print()

    result = lint_skill(skill_path)

    # Handle load errors
    if result.load_error:
        console.print(f"[red]Failed to load skill: {result.load_error}[/red]")
        raise typer.Exit(code=1)

    # Display issues
    if result.issues:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Severity")
        table.add_column("Code", style="cyan")
        table.add_column("Message")
        table.add_column("Location", style="dim")

        for issue in result.issues:
            severity_style = (
                "[red]ERROR[/red]"
                if issue.severity == LintSeverity.ERROR
                else "[yellow]WARNING[/yellow]"
            )
            table.add_row(
                severity_style,
                issue.code,
                issue.message,
                issue.location or "-",
            )

        console.print(table)
        console.print()

    # Summary
    if result.has_errors:
        console.print(
            f"[red]Found {result.error_count} error(s) and {result.warning_count} warning(s)[/red]"
        )
        raise typer.Exit(code=1)
    elif result.has_warnings:
        console.print(
            f"[yellow]Found {result.warning_count} warning(s)[/yellow]"
        )
        console.print("[green]No errors found.[/green]")
    else:
        console.print("[green]No issues found. Skill is valid.[/green]")


if __name__ == "__main__":
    app()
