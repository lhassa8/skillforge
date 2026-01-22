"""Tests for skillforge.analytics module."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillforge.analytics import (
    # Tracker
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
    # Reports
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


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_analytics_dir(tmp_path: Path):
    """Create a temporary analytics directory."""
    analytics_dir = tmp_path / "analytics"
    analytics_dir.mkdir()
    return analytics_dir


@pytest.fixture
def tracker(temp_analytics_dir: Path):
    """Create a tracker with temporary directory."""
    return UsageTracker(analytics_dir=temp_analytics_dir)


@pytest.fixture
def tracker_with_data(tracker: UsageTracker):
    """Create a tracker with sample data."""
    # Record some successful invocations
    for i in range(5):
        tracker.record(
            skill_name="code-reviewer",
            status=InvocationStatus.SUCCESS,
            latency_ms=1000 + i * 100,
            input_tokens=500 + i * 50,
            output_tokens=800 + i * 100,
            cost=0.02 + i * 0.005,
            model="claude-sonnet-4-20250514",
        )

    # Record some failures
    for i in range(2):
        tracker.record(
            skill_name="code-reviewer",
            status=InvocationStatus.FAILURE,
            latency_ms=500,
        )

    # Record for another skill
    for i in range(3):
        tracker.record(
            skill_name="doc-generator",
            status=InvocationStatus.SUCCESS,
            latency_ms=2000,
            input_tokens=1000,
            output_tokens=2000,
            cost=0.05,
            model="claude-opus-4",
        )

    return tracker


# =============================================================================
# InvocationStatus Tests
# =============================================================================


class TestInvocationStatus:
    """Tests for InvocationStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert InvocationStatus.SUCCESS.value == "success"
        assert InvocationStatus.FAILURE.value == "failure"
        assert InvocationStatus.TIMEOUT.value == "timeout"
        assert InvocationStatus.ERROR.value == "error"


# =============================================================================
# InvocationRecord Tests
# =============================================================================


class TestInvocationRecord:
    """Tests for InvocationRecord dataclass."""

    def test_record_creation(self):
        """Test creating an invocation record."""
        record = InvocationRecord(
            skill_name="test-skill",
            timestamp=datetime.now(),
            status=InvocationStatus.SUCCESS,
            latency_ms=1500,
            input_tokens=500,
            output_tokens=800,
            cost=0.02,
            model="claude-sonnet-4-20250514",
            platform="claude-code",
        )

        assert record.skill_name == "test-skill"
        assert record.status == InvocationStatus.SUCCESS
        assert record.latency_ms == 1500
        assert record.input_tokens == 500
        assert record.output_tokens == 800
        assert record.cost == 0.02

    def test_record_defaults(self):
        """Test record with default values."""
        record = InvocationRecord(
            skill_name="test-skill",
            timestamp=datetime.now(),
            status=InvocationStatus.SUCCESS,
        )

        assert record.latency_ms == 0.0
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.cost == 0.0
        assert record.model is None
        assert record.platform is None
        assert record.metadata == {}

    def test_to_dict(self):
        """Test converting record to dictionary."""
        now = datetime.now()
        record = InvocationRecord(
            skill_name="test-skill",
            timestamp=now,
            status=InvocationStatus.SUCCESS,
            latency_ms=1500,
            cost=0.02,
        )

        data = record.to_dict()

        assert data["skill_name"] == "test-skill"
        assert data["timestamp"] == now.isoformat()
        assert data["status"] == "success"
        assert data["latency_ms"] == 1500
        assert data["cost"] == 0.02

    def test_from_dict(self):
        """Test creating record from dictionary."""
        now = datetime.now()
        data = {
            "skill_name": "test-skill",
            "timestamp": now.isoformat(),
            "status": "success",
            "latency_ms": 1500,
            "input_tokens": 500,
            "output_tokens": 800,
            "cost": 0.02,
            "model": "claude-sonnet-4-20250514",
        }

        record = InvocationRecord.from_dict(data)

        assert record.skill_name == "test-skill"
        assert record.status == InvocationStatus.SUCCESS
        assert record.latency_ms == 1500

    def test_to_json(self):
        """Test converting record to JSON."""
        record = InvocationRecord(
            skill_name="test-skill",
            timestamp=datetime.now(),
            status=InvocationStatus.SUCCESS,
        )

        json_str = record.to_json()
        data = json.loads(json_str)

        assert data["skill_name"] == "test-skill"
        assert data["status"] == "success"


# =============================================================================
# SkillMetrics Tests
# =============================================================================


