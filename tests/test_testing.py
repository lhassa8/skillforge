"""Tests for the testing framework."""

import json
import pytest
import yaml

from skillforge.testing import (
    FixtureConfig,
    ComparisonResult,
    FixtureResult,
    SkillTestReport,
    load_fixture_config,
    discover_fixtures,
    run_fixture_test,
    compare_directories,
    compare_golden,
    run_all_fixtures,
)


def create_test_skill(tmp_path, skill_data: dict, name: str = "test_skill"):
    """Helper to create a test skill directory."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "skill.yaml").write_text(yaml.dump(skill_data))
    (skill_dir / "fixtures").mkdir()
    (skill_dir / "reports").mkdir()
    return skill_dir


def create_fixture(skill_dir, fixture_name: str, input_files: dict = None, expected_files: dict = None):
    """Helper to create a fixture directory."""
    fixture_dir = skill_dir / "fixtures" / fixture_name
    fixture_dir.mkdir(parents=True)

    # Create input directory
    input_dir = fixture_dir / "input"
    input_dir.mkdir()

    if input_files:
        for filename, content in input_files.items():
            file_path = input_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    # Create expected directory if provided
    if expected_files:
        expected_dir = fixture_dir / "expected"
        expected_dir.mkdir()
        for filename, content in expected_files.items():
            file_path = expected_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    return fixture_dir


class TestFixtureConfig:
    """Tests for FixtureConfig loading."""

    def test_default_config(self, tmp_path):
        """Test loading default config when no fixture.yaml."""
        fixture_dir = tmp_path / "test_fixture"
        fixture_dir.mkdir()

        config = load_fixture_config(fixture_dir)

        assert config.name == "test_fixture"
        assert config.inputs == {}
        assert config.allow_extra_files is False

    def test_config_with_inputs(self, tmp_path):
        """Test loading config with inputs."""
        fixture_dir = tmp_path / "test_fixture"
        fixture_dir.mkdir()

        config_content = {
            "inputs": {"message": "hello", "count": 5},
            "allow_extra_files": True,
        }
        (fixture_dir / "fixture.yaml").write_text(yaml.dump(config_content))

        config = load_fixture_config(fixture_dir)

        assert config.inputs == {"message": "hello", "count": 5}
        assert config.allow_extra_files is True

    def test_config_with_invalid_yaml(self, tmp_path):
        """Test loading config with invalid YAML falls back to defaults."""
        fixture_dir = tmp_path / "test_fixture"
        fixture_dir.mkdir()
        (fixture_dir / "fixture.yaml").write_text("not: valid: yaml: {{")

        config = load_fixture_config(fixture_dir)

        assert config.name == "test_fixture"
        assert config.inputs == {}


class TestDiscoverFixtures:
    """Tests for fixture discovery."""

    def test_no_fixtures_dir(self, tmp_path):
        """Test when fixtures directory doesn't exist."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        fixtures = discover_fixtures(skill_dir)

        assert fixtures == []

    def test_empty_fixtures_dir(self, tmp_path):
        """Test when fixtures directory is empty."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "fixtures").mkdir()

        fixtures = discover_fixtures(skill_dir)

        assert fixtures == []

    def test_discover_single_fixture(self, tmp_path):
        """Test discovering a single fixture."""
        skill_dir = create_test_skill(tmp_path, {"name": "test", "steps": [], "checks": []})
        create_fixture(skill_dir, "happy_path", {"test.txt": "hello"})

        fixtures = discover_fixtures(skill_dir)

        assert len(fixtures) == 1
        assert fixtures[0].name == "happy_path"

    def test_discover_multiple_fixtures(self, tmp_path):
        """Test discovering multiple fixtures."""
        skill_dir = create_test_skill(tmp_path, {"name": "test", "steps": [], "checks": []})
        create_fixture(skill_dir, "happy_path", {"test.txt": "hello"})
        create_fixture(skill_dir, "error_case", {"test.txt": "error"})
        create_fixture(skill_dir, "edge_case", {"test.txt": "edge"})

        fixtures = discover_fixtures(skill_dir)

        assert len(fixtures) == 3
        fixture_names = {f.name for f in fixtures}
        assert fixture_names == {"happy_path", "error_case", "edge_case"}

    def test_skip_fixture_without_input(self, tmp_path):
        """Test that fixtures without input directory are skipped."""
        skill_dir = create_test_skill(tmp_path, {"name": "test", "steps": [], "checks": []})

        # Create fixture with input
        create_fixture(skill_dir, "valid_fixture", {"test.txt": "hello"})

        # Create fixture without input
        invalid_fixture = skill_dir / "fixtures" / "invalid_fixture"
        invalid_fixture.mkdir()
        (invalid_fixture / "expected").mkdir()

        fixtures = discover_fixtures(skill_dir)

        assert len(fixtures) == 1
        assert fixtures[0].name == "valid_fixture"

    def test_skip_hidden_directories(self, tmp_path):
        """Test that hidden directories are skipped."""
        skill_dir = create_test_skill(tmp_path, {"name": "test", "steps": [], "checks": []})
        create_fixture(skill_dir, "valid_fixture", {"test.txt": "hello"})

        # Create hidden directory
        hidden = skill_dir / "fixtures" / ".hidden"
        hidden.mkdir()
        (hidden / "input").mkdir()

        fixtures = discover_fixtures(skill_dir)

        assert len(fixtures) == 1
        assert fixtures[0].name == "valid_fixture"


class TestCompareDirectories:
    """Tests for directory comparison."""

    def test_identical_directories(self, tmp_path):
        """Test comparing identical directories."""
        actual = tmp_path / "actual"
        expected = tmp_path / "expected"
        actual.mkdir()
        expected.mkdir()

        (actual / "file1.txt").write_text("content1")
        (actual / "file2.txt").write_text("content2")
        (expected / "file1.txt").write_text("content1")
        (expected / "file2.txt").write_text("content2")

        result = compare_directories(actual, expected)

        assert result.matches is True
        assert result.missing_files == []
        assert result.extra_files == []
        assert result.different_files == []

    def test_missing_files(self, tmp_path):
        """Test detecting missing files."""
        actual = tmp_path / "actual"
        expected = tmp_path / "expected"
        actual.mkdir()
        expected.mkdir()

        (actual / "file1.txt").write_text("content1")
        (expected / "file1.txt").write_text("content1")
        (expected / "file2.txt").write_text("content2")

        result = compare_directories(actual, expected)

        assert result.matches is False
        assert "file2.txt" in result.missing_files

    def test_extra_files(self, tmp_path):
        """Test detecting extra files."""
        actual = tmp_path / "actual"
        expected = tmp_path / "expected"
        actual.mkdir()
        expected.mkdir()

        (actual / "file1.txt").write_text("content1")
        (actual / "extra.txt").write_text("extra")
        (expected / "file1.txt").write_text("content1")

        result = compare_directories(actual, expected, allow_extra=False)

        assert result.matches is False
        assert "extra.txt" in result.extra_files

    def test_allow_extra_files(self, tmp_path):
        """Test allowing extra files."""
        actual = tmp_path / "actual"
        expected = tmp_path / "expected"
        actual.mkdir()
        expected.mkdir()

        (actual / "file1.txt").write_text("content1")
        (actual / "extra.txt").write_text("extra")
        (expected / "file1.txt").write_text("content1")

        result = compare_directories(actual, expected, allow_extra=True)

        assert result.matches is True
        assert result.extra_files == []

    def test_different_content(self, tmp_path):
        """Test detecting different file content."""
        actual = tmp_path / "actual"
        expected = tmp_path / "expected"
        actual.mkdir()
        expected.mkdir()

        (actual / "file1.txt").write_text("actual content")
        (expected / "file1.txt").write_text("expected content")

        result = compare_directories(actual, expected)

        assert result.matches is False
        assert "file1.txt" in result.different_files

    def test_nested_directories(self, tmp_path):
        """Test comparing nested directory structures."""
        actual = tmp_path / "actual"
        expected = tmp_path / "expected"

        # Create nested structure
        (actual / "subdir").mkdir(parents=True)
        (expected / "subdir").mkdir(parents=True)

        (actual / "subdir" / "nested.txt").write_text("nested")
        (expected / "subdir" / "nested.txt").write_text("nested")

        result = compare_directories(actual, expected)

        assert result.matches is True

    def test_skip_hidden_files(self, tmp_path):
        """Test that hidden files are skipped."""
        actual = tmp_path / "actual"
        expected = tmp_path / "expected"
        actual.mkdir()
        expected.mkdir()

        (actual / "file1.txt").write_text("content")
        (actual / ".hidden").write_text("hidden")
        (expected / "file1.txt").write_text("content")

        result = compare_directories(actual, expected)

        assert result.matches is True


class TestCompareGolden:
    """Tests for golden artifact comparison."""

    def test_no_golden_artifacts(self, tmp_path):
        """Test when no golden artifacts exist."""
        actual = tmp_path / "actual"
        golden = tmp_path / "golden"
        actual.mkdir()
        golden.mkdir()

        result = compare_golden(actual, golden)

        assert result.matches is True
        assert "No golden artifacts" in result.message

    def test_golden_file_list_match(self, tmp_path):
        """Test golden file list comparison."""
        actual = tmp_path / "actual"
        golden = tmp_path / "golden"
        actual.mkdir()
        golden.mkdir()

        # Create actual files
        (actual / "file1.txt").write_text("content1")
        (actual / "file2.txt").write_text("content2")

        # Create golden artifacts
        expected_changed = ["file1.txt", "file2.txt"]
        (golden / "expected_changed_files.json").write_text(json.dumps(expected_changed))

        result = compare_golden(actual, golden)

        assert result.matches is True

    def test_golden_missing_file(self, tmp_path):
        """Test golden comparison with missing file."""
        actual = tmp_path / "actual"
        golden = tmp_path / "golden"
        actual.mkdir()
        golden.mkdir()

        # Create only one actual file
        (actual / "file1.txt").write_text("content1")

        # Expect two files
        expected_changed = ["file1.txt", "file2.txt"]
        (golden / "expected_changed_files.json").write_text(json.dumps(expected_changed))

        result = compare_golden(actual, golden)

        assert result.matches is False
        assert "file2.txt" in result.missing_files

    def test_golden_extra_file(self, tmp_path):
        """Test golden comparison with extra file."""
        actual = tmp_path / "actual"
        golden = tmp_path / "golden"
        actual.mkdir()
        golden.mkdir()

        # Create more files than expected
        (actual / "file1.txt").write_text("content1")
        (actual / "extra.txt").write_text("extra")

        # Expect only one file
        expected_changed = ["file1.txt"]
        (golden / "expected_changed_files.json").write_text(json.dumps(expected_changed))

        result = compare_golden(actual, golden)

        assert result.matches is False
        assert "extra.txt" in result.extra_files


class TestRunFixtureTest:
    """Tests for fixture test execution."""

    def test_successful_fixture(self, tmp_path):
        """Test successful fixture execution."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello > output.txt", "cwd": "{sandbox_dir}"},
            ],
            "checks": [],
        })
        fixture_dir = create_fixture(
            skill_dir,
            "happy_path",
            input_files={"README.md": "# Test"},
            expected_files={"README.md": "# Test", "output.txt": "hello\n"},
        )

        result = run_fixture_test(skill_dir, fixture_dir, "test123")

        assert result.passed is True
        assert result.fixture_name == "happy_path"
        assert result.run_report is not None

    def test_fixture_without_input_dir(self, tmp_path):
        """Test fixture without input directory fails."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "steps": [],
            "checks": [],
        })
        fixture_dir = skill_dir / "fixtures" / "broken"
        fixture_dir.mkdir(parents=True)

        result = run_fixture_test(skill_dir, fixture_dir, "test123")

        assert result.passed is False
        assert "input directory" in result.error_message.lower()

    def test_fixture_with_expected_mismatch(self, tmp_path):
        """Test fixture that produces different output than expected."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo wrong > output.txt", "cwd": "{sandbox_dir}"},
            ],
            "checks": [],
        })
        fixture_dir = create_fixture(
            skill_dir,
            "happy_path",
            input_files={"README.md": "# Test"},
            expected_files={"README.md": "# Test", "output.txt": "expected\n"},
        )

        result = run_fixture_test(skill_dir, fixture_dir, "test123")

        assert result.passed is False
        assert "output.txt" in result.comparison.different_files


