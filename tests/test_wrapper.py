"""Tests for the wrap command."""

import pytest
import yaml

from skillforge.wrapper import (
    ScriptInfo,
    WrapResult,
    WrapError,
    detect_script_type,
    analyze_script,
    wrap_script,
    wrap_script_command,
    _normalize_name,
    _extract_description,
    _extract_env_vars,
    _extract_arguments,
    _has_help_option,
    SCRIPT_TYPES,
)


def create_script(tmp_path, content: str, name: str = "script.sh", executable: bool = False):
    """Helper to create a script file."""
    script_file = tmp_path / name
    script_file.write_text(content)
    if executable:
        script_file.chmod(script_file.stat().st_mode | 0o755)
    return script_file


class TestDetectScriptType:
    """Tests for script type detection."""

    def test_detect_bash_by_extension(self, tmp_path):
        """Test detecting bash script by .sh extension."""
        script = create_script(tmp_path, "echo hello", "test.sh")
        assert detect_script_type(script) == "bash"

    def test_detect_bash_by_bash_extension(self, tmp_path):
        """Test detecting bash script by .bash extension."""
        script = create_script(tmp_path, "echo hello", "test.bash")
        assert detect_script_type(script) == "bash"

    def test_detect_python_by_extension(self, tmp_path):
        """Test detecting python script by .py extension."""
        script = create_script(tmp_path, "print('hello')", "test.py")
        assert detect_script_type(script) == "python"

    def test_detect_node_by_extension(self, tmp_path):
        """Test detecting node script by .js extension."""
        script = create_script(tmp_path, "console.log('hello')", "test.js")
        assert detect_script_type(script) == "node"

    def test_detect_ruby_by_extension(self, tmp_path):
        """Test detecting ruby script by .rb extension."""
        script = create_script(tmp_path, "puts 'hello'", "test.rb")
        assert detect_script_type(script) == "ruby"

    def test_detect_bash_by_shebang(self, tmp_path):
        """Test detecting bash script by shebang."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "script")
        assert detect_script_type(script) == "bash"

    def test_detect_python_by_shebang(self, tmp_path):
        """Test detecting python script by shebang."""
        script = create_script(tmp_path, "#!/usr/bin/env python3\nprint('hello')", "script")
        assert detect_script_type(script) == "python"

    def test_detect_shell_by_sh_shebang(self, tmp_path):
        """Test detecting shell script by /bin/sh shebang."""
        script = create_script(tmp_path, "#!/bin/sh\necho hello", "script")
        assert detect_script_type(script) == "shell"

    def test_default_to_shell(self, tmp_path):
        """Test defaulting to shell for unknown scripts."""
        script = create_script(tmp_path, "some content", "script")
        assert detect_script_type(script) == "shell"


class TestAnalyzeScript:
    """Tests for script analysis."""

    def test_analyze_basic_script(self, tmp_path):
        """Test analyzing a basic script."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "deploy.sh")

        info = analyze_script(script)

        assert info.name == "deploy"
        assert info.type == "bash"
        assert info.shebang == "#!/bin/bash"

    def test_analyze_executable_script(self, tmp_path):
        """Test analyzing an executable script."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "script.sh", executable=True)

        info = analyze_script(script)

        assert info.executable is True

    def test_analyze_script_with_description(self, tmp_path):
        """Test extracting description from script comments."""
        content = """#!/bin/bash
# This is a deployment script
# It deploys the application to production
echo "Deploying..."
"""
        script = create_script(tmp_path, content, "deploy.sh")

        info = analyze_script(script)

        assert "deployment script" in info.description

    def test_analyze_python_docstring(self, tmp_path):
        """Test extracting description from Python docstring."""
        content = '''#!/usr/bin/env python3
"""Build script for the project.

This script handles the build process.
"""
import sys
print("Building...")
'''
        script = create_script(tmp_path, content, "build.py")

        info = analyze_script(script)

        assert "Build script" in info.description

    def test_analyze_env_vars(self, tmp_path):
        """Test extracting environment variable references."""
        content = """#!/bin/bash