class TestSkillMetrics:
    """Tests for SkillMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating skill metrics."""
        metrics = SkillMetrics(skill_name="test-skill")

        assert metrics.skill_name == "test-skill"
        assert metrics.total_invocations == 0
        assert metrics.successful_invocations == 0
        assert metrics.failed_invocations == 0

    def test_add_invocation_success(self):
        """Test adding successful invocation."""
        metrics = SkillMetrics(skill_name="test-skill")
        record = InvocationRecord(
            skill_name="test-skill",
            timestamp=datetime.now(),
            status=InvocationStatus.SUCCESS,
            latency_ms=1000,
            input_tokens=500,
            output_tokens=800,
            cost=0.02,
        )

        metrics.add_invocation(record)

        assert metrics.total_invocations == 1
        assert metrics.successful_invocations == 1
        assert metrics.failed_invocations == 0
        assert metrics.total_latency_ms == 1000
        assert metrics.total_cost == 0.02

    def test_add_invocation_failure(self):
        """Test adding failed invocation."""
        metrics = SkillMetrics(skill_name="test-skill")
        record = InvocationRecord(
            skill_name="test-skill",
            timestamp=datetime.now(),
            status=InvocationStatus.FAILURE,
            latency_ms=500,
        )

        metrics.add_invocation(record)

        assert metrics.total_invocations == 1
        assert metrics.successful_invocations == 0
        assert metrics.failed_invocations == 1

    def test_success_rate(self):
        """Test success rate calculation."""
        metrics = SkillMetrics(
            skill_name="test-skill",
            total_invocations=10,
            successful_invocations=8,
            failed_invocations=2,
        )

        assert metrics.success_rate == 80.0

    def test_success_rate_zero_invocations(self):
        """Test success rate with no invocations."""
        metrics = SkillMetrics(skill_name="test-skill")

        assert metrics.success_rate == 0.0

    def test_avg_latency(self):
        """Test average latency calculation."""
        metrics = SkillMetrics(
            skill_name="test-skill",
            total_invocations=5,
            total_latency_ms=5000,
        )

        assert metrics.avg_latency_ms == 1000.0

    def test_avg_cost(self):
        """Test average cost calculation."""
        metrics = SkillMetrics(
            skill_name="test-skill",
            total_invocations=10,
            total_cost=0.50,
        )

        assert metrics.avg_cost == 0.05

    def test_total_tokens(self):
        """Test total tokens calculation."""
        metrics = SkillMetrics(
            skill_name="test-skill",
            total_input_tokens=5000,
            total_output_tokens=8000,
        )

        assert metrics.total_tokens == 13000

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        now = datetime.now()
        metrics = SkillMetrics(
            skill_name="test-skill",
            total_invocations=10,
            successful_invocations=8,
            failed_invocations=2,
            total_cost=0.50,
            first_invocation=now,
            last_invocation=now,
        )

        data = metrics.to_dict()

        assert data["skill_name"] == "test-skill"
        assert data["total_invocations"] == 10
        assert data["success_rate"] == 80.0
        assert data["total_cost"] == 0.50


# =============================================================================
# UsageTracker Tests
# =============================================================================


