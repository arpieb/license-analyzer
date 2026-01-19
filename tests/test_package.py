"""Basic package tests for license-analyzer."""


def test_package_imports() -> None:
    """Test that the main package can be imported."""
    import license_analyzer

    assert license_analyzer.__version__ == "0.1.0"


def test_cli_imports() -> None:
    """Test that the CLI module can be imported."""
    from license_analyzer.cli import main

    assert main is not None


def test_exceptions_imports() -> None:
    """Test that the exceptions module can be imported."""
    from license_analyzer.exceptions import LicenseAnalyzerError

    assert issubclass(LicenseAnalyzerError, Exception)


def test_subpackages_import() -> None:
    """Test that all subpackages can be imported."""
    import license_analyzer.analysis
    import license_analyzer.cache
    import license_analyzer.config
    import license_analyzer.models
    import license_analyzer.output
    import license_analyzer.resolvers

    # Verify modules exist (avoiding F401 by using the imports)
    assert license_analyzer.models is not None
    assert license_analyzer.resolvers is not None
    assert license_analyzer.analysis is not None
    assert license_analyzer.cache is not None
    assert license_analyzer.output is not None
    assert license_analyzer.config is not None
