"""GitHub LICENSE file resolver."""
from typing import Any, Optional

import httpx

from license_analyzer.resolvers.base import BaseResolver

# Common LICENSE file names to try
LICENSE_FILES = ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE", "COPYING"]

# Common branch names to try
BRANCHES = ["main", "master", "HEAD"]


class GitHubLicenseResolver(BaseResolver):
    """Resolver that fetches LICENSE files from GitHub repositories.

    This resolver extracts the GitHub repository URL from PyPI metadata,
    fetches the LICENSE file content, and identifies the license type
    using pattern matching against common license templates.
    """

    def __init__(
        self,
        pypi_metadata: Optional[dict[str, Any]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Initialize with optional PyPI metadata and HTTP client.

        Args:
            pypi_metadata: PyPI JSON API response data containing repo URLs.
            client: Optional shared httpx.AsyncClient for connection reuse.
        """
        self._pypi_metadata = pypi_metadata
        self._client = client

    async def resolve(self, package_name: str, version: str) -> Optional[str]:
        """Resolve license from GitHub LICENSE file.

        Args:
            package_name: The package name to resolve.
            version: The package version (not used for GitHub resolution).

        Returns:
            SPDX license identifier (e.g., "MIT", "Apache-2.0"),
            or None if license cannot be determined.
        """
        repo_url = self._extract_github_url()
        if not repo_url:
            return None

        license_content = await self._fetch_license_file(repo_url)
        if not license_content:
            return None

        return self._identify_license(license_content)

    def _extract_github_url(self) -> Optional[str]:
        """Extract GitHub repository URL from PyPI metadata.

        Checks project_urls for common keys like Repository, Source,
        and falls back to home_page.

        Returns:
            Normalized GitHub URL, or None if not found.
        """
        if not self._pypi_metadata:
            return None

        info: dict[str, Any] = self._pypi_metadata.get("info", {})
        if not info:
            return None

        # Check project_urls first (most reliable source)
        project_urls: Optional[dict[str, str]] = info.get("project_urls")
        if project_urls:
            for key in ["Repository", "Source", "Source Code", "GitHub", "Homepage"]:
                url = project_urls.get(key)
                if url and "github.com" in url:
                    return self._normalize_github_url(url)

        # Fall back to home_page
        home_page: Optional[str] = info.get("home_page")
        if home_page and "github.com" in home_page:
            return self._normalize_github_url(home_page)

        return None

    def _normalize_github_url(self, url: str) -> str:
        """Normalize GitHub URL by removing trailing slashes and .git suffix.

        Args:
            url: The GitHub URL to normalize.

        Returns:
            Normalized URL.
        """
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        return url

    async def _fetch_license_file(self, repo_url: str) -> Optional[str]:
        """Fetch LICENSE file content from GitHub raw URL.

        Tries multiple branch names (main, master, HEAD) and LICENSE
        file variants (LICENSE, LICENSE.txt, etc.) until one succeeds.

        Args:
            repo_url: The GitHub repository URL (e.g., https://github.com/owner/repo).

        Returns:
            LICENSE file content as string, or None if not found.
        """
        # Extract owner/repo from URL
        # https://github.com/owner/repo -> owner/repo
        parts = repo_url.split("github.com/")
        if len(parts) != 2:
            return None
        owner_repo = parts[1]

        async def do_fetch(client: httpx.AsyncClient) -> Optional[str]:
            for branch in BRANCHES:
                for license_file in LICENSE_FILES:
                    raw_url = (
                        f"https://raw.githubusercontent.com/{owner_repo}/"
                        f"{branch}/{license_file}"
                    )
                    try:
                        response = await client.get(
                            raw_url, timeout=httpx.Timeout(10.0)
                        )
                        if response.status_code == 200:
                            return response.text
                    except httpx.RequestError:
                        # Network error - try next combination
                        continue
            return None

        # Use provided client or create new one
        if self._client:
            return await do_fetch(self._client)

        async with httpx.AsyncClient() as new_client:
            return await do_fetch(new_client)

    def _identify_license(self, content: str) -> Optional[str]:
        """Identify license type from LICENSE file content.

        Uses pattern matching against common license text to identify
        the SPDX license identifier.

        Args:
            content: The LICENSE file content.

        Returns:
            SPDX license identifier (e.g., "MIT", "Apache-2.0"),
            or None if license cannot be identified.
        """
        content_lower = content.lower()

        # MIT License detection
        if (
            "mit license" in content_lower
            or "permission is hereby granted, free of charge" in content_lower
        ):
            return "MIT"

        # Apache 2.0 detection
        if "apache license" in content_lower and "version 2.0" in content_lower:
            return "Apache-2.0"

        # GPL detection (check version-specific patterns first)
        if "gnu general public license" in content_lower:
            if "version 3" in content_lower:
                return "GPL-3.0"
            if "version 2" in content_lower:
                return "GPL-2.0"

        # LGPL detection (must come after GPL to avoid false positives)
        if "gnu lesser general public license" in content_lower:
            if "version 3" in content_lower:
                return "LGPL-3.0"
            if "version 2" in content_lower:
                return "LGPL-2.0"

        # BSD detection
        if "bsd" in content_lower:
            if "2-clause" in content_lower or "two clause" in content_lower:
                return "BSD-2-Clause"
            if "3-clause" in content_lower or "three clause" in content_lower:
                return "BSD-3-Clause"
            # Default BSD variant (most BSD licenses are 3-clause style)
            return "BSD-3-Clause"

        # ISC License detection
        if "isc license" in content_lower:
            return "ISC"

        # MPL 2.0 detection
        if "mozilla public license" in content_lower and "2.0" in content_lower:
            return "MPL-2.0"

        # Unlicense detection
        if "unlicense" in content_lower or (
            "this is free and unencumbered software" in content_lower
        ):
            return "Unlicense"

        return None
