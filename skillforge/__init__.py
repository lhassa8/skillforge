"""SkillForge - Create, validate, and bundle Anthropic Agent Skills."""

__version__ = "0.6.0"

from skillforge.skill import (
    Skill,
    SkillError,
    SkillParseError,
    SkillValidationError,
    normalize_skill_name,
)
from skillforge.validator import (
    validate_skill_directory,
    validate_skill_md,
    ValidationResult,
)
from skillforge.bundler import (
    bundle_skill,
    extract_skill,
    BundleResult,
)
from skillforge.scaffold import (
    create_skill_scaffold,
    add_reference_doc,
    add_script,
)
from skillforge.templates import (
    SkillTemplate,
    get_template,
    list_templates,
    get_templates_by_category,
    get_template_names,
)
from skillforge.claude_code import (
    install_skill,
    uninstall_skill,
    list_installed_skills,
    sync_skills,
    is_skill_installed,
    InstallResult,
    InstalledSkill,
    USER_SKILLS_DIR,
    PROJECT_SKILLS_DIR,
)
from skillforge.ai import (
    generate_skill,
    improve_skill,
    analyze_skill,
    get_available_providers,
    GenerationResult,
    AnalysisResult,
)
from skillforge.tester import (
    TestCase,
    TestResult,
    TestSuiteResult,
    TestSuiteDefinition,
    AssertionType,
    TestStatus,
    Assertion,
    AssertionResult,
    run_test_suite,
    run_test_mock,
    run_test_live,
    load_test_suite,
    discover_tests,
    evaluate_assertion,
    estimate_live_cost,
    SkillTestError,
    TestDefinitionError,
    TestExecutionError,
)

__all__ = [
    # Version
    "__version__",
    # Skill
    "Skill",
    "SkillError",
    "SkillParseError",
    "SkillValidationError",
    "normalize_skill_name",
    # Validation
    "validate_skill_directory",
    "validate_skill_md",
    "ValidationResult",
    # Bundling
    "bundle_skill",
    "extract_skill",
    "BundleResult",
    # Scaffolding
    "create_skill_scaffold",
    "add_reference_doc",
    "add_script",
    # Templates
    "SkillTemplate",
    "get_template",
    "list_templates",
    "get_templates_by_category",
    "get_template_names",
    # Claude Code Integration
    "install_skill",
    "uninstall_skill",
    "list_installed_skills",
    "sync_skills",
    "is_skill_installed",
    "InstallResult",
    "InstalledSkill",
    "USER_SKILLS_DIR",
    "PROJECT_SKILLS_DIR",
    # AI Generation & Analysis
    "generate_skill",
    "improve_skill",
    "analyze_skill",
    "get_available_providers",
    "GenerationResult",
    "AnalysisResult",
    # Testing
    "TestCase",
    "TestResult",
    "TestSuiteResult",
    "TestSuiteDefinition",
    "AssertionType",
    "TestStatus",
    "Assertion",
    "AssertionResult",
    "run_test_suite",
    "run_test_mock",
    "run_test_live",
    "load_test_suite",
    "discover_tests",
    "evaluate_assertion",
    "estimate_live_cost",
    "SkillTestError",
    "TestDefinitionError",
    "TestExecutionError",
]
