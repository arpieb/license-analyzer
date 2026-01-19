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
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)": (
        "GPL-3.0"
    ),
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)": (
        "GPL-2.0"
    ),
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
        url = f"{PYPI_BASE_URL}/{package_name}/json"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=httpx.Timeout(30.0))
                if response.status_code == 404:
                    return None
                response.raise_for_status()
            except httpx.HTTPStatusError:
                return None
            except httpx.RequestError as e:
                raise NetworkError(f"Failed to fetch {package_name}: {e}") from e

            data: dict[str, Any] = response.json()
            info: dict[str, Any] = data.get("info", {})

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
