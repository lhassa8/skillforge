"""Tests for skill versioning."""

import pytest

from skillforge.versioning import (
    SkillVersion,
    VersionConstraint,
    VersionError,
    VersionParseError,
    parse_version,
    parse_constraint,
    is_valid_version,
    compare_versions,
)


class TestSkillVersion:
    """Tests for SkillVersion dataclass."""

    def test_basic_version(self):
        """Test creating basic version."""
        v = SkillVersion(1, 2, 3)
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None

    def test_version_with_prerelease(self):
        """Test creating version with prerelease."""
        v = SkillVersion(1, 0, 0, "alpha")
        assert v.major == 1
        assert v.prerelease == "alpha"

    def test_version_string_representation(self):
        """Test version string conversion."""
        assert str(SkillVersion(1, 2, 3)) == "1.2.3"
        assert str(SkillVersion(1, 0, 0, "beta")) == "1.0.0-beta"
        assert str(SkillVersion(2, 1, 0, "rc.1")) == "2.1.0-rc.1"

    def test_version_equality(self):
        """Test version equality."""
        v1 = SkillVersion(1, 2, 3)
        v2 = SkillVersion(1, 2, 3)
        v3 = SkillVersion(1, 2, 4)

        assert v1 == v2
        assert v1 != v3

    def test_version_equality_with_prerelease(self):
        """Test version equality with prerelease."""
        v1 = SkillVersion(1, 0, 0, "alpha")
        v2 = SkillVersion(1, 0, 0, "alpha")
        v3 = SkillVersion(1, 0, 0, "beta")

        assert v1 == v2
        assert v1 != v3

    def test_version_comparison(self):
        """Test version comparison operators."""
        v1 = SkillVersion(1, 0, 0)
        v2 = SkillVersion(2, 0, 0)
        v3 = SkillVersion(1, 1, 0)
        v4 = SkillVersion(1, 0, 1)

        assert v1 < v2
        assert v1 < v3
        assert v1 < v4
        assert v2 > v1
        assert v3 > v1
        assert v4 > v1
        assert v1 <= v2
        assert v1 >= v1

    def test_prerelease_has_lower_precedence(self):
        """Test that prerelease versions have lower precedence."""
        v1 = SkillVersion(1, 0, 0)
        v2 = SkillVersion(1, 0, 0, "alpha")
        v3 = SkillVersion(1, 0, 0, "beta")

        assert v2 < v1  # Prerelease < release
        assert v3 < v1  # Prerelease < release
        assert v2 < v3  # alpha < beta

    def test_prerelease_comparison(self):
        """Test prerelease identifier comparison."""
        alpha = SkillVersion(1, 0, 0, "alpha")
        alpha1 = SkillVersion(1, 0, 0, "alpha.1")
        beta = SkillVersion(1, 0, 0, "beta")
        rc1 = SkillVersion(1, 0, 0, "rc.1")

        assert alpha < alpha1  # Longer prerelease has higher precedence
        assert alpha < beta
        assert beta < rc1

    def test_version_hash(self):
        """Test version is hashable."""
        v1 = SkillVersion(1, 2, 3)
        v2 = SkillVersion(1, 2, 3)

        # Should be able to use in sets and dicts
        s = {v1, v2}
        assert len(s) == 1

    def test_bump_major(self):
        """Test bumping major version."""
        v = SkillVersion(1, 2, 3)
        bumped = v.bump("major")

        assert bumped.major == 2
        assert bumped.minor == 0
        assert bumped.patch == 0

    def test_bump_minor(self):
        """Test bumping minor version."""
        v = SkillVersion(1, 2, 3)
        bumped = v.bump("minor")

        assert bumped.major == 1
        assert bumped.minor == 3
        assert bumped.patch == 0

    def test_bump_patch(self):
        """Test bumping patch version."""
        v = SkillVersion(1, 2, 3)
        bumped = v.bump("patch")

        assert bumped.major == 1
        assert bumped.minor == 2
        assert bumped.patch == 4

    def test_bump_invalid_part(self):
        """Test bumping invalid part raises error."""
        v = SkillVersion(1, 2, 3)

        with pytest.raises(ValueError):
            v.bump("invalid")

    def test_is_compatible_with_major_version(self):
        """Test API compatibility checking."""
        v1 = SkillVersion(1, 2, 0)
        v2 = SkillVersion(1, 5, 3)
        v3 = SkillVersion(2, 0, 0)

        assert v1.is_compatible_with(v2)  # Same major
        assert not v1.is_compatible_with(v3)  # Different major

    def test_is_compatible_with_zero_major(self):
        """Test compatibility for 0.x versions."""
        v1 = SkillVersion(0, 1, 0)
        v2 = SkillVersion(0, 1, 5)
        v3 = SkillVersion(0, 2, 0)

        assert v1.is_compatible_with(v2)  # Same 0.x
        assert not v1.is_compatible_with(v3)  # Different 0.x

    def test_is_prerelease(self):
        """Test prerelease detection."""
        v1 = SkillVersion(1, 0, 0)
        v2 = SkillVersion(1, 0, 0, "alpha")

        assert not v1.is_prerelease()
        assert v2.is_prerelease()


