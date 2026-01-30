"""License policy checking for allowed licenses configuration."""
from __future__ import annotations

from license_analyzer.models.config import AnalyzerConfig
from license_analyzer.models.policy import PolicyViolation
from license_analyzer.models.scan import PackageLicense


def check_allowed_licenses(
    packages: list[PackageLicense],
    config: AnalyzerConfig,
) -> list[PolicyViolation]:
    """Check packages against allowed licenses configuration.

    Args:
        packages: List of packages with detected licenses.
        config: Configuration with allowed_licenses list.

    Returns:
        List of policy violations for packages not in allowed list.
        Returns empty list if allowed_licenses is not configured (None).
    """
    # If allowed_licenses is None (not configured), no policy checking
    if config.allowed_licenses is None:
        return []

    violations: list[PolicyViolation] = []
    allowed_set = set(config.allowed_licenses)

    for pkg in packages:
        if pkg.license is None:
            # Unknown license is always a violation when policy is configured
            violations.append(
                PolicyViolation(
                    package_name=pkg.name,
                    package_version=pkg.version,
                    detected_license=None,
                    reason="Unknown license",
                )
            )
        elif pkg.license not in allowed_set:
            violations.append(
                PolicyViolation(
                    package_name=pkg.name,
                    package_version=pkg.version,
                    detected_license=pkg.license,
                    reason=f"License '{pkg.license}' not in allowed list",
                )
            )

    return violations
