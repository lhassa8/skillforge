"""Data models for SkillForge skills."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class InputType(str, Enum):
    """Supported input types for skill parameters."""

    STRING = "string"
    ENUM = "enum"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    PATH = "path"


class StepType(str, Enum):
    """Supported step types."""

    SHELL = "shell"
    PYTHON = "python"
    FILE_REPLACE = "file.replace"
    FILE_TEMPLATE = "file.template"
    JSON_PATCH = "json.patch"
    YAML_PATCH = "yaml.patch"


class CheckType(str, Enum):
    """Supported check types."""

    FILE_EXISTS = "file_exists"
    FILE_CONTAINS = "file_contains"
    GIT_CLEAN = "git_clean"
    STDOUT_CONTAINS = "stdout_contains"
    EXIT_CODE = "exit_code"


@dataclass
class SkillInput:
    """Definition of a skill input parameter."""

    name: str
    type: InputType
    description: str = ""
    default: Optional[Any] = None
    enum_values: Optional[list[str]] = None
    required: bool = True
    pattern: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type.value,
        }
        if self.description:
            result["description"] = self.description
        if self.default is not None:
            result["default"] = self.default
        if self.enum_values:
            result["enum_values"] = self.enum_values
        if not self.required:
            result["required"] = False
        if self.pattern:
            result["pattern"] = self.pattern
        return result


@dataclass
class Step:
    """Definition of a skill step."""

    id: str
    type: StepType
    name: str = ""
    cwd: Optional[str] = None
    env: Optional[dict[str, str]] = None
    timeout_sec: Optional[int] = None
    allow_failure: bool = False

    # Type-specific fields
    command: Optional[str] = None  # shell
    expect_exit: int = 0  # shell
    module: Optional[str] = None  # python
    file: Optional[str] = None  # python
    function: Optional[str] = None  # python
    args: Optional[list[str]] = None  # python
    path: Optional[str] = None  # file.replace, file.template, json.patch, yaml.patch
    pattern: Optional[str] = None  # file.replace
    replace_with: Optional[str] = None  # file.replace
    template: Optional[str] = None  # file.template
    template_file: Optional[str] = None  # file.template
    mode: Optional[str] = None  # file.template
    operations: Optional[list[dict[str, Any]]] = None  # json.patch, yaml.patch

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
        }
        if self.name:
            result["name"] = self.name
        if self.cwd:
            result["cwd"] = self.cwd
        if self.env:
            result["env"] = self.env
        if self.timeout_sec:
            result["timeout_sec"] = self.timeout_sec
        if self.allow_failure:
            result["allow_failure"] = True

        # Type-specific fields
        if self.type == StepType.SHELL:
            if self.command:
                result["command"] = self.command
            if self.expect_exit != 0:
                result["expect_exit"] = self.expect_exit
        elif self.type == StepType.PYTHON:
            if self.module:
                result["module"] = self.module
            if self.file:
                result["file"] = self.file
            if self.function:
                result["function"] = self.function
            if self.args:
                result["args"] = self.args
        elif self.type == StepType.FILE_REPLACE:
            if self.path:
                result["path"] = self.path
            if self.pattern:
                result["pattern"] = self.pattern
            if self.replace_with is not None:
                result["replace_with"] = self.replace_with
        elif self.type == StepType.FILE_TEMPLATE:
            if self.path:
                result["path"] = self.path
            if self.template:
                result["template"] = self.template
            if self.template_file:
                result["template_file"] = self.template_file
            if self.mode:
                result["mode"] = self.mode
        elif self.type in (StepType.JSON_PATCH, StepType.YAML_PATCH):
            if self.path:
                result["path"] = self.path
            if self.operations:
                result["operations"] = self.operations

        return result


@dataclass
class Check:
    """Definition of a skill check."""

    id: str
    type: CheckType

    # Type-specific fields
    path: Optional[str] = None  # file_exists, file_contains
    contains: Optional[str] = None  # file_contains, stdout_contains
    regex: Optional[str] = None  # file_contains, stdout_contains
    cwd: Optional[str] = None  # git_clean
    step_id: Optional[str] = None  # stdout_contains, exit_code
    equals: Optional[int] = None  # exit_code

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
        }

        if self.type == CheckType.FILE_EXISTS:
            if self.path:
                result["path"] = self.path
        elif self.type == CheckType.FILE_CONTAINS:
            if self.path:
                result["path"] = self.path
            if self.contains:
                result["contains"] = self.contains
            if self.regex:
                result["regex"] = self.regex
        elif self.type == CheckType.GIT_CLEAN:
            if self.cwd:
                result["cwd"] = self.cwd
        elif self.type == CheckType.STDOUT_CONTAINS:
            if self.step_id:
                result["step_id"] = self.step_id
            if self.contains:
                result["contains"] = self.contains
            if self.regex:
                result["regex"] = self.regex
        elif self.type == CheckType.EXIT_CODE:
            if self.step_id:
                result["step_id"] = self.step_id
            if self.equals is not None:
                result["equals"] = self.equals

        return result


@dataclass
class Skill:
    """Complete skill definition."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    requirements: dict[str, list[str]] = field(default_factory=dict)
    inputs: list[SkillInput] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {
            "name": self.name,
            "version": self.version,
        }
        if self.description:
            result["description"] = self.description
        if self.requirements:
            result["requirements"] = self.requirements
        if self.inputs:
            result["inputs"] = [i.to_dict() for i in self.inputs]
        if self.preconditions:
            result["preconditions"] = self.preconditions
        if self.steps:
            result["steps"] = [s.to_dict() for s in self.steps]
        if self.checks:
            result["checks"] = [c.to_dict() for c in self.checks]
        if self.metadata:
            result["metadata"] = self.metadata
        return result
