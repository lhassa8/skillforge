"""Analytics and usage tracking for SkillForge skills.

This module provides analytics features for tracking skill usage:

- Record invocations with metrics (latency, tokens, cost)
- Generate usage reports and statistics
- Calculate ROI and cost breakdowns
- Compare skill performance

Example usage:

    from skillforge.analytics import (
        # Tracking
        record_success,
        record_failure,
        get_skill_metrics,

        # Reports
        calculate_roi,
        generate_usage_report,
        generate_cost_breakdown,
        estimate_monthly_cost,
    )

    # Record a successful invocation
    record_success(
        skill_name="code-reviewer",
        latency_ms=1500,
        input_tokens=500,
        output_tokens=800,
        cost=0.02,
        model="claude-sonnet-4-20250514",
    )

    # Get metrics for a skill
    metrics = get_skill_metrics("code-reviewer", period_days=30)
    print(f"Success rate: {metrics.success_rate}%")
    print(f"Total cost: ${metrics.total_cost:.2f}")

    # Calculate ROI
    roi = calculate_roi("code-reviewer", period_days=30)
    print(f"ROI: {roi.roi_percentage}%")
    print(f"Net value: ${roi.net_value:.2f}")

    # Generate usage report
    report = generate_usage_report(period_days=7)
    print(f"Total invocations: {report.total_invocations}")
"""

from skillforge.analytics.tracker import (
    InvocationRecord,
    InvocationStatus,
    SkillMetrics,
    UsageTracker,
    ANALYTICS_DIR,
    ANALYTICS_LOG_FILE,
    get_analytics_dir,
    get_analytics_log_path,
    get_tracker,
    set_tracker,
    record_invocation,
    record_success,
    record_failure,
    get_skill_metrics,
)

from skillforge.analytics.reports import (
    ROIEstimate,
    UsageReport,
    CostBreakdown,
    DEFAULT_TIME_SAVED_MINUTES,
    DEFAULT_HOURLY_RATE,
    TOKEN_COSTS,
    calculate_roi,
    generate_usage_report,
    generate_cost_breakdown,
    estimate_monthly_cost,
    compare_skills,
)

__all__ = [
    # Tracker
    "InvocationRecord",
    "InvocationStatus",
    "SkillMetrics",
    "UsageTracker",
    "ANALYTICS_DIR",
    "ANALYTICS_LOG_FILE",
    "get_analytics_dir",
    "get_analytics_log_path",
    "get_tracker",
    "set_tracker",
    "record_invocation",
    "record_success",
    "record_failure",
    "get_skill_metrics",
    # Reports
    "ROIEstimate",
    "UsageReport",
    "CostBreakdown",
    "DEFAULT_TIME_SAVED_MINUTES",
    "DEFAULT_HOURLY_RATE",
    "TOKEN_COSTS",
    "calculate_roi",
    "generate_usage_report",
    "generate_cost_breakdown",
    "estimate_monthly_cost",
    "compare_skills",
]
