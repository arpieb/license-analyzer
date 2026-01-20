"""Tests for GitHub LICENSE file resolver."""
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from license_analyzer.resolvers.github import (
    BRANCHES,
    LICENSE_FILES,
    GitHubLicenseResolver,
)


class TestGitHubLicenseResolver:
    """Tests for GitHubLicenseResolver."""

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

    @pytest.fixture
    def mit_license_content(self) -> str:
        """MIT license text content."""
        return """MIT License

Copyright (c) 2024 Example

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

    @pytest.fixture
    def apache_license_content(self) -> str:
        """Apache 2.0 license text content."""
        return """
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
   ..."""

    @pytest.fixture
    def gpl3_license_content(self) -> str:
        """GPL-3.0 license text content."""
        return """
                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 ..."""

    @pytest.fixture
    def bsd3_license_content(self) -> str:
        """BSD-3-Clause license text content."""
        return """BSD 3-Clause License

Copyright (c) 2024, Example
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
..."""

    # AC #1: Successful license resolution from GitHub
    @pytest.mark.asyncio
    async def test_resolve_returns_mit_license_from_github(
        self, pypi_metadata_with_github: dict[str, Any], mit_license_content: str
    ) -> None:
        """Test successful MIT license resolution from GitHub."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_github)

        with patch.object(
            resolver, "_fetch_license_file", return_value=mit_license_content
        ):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result == "MIT"

    @pytest.mark.asyncio
    async def test_resolve_returns_apache_license(
        self, pypi_metadata_with_github: dict[str, Any], apache_license_content: str
    ) -> None:
        """Test successful Apache-2.0 license resolution."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_github)

        with patch.object(
            resolver, "_fetch_license_file", return_value=apache_license_content
        ):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result == "Apache-2.0"

    @pytest.mark.asyncio
    async def test_resolve_returns_gpl3_license(
        self, pypi_metadata_with_github: dict[str, Any], gpl3_license_content: str
    ) -> None:
        """Test successful GPL-3.0 license resolution."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_github)

        with patch.object(
            resolver, "_fetch_license_file", return_value=gpl3_license_content
        ):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result == "GPL-3.0"

    @pytest.mark.asyncio
    async def test_resolve_returns_bsd3_license(
        self, pypi_metadata_with_github: dict[str, Any], bsd3_license_content: str
    ) -> None:
        """Test successful BSD-3-Clause license resolution."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_github)

        with patch.object(
            resolver, "_fetch_license_file", return_value=bsd3_license_content
        ):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result == "BSD-3-Clause"

    # AC #2: No repository URL returns None
    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_no_repo_url(
        self, pypi_metadata_no_github: dict[str, Any]
    ) -> None:
        """Test returns None when no GitHub URL in metadata."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_no_github)
        result = await resolver.resolve("example-pkg", "1.0.0")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_no_metadata(self) -> None:
        """Test returns None when no metadata provided."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        result = await resolver.resolve("example-pkg", "1.0.0")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_empty_metadata(self) -> None:
        """Test returns None when empty metadata provided."""
        resolver = GitHubLicenseResolver(pypi_metadata={})
        result = await resolver.resolve("example-pkg", "1.0.0")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_empty_info(self) -> None:
        """Test returns None when info is empty."""
        resolver = GitHubLicenseResolver(pypi_metadata={"info": {}})
        result = await resolver.resolve("example-pkg", "1.0.0")
        assert result is None

    # AC #3: 404 and network errors return None
    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_license_file_not_found(
        self, pypi_metadata_with_github: dict[str, Any]
    ) -> None:
        """Test returns None when LICENSE file not found (404)."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_github)

        with patch.object(resolver, "_fetch_license_file", return_value=None):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_unidentified_license(
        self, pypi_metadata_with_github: dict[str, Any]
    ) -> None:
        """Test returns None when license text cannot be identified."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_github)

        unknown_license = "Some custom proprietary license text."

        with patch.object(
            resolver, "_fetch_license_file", return_value=unknown_license
        ):
            result = await resolver.resolve("example-pkg", "1.0.0")

        assert result is None

    # URL extraction tests
    def test_extract_github_url_from_repository(
        self, pypi_metadata_with_github: dict[str, Any]
    ) -> None:
        """Test extracting GitHub URL from Repository project_url."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_github)
        result = resolver._extract_github_url()
        assert result == "https://github.com/owner/repo"

    def test_extract_github_url_from_source(
        self, pypi_metadata_with_source: dict[str, Any]
    ) -> None:
        """Test extracting GitHub URL from Source project_url."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_source)
        result = resolver._extract_github_url()
        assert result == "https://github.com/owner/repo"

    def test_extract_github_url_from_home_page(
        self, pypi_metadata_with_homepage: dict[str, Any]
    ) -> None:
        """Test extracting GitHub URL from home_page."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_with_homepage)
        result = resolver._extract_github_url()
        assert result == "https://github.com/owner/repo"

    def test_extract_github_url_returns_none_for_non_github(
        self, pypi_metadata_no_github: dict[str, Any]
    ) -> None:
        """Test returns None when no GitHub URL found."""
        resolver = GitHubLicenseResolver(pypi_metadata=pypi_metadata_no_github)
        result = resolver._extract_github_url()
        assert result is None

    def test_normalize_github_url_removes_trailing_slash(self) -> None:
        """Test normalizing GitHub URL removes trailing slash."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        result = resolver._normalize_github_url("https://github.com/owner/repo/")
        assert result == "https://github.com/owner/repo"

    def test_normalize_github_url_removes_git_suffix(self) -> None:
        """Test normalizing GitHub URL removes .git suffix."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        result = resolver._normalize_github_url("https://github.com/owner/repo.git")
        assert result == "https://github.com/owner/repo"

    # License identification tests
    def test_identify_mit_license(self, mit_license_content: str) -> None:
        """Test identifying MIT license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        result = resolver._identify_license(mit_license_content)
        assert result == "MIT"

    def test_identify_apache_license(self, apache_license_content: str) -> None:
        """Test identifying Apache-2.0 license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        result = resolver._identify_license(apache_license_content)
        assert result == "Apache-2.0"

    def test_identify_gpl3_license(self, gpl3_license_content: str) -> None:
        """Test identifying GPL-3.0 license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        result = resolver._identify_license(gpl3_license_content)
        assert result == "GPL-3.0"

    def test_identify_gpl2_license(self) -> None:
        """Test identifying GPL-2.0 license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        gpl2_content = "GNU GENERAL PUBLIC LICENSE Version 2, June 1991"
        result = resolver._identify_license(gpl2_content)
        assert result == "GPL-2.0"

    def test_identify_bsd3_license(self, bsd3_license_content: str) -> None:
        """Test identifying BSD-3-Clause license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        result = resolver._identify_license(bsd3_license_content)
        assert result == "BSD-3-Clause"

    def test_identify_bsd2_license(self) -> None:
        """Test identifying BSD-2-Clause license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        bsd2_content = "BSD 2-Clause License\n\nRedistribution and use..."
        result = resolver._identify_license(bsd2_content)
        assert result == "BSD-2-Clause"

    def test_identify_isc_license(self) -> None:
        """Test identifying ISC license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        isc_content = "ISC License\n\nCopyright (c) 2024..."
        result = resolver._identify_license(isc_content)
        assert result == "ISC"

    def test_identify_mpl2_license(self) -> None:
        """Test identifying MPL-2.0 license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        mpl_content = "Mozilla Public License 2.0\n\n..."
        result = resolver._identify_license(mpl_content)
        assert result == "MPL-2.0"

    def test_identify_lgpl3_license(self) -> None:
        """Test identifying LGPL-3.0 license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        lgpl3_content = "GNU LESSER GENERAL PUBLIC LICENSE Version 3, 29 June 2007"
        result = resolver._identify_license(lgpl3_content)
        assert result == "LGPL-3.0"

    def test_identify_lgpl2_license(self) -> None:
        """Test identifying LGPL-2.0 license."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        lgpl2_content = "GNU Lesser General Public License Version 2.1, February 1999"
        result = resolver._identify_license(lgpl2_content)
        assert result == "LGPL-2.0"

    def test_identify_unlicense(self) -> None:
        """Test identifying Unlicense."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        unlicense_content = (
            "This is free and unencumbered software released into the public domain."
        )
        result = resolver._identify_license(unlicense_content)
        assert result == "Unlicense"

    def test_identify_unlicense_by_name(self) -> None:
        """Test identifying Unlicense by name."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        unlicense_content = "UNLICENSE\n\nAnyone is free to copy..."
        result = resolver._identify_license(unlicense_content)
        assert result == "Unlicense"

    def test_identify_unknown_license_returns_none(self) -> None:
        """Test unknown license returns None."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)
        result = resolver._identify_license("Custom proprietary license")
        assert result is None

    # Fetch license file tests (with mocked HTTP)
    @pytest.mark.asyncio
    async def test_fetch_license_file_success(self) -> None:
        """Test successful LICENSE file fetch."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "MIT License content"

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await resolver._fetch_license_file("https://github.com/owner/repo")

        assert result == "MIT License content"

    @pytest.mark.asyncio
    async def test_fetch_license_file_404_returns_none(self) -> None:
        """Test 404 response returns None."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)

        mock_response = AsyncMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await resolver._fetch_license_file("https://github.com/owner/repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_license_file_network_error_returns_none(self) -> None:
        """Test network error returns None."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.RequestError("Connection failed")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await resolver._fetch_license_file("https://github.com/owner/repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_license_file_invalid_url_returns_none(self) -> None:
        """Test invalid URL returns None."""
        resolver = GitHubLicenseResolver(pypi_metadata=None)

        result = await resolver._fetch_license_file("https://not-github.com/owner/repo")

        assert result is None

    # Constants tests
    def test_license_files_constant_exists(self) -> None:
        """Test LICENSE_FILES constant contains expected values."""
        assert "LICENSE" in LICENSE_FILES
        assert "LICENSE.txt" in LICENSE_FILES
        assert "LICENSE.md" in LICENSE_FILES
        assert "LICENCE" in LICENSE_FILES
        assert "COPYING" in LICENSE_FILES

    def test_branches_constant_exists(self) -> None:
        """Test BRANCHES constant contains expected values."""
        assert "main" in BRANCHES
        assert "master" in BRANCHES
