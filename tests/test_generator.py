"""Tests for the generate command."""

import pytest
import yaml

from skillforge.generator import (
    ParsedInput,
    ParsedStep,
    ParsedCheck,
    ParsedSpec,
    SpecParseError,
    parse_spec_content,
    parse_spec_file,
    generate_skill_from_spec,
)


class TestParseSpecContent:
    """Tests for parsing spec content."""

    def test_parse_minimal_spec(self):
        """Test parsing a minimal spec."""
        content = """
SKILL: my_skill
"""
        spec = parse_spec_content(content)

        assert spec.name == "my_skill"

    def test_parse_skill_with_description(self):
        """Test parsing skill with description."""
        content = """
SKILL: my_skill
DESCRIPTION: This is a test skill
VERSION: 1.0.0
"""
        spec = parse_spec_content(content)

        assert spec.name == "my_skill"
        assert spec.description == "This is a test skill"
        assert spec.version == "1.0.0"

    def test_parse_inputs(self):
        """Test parsing input definitions."""
        content = """
SKILL: my_skill

INPUTS:
- target_dir: path (required) - Target directory
- message: string (default: "hello") - Message to display
- count: integer - Number of items
"""
        spec = parse_spec_content(content)

        assert len(spec.inputs) == 3

        assert spec.inputs[0].name == "target_dir"
        assert spec.inputs[0].type == "path"
        assert spec.inputs[0].required is True

        assert spec.inputs[1].name == "message"
        assert spec.inputs[1].type == "string"
        assert spec.inputs[1].default == "hello"
        assert spec.inputs[1].required is False

        assert spec.inputs[2].name == "count"
        assert spec.inputs[2].type == "integer"

    def test_parse_preconditions(self):
        """Test parsing preconditions."""
        content = """
SKILL: my_skill

PRECONDITIONS:
- Git must be installed
- Target directory must exist
- Node.js version 16+
"""
        spec = parse_spec_content(content)

        assert len(spec.preconditions) == 3
        assert "Git must be installed" in spec.preconditions
        assert "Target directory must exist" in spec.preconditions

    def test_parse_requirements(self):
        """Test parsing requirements."""
        content = """
SKILL: my_skill

REQUIREMENTS:
- commands: git, npm, node
- files: package.json
"""
        spec = parse_spec_content(content)

        assert "commands" in spec.requirements
        assert "git" in spec.requirements["commands"]
        assert "npm" in spec.requirements["commands"]

    def test_parse_shell_steps(self):
        """Test parsing shell steps."""
        content = """
SKILL: my_skill

STEPS:
1. Initialize project
   shell: npm init -y
   cwd: {target_dir}

2. Install dependencies
   shell: npm install
"""
        spec = parse_spec_content(content)

        assert len(spec.steps) == 2

        assert spec.steps[0].id == "step1"
        assert spec.steps[0].name == "Initialize project"
        assert spec.steps[0].type == "shell"
        assert spec.steps[0].command == "npm init -y"
        assert spec.steps[0].cwd == "{target_dir}"

        assert spec.steps[1].id == "step2"
        assert spec.steps[1].command == "npm install"

    def test_parse_template_step(self):
        """Test parsing file template step."""
        content = """
SKILL: my_skill

STEPS:
1. Create config
   template: {sandbox_dir}/config.json
   content: |
       {"name": "test"}
"""
        spec = parse_spec_content(content)

        assert len(spec.steps) == 1
        assert spec.steps[0].type == "file.template"
        assert spec.steps[0].path == "{sandbox_dir}/config.json"
        assert '{"name": "test"}' in spec.steps[0].template

    def test_parse_checks(self):
        """Test parsing checks."""
        content = """
SKILL: my_skill

CHECKS:
- file_exists: {sandbox_dir}/package.json
- exit_code: step1 equals 0
- stdout_contains: step1 pattern "success"
- file_contains: {sandbox_dir}/output.txt pattern "done"
"""
        spec = parse_spec_content(content)

        assert len(spec.checks) == 4

        assert spec.checks[0].type == "file_exists"
        assert spec.checks[0].path == "{sandbox_dir}/package.json"

        assert spec.checks[1].type == "exit_code"
        assert spec.checks[1].step_id == "step1"
        assert spec.checks[1].equals == 0

        assert spec.checks[2].type == "stdout_contains"
        assert spec.checks[2].step_id == "step1"
        assert spec.checks[2].pattern == "success"

        assert spec.checks[3].type == "file_contains"
        assert spec.checks[3].path == "{sandbox_dir}/output.txt"
        assert spec.checks[3].pattern == "done"

    def test_parse_complete_spec(self):
        """Test parsing a complete spec file."""
        content = """
SKILL: npm_init
DESCRIPTION: Initialize an npm project
VERSION: 1.0.0

INPUTS:
- target_dir: path (required) - Target directory
- name: string (default: "my-project") - Project name

PRECONDITIONS:
- npm must be installed
- Target directory must exist

REQUIREMENTS:
- commands: npm

STEPS:
1. Initialize npm
   shell: npm init -y
   cwd: {sandbox_dir}

2. Set project name
   shell: npm pkg set name={name}
   cwd: {sandbox_dir}

CHECKS:
- file_exists: {sandbox_dir}/package.json
- exit_code: step1 equals 0
- file_contains: {sandbox_dir}/package.json pattern "{name}"
"""
        spec = parse_spec_content(content)

        assert spec.name == "npm_init"
        assert spec.description == "Initialize an npm project"
        assert spec.version == "1.0.0"
        assert len(spec.inputs) == 2
        assert len(spec.preconditions) == 2
        assert len(spec.steps) == 2
        assert len(spec.checks) == 3

    def test_parse_empty_spec_raises_error(self):
        """Test that empty spec raises error."""
        content = ""

        with pytest.raises(SpecParseError, match="must have a SKILL"):
            parse_spec_content(content)

    def test_parse_comments_ignored(self):
        """Test that comments are ignored."""
        content = """
# This is a comment
SKILL: my_skill
# Another comment
DESCRIPTION: Test
"""
        spec = parse_spec_content(content)

        assert spec.name == "my_skill"
        assert spec.description == "Test"

    def test_parse_step_with_timeout(self):
        """Test parsing step with timeout."""
        content = """
SKILL: my_skill

STEPS:
1. Long running task
   shell: sleep 10
   timeout: 30
"""
        spec = parse_spec_content(content)

        assert spec.steps[0].timeout_sec == 30


