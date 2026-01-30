"""Default configuration values for license-analyzer."""

from __future__ import annotations

from license_analyzer.models.config import AnalyzerConfig

# Default configuration file names to search for
DEFAULT_CONFIG_NAMES = [".license-analyzer.yaml", ".license-analyzer.yml"]


def get_default_config() -> AnalyzerConfig:
    """Get the default configuration.

    Returns:
        AnalyzerConfig with all defaults (all fields None).
    """
    return AnalyzerConfig()
