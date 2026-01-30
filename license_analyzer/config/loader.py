"""Configuration file discovery and loading for license-analyzer."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from license_analyzer.config.defaults import DEFAULT_CONFIG_NAMES, get_default_config
from license_analyzer.exceptions import ConfigurationError
from license_analyzer.models.config import AnalyzerConfig


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Find configuration file in the specified directory.

    Searches for `.license-analyzer.yaml` first, then `.license-analyzer.yml`.

    Args:
        start_dir: Directory to search. Defaults to current working directory.

    Returns:
        Path to the configuration file if found, None otherwise.
    """
    search_dir = start_dir or Path.cwd()
    for name in DEFAULT_CONFIG_NAMES:
        config_path = search_dir / name
        if config_path.exists():
            return config_path
    return None


def load_config_file(path: Path) -> AnalyzerConfig:
    """Load and validate configuration from a YAML file.

    Args:
        path: Path to the configuration file.

    Returns:
        Validated AnalyzerConfig instance.

    Raises:
        ConfigurationError: If file cannot be read, has invalid YAML,
            or fails Pydantic validation.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, PermissionError) as e:
        raise ConfigurationError(
            f"Cannot read configuration file '{path}': {e}"
        ) from e

    # Handle empty files - return default config
    if not content.strip():
        return get_default_config()

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML syntax in '{path}': {e}"
        ) from e

    # Handle YAML that parses to None (empty or just comments)
    if data is None:
        return get_default_config()

    # Ensure root is a dict
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"Invalid configuration in '{path}': "
            f"expected a mapping at root level, got {type(data).__name__}"
        )

    try:
        return AnalyzerConfig.model_validate(data)
    except ValidationError as e:
        # Format Pydantic errors nicely
        error_messages = _format_validation_errors(e)
        raise ConfigurationError(
            f"Invalid configuration in '{path}': {error_messages}"
        ) from e


def _format_validation_errors(error: ValidationError) -> str:
    """Format Pydantic validation errors into a readable string.

    Args:
        error: The Pydantic ValidationError.

    Returns:
        Formatted error message string.
    """
    messages: list[str] = []
    for err in error.errors():
        loc = ".".join(str(x) for x in err["loc"]) if err["loc"] else "root"
        msg = err["msg"]
        messages.append(f"{loc}: {msg}")
    return "; ".join(messages)


def load_config(config_path: str | None = None) -> AnalyzerConfig:
    """Load configuration from file or use defaults.

    If a config_path is provided, loads from that file.
    Otherwise, searches for a configuration file in the current directory.
    If no file is found, returns default configuration.

    Args:
        config_path: Optional path to configuration file.
            If provided, must exist and be valid.

    Returns:
        AnalyzerConfig with loaded or default values.

    Raises:
        ConfigurationError: If the specified config file is invalid,
            or if auto-discovered config file is invalid.
    """
    if config_path is not None:
        # User specified a path - load it (Click validates existence)
        return load_config_file(Path(config_path))

    # Auto-discover config file
    discovered = find_config_file()
    if discovered is not None:
        return load_config_file(discovered)

    # No config file found - use defaults
    return get_default_config()
