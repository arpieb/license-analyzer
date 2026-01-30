"""Tests for PolicyViolation Pydantic model."""
import pytest
from pydantic import ValidationError

from license_analyzer.models.policy import PolicyViolation


class TestPolicyViolation:
    """Tests for PolicyViolation model."""

    def test_valid_violation_with_license(self) -> None:
        """Test creating a violation with detected license."""
        violation = PolicyViolation(
            package_name="requests",
            package_version="2.28.0",
            detected_license="GPL-3.0",
            reason="License 'GPL-3.0' not in allowed list",
        )

        assert violation.package_name == "requests"
        assert violation.package_version == "2.28.0"
        assert violation.detected_license == "GPL-3.0"
        assert violation.reason == "License 'GPL-3.0' not in allowed list"

    def test_valid_violation_with_none_license(self) -> None:
        """Test creating a violation with unknown license (None)."""
        violation = PolicyViolation(
            package_name="unknown-pkg",
            package_version="1.0.0",
            detected_license=None,
            reason="Unknown license",
        )

        assert violation.package_name == "unknown-pkg"
        assert violation.package_version == "1.0.0"
        assert violation.detected_license is None
        assert violation.reason == "Unknown license"

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed (Pydantic strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            PolicyViolation(
                package_name="requests",
                package_version="2.28.0",
                detected_license="GPL-3.0",
                reason="Not allowed",
                extra_field="should fail",  # type: ignore[call-arg]
            )

        assert "extra_field" in str(exc_info.value)

    def test_missing_package_name_raises_error(self) -> None:
        """Test that package_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            PolicyViolation(
                package_version="2.28.0",
                detected_license="GPL-3.0",
                reason="Not allowed",
            )  # type: ignore[call-arg]

        assert "package_name" in str(exc_info.value)

    def test_missing_package_version_raises_error(self) -> None:
        """Test that package_version is required."""
        with pytest.raises(ValidationError) as exc_info:
            PolicyViolation(
                package_name="requests",
                detected_license="GPL-3.0",
                reason="Not allowed",
            )  # type: ignore[call-arg]

        assert "package_version" in str(exc_info.value)

    def test_missing_reason_raises_error(self) -> None:
        """Test that reason is required."""
        with pytest.raises(ValidationError) as exc_info:
            PolicyViolation(
                package_name="requests",
                package_version="2.28.0",
                detected_license="GPL-3.0",
            )  # type: ignore[call-arg]

        assert "reason" in str(exc_info.value)

    def test_detected_license_defaults_to_none(self) -> None:
        """Test that detected_license has a default of None."""
        violation = PolicyViolation(
            package_name="unknown-pkg",
            package_version="1.0.0",
            reason="Unknown license",
        )

        assert violation.detected_license is None

    def test_model_serialization(self) -> None:
        """Test that model can be serialized to dict."""
        violation = PolicyViolation(
            package_name="requests",
            package_version="2.28.0",
            detected_license="GPL-3.0",
            reason="Not allowed",
        )

        data = violation.model_dump()

        assert data["package_name"] == "requests"
        assert data["package_version"] == "2.28.0"
        assert data["detected_license"] == "GPL-3.0"
        assert data["reason"] == "Not allowed"
