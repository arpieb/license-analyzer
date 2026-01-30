"""Configuration handling for license-analyzer."""
from __future__ import annotations

from license_analyzer.config.defaults import DEFAULT_CONFIG_NAMES, get_default_config
from license_analyzer.config.loader import (
    find_config_file,
    load_config,
    load_config_file,
)
from license_analyzer.models.config import AnalyzerConfig, LicenseOverride

__all__ = [
    "AnalyzerConfig",
    "DEFAULT_CONFIG_NAMES",
    "LicenseOverride",
    "find_config_file",
    "get_default_config",
    "load_config",
    "load_config_file",
]
