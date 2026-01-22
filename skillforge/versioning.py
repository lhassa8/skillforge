"""Semantic versioning for skills."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional


class VersionError(Exception):
    """Raised when version operations fail."""
    pass


class VersionParseError(VersionError):
    """Raised when version string parsing fails."""
    pass


# Semantic version pattern: MAJOR.MINOR.PATCH[-PRERELEASE]
VERSION_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

# Constraint pattern: OPERATOR VERSION
CONSTRAINT_PATTERN = re.compile(
    r"^(?P<operator>\^|~|>=|<=|>|<|=)?(?P<version>.+)$"
)


@dataclass
class SkillVersion:
    """Semantic version for a skill.

    Follows Semantic Versioning 2.0.0 (https://semver.org/).

    Examples:
        - 1.0.0
        - 2.1.3
        - 1.0.0-alpha
        - 1.0.0-beta.1
        - 1.0.0-rc.1
    """
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None

    def __str__(self) -> str:
        """Return version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        return version

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SkillVersion):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: SkillVersion) -> bool:
        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Prerelease versions have lower precedence
        if self.prerelease is None and other.prerelease is None:
            return False
        if self.prerelease is None:
            return False  # Release > prerelease
        if other.prerelease is None:
            return True  # Prerelease < release

        # Compare prerelease identifiers
        return self._compare_prerelease(self.prerelease, other.prerelease) < 0

    def __le__(self, other: SkillVersion) -> bool:
        return self == other or self < other

    def __gt__(self, other: SkillVersion) -> bool:
        return not self <= other

    def __ge__(self, other: SkillVersion) -> bool:
        return not self < other

    @staticmethod
    def _compare_prerelease(a: str, b: str) -> int:
        """Compare prerelease identifiers."""
        a_parts = a.split(".")
        b_parts = b.split(".")

        for a_part, b_part in zip(a_parts, b_parts):
            # Numeric identifiers have lower precedence than alphanumeric
            a_is_num = a_part.isdigit()
            b_is_num = b_part.isdigit()

            if a_is_num and b_is_num:
                if int(a_part) != int(b_part):
                    return int(a_part) - int(b_part)
            elif a_is_num:
                return -1  # Numeric < alphanumeric
            elif b_is_num:
                return 1
            else:
                if a_part != b_part:
                    return -1 if a_part < b_part else 1

        # Longer prerelease has higher precedence
        return len(a_parts) - len(b_parts)

    @classmethod
    def parse(cls, version_str: str) -> SkillVersion:
        """Parse a version string.

        Args:
            version_str: Version string like "1.2.3" or "1.0.0-alpha"

        Returns:
            SkillVersion instance

        Raises:
            VersionParseError: If version string is invalid
        """
        version_str = version_str.strip()

        # Handle 'v' prefix
        if version_str.startswith("v"):
            version_str = version_str[1:]

        match = VERSION_PATTERN.match(version_str)
        if not match:
            raise VersionParseError(f"Invalid version string: {version_str}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
        )

    def bump(self, part: Literal["major", "minor", "patch"]) -> SkillVersion:
        """Create a new version with the specified part bumped.

        Args:
            part: Which part to bump ("major", "minor", or "patch")

        Returns:
            New SkillVersion with bumped version
        """
        if part == "major":
            return SkillVersion(self.major + 1, 0, 0)
        elif part == "minor":
            return SkillVersion(self.major, self.minor + 1, 0)
        elif part == "patch":
            return SkillVersion(self.major, self.minor, self.patch + 1)
        else:
            raise ValueError(f"Invalid version part: {part}")

    def is_compatible_with(self, other: SkillVersion) -> bool:
        """Check if this version is API-compatible with another.

        Compatible means same major version (for major > 0) or
        same major.minor (for major == 0).

        Args:
            other: Version to check compatibility with

        Returns:
            True if versions are compatible
        """
        if self.major == 0 and other.major == 0:
            # 0.x versions: minor version changes are breaking
            return self.minor == other.minor
        return self.major == other.major

    def is_prerelease(self) -> bool:
        """Check if this is a prerelease version."""
        return self.prerelease is not None