class TestParseVersion:
    """Tests for version parsing."""

    def test_parse_basic_version(self):
        """Test parsing basic version strings."""
        v = parse_version("1.2.3")
        assert v == SkillVersion(1, 2, 3)

    def test_parse_with_prerelease(self):
        """Test parsing versions with prerelease."""
        v = parse_version("1.0.0-alpha")
        assert v == SkillVersion(1, 0, 0, "alpha")

        v = parse_version("1.0.0-beta.1")
        assert v == SkillVersion(1, 0, 0, "beta.1")

    def test_parse_with_v_prefix(self):
        """Test parsing versions with v prefix."""
        v = parse_version("v1.2.3")
        assert v == SkillVersion(1, 2, 3)

    def test_parse_with_whitespace(self):
        """Test parsing versions with whitespace."""
        v = parse_version("  1.2.3  ")
        assert v == SkillVersion(1, 2, 3)

    def test_parse_invalid_format_fails(self):
        """Test parsing invalid formats fails."""
        with pytest.raises(VersionParseError):
            parse_version("invalid")

        with pytest.raises(VersionParseError):
            parse_version("1.2")

        with pytest.raises(VersionParseError):
            parse_version("1.2.3.4")

    def test_parse_leading_zeros_fail(self):
        """Test that leading zeros fail (semver requirement)."""
        with pytest.raises(VersionParseError):
            parse_version("01.2.3")

        with pytest.raises(VersionParseError):
            parse_version("1.02.3")