class TestRunAllFixtures:
    """Tests for running all fixtures."""

    def test_all_fixtures_pass(self, tmp_path):
        """Test running all fixtures successfully."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "fixture1", {"test.txt": "test"})
        create_fixture(skill_dir, "fixture2", {"test.txt": "test"})

        report = run_all_fixtures(skill_dir)

        assert report.total_passed == 2
        assert report.total_failed == 0
        assert report.all_passed is True

    def test_no_fixtures(self, tmp_path):
        """Test running with no fixtures."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "steps": [],
            "checks": [],
        })

        report = run_all_fixtures(skill_dir)

        assert report.total_passed == 0
        assert report.total_skipped == 1

    def test_mixed_results(self, tmp_path):
        """Test with some fixtures passing and some failing."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello"},
            ],
            "checks": [],
        })

        # Passing fixture - no expected dir
        create_fixture(skill_dir, "passing", {"test.txt": "test"})

        # Failing fixture - expected dir with wrong content
        fixture_dir = create_fixture(
            skill_dir,
            "failing",
            input_files={"test.txt": "test"},
            expected_files={"missing.txt": "this file won't exist"},
        )

        report = run_all_fixtures(skill_dir)

        assert report.total_passed == 1
        assert report.total_failed == 1
        assert report.all_passed is False


class TestSkillTestReport:
    """Tests for SkillTestReport dataclass."""

    def test_all_passed_property(self):
        """Test all_passed property."""
        report = SkillTestReport(
            skill_name="test",
            skill_dir="/test",
            started_at="2024-01-01T00:00:00",
            total_passed=3,
            total_failed=0,
        )

        assert report.all_passed is True

    def test_all_passed_with_failures(self):
        """Test all_passed when there are failures."""
        report = SkillTestReport(
            skill_name="test",
            skill_dir="/test",
            started_at="2024-01-01T00:00:00",
            total_passed=2,
            total_failed=1,
        )

        assert report.all_passed is False

    def test_all_passed_no_tests(self):
        """Test all_passed when there are no tests."""
        report = SkillTestReport(
            skill_name="test",
            skill_dir="/test",
            started_at="2024-01-01T00:00:00",
            total_passed=0,
            total_failed=0,
        )

        assert report.all_passed is False
