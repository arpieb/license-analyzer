"""Scan-related Pydantic models."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, Field

from license_analyzer.models.policy import PolicyViolation

if TYPE_CHECKING:
    from license_analyzer.models.config import AnalyzerConfig


class Verbosity(Enum):
    """Output verbosity levels."""

    QUIET = "quiet"
    NORMAL = "normal"
    VERBOSE = "verbose"


class ScanOptions(BaseModel):
    """Options for a license scan operation."""

    model_config = {"extra": "forbid"}

    format: Literal["terminal", "markdown", "json"] = Field(
        default="terminal",
        description="Output format for scan results",
    )
    verbosity: Verbosity = Field(
        default=Verbosity.NORMAL,
        description="Output verbosity level (quiet, normal, verbose)",
    )


class IgnoredPackagesSummary(BaseModel):
    """Summary of packages that were ignored during scanning.

    Used to track which packages were skipped due to ignored_packages config.
    """

    model_config = {"extra": "forbid"}

    ignored_count: int = Field(
        default=0,
        description="Number of packages that were ignored",
    )
    ignored_names: Optional[list[str]] = Field(
        default=None,
        description="Names of packages that were ignored",
    )


class PackageLicense(BaseModel):
    """License information for a single package."""

    model_config = {"extra": "forbid"}

    name: str = Field(description="Package name")
    version: str = Field(description="Package version")
    license: Optional[str] = Field(
        default=None, description="Detected or overridden license identifier"
    )
    original_license: Optional[str] = Field(
        default=None, description="Original detected license before override (FR25)"
    )
    override_reason: Optional[str] = Field(
        default=None, description="Reason for manual license override (FR25)"
    )

    @property
    def is_overridden(self) -> bool:
        """Check if this package has a manual override applied.

        Returns:
            True if override_reason is set, False otherwise.
        """
        return self.override_reason is not None


class ScanResult(BaseModel):
    """Result of a license scan operation."""

    model_config = {"extra": "forbid"}

    packages: list[PackageLicense] = Field(
        default_factory=list,
        description="List of packages with license information",
    )
    total_packages: int = Field(default=0, description="Total packages scanned")
    issues_found: int = Field(default=0, description="Number of license issues found")
    policy_violations: list[PolicyViolation] = Field(
        default_factory=list,
        description="List of license policy violations",
    )
    ignored_packages_summary: Optional[IgnoredPackagesSummary] = Field(
        default=None,
        description="Summary of packages ignored during scanning (FR24)",
    )

    @property
    def has_issues(self) -> bool:
        """Check if the scan result has any issues.

        Returns:
            True if issues_found > 0 or policy_violations exist, False otherwise.
        """
        return self.issues_found > 0 or len(self.policy_violations) > 0

    @classmethod
    def from_packages(cls, packages: list[PackageLicense]) -> ScanResult:
        """Create ScanResult from a list of packages.

        Calculates issues_found based on packages with no license (license=None).
        Does not perform policy checking - use from_packages_with_config for that.

        Args:
            packages: List of packages with license information.

        Returns:
            ScanResult with calculated totals and issues.
        """
        # Count packages with no license (None or empty string) as issues
        issues = sum(1 for pkg in packages if not pkg.license)
        return cls(
            packages=packages,
            total_packages=len(packages),
            issues_found=issues,
        )

    @classmethod
    def from_packages_with_config(
        cls,
        packages: list[PackageLicense],
        config: AnalyzerConfig,
        ignored_summary: Optional[IgnoredPackagesSummary] = None,
    ) -> ScanResult:
        """Create ScanResult from packages with policy checking.

        Calculates issues_found based on packages with no license,
        and checks packages against allowed licenses configuration.

        Args:
            packages: List of packages with license information.
            config: Configuration for policy checking.
            ignored_summary: Optional summary of ignored packages (FR24).

        Returns:
            ScanResult with calculated totals, issues, violations, and ignored summary.
        """
        from license_analyzer.analysis.policy import check_allowed_licenses

        issues = sum(1 for pkg in packages if not pkg.license)
        violations = check_allowed_licenses(packages, config)

        return cls(
            packages=packages,
            total_packages=len(packages),
            issues_found=issues,
            policy_violations=violations,
            ignored_packages_summary=ignored_summary,
        )
