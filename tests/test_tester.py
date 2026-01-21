"""Tests for the skill testing framework."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from skillforge.skill import Skill
from skillforge.tester import (
    Assertion,
    AssertionResult,
    AssertionType,
    MockConfig,
    TestCase,
    TestDefinitionError,
    TestResult,
    TestStatus,
    TestSuiteDefinition,
    TestSuiteResult,
    TriggerExpectation,
    discover_tests,
    estimate_live_cost,
    evaluate_assertion,
    load_test_suite,
    run_test_mock,
    run_test_suite,
)


class TestAssertion:
    """Tests for the Assertion dataclass."""

    def test_from_dict_contains(self):
        """Test creating a contains assertion from dict."""
        data = {"type": "contains", "value": "hello", "case_sensitive": False}
        assertion = Assertion.from_dict(data)

        assert assertion.type == AssertionType.CONTAINS
        assert assertion.value == "hello"
        assert assertion.case_sensitive is False

    def test_from_dict_regex(self):
        """Test creating a regex assertion from dict."""
        data = {"type": "regex", "pattern": r"\d+"}
        assertion = Assertion.from_dict(data)

        assert assertion.type == AssertionType.REGEX
        assert assertion.pattern == r"\d+"

    def test_from_dict_length(self):
        """Test creating a length assertion from dict."""
        data = {"type": "length", "min": 10, "max": 100}
        assertion = Assertion.from_dict(data)

        assert assertion.type == AssertionType.LENGTH
        assert assertion.min == 10
        assert assertion.max == 100


class TestEvaluateAssertion:
    """Tests for assertion evaluation."""

    def test_contains_passes(self):
        """Test contains assertion passes when text is present."""
        assertion = Assertion(type=AssertionType.CONTAINS, value="hello")
        result = evaluate_assertion(assertion, "hello world")

        assert result.passed is True

    def test_contains_fails(self):
        """Test contains assertion fails when text is absent."""
        assertion = Assertion(type=AssertionType.CONTAINS, value="goodbye")
        result = evaluate_assertion(assertion, "hello world")

        assert result.passed is False

    def test_contains_case_insensitive(self):
        """Test contains assertion with case insensitivity."""
        assertion = Assertion(
            type=AssertionType.CONTAINS, value="HELLO", case_sensitive=False
        )
        result = evaluate_assertion(assertion, "hello world")

        assert result.passed is True

    def test_not_contains_passes(self):
        """Test not_contains assertion passes when text is absent."""
        assertion = Assertion(type=AssertionType.NOT_CONTAINS, value="goodbye")
        result = evaluate_assertion(assertion, "hello world")

        assert result.passed is True

    def test_not_contains_fails(self):
        """Test not_contains assertion fails when text is present."""
        assertion = Assertion(type=AssertionType.NOT_CONTAINS, value="hello")
        result = evaluate_assertion(assertion, "hello world")

        assert result.passed is False

    def test_regex_passes(self):
        """Test regex assertion passes when pattern matches."""
        assertion = Assertion(type=AssertionType.REGEX, pattern=r"\d{3}")
        result = evaluate_assertion(assertion, "Code: 123")

        assert result.passed is True
        assert result.actual_value == "123"

    def test_regex_fails(self):
        """Test regex assertion fails when pattern doesn't match."""
        assertion = Assertion(type=AssertionType.REGEX, pattern=r"\d{3}")
        result = evaluate_assertion(assertion, "No numbers here")

        assert result.passed is False

    def test_starts_with_passes(self):
        """Test starts_with assertion passes."""
        assertion = Assertion(type=AssertionType.STARTS_WITH, value="Hello")
        result = evaluate_assertion(assertion, "Hello, world!")

        assert result.passed is True

    def test_starts_with_fails(self):
        """Test starts_with assertion fails."""
        assertion = Assertion(type=AssertionType.STARTS_WITH, value="Goodbye")
        result = evaluate_assertion(assertion, "Hello, world!")

        assert result.passed is False

    def test_ends_with_passes(self):
        """Test ends_with assertion passes."""
        assertion = Assertion(type=AssertionType.ENDS_WITH, value="world!")
        result = evaluate_assertion(assertion, "Hello, world!")

        assert result.passed is True

    def test_ends_with_fails(self):
        """Test ends_with assertion fails."""
        assertion = Assertion(type=AssertionType.ENDS_WITH, value="universe!")
        result = evaluate_assertion(assertion, "Hello, world!")

        assert result.passed is False

    def test_length_passes_within_bounds(self):
        """Test length assertion passes when within bounds."""
        assertion = Assertion(type=AssertionType.LENGTH, min=5, max=20)
        result = evaluate_assertion(assertion, "Hello world")

        assert result.passed is True

    def test_length_fails_too_short(self):
        """Test length assertion fails when too short."""
        assertion = Assertion(type=AssertionType.LENGTH, min=20)
        result = evaluate_assertion(assertion, "Short")

        assert result.passed is False

    def test_length_fails_too_long(self):
        """Test length assertion fails when too long."""
        assertion = Assertion(type=AssertionType.LENGTH, max=5)
        result = evaluate_assertion(assertion, "This is too long")

        assert result.passed is False

    def test_json_valid_passes(self):
        """Test json_valid assertion passes for valid JSON."""
        assertion = Assertion(type=AssertionType.JSON_VALID)
        result = evaluate_assertion(assertion, '{"key": "value"}')

        assert result.passed is True

    def test_json_valid_fails(self):
        """Test json_valid assertion fails for invalid JSON."""
        assertion = Assertion(type=AssertionType.JSON_VALID)
        result = evaluate_assertion(assertion, "not json")

        assert result.passed is False

    def test_json_path_passes(self):
        """Test json_path assertion passes when value matches."""
        assertion = Assertion(
            type=AssertionType.JSON_PATH, path="$.status", value="ok"
        )
        result = evaluate_assertion(assertion, '{"status": "ok"}')

        assert result.passed is True
        assert result.actual_value == "ok"

    def test_json_path_fails(self):
        """Test json_path assertion fails when value doesn't match."""
        assertion = Assertion(
            type=AssertionType.JSON_PATH, path="$.status", value="ok"
        )
        result = evaluate_assertion(assertion, '{"status": "error"}')

        assert result.passed is False

    def test_equals_passes(self):
        """Test equals assertion passes for exact match."""
        assertion = Assertion(type=AssertionType.EQUALS, value="exact match")
        result = evaluate_assertion(assertion, "exact match")

        assert result.passed is True

    def test_equals_fails(self):
        """Test equals assertion fails for non-match."""
        assertion = Assertion(type=AssertionType.EQUALS, value="exact match")
        result = evaluate_assertion(assertion, "not exact")

        assert result.passed is False


