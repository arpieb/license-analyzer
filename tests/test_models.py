"""Tests for Pydantic models."""
import pytest
from pydantic import ValidationError

from license_analyzer.models.scan import PackageLicense, ScanOptions, ScanResult


class TestScanOptions:
    """Tests for ScanOptions model."""

    def test_default_format(self) -> None:
        """Test that default format is terminal."""
        options = ScanOptions()
        assert options.format == "terminal"

    def test_valid_formats(self) -> None:
        """Test all valid format options."""
        for fmt in ["terminal", "markdown", "json"]:
            options = ScanOptions(format=fmt)  # type: ignore[arg-type]
            assert options.format == fmt

    def test_invalid_format_rejected(self) -> None:
        """Test that invalid format raises ValidationError."""
        with pytest.raises(ValidationError):
            ScanOptions(format="invalid")  # type: ignore[arg-type]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ScanOptions(format="json", unknown_field="value")  # type: ignore[call-arg]


class TestPackageLicense:
    """Tests for PackageLicense model."""

    def test_required_fields(self) -> None:
        """Test that name and version are required."""
        pkg = PackageLicense(name="click", version="8.1.0")
        assert pkg.name == "click"
        assert pkg.version == "8.1.0"
        assert pkg.license is None

    def test_with_license(self) -> None:
        """Test package with license."""
        pkg = PackageLicense(name="click", version="8.1.0", license="MIT")
        assert pkg.license == "MIT"

    def test_missing_name_rejected(self) -> None:
        """Test that missing name raises ValidationError."""
        with pytest.raises(ValidationError):
            PackageLicense(version="1.0.0")  # type: ignore[call-arg]

    def test_missing_version_rejected(self) -> None:
        """Test that missing version raises ValidationError."""
        with pytest.raises(ValidationError):
            PackageLicense(name="pkg")  # type: ignore[call-arg]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            PackageLicense(name="click", version="8.1.0", unknown_field="value")  # type: ignore[call-arg]

    def test_serialization(self) -> None:
        """Test JSON serialization."""
        pkg = PackageLicense(name="click", version="8.1.0", license="MIT")
        json_str = pkg.model_dump_json()
        assert "click" in json_str
        assert "8.1.0" in json_str
        assert "MIT" in json_str


class TestScanResult:
    """Tests for ScanResult model."""

    def test_defaults(self) -> None:
        """Test default values."""
        result = ScanResult()
        assert result.packages == []
        assert result.total_packages == 0
        assert result.issues_found == 0

    def test_with_packages(self) -> None:
        """Test result with packages."""
        pkg = PackageLicense(name="click", version="8.1.0", license="MIT")
        result = ScanResult(packages=[pkg], total_packages=1, issues_found=0)
        assert len(result.packages) == 1
        assert result.packages[0].name == "click"
        assert result.total_packages == 1

    def test_serialization(self) -> None:
        """Test JSON serialization."""
        pkg = PackageLicense(name="click", version="8.1.0", license="MIT")
        result = ScanResult(packages=[pkg], total_packages=1, issues_found=0)
        json_str = result.model_dump_json()
        assert "click" in json_str
        assert "MIT" in json_str

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ScanResult(packages=[], unknown_field="value")  # type: ignore[call-arg]
