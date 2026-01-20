"""Tests for scanner module."""
from io import StringIO
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from license_analyzer.exceptions import NetworkError
from license_analyzer.models.scan import PackageLicense
from license_analyzer.scanner import discover_packages, resolve_licenses


class TestDiscoverPackages:
    """Tests for discover_packages function."""

    def test_discovers_installed_packages(self) -> None:
        """Test that installed packages are discovered."""
        mock_dist1 = MagicMock()
        mock_dist1.metadata = {"Name": "click", "Version": "8.1.0"}

        mock_dist2 = MagicMock()
        mock_dist2.metadata = {"Name": "pydantic", "Version": "2.0.0"}

        with patch(
            "license_analyzer.scanner.distributions",
            return_value=[mock_dist1, mock_dist2],
        ):
            packages = discover_packages()

        assert len(packages) == 2
        assert packages[0].name == "click"
        assert packages[0].version == "8.1.0"
        assert packages[0].license is None
        assert packages[1].name == "pydantic"
        assert packages[1].version == "2.0.0"

    def test_empty_environment(self) -> None:
        """Test handling of empty environment."""
        with patch("license_analyzer.scanner.distributions", return_value=[]):
            packages = discover_packages()

        assert packages == []

    def test_returns_package_license_objects(self) -> None:
        """Test that PackageLicense objects are returned."""
        mock_dist = MagicMock()
        mock_dist.metadata = {"Name": "test-pkg", "Version": "1.0.0"}

        with patch("license_analyzer.scanner.distributions", return_value=[mock_dist]):
            packages = discover_packages()

        assert isinstance(packages[0], PackageLicense)

    def test_skips_packages_with_missing_name(self) -> None:
        """Test that packages with missing name are skipped."""
        mock_dist = MagicMock()
        mock_dist.metadata = {"Version": "1.0.0"}  # No Name

        with patch("license_analyzer.scanner.distributions", return_value=[mock_dist]):
            packages = discover_packages()

        assert packages == []

    def test_skips_packages_with_missing_version(self) -> None:
        """Test that packages with missing version are skipped."""
        mock_dist = MagicMock()
        mock_dist.metadata = {"Name": "test-pkg"}  # No Version

        with patch("license_analyzer.scanner.distributions", return_value=[mock_dist]):
            packages = discover_packages()

        assert packages == []

    def test_license_is_none_for_discovered_packages(self) -> None:
        """Test that license field is None for all discovered packages."""
        mock_dist = MagicMock()
        mock_dist.metadata = {"Name": "test-pkg", "Version": "1.0.0"}

        with patch("license_analyzer.scanner.distributions", return_value=[mock_dist]):
            packages = discover_packages()

        assert packages[0].license is None

    def test_packages_sorted_by_name(self) -> None:
        """Test that packages are returned sorted by name for deterministic output."""
        mock_dist_z = MagicMock()
        mock_dist_z.metadata = {"Name": "zebra", "Version": "1.0.0"}

        mock_dist_a = MagicMock()
        mock_dist_a.metadata = {"Name": "apple", "Version": "2.0.0"}

        mock_dist_m = MagicMock()
        mock_dist_m.metadata = {"Name": "Mango", "Version": "3.0.0"}

        # Provide in unsorted order
        with patch(
            "license_analyzer.scanner.distributions",
            return_value=[mock_dist_z, mock_dist_a, mock_dist_m],
        ):
            packages = discover_packages()

        # Should be sorted case-insensitively by name
        assert len(packages) == 3
        assert packages[0].name == "apple"
        assert packages[1].name == "Mango"
        assert packages[2].name == "zebra"


