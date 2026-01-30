"""Tests for custom exceptions."""

from license_analyzer.exceptions import (
    ConfigurationError,
    LicenseAnalyzerError,
    NetworkError,
    ScanError,
)


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_license_analyzer_error_is_exception(self) -> None:
        """Test that LicenseAnalyzerError inherits from Exception."""
        assert issubclass(LicenseAnalyzerError, Exception)

    def test_network_error_inherits_from_base(self) -> None:
        """Test that NetworkError inherits from LicenseAnalyzerError."""
        assert issubclass(NetworkError, LicenseAnalyzerError)

    def test_configuration_error_inherits_from_base(self) -> None:
        """Test that ConfigurationError inherits from LicenseAnalyzerError."""
        assert issubclass(ConfigurationError, LicenseAnalyzerError)

    def test_scan_error_inherits_from_base(self) -> None:
        """Test that ScanError inherits from LicenseAnalyzerError."""
        assert issubclass(ScanError, LicenseAnalyzerError)

    def test_network_error_can_be_raised(self) -> None:
        """Test that NetworkError can be raised with a message."""
        try:
            raise NetworkError("Connection failed")
        except LicenseAnalyzerError as e:
            assert str(e) == "Connection failed"
        else:
            raise AssertionError("NetworkError was not raised")

    def test_configuration_error_can_be_raised(self) -> None:
        """Test that ConfigurationError can be raised with a message."""
        try:
            raise ConfigurationError("Invalid config file")
        except LicenseAnalyzerError as e:
            assert str(e) == "Invalid config file"
        else:
            raise AssertionError("ConfigurationError was not raised")

    def test_scan_error_can_be_raised(self) -> None:
        """Test that ScanError can be raised with a message."""
        try:
            raise ScanError("Scan failed")
        except LicenseAnalyzerError as e:
            assert str(e) == "Scan failed"
        else:
            raise AssertionError("ScanError was not raised")

    def test_all_exceptions_catchable_by_base(self) -> None:
        """Test that all custom exceptions can be caught by LicenseAnalyzerError."""
        exceptions = [
            NetworkError("network"),
            ConfigurationError("config"),
            ScanError("scan"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except LicenseAnalyzerError:
                pass  # Expected - all should be caught
            else:
                raise AssertionError(f"{type(exc).__name__} not caught by base")
