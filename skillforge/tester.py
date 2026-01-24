"""Skill testing framework for SkillForge."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

import yaml

from skillforge.skill import Skill


class AssertionType(Enum):
    """Types of assertions supported in test definitions."""

    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    LENGTH = "length"
    JSON_VALID = "json_valid"
    JSON_PATH = "json_path"
    EQUALS = "equals"
    SIMILAR_TO = "similar_to"  # Fuzzy matching for regression testing


class TestStatus(Enum):
    """Status of a test execution."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class SkillTestError(Exception):
    """Base exception for skill testing errors."""

    pass


class TestDefinitionError(SkillTestError):
    """Raised when test definition is invalid."""

    pass


class TestExecutionError(SkillTestError):
    """Raised when test execution fails."""

    pass


# Cost estimation constants (approximate per 1K tokens)
COST_PER_1K_INPUT_TOKENS = {
    "claude-sonnet-4-20250514": 0.003,
    "claude-opus-4-1-20250219": 0.015,
    "gpt-4o": 0.005,
    "gpt-4-turbo": 0.01,
    "llama3.2": 0.0,
}

COST_PER_1K_OUTPUT_TOKENS = {
    "claude-sonnet-4-20250514": 0.015,
    "claude-opus-4-1-20250219": 0.075,
    "gpt-4o": 0.015,
    "gpt-4-turbo": 0.03,
    "llama3.2": 0.0,
}


@dataclass
class Assertion:
    """A single assertion to validate response."""

    type: AssertionType
    value: Optional[str] = None
    pattern: Optional[str] = None
    path: Optional[str] = None  # For JSON path
    min: Optional[int] = None  # For length
    max: Optional[int] = None  # For length
    case_sensitive: bool = True
    threshold: float = 0.8  # For similar_to: similarity threshold (0.0-1.0)
    baseline: Optional[str] = None  # For similar_to: baseline response

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Assertion:
        """Create an Assertion from a dictionary."""
        assertion_type = AssertionType(data["type"])
        return cls(
            type=assertion_type,
            value=data.get("value"),
            pattern=data.get("pattern"),
            path=data.get("path"),
            min=data.get("min"),
            max=data.get("max"),
            case_sensitive=data.get("case_sensitive", True),
            threshold=data.get("threshold", 0.8),
            baseline=data.get("baseline"),
        )


@dataclass
class TriggerExpectation:
    """Expected trigger behavior."""

    should_trigger: bool = True
    confidence: float = 0.5


@dataclass
class MockConfig:
    """Mock mode configuration for a test case."""

    response: str = ""
    delay: float = 0.0


@dataclass
class ContextMessage:
    """A message in conversation context."""

    role: Literal["user", "assistant"]
    content: str


@dataclass
class TestCase:
    """A single test case definition."""

    name: str
    input: str
    description: str = ""
    assertions: list[Assertion] = field(default_factory=list)
    trigger: TriggerExpectation = field(default_factory=TriggerExpectation)
    mock: MockConfig = field(default_factory=MockConfig)
    context: list[ContextMessage] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    skip_reason: Optional[str] = None
    timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: Optional[dict[str, Any]] = None) -> TestCase:
        """Create a TestCase from a dictionary."""
        defaults = defaults or {}

        assertions = [Assertion.from_dict(a) for a in data.get("assertions", [])]

        trigger_data = data.get("trigger", {})
        trigger = TriggerExpectation(
            should_trigger=trigger_data.get("should_trigger", True),
            confidence=trigger_data.get("confidence", 0.5),
        )

        mock_data = data.get("mock", {})
        mock = MockConfig(
            response=mock_data.get("response", ""),
            delay=mock_data.get("delay", 0.0),
        )

        context = [
            ContextMessage(role=c["role"], content=c["content"])
            for c in data.get("context", [])
        ]

        skip_data = data.get("skip", {})
        skip_reason = skip_data.get("reason") if skip_data else None

        return cls(
            name=data["name"],
            input=data["input"],
            description=data.get("description", ""),
            assertions=assertions,
            trigger=trigger,
            mock=mock,
            context=context,
            tags=data.get("tags", []),
            skip_reason=skip_reason,
            timeout=data.get("timeout", defaults.get("timeout", 30)),
        )


