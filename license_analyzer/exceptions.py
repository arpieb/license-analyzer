"""Custom exceptions for license-analyzer."""


class LicenseAnalyzerError(Exception):
    """Base exception for all license-analyzer errors."""

    pass


class NetworkError(LicenseAnalyzerError):
    """Exception raised when a network request fails."""

    pass


class ConfigurationError(LicenseAnalyzerError):
    """Exception raised when configuration is invalid."""

    pass


class ScanError(LicenseAnalyzerError):
    """Exception raised when a scan operation fails."""

    pass
