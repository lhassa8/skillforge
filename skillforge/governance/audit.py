"""Audit trail for skill governance.

This module provides audit logging for skill lifecycle events including
creation, modification, approval, deployment, and security scans.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml


class AuditEventType(Enum):
    """Types of audit events."""

    # Lifecycle events
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"

    # Trust events
    TRUST_CHANGED = "trust_changed"
    APPROVED = "approved"
    REVOKED = "revoked"

    # Security events
    SECURITY_SCAN = "security_scan"
    SECURITY_ISSUE_FOUND = "security_issue_found"
    SECURITY_ISSUE_RESOLVED = "security_issue_resolved"

    # Deployment events
    INSTALLED = "installed"
    UNINSTALLED = "uninstalled"
    DEPLOYED = "deployed"

    # Policy events
    POLICY_CHECK = "policy_check"
    POLICY_VIOLATION = "policy_violation"

    # Access events
    ACCESSED = "accessed"
    EXPORTED = "exported"
    IMPORTED = "imported"


@dataclass
class AuditEvent:
    """An audit event in the trail.

    Attributes:
        event_id: Unique event identifier
        timestamp: When the event occurred
        event_type: Type of event
        skill_name: Name of the skill involved
        actor: Who performed the action
        details: Additional event details
        source_ip: Source IP if available
        session_id: Session identifier if available
    """

    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    skill_name: str
    actor: str
    details: dict[str, Any] = field(default_factory=dict)
    source_ip: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "skill_name": self.skill_name,
            "actor": self.actor,
            "details": self.details,
            "source_ip": self.source_ip,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AuditEvent:
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=AuditEventType(data["event_type"]),
            skill_name=data["skill_name"],
            actor=data["actor"],
            details=data.get("details", {}),
            source_ip=data.get("source_ip"),
            session_id=data.get("session_id"),
        )

    def to_json(self) -> str:
        """Convert to JSON line format."""
        return json.dumps(self.to_dict())


@dataclass
class AuditQuery:
    """Query parameters for searching audit events.

    Attributes:
        skill_name: Filter by skill name
        event_types: Filter by event types
        actor: Filter by actor
        from_date: Start date
        to_date: End date
        limit: Maximum results
        offset: Pagination offset
    """

    skill_name: Optional[str] = None
    event_types: Optional[list[AuditEventType]] = None
    actor: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


@dataclass
class AuditSummary:
    """Summary of audit events.

    Attributes:
        total_events: Total number of events
        events_by_type: Count by event type
        events_by_skill: Count by skill name
        events_by_actor: Count by actor
        date_range: (earliest, latest) timestamps
    """

    total_events: int
    events_by_type: dict[str, int]
    events_by_skill: dict[str, int]
    events_by_actor: dict[str, int]
    date_range: tuple[Optional[datetime], Optional[datetime]]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "total_events": self.total_events,
            "events_by_type": self.events_by_type,
            "events_by_skill": self.events_by_skill,
            "events_by_actor": self.events_by_actor,
            "date_range": {
                "from": self.date_range[0].isoformat() if self.date_range[0] else None,
                "to": self.date_range[1].isoformat() if self.date_range[1] else None,
            },
        }


# =============================================================================
# Audit Log Storage
# =============================================================================

# Default audit log location
AUDIT_DIR = Path.home() / ".config" / "skillforge" / "audit"
AUDIT_LOG_FILE = "audit.jsonl"


def get_audit_dir() -> Path:
    """Get the audit directory, creating if needed."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIT_DIR


def get_audit_log_path(audit_dir: Optional[Path] = None) -> Path:
    """Get the path to the audit log file."""
    if audit_dir is None:
        audit_dir = get_audit_dir()
    return Path(audit_dir) / AUDIT_LOG_FILE


def get_current_actor() -> str:
    """Get the current actor (user) for audit events."""
    # Try various environment variables
    actor = os.environ.get("SKILLFORGE_ACTOR")
    if actor:
        return actor

    actor = os.environ.get("USER") or os.environ.get("USERNAME")
    if actor:
        return actor

    return "unknown"


