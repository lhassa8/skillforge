"""Step execution for SkillForge skills."""

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from skillforge.config import load_config
from skillforge.placeholders import substitute, substitute_dict


@dataclass
class StepResult:
    """Result of executing a single step."""

    step_id: str
    step_type: str
    status: str = "pending"  # "success", "failed", "skipped", "pending"
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    error_message: str = ""
    resolved_command: str = ""
    resolved_cwd: str = ""


class StepExecutionError(Exception):
    """Raised when step execution fails."""

    pass


def execute_step(
    step: dict[str, Any],
    context: dict[str, Any],
    logs_dir: Path,
    dry_run: bool = False,
    secret_manager: Optional[Any] = None,
    secret_masker: Optional[Any] = None,
) -> StepResult:
    """Execute a single step.

    Args:
        step: Step definition from skill.yaml
        context: Placeholder context for substitution
        logs_dir: Directory to write log files
        dry_run: If True, don't actually execute
        secret_manager: Optional SecretManager for {secret:name} resolution
        secret_masker: Optional SecretMasker for log redaction

    Returns:
        StepResult with execution details
    """
    step_id = step.get("id", "unknown")
    step_type = step.get("type", "unknown")

    # Resolve placeholders in step (including secrets)
    resolved_step = substitute_dict(step, context, secret_manager)

    if step_type == "shell":
        return _execute_shell_step(resolved_step, logs_dir, dry_run, secret_masker)
    elif step_type == "python":
        return _execute_python_step(resolved_step, logs_dir, dry_run, secret_masker)
    elif step_type == "file.replace":
        return _execute_file_replace_step(resolved_step, logs_dir, dry_run)
    elif step_type == "file.template":
        return _execute_file_template_step(resolved_step, context, logs_dir, dry_run, secret_manager)
    elif step_type == "json.patch":
        return _execute_json_patch_step(resolved_step, logs_dir, dry_run)
    elif step_type == "yaml.patch":
        return _execute_yaml_patch_step(resolved_step, logs_dir, dry_run)
    else:
        return StepResult(
            step_id=step_id,
            step_type=step_type,
            status="failed",
            error_message=f"Unknown step type: {step_type}",
        )