class TestTestCase:
    """Tests for TestCase dataclass."""

    def test_from_dict_basic(self):
        """Test creating a basic test case from dict."""
        data = {
            "name": "basic_test",
            "input": "Test input",
            "description": "A basic test",
        }
        test_case = TestCase.from_dict(data)

        assert test_case.name == "basic_test"
        assert test_case.input == "Test input"
        assert test_case.description == "A basic test"

    def test_from_dict_with_assertions(self):
        """Test creating a test case with assertions."""
        data = {
            "name": "test_with_assertions",
            "input": "Test input",
            "assertions": [
                {"type": "contains", "value": "expected"},
                {"type": "length", "min": 10},
            ],
        }
        test_case = TestCase.from_dict(data)

        assert len(test_case.assertions) == 2
        assert test_case.assertions[0].type == AssertionType.CONTAINS
        assert test_case.assertions[1].type == AssertionType.LENGTH

    def test_from_dict_with_mock(self):
        """Test creating a test case with mock config."""
        data = {
            "name": "test_with_mock",
            "input": "Test input",
            "mock": {"response": "Mocked response", "delay": 0.5},
        }
        test_case = TestCase.from_dict(data)

        assert test_case.mock.response == "Mocked response"
        assert test_case.mock.delay == 0.5

    def test_from_dict_with_trigger(self):
        """Test creating a test case with trigger expectation."""
        data = {
            "name": "test_with_trigger",
            "input": "Test input",
            "trigger": {"should_trigger": False, "confidence": 0.9},
        }
        test_case = TestCase.from_dict(data)

        assert test_case.trigger.should_trigger is False
        assert test_case.trigger.confidence == 0.9

    def test_from_dict_with_skip(self):
        """Test creating a test case with skip reason."""
        data = {
            "name": "skipped_test",
            "input": "Test input",
            "skip": {"reason": "Not implemented yet"},
        }
        test_case = TestCase.from_dict(data)

        assert test_case.skip_reason == "Not implemented yet"


