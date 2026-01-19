"""Tests for PyPI resolver."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from license_analyzer.exceptions import NetworkError
from license_analyzer.resolvers.pypi import CLASSIFIER_TO_SPDX, PyPIResolver


class TestPyPIResolver:
    """Tests for PyPIResolver."""

    @pytest.mark.asyncio
    async def test_resolve_returns_license_from_info(self) -> None:
        """Test that license is extracted from info.license field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "name": "click",
                "version": "8.1.7",
                "license": "BSD-3-Clause",
                "classifiers": [],
            }
        }

        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            resolver = PyPIResolver()
            result = await resolver.resolve("click", "8.1.7")

        assert result == "BSD-3-Clause"

    @pytest.mark.asyncio
    async def test_resolve_returns_license_from_classifier(self) -> None:
        """Test that license is extracted from classifiers when empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "name": "some-pkg",
                "version": "1.0.0",
                "license": "",
                "classifiers": [
                    "Programming Language :: Python :: 3",
                    "License :: OSI Approved :: MIT License",
                ],
            }
        }

        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            resolver = PyPIResolver()
            result = await resolver.resolve("some-pkg", "1.0.0")

        assert result == "MIT"

    @pytest.mark.asyncio
    async def test_resolve_returns_none_for_404(self) -> None:
        """Test that 404 returns None (package not on PyPI)."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            resolver = PyPIResolver()
            result = await resolver.resolve("nonexistent-package", "1.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_for_missing_license(self) -> None:
        """Test that missing license returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "name": "test-pkg",
                "version": "1.0.0",
                "license": "",
                "classifiers": [],
            }
        }

        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            resolver = PyPIResolver()
            result = await resolver.resolve("test-pkg", "1.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_for_unknown_license(self) -> None:
        """Test that 'UNKNOWN' license returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "name": "test-pkg",
                "version": "1.0.0",
                "license": "UNKNOWN",
                "classifiers": [],
            }
        }

        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            resolver = PyPIResolver()
            result = await resolver.resolve("test-pkg", "1.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_raises_network_error_on_request_failure(self) -> None:
        """Test that network errors raise NetworkError."""
        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )

            resolver = PyPIResolver()

            with pytest.raises(NetworkError) as exc_info:
                await resolver.resolve("test-pkg", "1.0.0")

            assert "Failed to fetch test-pkg" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_prefers_license_field_over_classifier(self) -> None:
        """Test that info.license takes precedence over classifiers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "name": "test-pkg",
                "version": "1.0.0",
                "license": "Apache-2.0",
                "classifiers": [
                    "License :: OSI Approved :: MIT License",
                ],
            }
        }

        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            resolver = PyPIResolver()
            result = await resolver.resolve("test-pkg", "1.0.0")

        # Should return the license field value, not the classifier
        assert result == "Apache-2.0"

    @pytest.mark.asyncio
    async def test_resolve_strips_whitespace_from_license(self) -> None:
        """Test that license strings are stripped of whitespace."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "name": "test-pkg",
                "version": "1.0.0",
                "license": "  MIT  ",
                "classifiers": [],
            }
        }

        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            resolver = PyPIResolver()
            result = await resolver.resolve("test-pkg", "1.0.0")

        assert result == "MIT"

    @pytest.mark.asyncio
    async def test_resolve_returns_none_for_http_500_error(self) -> None:
        """Test that HTTP 5xx server errors return None."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch("license_analyzer.resolvers.pypi.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            resolver = PyPIResolver()
            result = await resolver.resolve("test-pkg", "1.0.0")

        assert result is None


class TestClassifierMapping:
    """Tests for classifier to SPDX mapping."""

    def test_mit_classifier_maps_correctly(self) -> None:
        """Test MIT classifier mapping."""
        assert CLASSIFIER_TO_SPDX["License :: OSI Approved :: MIT License"] == "MIT"

    def test_apache_classifier_maps_correctly(self) -> None:
        """Test Apache classifier mapping."""
        key = "License :: OSI Approved :: Apache Software License"
        assert CLASSIFIER_TO_SPDX[key] == "Apache-2.0"

    def test_bsd_classifier_maps_correctly(self) -> None:
        """Test BSD classifier mapping."""
        key = "License :: OSI Approved :: BSD License"
        assert CLASSIFIER_TO_SPDX[key] == "BSD-3-Clause"

    def test_gpl3_classifier_maps_correctly(self) -> None:
        """Test GPL-3.0 classifier mapping."""
        key = "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
        assert CLASSIFIER_TO_SPDX[key] == "GPL-3.0"