def _execute_shell_step(
    step: dict[str, Any],
    logs_dir: Path,
    dry_run: bool,
    secret_masker: Optional[Any] = None,
) -> StepResult:
    """Execute a shell step."""
    step_id = step.get("id", "unknown")
    command = step.get("command", "")
    cwd = step.get("cwd", ".")
    env_vars = step.get("env", {})
    timeout_sec = step.get("timeout_sec", 300)  # 5 minute default
    expect_exit = step.get("expect_exit", 0)
    allow_failure = step.get("allow_failure", False)

    # Mask command for logging (secrets may be in command)
    masked_command = command
    if secret_masker:
        masked_command = secret_masker.mask(command)

    result = StepResult(
        step_id=step_id,
        step_type="shell",
        resolved_command=masked_command,  # Store masked command in report
        resolved_cwd=cwd,
    )

    if dry_run:
        result.status = "skipped"
        return result

    # Build environment
    env = os.environ.copy()
    env.update(env_vars)

    start_time = time.time()

    try:
        proc = subprocess.run(
            command,  # Execute actual command with secrets
            shell=True,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

        result.exit_code = proc.returncode
        stdout = _truncate_output(proc.stdout)
        stderr = _truncate_output(proc.stderr)

        # Mask secrets in output
        if secret_masker:
            stdout = secret_masker.mask(stdout)
            stderr = secret_masker.mask(stderr)

        result.stdout = stdout
        result.stderr = stderr
        result.duration_ms = int((time.time() - start_time) * 1000)

        # Check exit code
        if proc.returncode != expect_exit:
            if allow_failure:
                result.status = "success"  # Allowed to fail
            else:
                result.status = "failed"
                result.error_message = f"Exit code {proc.returncode}, expected {expect_exit}"
        else:
            result.status = "success"

    except subprocess.TimeoutExpired:
        result.status = "failed"
        result.error_message = f"Command timed out after {timeout_sec}s"
        result.duration_ms = timeout_sec * 1000

    except Exception as e:
        result.status = "failed"
        error_msg = str(e)
        if secret_masker:
            error_msg = secret_masker.mask(error_msg)
        result.error_message = error_msg
        result.duration_ms = int((time.time() - start_time) * 1000)

    # Write logs
    _write_step_logs(step_id, result, logs_dir)

    return result


def _execute_python_step(
    step: dict[str, Any],
    logs_dir: Path,
    dry_run: bool,
    secret_masker: Optional[Any] = None,
) -> StepResult:
    """Execute a python step."""
    step_id = step.get("id", "unknown")
    module = step.get("module")
    file_path = step.get("file")
    function = step.get("function")
    args = step.get("args", [])
    cwd = step.get("cwd", ".")
    timeout_sec = step.get("timeout_sec", 300)

    result = StepResult(
        step_id=step_id,
        step_type="python",
        resolved_cwd=cwd,
    )

    if dry_run:
        result.status = "skipped"
        return result

    start_time = time.time()

    try:
        # Build python command
        if module:
            cmd = ["python", "-m", module] + args
            result.resolved_command = f"python -m {module} {' '.join(args)}"
        elif file_path:
            cmd = ["python", file_path] + args
            result.resolved_command = f"python {file_path} {' '.join(args)}"
        elif function:
            # function format: "module:function_name"
            mod, func = function.split(":", 1)
            cmd = ["python", "-c", f"from {mod} import {func}; {func}()"]
            result.resolved_command = f"python -c 'from {mod} import {func}; {func}()'"
        else:
            result.status = "failed"
            result.error_message = "Python step requires module, file, or function"
            return result

        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

        result.exit_code = proc.returncode
        stdout = _truncate_output(proc.stdout)
        stderr = _truncate_output(proc.stderr)

        # Mask secrets in output
        if secret_masker:
            stdout = secret_masker.mask(stdout)
            stderr = secret_masker.mask(stderr)

        result.stdout = stdout
        result.stderr = stderr
        result.duration_ms = int((time.time() - start_time) * 1000)

        if proc.returncode == 0:
            result.status = "success"
        else:
            result.status = "failed"
            result.error_message = f"Python exited with code {proc.returncode}"

    except subprocess.TimeoutExpired:
        result.status = "failed"
        result.error_message = f"Python timed out after {timeout_sec}s"

    except Exception as e:
        result.status = "failed"
        error_msg = str(e)
        if secret_masker:
            error_msg = secret_masker.mask(error_msg)
        result.error_message = error_msg

    result.duration_ms = int((time.time() - start_time) * 1000)
    _write_step_logs(step_id, result, logs_dir)

    return result


def _execute_file_replace_step(
    step: dict[str, Any],
    logs_dir: Path,
    dry_run: bool,
) -> StepResult:
    """Execute a file.replace step."""
    step_id = step.get("id", "unknown")
    file_path = step.get("path", "")
    pattern = step.get("pattern", "")
    replace_with = step.get("replace_with", "")

    result = StepResult(
        step_id=step_id,
        step_type="file.replace",
        resolved_command=f"Replace '{pattern}' with '{replace_with}' in {file_path}",
    )

    if dry_run:
        result.status = "skipped"
        return result

    start_time = time.time()

    try:
        path = Path(file_path)
        if not path.exists():
            result.status = "failed"
            result.error_message = f"File not found: {file_path}"
            return result

        content = path.read_text()
        new_content, count = re.subn(pattern, replace_with, content)

        if count == 0:
            result.stdout = "No matches found"
        else:
            path.write_text(new_content)
            result.stdout = f"Replaced {count} occurrence(s)"

        result.status = "success"
        result.exit_code = 0

    except Exception as e:
        result.status = "failed"
        result.error_message = str(e)

    result.duration_ms = int((time.time() - start_time) * 1000)
    _write_step_logs(step_id, result, logs_dir)

    return result


def _execute_file_template_step(
    step: dict[str, Any],
    context: dict[str, Any],
    logs_dir: Path,
    dry_run: bool,
    secret_manager: Optional[Any] = None,
) -> StepResult:
    """Execute a file.template step."""
    step_id = step.get("id", "unknown")
    file_path = step.get("path", "")
    template = step.get("template", "")
    template_file = step.get("template_file")
    mode = step.get("mode", "overwrite")

    result = StepResult(
        step_id=step_id,
        step_type="file.template",
        resolved_command=f"Write template to {file_path}",
    )

    if dry_run:
        result.status = "skipped"
        return result

    start_time = time.time()

    try:
        path = Path(file_path)

        # Check mode
        if mode == "if_missing" and path.exists():
            result.stdout = "File exists, skipping (mode=if_missing)"
            result.status = "success"
            result.exit_code = 0
            return result

        # Get template content
        if template_file:
            template_path = Path(template_file)
            if not template_path.exists():
                result.status = "failed"
                result.error_message = f"Template file not found: {template_file}"
                return result
            template = template_path.read_text()

        # Substitute placeholders in template (including secrets)
        content = substitute(template, context, secret_manager)

        # Write file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

        result.stdout = f"Wrote {len(content)} bytes to {file_path}"
        result.status = "success"
        result.exit_code = 0

    except Exception as e:
        result.status = "failed"
        result.error_message = str(e)

    result.duration_ms = int((time.time() - start_time) * 1000)
    _write_step_logs(step_id, result, logs_dir)

    return result


def _execute_json_patch_step(
    step: dict[str, Any],
    logs_dir: Path,
    dry_run: bool,
) -> StepResult:
    """Execute a json.patch step."""
    step_id = step.get("id", "unknown")
    file_path = step.get("path", "")
    operations = step.get("operations", [])

    result = StepResult(
        step_id=step_id,
        step_type="json.patch",
        resolved_command=f"Patch JSON file {file_path}",
    )

    if dry_run:
        result.status = "skipped"
        return result

    start_time = time.time()

    try:
        path = Path(file_path)
        if not path.exists():
            result.status = "failed"
            result.error_message = f"File not found: {file_path}"
            return result

        with open(path) as f:
            data = json.load(f)

        # Apply operations
        data = _apply_patch_operations(data, operations)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        result.stdout = f"Applied {len(operations)} operation(s)"
        result.status = "success"
        result.exit_code = 0

    except Exception as e:
        result.status = "failed"
        result.error_message = str(e)

    result.duration_ms = int((time.time() - start_time) * 1000)
    _write_step_logs(step_id, result, logs_dir)

    return result


def _execute_yaml_patch_step(
    step: dict[str, Any],
    logs_dir: Path,
    dry_run: bool,
) -> StepResult:
    """Execute a yaml.patch step."""
    step_id = step.get("id", "unknown")
    file_path = step.get("path", "")
    operations = step.get("operations", [])

    result = StepResult(
        step_id=step_id,
        step_type="yaml.patch",
        resolved_command=f"Patch YAML file {file_path}",
    )

    if dry_run:
        result.status = "skipped"
        return result

    start_time = time.time()

    try:
        path = Path(file_path)
        if not path.exists():
            result.status = "failed"
            result.error_message = f"File not found: {file_path}"
            return result

        with open(path) as f:
            data = yaml.safe_load(f)

        # Apply operations
        data = _apply_patch_operations(data, operations)

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        result.stdout = f"Applied {len(operations)} operation(s)"
        result.status = "success"
        result.exit_code = 0

    except Exception as e:
        result.status = "failed"
        result.error_message = str(e)

    result.duration_ms = int((time.time() - start_time) * 1000)
    _write_step_logs(step_id, result, logs_dir)

    return result


def _apply_patch_operations(data: Any, operations: list[dict]) -> Any:
    """Apply patch operations to data.

    Supports simple operations:
    - {"op": "add", "path": "/key", "value": ...}
    - {"op": "replace", "path": "/key", "value": ...}
    - {"op": "remove", "path": "/key"}
    - {"merge": {...}}  # Simple merge
    """
    if not isinstance(data, dict):
        data = {}

    for op in operations:
        if "merge" in op:
            # Simple merge operation
            data.update(op["merge"])
        elif "op" in op:
            op_type = op["op"]
            path = op.get("path", "").lstrip("/")
            value = op.get("value")

            if op_type in ("add", "replace"):
                if "/" in path:
                    # Nested path - simple implementation
                    keys = path.split("/")
                    target = data
                    for key in keys[:-1]:
                        if key not in target:
                            target[key] = {}
                        target = target[key]
                    target[keys[-1]] = value
                else:
                    data[path] = value

            elif op_type == "remove":
                if "/" in path:
                    keys = path.split("/")
                    target = data
                    for key in keys[:-1]:
                        target = target.get(key, {})
                    target.pop(keys[-1], None)
                else:
                    data.pop(path, None)

    return data


def _truncate_output(output: str, max_kb: int = 256) -> str:
    """Truncate output to max size."""
    max_bytes = max_kb * 1024
    if len(output) > max_bytes:
        return output[:max_bytes] + f"\n... (truncated, {len(output)} bytes total)"
    return output


def _write_step_logs(step_id: str, result: StepResult, logs_dir: Path) -> None:
    """Write step logs to files."""
    logs_dir.mkdir(parents=True, exist_ok=True)

    if result.stdout:
        stdout_file = logs_dir / f"step_{step_id}.stdout"
        stdout_file.write_text(result.stdout)

    if result.stderr:
        stderr_file = logs_dir / f"step_{step_id}.stderr"
        stderr_file.write_text(result.stderr)


def redact_secrets(text: str) -> str:
    """Redact potential secrets from text."""
    config = load_config()
    patterns = config.get("redact_patterns", [])

    for pattern in patterns:
        try:
            text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
        except re.error:
            pass  # Skip invalid patterns

    return text
