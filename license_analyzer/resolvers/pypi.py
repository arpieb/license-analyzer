"""PyPI license resolver."""

from typing import Any, Optional

import httpx

from license_analyzer.exceptions import NetworkError
from license_analyzer.resolvers.base import BaseResolver

PYPI_BASE_URL = "https://pypi.org/pypi"

# Mapping of PyPI classifiers to SPDX identifiers
CLASSIFIER_TO_SPDX: dict[str, str] = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: BSD License": "BSD-3-Clause",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)": ("GPL-3.0"),
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)": ("GPL-2.0"),
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)": (
        "LGPL-3.0"
    ),
    "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)": (
        "LGPL-2.0"
    ),
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: The Unlicense (Unlicense)": "Unlicense",
    "License :: OSI Approved :: zlib/libpng License": "Zlib",
}


async def fetch_pypi_metadata(
    package_name: str, client: Optional[httpx.AsyncClient] = None
) -> Optional[dict[str, Any]]:
    """Fetch package metadata from PyPI JSON API.

    Args:
        package_name: The package name to fetch metadata for.
        client: Optional httpx.AsyncClient to use. If not provided,
            a new client will be created.

    Returns:
        PyPI JSON API response dict, or None if package not found.

    Raises:
        NetworkError: If the network request fails.
    """
    url = f"{PYPI_BASE_URL}/{package_name}/json"

    async def do_fetch(c: httpx.AsyncClient) -> Optional[dict[str, Any]]:
        try:
            response = await c.get(url, timeout=httpx.Timeout(30.0))
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError:
            return None
        except httpx.RequestError as e:
            raise NetworkError(f"Failed to fetch {package_name}: {e}") from e

    if client:
        return await do_fetch(client)

    async with httpx.AsyncClient() as new_client:
        return await do_fetch(new_client)


def extract_license_from_metadata(metadata: Optional[dict[str, Any]]) -> Optional[str]:
    """Extract license identifier from PyPI metadata.

    Args:
        metadata: PyPI JSON API response dict.

    Returns:
        License identifier string, or None if not found.
    """
    if not metadata:
        return None

    info: dict[str, Any] = metadata.get("info", {})

    # Try license field first
    license_str: Optional[str] = info.get("license")
    if license_str and license_str.strip():
        cleaned: str = license_str.strip()
        # Skip common "no license" values
        if cleaned.upper() not in ("UNKNOWN", "NONE", ""):
            return cleaned

    # Fall back to classifiers
    classifiers: list[str] = info.get("classifiers", [])
    for classifier in classifiers:
        if classifier in CLASSIFIER_TO_SPDX:
            return CLASSIFIER_TO_SPDX[classifier]

    return None


class PyPIResolver(BaseResolver):
    """Resolver that fetches license info from PyPI JSON API."""

    async def resolve(self, package_name: str, version: str) -> Optional[str]:
        """Resolve license from PyPI metadata.

        Args:
            package_name: The package name to resolve.
            version: The package version (not used for PyPI API, fetches latest).

        Returns:
            License identifier string, or None if not found.

        Raises:
            NetworkError: If the network request fails.
        """
        metadata = await fetch_pypi_metadata(package_name)
        return extract_license_from_metadata(metadata)