class TestUsageTracker:
    """Tests for UsageTracker class."""

    def test_tracker_creation(self, temp_analytics_dir: Path):
        """Test creating a tracker."""
        tracker = UsageTracker(analytics_dir=temp_analytics_dir)

        assert tracker.analytics_dir == temp_analytics_dir
        assert tracker.enabled is True

    def test_tracker_disabled(self, temp_analytics_dir: Path):
        """Test creating a disabled tracker."""
        tracker = UsageTracker(analytics_dir=temp_analytics_dir, enabled=False)

        assert tracker.enabled is False

    def test_record_invocation(self, tracker: UsageTracker):
        """Test recording an invocation."""
        record = tracker.record(
            skill_name="test-skill",
            status=InvocationStatus.SUCCESS,
            latency_ms=1500,
            input_tokens=500,
            output_tokens=800,
            cost=0.02,
            model="claude-sonnet-4-20250514",
        )

        assert isinstance(record, InvocationRecord)
        assert record.skill_name == "test-skill"
        assert record.status == InvocationStatus.SUCCESS

    def test_record_disabled(self, temp_analytics_dir: Path):
        """Test recording when disabled doesn't write file."""
        tracker = UsageTracker(analytics_dir=temp_analytics_dir, enabled=False)

        tracker.record(
            skill_name="test-skill",
            status=InvocationStatus.SUCCESS,
        )

        log_path = temp_analytics_dir / ANALYTICS_LOG_FILE
        assert not log_path.exists()

    def test_get_records(self, tracker_with_data: UsageTracker):
        """Test getting records."""
        records = tracker_with_data.get_records()

        assert len(records) > 0
        assert all(isinstance(r, InvocationRecord) for r in records)

    def test_get_records_by_skill(self, tracker_with_data: UsageTracker):
        """Test getting records filtered by skill."""
        records = tracker_with_data.get_records(skill_name="code-reviewer")

        assert len(records) == 7  # 5 success + 2 failure
        assert all(r.skill_name == "code-reviewer" for r in records)

    def test_get_records_by_status(self, tracker_with_data: UsageTracker):
        """Test getting records filtered by status."""
        records = tracker_with_data.get_records(status=InvocationStatus.SUCCESS)

        assert len(records) == 8  # 5 code-reviewer + 3 doc-generator
        assert all(r.status == InvocationStatus.SUCCESS for r in records)

    def test_get_records_by_date(self, tracker_with_data: UsageTracker):
        """Test getting records filtered by date."""
        from_date = datetime.now() - timedelta(days=1)
        records = tracker_with_data.get_records(from_date=from_date)

        assert len(records) > 0

    def test_get_records_limit(self, tracker_with_data: UsageTracker):
        """Test limiting records."""
        records = tracker_with_data.get_records(limit=3)

        assert len(records) == 3

    def test_get_metrics(self, tracker_with_data: UsageTracker):
        """Test getting metrics for a skill."""
        metrics = tracker_with_data.get_metrics("code-reviewer")

        assert metrics.skill_name == "code-reviewer"
        assert metrics.total_invocations == 7
        assert metrics.successful_invocations == 5
        assert metrics.failed_invocations == 2

    def test_get_all_metrics(self, tracker_with_data: UsageTracker):
        """Test getting metrics for all skills."""
        all_metrics = tracker_with_data.get_all_metrics()

        assert "code-reviewer" in all_metrics
        assert "doc-generator" in all_metrics
        assert all_metrics["code-reviewer"].total_invocations == 7
        assert all_metrics["doc-generator"].total_invocations == 3

    def test_get_period_metrics(self, tracker_with_data: UsageTracker):
        """Test getting metrics for a period."""
        metrics = tracker_with_data.get_period_metrics("code-reviewer", period_days=30)

        assert metrics.skill_name == "code-reviewer"
        assert metrics.total_invocations == 7

    def test_clear_all(self, tracker_with_data: UsageTracker):
        """Test clearing all data."""
        cleared = tracker_with_data.clear()

        assert cleared == 10  # Total records
        records = tracker_with_data.get_records()
        assert len(records) == 0

    def test_clear_by_skill(self, tracker_with_data: UsageTracker):
        """Test clearing data for specific skill."""
        cleared = tracker_with_data.clear(skill_name="code-reviewer")

        assert cleared == 7
        records = tracker_with_data.get_records()
        assert len(records) == 3  # Only doc-generator records remain


# =============================================================================
# Global Tracker Tests
# =============================================================================


class TestGlobalTracker:
    """Tests for global tracker functions."""

    def test_get_tracker(self):
        """Test getting global tracker."""
        tracker = get_tracker()
        assert isinstance(tracker, UsageTracker)

    def test_set_tracker(self, temp_analytics_dir: Path):
        """Test setting global tracker."""
        custom_tracker = UsageTracker(analytics_dir=temp_analytics_dir)
        set_tracker(custom_tracker)

        assert get_tracker() is custom_tracker

        # Reset to default
        set_tracker(None)


# =============================================================================
# Convenience Functions Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_record_success(self, temp_analytics_dir: Path):
        """Test record_success function."""
        tracker = UsageTracker(analytics_dir=temp_analytics_dir)
        set_tracker(tracker)

        record = record_success(
            skill_name="test-skill",
            latency_ms=1500,
            input_tokens=500,
            output_tokens=800,
            cost=0.02,
        )

        assert record.status == InvocationStatus.SUCCESS
        assert record.skill_name == "test-skill"

        set_tracker(None)

    def test_record_failure(self, temp_analytics_dir: Path):
        """Test record_failure function."""
        tracker = UsageTracker(analytics_dir=temp_analytics_dir)
        set_tracker(tracker)

        record = record_failure(
            skill_name="test-skill",
            latency_ms=500,
        )

        assert record.status == InvocationStatus.FAILURE

        set_tracker(None)

    def test_get_skill_metrics(self, temp_analytics_dir: Path):
        """Test get_skill_metrics function."""
        tracker = UsageTracker(analytics_dir=temp_analytics_dir)
        set_tracker(tracker)

        tracker.record(
            skill_name="test-skill",
            status=InvocationStatus.SUCCESS,
            latency_ms=1000,
            cost=0.02,
        )

        metrics = get_skill_metrics("test-skill")

        assert metrics.skill_name == "test-skill"
        assert metrics.total_invocations == 1

        set_tracker(None)