echo $API_KEY
curl -H "Authorization: $AUTH_TOKEN" $API_URL
"""
        script = create_script(tmp_path, content, "script.sh")

        info = analyze_script(script)

        assert "API_KEY" in info.env_vars
        assert "AUTH_TOKEN" in info.env_vars
        assert "API_URL" in info.env_vars

    def test_analyze_with_type_override(self, tmp_path):
        """Test analyzing with type override."""
        script = create_script(tmp_path, "print('hello')", "script")

        info = analyze_script(script, script_type="python")

        assert info.type == "python"

    def test_analyze_nonexistent_script(self, tmp_path):
        """Test analyzing non-existent script raises error."""
        with pytest.raises(WrapError, match="not found"):
            analyze_script(tmp_path / "nonexistent.sh")


class TestExtractDescription:
    """Tests for description extraction."""

    def test_extract_from_shell_comments(self):
        """Test extracting from shell comments."""
        lines = [
            "#!/bin/bash",
            "# Deploy the application",
            "# to production servers",
            "echo deploying",
        ]

        desc = _extract_description(lines, "bash")

        assert "Deploy the application" in desc

    def test_extract_from_python_docstring(self):
        """Test extracting from Python docstring."""
        lines = [
            "#!/usr/bin/env python3",
            '"""Build the project."""',
            "import sys",
        ]

        desc = _extract_description(lines, "python")

        assert "Build the project" in desc

    def test_skip_shellcheck_comments(self):
        """Test that shellcheck directives are skipped."""
        lines = [
            "#!/bin/bash",
            "# shellcheck disable=SC2034",
            "# This is the actual description",
            "echo hello",
        ]

        desc = _extract_description(lines, "bash")

        assert "shellcheck" not in desc.lower()
        assert "actual description" in desc


class TestExtractEnvVars:
    """Tests for environment variable extraction."""

    def test_extract_dollar_vars(self):
        """Test extracting $VAR syntax."""
        content = "echo $MY_VAR and $ANOTHER_VAR"

        env_vars = _extract_env_vars(content)

        assert "MY_VAR" in env_vars
        assert "ANOTHER_VAR" in env_vars

    def test_extract_brace_vars(self):
        """Test extracting ${VAR} syntax."""
        content = "echo ${CONFIG_PATH} and ${DATA_DIR}"

        env_vars = _extract_env_vars(content)

        assert "CONFIG_PATH" in env_vars
        assert "DATA_DIR" in env_vars

    def test_filter_common_vars(self):
        """Test that common shell variables are filtered."""
        content = "echo $HOME $PATH $USER $MY_CUSTOM_VAR"

        env_vars = _extract_env_vars(content)

        assert "HOME" not in env_vars
        assert "PATH" not in env_vars
        assert "MY_CUSTOM_VAR" in env_vars


class TestExtractArguments:
    """Tests for argument extraction."""

    def test_extract_getopts_short(self):
        """Test extracting short options from getopts."""
        content = 'while getopts "hvf:" opt; do'

        args = _extract_arguments(content, "bash")

        assert "-h" in args
        assert "-v" in args
        assert "-f" in args

    def test_extract_case_long_options(self):
        """Test extracting long options from case statements."""
        content = """
case $1 in
    --help)
        show_help
        ;;
    --verbose)
        VERBOSE=1
        ;;
esac
"""
        args = _extract_arguments(content, "bash")

        assert "--help" in args
        assert "--verbose" in args

    def test_extract_argparse_arguments(self):
        """Test extracting argparse arguments from Python."""
        content = """
