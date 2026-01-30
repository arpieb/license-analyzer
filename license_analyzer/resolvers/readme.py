"""README license mention resolver."""
import re
from typing import Any, Optional
from urllib.parse import unquote

import httpx

from license_analyzer.resolvers.base import BaseResolver

# Common README file names to try
README_FILES = ["README.md", "README.rst", "README.txt", "README", "readme.md"]

# Common branch names to try
BRANCHES = ["main", "master", "HEAD"]

# License aliases mapping common variations to SPDX identifiers
LICENSE_ALIASES: dict[str, str] = {
    "mit": "MIT",
    "apache 2.0": "Apache-2.0",
    "apache 2": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "apache2": "Apache-2.0",
    "gpl-3.0": "GPL-3.0",
    "gpl 3.0": "GPL-3.0",
    "gpl v3": "GPL-3.0",
    "gplv3": "GPL-3.0",
    "gpl-2.0": "GPL-2.0",
    "gpl 2.0": "GPL-2.0",
    "gpl v2": "GPL-2.0",
    "gplv2": "GPL-2.0",
    "lgpl-3.0": "LGPL-3.0",
    "lgpl 3.0": "LGPL-3.0",
    "lgpl-2.0": "LGPL-2.0",
    "lgpl 2.0": "LGPL-2.0",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "isc": "ISC",
    "mpl-2.0": "MPL-2.0",
    "mpl 2.0": "MPL-2.0",
    "unlicense": "Unlicense",
}