# =============================================================================
# ROI Estimate Tests
# =============================================================================


class TestROIEstimate:
    """Tests for ROIEstimate dataclass."""

    def test_roi_estimate_creation(self):
        """Test creating ROI estimate."""
        roi = ROIEstimate(
            skill_name="test-skill",
            period_days=30,
            total_invocations=100,
            total_cost=5.0,
            estimated_time_saved_hours=8.33,
            estimated_value=416.5,
            hourly_rate=50.0,
            roi_percentage=8230.0,
            net_value=411.5,
        )

        assert roi.skill_name == "test-skill"
        assert roi.roi_percentage == 8230.0
        assert roi.net_value == 411.5

    def test_to_dict(self):
        """Test converting to dictionary."""
        roi = ROIEstimate(
            skill_name="test-skill",
            period_days=30,
            total_invocations=100,
            total_cost=5.0,
            estimated_time_saved_hours=8.333333,
            estimated_value=416.66666,
            hourly_rate=50.0,
            roi_percentage=8230.12345,
            net_value=411.66666,
        )

        data = roi.to_dict()

        assert data["skill_name"] == "test-skill"
        # Values should be rounded
        assert data["estimated_time_saved_hours"] == 8.33
        assert data["roi_percentage"] == 8230.1
        assert data["net_value"] == 411.67


# =============================================================================
# Calculate ROI Tests
# =============================================================================


class TestCalculateROI:
    """Tests for calculate_roi function."""

    def test_calculate_roi(self, tracker_with_data: UsageTracker):
        """Test ROI calculation."""
        roi = calculate_roi(
            skill_name="code-reviewer",
            period_days=30,
            tracker=tracker_with_data,
        )

        assert isinstance(roi, ROIEstimate)
        assert roi.skill_name == "code-reviewer"
        assert roi.total_invocations == 7
        assert roi.total_cost > 0
        assert roi.net_value > 0

    def test_calculate_roi_custom_params(self, tracker_with_data: UsageTracker):
        """Test ROI with custom parameters."""
        roi = calculate_roi(
            skill_name="code-reviewer",
            period_days=30,
            time_saved_minutes=10,
            hourly_rate=100.0,
            tracker=tracker_with_data,
        )

        assert roi.hourly_rate == 100.0
        # 7 invocations * 10 minutes / 60 = 1.166 hours
        assert roi.estimated_time_saved_hours == pytest.approx(7 * 10 / 60, rel=0.01)

    def test_calculate_roi_zero_cost(self, temp_analytics_dir: Path):
        """Test ROI with zero cost returns infinity."""
        tracker = UsageTracker(analytics_dir=temp_analytics_dir)
        tracker.record(
            skill_name="free-skill",
            status=InvocationStatus.SUCCESS,
            latency_ms=1000,
            cost=0.0,
        )

        roi = calculate_roi("free-skill", tracker=tracker)

        assert roi.roi_percentage == float("inf")


# =============================================================================
# Usage Report Tests
# =============================================================================


class TestUsageReport:
    """Tests for UsageReport dataclass."""

    def test_generate_usage_report(self, tracker_with_data: UsageTracker):
        """Test generating usage report."""
        report = generate_usage_report(period_days=30, tracker=tracker_with_data)

        assert isinstance(report, UsageReport)
        assert report.total_invocations == 10
        assert len(report.skill_metrics) == 2
        assert len(report.top_skills) <= 10

    def test_report_to_dict(self, tracker_with_data: UsageTracker):
        """Test converting report to dictionary."""
        report = generate_usage_report(period_days=30, tracker=tracker_with_data)
        data = report.to_dict()

        assert "generated_at" in data
        assert "total_invocations" in data
        assert "skill_metrics" in data
        assert "top_skills" in data
        assert "status_breakdown" in data

    def test_report_to_json(self, tracker_with_data: UsageTracker):
        """Test converting report to JSON."""
        report = generate_usage_report(period_days=30, tracker=tracker_with_data)
        json_str = report.to_json()

        data = json.loads(json_str)
        assert data["total_invocations"] == 10