class TestResolveLicenses:
    """Tests for resolve_licenses function."""

    @pytest.fixture
    def mock_pypi_metadata(self) -> dict[str, Any]:
        """Mock PyPI metadata response."""
        return {
            "info": {
                "license": "MIT",
                "project_urls": {"Repository": "https://github.com/owner/repo"},
            }
        }

    @pytest.mark.asyncio
    async def test_resolves_licenses_for_packages(self) -> None:
        """Test that licenses are resolved for packages."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
            PackageLicense(name="pydantic", version="2.0.0", license=None),
        ]

        # Mock fetch_pypi_metadata to return metadata
        async def mock_fetch(name: str, client: Any = None) -> dict[str, Any]:
            return {"info": {"license": "BSD-3-Clause" if name == "click" else "MIT"}}

        with patch(
            "license_analyzer.scanner.fetch_pypi_metadata",
            side_effect=mock_fetch,
        ):
            result = await resolve_licenses(packages)

        assert len(result) == 2
        assert result[0].name == "click"
        assert result[0].license == "BSD-3-Clause"
        assert result[1].name == "pydantic"
        assert result[1].license == "MIT"

    @pytest.mark.asyncio
    async def test_handles_network_error_gracefully(self) -> None:
        """Test that NetworkError returns package with None license."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
            PackageLicense(name="failing-pkg", version="1.0.0", license=None),
        ]

        async def mock_fetch(
            name: str, client: Any = None
        ) -> Optional[dict[str, Any]]:
            if name == "failing-pkg":
                raise NetworkError("Connection failed")
            return {"info": {"license": "MIT"}}

        with patch(
            "license_analyzer.scanner.fetch_pypi_metadata",
            side_effect=mock_fetch,
        ):
            result = await resolve_licenses(packages)

        assert len(result) == 2
        # First package resolved successfully
        assert result[0].name == "click"
        assert result[0].license == "MIT"
        # Second package failed but still included with None license
        assert result[1].name == "failing-pkg"
        assert result[1].license is None

    @pytest.mark.asyncio
    async def test_reraises_unexpected_exceptions(self) -> None:
        """Test that unexpected exceptions are re-raised."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
        ]

        async def mock_fetch(
            name: str, client: Any = None
        ) -> Optional[dict[str, Any]]:
            raise ValueError("Unexpected bug")

        with (
            patch(
                "license_analyzer.scanner.fetch_pypi_metadata",
                side_effect=mock_fetch,
            ),
            pytest.raises(ValueError, match="Unexpected bug"),
        ):
            await resolve_licenses(packages)

    @pytest.mark.asyncio
    async def test_returns_sorted_results(self) -> None:
        """Test that results are sorted by name."""
        packages = [
            PackageLicense(name="zebra", version="1.0.0", license=None),
            PackageLicense(name="apple", version="2.0.0", license=None),
        ]

        async def mock_fetch(name: str, client: Any = None) -> dict[str, Any]:
            return {"info": {"license": "MIT" if name == "zebra" else "Apache-2.0"}}

        with patch(
            "license_analyzer.scanner.fetch_pypi_metadata",
            side_effect=mock_fetch,
        ):
            result = await resolve_licenses(packages)

        assert result[0].name == "apple"
        assert result[1].name == "zebra"

    @pytest.mark.asyncio
    async def test_handles_none_license_from_pypi(self) -> None:
        """Test that None license from PyPI triggers GitHub resolver."""
        packages = [
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]

        # PyPI has no license but has GitHub URL
        pypi_metadata = {
            "info": {
                "license": None,
                "project_urls": {"Repository": "https://github.com/owner/repo"},
            }
        }

        async def mock_fetch(
            name: str, client: Any = None
        ) -> Optional[dict[str, Any]]:
            return pypi_metadata

        # Mock GitHub resolver to return None (no LICENSE file found)
        mock_github_resolver = AsyncMock()
        mock_github_resolver.resolve.return_value = None

        with (
            patch(
                "license_analyzer.scanner.fetch_pypi_metadata",
                side_effect=mock_fetch,
            ),
            patch(
                "license_analyzer.scanner.GitHubLicenseResolver",
                return_value=mock_github_resolver,
            ),
        ):
            result = await resolve_licenses(packages)

        assert len(result) == 1
        assert result[0].license is None
        # Verify GitHub resolver was called
        mock_github_resolver.resolve.assert_called_once()

    @pytest.mark.asyncio
    async def test_github_fallback_when_pypi_has_no_license(self) -> None:
        """Test that GitHub resolver is used when PyPI returns no license."""
        packages = [
            PackageLicense(name="github-pkg", version="1.0.0", license=None),
        ]

        # PyPI has no license but has GitHub URL
        pypi_metadata = {
            "info": {
                "license": None,
                "project_urls": {"Repository": "https://github.com/owner/repo"},
            }
        }

        async def mock_fetch(
            name: str, client: Any = None
        ) -> Optional[dict[str, Any]]:
            return pypi_metadata

        # Mock GitHub resolver to return MIT from LICENSE file
        mock_github_resolver = AsyncMock()
        mock_github_resolver.resolve.return_value = "MIT"

        with (
            patch(
                "license_analyzer.scanner.fetch_pypi_metadata",
                side_effect=mock_fetch,
            ),
            patch(
                "license_analyzer.scanner.GitHubLicenseResolver",
                return_value=mock_github_resolver,
            ),
        ):
            result = await resolve_licenses(packages)

        assert len(result) == 1
        assert result[0].license == "MIT"

    @pytest.mark.asyncio
    async def test_pypi_license_takes_precedence_over_github(self) -> None:
        """Test that PyPI license is used when available, GitHub not called."""
        packages = [
            PackageLicense(name="pypi-pkg", version="1.0.0", license=None),
        ]

        # PyPI has license
        pypi_metadata = {
            "info": {
                "license": "Apache-2.0",
                "project_urls": {"Repository": "https://github.com/owner/repo"},
            }
        }

        async def mock_fetch(
            name: str, client: Any = None
        ) -> Optional[dict[str, Any]]:
            return pypi_metadata

        # Mock GitHub resolver (should NOT be called)
        mock_github_resolver = AsyncMock()
        mock_github_resolver.resolve.return_value = "MIT"

        with (
            patch(
                "license_analyzer.scanner.fetch_pypi_metadata",
                side_effect=mock_fetch,
            ),
            patch(
                "license_analyzer.scanner.GitHubLicenseResolver",
                return_value=mock_github_resolver,
            ),
        ):
            result = await resolve_licenses(packages)

        assert len(result) == 1
        assert result[0].license == "Apache-2.0"
        # GitHub resolver should NOT be called since PyPI had license
        mock_github_resolver.resolve.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolves_with_progress_indicator(self) -> None:
        """Test that progress indicator works when console is provided."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
            PackageLicense(name="pydantic", version="2.0.0", license=None),
        ]

        async def mock_fetch(name: str, client: Any = None) -> dict[str, Any]:
            return {"info": {"license": "BSD-3-Clause" if name == "click" else "MIT"}}

        # Create a console to capture output
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch(
            "license_analyzer.scanner.fetch_pypi_metadata",
            side_effect=mock_fetch,
        ):
            result = await resolve_licenses(
                packages, console=console, show_progress=True
            )

        assert len(result) == 2
        # Results are sorted by name
        assert result[0].name == "click"
        assert result[0].license == "BSD-3-Clause"
        assert result[1].name == "pydantic"
        assert result[1].license == "MIT"

    @pytest.mark.asyncio
    async def test_resolves_without_progress_when_disabled(self) -> None:
        """Test that no progress is shown when show_progress=False."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
        ]

        async def mock_fetch(
            name: str, client: Any = None
        ) -> Optional[dict[str, Any]]:
            return {"info": {"license": "MIT"}}

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch(
            "license_analyzer.scanner.fetch_pypi_metadata",
            side_effect=mock_fetch,
        ):
            result = await resolve_licenses(
                packages, console=console, show_progress=False
            )

        assert len(result) == 1
        assert result[0].license == "MIT"
        # No progress output when disabled
        output = string_io.getvalue()
        assert "Resolving" not in output

    @pytest.mark.asyncio
    async def test_progress_mode_handles_network_error(self) -> None:
        """Test that progress mode handles NetworkError gracefully."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
            PackageLicense(name="failing-pkg", version="1.0.0", license=None),
        ]

        async def mock_fetch(
            name: str, client: Any = None
        ) -> Optional[dict[str, Any]]:
            if name == "failing-pkg":
                raise NetworkError("Connection failed")
            return {"info": {"license": "MIT"}}

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch(
            "license_analyzer.scanner.fetch_pypi_metadata",
            side_effect=mock_fetch,
        ):
            result = await resolve_licenses(
                packages, console=console, show_progress=True
            )

        assert len(result) == 2
        # Results are sorted by name: click < failing-pkg
        assert result[0].name == "click"
        assert result[0].license == "MIT"
        # Second package failed but still included with None license
        assert result[1].name == "failing-pkg"
        assert result[1].license is None

    @pytest.mark.asyncio
    async def test_empty_packages_with_progress(self) -> None:
        """Test that empty package list is handled with progress mode."""
        packages: list[PackageLicense] = []

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        result = await resolve_licenses(packages, console=console, show_progress=True)

        assert result == []

    @pytest.mark.asyncio
    async def test_github_not_tried_when_no_metadata(self) -> None:
        """Test that GitHub resolver is not called when PyPI returns no metadata."""
        packages = [
            PackageLicense(name="no-pypi-pkg", version="1.0.0", license=None),
        ]

        async def mock_fetch(
            name: str, client: Any = None
        ) -> Optional[dict[str, Any]]:
            return None  # Package not on PyPI

        # Mock GitHub resolver
        mock_github_resolver = AsyncMock()
        mock_github_resolver.resolve.return_value = "MIT"

        with (
            patch(
                "license_analyzer.scanner.fetch_pypi_metadata",
                side_effect=mock_fetch,
            ),
            patch(
                "license_analyzer.scanner.GitHubLicenseResolver",
                return_value=mock_github_resolver,
            ),
        ):
            result = await resolve_licenses(packages)

        assert len(result) == 1
        assert result[0].license is None
        # GitHub resolver should NOT be called since no metadata
        mock_github_resolver.resolve.assert_not_called()
