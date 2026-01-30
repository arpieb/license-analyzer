"""Problematic license detection for license-analyzer.

Provides functions to identify licenses that may be problematic for
commercial or permissive-licensed projects (FR10).
"""
from enum import Enum
from typing import Optional


class LicenseCategory(Enum):
    """Categories of licenses by restriction level."""

    PERMISSIVE = "permissive"
    COPYLEFT = "copyleft"
    WEAK_COPYLEFT = "weak_copyleft"
    PROPRIETARY = "proprietary"
    UNKNOWN = "unknown"


# Licenses commonly considered "problematic" for commercial/permissive projects
PROBLEMATIC_LICENSES: set[str] = {
    # Strong copyleft - GPL variants
    "GPL-2.0",
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-2.0+",
    "GPL-3.0",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "GPL-3.0+",
    # Strong copyleft - AGPL variants
    "AGPL-3.0",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
    # Weak copyleft - LGPL variants
    "LGPL-2.0",
    "LGPL-2.0-only",
    "LGPL-2.0-or-later",
    "LGPL-2.1",
    "LGPL-2.1-only",
    "LGPL-2.1-or-later",
    "LGPL-3.0",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
    # Weak copyleft - MPL
    "MPL-2.0",
    # Other restrictive
    "SSPL-1.0",
    # Note: BSL-1.0 (Boost Software License) is permissive, not problematic
    # BUSL (Business Source License) would be problematic but uses different SPDX ID
}

# Permissive licenses (for categorization)
PERMISSIVE_LICENSES: set[str] = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Unlicense",
    "CC0-1.0",
    "0BSD",
}

# Strong copyleft licenses
COPYLEFT_LICENSES: set[str] = {
    "GPL-2.0",
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-2.0+",
    "GPL-3.0",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "GPL-3.0+",
    "AGPL-3.0",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
}

# Weak copyleft licenses
WEAK_COPYLEFT_LICENSES: set[str] = {
    "LGPL-2.0",
    "LGPL-2.0-only",
    "LGPL-2.0-or-later",
    "LGPL-2.1",
    "LGPL-2.1-only",
    "LGPL-2.1-or-later",
    "LGPL-3.0",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
    "MPL-2.0",
}


def _normalize_license_id(license_id: Optional[str]) -> str:
    """Normalize license ID for comparison.

    Args:
        license_id: SPDX license identifier or None.

    Returns:
        Normalized uppercase license ID, or empty string for None.
    """
    if license_id is None:
        return ""
    return license_id.upper().strip()


def is_problematic_license(license_id: Optional[str]) -> bool:
    """Check if a license is considered problematic.

    Problematic licenses include strong copyleft (GPL, AGPL) and
    weak copyleft (LGPL, MPL) licenses that may impose restrictions
    on derivative works.

    Args:
        license_id: SPDX license identifier or None.

    Returns:
        True if license is in the problematic set.
    """
    if not license_id:
        return False

    normalized = _normalize_license_id(license_id)
    if not normalized:
        return False

    # Check exact match or if license contains a problematic identifier
    # This catches variants like "GPL-3.0-with-GCC-exception"
    return any(
        prob.upper() == normalized or prob.upper() in normalized
        for prob in PROBLEMATIC_LICENSES
    )


def get_license_category(license_id: Optional[str]) -> LicenseCategory:
    """Categorize a license by its restriction level.

    Args:
        license_id: SPDX license identifier or None.

    Returns:
        LicenseCategory indicating the type of license.
    """
    if not license_id:
        return LicenseCategory.UNKNOWN

    normalized = _normalize_license_id(license_id)
    if not normalized:
        return LicenseCategory.UNKNOWN

    # Check permissive first (most common)
    for perm in PERMISSIVE_LICENSES:
        if perm.upper() == normalized or perm.upper() in normalized:
            return LicenseCategory.PERMISSIVE

    # Check weak copyleft BEFORE strong copyleft (LGPL contains GPL)
    for weak in WEAK_COPYLEFT_LICENSES:
        if weak.upper() == normalized or weak.upper() in normalized:
            return LicenseCategory.WEAK_COPYLEFT

    # Check strong copyleft
    for copyleft in COPYLEFT_LICENSES:
        if copyleft.upper() == normalized or copyleft.upper() in normalized:
            return LicenseCategory.COPYLEFT

    return LicenseCategory.UNKNOWN
