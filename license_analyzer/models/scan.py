"""Scan-related Pydantic models."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ScanOptions(BaseModel):
    """Options for a license scan operation."""

    model_config = {"extra": "forbid"}

    format: Literal["terminal", "markdown", "json"] = Field(
        default="terminal",
        description="Output format for scan results",
    )
    # Future options will be added here:
    # output: str | None = None
    # quiet: bool = False
    # verbose: bool = False


class PackageLicense(BaseModel):
    """License information for a single package."""

    model_config = {"extra": "forbid"}

    name: str = Field(description="Package name")
    version: str = Field(description="Package version")
    license: Optional[str] = Field(
        default=None, description="Detected license identifier"
    )


class ScanResult(BaseModel):
    """Result of a license scan operation."""

    model_config = {"extra": "forbid"}

    packages: list[PackageLicense] = Field(
        default_factory=list,
        description="List of packages with license information",
    )
    total_packages: int = Field(default=0, description="Total packages scanned")
    issues_found: int = Field(default=0, description="Number of license issues found")

    @property
    def has_issues(self) -> bool:
        """Check if the scan result has any issues.

        Returns:
            True if issues_found > 0, False otherwise.
        """
        return self.issues_found > 0

    @classmethod
    def from_packages(cls, packages: list[PackageLicense]) -> ScanResult:
        """Create ScanResult from a list of packages.

        Calculates issues_found based on packages with no license (license=None).

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
