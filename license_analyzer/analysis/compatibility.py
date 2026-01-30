"""License compatibility checking for license-analyzer.

Provides functions to check license compatibility using SPDX rules (FR13).
Uses the license-expression library for accurate SPDX parsing and normalization.
"""

from typing import Optional

from license_expression import (
    ExpressionError,
    get_spdx_licensing,
)

from license_analyzer.models.dependency import CompatibilityResult, CompatibilityStatus

# Initialize SPDX licensing for parsing
_licensing = get_spdx_licensing()

# Permissive licenses - compatible with everything
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

# Strong copyleft licenses - GPL family
GPL_LICENSES: set[str] = {
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
}

# GPL-3.0 specific variants
GPL_3_LICENSES: set[str] = {
    "GPL-3.0-only",
    "GPL-3.0-or-later",
}

# GPL-2.0 specific variants (only, not or-later)
GPL_2_ONLY_LICENSES: set[str] = {
    "GPL-2.0-only",
}

# AGPL licenses - network copyleft
AGPL_LICENSES: set[str] = {
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
}

# Weak copyleft licenses
WEAK_COPYLEFT_LICENSES: set[str] = {
    "LGPL-2.0-only",
    "LGPL-2.0-or-later",
    "LGPL-2.1-only",
    "LGPL-2.1-or-later",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
    "MPL-2.0",
}


def _normalize_license_id(license_id: Optional[str]) -> Optional[str]:
    """Normalize license ID using license-expression library.

    Uses SPDX licensing to parse and normalize license identifiers.
    Handles common variations like GPL-3.0 -> GPL-3.0-only.

    Args:
        license_id: SPDX license identifier or None.

    Returns:
        Normalized SPDX license key, or None if invalid/unknown.
    """
    if license_id is None:
        return None

    license_id = license_id.strip()
    if not license_id:
        return None

    try:
        parsed = _licensing.parse(license_id, validate=True)
        # For simple licenses, return the key
        if hasattr(parsed, "key"):
            return str(parsed.key)
        # For compound expressions, return as-is for now
        return license_id
    except ExpressionError:
        # Not a valid SPDX identifier - return original for unknown handling
        return license_id


def _is_valid_spdx(license_id: str) -> bool:
    """Check if a license ID is a valid SPDX identifier."""
    try:
        _licensing.parse(license_id, validate=True)
        return True
    except ExpressionError:
        return False


def _is_permissive(license_id: str) -> bool:
    """Check if a license is permissive."""
    normalized = _normalize_license_id(license_id)
    if normalized is None:
        return False
    return normalized in PERMISSIVE_LICENSES


def _is_gpl(license_id: str) -> bool:
    """Check if a license is in the GPL family."""
    normalized = _normalize_license_id(license_id)
    if normalized is None:
        return False
    return normalized in GPL_LICENSES


def _is_gpl_3(license_id: str) -> bool:
    """Check if a license is GPL-3.0 or compatible."""
    normalized = _normalize_license_id(license_id)
    if normalized is None:
        return False
    return normalized in GPL_3_LICENSES


def _is_gpl_2_only(license_id: str) -> bool:
    """Check if a license is GPL-2.0-only (not or-later)."""
    normalized = _normalize_license_id(license_id)
    if normalized is None:
        return False
    return normalized in GPL_2_ONLY_LICENSES


def _is_agpl(license_id: str) -> bool:
    """Check if a license is AGPL."""
    normalized = _normalize_license_id(license_id)
    if normalized is None:
        return False
    return normalized in AGPL_LICENSES


def _is_weak_copyleft(license_id: str) -> bool:
    """Check if a license is weak copyleft."""
    normalized = _normalize_license_id(license_id)
    if normalized is None:
        return False
    return normalized in WEAK_COPYLEFT_LICENSES


def _is_known_license(license_id: str) -> bool:
    """Check if a license is in our compatibility rules."""
    return (
        _is_permissive(license_id)
        or _is_gpl(license_id)
        or _is_agpl(license_id)
        or _is_weak_copyleft(license_id)
    )


