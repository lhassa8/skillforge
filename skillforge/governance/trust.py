"""Trust tier system for skill governance.

This module provides trust tiers for classifying skills based on
their source, verification status, and security posture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Optional

import yaml


class TrustTier(IntEnum):
    """Trust tiers for skills.

    Higher values indicate higher trust levels.
    """

    UNTRUSTED = 0  # Unknown source, not verified
    COMMUNITY = 1  # From community registry, basic checks
    VERIFIED = 2  # Verified publisher, security scanned
    ENTERPRISE = 3  # Internal/approved, full audit trail


TRUST_TIER_DESCRIPTIONS = {
    TrustTier.UNTRUSTED: "Unknown source, not verified. Use with caution.",
    TrustTier.COMMUNITY: "Community-contributed skill with basic verification.",
    TrustTier.VERIFIED: "Verified publisher with security scanning.",
    TrustTier.ENTERPRISE: "Enterprise-approved with full audit trail.",
}


@dataclass
class TrustMetadata:
    """Trust metadata for a skill.

    Attributes:
        tier: Current trust tier
        verified_at: When the skill was last verified
        verified_by: Who verified the skill
        security_scan_passed: Whether security scan passed
        security_scan_date: When security was last scanned
        approval_id: Approval record ID if enterprise tier
        notes: Additional notes about trust status
    """

    tier: TrustTier = TrustTier.UNTRUSTED
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    security_scan_passed: Optional[bool] = None
    security_scan_date: Optional[datetime] = None
    approval_id: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "tier": self.tier.name.lower(),
            "tier_value": int(self.tier),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_by": self.verified_by,
            "security_scan_passed": self.security_scan_passed,
            "security_scan_date": (
                self.security_scan_date.isoformat() if self.security_scan_date else None
            ),
            "approval_id": self.approval_id,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrustMetadata:
        """Create from dictionary."""
        tier_str = data.get("tier", "untrusted").upper()
        try:
            tier = TrustTier[tier_str]
        except KeyError:
            tier = TrustTier.UNTRUSTED

        verified_at = None
        if data.get("verified_at"):
            verified_at = datetime.fromisoformat(data["verified_at"])

        security_scan_date = None
        if data.get("security_scan_date"):
            security_scan_date = datetime.fromisoformat(data["security_scan_date"])

        return cls(
            tier=tier,
            verified_at=verified_at,
            verified_by=data.get("verified_by"),
            security_scan_passed=data.get("security_scan_passed"),
            security_scan_date=security_scan_date,
            approval_id=data.get("approval_id"),
            notes=data.get("notes", ""),
        )


# Trust metadata file name
TRUST_FILE = ".trust.yml"


def get_trust_metadata(skill_path: Path) -> TrustMetadata:
    """Get trust metadata for a skill.

    Args:
        skill_path: Path to skill directory

    Returns:
        TrustMetadata for the skill
    """
    skill_path = Path(skill_path)
    trust_file = skill_path / TRUST_FILE

    if not trust_file.exists():
        return TrustMetadata()

    try:
        content = trust_file.read_text()
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            return TrustMetadata.from_dict(data)
    except (yaml.YAMLError, OSError):
        pass

    return TrustMetadata()


def set_trust_metadata(skill_path: Path, metadata: TrustMetadata) -> None:
    """Set trust metadata for a skill.

    Args:
        skill_path: Path to skill directory
        metadata: Trust metadata to set
    """
    skill_path = Path(skill_path)
    trust_file = skill_path / TRUST_FILE

    content = yaml.dump(
        metadata.to_dict(),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    trust_file.write_text(content)


def set_trust_tier(
    skill_path: Path,
    tier: TrustTier,
    verified_by: Optional[str] = None,
    notes: str = "",
) -> TrustMetadata:
    """Set the trust tier for a skill.

    Args:
        skill_path: Path to skill directory
        tier: Trust tier to set
        verified_by: Who is setting the trust tier
        notes: Additional notes

    Returns:
        Updated TrustMetadata
    """
    metadata = get_trust_metadata(skill_path)
    metadata.tier = tier
    metadata.verified_at = datetime.now()
    metadata.verified_by = verified_by
    metadata.notes = notes

    set_trust_metadata(skill_path, metadata)
    return metadata


def meets_trust_requirement(skill_path: Path, required_tier: TrustTier) -> bool:
    """Check if a skill meets a trust tier requirement.

    Args:
        skill_path: Path to skill directory
        required_tier: Minimum required trust tier

    Returns:
        True if skill meets or exceeds required tier
    """
    metadata = get_trust_metadata(skill_path)
    return metadata.tier >= required_tier


def get_trust_tier_name(tier: TrustTier) -> str:
    """Get human-readable name for a trust tier."""
    return tier.name.lower().replace("_", " ").title()


def get_trust_tier_description(tier: TrustTier) -> str:
    """Get description for a trust tier."""
    return TRUST_TIER_DESCRIPTIONS.get(tier, "Unknown trust tier")
