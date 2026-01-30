"""Tests for license compatibility checking."""

from license_analyzer.analysis.compatibility import (
    check_all_compatibility,
    check_license_compatibility,
)
from license_analyzer.models.dependency import CompatibilityStatus


class TestCheckLicenseCompatibility:
    """Tests for check_license_compatibility function."""

    # ===== Permissive + Permissive Tests =====

    def test_mit_mit_compatible(self) -> None:
        """Test MIT + MIT is compatible (same license)."""
        result = check_license_compatibility("MIT", "MIT")
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert result.compatible is True
        assert "Same license" in result.reason

    def test_mit_apache_compatible(self) -> None:
        """Test MIT + Apache-2.0 is compatible (both permissive)."""
        result = check_license_compatibility("MIT", "Apache-2.0")
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert "permissive" in result.reason.lower()

    def test_bsd_isc_compatible(self) -> None:
        """Test BSD-3-Clause + ISC is compatible (both permissive)."""
        result = check_license_compatibility("BSD-3-Clause", "ISC")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_all_permissive_combinations(self) -> None:
        """Test all permissive licenses are compatible with each other."""
        permissive = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"]
        for i, lic_a in enumerate(permissive):
            for lic_b in permissive[i:]:
                result = check_license_compatibility(lic_a, lic_b)
                assert result.status == CompatibilityStatus.COMPATIBLE, (
                    f"{lic_a} + {lic_b} should be compatible"
                )

    # ===== Permissive + Copyleft Tests =====

    def test_mit_gpl3_compatible(self) -> None:
        """Test MIT + GPL-3.0 is compatible (MIT can be used in GPL projects)."""
        result = check_license_compatibility("MIT", "GPL-3.0")
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert "MIT" in result.reason

    def test_apache_gpl3_compatible(self) -> None:
        """Test Apache-2.0 + GPL-3.0 is compatible."""
        result = check_license_compatibility("Apache-2.0", "GPL-3.0")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_bsd_lgpl_compatible(self) -> None:
        """Test BSD-3-Clause + LGPL-3.0 is compatible."""
        result = check_license_compatibility("BSD-3-Clause", "LGPL-3.0")
        assert result.status == CompatibilityStatus.COMPATIBLE

    # ===== GPL Family Tests =====

    def test_gpl3_gpl3_compatible(self) -> None:
        """Test GPL-3.0 + GPL-3.0 is compatible."""
        result = check_license_compatibility("GPL-3.0", "GPL-3.0")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_gpl2_only_gpl3_incompatible(self) -> None:
        """Test GPL-2.0-only + GPL-3.0 is incompatible."""
        result = check_license_compatibility("GPL-2.0-only", "GPL-3.0")
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert "GPL-2.0-only" in result.reason

    def test_gpl2_gpl3_incompatible(self) -> None:
        """Test GPL-2.0 + GPL-3.0 is incompatible (GPL-2.0 treated as only)."""
        result = check_license_compatibility("GPL-2.0", "GPL-3.0")
        assert result.status == CompatibilityStatus.INCOMPATIBLE

    def test_gpl3_or_later_gpl3_compatible(self) -> None:
        """Test GPL-3.0-or-later + GPL-3.0 is compatible."""
        result = check_license_compatibility("GPL-3.0-or-later", "GPL-3.0")
        assert result.status == CompatibilityStatus.COMPATIBLE

    # ===== AGPL Tests =====

    def test_agpl_gpl3_compatible(self) -> None:
        """Test AGPL-3.0 + GPL-3.0 is compatible."""
        result = check_license_compatibility("AGPL-3.0", "GPL-3.0")
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert "AGPL" in result.reason

    def test_agpl_gpl2_incompatible(self) -> None:
        """Test AGPL-3.0 + GPL-2.0 is incompatible."""
        result = check_license_compatibility("AGPL-3.0", "GPL-2.0")
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert "network copyleft" in result.reason.lower()

    def test_agpl_lgpl_incompatible(self) -> None:
        """Test AGPL-3.0 + LGPL-3.0 may have issues."""
        result = check_license_compatibility("AGPL-3.0", "LGPL-3.0")
        assert result.status == CompatibilityStatus.INCOMPATIBLE

    # ===== Weak Copyleft Tests =====

    def test_lgpl_lgpl_compatible(self) -> None:
        """Test LGPL-3.0 + LGPL-2.1 is compatible."""
        result = check_license_compatibility("LGPL-3.0", "LGPL-2.1")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_lgpl_mpl_compatible(self) -> None:
        """Test LGPL-3.0 + MPL-2.0 is compatible (both weak copyleft)."""
        result = check_license_compatibility("LGPL-3.0", "MPL-2.0")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_lgpl_gpl_compatible(self) -> None:
        """Test LGPL-3.0 + GPL-3.0 is compatible."""
        result = check_license_compatibility("LGPL-3.0", "GPL-3.0")
        assert result.status == CompatibilityStatus.COMPATIBLE

    # ===== Unknown License Tests =====

    def test_unknown_license_a(self) -> None:
        """Test unknown license_a returns UNKNOWN status."""
        result = check_license_compatibility("Custom-License", "MIT")
        assert result.status == CompatibilityStatus.UNKNOWN
        assert "Custom-License" in result.reason

    def test_unknown_license_b(self) -> None:
        """Test unknown license_b returns UNKNOWN status."""
        result = check_license_compatibility("MIT", "Proprietary")
        assert result.status == CompatibilityStatus.UNKNOWN
        assert "Proprietary" in result.reason

    def test_none_license_a(self) -> None:
        """Test None license_a returns UNKNOWN status."""
        result = check_license_compatibility(None, "MIT")
        assert result.status == CompatibilityStatus.UNKNOWN
        assert "unknown" in result.reason.lower()

    def test_none_license_b(self) -> None:
        """Test None license_b returns UNKNOWN status."""
        result = check_license_compatibility("MIT", None)
        assert result.status == CompatibilityStatus.UNKNOWN

    def test_both_none(self) -> None:
        """Test both licenses None returns UNKNOWN status."""
        result = check_license_compatibility(None, None)
        assert result.status == CompatibilityStatus.UNKNOWN

    # ===== Case Insensitivity Tests =====

    def test_case_insensitive_mit(self) -> None:
        """Test license comparison is case-insensitive."""
        result = check_license_compatibility("mit", "MIT")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_case_insensitive_apache(self) -> None:
        """Test Apache-2.0 case variations."""
        result = check_license_compatibility("apache-2.0", "APACHE-2.0")
        assert result.status == CompatibilityStatus.COMPATIBLE