class ReadmeLicenseResolver(BaseResolver):
    """Resolver that extracts license mentions from README files.

    This resolver extracts the GitHub repository URL from PyPI metadata,
    fetches the README file content, and identifies license mentions
    using pattern matching.
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
        """Resolve license from README file content.

        Args:
            package_name: The package name to resolve.
            version: The package version (not used for README resolution).

        Returns:
            SPDX license identifier (e.g., "MIT", "Apache-2.0"),
            or None if license cannot be determined.
        """
        repo_url = self._extract_github_url()
        if not repo_url:
            return None

        readme_content = await self._fetch_readme_file(repo_url)
        if not readme_content:
            return None

        return self._extract_license_mention(readme_content)

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

    async def _fetch_readme_file(self, repo_url: str) -> Optional[str]:
        """Fetch README file content from GitHub raw URL.

        Tries multiple branch names (main, master, HEAD) and README
        file variants (README.md, README.rst, etc.) until one succeeds.

        Args:
            repo_url: The GitHub repository URL (e.g., https://github.com/owner/repo).

        Returns:
            README file content as string, or None if not found.
        """
        # Extract owner/repo from URL
        # https://github.com/owner/repo -> owner/repo
        parts = repo_url.split("github.com/")
        if len(parts) != 2:
            return None
        owner_repo = parts[1]

        async def do_fetch(client: httpx.AsyncClient) -> Optional[str]:
            for branch in BRANCHES:
                for readme_file in README_FILES:
                    raw_url = (
                        f"https://raw.githubusercontent.com/{owner_repo}/"
                        f"{branch}/{readme_file}"
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

    def _extract_license_mention(self, content: str) -> Optional[str]:
        """Extract license mention from README content.

        Uses pattern matching to detect common license mentions including
        SPDX identifiers, "Licensed under X" patterns, badge URLs, etc.

        Args:
            content: The README file content.

        Returns:
            SPDX license identifier (e.g., "MIT", "Apache-2.0"),
            or None if no license mention found.
        """
        if not content:
            return None

        # Try each pattern in order of reliability
        # 1. SPDX identifier (most reliable)
        spdx_match = re.search(
            r"SPDX-License-Identifier:\s*([A-Za-z0-9\-\.]+)", content, re.IGNORECASE
        )
        if spdx_match:
            return self._normalize_license_id(spdx_match.group(1))

        # 2. shields.io badge URL (reliable because it's explicit)
        badge_match = re.search(
            r"img\.shields\.io/badge/[Ll]icense-([A-Za-z0-9\-\.%]+)-", content
        )
        if badge_match:
            # URL decode the match (e.g., Apache%202.0 -> Apache 2.0)
            badge_license = unquote(badge_match.group(1))
            return self._normalize_license_id(badge_license)

        # 3. "License: X" pattern
        license_colon_match = re.search(
            r"[Ll]icense:\s*([A-Za-z0-9\-\.]+)", content
        )
        if license_colon_match:
            return self._normalize_license_id(license_colon_match.group(1))

        # 4. Markdown license link: [MIT License](LICENSE)
        markdown_link_match = re.search(
            r"\[([A-Za-z0-9\-\.\s]+?)\s*[Ll]icense\]\s*\(", content
        )
        if markdown_link_match:
            return self._normalize_license_id(markdown_link_match.group(1))

        # 5. "Licensed under X" pattern (common but can be ambiguous)
        # Match known license names to avoid false positives like "Licensed under terms"
        licensed_under_match = re.search(
            r"licensed\s+under\s+(?:the\s+)?"
            r"(MIT|Apache(?:\s+2\.0|\-2\.0)?|GPL(?:\-?[23]\.0)?|LGPL(?:\-?[23]\.0)?|"
            r"BSD(?:\-?[23]\-Clause)?|ISC|MPL(?:\-?2\.0)?|Unlicense)"
            r"(?:\s+license)?",
            content,
            re.IGNORECASE,
        )
        if licensed_under_match:
            return self._normalize_license_id(licensed_under_match.group(1))

        return None

    def _normalize_license_id(self, raw_license: str) -> Optional[str]:
        """Normalize a raw license string to SPDX identifier.

        Args:
            raw_license: The raw license string from README.

        Returns:
            SPDX license identifier, or None if unknown.
        """
        # Clean up the raw string
        cleaned = raw_license.strip().lower()

        # Direct match in aliases
        if cleaned in LICENSE_ALIASES:
            return LICENSE_ALIASES[cleaned]

        # Check if it's already a valid SPDX identifier (case-insensitive)
        # Common SPDX identifiers we recognize
        known_spdx = {
            "mit": "MIT",
            "apache-2.0": "Apache-2.0",
            "gpl-3.0": "GPL-3.0",
            "gpl-2.0": "GPL-2.0",
            "lgpl-3.0": "LGPL-3.0",
            "lgpl-2.0": "LGPL-2.0",
            "bsd-3-clause": "BSD-3-Clause",
            "bsd-2-clause": "BSD-2-Clause",
            "isc": "ISC",
            "mpl-2.0": "MPL-2.0",
            "unlicense": "Unlicense",
        }

        if cleaned in known_spdx:
            return known_spdx[cleaned]

        # Try partial matching for common variations
        if "mit" in cleaned:
            return "MIT"
        if "apache" in cleaned and ("2.0" in cleaned or "2" in cleaned):
            return "Apache-2.0"

        # GPL/LGPL detection - check for specific variants first
        if "lgpl" in cleaned or "lesser general public" in cleaned:
            # Check for version-specific patterns
            if "3.0-or-later" in cleaned or "3-or-later" in cleaned:
                return "LGPL-3.0-or-later"
            if "3.0-only" in cleaned or "3-only" in cleaned:
                return "LGPL-3.0-only"
            if "3" in cleaned:
                return "LGPL-3.0"
            if "2.1" in cleaned:
                return "LGPL-2.1"
            if "2.0-or-later" in cleaned or "2-or-later" in cleaned:
                return "LGPL-2.0-or-later"
            if "2.0-only" in cleaned or "2-only" in cleaned:
                return "LGPL-2.0-only"
            if "2" in cleaned:
                return "LGPL-2.0"
        elif "gpl" in cleaned:
            # Check for version-specific patterns
            if "3.0-or-later" in cleaned or "3-or-later" in cleaned:
                return "GPL-3.0-or-later"
            if "3.0-only" in cleaned or "3-only" in cleaned:
                return "GPL-3.0-only"
            if "3" in cleaned:
                return "GPL-3.0"
            if "2.0-or-later" in cleaned or "2-or-later" in cleaned:
                return "GPL-2.0-or-later"
            if "2.0-only" in cleaned or "2-only" in cleaned:
                return "GPL-2.0-only"
            if "2" in cleaned:
                return "GPL-2.0"

        if "bsd" in cleaned:
            if "2" in cleaned:
                return "BSD-2-Clause"
            return "BSD-3-Clause"
        if "isc" in cleaned:
            return "ISC"
        if "mpl" in cleaned and "2" in cleaned:
            return "MPL-2.0"
        if "unlicense" in cleaned:
            return "Unlicense"

        return None