def generate_event_id() -> str:
    """Generate a unique event ID."""
    return str(uuid.uuid4())


# =============================================================================
# Audit Logger
# =============================================================================


class AuditLogger:
    """Logger for audit events.

    Attributes:
        audit_dir: Directory for audit logs
        enabled: Whether logging is enabled
    """

    def __init__(
        self,
        audit_dir: Optional[Path] = None,
        enabled: bool = True,
    ):
        self.audit_dir = Path(audit_dir) if audit_dir else get_audit_dir()
        self.enabled = enabled
        self._ensure_audit_dir()

    def _ensure_audit_dir(self) -> None:
        """Ensure the audit directory exists."""
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self) -> Path:
        """Get the current audit log path."""
        return self.audit_dir / AUDIT_LOG_FILE

    def log(
        self,
        event_type: AuditEventType,
        skill_name: str,
        actor: Optional[str] = None,
        details: Optional[dict] = None,
        source_ip: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log an audit event.

        Args:
            event_type: Type of event
            skill_name: Name of skill involved
            actor: Who performed the action (defaults to current user)
            details: Additional details
            source_ip: Source IP address
            session_id: Session identifier

        Returns:
            The logged AuditEvent
        """
        event = AuditEvent(
            event_id=generate_event_id(),
            timestamp=datetime.now(),
            event_type=event_type,
            skill_name=skill_name,
            actor=actor or get_current_actor(),
            details=details or {},
            source_ip=source_ip,
            session_id=session_id,
        )

        if self.enabled:
            log_path = self._get_log_path()
            with open(log_path, "a") as f:
                f.write(event.to_json() + "\n")

        return event

    def query(self, query: AuditQuery) -> list[AuditEvent]:
        """Query audit events.

        Args:
            query: Query parameters

        Returns:
            List of matching events
        """
        log_path = self._get_log_path()

        if not log_path.exists():
            return []

        events = []
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    event = AuditEvent.from_dict(data)

                    # Apply filters
                    if query.skill_name and event.skill_name != query.skill_name:
                        continue

                    if query.event_types and event.event_type not in query.event_types:
                        continue

                    if query.actor and event.actor != query.actor:
                        continue

                    if query.from_date and event.timestamp < query.from_date:
                        continue

                    if query.to_date and event.timestamp > query.to_date:
                        continue

                    events.append(event)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        # Sort by timestamp descending (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply pagination
        start = query.offset
        end = start + query.limit

        return events[start:end]

    def get_events_for_skill(
        self,
        skill_name: str,
        limit: int = 50,
    ) -> list[AuditEvent]:
        """Get audit events for a specific skill.

        Args:
            skill_name: Name of the skill
            limit: Maximum number of events

        Returns:
            List of events for the skill
        """
        return self.query(AuditQuery(skill_name=skill_name, limit=limit))

    def get_recent_events(self, limit: int = 50) -> list[AuditEvent]:
        """Get the most recent audit events.

        Args:
            limit: Maximum number of events

        Returns:
            List of recent events
        """
        return self.query(AuditQuery(limit=limit))

    def get_summary(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> AuditSummary:
        """Get a summary of audit events.

        Args:
            from_date: Start date filter
            to_date: End date filter

        Returns:
            AuditSummary with aggregated data
        """
        # Get all events (with a high limit)
        events = self.query(
            AuditQuery(from_date=from_date, to_date=to_date, limit=100000)
        )

        events_by_type: dict[str, int] = {}
        events_by_skill: dict[str, int] = {}
        events_by_actor: dict[str, int] = {}
        earliest: Optional[datetime] = None
        latest: Optional[datetime] = None

        for event in events:
            # Count by type
            type_name = event.event_type.value
            events_by_type[type_name] = events_by_type.get(type_name, 0) + 1

            # Count by skill
            events_by_skill[event.skill_name] = (
                events_by_skill.get(event.skill_name, 0) + 1
            )

            # Count by actor
            events_by_actor[event.actor] = events_by_actor.get(event.actor, 0) + 1

            # Track date range
            if earliest is None or event.timestamp < earliest:
                earliest = event.timestamp
            if latest is None or event.timestamp > latest:
                latest = event.timestamp

        return AuditSummary(
            total_events=len(events),
            events_by_type=events_by_type,
            events_by_skill=events_by_skill,
            events_by_actor=events_by_actor,
            date_range=(earliest, latest),
        )

    def clear(self) -> int:
        """Clear all audit events.

        Returns:
            Number of events cleared
        """
        log_path = self._get_log_path()

        if not log_path.exists():
            return 0

        # Count lines
        with open(log_path, "r") as f:
            count = sum(1 for line in f if line.strip())

        # Clear file
        log_path.write_text("")

        return count


# =============================================================================
# Global Logger Instance
# =============================================================================

_logger: Optional[AuditLogger] = None


def get_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _logger
    if _logger is None:
        _logger = AuditLogger()
    return _logger


def set_logger(logger: AuditLogger) -> None:
    """Set the global audit logger instance."""
    global _logger
    _logger = logger


# =============================================================================
# Convenience Functions
# =============================================================================


def log_event(
    event_type: AuditEventType,
    skill_name: str,
    actor: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditEvent:
    """Log an audit event using the global logger.

    Args:
        event_type: Type of event
        skill_name: Name of skill involved
        actor: Who performed the action
        details: Additional details

    Returns:
        The logged AuditEvent
    """
    return get_logger().log(event_type, skill_name, actor, details)


def log_skill_created(skill_name: str, actor: Optional[str] = None) -> AuditEvent:
    """Log a skill creation event."""
    return log_event(AuditEventType.CREATED, skill_name, actor)


def log_skill_modified(
    skill_name: str,
    changes: Optional[dict] = None,
    actor: Optional[str] = None,
) -> AuditEvent:
    """Log a skill modification event."""
    return log_event(AuditEventType.MODIFIED, skill_name, actor, {"changes": changes})


def log_security_scan(
    skill_name: str,
    passed: bool,
    risk_score: int,
    finding_count: int,
    actor: Optional[str] = None,
) -> AuditEvent:
    """Log a security scan event."""
    return log_event(
        AuditEventType.SECURITY_SCAN,
        skill_name,
        actor,
        {
            "passed": passed,
            "risk_score": risk_score,
            "finding_count": finding_count,
        },
    )


def log_trust_changed(
    skill_name: str,
    old_tier: str,
    new_tier: str,
    actor: Optional[str] = None,
) -> AuditEvent:
    """Log a trust tier change event."""
    return log_event(
        AuditEventType.TRUST_CHANGED,
        skill_name,
        actor,
        {"old_tier": old_tier, "new_tier": new_tier},
    )


def log_approval(
    skill_name: str,
    approval_id: str,
    tier: str,
    actor: Optional[str] = None,
) -> AuditEvent:
    """Log an approval event."""
    return log_event(
        AuditEventType.APPROVED,
        skill_name,
        actor,
        {"approval_id": approval_id, "tier": tier},
    )


def log_policy_check(
    skill_name: str,
    policy_name: str,
    passed: bool,
    violations: Optional[list[str]] = None,
    actor: Optional[str] = None,
) -> AuditEvent:
    """Log a policy check event."""
    event_type = AuditEventType.POLICY_CHECK if passed else AuditEventType.POLICY_VIOLATION
    return log_event(
        event_type,
        skill_name,
        actor,
        {"policy": policy_name, "passed": passed, "violations": violations or []},
    )


def log_deployment(
    skill_name: str,
    environment: str,
    version: Optional[str] = None,
    actor: Optional[str] = None,
) -> AuditEvent:
    """Log a deployment event."""
    return log_event(
        AuditEventType.DEPLOYED,
        skill_name,
        actor,
        {"environment": environment, "version": version},
    )


def query_events(query: AuditQuery) -> list[AuditEvent]:
    """Query audit events using the global logger."""
    return get_logger().query(query)


def get_audit_summary(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> AuditSummary:
    """Get audit summary using the global logger."""
    return get_logger().get_summary(from_date, to_date)
