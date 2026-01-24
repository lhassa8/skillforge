"""Analytics reports and ROI calculations for SkillForge skills.

This module provides functionality to generate analytics reports
and calculate return on investment for skills.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from skillforge.analytics.tracker import (
    SkillMetrics,
    UsageTracker,
    get_tracker,
)


@dataclass
class ROIEstimate:
    """ROI estimate for a skill.

    Attributes:
        skill_name: Name of the skill
        period_days: Period for the estimate
        total_invocations: Total invocations in period
        total_cost: Total API costs
        estimated_time_saved_hours: Estimated time saved
        estimated_value: Estimated value of time saved
        hourly_rate: Hourly rate used for calculation
        roi_percentage: Return on investment percentage
        net_value: Net value (value - cost)
    """

    skill_name: str
    period_days: int
    total_invocations: int
    total_cost: float
    estimated_time_saved_hours: float
    estimated_value: float
    hourly_rate: float
    roi_percentage: float
    net_value: float

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "skill_name": self.skill_name,
            "period_days": self.period_days,
            "total_invocations": self.total_invocations,
            "total_cost": round(self.total_cost, 2),
            "estimated_time_saved_hours": round(self.estimated_time_saved_hours, 2),
            "estimated_value": round(self.estimated_value, 2),
            "hourly_rate": self.hourly_rate,
            "roi_percentage": round(self.roi_percentage, 1),
            "net_value": round(self.net_value, 2),
        }


@dataclass
class UsageReport:
    """Usage report for skills.

    Attributes:
        generated_at: When the report was generated
        period_start: Start of the reporting period
        period_end: End of the reporting period
        total_invocations: Total invocations across all skills
        total_cost: Total cost across all skills
        total_tokens: Total tokens used
        skill_metrics: Metrics for each skill
        top_skills: Top skills by invocations
        status_breakdown: Invocations by status
    """

    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_invocations: int
    total_cost: float
    total_tokens: int
    skill_metrics: dict[str, SkillMetrics]
    top_skills: list[tuple[str, int]]
    status_breakdown: dict[str, int]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_invocations": self.total_invocations,
            "total_cost": round(self.total_cost, 2),
            "total_tokens": self.total_tokens,
            "skill_count": len(self.skill_metrics),
            "skill_metrics": {
                name: metrics.to_dict()
                for name, metrics in self.skill_metrics.items()
            },
            "top_skills": [
                {"name": name, "invocations": count}
                for name, count in self.top_skills
            ],
            "status_breakdown": self.status_breakdown,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class CostBreakdown:
    """Cost breakdown for a skill or period.

    Attributes:
        total_cost: Total cost
        input_cost: Cost for input tokens
        output_cost: Cost for output tokens
        cost_by_model: Cost breakdown by model
        cost_by_day: Cost breakdown by day
        avg_cost_per_invocation: Average cost per invocation
    """

    total_cost: float
    input_cost: float
    output_cost: float
    cost_by_model: dict[str, float]
    cost_by_day: dict[str, float]
    avg_cost_per_invocation: float

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "total_cost": round(self.total_cost, 4),
            "input_cost": round(self.input_cost, 4),
            "output_cost": round(self.output_cost, 4),
            "cost_by_model": {k: round(v, 4) for k, v in self.cost_by_model.items()},
            "cost_by_day": {k: round(v, 4) for k, v in self.cost_by_day.items()},
            "avg_cost_per_invocation": round(self.avg_cost_per_invocation, 4),
        }


# =============================================================================
# Default Estimation Parameters
# =============================================================================

# Default time saved per invocation (in minutes)
DEFAULT_TIME_SAVED_MINUTES = 5

# Default hourly rate for ROI calculation (USD)
DEFAULT_HOURLY_RATE = 50.0

# Token cost estimates (USD per 1K tokens)
TOKEN_COSTS = {
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-opus-4": {"input": 0.015, "output": 0.075},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "default": {"input": 0.003, "output": 0.015},
}


# =============================================================================
# Report Generation
# =============================================================================


def calculate_roi(
    skill_name: str,
    period_days: int = 30,
    time_saved_minutes: float = DEFAULT_TIME_SAVED_MINUTES,
    hourly_rate: float = DEFAULT_HOURLY_RATE,
    tracker: Optional[UsageTracker] = None,
) -> ROIEstimate:
    """Calculate ROI estimate for a skill.

    Args:
        skill_name: Name of the skill
        period_days: Number of days to analyze
        time_saved_minutes: Estimated minutes saved per invocation
        hourly_rate: Hourly rate for value calculation (USD)
        tracker: Usage tracker instance (uses global if not provided)

    Returns:
        ROIEstimate with calculated values
    """
    if tracker is None:
        tracker = get_tracker()

    metrics = tracker.get_period_metrics(skill_name, period_days)

    # Calculate time saved
    time_saved_hours = (metrics.total_invocations * time_saved_minutes) / 60

    # Calculate value of time saved
    estimated_value = time_saved_hours * hourly_rate

    # Calculate ROI
    if metrics.total_cost > 0:
        roi_percentage = ((estimated_value - metrics.total_cost) / metrics.total_cost) * 100
    else:
        roi_percentage = float("inf") if estimated_value > 0 else 0.0

    # Calculate net value
    net_value = estimated_value - metrics.total_cost

    return ROIEstimate(
        skill_name=skill_name,
        period_days=period_days,
        total_invocations=metrics.total_invocations,
        total_cost=metrics.total_cost,
        estimated_time_saved_hours=time_saved_hours,
        estimated_value=estimated_value,
        hourly_rate=hourly_rate,
        roi_percentage=roi_percentage,
        net_value=net_value,
    )


def generate_usage_report(
    period_days: int = 30,
    tracker: Optional[UsageTracker] = None,
) -> UsageReport:
    """Generate a usage report for all skills.

    Args:
        period_days: Number of days to include
        tracker: Usage tracker instance (uses global if not provided)

    Returns:
        UsageReport with aggregated data
    """
    if tracker is None:
        tracker = get_tracker()

    now = datetime.now()
    from_date = now - timedelta(days=period_days)

    # Get all metrics
    all_metrics = tracker.get_all_metrics(from_date=from_date)

    # Calculate totals
    total_invocations = sum(m.total_invocations for m in all_metrics.values())
    total_cost = sum(m.total_cost for m in all_metrics.values())
    total_tokens = sum(m.total_tokens for m in all_metrics.values())

    # Get top skills
    top_skills = sorted(
        [(name, m.total_invocations) for name, m in all_metrics.items()],
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    # Calculate status breakdown
    records = tracker.get_records(from_date=from_date, limit=100000)
    status_breakdown = {}
    for record in records:
        status = record.status.value
        status_breakdown[status] = status_breakdown.get(status, 0) + 1

    return UsageReport(
        generated_at=now,
        period_start=from_date,
        period_end=now,
        total_invocations=total_invocations,
        total_cost=total_cost,
        total_tokens=total_tokens,
        skill_metrics=all_metrics,
        top_skills=top_skills,
        status_breakdown=status_breakdown,
    )


def generate_cost_breakdown(
    skill_name: Optional[str] = None,
    period_days: int = 30,
    tracker: Optional[UsageTracker] = None,
) -> CostBreakdown:
    """Generate a cost breakdown for a skill or all skills.

    Args:
        skill_name: Name of skill (None for all skills)
        period_days: Number of days to include
        tracker: Usage tracker instance (uses global if not provided)

    Returns:
        CostBreakdown with detailed cost analysis
    """
    if tracker is None:
        tracker = get_tracker()

    from_date = datetime.now() - timedelta(days=period_days)

    records = tracker.get_records(
        skill_name=skill_name,
        from_date=from_date,
        limit=100000,
    )

    # Aggregate costs
    total_cost = 0.0
    input_cost = 0.0
    output_cost = 0.0
    cost_by_model: dict[str, float] = {}
    cost_by_day: dict[str, float] = {}

    for record in records:
        total_cost += record.cost

        # Estimate input/output split based on tokens
        model = record.model or "default"
        costs = TOKEN_COSTS.get(model, TOKEN_COSTS["default"])

        input_token_cost = (record.input_tokens / 1000) * costs["input"]
        output_token_cost = (record.output_tokens / 1000) * costs["output"]

        input_cost += input_token_cost
        output_cost += output_token_cost

        # By model
        cost_by_model[model] = cost_by_model.get(model, 0.0) + record.cost

        # By day
        day_key = record.timestamp.strftime("%Y-%m-%d")
        cost_by_day[day_key] = cost_by_day.get(day_key, 0.0) + record.cost

    # Calculate average
    avg_cost = total_cost / len(records) if records else 0.0

    return CostBreakdown(
        total_cost=total_cost,
        input_cost=input_cost,
        output_cost=output_cost,
        cost_by_model=cost_by_model,
        cost_by_day=dict(sorted(cost_by_day.items())),
        avg_cost_per_invocation=avg_cost,
    )


def estimate_monthly_cost(
    skill_name: str,
    expected_daily_invocations: int,
    avg_input_tokens: int = 1000,
    avg_output_tokens: int = 500,
    model: str = "default",
) -> dict[str, float]:
    """Estimate monthly cost for a skill.

    Args:
        skill_name: Name of the skill
        expected_daily_invocations: Expected invocations per day
        avg_input_tokens: Average input tokens per invocation
        avg_output_tokens: Average output tokens per invocation
        model: Model to use for cost estimation

    Returns:
        Dictionary with cost estimates
    """
    costs = TOKEN_COSTS.get(model, TOKEN_COSTS["default"])

    # Per invocation cost
    input_cost = (avg_input_tokens / 1000) * costs["input"]
    output_cost = (avg_output_tokens / 1000) * costs["output"]
    per_invocation = input_cost + output_cost

    # Projections
    daily_cost = per_invocation * expected_daily_invocations
    weekly_cost = daily_cost * 7
    monthly_cost = daily_cost * 30

    return {
        "skill_name": skill_name,
        "model": model,
        "per_invocation": round(per_invocation, 4),
        "daily_cost": round(daily_cost, 2),
        "weekly_cost": round(weekly_cost, 2),
        "monthly_cost": round(monthly_cost, 2),
        "expected_daily_invocations": expected_daily_invocations,
        "avg_input_tokens": avg_input_tokens,
        "avg_output_tokens": avg_output_tokens,
    }


def compare_skills(
    skill_names: list[str],
    period_days: int = 30,
    tracker: Optional[UsageTracker] = None,
) -> list[dict]:
    """Compare metrics across multiple skills.

    Args:
        skill_names: List of skill names to compare
        period_days: Number of days to analyze
        tracker: Usage tracker instance (uses global if not provided)

    Returns:
        List of skill comparisons sorted by invocations
    """
    if tracker is None:
        tracker = get_tracker()

    comparisons = []
    for name in skill_names:
        metrics = tracker.get_period_metrics(name, period_days)
        roi = calculate_roi(name, period_days, tracker=tracker)

        comparisons.append({
            "skill_name": name,
            "total_invocations": metrics.total_invocations,
            "success_rate": round(metrics.success_rate, 1),
            "avg_latency_ms": round(metrics.avg_latency_ms, 1),
            "total_cost": round(metrics.total_cost, 2),
            "total_tokens": metrics.total_tokens,
            "roi_percentage": round(roi.roi_percentage, 1) if roi.roi_percentage != float("inf") else "∞",
            "net_value": round(roi.net_value, 2),
        })

    # Sort by invocations
    comparisons.sort(key=lambda x: x["total_invocations"], reverse=True)

    return comparisons
