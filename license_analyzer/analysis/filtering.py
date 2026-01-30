"""Package filtering for ignored packages configuration."""

from __future__ import annotations

from typing import NamedTuple

from license_analyzer.models.config import AnalyzerConfig
from license_analyzer.models.scan import PackageLicense


class FilterResult(NamedTuple):
    """Result of filtering packages.

    Attributes:
        packages: List of packages after filtering.
        ignored_count: Number of packages that were ignored.
        ignored_names: Names of packages that were ignored.
    """

    packages: list[PackageLicense]
    ignored_count: int
    ignored_names: list[str]


def filter_ignored_packages(
    packages: list[PackageLicense],
    config: AnalyzerConfig,
) -> FilterResult:
    """Filter out ignored packages from the list.

    Package name matching is case-sensitive. If your config specifies
    "Requests" but the installed package is "requests", it will NOT
    be filtered. Use the exact package name as shown by pip list.

    Args:
        packages: List of packages to filter.
        config: Configuration with ignored_packages list.

    Returns:
        FilterResult with filtered packages and summary of ignored.
        If ignored_packages is None or empty, returns all packages.
    """
    # If ignored_packages is None or empty, return all packages
    if not config.ignored_packages:
        return FilterResult(
            packages=packages,
            ignored_count=0,
            ignored_names=[],
        )

    ignored_set = set(config.ignored_packages)
    filtered: list[PackageLicense] = []
    ignored_names: list[str] = []

    for pkg in packages:
        if pkg.name in ignored_set:
            ignored_names.append(pkg.name)
        else:
            filtered.append(pkg)

    return FilterResult(
        packages=filtered,
        ignored_count=len(ignored_names),
        ignored_names=ignored_names,
    )
