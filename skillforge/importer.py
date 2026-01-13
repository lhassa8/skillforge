"""Import skills from external sources like GitHub Actions workflows."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class ImportedStep:
    """A step imported from an external source."""

    id: str
    name: str
    type: str  # shell, action (unsupported)
    command: Optional[str] = None
    cwd: Optional[str] = None
    env: Optional[dict[str, str]] = None
    shell: Optional[str] = None
    condition: Optional[str] = None  # 'if' condition
    action: Optional[str] = None  # For 'uses' steps
    action_with: Optional[dict[str, Any]] = None  # For 'uses' inputs
    supported: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass
class ImportedJob:
    """A job imported from a workflow."""

    id: str
    name: str
    runs_on: str = ""
    env: dict[str, str] = field(default_factory=dict)
    steps: list[ImportedStep] = field(default_factory=list)


@dataclass
class ImportedWorkflow:
    """A complete imported workflow."""

    name: str
    source_file: str = ""
    env: dict[str, str] = field(default_factory=dict)
    jobs: list[ImportedJob] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImportResult:
    """Result of importing a workflow."""

    success: bool = False
    error_message: str = ""
    skill_dir: str = ""
    workflow: Optional[ImportedWorkflow] = None
    steps_imported: int = 0
    steps_skipped: int = 0


class WorkflowParseError(Exception):
    """Raised when workflow parsing fails."""

    pass


def parse_github_workflow(workflow_path: Path) -> ImportedWorkflow:
    """Parse a GitHub Actions workflow file.

    Args:
        workflow_path: Path to the workflow YAML file

    Returns:
        ImportedWorkflow with parsed content

    Raises:
        WorkflowParseError: If parsing fails
    """
    if not workflow_path.exists():
        raise WorkflowParseError(f"Workflow file not found: {workflow_path}")

    try:
        with open(workflow_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise WorkflowParseError(f"Invalid YAML: {e}")

    if not data:
        raise WorkflowParseError("Empty workflow file")

    if not isinstance(data, dict):
        raise WorkflowParseError("Workflow must be a YAML mapping")

    # Extract workflow name
    workflow_name = data.get("name", workflow_path.stem)

    workflow = ImportedWorkflow(
        name=workflow_name,
        source_file=str(workflow_path),
    )

    # Extract workflow-level env
    if "env" in data and isinstance(data["env"], dict):
        workflow.env = {str(k): str(v) for k, v in data["env"].items()}

    # Parse jobs
    jobs_data = data.get("jobs", {})
    if not isinstance(jobs_data, dict):
        raise WorkflowParseError("'jobs' must be a mapping")

    for job_id, job_data in jobs_data.items():
        if not isinstance(job_data, dict):
            continue

        job = _parse_job(job_id, job_data)
        workflow.jobs.append(job)

        # Collect warnings about unsupported features
        for step in job.steps:
            if not step.supported:
                workflow.warnings.append(
                    f"Job '{job_id}' step '{step.name}': {'; '.join(step.notes)}"
                )

    return workflow


def _parse_job(job_id: str, job_data: dict) -> ImportedJob:
    """Parse a single job from workflow data."""
    job = ImportedJob(
        id=job_id,
        name=job_data.get("name", job_id),
        runs_on=str(job_data.get("runs-on", "")),
    )

    # Job-level env
    if "env" in job_data and isinstance(job_data["env"], dict):
        job.env = {str(k): str(v) for k, v in job_data["env"].items()}

    # Parse steps
    steps_data = job_data.get("steps", [])
    if not isinstance(steps_data, list):
        return job

    step_count = 0
    for step_data in steps_data:
        if not isinstance(step_data, dict):
            continue

        step_count += 1
        step = _parse_step(step_count, step_data)
        job.steps.append(step)

    return job


def _parse_step(step_num: int, step_data: dict) -> ImportedStep:
    """Parse a single step from job data."""
    step_id = f"step{step_num}"
    step_name = step_data.get("name", f"Step {step_num}")

    # Determine step type
    if "run" in step_data:
        # Shell command step - fully supported
        step = ImportedStep(
            id=step_id,
            name=step_name,
            type="shell",
            command=str(step_data["run"]),
            supported=True,
        )

        # Working directory
        if "working-directory" in step_data:
            step.cwd = str(step_data["working-directory"])

        # Shell type
        if "shell" in step_data:
            step.shell = str(step_data["shell"])

        # Environment variables
        if "env" in step_data and isinstance(step_data["env"], dict):
            step.env = {str(k): str(v) for k, v in step_data["env"].items()}

        # Conditional
        if "if" in step_data:
            step.condition = str(step_data["if"])
            step.notes.append(f"Has condition: {step.condition}")

    elif "uses" in step_data:
        # Action step - not directly supported
        action = str(step_data["uses"])
        step = ImportedStep(
            id=step_id,
            name=step_name,
            type="action",
            action=action,
            supported=False,
            notes=[f"Uses action '{action}' which cannot be directly converted"],
        )

        # Action inputs
        if "with" in step_data and isinstance(step_data["with"], dict):
            step.action_with = step_data["with"]

        # Environment
        if "env" in step_data and isinstance(step_data["env"], dict):
            step.env = {str(k): str(v) for k, v in step_data["env"].items()}

    else:
        # Unknown step type
        step = ImportedStep(
            id=step_id,
            name=step_name,
            type="unknown",
            supported=False,
            notes=["Unknown step type (no 'run' or 'uses')"],
        )

    return step


def convert_workflow_to_skill(
    workflow: ImportedWorkflow,
    output_dir: Path,
    job_id: Optional[str] = None,
) -> Path:
    """Convert an imported workflow to a SkillForge skill.

    Args:
        workflow: Parsed workflow
        output_dir: Directory to create skill in
        job_id: Optional specific job to convert (default: first job)

    Returns:
        Path to created skill directory
    """
    # Select job to convert
    if not workflow.jobs:
        raise WorkflowParseError("Workflow has no jobs")

    if job_id:
        job = next((j for j in workflow.jobs if j.id == job_id), None)
        if not job:
            raise WorkflowParseError(f"Job '{job_id}' not found in workflow")
    else:
        job = workflow.jobs[0]

    # Normalize skill name
    skill_name = _normalize_name(workflow.name)
    skill_dir = output_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (skill_dir / "fixtures" / "happy_path" / "input").mkdir(parents=True, exist_ok=True)
    (skill_dir / "fixtures" / "happy_path" / "expected").mkdir(parents=True, exist_ok=True)
    (skill_dir / "reports").mkdir(parents=True, exist_ok=True)
    (skill_dir / "cassettes").mkdir(parents=True, exist_ok=True)

    # Generate skill.yaml
    skill_data = _workflow_to_skill_data(workflow, job)
    skill_yaml = skill_dir / "skill.yaml"
    with open(skill_yaml, "w") as f:
        yaml.dump(skill_data, f, default_flow_style=False, sort_keys=False)

    # Generate SKILL.txt
    skill_txt = skill_dir / "SKILL.txt"
    skill_txt.write_text(_generate_skill_txt(workflow, job))

    # Generate checks.py
    checks_py = skill_dir / "checks.py"
    checks_py.write_text(_generate_checks_py(workflow.name))

    # Generate fixture.yaml
    fixture_yaml = skill_dir / "fixtures" / "happy_path" / "fixture.yaml"
    fixture_yaml.write_text(_generate_fixture_yaml())

    # Create .gitkeep files
    for gitkeep_dir in [
        skill_dir / "fixtures" / "happy_path" / "input",
        skill_dir / "fixtures" / "happy_path" / "expected",
        skill_dir / "reports",
        skill_dir / "cassettes",
    ]:
        (gitkeep_dir / ".gitkeep").write_text("")

    return skill_dir


def _normalize_name(name: str) -> str:
    """Normalize a name for use as directory name."""
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    safe_name = safe_name.strip("_").lower()
    # Collapse multiple underscores
    while "__" in safe_name:
        safe_name = safe_name.replace("__", "_")
    return safe_name or "imported_skill"


def _workflow_to_skill_data(workflow: ImportedWorkflow, job: ImportedJob) -> dict[str, Any]:
    """Convert workflow to skill.yaml data structure."""
    data: dict[str, Any] = {
        "name": _normalize_name(workflow.name),
        "version": "0.1.0",
        "description": f"Imported from GitHub Actions workflow: {workflow.name}",
    }

    # Add source info as metadata
    data["metadata"] = {
        "imported_from": "github-actions",
        "source_file": workflow.source_file,
        "source_job": job.id,
    }

    # Standard inputs
    data["inputs"] = [
        {
            "name": "target_dir",
            "type": "path",
            "description": "Target directory to run the skill against",
            "required": True,
        },
    ]

    # Preconditions based on runs-on
    if job.runs_on:
        data["preconditions"] = [
            f"Originally designed for: {job.runs_on}",
        ]

    # Combine environment variables
    combined_env = {}
    combined_env.update(workflow.env)
    combined_env.update(job.env)

    # Steps
    data["steps"] = []
    step_num = 0
    for step in job.steps:
        if step.type == "shell" and step.supported:
            step_num += 1
            step_data: dict[str, Any] = {
                "id": f"step{step_num}",
                "type": "shell",
                "name": step.name,
                "command": _convert_github_vars(step.command or ""),
                "cwd": "{sandbox_dir}",
            }

            # Add working directory if specified
            if step.cwd:
                step_data["cwd"] = _convert_github_vars(step.cwd)

            # Add step-level env vars
            step_env = {}
            step_env.update(combined_env)
            if step.env:
                step_env.update(step.env)
            if step_env:
                step_data["env"] = {k: _convert_github_vars(str(v)) for k, v in step_env.items()}

            data["steps"].append(step_data)

        elif step.type == "action":
            # Add as commented step
            step_num += 1
            data["steps"].append({
                "id": f"step{step_num}",
                "type": "shell",
                "name": f"[MANUAL] {step.name}",
                "command": f"echo 'TODO: Replace GitHub Action: {step.action}'",
                "cwd": "{sandbox_dir}",
                "_note": f"Originally used action: {step.action}",
            })

    # Checks - add exit code checks for shell steps
    data["checks"] = []
    for i, step in enumerate(data["steps"], 1):
        if not step.get("_note"):  # Skip action placeholders
            data["checks"].append({
                "id": f"check{i}",
                "type": "exit_code",
                "step_id": step["id"],
                "equals": 0,
            })

    return data


def _convert_github_vars(text: str) -> str:
    """Convert GitHub Actions variable syntax to SkillForge placeholders.

    GitHub uses:
    - ${{ github.workspace }} -> {sandbox_dir}
    - ${{ env.VAR }} -> {VAR} or leave as env var
    - $GITHUB_WORKSPACE -> {sandbox_dir}
    """
    if not text:
        return text

    # Convert ${{ github.workspace }} and $GITHUB_WORKSPACE
    text = text.replace("${{ github.workspace }}", "{sandbox_dir}")
    text = text.replace("${{github.workspace}}", "{sandbox_dir}")
    text = text.replace("$GITHUB_WORKSPACE", "{sandbox_dir}")

    # Convert ${{ github.event.* }} - leave as TODO
    import re
    text = re.sub(
        r"\$\{\{\s*github\.event\.[^}]+\s*\}\}",
        "{TODO_GITHUB_EVENT}",
        text
    )

    # Convert ${{ secrets.* }} - leave as TODO
    text = re.sub(
        r"\$\{\{\s*secrets\.[^}]+\s*\}\}",
        "{TODO_SECRET}",
        text
    )

    return text


def _generate_skill_txt(workflow: ImportedWorkflow, job: ImportedJob) -> str:
    """Generate SKILL.txt content."""
    lines = [
        f"SKILL: {_normalize_name(workflow.name)}",
        "=" * (7 + len(_normalize_name(workflow.name))),
        "",
        "DESCRIPTION",
        "-----------",
        f"Imported from GitHub Actions workflow: {workflow.name}",
        f"Source file: {workflow.source_file}",
        f"Job: {job.name} ({job.id})",
        "",
    ]

    if job.runs_on:
        lines.extend([
            "ORIGINAL ENVIRONMENT",
            "--------------------",
            f"Runs on: {job.runs_on}",
            "",
        ])

    lines.extend([
        "INPUTS",
        "------",
        "- target_dir: path (required) - Target directory",
        "",
        "STEPS",
        "-----",
    ])

    step_num = 0
    for step in job.steps:
        step_num += 1
        if step.type == "shell" and step.supported:
            lines.append(f"{step_num}. {step.name}")
            if step.command:
                # Truncate long commands
                cmd = step.command.split("\n")[0]
                if len(cmd) > 60:
                    cmd = cmd[:57] + "..."
                lines.append(f"   - Run: {cmd}")
        elif step.type == "action":
            lines.append(f"{step_num}. [ACTION] {step.name}")
            lines.append(f"   - Uses: {step.action}")
            lines.append("   - NOTE: Requires manual conversion")

    lines.append("")

    if workflow.warnings:
        lines.extend([
            "CONVERSION NOTES",
            "----------------",
        ])
        for warning in workflow.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    return "\n".join(lines)


def _generate_checks_py(name: str) -> str:
    """Generate checks.py content."""
    return f'''"""Custom checks for the {name} skill."""

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


def _generate_fixture_yaml() -> str:
    """Generate fixture.yaml content."""
    return """# Fixture configuration
# Override skill inputs for this fixture

# inputs:
#   target_dir: "."

# allow_extra_files: false
"""


def import_github_workflow(
    workflow_path: Path,
    output_dir: Path,
    job_id: Optional[str] = None,
) -> ImportResult:
    """Import a GitHub Actions workflow as a skill.

    Args:
        workflow_path: Path to the workflow YAML file
        output_dir: Directory to create skill in
        job_id: Optional specific job to import

    Returns:
        ImportResult with outcome details
    """
    result = ImportResult()

    try:
        # Parse workflow
        workflow = parse_github_workflow(workflow_path)
        result.workflow = workflow

        # Count steps
        for job in workflow.jobs:
            for step in job.steps:
                if step.supported:
                    result.steps_imported += 1
                else:
                    result.steps_skipped += 1

        # Convert to skill
        skill_dir = convert_workflow_to_skill(workflow, output_dir, job_id)

        result.success = True
        result.skill_dir = str(skill_dir)

    except WorkflowParseError as e:
        result.error_message = str(e)

    except Exception as e:
        result.error_message = f"Unexpected error: {e}"

    return result
