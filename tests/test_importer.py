"""Tests for the import command."""

import pytest
import yaml

from skillforge.importer import (
    ImportedStep,
    ImportedJob,
    ImportedWorkflow,
    ImportResult,
    WorkflowParseError,
    parse_github_workflow,
    convert_workflow_to_skill,
    import_github_workflow,
    _normalize_name,
    _convert_github_vars,
)


def create_workflow_file(tmp_path, content: str, name: str = "workflow.yml"):
    """Helper to create a workflow file."""
    workflow_file = tmp_path / name
    workflow_file.write_text(content)
    return workflow_file


class TestParseGithubWorkflow:
    """Tests for parsing GitHub Actions workflows."""

    def test_parse_minimal_workflow(self, tmp_path):
        """Test parsing a minimal workflow."""
        content = """
name: Test Workflow
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        workflow_file = create_workflow_file(tmp_path, content)

        workflow = parse_github_workflow(workflow_file)

        assert workflow.name == "Test Workflow"
        assert len(workflow.jobs) == 1
        assert workflow.jobs[0].id == "build"

    def test_parse_workflow_with_shell_steps(self, tmp_path):
        """Test parsing workflow with shell steps."""
        content = """
name: Build
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        run: git checkout
      - name: Build
        run: npm run build
        working-directory: ./app
"""
        workflow_file = create_workflow_file(tmp_path, content)

        workflow = parse_github_workflow(workflow_file)

        assert len(workflow.jobs[0].steps) == 2

        step1 = workflow.jobs[0].steps[0]
        assert step1.name == "Checkout"
        assert step1.type == "shell"
        assert step1.command == "git checkout"
        assert step1.supported is True

        step2 = workflow.jobs[0].steps[1]
        assert step2.name == "Build"
        assert step2.cwd == "./app"

    def test_parse_workflow_with_action_steps(self, tmp_path):
        """Test parsing workflow with action steps."""
        content = """
name: CI
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
      - run: npm test
"""
        workflow_file = create_workflow_file(tmp_path, content)

        workflow = parse_github_workflow(workflow_file)

        assert len(workflow.jobs[0].steps) == 3

        # Action steps are not supported
        step1 = workflow.jobs[0].steps[0]
        assert step1.type == "action"
        assert step1.action == "actions/checkout@v4"
        assert step1.supported is False

        step2 = workflow.jobs[0].steps[1]
        assert step2.action == "actions/setup-node@v4"
        assert step2.action_with == {"node-version": 18}
        assert step2.supported is False

        # Shell step is supported
        step3 = workflow.jobs[0].steps[2]
        assert step3.type == "shell"
        assert step3.supported is True

    def test_parse_workflow_with_env_vars(self, tmp_path):
        """Test parsing workflow with environment variables."""
        content = """
name: Build
on: push
env:
  GLOBAL_VAR: global_value
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      JOB_VAR: job_value
    steps:
      - name: Build
        run: echo $BUILD_VAR
        env:
          BUILD_VAR: step_value
"""
        workflow_file = create_workflow_file(tmp_path, content)

        workflow = parse_github_workflow(workflow_file)

        assert workflow.env == {"GLOBAL_VAR": "global_value"}
        assert workflow.jobs[0].env == {"JOB_VAR": "job_value"}
        assert workflow.jobs[0].steps[0].env == {"BUILD_VAR": "step_value"}

    def test_parse_workflow_with_multiple_jobs(self, tmp_path):
        """Test parsing workflow with multiple jobs."""
        content = """
name: CI Pipeline
on: push
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: npm run lint
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm run build
"""
        workflow_file = create_workflow_file(tmp_path, content)

        workflow = parse_github_workflow(workflow_file)

        assert len(workflow.jobs) == 3
        job_ids = {j.id for j in workflow.jobs}
        assert job_ids == {"lint", "test", "build"}

    def test_parse_workflow_with_conditional_steps(self, tmp_path):
        """Test parsing workflow with conditional steps."""
        content = """
name: Deploy
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: ./deploy.sh
        if: github.ref == 'refs/heads/main'
"""
        workflow_file = create_workflow_file(tmp_path, content)

        workflow = parse_github_workflow(workflow_file)

        step = workflow.jobs[0].steps[0]
        assert step.condition == "github.ref == 'refs/heads/main'"
        assert "Has condition" in step.notes[0]

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing non-existent file raises error."""
        with pytest.raises(WorkflowParseError, match="not found"):
            parse_github_workflow(tmp_path / "nonexistent.yml")

    def test_parse_invalid_yaml(self, tmp_path):
        """Test parsing invalid YAML raises error."""
        content = "not: valid: yaml: {{"
        workflow_file = create_workflow_file(tmp_path, content)

        with pytest.raises(WorkflowParseError, match="Invalid YAML"):
            parse_github_workflow(workflow_file)

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file raises error."""
        workflow_file = create_workflow_file(tmp_path, "")

        with pytest.raises(WorkflowParseError, match="Empty"):
            parse_github_workflow(workflow_file)

    def test_parse_workflow_generates_warnings(self, tmp_path):
        """Test that unsupported features generate warnings."""
        content = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
"""
        workflow_file = create_workflow_file(tmp_path, content)

        workflow = parse_github_workflow(workflow_file)

        assert len(workflow.warnings) == 2
        assert "actions/checkout" in workflow.warnings[0]