class TestTestSuiteDefinition:
    """Tests for TestSuiteDefinition."""

    def test_from_yaml(self, tmp_path):
        """Test loading a test suite from YAML."""
        yaml_content = """
version: "1.0"
defaults:
  timeout: 60
tests:
  - name: "test_one"
    input: "First test"
    assertions:
      - type: contains
        value: "response"
  - name: "test_two"
    input: "Second test"
"""
        yaml_file = tmp_path / "tests.yml"
        yaml_file.write_text(yaml_content)

        suite = TestSuiteDefinition.from_yaml(yaml_file)

        assert suite.version == "1.0"
        assert suite.defaults["timeout"] == 60
        assert len(suite.tests) == 2
        assert suite.tests[0].name == "test_one"
        assert suite.tests[1].name == "test_two"

    def test_from_yaml_invalid(self, tmp_path):
        """Test loading invalid YAML raises error."""
        yaml_file = tmp_path / "tests.yml"
        yaml_file.write_text("not a dict")

        with pytest.raises(TestDefinitionError):
            TestSuiteDefinition.from_yaml(yaml_file)


class TestDiscoverTests:
    """Tests for test discovery."""

    def test_discover_root_tests_yml(self, tmp_path):
        """Test discovering tests.yml in skill root."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "tests.yml").write_text("version: '1.0'\ntests: []")

        test_files = discover_tests(skill_dir)

        assert len(test_files) == 1
        assert test_files[0].name == "tests.yml"

    def test_discover_tests_directory(self, tmp_path):
        """Test discovering tests in tests/ directory."""
        skill_dir = tmp_path / "my-skill"
        tests_dir = skill_dir / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "basic.test.yml").write_text("version: '1.0'\ntests: []")
        (tests_dir / "advanced.test.yml").write_text("version: '1.0'\ntests: []")

        test_files = discover_tests(skill_dir)

        assert len(test_files) == 2
        names = [f.name for f in test_files]
        assert "basic.test.yml" in names
        assert "advanced.test.yml" in names

    def test_discover_no_tests(self, tmp_path):
        """Test that empty list is returned when no tests exist."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        test_files = discover_tests(skill_dir)

        assert test_files == []


class TestRunTestMock:
    """Tests for mock mode execution."""

    def test_mock_passes_with_matching_response(self):
        """Test mock mode passes when assertions match."""
        skill = Skill(
            name="commit-helper",
            description="A skill that helps write commit messages",
            content="Write commit messages",
        )
        test_case = TestCase(
            name="basic_test",
            input="Help me write a commit message",
            assertions=[
                Assertion(type=AssertionType.CONTAINS, value="commit"),
            ],
            mock=MockConfig(response="Here is a commit message for you"),
            # Trigger expectation matches the mock trigger detection
            trigger=TriggerExpectation(should_trigger=True),
        )

        result = run_test_mock(skill, test_case)

        assert result.status == TestStatus.PASSED
        assert result.passed is True

    def test_mock_fails_with_non_matching_response(self):
        """Test mock mode fails when assertions don't match."""
        skill = Skill(
            name="test-skill",
            description="A test skill",
            content="Content",
        )
        test_case = TestCase(
            name="failing_test",
            input="Test input",
            assertions=[
                Assertion(type=AssertionType.CONTAINS, value="not present"),
            ],
            mock=MockConfig(response="This response doesn't have the expected text"),
            # Set trigger expectation to False since input doesn't match skill keywords
            trigger=TriggerExpectation(should_trigger=False),
        )

        result = run_test_mock(skill, test_case)

        assert result.status == TestStatus.FAILED
        assert result.passed is False
        assert len(result.failed_assertions) == 1

    def test_mock_skips_when_skip_reason_set(self):
        """Test mock mode skips when skip_reason is set."""
        skill = Skill(name="test-skill", description="Test", content="Content")
        test_case = TestCase(
            name="skipped_test",
            input="Test input",
            skip_reason="Not implemented",
        )

        result = run_test_mock(skill, test_case)

        assert result.status == TestStatus.SKIPPED
        assert result.error == "Not implemented"


