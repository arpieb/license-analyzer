"""License resolvers package."""
from license_analyzer.resolvers.base import BaseResolver
from license_analyzer.resolvers.github import GitHubLicenseResolver
from license_analyzer.resolvers.pypi import PyPIResolver

__all__ = ["BaseResolver", "GitHubLicenseResolver", "PyPIResolver"]
