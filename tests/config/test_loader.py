"""Tests for configuration file loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from license_analyzer.config.loader import (
    find_config_file,
    load_config,
    load_config_file,
)
from license_analyzer.exceptions import ConfigurationError
from license_analyzer.models.config import AnalyzerConfig


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_finds_yaml_extension(self, tmp_path: Path) -> None:
        """Test that .yaml extension is found."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        result = find_config_file(tmp_path)
        assert result == config_file

    def test_finds_yml_extension(self, tmp_path: Path) -> None:
        """Test that .yml extension is found."""
        config_file = tmp_path / ".license-analyzer.yml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        result = find_config_file(tmp_path)
        assert result == config_file

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Test that None is returned when no config file exists."""
        result = find_config_file(tmp_path)
        assert result is None

    def test_yaml_takes_precedence_over_yml(self, tmp_path: Path) -> None:
        """Test that .yaml file takes precedence over .yml."""
        yaml_file = tmp_path / ".license-analyzer.yaml"
        yml_file = tmp_path / ".license-analyzer.yml"
        yaml_file.write_text("allowed_licenses:\n  - MIT\n")
        yml_file.write_text("allowed_licenses:\n  - Apache-2.0\n")

        result = find_config_file(tmp_path)
        assert result == yaml_file

    def test_uses_cwd_when_no_start_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that current working directory is used when start_dir is None."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")
        monkeypatch.chdir(tmp_path)

        result = find_config_file()
        assert result == config_file


class TestLoadConfigFile:
    """Tests for load_config_file function."""

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid configuration file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "allowed_licenses:\n"
            "  - MIT\n"
            "  - Apache-2.0\n"
            "ignored_packages:\n"
            "  - internal-tool\n"
        )

        result = load_config_file(config_file)
        assert isinstance(result, AnalyzerConfig)
        assert result.allowed_licenses == ["MIT", "Apache-2.0"]
        assert result.ignored_packages == ["internal-tool"]

    def test_loads_config_with_overrides(self, tmp_path: Path) -> None:
        """Test loading configuration with license overrides."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "overrides:\n"
            "  some-package:\n"
            "    license: MIT\n"
            "    reason: Confirmed with maintainer\n"
        )

        result = load_config_file(config_file)
        assert result.overrides is not None
        assert "some-package" in result.overrides
        assert result.overrides["some-package"].license == "MIT"

    def test_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        """Test that empty file returns default config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        result = load_config_file(config_file)
        assert result.allowed_licenses is None
        assert result.ignored_packages is None
        assert result.overrides is None

    def test_file_with_only_comments_returns_defaults(self, tmp_path: Path) -> None:
        """Test that file with only comments returns default config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("# This is a comment\n# Another comment\n")

        result = load_config_file(config_file)
        assert result.allowed_licenses is None

    def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid YAML syntax raises ConfigurationError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n  invalid yaml here")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_file(config_file)
        assert "Invalid YAML syntax" in str(exc_info.value)
        assert str(config_file) in str(exc_info.value)

    def test_unknown_fields_raise_error(self, tmp_path: Path) -> None:
        """Test that unknown fields raise ConfigurationError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("unknown_field: value\n")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_file(config_file)
        assert "Invalid configuration" in str(exc_info.value)
        assert "unknown_field" in str(exc_info.value)

    def test_invalid_field_type_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid field type raises ConfigurationError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("allowed_licenses: not_a_list\n")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_file(config_file)
        assert "Invalid configuration" in str(exc_info.value)
        assert "allowed_licenses" in str(exc_info.value)

    def test_non_dict_root_raises_error(self, tmp_path: Path) -> None:
        """Test that YAML with non-dict root raises ConfigurationError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("- item1\n- item2\n")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_file(config_file)
        assert "expected a mapping at root level" in str(exc_info.value)

    def test_unreadable_file_raises_error(self, tmp_path: Path) -> None:
        """Test that unreadable file raises ConfigurationError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")
        config_file.chmod(0o000)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config_file(config_file)
            assert "Cannot read configuration file" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            config_file.chmod(0o644)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_from_custom_path(self, tmp_path: Path) -> None:
        """Test loading from a custom config path."""
        config_file = tmp_path / "custom-config.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        result = load_config(str(config_file))
        assert result.allowed_licenses == ["MIT"]

    def test_auto_discovers_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test auto-discovery of config file in current directory."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - Apache-2.0\n")
        monkeypatch.chdir(tmp_path)

        result = load_config()
        assert result.allowed_licenses == ["Apache-2.0"]

    def test_returns_defaults_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that defaults are returned when no config file exists."""
        monkeypatch.chdir(tmp_path)

        result = load_config()
        assert result.allowed_licenses is None
        assert result.ignored_packages is None
        assert result.overrides is None

    def test_custom_path_overrides_discovery(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that custom path takes precedence over auto-discovery."""
        # Create both auto-discover and custom config files
        auto_config = tmp_path / ".license-analyzer.yaml"
        auto_config.write_text("allowed_licenses:\n  - MIT\n")

        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        custom_config = custom_dir / "my-config.yaml"
        custom_config.write_text("allowed_licenses:\n  - Apache-2.0\n")

        monkeypatch.chdir(tmp_path)

        # Custom path should be used
        result = load_config(str(custom_config))
        assert result.allowed_licenses == ["Apache-2.0"]

    def test_invalid_custom_path_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid custom path raises ConfigurationError."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("unknown_field: value\n")

        with pytest.raises(ConfigurationError):
            load_config(str(config_file))

    def test_invalid_discovered_config_raises_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid discovered config raises ConfigurationError."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("unknown_field: value\n")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigurationError):
            load_config()
