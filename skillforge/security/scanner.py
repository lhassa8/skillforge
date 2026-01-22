"""Security scanner for SkillForge skills.

This module provides functionality to scan skills for security vulnerabilities
and generate security reports.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from skillforge.skill import Skill, SkillParseError
from skillforge.security.patterns import (
    SECURITY_PATTERNS,
    SecurityFinding,
    SecurityIssueType,
    SecurityPattern,
    Severity,
)


class SecurityScanError(Exception):
    """Raised when security scanning fails."""

    pass


@dataclass
class ScanResult:
    """Result of scanning a skill for security issues.

    Attributes:
        skill_name: Name of the scanned skill
        skill_path: Path to the skill directory
        findings: List of security findings
        scanned_at: When the scan was performed
        scan_duration_ms: How long the scan took
        risk_score: Overall risk score (0-100)
        passed: Whether the skill passed security checks
    """

    skill_name: str
    skill_path: Optional[Path]
    findings: list[SecurityFinding] = field(default_factory=list)
    scanned_at: datetime = field(default_factory=datetime.now)
    scan_duration_ms: float = 0.0
    risk_score: int = 0
    passed: bool = True

    def __post_init__(self):
        """Calculate risk score and pass status after initialization."""
        self._calculate_risk_score()

    def _calculate_risk_score(self) -> None:
        """Calculate the overall risk score based on findings."""
        if not self.findings:
            self.risk_score = 0
            self.passed = True
            return

        # Severity weights
        weights = {
            Severity.CRITICAL: 40,
            Severity.HIGH: 25,
            Severity.MEDIUM: 15,
            Severity.LOW: 5,
            Severity.INFO: 1,
        }

        total_score = 0
        has_critical = False
        has_high = False

        for finding in self.findings:
            total_score += weights.get(finding.severity, 0)
            if finding.severity == Severity.CRITICAL:
                has_critical = True
            elif finding.severity == Severity.HIGH:
                has_high = True

        # Cap at 100
        self.risk_score = min(100, total_score)

        # Determine pass/fail
        # Fail if any critical issues or score >= 50
        self.passed = not has_critical and self.risk_score < 50

    @property
    def critical_count(self) -> int:
        """Count of critical severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        """Count of high severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        """Count of medium severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        """Count of low severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.LOW)

    @property
    def info_count(self) -> int:
        """Count of info severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.INFO)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "skill_name": self.skill_name,
            "skill_path": str(self.skill_path) if self.skill_path else None,
            "findings": [f.to_dict() for f in self.findings],
            "scanned_at": self.scanned_at.isoformat(),
            "scan_duration_ms": self.scan_duration_ms,
            "risk_score": self.risk_score,
            "passed": self.passed,
            "summary": {
                "total": len(self.findings),
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "info": self.info_count,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class SecurityScanner:
    """Scanner for detecting security issues in skills.

    Attributes:
        patterns: List of security patterns to check
        min_severity: Minimum severity level to report
        exclude_patterns: Pattern names to exclude
    """

    patterns: list[SecurityPattern] = field(default_factory=lambda: SECURITY_PATTERNS.copy())
    min_severity: Severity = Severity.INFO
    exclude_patterns: list[str] = field(default_factory=list)

    def scan_content(
        self,
        content: str,
        skill_name: str = "unknown",
        skill_path: Optional[Path] = None,
    ) -> ScanResult:
        """Scan content for security issues.

        Args:
            content: The content to scan
            skill_name: Name of the skill
            skill_path: Path to the skill

        Returns:
            ScanResult with all findings
        """
        import time

        start_time = time.time()
        findings: list[SecurityFinding] = []

        # Build line offset map for line number calculation
        line_offsets = self._build_line_offsets(content)

        # Severity order for filtering
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        min_severity_value = severity_order[self.min_severity]

        for pattern in self.patterns:
            # Skip excluded patterns
            if pattern.name in self.exclude_patterns:
                continue

            # Skip patterns below minimum severity
            if severity_order[pattern.severity] > min_severity_value:
                continue

            # Compile and search
            regex = pattern.compile()
            for match in regex.finditer(content):
                location = match.start()
                line_number = self._get_line_number(location, line_offsets)
                context = self._get_context(content, location)

                findings.append(
                    SecurityFinding(
                        pattern_name=pattern.name,
                        issue_type=pattern.issue_type,
                        severity=pattern.severity,
                        description=pattern.description,
                        recommendation=pattern.recommendation,
                        location=location,
                        matched_text=match.group(),
                        line_number=line_number,
                        context=context,
                    )
                )

        elapsed_ms = (time.time() - start_time) * 1000

        result = ScanResult(
            skill_name=skill_name,
            skill_path=skill_path,
            findings=findings,
            scan_duration_ms=elapsed_ms,
        )

        return result

    def scan_skill(self, skill: Skill, skill_path: Optional[Path] = None) -> ScanResult:
        """Scan a skill object for security issues.

        Args:
            skill: The skill to scan
            skill_path: Optional path to the skill

        Returns:
            ScanResult with all findings
        """
        # Combine all content to scan
        content_parts = [skill.content]

        # Include description
        if skill.description:
            content_parts.insert(0, skill.description)

        combined_content = "\n\n".join(content_parts)

        return self.scan_content(
            content=combined_content,
            skill_name=skill.name,
            skill_path=skill_path,
        )

    def scan_directory(self, skill_path: Path) -> ScanResult:
        """Scan a skill directory for security issues.

        Args:
            skill_path: Path to the skill directory

        Returns:
            ScanResult with all findings

        Raises:
            SecurityScanError: If skill cannot be loaded
        """
        skill_path = Path(skill_path)

        try:
            skill = Skill.from_directory(skill_path)
        except SkillParseError as e:
            raise SecurityScanError(f"Cannot load skill: {e}")

        # Scan the main skill
        result = self.scan_skill(skill, skill_path)

        # Also scan any reference files
        refs_dir = skill_path / "refs"
        if refs_dir.exists():
            for ref_file in refs_dir.glob("*.md"):
                ref_content = ref_file.read_text()
                ref_result = self.scan_content(
                    content=ref_content,
                    skill_name=f"{skill.name}:{ref_file.name}",
                )
                result.findings.extend(ref_result.findings)

        # Scan scripts directory
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.iterdir():
                if script_file.is_file():
                    try:
                        script_content = script_file.read_text()
                        script_result = self.scan_content(
                            content=script_content,
                            skill_name=f"{skill.name}:scripts/{script_file.name}",
                        )
                        result.findings.extend(script_result.findings)
                    except UnicodeDecodeError:
                        # Skip binary files
                        pass

        # Recalculate risk score with all findings
        result._calculate_risk_score()

        return result

    def _build_line_offsets(self, content: str) -> list[int]:
        """Build a list of character offsets for each line."""
        offsets = [0]
        for i, char in enumerate(content):
            if char == "\n":
                offsets.append(i + 1)
        return offsets

    def _get_line_number(self, offset: int, line_offsets: list[int]) -> int:
        """Get line number for a character offset."""
        for i, line_offset in enumerate(line_offsets):
            if offset < line_offset:
                return i
        return len(line_offsets)

    def _get_context(self, content: str, offset: int, context_chars: int = 50) -> str:
        """Get surrounding context for a finding."""
        start = max(0, offset - context_chars)
        end = min(len(content), offset + context_chars)

        context = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        # Replace newlines for single-line display
        context = context.replace("\n", " ")

        return context


# =============================================================================
# Convenience Functions
# =============================================================================


def scan_skill(
    skill_path: Path,
    min_severity: Severity = Severity.INFO,
    exclude_patterns: Optional[list[str]] = None,
) -> ScanResult:
    """Scan a skill directory for security issues.

    Args:
        skill_path: Path to the skill directory
        min_severity: Minimum severity to report
        exclude_patterns: Pattern names to exclude

    Returns:
        ScanResult with all findings
    """
    scanner = SecurityScanner(
        min_severity=min_severity,
        exclude_patterns=exclude_patterns or [],
    )
    return scanner.scan_directory(skill_path)


def scan_content(
    content: str,
    skill_name: str = "unknown",
    min_severity: Severity = Severity.INFO,
) -> ScanResult:
    """Scan content for security issues.

    Args:
        content: The content to scan
        skill_name: Name for the scan result
        min_severity: Minimum severity to report

    Returns:
        ScanResult with all findings
    """
    scanner = SecurityScanner(min_severity=min_severity)
    return scanner.scan_content(content, skill_name)


def quick_scan(skill_path: Path) -> bool:
    """Quickly check if a skill passes security scan.

    Args:
        skill_path: Path to the skill directory

    Returns:
        True if skill passes, False otherwise
    """
    result = scan_skill(skill_path, min_severity=Severity.MEDIUM)
    return result.passed


def get_risk_level(score: int) -> str:
    """Get a human-readable risk level from score.

    Args:
        score: Risk score (0-100)

    Returns:
        Risk level string
    """
    if score == 0:
        return "none"
    elif score < 20:
        return "low"
    elif score < 50:
        return "medium"
    elif score < 80:
        return "high"
    else:
        return "critical"
