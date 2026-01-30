"""License resolvers package."""

from license_analyzer.resolvers.base import BaseResolver
from license_analyzer.resolvers.dependency import DependencyResolver
from license_analyzer.resolvers.github import GitHubLicenseResolver
from license_analyzer.resolvers.pypi import PyPIResolver
from license_analyzer.resolvers.readme import ReadmeLicenseResolver

__all__ = [
    "BaseResolver",
    "DependencyResolver",
    "GitHubLicenseResolver",
    "PyPIResolver",
    "ReadmeLicenseResolver",
]
