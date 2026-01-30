"""Tests for license policy checker."""
from license_analyzer.analysis.overrides import apply_license_overrides
from license_analyzer.analysis.policy import check_allowed_licenses
from license_analyzer.models.config import AnalyzerConfig, LicenseOverride
from license_analyzer.models.policy import PolicyViolation
from license_analyzer.models.scan import PackageLicense


class TestCheckAllowedLicenses:
    """Tests for check_allowed_licenses function."""

    def test_none_config_returns_empty(self) -> None:
        """Test that None allowed_licenses means no policy checking."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="GPL-3.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=None)

        violations = check_allowed_licenses(packages, config)

        assert violations == []

    def test_all_packages_allowed(self) -> None:
        """Test no violations when all packages use allowed licenses."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
            PackageLicense(name="pydantic", version="2.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(
            allowed_licenses=["MIT", "Apache-2.0", "BSD-3-Clause"]
        )

        violations = check_allowed_licenses(packages, config)

        assert violations == []

    def test_disallowed_license_flagged(self) -> None:
        """Test that packages with disallowed licenses are flagged."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="GPL-3.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT", "Apache-2.0"])

        violations = check_allowed_licenses(packages, config)

        assert len(violations) == 1
        assert violations[0].package_name == "requests"
        assert violations[0].package_version == "2.28.0"
        assert violations[0].detected_license == "GPL-3.0"
        assert "GPL-3.0" in violations[0].reason
        assert "not in allowed list" in violations[0].reason

    def test_empty_allowed_list_flags_all(self) -> None:
        """Test that empty allowed list flags all packages with licenses."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ]
        config = AnalyzerConfig(allowed_licenses=[])

        violations = check_allowed_licenses(packages, config)

        assert len(violations) == 2
        package_names = {v.package_name for v in violations}
        assert package_names == {"click", "requests"}

    def test_unknown_license_flagged_differently(self) -> None:
        """Test that unknown license (None) is flagged with different reason."""
        packages = [
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        violations = check_allowed_licenses(packages, config)

        assert len(violations) == 1
        assert violations[0].package_name == "unknown-pkg"
        assert violations[0].detected_license is None
        assert violations[0].reason == "Unknown license"

    def test_multiple_violations(self) -> None:
        """Test multiple packages can have violations."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="GPL-3.0"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
            PackageLicense(name="safe", version="1.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        violations = check_allowed_licenses(packages, config)

        assert len(violations) == 3
        package_names = {v.package_name for v in violations}
        assert package_names == {"click", "requests", "unknown"}

    def test_case_sensitive_matching(self) -> None:
        """Test that license matching is case-sensitive."""
        packages = [
            PackageLicense(name="pkg", version="1.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(allowed_licenses=["mit"])  # lowercase

        violations = check_allowed_licenses(packages, config)

        # MIT != mit, so should be flagged
        assert len(violations) == 1
        assert violations[0].package_name == "pkg"

    def test_allowed_packages_not_flagged(self) -> None:
        """Test that allowed packages are not in violations."""
        packages = [
            PackageLicense(name="allowed1", version="1.0.0", license="MIT"),
            PackageLicense(name="not-allowed", version="1.0.0", license="GPL-3.0"),
            PackageLicense(name="allowed2", version="1.0.0", license="Apache-2.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT", "Apache-2.0"])

        violations = check_allowed_licenses(packages, config)

        assert len(violations) == 1
        assert violations[0].package_name == "not-allowed"

    def test_empty_packages_list(self) -> None:
        """Test handling of empty packages list."""
        packages: list[PackageLicense] = []
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        violations = check_allowed_licenses(packages, config)

        assert violations == []

    def test_default_config_no_violations(self) -> None:
        """Test that default config (allowed_licenses=None) returns no violations."""
        packages = [
            PackageLicense(name="any", version="1.0.0", license="AGPL-3.0"),
        ]
        config = AnalyzerConfig()  # Default config

        violations = check_allowed_licenses(packages, config)

        assert violations == []

    def test_mixed_allowed_and_unknown(self) -> None:
        """Test packages with both allowed licenses and unknown licenses."""
        packages = [
            PackageLicense(name="allowed", version="1.0.0", license="MIT"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        violations = check_allowed_licenses(packages, config)

        # Only unknown should be flagged
        assert len(violations) == 1
        assert violations[0].package_name == "unknown"
        assert violations[0].reason == "Unknown license"


class TestCheckAllowedLicensesViolationDetails:
    """Tests for violation details and messages."""

    def test_violation_message_includes_license_name(self) -> None:
        """Test that violation reason includes the license name."""
        packages = [
            PackageLicense(name="pkg", version="1.0.0", license="LGPL-2.1"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        violations = check_allowed_licenses(packages, config)

        assert "LGPL-2.1" in violations[0].reason

    def test_violation_includes_version(self) -> None:
        """Test that violation includes package version."""
        packages = [
            PackageLicense(name="pkg", version="1.2.3", license="GPL-3.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        violations = check_allowed_licenses(packages, config)

        assert violations[0].package_version == "1.2.3"

    def test_violation_is_policy_violation_instance(self) -> None:
        """Test that returned violations are PolicyViolation instances."""
        packages = [
            PackageLicense(name="pkg", version="1.0.0", license="GPL-3.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        violations = check_allowed_licenses(packages, config)

        assert isinstance(violations[0], PolicyViolation)


class TestOverridesWithPolicy:
    """Tests for interaction between overrides and policy checking (FR25 + FR23)."""

    def test_overridden_license_checked_against_allowed(self) -> None:
        """Test that overridden license is checked against allowed_licenses."""
        packages = [
            PackageLicense(name="pkg", version="1.0.0", license="Unknown"),
        ]
        config = AnalyzerConfig(
            allowed_licenses=["MIT"],
            overrides={
                "pkg": LicenseOverride(
                    license="GPL-3.0",  # Not in allowed list
                    reason="Verified license",
                ),
            },
        )

        # Apply overrides first (simulating CLI flow)
        packages_with_overrides = apply_license_overrides(packages, config)

        # Then check policy
        violations = check_allowed_licenses(packages_with_overrides, config)

        # GPL-3.0 should be flagged even though it was overridden
        assert len(violations) == 1
        assert violations[0].package_name == "pkg"
        assert violations[0].detected_license == "GPL-3.0"

    def test_override_does_not_bypass_policy(self) -> None:
        """Test that override cannot bypass allowed_licenses policy."""
        packages = [
            PackageLicense(name="restricted", version="1.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(
            allowed_licenses=["Apache-2.0"],  # Only Apache allowed
            overrides={
                "restricted": LicenseOverride(
                    license="MIT",  # MIT not in allowed list
                    reason="Changing to MIT",
                ),
            },
        )

        # Apply overrides
        packages_with_overrides = apply_license_overrides(packages, config)

        # Check policy - MIT should still be flagged
        violations = check_allowed_licenses(packages_with_overrides, config)

        assert len(violations) == 1
        assert violations[0].detected_license == "MIT"

    def test_override_to_allowed_license_passes(self) -> None:
        """Test that overriding to an allowed license passes policy."""
        packages = [
            PackageLicense(name="pkg", version="1.0.0", license="GPL-3.0"),
        ]
        config = AnalyzerConfig(
            allowed_licenses=["MIT", "Apache-2.0"],
            overrides={
                "pkg": LicenseOverride(
                    license="MIT",  # In allowed list
                    reason="Verified as MIT",
                ),
            },
        )

        # Apply overrides
        packages_with_overrides = apply_license_overrides(packages, config)

        # Check policy - should pass because MIT is allowed
        violations = check_allowed_licenses(packages_with_overrides, config)

        assert len(violations) == 0

    def test_override_unknown_to_allowed_passes(self) -> None:
        """Test that overriding unknown license to allowed license passes."""
        packages = [
            PackageLicense(name="pkg", version="1.0.0", license=None),  # Unknown
        ]
        config = AnalyzerConfig(
            allowed_licenses=["MIT"],
            overrides={
                "pkg": LicenseOverride(
                    license="MIT",
                    reason="Verified from LICENSE file",
                ),
            },
        )

        # Apply overrides
        packages_with_overrides = apply_license_overrides(packages, config)

        # Check policy - should pass
        violations = check_allowed_licenses(packages_with_overrides, config)

        assert len(violations) == 0
        # Also verify the override was applied
        assert packages_with_overrides[0].license == "MIT"
        assert packages_with_overrides[0].is_overridden

    def test_mixed_overrides_and_policy(self) -> None:
        """Test scenario with some overrides passing and some failing policy."""
        packages = [
            PackageLicense(name="good", version="1.0.0", license="Unknown"),
            PackageLicense(name="bad", version="1.0.0", license="Unknown"),
            PackageLicense(name="unchanged", version="1.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(
            allowed_licenses=["MIT", "Apache-2.0"],
            overrides={
                "good": LicenseOverride(
                    license="MIT",  # Allowed
                    reason="Verified",
                ),
                "bad": LicenseOverride(
                    license="GPL-3.0",  # Not allowed
                    reason="Verified",
                ),
            },
        )

        # Apply overrides
        packages_with_overrides = apply_license_overrides(packages, config)

        # Check policy
        violations = check_allowed_licenses(packages_with_overrides, config)

        # Only "bad" should have violation
        assert len(violations) == 1
        assert violations[0].package_name == "bad"
        assert violations[0].detected_license == "GPL-3.0"
