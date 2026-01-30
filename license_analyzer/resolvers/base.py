"""Base resolver interface."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseResolver(ABC):
    """Abstract base class for license resolvers.

    All license resolvers must inherit from this class and implement
    the async resolve() method.
    """

    @abstractmethod
    async def resolve(self, package_name: str, version: str) -> Optional[str]:
        """Resolve license for a package.

        Args:
            package_name: The package name to resolve.
            version: The package version.

        Returns:
            License identifier string (e.g., "MIT", "Apache-2.0"),
            or None if license cannot be determined.

        Raises:
            NetworkError: If a network request fails.
        """
