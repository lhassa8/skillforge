"""SkillForge Public API - v1.0.0 Stable

This module provides the stable public API for SkillForge.
All exports from this module are considered part of the public API
and follow semantic versioning guarantees.

Usage:
    from skillforge.api import (
        # Core
        Skill,
        validate_skill,

        # Testing
        run_tests,

        # Security
        scan_skill,

        # Platforms
        publish_skill,
        Platform,

        # Analytics
        record_success,
        get_skill_metrics,
    )

API Stability:
- All exports are stable and will not have breaking changes in minor versions
- Deprecated features will have at least one minor version warning before removal
- New features may be added in minor versions
- Breaking changes only in major versions

Version: 1.0.0
"""

from __future__ import annotations

import warnings

# =============================================================================
# Version Information
# =============================================================================

__version__ = "1.0.0"
__api_version__ = "1.0"

# =============================================================================
# Core Skill Management
# =============================================================================

from skillforge.skill import (
    Skill,
    SkillError,
    SkillParseError,
    SkillValidationError,
)

from skillforge.validator import (
    ValidationResult,
    ValidationError as SkillValidationIssue,
    validate_skill,
    validate_skill_directory,
)

from skillforge.bundler import (
    BundleResult,
    bundle_skill,
)

from skillforge.composer import (
    ComposedSkill,
    compose_skills,
)

# =============================================================================
# Versioning
# =============================================================================

from skillforge.versioning import (
    SkillVersion,
    VersionConstraint,
    parse_version,
    parse_constraint,
    version_satisfies,
    bump_version,
)

from skillforge.lockfile import (
    LockFile,
    LockedSkill,
    generate_lockfile,
    load_lockfile,
    verify_lockfile,
)

# =============================================================================
# Testing
# =============================================================================

from skillforge.tester import (
    TestCase,
    TestResult,
    TestSuiteResult,
    TestStatus,
    run_tests,
    run_test_file,
)

# =============================================================================
# Claude Code Integration
# =============================================================================

from skillforge.claude_code import (
    InstallResult,
    InstalledSkill,
    install_skill,
    uninstall_skill,
    list_installed_skills,
    sync_skills,
    get_skills_dir,
)

# =============================================================================
# MCP Integration
# =============================================================================

from skillforge.mcp import (
    # Mapping
    skill_to_mcp_tool,
    mcp_tool_to_skill,
    MCPToolDefinition,
    # Server
    SkillMCPServer,
    MCPServerConfig,
    create_mcp_server,
    # Client
    MCPClient,
    discover_tools,
    import_tool,
)

# =============================================================================
# Security
# =============================================================================

from skillforge.security import (
    # Scanner
    SecurityScanner,
    ScanResult,
    SecurityFinding,
    scan_skill,
    scan_content,
    quick_scan,
    # Patterns
    SecurityPattern,
    Severity,
    SecurityIssueType,
    get_patterns_by_severity,
    get_patterns_by_type,
    SECURITY_PATTERNS,
)

# =============================================================================
# Governance
# =============================================================================

from skillforge.governance import (
    # Trust
    TrustTier,
    TrustMetadata,
    get_trust_metadata,
    set_trust_tier,
    meets_trust_requirement,
    # Policy
    TrustPolicy,
    PolicyCheckResult,
    check_policy,
    enforce_policy,
    load_policy,
    save_policy,
    BUILTIN_POLICIES,
    # Audit
    AuditLogger,
    AuditEvent,
    AuditQuery,
    AuditSummary,
    log_skill_created,
    log_security_scan,
    log_trust_changed,
    log_policy_check,
    log_approval,
    query_events,
    get_audit_summary,
)

# =============================================================================
# Multi-Platform Publishing
# =============================================================================

from skillforge.platforms import (
    # Core types
    Platform,
    PlatformAdapter,
    PlatformCredentials,
    TransformResult,
    PublishResult,
    PublishError,
    TransformError,
    # Registry
    get_adapter,
    list_adapters,
    register_adapter,
    # Adapters
    ClaudeAdapter,
    OpenAIAdapter,
    LangChainAdapter,
    # Convenience functions
    transform_skill,
    publish_skill,
    publish_to_all,
    preview_for_platform,
)

# =============================================================================
# Analytics
# =============================================================================

from skillforge.analytics import (
    # Tracker
    InvocationRecord,
    InvocationStatus,
    SkillMetrics,
    UsageTracker,
    get_tracker,
    set_tracker,
    record_invocation,
    record_success,
    record_failure,
    get_skill_metrics,
    # Reports
    ROIEstimate,
    UsageReport,
    CostBreakdown,
    calculate_roi,
    generate_usage_report,
    generate_cost_breakdown,
    estimate_monthly_cost,
    compare_skills,
    TOKEN_COSTS,
)

# =============================================================================
# Configuration
# =============================================================================