@dataclass
class AssertionResult:
    """Result of evaluating a single assertion."""

    assertion: Assertion
    passed: bool
    message: str
    actual_value: Optional[str] = None


@dataclass
class TestResult:
    """Result of running a single test case."""

    test_case: TestCase
    status: TestStatus
    duration_ms: float
    assertion_results: list[AssertionResult] = field(default_factory=list)
    response: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    tokens_used: int = 0
    cost_estimate: float = 0.0

    @property
    def passed(self) -> bool:
        """Check if test passed."""
        return self.status == TestStatus.PASSED

    @property
    def failed_assertions(self) -> list[AssertionResult]:
        """Get list of failed assertions."""
        return [r for r in self.assertion_results if not r.passed]


@dataclass
class TestSuiteResult:
    """Result of running a complete test suite."""

    skill: Skill
    test_results: list[TestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    mode: Literal["mock", "live"] = "mock"

    @property
    def total_tests(self) -> int:
        """Total number of tests."""
        return len(self.test_results)

    @property
    def passed_tests(self) -> int:
        """Number of passed tests."""
        return sum(1 for r in self.test_results if r.status == TestStatus.PASSED)

    @property
    def failed_tests(self) -> int:
        """Number of failed tests."""
        return sum(1 for r in self.test_results if r.status == TestStatus.FAILED)

    @property
    def skipped_tests(self) -> int:
        """Number of skipped tests."""
        return sum(1 for r in self.test_results if r.status == TestStatus.SKIPPED)

    @property
    def error_tests(self) -> int:
        """Number of tests with errors."""
        return sum(1 for r in self.test_results if r.status == TestStatus.ERROR)

    @property
    def duration_ms(self) -> float:
        """Total duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return sum(r.duration_ms for r in self.test_results)

    @property
    def total_cost(self) -> float:
        """Total estimated cost of all tests."""
        return sum(r.cost_estimate for r in self.test_results)

    @property
    def success(self) -> bool:
        """Check if all tests passed or were skipped."""
        return self.failed_tests == 0 and self.error_tests == 0


@dataclass
class TestSuiteDefinition:
    """Definition of a test suite loaded from YAML."""

    version: str
    skill_path: Optional[Path]
    defaults: dict[str, Any]
    tests: list[TestCase]

    @classmethod
    def from_yaml(
        cls, yaml_path: Path, skill_dir: Optional[Path] = None
    ) -> TestSuiteDefinition:
        """Load test suite definition from YAML file."""
        content = yaml_path.read_text()
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            raise TestDefinitionError(f"Invalid test file format: {yaml_path}")

        version = data.get("version", "1.0")
        defaults = data.get("defaults", {})

        # Resolve skill path
        skill_path = None
        if "skill" in data:
            skill_path = Path(data["skill"])
        elif skill_dir:
            skill_path = skill_dir

        tests = [TestCase.from_dict(t, defaults) for t in data.get("tests", [])]

        return cls(
            version=version,
            skill_path=skill_path,
            defaults=defaults,
            tests=tests,
        )


def discover_tests(skill_dir: Path) -> list[Path]:
    """Discover test files for a skill.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        List of paths to test files
    """
    test_files = []

    # Check for tests.yml in skill root
    root_tests = skill_dir / "tests.yml"
    if root_tests.exists():
        test_files.append(root_tests)

    # Also check tests.yaml
    root_tests_yaml = skill_dir / "tests.yaml"
    if root_tests_yaml.exists():
        test_files.append(root_tests_yaml)

    # Check for tests/ directory
    tests_dir = skill_dir / "tests"
    if tests_dir.is_dir():
        for test_file in tests_dir.glob("*.test.yml"):
            test_files.append(test_file)
        for test_file in tests_dir.glob("*.test.yaml"):
            test_files.append(test_file)

    return sorted(test_files)


def load_test_suite(
    skill_dir: Path,
    test_file: Optional[Path] = None,
) -> tuple[Skill, TestSuiteDefinition]:
    """Load a skill and its test suite.

    Args:
        skill_dir: Path to the skill directory
        test_file: Optional specific test file to load

    Returns:
        Tuple of (Skill, TestSuiteDefinition)

    Raises:
        SkillParseError: If skill cannot be loaded
        TestDefinitionError: If tests cannot be loaded
    """
    # Load skill
    skill = Skill.from_directory(skill_dir)

    # Find test files
    if test_file:
        test_files = [test_file]
    else:
        test_files = discover_tests(skill_dir)

    if not test_files:
        raise TestDefinitionError(f"No tests found for skill: {skill_dir}")

    # Merge all test definitions
    all_tests: list[TestCase] = []
    defaults: dict[str, Any] = {}
    version = "1.0"

    for tf in test_files:
        suite_def = TestSuiteDefinition.from_yaml(tf, skill_dir)
        all_tests.extend(suite_def.tests)
        defaults.update(suite_def.defaults)
        version = suite_def.version

    merged_suite = TestSuiteDefinition(
        version=version,
        skill_path=skill_dir,
        defaults=defaults,
        tests=all_tests,
    )

    return skill, merged_suite


def _compute_similarity(text1: str, text2: str) -> float:
    """Compute similarity ratio between two texts using difflib.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    from difflib import SequenceMatcher

    # Normalize texts
    t1 = text1.strip().lower()
    t2 = text2.strip().lower()

    if not t1 and not t2:
        return 1.0
    if not t1 or not t2:
        return 0.0

    return SequenceMatcher(None, t1, t2).ratio()


def _evaluate_jsonpath(data: Any, path: str) -> Any:
    """Simple JSONPath evaluator for basic paths like $.key.subkey."""
    if not path.startswith("$"):
        raise ValueError("JSONPath must start with $")

    parts = path[1:].split(".")
    result = data

    for part in parts:
        if not part:
            continue
        if isinstance(result, dict):
            result = result.get(part)
        elif isinstance(result, list) and part.isdigit():
            result = result[int(part)]
        else:
            return None

    return result


def evaluate_assertion(assertion: Assertion, response: str) -> AssertionResult:
    """Evaluate a single assertion against a response.

    Args:
        assertion: The assertion to evaluate
        response: The response text to check

    Returns:
        AssertionResult with pass/fail status
    """
    text = response if assertion.case_sensitive else response.lower()
    value = assertion.value
    if value and not assertion.case_sensitive:
        value = value.lower()

    passed = False
    message = ""
    actual: Optional[str] = None

    if assertion.type == AssertionType.CONTAINS:
        if value is None:
            passed = False
            message = "Assertion value is required for 'contains'"
        else:
            passed = value in text
            message = f"Expected response to contain '{assertion.value}'"
            actual = f"...{text[:100]}..." if len(text) > 100 else text

    elif assertion.type == AssertionType.NOT_CONTAINS:
        if value is None:
            passed = False
            message = "Assertion value is required for 'not_contains'"
        else:
            passed = value not in text
            message = f"Expected response to NOT contain '{assertion.value}'"

    elif assertion.type == AssertionType.REGEX:
        if assertion.pattern is None:
            passed = False
            message = "Assertion pattern is required for 'regex'"
        else:
            flags = 0 if assertion.case_sensitive else re.IGNORECASE
            match = re.search(assertion.pattern, response, flags)
            passed = match is not None
            message = f"Expected response to match pattern '{assertion.pattern}'"
            actual = match.group(0) if match else None

    elif assertion.type == AssertionType.STARTS_WITH:
        if value is None:
            passed = False
            message = "Assertion value is required for 'starts_with'"
        else:
            passed = text.startswith(value)
            message = f"Expected response to start with '{assertion.value}'"
            actual = text[: len(value) + 20] if len(text) > len(value) + 20 else text

    elif assertion.type == AssertionType.ENDS_WITH:
        if value is None:
            passed = False
            message = "Assertion value is required for 'ends_with'"
        else:
            passed = text.endswith(value)
            message = f"Expected response to end with '{assertion.value}'"
            actual = text[-len(value) - 20 :] if len(text) > len(value) + 20 else text

    elif assertion.type == AssertionType.LENGTH:
        length = len(response)
        passed = True
        if assertion.min is not None and length < assertion.min:
            passed = False
            message = f"Expected length >= {assertion.min}, got {length}"
        if assertion.max is not None and length > assertion.max:
            passed = False
            message = f"Expected length <= {assertion.max}, got {length}"
        if passed:
            message = f"Length {length} is within bounds"
        actual = str(length)

    elif assertion.type == AssertionType.JSON_VALID:
        try:
            json.loads(response)
            passed = True
            message = "Response is valid JSON"
        except json.JSONDecodeError as e:
            passed = False
            message = f"Response is not valid JSON: {e}"

    elif assertion.type == AssertionType.JSON_PATH:
        if assertion.path is None:
            passed = False
            message = "Assertion path is required for 'json_path'"
        else:
            try:
                data = json.loads(response)
                actual_value = _evaluate_jsonpath(data, assertion.path)
                passed = str(actual_value) == str(assertion.value)
                message = f"JSONPath {assertion.path} = {assertion.value}"
                actual = str(actual_value)
            except Exception as e:
                passed = False
                message = f"JSONPath evaluation failed: {e}"

    elif assertion.type == AssertionType.EQUALS:
        if assertion.value is None:
            passed = False
            message = "Assertion value is required for 'equals'"
        else:
            passed = response.strip() == assertion.value.strip()
            message = "Expected exact match"
            actual = response[:100] + "..." if len(response) > 100 else response

    elif assertion.type == AssertionType.SIMILAR_TO:
        # Use baseline if provided, otherwise use value
        baseline = assertion.baseline or assertion.value
        if baseline is None:
            passed = False
            message = "Assertion baseline or value is required for 'similar_to'"
        else:
            similarity = _compute_similarity(response, baseline)
            passed = similarity >= assertion.threshold
            message = (
                f"Similarity {similarity:.2%} "
                f"{'≥' if passed else '<'} threshold {assertion.threshold:.0%}"
            )
            actual = f"similarity={similarity:.2%}"

    return AssertionResult(
        assertion=assertion,
        passed=passed,
        message=message if not passed else f"OK: {message}",
        actual_value=actual,
    )


def _check_mock_trigger(skill: Skill, user_input: str) -> bool:
    """Check if skill would be triggered in mock mode.

    Uses keyword matching based on skill description and name.
    Supports partial/stem matching for better detection.
    """
    input_lower = user_input.lower()
    input_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", input_lower))

    # Extract keywords from skill name and description
    keywords: set[str] = set()

    # From skill name (split on hyphens)
    for word in skill.name.split("-"):
        if len(word) >= 3:
            keywords.add(word.lower())

    # From description (simple word extraction)
    desc_words = re.findall(r"\b[a-zA-Z]{4,}\b", skill.description.lower())
    keywords.update(desc_words[:10])

    # Check for matches using prefix/stem matching
    matches = 0
    for kw in keywords:
        # Exact match
        if kw in input_lower:
            matches += 1
            continue
        # Stem/prefix match: check if keyword shares a common root with input words
        kw_stem = kw[:4] if len(kw) >= 4 else kw
        for iw in input_words:
            iw_stem = iw[:4] if len(iw) >= 4 else iw
            if kw_stem == iw_stem:
                matches += 1
                break

    # Trigger if at least 1 keyword matches or input mentions skill name
    return matches >= 1 or skill.name.lower().replace("-", " ") in input_lower


def run_test_mock(skill: Skill, test_case: TestCase) -> TestResult:
    """Run a test case in mock mode (no API calls).

    Mock mode uses pattern matching to simulate whether the skill
    would be triggered, then uses the mock response for assertions.

    Args:
        skill: The skill being tested
        test_case: The test case to run

    Returns:
        TestResult with pass/fail status
    """
    start_time = time.perf_counter()

    # Check if test should be skipped
    if test_case.skip_reason:
        return TestResult(
            test_case=test_case,
            status=TestStatus.SKIPPED,
            duration_ms=0,
            error=test_case.skip_reason,
        )

    # Simulate trigger detection using keyword matching
    trigger_detected = _check_mock_trigger(skill, test_case.input)

    # Validate trigger expectation
    assertion_results: list[AssertionResult] = []

    if test_case.trigger.should_trigger != trigger_detected:
        assertion_results.append(
            AssertionResult(
                assertion=Assertion(type=AssertionType.EQUALS, value="trigger"),
                passed=False,
                message=f"Expected trigger={test_case.trigger.should_trigger}, got {trigger_detected}",
            )
        )

    # Get mock response
    response = test_case.mock.response
    if not response:
        response = f"[Mock response for {test_case.name}]"

    # Apply simulated delay
    if test_case.mock.delay > 0:
        time.sleep(test_case.mock.delay)

    # Evaluate assertions against mock response
    for assertion in test_case.assertions:
        result = evaluate_assertion(assertion, response)
        assertion_results.append(result)

    duration_ms = (time.perf_counter() - start_time) * 1000

    # Determine overall status
    all_passed = all(r.passed for r in assertion_results)
    status = TestStatus.PASSED if all_passed else TestStatus.FAILED

    return TestResult(
        test_case=test_case,
        status=status,
        duration_ms=duration_ms,
        assertion_results=assertion_results,
        response=response,
    )


def _build_skill_system_prompt(skill: Skill) -> str:
    """Build system prompt with skill as context."""
    return f"""You have access to the following skill:

Name: {skill.name}
Description: {skill.description}

When the user's request matches this skill's purpose, use the following instructions:

{skill.content}

---

Respond naturally to the user's request, utilizing the skill when appropriate."""


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for API call."""
    input_rate = COST_PER_1K_INPUT_TOKENS.get(model, 0.003)
    output_rate = COST_PER_1K_OUTPUT_TOKENS.get(model, 0.015)

    return (input_tokens / 1000 * input_rate) + (output_tokens / 1000 * output_rate)


def _call_ai_with_skill(
    system_prompt: str,
    messages: list[dict[str, str]],
    provider: str,
    model: str,
    timeout: int,
) -> str:
    """Call AI provider with skill context."""
    import os

    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,  # type: ignore[arg-type]
            timeout=float(timeout),
        )
        return response.content[0].text  # type: ignore[union-attr]

    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        import openai

        client = openai.OpenAI(api_key=api_key)

        all_messages = [{"role": "system", "content": system_prompt}] + messages
        response = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=all_messages,  # type: ignore[arg-type]
            timeout=float(timeout),
        )
        return response.choices[0].message.content or ""

    elif provider == "ollama":
        import urllib.request

        full_prompt = f"{system_prompt}\n\n"
        for msg in messages:
            full_prompt += f"{msg['role'].title()}: {msg['content']}\n"
        full_prompt += "Assistant: "

        data = json.dumps(
            {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
            }
        ).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return str(result.get("response", ""))

    else:
        raise ValueError(f"Unknown provider: {provider}")


def run_test_live(
    skill: Skill,
    test_case: TestCase,
    provider: str,
    model: str,
    timeout: int = 30,
) -> TestResult:
    """Run a test case in live mode (real API calls).

    Args:
        skill: The skill being tested
        test_case: The test case to run
        provider: AI provider to use
        model: Model to use
        timeout: Timeout in seconds

    Returns:
        TestResult with pass/fail status
    """
    start_time = time.perf_counter()

    # Check if test should be skipped
    if test_case.skip_reason:
        return TestResult(
            test_case=test_case,
            status=TestStatus.SKIPPED,
            duration_ms=0,
            error=test_case.skip_reason,
        )

    # Build system prompt with skill content
    system_prompt = _build_skill_system_prompt(skill)

    # Build messages with context
    messages: list[dict[str, str]] = []
    for ctx_msg in test_case.context:
        messages.append({"role": ctx_msg.role, "content": ctx_msg.content})
    messages.append({"role": "user", "content": test_case.input})

    # Call AI provider
    try:
        response = _call_ai_with_skill(
            system_prompt=system_prompt,
            messages=messages,
            provider=provider,
            model=model,
            timeout=timeout,
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return TestResult(
            test_case=test_case,
            status=TestStatus.ERROR,
            duration_ms=duration_ms,
            error=f"API call failed: {e}",
            provider=provider,
            model=model,
        )

    # Evaluate assertions
    assertion_results: list[AssertionResult] = []
    for assertion in test_case.assertions:
        result = evaluate_assertion(assertion, response)
        assertion_results.append(result)

    duration_ms = (time.perf_counter() - start_time) * 1000

    # Estimate cost (rough approximation based on word count)
    input_tokens = len(system_prompt.split()) + sum(
        len(m["content"].split()) for m in messages
    )
    output_tokens = len(response.split())
    cost = _estimate_cost(model, input_tokens, output_tokens)

    # Determine status
    all_passed = all(r.passed for r in assertion_results)
    status = TestStatus.PASSED if all_passed else TestStatus.FAILED

    return TestResult(
        test_case=test_case,
        status=status,
        duration_ms=duration_ms,
        assertion_results=assertion_results,
        response=response,
        provider=provider,
        model=model,
        tokens_used=input_tokens + output_tokens,
        cost_estimate=cost,
    )


def run_test_suite(
    skill: Skill,
    suite: TestSuiteDefinition,
    mode: Literal["mock", "live"] = "mock",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    filter_tags: Optional[list[str]] = None,
    filter_names: Optional[list[str]] = None,
    stop_on_failure: bool = False,
) -> TestSuiteResult:
    """Run a complete test suite.

    Args:
        skill: The skill to test
        suite: Test suite definition
        mode: "mock" or "live"
        provider: AI provider (required for live mode)
        model: Model to use (required for live mode)
        filter_tags: Only run tests with these tags
        filter_names: Only run tests with these names
        stop_on_failure: Stop at first failure

    Returns:
        TestSuiteResult with all test results
    """
    result = TestSuiteResult(
        skill=skill,
        mode=mode,
        start_time=datetime.now(),
    )

    # Filter tests
    tests_to_run = suite.tests

    if filter_tags:
        tests_to_run = [
            t for t in tests_to_run if any(tag in t.tags for tag in filter_tags)
        ]

    if filter_names:
        tests_to_run = [
            t
            for t in tests_to_run
            if t.name in filter_names or any(n in t.name for n in filter_names)
        ]

    # Run tests
    for test_case in tests_to_run:
        if mode == "mock":
            test_result = run_test_mock(skill, test_case)
        else:
            if not provider or not model:
                raise ValueError("Provider and model required for live mode")
            test_result = run_test_live(
                skill,
                test_case,
                provider,
                model,
                timeout=test_case.timeout,
            )

        result.test_results.append(test_result)

        if stop_on_failure and test_result.status == TestStatus.FAILED:
            break

    result.end_time = datetime.now()
    return result


def estimate_live_cost(
    suite: TestSuiteDefinition,
    model: str,
    skill_content_tokens: int = 500,
) -> dict[str, Any]:
    """Estimate cost for running tests in live mode.

    Args:
        suite: Test suite definition
        model: Model to use
        skill_content_tokens: Estimated tokens in skill content

    Returns:
        Dictionary with cost estimates
    """
    num_tests = len([t for t in suite.tests if not t.skip_reason])

    # Estimate tokens per test
    avg_input_per_test = skill_content_tokens + 50  # skill + user input
    avg_output_per_test = 200  # average response length

    total_input = num_tests * avg_input_per_test
    total_output = num_tests * avg_output_per_test

    total_cost = _estimate_cost(model, total_input, total_output)

    return {
        "num_tests": num_tests,
        "estimated_input_tokens": total_input,
        "estimated_output_tokens": total_output,
        "estimated_total_cost": total_cost,
        "model": model,
        "note": "Actual costs may vary based on response lengths",
    }


# =============================================================================
# Regression Testing
# =============================================================================


BASELINE_FILE_NAME = "baselines.yml"


@dataclass
class RegressionBaseline:
    """Baseline response for regression testing.

    Attributes:
        test_name: Name of the test case
        response: Baseline response text
        recorded_at: When the baseline was recorded
        version: Skill version when baseline was recorded
        provider: AI provider used (for live mode)
        model: Model used (for live mode)
    """
    test_name: str
    response: str
    recorded_at: str
    version: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "response": self.response,
            "recorded_at": self.recorded_at,
            "version": self.version,
            "provider": self.provider,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, test_name: str, data: dict) -> RegressionBaseline:
        """Create from dictionary."""
        return cls(
            test_name=test_name,
            response=data["response"],
            recorded_at=data.get("recorded_at", ""),
            version=data.get("version"),
            provider=data.get("provider"),
            model=data.get("model"),
        )


@dataclass
class RegressionBaselineFile:
    """Collection of regression baselines for a skill.

    Stored as baselines.yml in the skill directory.
    """
    version: str = "1"
    skill_version: Optional[str] = None
    baselines: dict[str, RegressionBaseline] = field(default_factory=dict)

    def add_baseline(
        self,
        test_name: str,
        response: str,
        version: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> RegressionBaseline:
        """Add or update a baseline."""
        baseline = RegressionBaseline(
            test_name=test_name,
            response=response,
            recorded_at=datetime.now().isoformat(),
            version=version,
            provider=provider,
            model=model,
        )
        self.baselines[test_name] = baseline
        return baseline

    def get_baseline(self, test_name: str) -> Optional[RegressionBaseline]:
        """Get baseline for a test."""
        return self.baselines.get(test_name)

    def has_baseline(self, test_name: str) -> bool:
        """Check if baseline exists for a test."""
        return test_name in self.baselines

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "skill_version": self.skill_version,
            "baselines": {
                name: bl.to_dict()
                for name, bl in sorted(self.baselines.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> RegressionBaselineFile:
        """Create from dictionary."""
        baselines = {}
        for name, bl_data in data.get("baselines", {}).items():
            baselines[name] = RegressionBaseline.from_dict(name, bl_data)

        return cls(
            version=data.get("version", "1"),
            skill_version=data.get("skill_version"),
            baselines=baselines,
        )

    def save(self, path: Path) -> None:
        """Save baselines to disk."""
        if path.is_dir():
            path = path / BASELINE_FILE_NAME

        content = yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        path.write_text(content)

    @classmethod
    def load(cls, path: Path) -> RegressionBaselineFile:
        """Load baselines from disk."""
        if path.is_dir():
            path = path / BASELINE_FILE_NAME

        if not path.exists():
            raise SkillTestError(f"Baseline file not found: {path}")

        content = path.read_text()
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            raise SkillTestError(f"Invalid baseline file format: {path}")

        return cls.from_dict(data)

    @classmethod
    def load_or_create(cls, path: Path) -> RegressionBaselineFile:
        """Load existing baselines or create new."""
        try:
            return cls.load(path)
        except SkillTestError:
            return cls()


@dataclass
class RegressionResult:
    """Result of a regression test comparison."""
    test_name: str
    passed: bool
    similarity: float
    threshold: float
    current_response: str
    baseline_response: str
    baseline_version: Optional[str] = None
    message: str = ""


@dataclass
class RegressionSuiteResult:
    """Result of running regression tests for a skill."""
    skill_name: str
    skill_version: Optional[str]
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    missing_baselines: int = 0
    results: list[RegressionResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if all regression tests passed."""
        return self.failed_tests == 0


def record_baselines(
    skill: Skill,
    suite: TestSuiteDefinition,
    baselines_path: Path,
    mode: Literal["mock", "live"] = "mock",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    overwrite: bool = False,
) -> RegressionBaselineFile:
    """Record baseline responses for regression testing.

    Args:
        skill: The skill to test
        suite: Test suite definition
        baselines_path: Path to save baselines
        mode: "mock" or "live"
        provider: AI provider (required for live mode)
        model: Model to use (required for live mode)
        overwrite: If True, overwrite existing baselines

    Returns:
        RegressionBaselineFile with recorded baselines
    """
    baselines = RegressionBaselineFile.load_or_create(baselines_path)
    baselines.skill_version = skill.version

    for test_case in suite.tests:
        if test_case.skip_reason:
            continue

        # Skip if baseline exists and not overwriting
        if baselines.has_baseline(test_case.name) and not overwrite:
            continue

        # Run the test to get response
        if mode == "mock":
            result = run_test_mock(skill, test_case)
        else:
            if not provider or not model:
                raise ValueError("Provider and model required for live mode")
            result = run_test_live(skill, test_case, provider, model)

        if result.response:
            baselines.add_baseline(
                test_name=test_case.name,
                response=result.response,
                version=skill.version,
                provider=provider,
                model=model,
            )

    baselines.save(baselines_path)
    return baselines


def run_regression_tests(
    skill: Skill,
    suite: TestSuiteDefinition,
    baselines: RegressionBaselineFile,
    mode: Literal["mock", "live"] = "mock",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    threshold: float = 0.8,
    stop_on_failure: bool = False,
) -> RegressionSuiteResult:
    """Run regression tests comparing current responses to baselines.

    Args:
        skill: The skill to test
        suite: Test suite definition
        baselines: Baseline file to compare against
        mode: "mock" or "live"
        provider: AI provider (required for live mode)
        model: Model to use (required for live mode)
        threshold: Similarity threshold (0.0-1.0)
        stop_on_failure: Stop at first failure

    Returns:
        RegressionSuiteResult with comparison results
    """
    result = RegressionSuiteResult(
        skill_name=skill.name,
        skill_version=skill.version,
    )

    for test_case in suite.tests:
        if test_case.skip_reason:
            continue

        result.total_tests += 1

        # Check if baseline exists
        baseline = baselines.get_baseline(test_case.name)
        if not baseline:
            result.missing_baselines += 1
            result.results.append(RegressionResult(
                test_name=test_case.name,
                passed=False,
                similarity=0.0,
                threshold=threshold,
                current_response="",
                baseline_response="",
                message="No baseline recorded for this test",
            ))
            continue

        # Run the test
        if mode == "mock":
            test_result = run_test_mock(skill, test_case)
        else:
            if not provider or not model:
                raise ValueError("Provider and model required for live mode")
            test_result = run_test_live(skill, test_case, provider, model)

        current_response = test_result.response or ""

        # Compute similarity
        similarity = _compute_similarity(current_response, baseline.response)
        passed = similarity >= threshold

        if passed:
            result.passed_tests += 1
        else:
            result.failed_tests += 1

        regression_result = RegressionResult(
            test_name=test_case.name,
            passed=passed,
            similarity=similarity,
            threshold=threshold,
            current_response=current_response,
            baseline_response=baseline.response,
            baseline_version=baseline.version,
            message=(
                f"Similarity {similarity:.2%} "
                f"{'≥' if passed else '<'} threshold {threshold:.0%}"
            ),
        )
        result.results.append(regression_result)

        if stop_on_failure and not passed:
            break

    return result


def load_baselines(skill_dir: Path) -> RegressionBaselineFile:
    """Load baselines for a skill.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        RegressionBaselineFile
    """
    return RegressionBaselineFile.load(skill_dir)


def has_baselines(skill_dir: Path) -> bool:
    """Check if a skill has recorded baselines.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        True if baselines exist
    """
    baseline_path = skill_dir / BASELINE_FILE_NAME
    return baseline_path.exists()
