"""Scanner module for dependency discovery and license resolution."""
import asyncio
from importlib.metadata import distributions
from typing import Any, Optional

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from license_analyzer.exceptions import NetworkError
from license_analyzer.models.scan import PackageLicense
from license_analyzer.resolvers.github import GitHubLicenseResolver
from license_analyzer.resolvers.pypi import (
    extract_license_from_metadata,
    fetch_pypi_metadata,
)

# Rate limiting for concurrent HTTP requests (per architecture.md)
MAX_CONCURRENT_REQUESTS = 10


def discover_packages() -> list[PackageLicense]:
    """Discover all installed packages in the current environment.

    Returns:
        List of PackageLicense objects with name and version populated.
        License field is None (to be populated by resolvers).
    """
    packages: list[PackageLicense] = []

    for dist in distributions():
        name = dist.metadata.get("Name")
        version = dist.metadata.get("Version")

        # Skip packages with missing metadata
        if name is None or version is None:
            continue

        packages.append(
            PackageLicense(
                name=name,
                version=version,
                license=None,  # Will be populated by resolvers
            )
        )

    # Sort by name for deterministic output (NFR13)
    return sorted(packages, key=lambda p: p.name.lower())


async def resolve_licenses(
    packages: list[PackageLicense],
    console: Optional[Console] = None,
    show_progress: bool = True,
) -> list[PackageLicense]:
    """Resolve licenses for all packages using multi-source resolution.

    Resolution order:
    1. PyPI metadata (license field and classifiers)
    2. GitHub LICENSE file (if PyPI returns None and repo URL available)

    Args:
        packages: List of packages to resolve licenses for.
        console: Optional Rich Console for progress display.
        show_progress: Whether to show progress indicator (default: True).

    Returns:
        List of PackageLicense objects with license field populated where found.
        Packages that fail resolution will have license=None.

    Note:
        NetworkErrors are caught and logged, not propagated, to allow
        partial results when some packages fail to resolve.
    """
    # Rate limiting semaphore for concurrent HTTP requests
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def resolve_one(
        pkg: PackageLicense, client: httpx.AsyncClient
    ) -> PackageLicense:
        """Resolve license for a single package using multi-source resolution."""
        async with semaphore:
            # Fetch PyPI metadata (used for both PyPI license and GitHub repo URL)
            metadata: Optional[dict[str, Any]] = await fetch_pypi_metadata(
                pkg.name, client=client
            )

            # Try PyPI license first
            license_id = extract_license_from_metadata(metadata)

            # If PyPI doesn't have license, try GitHub LICENSE file
            if license_id is None and metadata is not None:
                github_resolver = GitHubLicenseResolver(
                    pypi_metadata=metadata, client=client
                )
                license_id = await github_resolver.resolve(pkg.name, pkg.version)

            return PackageLicense(
                name=pkg.name,
                version=pkg.version,
                license=license_id,
            )

    # Use shared HTTP client for connection reuse
    async with httpx.AsyncClient() as client:
        # Use progress indicator if console provided and show_progress is True
        if console is not None and show_progress and len(packages) > 0:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task_id = progress.add_task(
                    f"Resolving licenses for {len(packages)} packages...",
                    total=len(packages),
                )

                # Wrap resolve_one to handle errors and return result with index
                async def resolve_with_error_handling(
                    idx: int, pkg: PackageLicense
                ) -> tuple[int, PackageLicense]:
                    try:
                        result = await resolve_one(pkg, client)
                        return (idx, result)
                    except NetworkError:
                        # Network error - return package with no license
                        return (
                            idx,
                            PackageLicense(
                                name=pkg.name, version=pkg.version, license=None
                            ),
                        )

                progress_tasks = [
                    resolve_with_error_handling(i, pkg)
                    for i, pkg in enumerate(packages)
                ]

                # Process concurrently, updating progress as each completes
                resolved: list[Optional[PackageLicense]] = [None] * len(packages)

                for coro in asyncio.as_completed(progress_tasks):
                    idx, result = await coro
                    resolved[idx] = result
                    progress.advance(task_id)

                # Filter out None values and sort (all slots should be filled)
                final_resolved = [pkg for pkg in resolved if pkg is not None]
                return sorted(final_resolved, key=lambda p: p.name.lower())

        # No progress display - use concurrent gather
        gather_tasks = [resolve_one(pkg, client) for pkg in packages]
        results = await asyncio.gather(*gather_tasks, return_exceptions=True)

        # Process results, handling exceptions gracefully
        resolved_list: list[PackageLicense] = []
        for i, item in enumerate(results):
            if isinstance(item, PackageLicense):
                resolved_list.append(item)
            elif isinstance(item, NetworkError):
                # Network error - return package with no license but continue
                resolved_list.append(
                    PackageLicense(
                        name=packages[i].name,
                        version=packages[i].version,
                        license=None,
                    )
                )
            elif isinstance(item, BaseException):
                # Unexpected error - re-raise to surface bugs
                raise item

        # Sort by name for deterministic output (NFR13)
        return sorted(resolved_list, key=lambda p: p.name.lower())
