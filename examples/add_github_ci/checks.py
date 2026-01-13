"""Custom checks for the add_github_ci skill."""

from pathlib import Path
from typing import Any

import yaml


def check_valid_workflow_yaml(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify the CI workflow is valid YAML.

    Args:
        context: Dictionary containing execution context

    Returns:
        Tuple of (success: bool, message: str)
    """
    sandbox_dir = Path(context["sandbox_dir"])
    workflow_path = sandbox_dir / ".github" / "workflows" / "ci.yml"

    if not workflow_path.exists():
        return False, "ci.yml not found"

    try:
        content = workflow_path.read_text()
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            return False, "Workflow is not a valid YAML mapping"

        if "name" not in data:
            return False, "Workflow missing 'name' field"

        if "on" not in data:
            return False, "Workflow missing 'on' trigger field"

        if "jobs" not in data:
            return False, "Workflow missing 'jobs' field"

        return True, "Workflow YAML is valid"

    except yaml.YAMLError as e:
        return False, f"Invalid YAML: {e}"
    except Exception as e:
        return False, f"Error reading workflow: {e}"


def check_workflow_triggers(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify the workflow has proper triggers configured.

    Args:
        context: Dictionary containing execution context

    Returns:
        Tuple of (success: bool, message: str)
    """
    sandbox_dir = Path(context["sandbox_dir"])
    workflow_path = sandbox_dir / ".github" / "workflows" / "ci.yml"

    if not workflow_path.exists():
        return False, "ci.yml not found"

    try:
        content = workflow_path.read_text()
        data = yaml.safe_load(content)

        triggers = data.get("on", {})

        if isinstance(triggers, str):
            # Simple trigger like "on: push"
            return True, f"Trigger configured: {triggers}"

        if isinstance(triggers, list):
            return True, f"Triggers configured: {', '.join(triggers)}"

        if isinstance(triggers, dict):
            trigger_names = list(triggers.keys())
            if "push" not in trigger_names and "pull_request" not in trigger_names:
                return False, "Workflow should trigger on push or pull_request"
            return True, f"Triggers configured: {', '.join(trigger_names)}"

        return False, "Invalid trigger configuration"

    except Exception as e:
        return False, f"Error checking triggers: {e}"


def check_test_matrix(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify the workflow uses a test matrix.

    Args:
        context: Dictionary containing execution context

    Returns:
        Tuple of (success: bool, message: str)
    """
    sandbox_dir = Path(context["sandbox_dir"])
    workflow_path = sandbox_dir / ".github" / "workflows" / "ci.yml"

    if not workflow_path.exists():
        return False, "ci.yml not found"

    try:
        content = workflow_path.read_text()
        data = yaml.safe_load(content)

        jobs = data.get("jobs", {})
        for job_name, job_config in jobs.items():
            if isinstance(job_config, dict):
                strategy = job_config.get("strategy", {})
                if isinstance(strategy, dict) and "matrix" in strategy:
                    matrix = strategy["matrix"]
                    return True, f"Matrix strategy found in job '{job_name}'"

        return False, "No matrix strategy found in any job"

    except Exception as e:
        return False, f"Error checking matrix: {e}"


def check_dependabot_config(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify Dependabot configuration if enabled.

    Args:
        context: Dictionary containing execution context

    Returns:
        Tuple of (success: bool, message: str)
    """
    sandbox_dir = Path(context["sandbox_dir"])
    inputs = context.get("inputs", {})
    enable_dependabot = inputs.get("enable_dependabot", "true")

    dependabot_path = sandbox_dir / ".github" / "dependabot.yml"

    if enable_dependabot != "true":
        if dependabot_path.exists():
            return False, "Dependabot file exists but should be disabled"
        return True, "Dependabot correctly disabled"

    if not dependabot_path.exists():
        return False, "dependabot.yml not found but should exist"

    try:
        content = dependabot_path.read_text()
        data = yaml.safe_load(content)

        if data.get("version") != 2:
            return False, "Dependabot config should be version 2"

        updates = data.get("updates", [])
        if not updates:
            return False, "Dependabot config has no update rules"

        ecosystems = [u.get("package-ecosystem") for u in updates if isinstance(u, dict)]
        return True, f"Dependabot configured for: {', '.join(ecosystems)}"

    except Exception as e:
        return False, f"Error checking Dependabot config: {e}"
