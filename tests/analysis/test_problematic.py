"""Tests for problematic license detection."""
from license_analyzer.analysis.problematic import (
    PROBLEMATIC_LICENSES,
    LicenseCategory,
    get_license_category,
    is_problematic_license,
)


class TestLicenseCategory:
    """Tests for LicenseCategory enum."""

    def test_category_values(self) -> None:
        """Test LicenseCategory has expected values."""
        assert LicenseCategory.PERMISSIVE.value == "permissive"
        assert LicenseCategory.COPYLEFT.value == "copyleft"
        assert LicenseCategory.WEAK_COPYLEFT.value == "weak_copyleft"
        assert LicenseCategory.PROPRIETARY.value == "proprietary"
        assert LicenseCategory.UNKNOWN.value == "unknown"


class TestProblematicLicenses:
    """Tests for problematic license detection."""

    def test_gpl_variants_are_problematic(self) -> None:
        """Test GPL variants are detected as problematic."""
        assert is_problematic_license("GPL-3.0") is True
        assert is_problematic_license("GPL-2.0") is True
        assert is_problematic_license("GPL-2.0-only") is True
        assert is_problematic_license("GPL-2.0-or-later") is True
        assert is_problematic_license("GPL-3.0-only") is True
        assert is_problematic_license("GPL-3.0-or-later") is True

    def test_agpl_is_problematic(self) -> None:
        """Test AGPL is detected as problematic."""
        assert is_problematic_license("AGPL-3.0") is True
        assert is_problematic_license("AGPL-3.0-only") is True
        assert is_problematic_license("AGPL-3.0-or-later") is True

    def test_lgpl_is_problematic(self) -> None:
        """Test LGPL is detected as problematic."""
        assert is_problematic_license("LGPL-2.0") is True
        assert is_problematic_license("LGPL-2.1") is True
        assert is_problematic_license("LGPL-3.0") is True

    def test_permissive_not_problematic(self) -> None:
        """Test permissive licenses are not flagged."""
        assert is_problematic_license("MIT") is False
        assert is_problematic_license("Apache-2.0") is False
        assert is_problematic_license("BSD-3-Clause") is False
        assert is_problematic_license("BSD-2-Clause") is False
        assert is_problematic_license("ISC") is False

    def test_none_license_not_problematic(self) -> None:
        """Test None license is not flagged as problematic."""
        assert is_problematic_license(None) is False

    def test_empty_string_not_problematic(self) -> None:
        """Test empty string is not flagged as problematic."""
        assert is_problematic_license("") is False

    def test_case_insensitive_matching(self) -> None:
        """Test license matching is case-insensitive."""
        assert is_problematic_license("gpl-3.0") is True
        assert is_problematic_license("GPL-3.0") is True
        assert is_problematic_license("Gpl-3.0") is True
        assert is_problematic_license("agpl-3.0") is True

    def test_gpl_with_exception_is_problematic(self) -> None:
        """Test GPL-with-exception variants are detected as problematic."""
        assert is_problematic_license("GPL-3.0-with-GCC-exception") is True
        assert is_problematic_license("GPL-2.0-with-classpath-exception") is True
        assert is_problematic_license("GPL-2.0-with-bison-exception") is True

    def test_problematic_licenses_set_not_empty(self) -> None:
        """Test PROBLEMATIC_LICENSES constant is populated."""
        assert len(PROBLEMATIC_LICENSES) > 0
        assert "GPL-3.0" in PROBLEMATIC_LICENSES


class TestGetLicenseCategory:
    """Tests for license categorization."""

    def test_permissive_licenses(self) -> None:
        """Test permissive licenses are categorized correctly."""
        assert get_license_category("MIT") == LicenseCategory.PERMISSIVE
        assert get_license_category("Apache-2.0") == LicenseCategory.PERMISSIVE
        assert get_license_category("BSD-3-Clause") == LicenseCategory.PERMISSIVE

    def test_copyleft_licenses(self) -> None:
        """Test copyleft licenses are categorized correctly."""
        assert get_license_category("GPL-3.0") == LicenseCategory.COPYLEFT
        assert get_license_category("GPL-2.0") == LicenseCategory.COPYLEFT
        assert get_license_category("AGPL-3.0") == LicenseCategory.COPYLEFT

    def test_weak_copyleft_licenses(self) -> None:
        """Test weak copyleft licenses are categorized correctly."""
        assert get_license_category("LGPL-3.0") == LicenseCategory.WEAK_COPYLEFT
        assert get_license_category("MPL-2.0") == LicenseCategory.WEAK_COPYLEFT

    def test_unknown_license(self) -> None:
        """Test unknown licenses return UNKNOWN category."""
        assert get_license_category("SomeRandomLicense") == LicenseCategory.UNKNOWN
        assert get_license_category(None) == LicenseCategory.UNKNOWN
        assert get_license_category("") == LicenseCategory.UNKNOWN