class TestCheckAllCompatibility:
    """Tests for check_all_compatibility function."""

    def test_all_permissive_no_issues(self) -> None:
        """Test all permissive licenses returns empty list."""
        licenses = ["MIT", "Apache-2.0", "BSD-3-Clause"]
        results = check_all_compatibility(licenses)
        assert len(results) == 0

    def test_gpl2_gpl3_returns_incompatible(self) -> None:
        """Test GPL-2.0 + GPL-3.0 returns incompatible result."""
        licenses = ["GPL-2.0", "GPL-3.0"]
        results = check_all_compatibility(licenses)
        assert len(results) == 1
        assert results[0].status == CompatibilityStatus.INCOMPATIBLE

    def test_mixed_licenses_returns_issues(self) -> None:
        """Test mixed licenses returns only incompatible pairs."""
        licenses = ["MIT", "GPL-2.0", "GPL-3.0"]
        results = check_all_compatibility(licenses)
        # MIT + GPL-2.0 = compatible
        # MIT + GPL-3.0 = compatible
        # GPL-2.0 + GPL-3.0 = incompatible
        assert len(results) == 1
        assert results[0].status == CompatibilityStatus.INCOMPATIBLE

    def test_deduplicates_symmetric_pairs(self) -> None:
        """Test that (A,B) and (B,A) are not both checked."""
        licenses = ["MIT", "MIT", "Apache-2.0"]  # Duplicate MIT
        results = check_all_compatibility(licenses)
        # Should only check unique pairs: MIT+Apache-2.0
        assert len(results) == 0  # Both permissive

    def test_single_license_returns_empty(self) -> None:
        """Test single license returns empty list."""
        licenses = ["MIT"]
        results = check_all_compatibility(licenses)
        assert len(results) == 0

    def test_empty_list_returns_empty(self) -> None:
        """Test empty list returns empty list."""
        licenses: list[str] = []
        results = check_all_compatibility(licenses)
        assert len(results) == 0

    def test_unknown_license_included(self) -> None:
        """Test unknown license is included in results."""
        licenses = ["MIT", "Custom-License"]
        results = check_all_compatibility(licenses)
        assert len(results) == 1
        assert results[0].status == CompatibilityStatus.UNKNOWN

    def test_multiple_incompatible_pairs(self) -> None:
        """Test multiple incompatible pairs are all returned."""
        licenses = ["GPL-2.0", "GPL-3.0", "AGPL-3.0"]
        results = check_all_compatibility(licenses)
        # GPL-2.0 + GPL-3.0 = incompatible
        # GPL-2.0 + AGPL-3.0 = incompatible (network copyleft)
        # GPL-3.0 + AGPL-3.0 = compatible
        assert len(results) == 2
        statuses = [r.status for r in results]
        assert all(s == CompatibilityStatus.INCOMPATIBLE for s in statuses)
