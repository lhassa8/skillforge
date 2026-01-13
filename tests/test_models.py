"""Tests for the data models."""

import pytest

from skillforge.models import (
    InputType,
    StepType,
    CheckType,
    SkillInput,
    Step,
    Check,
    Skill,
)


class TestSkillInput:
    """Tests for SkillInput model."""

    def test_basic_input_to_dict(self):
        """Test basic input serialization."""
        inp = SkillInput(
            name="target_dir",
            type=InputType.PATH,
            description="Target directory",
        )
        result = inp.to_dict()

        assert result["name"] == "target_dir"
        assert result["type"] == "path"
        assert result["description"] == "Target directory"
        assert "required" not in result  # True is default, not serialized

    def test_optional_input_to_dict(self):
        """Test optional input serialization."""
        inp = SkillInput(
            name="verbose",
            type=InputType.BOOL,
            default=False,
            required=False,
        )
        result = inp.to_dict()

        assert result["required"] is False
        assert result["default"] is False

    def test_enum_input_to_dict(self):
        """Test enum input serialization."""
        inp = SkillInput(
            name="level",
            type=InputType.ENUM,
            enum_values=["low", "medium", "high"],
        )
        result = inp.to_dict()

        assert result["type"] == "enum"
        assert result["enum_values"] == ["low", "medium", "high"]


class TestStep:
    """Tests for Step model."""

    def test_shell_step_to_dict(self):
        """Test shell step serialization."""
        step = Step(
            id="run_tests",
            type=StepType.SHELL,
            name="Run tests",
            command="pytest",
            cwd="{target_dir}",
        )
        result = step.to_dict()

        assert result["id"] == "run_tests"
        assert result["type"] == "shell"
        assert result["name"] == "Run tests"
        assert result["command"] == "pytest"
        assert result["cwd"] == "{target_dir}"

    def test_shell_step_with_expect_exit(self):
        """Test shell step with non-zero expected exit code."""
        step = Step(
            id="check_fail",
            type=StepType.SHELL,
            command="exit 1",
            expect_exit=1,
        )
        result = step.to_dict()

        assert result["expect_exit"] == 1

    def test_file_replace_step_to_dict(self):
        """Test file.replace step serialization."""
        step = Step(
            id="update_version",
            type=StepType.FILE_REPLACE,
            path="version.txt",
            pattern=r"\d+\.\d+\.\d+",
            replace_with="1.0.0",
        )
        result = step.to_dict()

        assert result["type"] == "file.replace"
        assert result["path"] == "version.txt"
        assert result["pattern"] == r"\d+\.\d+\.\d+"
        assert result["replace_with"] == "1.0.0"

    def test_step_with_env(self):
        """Test step with environment variables."""
        step = Step(
            id="build",
            type=StepType.SHELL,
            command="make build",
            env={"DEBUG": "1", "CI": "true"},
        )
        result = step.to_dict()

        assert result["env"] == {"DEBUG": "1", "CI": "true"}

    def test_step_with_timeout(self):
        """Test step with timeout."""
        step = Step(
            id="long_task",
            type=StepType.SHELL,
            command="sleep 100",
            timeout_sec=60,
        )
        result = step.to_dict()

        assert result["timeout_sec"] == 60


class TestCheck:
    """Tests for Check model."""

    def test_file_exists_check_to_dict(self):
        """Test file_exists check serialization."""
        check = Check(
            id="check_output",
            type=CheckType.FILE_EXISTS,
            path="output.txt",
        )
        result = check.to_dict()

        assert result["id"] == "check_output"
        assert result["type"] == "file_exists"
        assert result["path"] == "output.txt"

    def test_file_contains_check_to_dict(self):
        """Test file_contains check serialization."""
        check = Check(
            id="check_content",
            type=CheckType.FILE_CONTAINS,
            path="README.md",
            contains="# Project",
        )
        result = check.to_dict()

        assert result["type"] == "file_contains"
        assert result["contains"] == "# Project"

    def test_git_clean_check_to_dict(self):
        """Test git_clean check serialization."""
        check = Check(
            id="check_clean",
            type=CheckType.GIT_CLEAN,
            cwd="{target_dir}",
        )
        result = check.to_dict()

        assert result["type"] == "git_clean"
        assert result["cwd"] == "{target_dir}"

    def test_exit_code_check_to_dict(self):
        """Test exit_code check serialization."""
        check = Check(
            id="check_exit",
            type=CheckType.EXIT_CODE,
            step_id="run_tests",
            equals=0,
        )
        result = check.to_dict()

        assert result["type"] == "exit_code"
        assert result["step_id"] == "run_tests"
        assert result["equals"] == 0


class TestSkill:
    """Tests for Skill model."""

    def test_minimal_skill_to_dict(self):
        """Test minimal skill serialization."""
        skill = Skill(name="test_skill")
        result = skill.to_dict()

        assert result["name"] == "test_skill"
        assert result["version"] == "0.1.0"

    def test_complete_skill_to_dict(self):
        """Test complete skill serialization."""
        skill = Skill(
            name="release_prep",
            version="1.0.0",
            description="Prepare repository for release",
            requirements={"commands": ["git", "npm"]},
            inputs=[
                SkillInput(name="target_dir", type=InputType.PATH),
            ],
            preconditions=["Git repository exists"],
            steps=[
                Step(id="test", type=StepType.SHELL, command="npm test"),
            ],
            checks=[
                Check(id="check_exit", type=CheckType.EXIT_CODE, step_id="test", equals=0),
            ],
            metadata={"author": "test"},
        )
        result = skill.to_dict()

        assert result["name"] == "release_prep"
        assert result["version"] == "1.0.0"
        assert result["description"] == "Prepare repository for release"
        assert result["requirements"] == {"commands": ["git", "npm"]}
        assert len(result["inputs"]) == 1
        assert len(result["steps"]) == 1
        assert len(result["checks"]) == 1
        assert result["metadata"] == {"author": "test"}
