"""Enterprise governance for SkillForge skills.

This module provides governance features for enterprise skill management:

- Trust tiers for classifying skill sources
- Policies for controlling skill usage in different environments
- Audit trails for tracking skill lifecycle events

Example usage:

    from skillforge.governance import (
        # Trust
        TrustTier,
        get_trust_metadata,
        set_trust_tier,
        meets_trust_requirement,

        # Policy
        TrustPolicy,
        check_policy,
        enforce_policy,
        load_policy,
        BUILTIN_POLICIES,

        # Audit
        AuditLogger,
        log_event,
        log_skill_created,
        log_security_scan,
        query_events,
        AuditQuery,
    )

    # Set trust tier for a skill
    set_trust_tier("./skills/my-skill", TrustTier.VERIFIED, verified_by="admin")

    # Check if skill meets trust requirement
    if meets_trust_requirement("./skills/my-skill", TrustTier.COMMUNITY):
        print("Skill is trusted")

    # Check skill against a policy
    result = check_policy("./skills/my-skill", BUILTIN_POLICIES["production"])
    if result.passed:
        print("Skill meets production policy")
    else:
        print("Violations:", result.violations)

    # Log audit events
    log_skill_created("my-skill")
    log_security_scan("my-skill", passed=True, risk_score=15, finding_count=2)

    # Query audit history
    events = query_events(AuditQuery(skill_name="my-skill", limit=10))
"""

from skillforge.governance.trust import (
    TrustTier,
    TrustMetadata,
    TRUST_FILE,
    TRUST_TIER_DESCRIPTIONS,
    get_trust_metadata,
    set_trust_metadata,
    set_trust_tier,
    meets_trust_requirement,
    get_trust_tier_name,
    get_trust_tier_description,
)

from skillforge.governance.policy import (
    PolicyError,
    PolicyViolation,
    TrustPolicy,
    PolicyCheckResult,
    BUILTIN_POLICIES,
    POLICIES_DIR,
    get_policies_dir,
    save_policy,
    load_policy,
    list_policies,
    delete_policy,
    check_policy,
    enforce_policy,
)

from skillforge.governance.audit import (
    AuditEventType,
    AuditEvent,
    AuditQuery,
    AuditSummary,
    AuditLogger,
    AUDIT_DIR,
    AUDIT_LOG_FILE,
    get_audit_dir,
    get_audit_log_path,
    get_current_actor,
    generate_event_id,
    get_logger,
    set_logger,
    log_event,
    log_skill_created,
    log_skill_modified,
    log_security_scan,
    log_trust_changed,
    log_approval,
    log_policy_check,
    log_deployment,
    query_events,
    get_audit_summary,
)

__all__ = [
    # Trust
    "TrustTier",
    "TrustMetadata",
    "TRUST_FILE",
    "TRUST_TIER_DESCRIPTIONS",
    "get_trust_metadata",
    "set_trust_metadata",
    "set_trust_tier",
    "meets_trust_requirement",
    "get_trust_tier_name",
    "get_trust_tier_description",
    # Policy
    "PolicyError",
    "PolicyViolation",
    "TrustPolicy",
    "PolicyCheckResult",
    "BUILTIN_POLICIES",
    "POLICIES_DIR",
    "get_policies_dir",
    "save_policy",
    "load_policy",
    "list_policies",
    "delete_policy",
    "check_policy",
    "enforce_policy",
    # Audit
    "AuditEventType",
    "AuditEvent",
    "AuditQuery",
    "AuditSummary",
    "AuditLogger",
    "AUDIT_DIR",
    "AUDIT_LOG_FILE",
    "get_audit_dir",
    "get_audit_log_path",
    "get_current_actor",
    "generate_event_id",
    "get_logger",
    "set_logger",
    "log_event",
    "log_skill_created",
    "log_skill_modified",
    "log_security_scan",
    "log_trust_changed",
    "log_approval",
    "log_policy_check",
    "log_deployment",
    "query_events",
    "get_audit_summary",
]
