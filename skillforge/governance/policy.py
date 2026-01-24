"""Policy management for skill governance.

This module provides policy definitions and enforcement for controlling
which skills can be used in different environments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from skillforge.governance.trust import TrustTier, get_trust_metadata
from skillforge.security import ScanResult, Severity


class PolicyError(Exception):
    """Raised when policy operations fail."""

    pass


class PolicyViolation(Exception):
    """Raised when a skill violates a policy."""

    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


@dataclass
class TrustPolicy:
    """A policy for skill usage and deployment.

    Attributes:
        name: Policy name (e.g., "production", "development")
        description: Human-readable description
        min_trust_tier: Minimum required trust tier
        require_security_scan: Whether security scan is required
        max_risk_score: Maximum allowed risk score (0-100)
        min_severity_block: Minimum severity that blocks deployment
        allowed_sources: List of allowed skill sources (registries)
        blocked_patterns: Security patterns that block deployment
        approval_required: Whether manual approval is required
        created_at: When the policy was created
        updated_at: When the policy was last updated
    """

    name: str
    description: str = ""
    min_trust_tier: TrustTier = TrustTier.UNTRUSTED
    require_security_scan: bool = False
    max_risk_score: int = 100
    min_severity_block: Optional[Severity] = None
    allowed_sources: list[str] = field(default_factory=list)
    blocked_patterns: list[str] = field(default_factory=list)
    approval_required: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "min_trust_tier": self.min_trust_tier.name.lower(),
            "require_security_scan": self.require_security_scan,
            "max_risk_score": self.max_risk_score,
            "min_severity_block": (
                self.min_severity_block.value if self.min_severity_block else None
            ),
            "allowed_sources": self.allowed_sources,
            "blocked_patterns": self.blocked_patterns,
            "approval_required": self.approval_required,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrustPolicy:
        """Create from dictionary."""
        tier_str = data.get("min_trust_tier", "untrusted").upper()
        try:
            min_trust_tier = TrustTier[tier_str]
        except KeyError:
            min_trust_tier = TrustTier.UNTRUSTED

        min_severity_block = None
        if data.get("min_severity_block"):
            try:
                min_severity_block = Severity(data["min_severity_block"])
            except ValueError:
                pass

        created_at = datetime.now()
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        updated_at = datetime.now()
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            min_trust_tier=min_trust_tier,
            require_security_scan=data.get("require_security_scan", False),
            max_risk_score=data.get("max_risk_score", 100),
            min_severity_block=min_severity_block,
            allowed_sources=data.get("allowed_sources", []),
            blocked_patterns=data.get("blocked_patterns", []),
            approval_required=data.get("approval_required", False),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class PolicyCheckResult:
    """Result of checking a skill against a policy.

    Attributes:
        policy_name: Name of the policy checked
        skill_name: Name of the skill checked
        passed: Whether the skill passed the policy
        violations: List of policy violations
        warnings: List of warnings (non-blocking)
        checked_at: When the check was performed
    """

    policy_name: str
    skill_name: str
    passed: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "policy_name": self.policy_name,
            "skill_name": self.skill_name,
            "passed": self.passed,
            "violations": self.violations,
            "warnings": self.warnings,
            "checked_at": self.checked_at.isoformat(),
        }


# =============================================================================
# Built-in Policies
# =============================================================================

BUILTIN_POLICIES = {
    "development": TrustPolicy(
        name="development",
        description="Permissive policy for development environments",
        min_trust_tier=TrustTier.UNTRUSTED,
        require_security_scan=False,
        max_risk_score=100,
        approval_required=False,
    ),
    "staging": TrustPolicy(
        name="staging",
        description="Moderate policy for staging environments",
        min_trust_tier=TrustTier.COMMUNITY,
        require_security_scan=True,
        max_risk_score=50,
        min_severity_block=Severity.CRITICAL,
        approval_required=False,
    ),
    "production": TrustPolicy(
        name="production",
        description="Strict policy for production environments",
        min_trust_tier=TrustTier.VERIFIED,
        require_security_scan=True,
        max_risk_score=20,
        min_severity_block=Severity.HIGH,
        approval_required=True,
    ),
    "enterprise": TrustPolicy(
        name="enterprise",
        description="Maximum security policy for enterprise environments",
        min_trust_tier=TrustTier.ENTERPRISE,
        require_security_scan=True,
        max_risk_score=0,
        min_severity_block=Severity.MEDIUM,
        approval_required=True,
        blocked_patterns=[
            "api_key_pattern",
            "aws_key",
            "private_key",
            "password_in_content",
        ],
    ),
}


# =============================================================================
# Policy Storage
# =============================================================================

# Default policy storage location
POLICIES_DIR = Path.home() / ".config" / "skillforge" / "policies"


def get_policies_dir() -> Path:
    """Get the policies directory, creating if needed."""
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)
    return POLICIES_DIR


def save_policy(policy: TrustPolicy, policies_dir: Optional[Path] = None) -> Path:
    """Save a policy to disk.

    Args:
        policy: The policy to save
        policies_dir: Directory to save to (defaults to user config)

    Returns:
        Path to the saved policy file
    """
    if policies_dir is None:
        policies_dir = get_policies_dir()
    else:
        policies_dir = Path(policies_dir)
        policies_dir.mkdir(parents=True, exist_ok=True)

    policy.updated_at = datetime.now()
    policy_file = policies_dir / f"{policy.name}.yml"

    content = yaml.dump(
        policy.to_dict(),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    policy_file.write_text(content)

    return policy_file


def load_policy(name: str, policies_dir: Optional[Path] = None) -> TrustPolicy:
    """Load a policy by name.

    Args:
        name: Policy name
        policies_dir: Directory to load from

    Returns:
        The loaded policy

    Raises:
        PolicyError: If policy not found
    """
    # Check built-in policies first
    if name in BUILTIN_POLICIES:
        return BUILTIN_POLICIES[name]

    # Check custom policies
    if policies_dir is None:
        policies_dir = get_policies_dir()

    policy_file = Path(policies_dir) / f"{name}.yml"

    if not policy_file.exists():
        raise PolicyError(f"Policy not found: {name}")

    try:
        content = policy_file.read_text()
        data = yaml.safe_load(content)
        return TrustPolicy.from_dict(data)
    except (yaml.YAMLError, OSError) as e:
        raise PolicyError(f"Error loading policy: {e}")


def list_policies(policies_dir: Optional[Path] = None) -> list[TrustPolicy]:
    """List all available policies.

    Args:
        policies_dir: Directory to list from

    Returns:
        List of policies (built-in + custom)
    """
    policies = list(BUILTIN_POLICIES.values())

    if policies_dir is None:
        policies_dir = get_policies_dir()

    # Add custom policies
    for policy_file in Path(policies_dir).glob("*.yml"):
        try:
            content = policy_file.read_text()
            data = yaml.safe_load(content)
            policy = TrustPolicy.from_dict(data)
            # Don't duplicate built-in policies
            if policy.name not in BUILTIN_POLICIES:
                policies.append(policy)
        except (yaml.YAMLError, OSError):
            continue

    return policies


def delete_policy(name: str, policies_dir: Optional[Path] = None) -> bool:
    """Delete a custom policy.

    Args:
        name: Policy name
        policies_dir: Directory to delete from

    Returns:
        True if deleted, False if not found

    Raises:
        PolicyError: If trying to delete built-in policy
    """
    if name in BUILTIN_POLICIES:
        raise PolicyError(f"Cannot delete built-in policy: {name}")

    if policies_dir is None:
        policies_dir = get_policies_dir()

    policy_file = Path(policies_dir) / f"{name}.yml"

    if policy_file.exists():
        policy_file.unlink()
        return True

    return False


# =============================================================================
# Policy Enforcement
# =============================================================================


def check_policy(
    skill_path: Path,
    policy: TrustPolicy,
    scan_result: Optional["ScanResult"] = None,
) -> PolicyCheckResult:
    """Check a skill against a policy.

    Args:
        skill_path: Path to skill directory
        policy: Policy to check against
        scan_result: Optional pre-computed scan result

    Returns:
        PolicyCheckResult indicating pass/fail and violations
    """
    from skillforge.skill import Skill

    skill_path = Path(skill_path)
    violations = []
    warnings = []

    # Load skill
    try:
        skill = Skill.from_directory(skill_path)
        skill_name = skill.name
    except Exception as e:
        return PolicyCheckResult(
            policy_name=policy.name,
            skill_name=str(skill_path.name),
            passed=False,
            violations=[f"Cannot load skill: {e}"],
        )

    # Check trust tier
    trust_metadata = get_trust_metadata(skill_path)
    if trust_metadata.tier < policy.min_trust_tier:
        violations.append(
            f"Trust tier {trust_metadata.tier.name} is below required "
            f"{policy.min_trust_tier.name}"
        )

    # Check security scan if required
    if policy.require_security_scan:
        if scan_result is None:
            from skillforge.security import scan_skill

            scan_result = scan_skill(skill_path)

        # Check risk score
        if scan_result.risk_score > policy.max_risk_score:
            violations.append(
                f"Risk score {scan_result.risk_score} exceeds maximum "
                f"{policy.max_risk_score}"
            )

        # Check severity blocking
        if policy.min_severity_block:
            severity_order = {
                Severity.CRITICAL: 0,
                Severity.HIGH: 1,
                Severity.MEDIUM: 2,
                Severity.LOW: 3,
                Severity.INFO: 4,
            }
            block_level = severity_order[policy.min_severity_block]

            for finding in scan_result.findings:
                if severity_order[finding.severity] <= block_level:
                    violations.append(
                        f"Security issue blocked by policy: "
                        f"{finding.severity.value} - {finding.description}"
                    )

        # Check blocked patterns
        for finding in scan_result.findings:
            if finding.pattern_name in policy.blocked_patterns:
                violations.append(
                    f"Blocked pattern detected: {finding.pattern_name}"
                )

    # Check approval if required
    if policy.approval_required:
        if not trust_metadata.approval_id:
            warnings.append("Policy requires approval but skill is not approved")

    passed = len(violations) == 0

    return PolicyCheckResult(
        policy_name=policy.name,
        skill_name=skill_name,
        passed=passed,
        violations=violations,
        warnings=warnings,
    )


def enforce_policy(
    skill_path: Path,
    policy_name: str,
    scan_result: Optional["ScanResult"] = None,
) -> PolicyCheckResult:
    """Enforce a policy on a skill, raising if violations.

    Args:
        skill_path: Path to skill directory
        policy_name: Name of policy to enforce
        scan_result: Optional pre-computed scan result

    Returns:
        PolicyCheckResult if passed

    Raises:
        PolicyViolation: If skill violates the policy
    """
    policy = load_policy(policy_name)
    result = check_policy(skill_path, policy, scan_result)

    if not result.passed:
        raise PolicyViolation(
            f"Skill '{result.skill_name}' violates policy '{policy_name}'",
            result.violations,
        )

    return result