class TestVersionConstraint:
    """Tests for VersionConstraint class."""

    def test_exact_constraint(self):
        """Test exact version constraint."""
        vc = parse_constraint("1.2.3")
        assert vc.operator == "="
        assert vc.version == SkillVersion(1, 2, 3)

    def test_exact_with_operator(self):
        """Test explicit exact constraint."""
        vc = parse_constraint("=1.2.3")
        assert vc.operator == "="

    def test_greater_than_or_equal(self):
        """Test >= constraint."""
        vc = parse_constraint(">=1.2.3")
        assert vc.operator == ">="

        assert vc.satisfies(SkillVersion(1, 2, 3))
        assert vc.satisfies(SkillVersion(1, 2, 4))
        assert vc.satisfies(SkillVersion(2, 0, 0))
        assert not vc.satisfies(SkillVersion(1, 2, 2))

    def test_less_than_or_equal(self):
        """Test <= constraint."""
        vc = parse_constraint("<=1.2.3")
        assert vc.operator == "<="

        assert vc.satisfies(SkillVersion(1, 2, 3))
        assert vc.satisfies(SkillVersion(1, 2, 2))
        assert vc.satisfies(SkillVersion(1, 0, 0))
        assert not vc.satisfies(SkillVersion(1, 2, 4))

    def test_greater_than(self):
        """Test > constraint."""
        vc = parse_constraint(">1.2.3")
        assert vc.operator == ">"

        assert vc.satisfies(SkillVersion(1, 2, 4))
        assert vc.satisfies(SkillVersion(2, 0, 0))
        assert not vc.satisfies(SkillVersion(1, 2, 3))
        assert not vc.satisfies(SkillVersion(1, 2, 2))

    def test_less_than(self):
        """Test < constraint."""
        vc = parse_constraint("<1.2.3")
        assert vc.operator == "<"

        assert vc.satisfies(SkillVersion(1, 2, 2))
        assert vc.satisfies(SkillVersion(1, 0, 0))
        assert not vc.satisfies(SkillVersion(1, 2, 3))
        assert not vc.satisfies(SkillVersion(1, 2, 4))

    def test_caret_constraint_basic(self):
        """Test ^ (caret) constraint for 1.x.x versions."""
        vc = parse_constraint("^1.2.3")
        assert vc.operator == "^"

        # Should allow any 1.x.x >= 1.2.3
        assert vc.satisfies(SkillVersion(1, 2, 3))
        assert vc.satisfies(SkillVersion(1, 2, 4))
        assert vc.satisfies(SkillVersion(1, 9, 0))

        # Should not allow 2.x or < 1.2.3
        assert not vc.satisfies(SkillVersion(2, 0, 0))
        assert not vc.satisfies(SkillVersion(1, 2, 2))

    def test_caret_constraint_zero_major(self):
        """Test ^ constraint for 0.x.x versions."""
        vc = parse_constraint("^0.2.3")

        # For 0.x versions, only allow same 0.x
        assert vc.satisfies(SkillVersion(0, 2, 3))
        assert vc.satisfies(SkillVersion(0, 2, 4))

        # Different minor is breaking for 0.x
        assert not vc.satisfies(SkillVersion(0, 3, 0))
        assert not vc.satisfies(SkillVersion(0, 2, 2))

    def test_caret_constraint_zero_minor(self):
        """Test ^ constraint for 0.0.x versions."""
        vc = parse_constraint("^0.0.3")

        # For 0.0.x, only allow exact patch
        assert vc.satisfies(SkillVersion(0, 0, 3))

        # Any other version is incompatible
        assert not vc.satisfies(SkillVersion(0, 0, 4))
        assert not vc.satisfies(SkillVersion(0, 0, 2))

    def test_tilde_constraint(self):
        """Test ~ (tilde) constraint."""
        vc = parse_constraint("~1.2.3")
        assert vc.operator == "~"

        # Should allow 1.2.x >= 1.2.3
        assert vc.satisfies(SkillVersion(1, 2, 3))
        assert vc.satisfies(SkillVersion(1, 2, 9))

        # Should not allow different minor
        assert not vc.satisfies(SkillVersion(1, 3, 0))
        assert not vc.satisfies(SkillVersion(1, 2, 2))

    def test_constraint_string_representation(self):
        """Test constraint string conversion."""
        vc = parse_constraint("^1.2.3")
        assert str(vc) == "^1.2.3"

        vc = parse_constraint("1.2.3")
        assert str(vc) == "1.2.3"  # Exact constraint without =


class TestIsValidVersion:
    """Tests for is_valid_version function."""

    def test_valid_versions(self):
        """Test valid version strings."""
        assert is_valid_version("1.0.0")
        assert is_valid_version("1.2.3")
        assert is_valid_version("0.0.1")
        assert is_valid_version("1.0.0-alpha")
        assert is_valid_version("1.0.0-beta.1")
        assert is_valid_version("v1.2.3")

    def test_invalid_versions(self):
        """Test invalid version strings."""
        assert not is_valid_version("invalid")
        assert not is_valid_version("1.2")
        assert not is_valid_version("1.2.3.4")
        assert not is_valid_version("01.2.3")
        assert not is_valid_version("")


class TestCompareVersions:
    """Tests for compare_versions function."""

    def test_less_than(self):
        """Test v1 < v2."""
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("1.0.0", "1.1.0") == -1
        assert compare_versions("1.0.0", "1.0.1") == -1

    def test_greater_than(self):
        """Test v1 > v2."""
        assert compare_versions("2.0.0", "1.0.0") == 1
        assert compare_versions("1.1.0", "1.0.0") == 1
        assert compare_versions("1.0.1", "1.0.0") == 1

    def test_equal(self):
        """Test v1 == v2."""
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("1.2.3", "1.2.3") == 0

    def test_prerelease_comparison(self):
        """Test prerelease version comparison."""
        assert compare_versions("1.0.0-alpha", "1.0.0") == -1  # Prerelease < release
        assert compare_versions("1.0.0-alpha", "1.0.0-beta") == -1
