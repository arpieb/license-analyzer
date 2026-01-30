"""Tests for README license mention resolver."""
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from license_analyzer.resolvers.readme import (
    BRANCHES,
    README_FILES,
    ReadmeLicenseResolver,
)


class TestReadmeLicenseResolver:
    """Tests for ReadmeLicenseResolver."""

    @pytest.fixture
    def pypi_metadata_with_github(self) -> dict[str, Any]:
        """PyPI metadata with GitHub repository URL."""
        return {
            "info": {
                "project_urls": {"Repository": "https://github.com/owner/repo"}
            }
        }

    @pytest.fixture
    def pypi_metadata_with_source(self) -> dict[str, Any]:
        """PyPI metadata with Source URL."""
        return {
            "info": {
                "project_urls": {"Source": "https://github.com/owner/repo"}
            }
        }

    @pytest.fixture
    def pypi_metadata_with_homepage(self) -> dict[str, Any]:
        """PyPI metadata with home_page pointing to GitHub."""
        return {"info": {"home_page": "https://github.com/owner/repo"}}

    @pytest.fixture
    def pypi_metadata_no_github(self) -> dict[str, Any]:
        """PyPI metadata without GitHub URL."""
        return {
            "info": {
                "project_urls": {"Homepage": "https://example.com"},
                "home_page": "https://example.com",
            }
        }

    # ==========================================================================
    # Task 1 Tests: Basic class structure and README fetching
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_no_metadata(self) -> None:
        """Test returns None when no metadata provided."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        result = await resolver.resolve("example-pkg", "1.0.0")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_empty_metadata(self) -> None:
        """Test returns None when empty metadata provided."""
        resolver = ReadmeLicenseResolver(pypi_metadata={})
        result = await resolver.resolve("example-pkg", "1.0.0")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_no_github_url(
        self, pypi_metadata_no_github: dict[str, Any]
    ) -> None:
        """Test returns None when no GitHub URL in metadata."""
        resolver = ReadmeLicenseResolver(pypi_metadata=pypi_metadata_no_github)
        result = await resolver.resolve("example-pkg", "1.0.0")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_readme_not_found(
        self, pypi_metadata_with_github: dict[str, Any]
    ) -> None:
        """Test returns None when README file not found."""
        resolver = ReadmeLicenseResolver(pypi_metadata=pypi_metadata_with_github)

        with patch.object(resolver, "_fetch_readme_file", return_value=None):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result is None

    # URL extraction tests
    def test_extract_github_url_from_repository(
        self, pypi_metadata_with_github: dict[str, Any]
    ) -> None:
        """Test extracting GitHub URL from Repository project_url."""
        resolver = ReadmeLicenseResolver(pypi_metadata=pypi_metadata_with_github)
        result = resolver._extract_github_url()
        assert result == "https://github.com/owner/repo"

    def test_extract_github_url_from_source(
        self, pypi_metadata_with_source: dict[str, Any]
    ) -> None:
        """Test extracting GitHub URL from Source project_url."""
        resolver = ReadmeLicenseResolver(pypi_metadata=pypi_metadata_with_source)
        result = resolver._extract_github_url()
        assert result == "https://github.com/owner/repo"

    def test_extract_github_url_from_home_page(
        self, pypi_metadata_with_homepage: dict[str, Any]
    ) -> None:
        """Test extracting GitHub URL from home_page."""
        resolver = ReadmeLicenseResolver(pypi_metadata=pypi_metadata_with_homepage)
        result = resolver._extract_github_url()
        assert result == "https://github.com/owner/repo"

    def test_extract_github_url_returns_none_for_non_github(
        self, pypi_metadata_no_github: dict[str, Any]
    ) -> None:
        """Test returns None when no GitHub URL found."""
        resolver = ReadmeLicenseResolver(pypi_metadata=pypi_metadata_no_github)
        result = resolver._extract_github_url()
        assert result is None

    def test_normalize_github_url_removes_trailing_slash(self) -> None:
        """Test normalizing GitHub URL removes trailing slash."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        result = resolver._normalize_github_url("https://github.com/owner/repo/")
        assert result == "https://github.com/owner/repo"

    def test_normalize_github_url_removes_git_suffix(self) -> None:
        """Test normalizing GitHub URL removes .git suffix."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        result = resolver._normalize_github_url("https://github.com/owner/repo.git")
        assert result == "https://github.com/owner/repo"

    # Fetch README file tests (with mocked HTTP)
    @pytest.mark.asyncio
    async def test_fetch_readme_file_success(self) -> None:
        """Test successful README file fetch."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "# My Package\n\nLicensed under MIT"

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await resolver._fetch_readme_file("https://github.com/owner/repo")

        assert result == "# My Package\n\nLicensed under MIT"

    @pytest.mark.asyncio
    async def test_fetch_readme_file_404_returns_none(self) -> None:
        """Test 404 response returns None."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)

        mock_response = AsyncMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await resolver._fetch_readme_file("https://github.com/owner/repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_readme_file_network_error_returns_none(self) -> None:
        """Test network error returns None."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.RequestError("Connection failed")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await resolver._fetch_readme_file("https://github.com/owner/repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_readme_file_invalid_url_returns_none(self) -> None:
        """Test invalid URL returns None."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)

        result = await resolver._fetch_readme_file("https://not-github.com/owner/repo")

        assert result is None

    # Constants tests
    def test_readme_files_constant_exists(self) -> None:
        """Test README_FILES constant contains expected values."""
        assert "README.md" in README_FILES
        assert "README.rst" in README_FILES
        assert "README.txt" in README_FILES
        assert "README" in README_FILES

    def test_branches_constant_exists(self) -> None:
        """Test BRANCHES constant contains expected values."""
        assert "main" in BRANCHES
        assert "master" in BRANCHES

    # ==========================================================================
    # Task 2 Tests: License pattern matching
    # ==========================================================================

    # SPDX identifier detection tests
    def test_extract_license_mention_spdx_identifier(self) -> None:
        """Test detecting SPDX-License-Identifier."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "# Package\n\nSPDX-License-Identifier: MIT\n"
        result = resolver._extract_license_mention(readme)
        assert result == "MIT"

    def test_extract_license_mention_spdx_apache(self) -> None:
        """Test detecting SPDX identifier for Apache-2.0."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "SPDX-License-Identifier: Apache-2.0\n"
        result = resolver._extract_license_mention(readme)
        assert result == "Apache-2.0"

    # "Licensed under X" pattern tests
    def test_extract_license_mention_licensed_under_mit(self) -> None:
        """Test detecting 'Licensed under MIT'."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "# Package\n\nThis project is licensed under the MIT License."
        result = resolver._extract_license_mention(readme)
        assert result == "MIT"

    def test_extract_license_mention_licensed_under_apache(self) -> None:
        """Test detecting 'Licensed under Apache 2.0'."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "Licensed under Apache 2.0"
        result = resolver._extract_license_mention(readme)
        assert result == "Apache-2.0"

    def test_extract_license_mention_licensed_under_gpl(self) -> None:
        """Test detecting 'Licensed under GPL-3.0'."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "This software is licensed under GPL-3.0."
        result = resolver._extract_license_mention(readme)
        assert result == "GPL-3.0"

    # "License: X" pattern tests
    def test_extract_license_mention_license_colon_mit(self) -> None:
        """Test detecting 'License: MIT'."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "# Package\n\nLicense: MIT\n"
        result = resolver._extract_license_mention(readme)
        assert result == "MIT"

    def test_extract_license_mention_license_colon_bsd(self) -> None:
        """Test detecting 'License: BSD-3-Clause'."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "License: BSD-3-Clause"
        result = resolver._extract_license_mention(readme)
        assert result == "BSD-3-Clause"

    # Badge URL detection tests
    def test_extract_license_mention_shields_badge(self) -> None:
        """Test detecting shields.io license badge."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "[![License](https://img.shields.io/badge/License-MIT-blue.svg)]"
        result = resolver._extract_license_mention(readme)
        assert result == "MIT"

    def test_extract_license_mention_shields_badge_apache(self) -> None:
        """Test detecting shields.io Apache badge."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "![License](https://img.shields.io/badge/license-Apache%202.0-green)"
        result = resolver._extract_license_mention(readme)
        assert result == "Apache-2.0"

    # Markdown link detection tests
    def test_extract_license_mention_markdown_link(self) -> None:
        """Test detecting markdown license link."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "See the [MIT License](LICENSE) for details."
        result = resolver._extract_license_mention(readme)
        assert result == "MIT"

    def test_extract_license_mention_markdown_link_apache(self) -> None:
        """Test detecting Apache license markdown link."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "Released under the [Apache 2.0 License](LICENSE.txt)"
        result = resolver._extract_license_mention(readme)
        assert result == "Apache-2.0"

    # Case insensitivity tests
    def test_extract_license_mention_case_insensitive(self) -> None:
        """Test case-insensitive matching."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "licensed UNDER mit"
        result = resolver._extract_license_mention(readme)
        assert result == "MIT"

    # No license mention tests
    def test_extract_license_mention_no_license_returns_none(self) -> None:
        """Test returns None when no license mention found."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "# My Package\n\nA great package for doing things."
        result = resolver._extract_license_mention(readme)
        assert result is None

    def test_extract_license_mention_empty_readme_returns_none(self) -> None:
        """Test returns None for empty README."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        result = resolver._extract_license_mention("")
        assert result is None

    # Additional license types
    def test_extract_license_mention_isc(self) -> None:
        """Test detecting ISC license."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "This project is licensed under the ISC license."
        result = resolver._extract_license_mention(readme)
        assert result == "ISC"

    def test_extract_license_mention_unlicense(self) -> None:
        """Test detecting Unlicense."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "License: Unlicense"
        result = resolver._extract_license_mention(readme)
        assert result == "Unlicense"

    def test_extract_license_mention_mpl(self) -> None:
        """Test detecting MPL-2.0."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        readme = "Licensed under MPL-2.0"
        result = resolver._extract_license_mention(readme)
        assert result == "MPL-2.0"

    # End-to-end resolution tests
    @pytest.mark.asyncio
    async def test_resolve_extracts_license_from_readme(
        self, pypi_metadata_with_github: dict[str, Any]
    ) -> None:
        """Test successful license extraction from README."""
        resolver = ReadmeLicenseResolver(pypi_metadata=pypi_metadata_with_github)
        readme_content = "# My Package\n\nLicensed under the MIT License."

        with patch.object(
            resolver, "_fetch_readme_file", return_value=readme_content
        ):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result == "MIT"

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_no_license_mention(
        self, pypi_metadata_with_github: dict[str, Any]
    ) -> None:
        """Test returns None when README has no license mention."""
        resolver = ReadmeLicenseResolver(pypi_metadata=pypi_metadata_with_github)
        readme_no_license = "# My Package\n\nJust a package.\n"

        with patch.object(
            resolver, "_fetch_readme_file", return_value=readme_no_license
        ):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result is None

    # ==========================================================================
    # Additional Tests: Edge cases (from code review LOW issues)
    # ==========================================================================

    def test_normalize_license_id_returns_none_for_unknown(self) -> None:
        """Test _normalize_license_id returns None for unknown license strings."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        # Unknown/unrecognized license strings should return None
        assert resolver._normalize_license_id("proprietary") is None
        assert resolver._normalize_license_id("custom-license") is None
        assert resolver._normalize_license_id("unknown") is None
        assert resolver._normalize_license_id("ACME Corp License") is None

    def test_normalize_license_id_gpl_variants(self) -> None:
        """Test _normalize_license_id handles GPL/LGPL variants correctly."""
        resolver = ReadmeLicenseResolver(pypi_metadata=None)
        # GPL variants
        assert resolver._normalize_license_id("GPL-3.0-only") == "GPL-3.0-only"
        assert resolver._normalize_license_id("GPL-3.0-or-later") == "GPL-3.0-or-later"
        assert resolver._normalize_license_id("GPL-2.0-only") == "GPL-2.0-only"
        assert resolver._normalize_license_id("GPL-2.0-or-later") == "GPL-2.0-or-later"
        # LGPL variants
        assert resolver._normalize_license_id("LGPL-3.0-only") == "LGPL-3.0-only"
        result = resolver._normalize_license_id("LGPL-3.0-or-later")
        assert result == "LGPL-3.0-or-later"
        assert resolver._normalize_license_id("LGPL-2.1") == "LGPL-2.1"
        assert resolver._normalize_license_id("LGPL-2.0-only") == "LGPL-2.0-only"

    @pytest.mark.asyncio
    async def test_fetch_readme_file_uses_provided_client(self) -> None:
        """Test _fetch_readme_file uses provided client instead of creating new one."""
        # Create mock client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "# README\n\nLicense: MIT"

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_response

        # Create resolver with provided client
        resolver = ReadmeLicenseResolver(pypi_metadata=None, client=mock_client)

        # Fetch should use provided client
        result = await resolver._fetch_readme_file("https://github.com/owner/repo")

        assert result == "# README\n\nLicense: MIT"
        # Verify our mock client was called
        mock_client.get.assert_called()
        # Verify it was called with the expected URL pattern
        call_args = mock_client.get.call_args
        assert "raw.githubusercontent.com" in call_args[0][0]
