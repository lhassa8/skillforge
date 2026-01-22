"""Security vulnerability patterns for skill scanning.

This module defines patterns used to detect potential security issues
in skill content including prompt injection, data exfiltration,
credential exposure, and other vulnerabilities.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SecurityIssueType(Enum):
    """Types of security issues that can be detected."""

    # Prompt injection patterns
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    INSTRUCTION_OVERRIDE = "instruction_override"

    # Data security
    DATA_EXFILTRATION = "data_exfiltration"
    SENSITIVE_DATA_LOGGING = "sensitive_data_logging"
    UNAUTHORIZED_ACCESS = "unauthorized_access"

    # Credential exposure
    CREDENTIAL_EXPOSURE = "credential_exposure"
    HARDCODED_SECRET = "hardcoded_secret"
    API_KEY_EXPOSURE = "api_key_exposure"

    # Code execution
    UNSAFE_CODE_EXECUTION = "unsafe_code_execution"
    SHELL_INJECTION = "shell_injection"
    COMMAND_INJECTION = "command_injection"

    # File system
    PATH_TRAVERSAL = "path_traversal"
    UNSAFE_FILE_ACCESS = "unsafe_file_access"

    # Network
    UNSAFE_URL = "unsafe_url"
    SSRF_RISK = "ssrf_risk"

    # Other
    PRIVILEGE_ESCALATION = "privilege_escalation"
    INFORMATION_DISCLOSURE = "information_disclosure"


class Severity(Enum):
    """Severity levels for security issues."""

    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Serious vulnerability
    MEDIUM = "medium"  # Moderate risk
    LOW = "low"  # Minor concern
    INFO = "info"  # Informational only


@dataclass
class SecurityPattern:
    """A pattern for detecting security issues.

    Attributes:
        name: Pattern identifier
        issue_type: Type of security issue
        severity: How serious the issue is
        pattern: Regex pattern to match
        description: Human-readable description
        recommendation: How to fix the issue
        false_positive_hint: When this might be a false positive
    """

    name: str
    issue_type: SecurityIssueType
    severity: Severity
    pattern: str
    description: str
    recommendation: str
    false_positive_hint: Optional[str] = None
    case_sensitive: bool = False

    def compile(self) -> re.Pattern:
        """Compile the regex pattern."""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        return re.compile(self.pattern, flags | re.MULTILINE)


@dataclass
class SecurityFinding:
    """A security issue found during scanning.

    Attributes:
        pattern_name: Name of the pattern that matched
        issue_type: Type of security issue
        severity: Severity level
        description: Description of the issue
        recommendation: How to fix it
        location: Where in the content the issue was found
        matched_text: The text that matched
        line_number: Line number if available
        context: Surrounding context
    """

    pattern_name: str
    issue_type: SecurityIssueType
    severity: Severity
    description: str
    recommendation: str
    location: int  # Character offset
    matched_text: str
    line_number: Optional[int] = None
    context: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "pattern_name": self.pattern_name,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "recommendation": self.recommendation,
            "location": self.location,
            "matched_text": self.matched_text,
            "line_number": self.line_number,
            "context": self.context,
        }


# =============================================================================
# Security Patterns Database
# =============================================================================

SECURITY_PATTERNS: list[SecurityPattern] = [
    # -------------------------------------------------------------------------
    # Prompt Injection Patterns
    # -------------------------------------------------------------------------
    SecurityPattern(
        name="ignore_instructions",
        issue_type=SecurityIssueType.PROMPT_INJECTION,
        severity=Severity.CRITICAL,
        pattern=r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
        description="Pattern that attempts to override previous instructions",
        recommendation="Remove instruction override language. Skills should not instruct the model to ignore its guidelines.",
    ),
    SecurityPattern(
        name="disregard_rules",
        issue_type=SecurityIssueType.PROMPT_INJECTION,
        severity=Severity.CRITICAL,
        pattern=r"disregard\s+(all\s+)?(previous|prior|above|earlier|safety|security)\s+(instructions?|prompts?|rules?|guidelines?)",
        description="Pattern that attempts to disregard safety rules",
        recommendation="Remove language that attempts to bypass safety guidelines.",
    ),
    SecurityPattern(
        name="new_instructions",
        issue_type=SecurityIssueType.PROMPT_INJECTION,
        severity=Severity.HIGH,
        pattern=r"(new|updated|revised)\s+instructions?\s*[:=]",
        description="Pattern that may attempt to inject new instructions",
        recommendation="Avoid language that could be used to inject replacement instructions.",
        false_positive_hint="May be legitimate if documenting instruction updates",
    ),
    SecurityPattern(
        name="jailbreak_phrases",
        issue_type=SecurityIssueType.JAILBREAK_ATTEMPT,
        severity=Severity.CRITICAL,
        pattern=r"(DAN|do\s+anything\s+now|developer\s+mode|jailbreak|bypass\s+(restrictions?|filters?|safety))",
        description="Known jailbreak attempt phrases",
        recommendation="Remove jailbreak language. Skills should work within model guidelines.",
    ),
    SecurityPattern(
        name="roleplay_override",
        issue_type=SecurityIssueType.JAILBREAK_ATTEMPT,
        severity=Severity.HIGH,
        pattern=r"(pretend|act\s+as\s+if|imagine)\s+you\s+(have\s+no|don't\s+have|are\s+not\s+bound\s+by)\s+(restrictions?|rules?|limitations?)",
        description="Roleplay used to bypass restrictions",
        recommendation="Remove roleplay scenarios that attempt to remove model limitations.",
    ),

    # -------------------------------------------------------------------------
    # Credential Exposure Patterns
    # -------------------------------------------------------------------------
    SecurityPattern(
        name="api_key_pattern",
        issue_type=SecurityIssueType.API_KEY_EXPOSURE,
        severity=Severity.CRITICAL,
        pattern=r"(api[_-]?key|apikey)\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}['\"]?",
        description="Potential API key exposure",
        recommendation="Remove API keys from skill content. Use environment variables or secure vaults.",
    ),
    SecurityPattern(
        name="aws_key",
        issue_type=SecurityIssueType.CREDENTIAL_EXPOSURE,
        severity=Severity.CRITICAL,
        pattern=r"(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}",
        description="AWS access key ID pattern detected",
        recommendation="Remove AWS credentials. Use IAM roles or environment variables.",
        case_sensitive=True,
    ),
    SecurityPattern(
        name="aws_secret",
        issue_type=SecurityIssueType.CREDENTIAL_EXPOSURE,
        severity=Severity.CRITICAL,
        pattern=r"aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?",
        description="AWS secret access key pattern detected",
        recommendation="Remove AWS credentials. Use IAM roles or environment variables.",
    ),
    SecurityPattern(
        name="password_in_content",
        issue_type=SecurityIssueType.HARDCODED_SECRET,
        severity=Severity.HIGH,
        pattern=r"(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{4,}['\"]",
        description="Hardcoded password detected",
        recommendation="Remove hardcoded passwords. Use secure credential management.",
    ),
    SecurityPattern(
        name="private_key",
        issue_type=SecurityIssueType.CREDENTIAL_EXPOSURE,
        severity=Severity.CRITICAL,
        pattern=r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
        description="Private key detected in content",
        recommendation="Remove private keys. Store them securely outside skill content.",
    ),
    SecurityPattern(
        name="bearer_token",
        issue_type=SecurityIssueType.CREDENTIAL_EXPOSURE,
        severity=Severity.HIGH,
        pattern=r"(bearer|authorization)\s*[=:]\s*['\"]?[a-zA-Z0-9_.-]{20,}['\"]?",
        description="Bearer token or authorization header detected",
        recommendation="Remove tokens from skill content. Use secure token management.",
    ),
    SecurityPattern(
        name="github_token",
        issue_type=SecurityIssueType.CREDENTIAL_EXPOSURE,
        severity=Severity.CRITICAL,
        pattern=r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})",
        description="GitHub personal access token detected",
        recommendation="Remove GitHub tokens. Use environment variables or GitHub Apps.",
    ),

    # -------------------------------------------------------------------------
    # Data Exfiltration Patterns
    # -------------------------------------------------------------------------
    SecurityPattern(
        name="send_to_url",
        issue_type=SecurityIssueType.DATA_EXFILTRATION,
        severity=Severity.HIGH,
        pattern=r"(send|post|upload|transmit|exfiltrate)\s+(data|information|content|files?)\s+(to|via)\s+(https?://|ftp://)",
        description="Pattern suggesting data transmission to external URL",
        recommendation="Review data transmission instructions. Ensure data is only sent to authorized destinations.",
        false_positive_hint="May be legitimate for intended API integrations",
    ),
    SecurityPattern(
        name="collect_sensitive",
        issue_type=SecurityIssueType.DATA_EXFILTRATION,
        severity=Severity.MEDIUM,
        pattern=r"(collect|gather|extract|capture)\s+(all\s+)?(sensitive|personal|private|confidential)\s+(data|information)",
        description="Instructions to collect sensitive information",
        recommendation="Review data collection scope. Minimize collection of sensitive data.",
    ),
    SecurityPattern(
        name="webhook_exfil",
        issue_type=SecurityIssueType.DATA_EXFILTRATION,
        severity=Severity.HIGH,
        pattern=r"(webhook|callback)\s*[=:]\s*['\"]?https?://[^'\">\s]+['\"]?",
        description="Webhook URL that could be used for data exfiltration",
        recommendation="Verify webhook URLs are authorized and necessary.",
    ),

    # -------------------------------------------------------------------------
    # Code Execution Patterns
    # -------------------------------------------------------------------------
    SecurityPattern(
        name="eval_exec",
        issue_type=SecurityIssueType.UNSAFE_CODE_EXECUTION,
        severity=Severity.HIGH,
        pattern=r"\b(eval|exec|compile)\s*\(",
        description="Dynamic code execution function detected",
        recommendation="Avoid dynamic code execution. Use safer alternatives.",
        false_positive_hint="May be legitimate in code examples being reviewed",
    ),
    SecurityPattern(
        name="shell_command",
        issue_type=SecurityIssueType.SHELL_INJECTION,
        severity=Severity.MEDIUM,
        pattern=r"(subprocess|os\.system|os\.popen|shell\s*=\s*True)",
        description="Shell command execution pattern",
        recommendation="Ensure shell commands are properly sanitized if needed.",
        false_positive_hint="May be legitimate for skill scripts",
    ),
    SecurityPattern(
        name="command_injection",
        issue_type=SecurityIssueType.COMMAND_INJECTION,
        severity=Severity.HIGH,
        pattern=r"(;|\||&&|\$\(|`)\s*(rm|del|format|mkfs|dd|chmod|chown)",
        description="Potential command injection with dangerous commands",
        recommendation="Avoid chaining dangerous shell commands. Use safe APIs.",
    ),

    # -------------------------------------------------------------------------
    # File System Patterns
    # -------------------------------------------------------------------------
    SecurityPattern(
        name="path_traversal",
        issue_type=SecurityIssueType.PATH_TRAVERSAL,
        severity=Severity.HIGH,
        pattern=r"\.\./|\.\.\\",
        description="Path traversal pattern detected",
        recommendation="Use absolute paths or validate path components to prevent traversal.",
        false_positive_hint="May be legitimate in relative path examples",
    ),
    SecurityPattern(
        name="sensitive_paths",
        issue_type=SecurityIssueType.UNSAFE_FILE_ACCESS,
        severity=Severity.MEDIUM,
        pattern=r"(/etc/passwd|/etc/shadow|\.ssh/|\.aws/|\.gnupg/|~/.bashrc|~/.zshrc)",
        description="Reference to sensitive system paths",
        recommendation="Avoid referencing sensitive system paths unless necessary.",
    ),
    SecurityPattern(
        name="root_access",
        issue_type=SecurityIssueType.PRIVILEGE_ESCALATION,
        severity=Severity.HIGH,
        pattern=r"(sudo\s+|as\s+root|with\s+root|#\s*chmod\s+777)",
        description="Root/admin privilege usage",
        recommendation="Minimize use of elevated privileges. Follow principle of least privilege.",
    ),

    # -------------------------------------------------------------------------
    # Network Patterns
    # -------------------------------------------------------------------------
    SecurityPattern(
        name="internal_ip",
        issue_type=SecurityIssueType.SSRF_RISK,
        severity=Severity.MEDIUM,
        pattern=r"(https?://)(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+)",
        description="Internal/private IP address in URL",
        recommendation="Avoid hardcoded internal addresses. Use configuration for network addresses.",
        false_positive_hint="May be legitimate for local development examples",
    ),
    SecurityPattern(
        name="insecure_protocol",
        issue_type=SecurityIssueType.UNSAFE_URL,
        severity=Severity.LOW,
        pattern=r"http://(?!localhost|127\.0\.0\.1)",
        description="Non-HTTPS URL detected",
        recommendation="Use HTTPS for external URLs to ensure encrypted communication.",
        false_positive_hint="May be acceptable for local development",
    ),

    # -------------------------------------------------------------------------
    # Information Disclosure
    # -------------------------------------------------------------------------
    SecurityPattern(
        name="debug_enabled",
        issue_type=SecurityIssueType.INFORMATION_DISCLOSURE,
        severity=Severity.LOW,
        pattern=r"(debug\s*[=:]\s*true|DEBUG\s*=\s*1|enable[_-]?debug)",
        description="Debug mode may be enabled",
        recommendation="Disable debug mode in production skills.",
    ),
    SecurityPattern(
        name="verbose_errors",
        issue_type=SecurityIssueType.INFORMATION_DISCLOSURE,
        severity=Severity.LOW,
        pattern=r"(show|display|print|log)\s+(full\s+)?(stack\s*trace|error\s+details|exception)",
        description="Verbose error output may leak information",
        recommendation="Limit error details in responses to prevent information leakage.",
    ),
]


def get_patterns_by_severity(severity: Severity) -> list[SecurityPattern]:
    """Get all patterns with a specific severity level."""
    return [p for p in SECURITY_PATTERNS if p.severity == severity]


def get_patterns_by_type(issue_type: SecurityIssueType) -> list[SecurityPattern]:
    """Get all patterns for a specific issue type."""
    return [p for p in SECURITY_PATTERNS if p.issue_type == issue_type]


def get_pattern_by_name(name: str) -> Optional[SecurityPattern]:
    """Get a pattern by its name."""
    for p in SECURITY_PATTERNS:
        if p.name == name:
            return p
    return None