class TestParseSpecFile:
    """Tests for parsing spec files from disk."""

    def test_parse_existing_file(self, tmp_path):
        """Test parsing an existing spec file."""
        spec_file = tmp_path / "spec.txt"
        spec_file.write_text("""
SKILL: file_test
DESCRIPTION: Test from file
""")

        spec = parse_spec_file(spec_file)

        assert spec.name == "file_test"
        assert spec.description == "Test from file"

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing a non-existent file raises error."""
        spec_file = tmp_path / "nonexistent.txt"

        with pytest.raises(SpecParseError, match="not found"):
            parse_spec_file(spec_file)


class TestGenerateSkillFromSpec:
    """Tests for generating skills from specs."""

    def test_generate_creates_directory(self, tmp_path):
        """Test that generate creates skill directory."""
        spec = ParsedSpec(name="my_skill")

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        assert skill_dir.exists()
        assert skill_dir.name == "my_skill"

    def test_generate_creates_skill_yaml(self, tmp_path):
        """Test that generate creates skill.yaml."""
        spec = ParsedSpec(
            name="my_skill",
            description="Test skill",
            version="1.0.0",
        )

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        skill_yaml = skill_dir / "skill.yaml"
        assert skill_yaml.exists()

        with open(skill_yaml) as f:
            data = yaml.safe_load(f)

        assert data["name"] == "my_skill"
        assert data["description"] == "Test skill"
        assert data["version"] == "1.0.0"

    def test_generate_creates_skill_txt(self, tmp_path):
        """Test that generate creates SKILL.txt."""
        spec = ParsedSpec(
            name="my_skill",
            description="Test skill",
        )

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        skill_txt = skill_dir / "SKILL.txt"
        assert skill_txt.exists()
        content = skill_txt.read_text()
        assert "my_skill" in content
        assert "Test skill" in content

    def test_generate_creates_checks_py(self, tmp_path):
        """Test that generate creates checks.py."""
        spec = ParsedSpec(name="my_skill")

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        checks_py = skill_dir / "checks.py"
        assert checks_py.exists()
        content = checks_py.read_text()
        assert "def custom_check" in content

    def test_generate_creates_fixtures(self, tmp_path):
        """Test that generate creates fixtures directory."""
        spec = ParsedSpec(name="my_skill")

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        assert (skill_dir / "fixtures" / "happy_path" / "input").exists()
        assert (skill_dir / "fixtures" / "happy_path" / "expected").exists()
        assert (skill_dir / "fixtures" / "happy_path" / "fixture.yaml").exists()

    def test_generate_creates_reports_and_cassettes(self, tmp_path):
        """Test that generate creates reports and cassettes directories."""
        spec = ParsedSpec(name="my_skill")

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        assert (skill_dir / "reports").exists()
        assert (skill_dir / "cassettes").exists()

    def test_generate_with_inputs(self, tmp_path):
        """Test that generate includes inputs in skill.yaml."""
        spec = ParsedSpec(
            name="my_skill",
            inputs=[
                ParsedInput(name="target_dir", type="path", required=True),
                ParsedInput(name="message", type="string", default="hello"),
            ],
        )

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert len(data["inputs"]) == 2
        assert data["inputs"][0]["name"] == "target_dir"
        assert data["inputs"][1]["default"] == "hello"

    def test_generate_with_steps(self, tmp_path):
        """Test that generate includes steps in skill.yaml."""
        spec = ParsedSpec(
            name="my_skill",
            steps=[
                ParsedStep(
                    id="step1",
                    name="Run command",
                    type="shell",
                    command="echo hello",
                    cwd="{sandbox_dir}",
                ),
            ],
        )

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert len(data["steps"]) == 1
        assert data["steps"][0]["id"] == "step1"
        assert data["steps"][0]["type"] == "shell"
        assert data["steps"][0]["command"] == "echo hello"

    def test_generate_with_checks(self, tmp_path):
        """Test that generate includes checks in skill.yaml."""
        spec = ParsedSpec(
            name="my_skill",
            checks=[
                ParsedCheck(
                    id="check1",
                    type="file_exists",
                    path="{sandbox_dir}/output.txt",
                ),
                ParsedCheck(
                    id="check2",
                    type="exit_code",
                    step_id="step1",
                    equals=0,
                ),
            ],
        )

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert len(data["checks"]) == 2
        assert data["checks"][0]["type"] == "file_exists"
        assert data["checks"][1]["type"] == "exit_code"
        assert data["checks"][1]["equals"] == 0

    def test_generate_normalizes_name(self, tmp_path):
        """Test that generate normalizes skill name for directory."""
        spec = ParsedSpec(name="My Skill Name!")

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        assert skill_dir.name == "my_skill_name"

    def test_generate_valid_skill_yaml(self, tmp_path):
        """Test that generated skill.yaml is valid for linting."""
        spec = ParsedSpec(
            name="test_skill",
            description="A test skill",
            inputs=[
                ParsedInput(name="target_dir", type="path", required=True),
            ],
            steps=[
                ParsedStep(
                    id="step1",
                    name="Echo test",
                    type="shell",
                    command="echo test",
                ),
            ],
            checks=[
                ParsedCheck(
                    id="check1",
                    type="exit_code",
                    step_id="step1",
                    equals=0,
                ),
            ],
        )

        skill_dir = generate_skill_from_spec(spec, tmp_path)

        # Load and validate structure
        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert "name" in data
        assert "steps" in data
        assert "checks" in data


class TestParsedInput:
    """Tests for ParsedInput parsing."""

    def test_parse_simple_input(self):
        """Test parsing simple input."""
        from skillforge.generator import _parse_input_line

        inp = _parse_input_line("target_dir: path (required) - Target directory")

        assert inp.name == "target_dir"
        assert inp.type == "path"
        assert inp.required is True
        assert inp.description == "Target directory"

    def test_parse_input_with_default(self):
        """Test parsing input with default value."""
        from skillforge.generator import _parse_input_line

        inp = _parse_input_line('message: string (default: "hello") - Message')

        assert inp.name == "message"
        assert inp.default == "hello"
        assert inp.required is False

    def test_parse_input_optional(self):
        """Test parsing optional input."""
        from skillforge.generator import _parse_input_line

        inp = _parse_input_line("config: string (optional) - Config file")

        assert inp.name == "config"
        assert inp.required is False


class TestParsedCheck:
    """Tests for check parsing."""

    def test_parse_file_exists_check(self):
        """Test parsing file_exists check."""
        from skillforge.generator import _parse_check_line

        check = _parse_check_line("file_exists: {sandbox_dir}/output.txt", 1)

        assert check.type == "file_exists"
        assert check.path == "{sandbox_dir}/output.txt"

    def test_parse_exit_code_check(self):
        """Test parsing exit_code check."""
        from skillforge.generator import _parse_check_line

        check = _parse_check_line("exit_code: step1 equals 0", 1)

        assert check.type == "exit_code"
        assert check.step_id == "step1"
        assert check.equals == 0

    def test_parse_stdout_contains_check(self):
        """Test parsing stdout_contains check."""
        from skillforge.generator import _parse_check_line

        check = _parse_check_line('stdout_contains: step1 pattern "success"', 1)

        assert check.type == "stdout_contains"
        assert check.step_id == "step1"
        assert check.pattern == "success"

    def test_parse_file_contains_check(self):
        """Test parsing file_contains check."""
        from skillforge.generator import _parse_check_line

        check = _parse_check_line('file_contains: {sandbox_dir}/out.txt pattern "done"', 1)

        assert check.type == "file_contains"
        assert check.path == "{sandbox_dir}/out.txt"
        assert check.pattern == "done"


class TestIntegration:
    """Integration tests for generate command."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow: parse spec, generate skill, validate output."""
        spec_content = """
SKILL: integration_test
DESCRIPTION: Integration test skill
VERSION: 2.0.0

INPUTS:
- target_dir: path (required) - Target directory
- greeting: string (default: "Hello") - Greeting message

PRECONDITIONS:
- Target directory must exist

STEPS:
1. Print greeting
   shell: echo {greeting}
   cwd: {sandbox_dir}

2. Create output file
   shell: echo {greeting} > output.txt
   cwd: {sandbox_dir}

CHECKS:
- exit_code: step1 equals 0
- file_exists: {sandbox_dir}/output.txt
"""
        spec_file = tmp_path / "spec.txt"
        spec_file.write_text(spec_content)

        # Parse
        spec = parse_spec_file(spec_file)
        assert spec.name == "integration_test"

        # Generate
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        skill_dir = generate_skill_from_spec(spec, output_dir)

        # Validate
        assert skill_dir.exists()
        assert (skill_dir / "skill.yaml").exists()
        assert (skill_dir / "SKILL.txt").exists()
        assert (skill_dir / "checks.py").exists()

        # Verify skill.yaml content
        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "integration_test"
        assert data["version"] == "2.0.0"
        assert len(data["inputs"]) == 2
        assert len(data["steps"]) == 2
        assert len(data["checks"]) == 2
