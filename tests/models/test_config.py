"""Tests for configuration Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from license_analyzer.models.config import AnalyzerConfig, LicenseOverride


class TestLicenseOverride:
    """Tests for LicenseOverride model."""

    def test_valid_override(self) -> None:
        """Test creating a valid license override."""
        override = LicenseOverride(
            license="MIT",
            reason="Confirmed with maintainer via email",
        )
        assert override.license == "MIT"
        assert override.reason == "Confirmed with maintainer via email"

    def test_requires_license_field(self) -> None:
        """Test that license field is required."""
        with pytest.raises(ValidationError) as exc_info:
            LicenseOverride(reason="some reason")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("license",) for e in errors)

    def test_requires_reason_field(self) -> None:
        """Test that reason field is required."""
        with pytest.raises(ValidationError) as exc_info:
            LicenseOverride(license="MIT")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("reason",) for e in errors)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            LicenseOverride(
                license="MIT",
                reason="test",
                unknown_field="value",  # type: ignore[call-arg]
            )
        errors = exc_info.value.errors()
        assert any("extra" in str(e).lower() for e in errors)


class TestAnalyzerConfig:
    """Tests for AnalyzerConfig model."""

    def test_valid_config_all_fields(self) -> None:
        """Test creating a config with all fields populated."""
        config = AnalyzerConfig(
            allowed_licenses=["MIT", "Apache-2.0"],
            ignored_packages=["internal-tool"],
            overrides={
                "some-package": LicenseOverride(
                    license="MIT",
                    reason="Confirmed",
                )
            },
        )
        assert config.allowed_licenses == ["MIT", "Apache-2.0"]
        assert config.ignored_packages == ["internal-tool"]
        assert "some-package" in config.overrides  # type: ignore[operator]
        assert config.overrides["some-package"].license == "MIT"  # type: ignore[index]

    def test_optional_fields_default_to_none(self) -> None:
        """Test that all fields default to None when not provided."""
        config = AnalyzerConfig()
        assert config.allowed_licenses is None
        assert config.ignored_packages is None
        assert config.overrides is None

    def test_partial_config(self) -> None:
        """Test creating a config with only some fields."""
        config = AnalyzerConfig(allowed_licenses=["MIT"])
        assert config.allowed_licenses == ["MIT"]
        assert config.ignored_packages is None
        assert config.overrides is None

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzerConfig(
                allowed_licenses=["MIT"],
                unknown_field="value",  # type: ignore[call-arg]
            )
        errors = exc_info.value.errors()
        assert any("extra" in str(e).lower() for e in errors)

    def test_allowed_licenses_must_be_list(self) -> None:
        """Test that allowed_licenses must be a list if provided."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzerConfig(allowed_licenses="MIT")  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("allowed_licenses",) for e in errors)

    def test_ignored_packages_must_be_list(self) -> None:
        """Test that ignored_packages must be a list if provided."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzerConfig(ignored_packages="some-package")  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("ignored_packages",) for e in errors)

    def test_overrides_must_be_dict(self) -> None:
        """Test that overrides must be a dict if provided."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzerConfig(overrides=["invalid"])  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "overrides" for e in errors)

    def test_overrides_values_must_be_license_override(self) -> None:
        """Test that override values must be LicenseOverride objects."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzerConfig(
                overrides={"pkg": {"invalid": "structure"}}  # type: ignore[dict-item]
            )
        errors = exc_info.value.errors()
        # Should fail validation due to missing required fields
        assert len(errors) > 0

    def test_empty_lists_are_valid(self) -> None:
        """Test that empty lists are valid for list fields."""
        config = AnalyzerConfig(
            allowed_licenses=[],
            ignored_packages=[],
        )
        assert config.allowed_licenses == []
        assert config.ignored_packages == []

    def test_empty_dict_is_valid_for_overrides(self) -> None:
        """Test that empty dict is valid for overrides."""
        config = AnalyzerConfig(overrides={})
        assert config.overrides == {}