@dataclass
class VersionConstraint:
    """Version constraint for dependency resolution.

    Supports operators:
        - ^1.2.3: Compatible with 1.2.3 (>=1.2.3 <2.0.0)
        - ~1.2.3: Approximately 1.2.3 (>=1.2.3 <1.3.0)
        - >=1.2.3: Greater than or equal
        - <=1.2.3: Less than or equal
        - >1.2.3: Greater than
        - <1.2.3: Less than
        - =1.2.3 or 1.2.3: Exactly 1.2.3
    """
    operator: str
    version: SkillVersion

    def __str__(self) -> str:
        if self.operator == "=":
            return str(self.version)
        return f"{self.operator}{self.version}"

    @classmethod
    def parse(cls, constraint_str: str) -> VersionConstraint:
        """Parse a constraint string.

        Args:
            constraint_str: Constraint like "^1.2.3" or ">=1.0.0"

        Returns:
            VersionConstraint instance

        Raises:
            VersionParseError: If constraint string is invalid
        """
        constraint_str = constraint_str.strip()
        match = CONSTRAINT_PATTERN.match(constraint_str)

        if not match:
            raise VersionParseError(f"Invalid constraint: {constraint_str}")

        operator = match.group("operator") or "="
        version_str = match.group("version")

        try:
            version = SkillVersion.parse(version_str)
        except VersionParseError:
            raise VersionParseError(f"Invalid version in constraint: {constraint_str}")

        return cls(operator=operator, version=version)

    def satisfies(self, version: SkillVersion) -> bool:
        """Check if a version satisfies this constraint.

        Args:
            version: Version to check

        Returns:
            True if version satisfies the constraint
        """
        if self.operator == "=":
            return version == self.version
        elif self.operator == ">=":
            return version >= self.version
        elif self.operator == "<=":
            return version <= self.version
        elif self.operator == ">":
            return version > self.version
        elif self.operator == "<":
            return version < self.version
        elif self.operator == "^":
            # Caret: compatible versions
            return self._satisfies_caret(version)
        elif self.operator == "~":
            # Tilde: approximately equivalent
            return self._satisfies_tilde(version)
        else:
            raise VersionError(f"Unknown operator: {self.operator}")

    def _satisfies_caret(self, version: SkillVersion) -> bool:
        """Check caret constraint (^): compatible versions.

        ^1.2.3 := >=1.2.3 <2.0.0
        ^0.2.3 := >=0.2.3 <0.3.0
        ^0.0.3 := >=0.0.3 <0.0.4
        """
        if version < self.version:
            return False

        if self.version.major == 0:
            if self.version.minor == 0:
                # ^0.0.x: only patch updates
                return (
                    version.major == 0
                    and version.minor == 0
                    and version.patch == self.version.patch
                )
            else:
                # ^0.x.y: minor updates within 0.x
                return version.major == 0 and version.minor == self.version.minor
        else:
            # ^x.y.z: major updates
            return version.major == self.version.major

    def _satisfies_tilde(self, version: SkillVersion) -> bool:
        """Check tilde constraint (~): approximately equivalent.

        ~1.2.3 := >=1.2.3 <1.3.0
        ~1.2 := >=1.2.0 <1.3.0
        ~0.2.3 := >=0.2.3 <0.3.0
        """
        if version < self.version:
            return False

        return (
            version.major == self.version.major
            and version.minor == self.version.minor
        )


def parse_version(version_str: str) -> SkillVersion:
    """Parse a version string.

    Args:
        version_str: Version string like "1.2.3"

    Returns:
        SkillVersion instance
    """
    return SkillVersion.parse(version_str)


def parse_constraint(constraint_str: str) -> VersionConstraint:
    """Parse a version constraint string.

    Args:
        constraint_str: Constraint string like "^1.2.3"

    Returns:
        VersionConstraint instance
    """
    return VersionConstraint.parse(constraint_str)


def is_valid_version(version_str: str) -> bool:
    """Check if a string is a valid version.

    Args:
        version_str: String to check

    Returns:
        True if valid version string
    """
    try:
        SkillVersion.parse(version_str)
        return True
    except VersionParseError:
        return False


def compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    ver1 = SkillVersion.parse(v1)
    ver2 = SkillVersion.parse(v2)

    if ver1 < ver2:
        return -1
    elif ver1 > ver2:
        return 1
    return 0