parser = argparse.ArgumentParser()
parser.add_argument('--config', help='Config file')
parser.add_argument('-v', '--verbose', action='store_true')
"""
        args = _extract_arguments(content, "python")

        assert "--config" in args
        assert "--verbose" in args


class TestHasHelpOption:
    """Tests for help option detection."""

    def test_detect_help_long(self):
        """Test detecting --help option."""
        content = 'if [ "$1" = "--help" ]; then'

        assert _has_help_option(content) is True

    def test_detect_usage(self):
        """Test detecting usage pattern."""
        content = "usage: script.sh [options]"

        assert _has_help_option(content) is True

    def test_detect_argparse(self):
        """Test detecting argparse."""
        content = "import argparse"

        assert _has_help_option(content) is True

    def test_no_help(self):
        """Test when no help option present."""
        content = "echo hello"

        assert _has_help_option(content) is False


class TestNormalizeName:
    """Tests for name normalization."""

    def test_normalize_simple_name(self):
        """Test normalizing a simple name."""
        assert _normalize_name("my_script") == "my_script"

    def test_normalize_with_extension(self):
        """Test normalizing name (extension not included in name)."""
        assert _normalize_name("deploy") == "deploy"

    def test_normalize_with_spaces(self):
        """Test normalizing name with spaces."""
        assert _normalize_name("my script") == "my_script"

    def test_normalize_with_special_chars(self):
        """Test normalizing name with special characters."""
        assert _normalize_name("build-script.v2") == "build_script_v2"

    def test_normalize_collapses_underscores(self):
        """Test that multiple underscores are collapsed."""
        assert _normalize_name("my--script") == "my_script"


class TestWrapScript:
    """Tests for script wrapping."""

    def test_wrap_creates_skill_directory(self, tmp_path):
        """Test that wrap creates skill directory."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "deploy.sh")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir)

        assert skill_dir.exists()
        assert skill_dir.name == "deploy"

    def test_wrap_creates_skill_yaml(self, tmp_path):
        """Test that wrap creates skill.yaml."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "deploy.sh")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir)

        skill_yaml = skill_dir / "skill.yaml"
        assert skill_yaml.exists()

        with open(skill_yaml) as f:
            data = yaml.safe_load(f)

        assert data["name"] == "deploy"
        assert "bash" in data["requirements"]["commands"]

    def test_wrap_copies_script(self, tmp_path):
        """Test that wrap copies script to skill."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "deploy.sh")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir)

        copied_script = skill_dir / "scripts" / "deploy.sh"
        assert copied_script.exists()
        assert "echo hello" in copied_script.read_text()

    def test_wrap_makes_script_executable(self, tmp_path):
        """Test that wrapped script is made executable."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "deploy.sh")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir)

        copied_script = skill_dir / "scripts" / "deploy.sh"
        assert copied_script.stat().st_mode & 0o111 != 0

    def test_wrap_creates_fixtures(self, tmp_path):
        """Test that wrap creates fixtures directory."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "script.sh")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir)

        assert (skill_dir / "fixtures" / "happy_path" / "input").exists()
        assert (skill_dir / "fixtures" / "happy_path" / "expected").exists()

    def test_wrap_with_custom_name(self, tmp_path):
        """Test wrapping with custom skill name."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "script.sh")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir, skill_name="my_deployment")

        assert skill_dir.name == "my_deployment"

    def test_wrap_python_script(self, tmp_path):
        """Test wrapping a Python script."""
        content = '''#!/usr/bin/env python3
"""Build script."""
import sys
print("Building...")
'''
        script = create_script(tmp_path, content, "build.py")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert "python" in data["requirements"]["commands"]
        assert "python" in data["steps"][0]["command"]

    def test_wrap_node_script(self, tmp_path):
        """Test wrapping a Node.js script."""
        script = create_script(tmp_path, "console.log('hello')", "build.js")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert "node" in data["requirements"]["commands"]
        assert "node" in data["steps"][0]["command"]

    def test_wrap_script_with_arguments(self, tmp_path):
        """Test wrapping script that takes arguments."""
        content = """#!/bin/bash
while getopts "hv" opt; do
    case $opt in
        h) show_help ;;
        v) VERBOSE=1 ;;
    esac
done
"""
        script = create_script(tmp_path, content, "script.sh")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        skill_dir = wrap_script(script, output_dir)

        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        # Should have script_args input
        input_names = [i["name"] for i in data["inputs"]]
        assert "script_args" in input_names


class TestWrapScriptCommand:
    """Tests for the wrap command entry point."""

    def test_wrap_command_successful(self, tmp_path):
        """Test successful wrap command."""
        script = create_script(tmp_path, "#!/bin/bash\necho hello", "deploy.sh")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = wrap_script_command(script, output_dir)

        assert result.success is True
        assert result.skill_dir != ""
        assert result.script_info is not None

    def test_wrap_command_nonexistent_script(self, tmp_path):
        """Test wrap command with non-existent script."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = wrap_script_command(tmp_path / "nonexistent.sh", output_dir)

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_wrap_command_with_type_override(self, tmp_path):
        """Test wrap command with type override."""
        script = create_script(tmp_path, "print('hello')", "script")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = wrap_script_command(script, output_dir, script_type="python")

        assert result.success is True
        assert result.script_info.type == "python"


class TestIntegration:
    """Integration tests for wrap command."""

    def test_full_wrap_workflow(self, tmp_path):
        """Test complete wrap workflow."""
        content = """#!/bin/bash
# Deployment script for the application
# Deploys to production environment

set -e

echo "Starting deployment..."
echo "Using API key: $API_KEY"
echo "Target: $DEPLOY_TARGET"

if [ "$1" = "--help" ]; then
    echo "Usage: deploy.sh [--dry-run]"
    exit 0
fi

echo "Deployment complete!"
"""
        script = create_script(tmp_path, content, "deploy.sh", executable=True)
        output_dir = tmp_path / "skills"
        output_dir.mkdir()

        result = wrap_script_command(script, output_dir)

        assert result.success is True

        # Verify skill structure
        skill_dir = output_dir / "deploy"
        assert skill_dir.exists()
        assert (skill_dir / "skill.yaml").exists()
        assert (skill_dir / "SKILL.txt").exists()
        assert (skill_dir / "scripts" / "deploy.sh").exists()

        # Verify skill.yaml content
        with open(skill_dir / "skill.yaml") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "deploy"
        assert "Deployment script" in data["description"]
        assert "bash" in data["requirements"]["commands"]

        # Verify env vars were detected
        assert result.script_info.env_vars
        assert "API_KEY" in result.script_info.env_vars

        # Verify script was copied and is executable
        copied = skill_dir / "scripts" / "deploy.sh"
        assert copied.stat().st_mode & 0o111 != 0