# =============================================================================
# Cost Breakdown Tests
# =============================================================================


class TestCostBreakdown:
    """Tests for CostBreakdown dataclass."""

    def test_generate_cost_breakdown(self, tracker_with_data: UsageTracker):
        """Test generating cost breakdown."""
        breakdown = generate_cost_breakdown(
            skill_name="code-reviewer",
            period_days=30,
            tracker=tracker_with_data,
        )

        assert isinstance(breakdown, CostBreakdown)
        assert breakdown.total_cost > 0
        assert breakdown.avg_cost_per_invocation > 0

    def test_cost_breakdown_all_skills(self, tracker_with_data: UsageTracker):
        """Test cost breakdown for all skills."""
        breakdown = generate_cost_breakdown(period_days=30, tracker=tracker_with_data)

        assert breakdown.total_cost > 0
        assert len(breakdown.cost_by_model) > 0

    def test_cost_breakdown_to_dict(self, tracker_with_data: UsageTracker):
        """Test converting breakdown to dictionary."""
        breakdown = generate_cost_breakdown(period_days=30, tracker=tracker_with_data)
        data = breakdown.to_dict()

        assert "total_cost" in data
        assert "input_cost" in data
        assert "output_cost" in data
        assert "cost_by_model" in data
        assert "cost_by_day" in data


# =============================================================================
# Monthly Cost Estimate Tests
# =============================================================================


class TestEstimateMonthlyCost:
    """Tests for estimate_monthly_cost function."""

    def test_estimate_monthly_cost(self):
        """Test monthly cost estimation."""
        estimate = estimate_monthly_cost(
            skill_name="test-skill",
            expected_daily_invocations=10,
            avg_input_tokens=1000,
            avg_output_tokens=500,
            model="claude-sonnet-4-20250514",
        )

        assert estimate["skill_name"] == "test-skill"
        assert estimate["expected_daily_invocations"] == 10
        assert estimate["daily_cost"] > 0
        assert estimate["monthly_cost"] > estimate["daily_cost"]

    def test_estimate_default_model(self):
        """Test estimation with default model."""
        estimate = estimate_monthly_cost(
            skill_name="test-skill",
            expected_daily_invocations=10,
        )

        assert estimate["model"] == "default"


# =============================================================================
# Compare Skills Tests
# =============================================================================


class TestCompareSkills:
    """Tests for compare_skills function."""

    def test_compare_skills(self, tracker_with_data: UsageTracker):
        """Test comparing multiple skills."""
        comparisons = compare_skills(
            skill_names=["code-reviewer", "doc-generator"],
            period_days=30,
            tracker=tracker_with_data,
        )

        assert len(comparisons) == 2
        # Should be sorted by invocations (descending)
        assert comparisons[0]["total_invocations"] >= comparisons[1]["total_invocations"]

    def test_comparison_fields(self, tracker_with_data: UsageTracker):
        """Test comparison has expected fields."""
        comparisons = compare_skills(
            skill_names=["code-reviewer"],
            period_days=30,
            tracker=tracker_with_data,
        )

        comparison = comparisons[0]
        assert "skill_name" in comparison
        assert "total_invocations" in comparison
        assert "success_rate" in comparison
        assert "avg_latency_ms" in comparison
        assert "total_cost" in comparison
        assert "roi_percentage" in comparison
        assert "net_value" in comparison


# =============================================================================
# Token Costs Tests
# =============================================================================


class TestTokenCosts:
    """Tests for token cost constants."""

    def test_token_costs_exist(self):
        """Test TOKEN_COSTS dictionary exists with models."""
        assert "claude-sonnet-4-20250514" in TOKEN_COSTS
        assert "claude-opus-4" in TOKEN_COSTS
        assert "gpt-4o" in TOKEN_COSTS
        assert "default" in TOKEN_COSTS

    def test_token_costs_structure(self):
        """Test token cost structure."""
        for model, costs in TOKEN_COSTS.items():
            assert "input" in costs
            assert "output" in costs
            assert isinstance(costs["input"], (int, float))
            assert isinstance(costs["output"], (int, float))


# =============================================================================
# Default Constants Tests
# =============================================================================


class TestDefaultConstants:
    """Tests for default constants."""

    def test_default_time_saved(self):
        """Test default time saved constant."""
        assert DEFAULT_TIME_SAVED_MINUTES == 5

    def test_default_hourly_rate(self):
        """Test default hourly rate constant."""
        assert DEFAULT_HOURLY_RATE == 50.0
