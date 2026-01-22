"""Usage tracking for SkillForge skills.

This module provides functionality to track skill usage metrics
including invocations, latency, costs, and success rates.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class InvocationStatus(Enum):
    """Status of a skill invocation."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class InvocationRecord:
    """Record of a single skill invocation.

    Attributes:
        skill_name: Name of the skill invoked
        timestamp: When the invocation occurred
        status: Outcome of the invocation
        latency_ms: Response time in milliseconds
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost: Estimated cost in USD
        model: Model used for the invocation
        platform: Platform where invocation occurred
        metadata: Additional invocation metadata
    """

    skill_name: str
    timestamp: datetime
    status: InvocationStatus
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    model: Optional[str] = None
    platform: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "skill_name": self.skill_name,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost": self.cost,
            "model": self.model,
            "platform": self.platform,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> InvocationRecord:
        """Create from dictionary."""
        return cls(
            skill_name=data["skill_name"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status=InvocationStatus(data["status"]),
            latency_ms=data.get("latency_ms", 0.0),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cost=data.get("cost", 0.0),
            model=data.get("model"),
            platform=data.get("platform"),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Convert to JSON line format."""
        return json.dumps(self.to_dict())


@dataclass
class SkillMetrics:
    """Aggregated metrics for a skill.

    Attributes:
        skill_name: Name of the skill
        total_invocations: Total number of invocations
        successful_invocations: Number of successful invocations
        failed_invocations: Number of failed invocations
        total_latency_ms: Sum of all latencies
        total_input_tokens: Sum of all input tokens
        total_output_tokens: Sum of all output tokens
        total_cost: Sum of all costs
        first_invocation: Earliest invocation timestamp
        last_invocation: Latest invocation timestamp
    """

    skill_name: str
    total_invocations: int = 0
    successful_invocations: int = 0
    failed_invocations: int = 0
    total_latency_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    first_invocation: Optional[datetime] = None
    last_invocation: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_invocations == 0:
            return 0.0
        return (self.successful_invocations / self.total_invocations) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.total_invocations == 0:
            return 0.0
        return self.total_latency_ms / self.total_invocations

    @property
    def avg_cost(self) -> float:
        """Calculate average cost per invocation."""
        if self.total_invocations == 0:
            return 0.0
        return self.total_cost / self.total_invocations

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        return self.total_input_tokens + self.total_output_tokens

    def add_invocation(self, record: InvocationRecord) -> None:
        """Add an invocation record to the metrics."""
        self.total_invocations += 1
        self.total_latency_ms += record.latency_ms
        self.total_input_tokens += record.input_tokens
        self.total_output_tokens += record.output_tokens
        self.total_cost += record.cost

        if record.status == InvocationStatus.SUCCESS:
            self.successful_invocations += 1
        else:
            self.failed_invocations += 1

        if self.first_invocation is None or record.timestamp < self.first_invocation:
            self.first_invocation = record.timestamp
        if self.last_invocation is None or record.timestamp > self.last_invocation:
            self.last_invocation = record.timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "skill_name": self.skill_name,
            "total_invocations": self.total_invocations,
            "successful_invocations": self.successful_invocations,
            "failed_invocations": self.failed_invocations,
            "success_rate": self.success_rate,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_cost": self.avg_cost,
            "first_invocation": self.first_invocation.isoformat() if self.first_invocation else None,
            "last_invocation": self.last_invocation.isoformat() if self.last_invocation else None,
        }


# =============================================================================
# Analytics Storage
# =============================================================================

ANALYTICS_DIR = Path.home() / ".config" / "skillforge" / "analytics"
ANALYTICS_LOG_FILE = "invocations.jsonl"


def get_analytics_dir() -> Path:
    """Get the analytics directory, creating if needed."""
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    return ANALYTICS_DIR


def get_analytics_log_path(analytics_dir: Optional[Path] = None) -> Path:
    """Get the path to the analytics log file."""
    if analytics_dir is None:
        analytics_dir = get_analytics_dir()
    return Path(analytics_dir) / ANALYTICS_LOG_FILE


# =============================================================================
# Usage Tracker
# =============================================================================


class UsageTracker:
    """Tracker for skill usage metrics.

    Attributes:
        analytics_dir: Directory for analytics data
        enabled: Whether tracking is enabled
    """

    def __init__(
        self,
        analytics_dir: Optional[Path] = None,
        enabled: bool = True,
    ):
        self.analytics_dir = Path(analytics_dir) if analytics_dir else get_analytics_dir()
        self.enabled = enabled
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure the analytics directory exists."""
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self) -> Path:
        """Get the current analytics log path."""
        return self.analytics_dir / ANALYTICS_LOG_FILE

    def record(
        self,
        skill_name: str,
        status: InvocationStatus,
        latency_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        model: Optional[str] = None,
        platform: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> InvocationRecord:
        """Record a skill invocation.

        Args:
            skill_name: Name of the skill
            status: Outcome of the invocation
            latency_ms: Response time
            input_tokens: Input token count
            output_tokens: Output token count
            cost: Estimated cost
            model: Model used
            platform: Platform used
            metadata: Additional metadata

        Returns:
            The recorded InvocationRecord
        """
        record = InvocationRecord(
            skill_name=skill_name,
            timestamp=datetime.now(),
            status=status,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            model=model,
            platform=platform,
            metadata=metadata or {},
        )

        if self.enabled:
            log_path = self._get_log_path()
            with open(log_path, "a") as f:
                f.write(record.to_json() + "\n")

        return record

    def get_records(
        self,
        skill_name: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        status: Optional[InvocationStatus] = None,
        limit: int = 1000,
    ) -> list[InvocationRecord]:
        """Get invocation records with optional filtering.

        Args:
            skill_name: Filter by skill name
            from_date: Start date filter
            to_date: End date filter
            status: Filter by status
            limit: Maximum records to return

        Returns:
            List of matching InvocationRecords
        """
        log_path = self._get_log_path()

        if not log_path.exists():
            return []

        records = []
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    record = InvocationRecord.from_dict(data)

                    # Apply filters
                    if skill_name and record.skill_name != skill_name:
                        continue
                    if from_date and record.timestamp < from_date:
                        continue
                    if to_date and record.timestamp > to_date:
                        continue
                    if status and record.status != status:
                        continue

                    records.append(record)

                    if len(records) >= limit:
                        break

                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        # Sort by timestamp descending
        records.sort(key=lambda r: r.timestamp, reverse=True)

        return records

    def get_metrics(
        self,
        skill_name: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> SkillMetrics:
        """Get aggregated metrics for a skill.

        Args:
            skill_name: Name of the skill
            from_date: Start date filter
            to_date: End date filter

        Returns:
            SkillMetrics with aggregated data
        """
        records = self.get_records(
            skill_name=skill_name,
            from_date=from_date,
            to_date=to_date,
            limit=100000,
        )

        metrics = SkillMetrics(skill_name=skill_name)
        for record in records:
            metrics.add_invocation(record)

        return metrics

    def get_all_metrics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict[str, SkillMetrics]:
        """Get metrics for all tracked skills.

        Args:
            from_date: Start date filter
            to_date: End date filter

        Returns:
            Dictionary mapping skill names to their metrics
        """
        records = self.get_records(
            from_date=from_date,
            to_date=to_date,
            limit=100000,
        )

        metrics_by_skill: dict[str, SkillMetrics] = {}
        for record in records:
            if record.skill_name not in metrics_by_skill:
                metrics_by_skill[record.skill_name] = SkillMetrics(
                    skill_name=record.skill_name
                )
            metrics_by_skill[record.skill_name].add_invocation(record)

        return metrics_by_skill

    def get_period_metrics(
        self,
        skill_name: str,
        period_days: int = 30,
    ) -> SkillMetrics:
        """Get metrics for a specific time period.

        Args:
            skill_name: Name of the skill
            period_days: Number of days to include

        Returns:
            SkillMetrics for the period
        """
        from_date = datetime.now() - timedelta(days=period_days)
        return self.get_metrics(skill_name, from_date=from_date)

    def clear(self, skill_name: Optional[str] = None) -> int:
        """Clear analytics data.

        Args:
            skill_name: If provided, only clear data for this skill

        Returns:
            Number of records cleared
        """
        log_path = self._get_log_path()

        if not log_path.exists():
            return 0

        if skill_name is None:
            # Clear all
            with open(log_path, "r") as f:
                count = sum(1 for line in f if line.strip())
            log_path.write_text("")
            return count

        # Clear for specific skill
        records = self.get_records(limit=100000)
        kept = [r for r in records if r.skill_name != skill_name]
        cleared = len(records) - len(kept)

        # Rewrite file
        with open(log_path, "w") as f:
            for record in kept:
                f.write(record.to_json() + "\n")

        return cleared


# =============================================================================
# Global Tracker Instance
# =============================================================================

_tracker: Optional[UsageTracker] = None


def get_tracker() -> UsageTracker:
    """Get the global usage tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker


def set_tracker(tracker: UsageTracker) -> None:
    """Set the global usage tracker instance."""
    global _tracker
    _tracker = tracker


# =============================================================================
# Convenience Functions
# =============================================================================


def record_invocation(
    skill_name: str,
    status: InvocationStatus,
    latency_ms: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0,
    model: Optional[str] = None,
    platform: Optional[str] = None,
) -> InvocationRecord:
    """Record a skill invocation using the global tracker."""
    return get_tracker().record(
        skill_name=skill_name,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
        model=model,
        platform=platform,
    )


def record_success(
    skill_name: str,
    latency_ms: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0,
    **kwargs,
) -> InvocationRecord:
    """Record a successful invocation."""
    return record_invocation(
        skill_name=skill_name,
        status=InvocationStatus.SUCCESS,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
        **kwargs,
    )


def record_failure(
    skill_name: str,
    latency_ms: float = 0.0,
    **kwargs,
) -> InvocationRecord:
    """Record a failed invocation."""
    return record_invocation(
        skill_name=skill_name,
        status=InvocationStatus.FAILURE,
        latency_ms=latency_ms,
        **kwargs,
    )


def get_skill_metrics(
    skill_name: str,
    period_days: Optional[int] = None,
) -> SkillMetrics:
    """Get metrics for a skill using the global tracker."""
    tracker = get_tracker()
    if period_days:
        return tracker.get_period_metrics(skill_name, period_days)
    return tracker.get_metrics(skill_name)