class TestConvertWorkflowToSkill:
    """Tests for converting workflows to skills."""

    def test_convert_creates_skill_directory(self, tmp_path):
        """Test that conversion creates skill directory."""
        workflow = ImportedWorkflow(
            name="Test Workflow",
            jobs=[
                ImportedJob(
                    id="build",
                    name="Build",
                    steps=[
                        ImportedStep(id="step1", name="Build", type="shell", command="npm run build"),
                    ],
                ),
            ],
        )

        skill_dir = convert_workflow_to_skill(workflow, tmp_path)

        assert skill_dir.exists()
        assert (skill_dir / "skill.yaml").exists()
        assert (skill_dir / "SKILL.txt").exists()
        assert (skill_dir / "checks.py").exists()

    def test_convert_creates_skill_yaml(self, tmp_path):
        """Test that conversion creates valid skill.yaml."""
        workflow = ImportedWorkflow(
            name="My CI",
            source_file="/path/to/workflow.yml",
            jobs=[
                ImportedJob(
                    id="build",
                    name="Build Job",
                    runs_on="ubuntu-latest",
                    steps=[
                        ImportedStep(id="step1", name="Build", type="shell", command="npm run build"),
                    ],
                ),
            ],
        )

        skill_dir = convert_workflow_to_skill(workflow, tmp_path)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "my_ci"
        assert "Imported from GitHub Actions" in data["description"]
        assert data["metadata"]["imported_from"] == "github-actions"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["command"] == "npm run build"

    def test_convert_includes_checks(self, tmp_path):
        """Test that conversion includes exit code checks."""
        workflow = ImportedWorkflow(
            name="Test",
            jobs=[
                ImportedJob(
                    id="build",
                    name="Build",
                    steps=[
                        ImportedStep(id="step1", name="Step 1", type="shell", command="echo 1"),
                        ImportedStep(id="step2", name="Step 2", type="shell", command="echo 2"),
                    ],
                ),
            ],
        )

        skill_dir = convert_workflow_to_skill(workflow, tmp_path)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert len(data["checks"]) == 2
        assert data["checks"][0]["type"] == "exit_code"
        assert data["checks"][0]["equals"] == 0

    def test_convert_handles_action_steps(self, tmp_path):
        """Test that action steps become placeholders."""
        workflow = ImportedWorkflow(
            name="Test",
            jobs=[
                ImportedJob(
                    id="build",
                    name="Build",
                    steps=[
                        ImportedStep(
                            id="step1",
                            name="Checkout",
                            type="action",
                            action="actions/checkout@v4",
                            supported=False,
                        ),
                        ImportedStep(id="step2", name="Build", type="shell", command="npm build"),
                    ],
                ),
            ],
        )

        skill_dir = convert_workflow_to_skill(workflow, tmp_path)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        # Action step becomes a TODO placeholder
        assert "[MANUAL]" in data["steps"][0]["name"]
        assert "TODO" in data["steps"][0]["command"]

    def test_convert_specific_job(self, tmp_path):
        """Test converting a specific job from workflow."""
        workflow = ImportedWorkflow(
            name="CI",
            jobs=[
                ImportedJob(
                    id="lint",
                    name="Lint",
                    steps=[
                        ImportedStep(id="step1", name="Lint", type="shell", command="npm run lint"),
                    ],
                ),
                ImportedJob(
                    id="test",
                    name="Test",
                    steps=[
                        ImportedStep(id="step1", name="Test", type="shell", command="npm test"),
                    ],
                ),
            ],
        )

        skill_dir = convert_workflow_to_skill(workflow, tmp_path, job_id="test")

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert data["metadata"]["source_job"] == "test"
        assert "npm test" in data["steps"][0]["command"]

    def test_convert_preserves_env_vars(self, tmp_path):
        """Test that env vars are preserved in conversion."""
        workflow = ImportedWorkflow(
            name="Test",
            env={"GLOBAL": "value"},
            jobs=[
                ImportedJob(
                    id="build",
                    name="Build",
                    env={"JOB_VAR": "job_value"},
                    steps=[
                        ImportedStep(
                            id="step1",
                            name="Build",
                            type="shell",
                            command="echo $STEP_VAR",
                            env={"STEP_VAR": "step_value"},
                        ),
                    ],
                ),
            ],
        )

        skill_dir = convert_workflow_to_skill(workflow, tmp_path)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        step_env = data["steps"][0]["env"]
        assert step_env["GLOBAL"] == "value"
        assert step_env["JOB_VAR"] == "job_value"
        assert step_env["STEP_VAR"] == "step_value"


