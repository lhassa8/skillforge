"""SkillForge - Create, validate, and bundle Anthropic Agent Skills."""

__version__ = "0.2.0"

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
from skillforge.ai import (
    generate_skill,
    improve_skill,
    get_available_providers,
    GenerationResult,
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
    # AI Generation
    "generate_skill",
    "improve_skill",
    "get_available_providers",
    "GenerationResult",
]
