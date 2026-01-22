"""Security scanning for SkillForge skills.

This module provides security scanning and vulnerability detection for skills:

- Scan skills for security vulnerabilities
- Detect prompt injection, credential exposure, data exfiltration
- Generate security reports
- Calculate risk scores

Example usage:

    from skillforge.security import (
        scan_skill,
        scan_content,
        quick_scan,
        SecurityScanner,
        ScanResult,
        Severity,
    )

    # Quick pass/fail check
    if quick_scan("./skills/my-skill"):
        print("Skill passed security scan")

    # Full scan with details
    result = scan_skill("./skills/my-skill")
    print(f"Risk score: {result.risk_score}")
    for finding in result.findings:
        print(f"  {finding.severity.value}: {finding.description}")

    # Scan raw content
    result = scan_content("Some skill content to check")
"""

from skillforge.security.patterns import (
    SecurityFinding,
    SecurityIssueType,
    SecurityPattern,
    Severity,
    SECURITY_PATTERNS,
    get_pattern_by_name,
    get_patterns_by_severity,
    get_patterns_by_type,
)

from skillforge.security.scanner import (
    ScanResult,
    SecurityScanner,
    SecurityScanError,
    get_risk_level,
    quick_scan,
    scan_content,
    scan_skill,
)

__all__ = [
    # Patterns
    "SecurityFinding",
    "SecurityIssueType",
    "SecurityPattern",
    "Severity",
    "SECURITY_PATTERNS",
    "get_pattern_by_name",
    "get_patterns_by_severity",
    "get_patterns_by_type",
    # Scanner
    "ScanResult",
    "SecurityScanner",
    "SecurityScanError",
    "get_risk_level",
    "quick_scan",
    "scan_content",
    "scan_skill",
]