class TestConvertGithubVars:
    """Tests for GitHub variable conversion."""

    def test_convert_github_workspace(self):
        """Test converting github.workspace."""
        text = "${{ github.workspace }}/src"
        result = _convert_github_vars(text)
        assert result == "{sandbox_dir}/src"

    def test_convert_github_workspace_no_spaces(self):
        """Test converting github.workspace without spaces."""
        text = "${{github.workspace}}/src"
        result = _convert_github_vars(text)
        assert result == "{sandbox_dir}/src"

    def test_convert_env_var(self):
        """Test converting GITHUB_WORKSPACE env var."""
        text = "$GITHUB_WORKSPACE/build"
        result = _convert_github_vars(text)
        assert result == "{sandbox_dir}/build"

    def test_convert_secrets_to_todo(self):
        """Test that secrets become TODO placeholders."""
        text = "${{ secrets.API_KEY }}"
        result = _convert_github_vars(text)
        assert result == "{TODO_SECRET}"

    def test_convert_github_event_to_todo(self):
        """Test that github.event becomes TODO placeholder."""
        text = "${{ github.event.inputs.version }}"
        result = _convert_github_vars(text)
        assert result == "{TODO_GITHUB_EVENT}"


class TestNormalizeName:
    """Tests for name normalization."""

    def test_normalize_simple_name(self):
        """Test normalizing a simple name."""
        assert _normalize_name("my_skill") == "my_skill"

    def test_normalize_with_spaces(self):
        """Test normalizing name with spaces."""
        assert _normalize_name("My Skill Name") == "my_skill_name"

    def test_normalize_with_special_chars(self):
        """Test normalizing name with special characters."""
        assert _normalize_name("My-Skill (CI/CD)") == "my_skill_ci_cd"

    def test_normalize_collapses_underscores(self):
        """Test that multiple underscores are collapsed."""
        assert _normalize_name("My   Skill") == "my_skill"

    def test_normalize_empty_becomes_default(self):
        """Test that empty name becomes default."""
        assert _normalize_name("!!!") == "imported_skill"


class TestImportGithubWorkflow:
    """Tests for the complete import function."""

    def test_import_successful(self, tmp_path):
        """Test successful import."""
        content = """
name: Build Project
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: npm run build
      - name: Test
        run: npm test
"""
        workflow_file = create_workflow_file(tmp_path, content)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = import_github_workflow(workflow_file, output_dir)

        assert result.success is True
        assert result.steps_imported == 2
        assert result.steps_skipped == 0
        assert result.skill_dir != ""

    def test_import_with_action_steps(self, tmp_path):
        """Test import with action steps (skipped)."""
        content = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        workflow_file = create_workflow_file(tmp_path, content)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = import_github_workflow(workflow_file, output_dir)

        assert result.success is True
        assert result.steps_imported == 1
        assert result.steps_skipped == 1

    def test_import_nonexistent_file(self, tmp_path):
        """Test import with non-existent file."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = import_github_workflow(tmp_path / "nonexistent.yml", output_dir)

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_import_specific_job(self, tmp_path):
        """Test importing a specific job."""
        content = """
name: CI
on: push
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: npm run lint
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
"""
        workflow_file = create_workflow_file(tmp_path, content)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = import_github_workflow(workflow_file, output_dir, job_id="test")

        assert result.success is True

        # Verify the correct job was imported
        with open(f"{result.skill_dir}/skill.yaml") as f:
            data = yaml.safe_load(f)

        assert data["metadata"]["source_job"] == "test"


class TestIntegration:
    """Integration tests for the import command."""

    def test_full_workflow_import(self, tmp_path):
        """Test complete workflow import."""
        content = """
name: Node.js CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  CI: true

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 18

      - name: Install dependencies
        run: npm ci
        working-directory: ${{ github.workspace }}

      - name: Run tests
        run: npm test
        env:
          NODE_ENV: test

      - name: Build
        run: npm run build
"""
        workflow_file = create_workflow_file(tmp_path, content)
        output_dir = tmp_path / "skills"
        output_dir.mkdir()

        result = import_github_workflow(workflow_file, output_dir)

        assert result.success is True
        assert result.steps_imported == 3  # npm ci, npm test, npm run build
        assert result.steps_skipped == 2  # checkout, setup-node

        # Verify skill structure
        skill_dir = output_dir / "node_js_ci"
        assert skill_dir.exists()
        assert (skill_dir / "skill.yaml").exists()
        assert (skill_dir / "SKILL.txt").exists()
        assert (skill_dir / "fixtures" / "happy_path" / "input").exists()

        # Verify skill.yaml content
        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "node_js_ci"
        assert len(data["steps"]) == 5  # 2 placeholder + 3 shell
        assert any("npm ci" in str(s.get("command", "")) for s in data["steps"])

        # Verify github.workspace was converted
        npm_ci_step = next(s for s in data["steps"] if "npm ci" in str(s.get("command", "")))
        assert npm_ci_step["cwd"] == "{sandbox_dir}"