class TestRunTestSuite:
    """Tests for running a complete test suite."""

    def test_run_suite_all_pass(self):
        """Test running a suite where all tests pass."""
        skill = Skill(
            name="test-skill",
            description="A test skill",
            content="Content",
        )
        suite = TestSuiteDefinition(
            version="1.0",
            skill_path=None,
            defaults={},
            tests=[
                TestCase(
                    name="test_one",
                    input="Input one",
                    mock=MockConfig(response="Response one"),
                    assertions=[
                        Assertion(type=AssertionType.CONTAINS, value="one"),
                    ],
                    trigger=TriggerExpectation(should_trigger=False),
                ),
                TestCase(
                    name="test_two",
                    input="Input two",
                    mock=MockConfig(response="Response two"),
                    assertions=[
                        Assertion(type=AssertionType.CONTAINS, value="two"),
                    ],
                    trigger=TriggerExpectation(should_trigger=False),
                ),
            ],
        )

        result = run_test_suite(skill, suite, mode="mock")

        assert result.success is True
        assert result.total_tests == 2
        assert result.passed_tests == 2
        assert result.failed_tests == 0

    def test_run_suite_with_failure(self):
        """Test running a suite with a failing test."""
        skill = Skill(name="test-skill", description="Test", content="Content")
        suite = TestSuiteDefinition(
            version="1.0",
            skill_path=None,
            defaults={},
            tests=[
                TestCase(
                    name="passing_test",
                    input="Input",
                    mock=MockConfig(response="expected"),
                    assertions=[
                        Assertion(type=AssertionType.CONTAINS, value="expected"),
                    ],
                    trigger=TriggerExpectation(should_trigger=False),
                ),
                TestCase(
                    name="failing_test",
                    input="Input",
                    mock=MockConfig(response="wrong"),
                    assertions=[
                        Assertion(type=AssertionType.CONTAINS, value="expected"),
                    ],
                    trigger=TriggerExpectation(should_trigger=False),
                ),
            ],
        )

        result = run_test_suite(skill, suite, mode="mock")

        assert result.success is False
        assert result.passed_tests == 1
        assert result.failed_tests == 1

    def test_run_suite_with_tag_filter(self):
        """Test running a suite with tag filter."""
        skill = Skill(name="test-skill", description="Test", content="Content")
        suite = TestSuiteDefinition(
            version="1.0",
            skill_path=None,
            defaults={},
            tests=[
                TestCase(
                    name="smoke_test",
                    input="Input",
                    mock=MockConfig(response="response"),
                    tags=["smoke"],
                ),
                TestCase(
                    name="full_test",
                    input="Input",
                    mock=MockConfig(response="response"),
                    tags=["full"],
                ),
            ],
        )

        result = run_test_suite(skill, suite, mode="mock", filter_tags=["smoke"])

        assert result.total_tests == 1
        assert result.test_results[0].test_case.name == "smoke_test"

    def test_run_suite_stop_on_failure(self):
        """Test that stop_on_failure stops after first failure."""
        skill = Skill(name="test-skill", description="Test", content="Content")
        suite = TestSuiteDefinition(
            version="1.0",
            skill_path=None,
            defaults={},
            tests=[
                TestCase(
                    name="failing_test",
                    input="Input",
                    mock=MockConfig(response="wrong"),
                    assertions=[
                        Assertion(type=AssertionType.CONTAINS, value="expected"),
                    ],
                ),
                TestCase(
                    name="would_pass_test",
                    input="Input",
                    mock=MockConfig(response="expected"),
                    assertions=[
                        Assertion(type=AssertionType.CONTAINS, value="expected"),
                    ],
                ),
            ],
        )

        result = run_test_suite(skill, suite, mode="mock", stop_on_failure=True)

        # Only the first test should have run
        assert result.total_tests == 1
        assert result.failed_tests == 1


class TestEstimateLiveCost:
    """Tests for cost estimation."""

    def test_estimate_returns_dict(self):
        """Test that estimate returns a dictionary with expected keys."""
        suite = TestSuiteDefinition(
            version="1.0",
            skill_path=None,
            defaults={},
            tests=[
                TestCase(name="test_one", input="Input"),
                TestCase(name="test_two", input="Input"),
            ],
        )

        estimate = estimate_live_cost(suite, "claude-sonnet-4-20250514")

        assert "num_tests" in estimate
        assert "estimated_input_tokens" in estimate
        assert "estimated_output_tokens" in estimate
        assert "estimated_total_cost" in estimate
        assert estimate["num_tests"] == 2

    def test_estimate_excludes_skipped(self):
        """Test that cost estimate excludes skipped tests."""
        suite = TestSuiteDefinition(
            version="1.0",
            skill_path=None,
            defaults={},
            tests=[
                TestCase(name="test_one", input="Input"),
                TestCase(name="skipped", input="Input", skip_reason="Skip me"),
            ],
        )

        estimate = estimate_live_cost(suite, "claude-sonnet-4-20250514")

        assert estimate["num_tests"] == 1