def check_license_compatibility(
    license_a: Optional[str], license_b: Optional[str]
) -> CompatibilityResult:
    """Check if two licenses are compatible.

    Uses the license-expression library for SPDX parsing and applies
    compatibility rules based on license categories.

    Args:
        license_a: First SPDX license identifier.
        license_b: Second SPDX license identifier.

    Returns:
        CompatibilityResult with status and reason.
    """
    # Handle None/empty licenses
    if not license_a or not license_b:
        return CompatibilityResult(
            license_a=license_a or "Unknown",
            license_b=license_b or "Unknown",
            status=CompatibilityStatus.UNKNOWN,
            reason="Cannot determine compatibility with unknown license",
        )

    # Normalize using license-expression library
    norm_a = _normalize_license_id(license_a)
    norm_b = _normalize_license_id(license_b)

    # Same license is always compatible
    if norm_a and norm_b and norm_a == norm_b:
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.COMPATIBLE,
            reason="Same license",
        )

    # Check for unknown/invalid licenses
    if not _is_known_license(license_a) or not _is_known_license(license_b):
        unknown = license_a if not _is_known_license(license_a) else license_b
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.UNKNOWN,
            reason=f"{unknown} is not a recognized license",
        )

    # Both permissive - always compatible
    if _is_permissive(license_a) and _is_permissive(license_b):
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.COMPATIBLE,
            reason="Both licenses are permissive",
        )

    # Permissive + anything else - permissive can be used in copyleft projects
    if _is_permissive(license_a) or _is_permissive(license_b):
        permissive = license_a if _is_permissive(license_a) else license_b
        other = license_b if _is_permissive(license_a) else license_a
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.COMPATIBLE,
            reason=f"{permissive} code can be used in {other} projects",
        )

    # GPL + GPL (same family)
    if _is_gpl(license_a) and _is_gpl(license_b):
        # GPL-2.0-only with GPL-3.0 = incompatible
        if (_is_gpl_2_only(license_a) and _is_gpl_3(license_b)) or (
            _is_gpl_2_only(license_b) and _is_gpl_3(license_a)
        ):
            return CompatibilityResult(
                license_a=license_a,
                license_b=license_b,
                status=CompatibilityStatus.INCOMPATIBLE,
                reason="GPL-2.0-only is not compatible with GPL-3.0",
            )
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.COMPATIBLE,
            reason="Both licenses are in the GPL family",
        )

    # AGPL + GPL-3.0 = compatible (AGPL is based on GPL-3.0)
    if (_is_agpl(license_a) and _is_gpl_3(license_b)) or (
        _is_agpl(license_b) and _is_gpl_3(license_a)
    ):
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.COMPATIBLE,
            reason="AGPL-3.0 is compatible with GPL-3.0",
        )

    # AGPL + non-AGPL copyleft = potentially problematic
    if _is_agpl(license_a) or _is_agpl(license_b):
        agpl = license_a if _is_agpl(license_a) else license_b
        other = license_b if _is_agpl(license_a) else license_a
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.INCOMPATIBLE,
            reason=f"{agpl} network copyleft may conflict with {other}",
        )

    # Weak copyleft + GPL = generally compatible (LGPL can link with GPL)
    if (_is_weak_copyleft(license_a) and _is_gpl(license_b)) or (
        _is_weak_copyleft(license_b) and _is_gpl(license_a)
    ):
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.COMPATIBLE,
            reason="Weak copyleft licenses can be used with GPL",
        )

    # Weak copyleft + weak copyleft = compatible
    if _is_weak_copyleft(license_a) and _is_weak_copyleft(license_b):
        return CompatibilityResult(
            license_a=license_a,
            license_b=license_b,
            status=CompatibilityStatus.COMPATIBLE,
            reason="Both licenses are weak copyleft",
        )

    # Default: unknown compatibility
    return CompatibilityResult(
        license_a=license_a,
        license_b=license_b,
        status=CompatibilityStatus.UNKNOWN,
        reason=f"Compatibility between {license_a} and {license_b} is unclear",
    )


def check_all_compatibility(
    licenses: list[str],
) -> list[CompatibilityResult]:
    """Check compatibility between all license pairs.

    Args:
        licenses: List of SPDX license identifiers.

    Returns:
        List of CompatibilityResult for incompatible or unknown pairs.
        Compatible pairs are not included in the result.
    """
    results: list[CompatibilityResult] = []

    # Get unique licenses
    unique_licenses = list(set(licenses))

    # Check all pairs (i+1 slicing prevents duplicate symmetric checks)
    for i, license_a in enumerate(unique_licenses):
        for license_b in unique_licenses[i + 1 :]:
            result = check_license_compatibility(license_a, license_b)

            # Only include non-compatible results
            if result.status != CompatibilityStatus.COMPATIBLE:
                results.append(result)

    return results
