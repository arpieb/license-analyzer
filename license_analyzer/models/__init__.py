"""Pydantic data models for license-analyzer."""

from license_analyzer.models.dependency import (
    CategoryStatistics,
    CircularReference,
    CompatibilityMatrix,
    CompatibilityResult,
    CompatibilityStatus,
    DependencyNode,
    DependencyTree,
    LicenseStatistics,
)
from license_analyzer.models.policy import PolicyViolation
from license_analyzer.models.scan import (
    IgnoredPackagesSummary,
    PackageLicense,
    ScanOptions,
    ScanResult,
)

__all__ = [
    "CategoryStatistics",
    "CircularReference",
    "CompatibilityMatrix",
    "CompatibilityResult",
    "CompatibilityStatus",
    "DependencyNode",
    "DependencyTree",
    "IgnoredPackagesSummary",
    "LicenseStatistics",
    "PackageLicense",
    "PolicyViolation",
    "ScanOptions",
    "ScanResult",
]