class TestLoadTestSuite:
    """Tests for loading test suites."""

    def test_load_test_suite(self, tmp_path):
        """Test loading a complete test suite."""
        # Create skill directory with SKILL.md
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill for testing purposes. Use when testing.
---

# My Skill

Instructions here.
"""
        )

        # Create tests.yml
        (skill_dir / "tests.yml").write_text(
            """
version: "1.0"
tests:
  - name: "basic_test"
    input: "Test input"
    assertions:
      - type: contains
        value: "response"
    mock:
      response: "A mock response"
"""
        )

        skill, suite = load_test_suite(skill_dir)

        assert skill.name == "my-skill"
        assert len(suite.tests) == 1
        assert suite.tests[0].name == "basic_test"

    def test_load_test_suite_no_tests(self, tmp_path):
        """Test that loading a skill with no tests raises error."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill. Use when testing.
---

# My Skill
"""
        )

        with pytest.raises(TestDefinitionError):
            load_test_suite(skill_dir)


class TestTestSuiteResult:
    """Tests for TestSuiteResult properties."""

    def test_success_when_all_pass(self):
        """Test success is True when all tests pass."""
        skill = Skill(name="test", description="Test", content="")
        result = TestSuiteResult(
            skill=skill,
            test_results=[
                TestResult(
                    test_case=TestCase(name="test", input="input"),
                    status=TestStatus.PASSED,
                    duration_ms=10,
                ),
            ],
        )

        assert result.success is True

    def test_success_false_when_failure(self):
        """Test success is False when there's a failure."""
        skill = Skill(name="test", description="Test", content="")
        result = TestSuiteResult(
            skill=skill,
            test_results=[
                TestResult(
                    test_case=TestCase(name="test", input="input"),
                    status=TestStatus.FAILED,
                    duration_ms=10,
                ),
            ],
        )

        assert result.success is False

    def test_total_cost(self):
        """Test total_cost sums individual costs."""
        skill = Skill(name="test", description="Test", content="")
        result = TestSuiteResult(
            skill=skill,
            test_results=[
                TestResult(
                    test_case=TestCase(name="test1", input="input"),
                    status=TestStatus.PASSED,
                    duration_ms=10,
                    cost_estimate=0.001,
                ),
                TestResult(
                    test_case=TestCase(name="test2", input="input"),
                    status=TestStatus.PASSED,
                    duration_ms=10,
                    cost_estimate=0.002,
                ),
            ],
        )

        assert result.total_cost == pytest.approx(0.003)


class TestCLITestCommand:
    """Tests for the CLI test command."""

    def test_test_command_no_tests(self, tmp_path):
        """Test that test command handles no tests gracefully."""
        from typer.testing import CliRunner
        from skillforge.cli import app

        runner = CliRunner()

        # Create skill with no tests
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill. Use when testing.
---

# My Skill
"""
        )

        result = runner.invoke(app, ["test", str(skill_dir)])

        assert result.exit_code == 0
        assert "No tests found" in result.output

    def test_test_command_with_tests(self, tmp_path):
        """Test that test command runs tests."""
        from typer.testing import CliRunner
        from skillforge.cli import app

        runner = CliRunner()

        # Create skill with tests
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill for testing. Use when testing.
---

# My Skill

Instructions here.
"""
        )
        (skill_dir / "tests.yml").write_text(
            """
version: "1.0"
tests:
  - name: "basic_test"
    input: "Test input"
    assertions:
      - type: contains
        value: "response"
    mock:
      response: "A mock response"
"""
        )

        result = runner.invoke(app, ["test", str(skill_dir)])

        assert "Test Results" in result.output
        assert "basic_test" in result.output

    def test_test_command_json_output(self, tmp_path):
        """Test that test command can output JSON."""
        from typer.testing import CliRunner
        from skillforge.cli import app

        runner = CliRunner()

        # Create skill with tests
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill. Use when testing.
---

# My Skill
"""
        )
        (skill_dir / "tests.yml").write_text(
            """
version: "1.0"
tests:
  - name: "test"
    input: "input"
    trigger:
      should_trigger: false
    mock:
      response: "response"
"""
        )

        # Write to file to avoid header output
        json_output = tmp_path / "results.json"
        result = runner.invoke(
            app, ["test", str(skill_dir), "--format", "json", "-o", str(json_output)]
        )

        assert result.exit_code == 0
        # Should be valid JSON in the file
        data = json.loads(json_output.read_text())
        assert "skill" in data
        assert "tests" in data