from skillforge.config import (
    SkillForgeConfig,
    ProxyConfig,
    AuthConfig,
    StorageConfig,
    TelemetryConfig,
    AuthProvider,
    StorageBackend,
    LogLevel,
    ConfigError,
    get_config,
    set_config,
    reset_config,
    save_user_config,
    save_project_config,
    validate_config,
    get_skills_directory,
    get_cache_directory,
    is_enterprise_mode,
    get_default_model,
    get_proxy_settings,
)

# =============================================================================
# Migration
# =============================================================================

from skillforge.migrate import (
    SkillFormat,
    MigrationResult,
    BatchMigrationResult,
    MigrationError,
    detect_format,
    migrate_skill,
    migrate_directory,
    validate_migration,
    list_migrations_needed,
    get_migration_preview,
    create_backup,
)

# =============================================================================
# Deprecation Helpers
# =============================================================================


def deprecated(message: str, version: str = "1.1.0"):
    """Decorator to mark a function as deprecated.

    Args:
        message: Deprecation message explaining what to use instead
        version: Version when the function will be removed
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated and will be removed in v{version}. {message}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# =============================================================================
# Public API Exports
# =============================================================================

__all__ = [
    # Version
    "__version__",
    "__api_version__",

    # Core
    "Skill",
    "SkillError",
    "SkillParseError",
    "SkillValidationError",
    "ValidationResult",
    "SkillValidationIssue",
    "validate_skill",
    "validate_skill_directory",
    "BundleResult",
    "bundle_skill",
    "ComposedSkill",
    "compose_skills",

    # Versioning
    "SkillVersion",
    "VersionConstraint",
    "parse_version",
    "parse_constraint",
    "version_satisfies",
    "bump_version",
    "LockFile",
    "LockedSkill",
    "generate_lockfile",
    "load_lockfile",
    "verify_lockfile",

    # Testing
    "TestCase",
    "TestResult",
    "TestSuiteResult",
    "TestStatus",
    "run_tests",
    "run_test_file",

    # Claude Code
    "InstallResult",
    "InstalledSkill",
    "install_skill",
    "uninstall_skill",
    "list_installed_skills",
    "sync_skills",
    "get_skills_dir",

    # MCP
    "skill_to_mcp_tool",
    "mcp_tool_to_skill",
    "MCPToolDefinition",
    "SkillMCPServer",
    "MCPServerConfig",
    "create_mcp_server",
    "MCPClient",
    "discover_tools",
    "import_tool",

    # Security
    "SecurityScanner",
    "ScanResult",
    "SecurityFinding",
    "scan_skill",
    "scan_content",
    "quick_scan",
    "SecurityPattern",
    "Severity",
    "SecurityIssueType",
    "get_patterns_by_severity",
    "get_patterns_by_type",
    "SECURITY_PATTERNS",

    # Governance
    "TrustTier",
    "TrustMetadata",
    "get_trust_metadata",
    "set_trust_tier",
    "meets_trust_requirement",
    "TrustPolicy",
    "PolicyCheckResult",
    "check_policy",
    "enforce_policy",
    "load_policy",
    "save_policy",
    "BUILTIN_POLICIES",
    "AuditLogger",
    "AuditEvent",
    "AuditQuery",
    "AuditSummary",
    "log_skill_created",
    "log_security_scan",
    "log_trust_changed",
    "log_policy_check",
    "log_approval",
    "query_events",
    "get_audit_summary",

    # Platforms
    "Platform",
    "PlatformAdapter",
    "PlatformCredentials",
    "TransformResult",
    "PublishResult",
    "PublishError",
    "TransformError",
    "get_adapter",
    "list_adapters",
    "register_adapter",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "LangChainAdapter",
    "transform_skill",
    "publish_skill",
    "publish_to_all",
    "preview_for_platform",

    # Analytics
    "InvocationRecord",
    "InvocationStatus",
    "SkillMetrics",
    "UsageTracker",
    "get_tracker",
    "set_tracker",
    "record_invocation",
    "record_success",
    "record_failure",
    "get_skill_metrics",
    "ROIEstimate",
    "UsageReport",
    "CostBreakdown",
    "calculate_roi",
    "generate_usage_report",
    "generate_cost_breakdown",
    "estimate_monthly_cost",
    "compare_skills",
    "TOKEN_COSTS",

    # Configuration
    "SkillForgeConfig",
    "ProxyConfig",
    "AuthConfig",
    "StorageConfig",
    "TelemetryConfig",
    "AuthProvider",
    "StorageBackend",
    "LogLevel",
    "ConfigError",
    "get_config",
    "set_config",
    "reset_config",
    "save_user_config",
    "save_project_config",
    "validate_config",
    "get_skills_directory",
    "get_cache_directory",
    "is_enterprise_mode",
    "get_default_model",
    "get_proxy_settings",

    # Migration
    "SkillFormat",
    "MigrationResult",
    "BatchMigrationResult",
    "MigrationError",
    "detect_format",
    "migrate_skill",
    "migrate_directory",
    "validate_migration",
    "list_migrations_needed",
    "get_migration_preview",
    "create_backup",

    # Utilities
    "deprecated",
]
