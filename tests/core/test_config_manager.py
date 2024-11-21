import os

import pytest
import yaml

from app.core.config_manager import ConfigManager, is_truthy, is_falsy


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with test YAML files."""
    config_dir = tmp_path / "app-configs"
    config_dir.mkdir()

    # Create default config
    default_config = {
        "log_level": "INFO",
        "log_stdout": True,
        "db_name": "test_db",
        "db_user": "test_user",
        "db_pass": "test_pass",
        "db_host": "localhost",
        "db_port": "5432"
    }

    with open(config_dir / "default.yml", "w") as f:
        yaml.dump(default_config, f)

    # Create env-specific config
    dev_config = {
        "log_level": "DEBUG",
        "db_name": "dev_db"
    }

    with open(config_dir / "dev.yml", "w") as f:
        yaml.dump(dev_config, f)

    return str(config_dir)


def test_config_loading(temp_config_dir, monkeypatch):
    """Test basic configuration loading."""
    monkeypatch.setenv("CAPI_CONF_PATH", temp_config_dir)
    monkeypatch.setenv("CAPI_ENV", "dev")

    config = ConfigManager()

    # Check values from default.yml
    assert config.log_stdout is True
    assert config.db_user == "test_user"
    assert config.db_pass == "test_pass"
    assert config.db_host == "localhost"
    assert config.db_port == "5432"

    # Check override from dev.yml
    assert config.log_level == "DEBUG"
    assert config.db_name == "dev_db"


def test_environment_variable_override(temp_config_dir, monkeypatch):
    """Test environment variable overrides."""
    monkeypatch.setenv("CAPI_CONF_PATH", temp_config_dir)
    monkeypatch.setenv("CAPI_ENV", "dev")
    monkeypatch.setenv("CAPI_DB_HOST", "custom-host")
    monkeypatch.setenv("CAPI_LOG_STDOUT", "false")

    config = ConfigManager()

    # Check environment variable overrides
    assert config.db_host == "custom-host"
    assert config.log_stdout is False


def test_default_environment(temp_config_dir, monkeypatch):
    """Test default environment when none specified."""
    monkeypatch.setenv("CAPI_CONF_PATH", temp_config_dir)
    monkeypatch.delenv("CAPI_ENV", raising=False)

    config = ConfigManager()
    assert config.env_name == "local"


def test_database_url_construction(temp_config_dir, monkeypatch):
    """Test database URL construction."""
    monkeypatch.setenv("CAPI_CONF_PATH", temp_config_dir)
    monkeypatch.setenv("CAPI_ENV", "dev")

    config = ConfigManager()
    expected_url = f"postgresql+asyncpg://{config.db_user}:{config.db_pass}@{config.db_host}:{config.db_port}/{config.db_name}"
    assert config.database_url == expected_url


def test_missing_config_file(temp_config_dir, monkeypatch):
    """Test handling of missing config files."""
    monkeypatch.setenv("CAPI_CONF_PATH", temp_config_dir)
    monkeypatch.setenv("CAPI_ENV", "nonexistent")

    config = ConfigManager()
    # Should still load default config even if env-specific config is missing
    assert config.log_stdout is True
    assert config.db_user == "test_user"


def test_env_var_type_conversion(temp_config_dir, monkeypatch):
    """Test environment variable type conversion."""
    monkeypatch.setenv("CAPI_CONF_PATH", temp_config_dir)
    monkeypatch.setenv("CAPI_ENV", "dev")

    # Test boolean conversion
    monkeypatch.setenv("CAPI_LOG_STDOUT", "true")
    config = ConfigManager()
    assert config.log_stdout is True

    monkeypatch.setenv("CAPI_LOG_STDOUT", "1")
    config = ConfigManager()
    assert config.log_stdout is True

    monkeypatch.setenv("CAPI_LOG_STDOUT", "false")
    config = ConfigManager()
    assert config.log_stdout is False


def test_empty_env_vars(temp_config_dir, monkeypatch):
    """Test handling of empty environment variables."""
    monkeypatch.setenv("CAPI_CONF_PATH", temp_config_dir)
    monkeypatch.setenv("CAPI_ENV", "dev")
    monkeypatch.setenv("CAPI_DB_HOST", "")

    config = ConfigManager()
    # Empty env var should not override config file value
    assert config.db_host == "localhost"


def test_truthy_falsy_helpers():
    """Test truthy and falsy helper functions."""
    # Test truthy values
    assert is_truthy(True)
    assert is_truthy("true")
    assert is_truthy("True")
    assert is_truthy("1")
    assert is_truthy("yes")
    assert not is_truthy("false")
    assert not is_truthy("0")

    # Test falsy values
    assert is_falsy(False)
    assert is_falsy("false")
    assert is_falsy("False")
    assert is_falsy("0")
    assert is_falsy("no")
    assert not is_falsy("true")
    assert not is_falsy("1")


def test_config_environment_export(temp_config_dir, monkeypatch):
    """Test exporting of config values to environment variables."""
    monkeypatch.setenv("CAPI_CONF_PATH", temp_config_dir)
    monkeypatch.setenv("CAPI_ENV", "dev")

    config = ConfigManager()

    # Check if config values are exported to environment
    assert os.environ.get("db_name") == config.db_name
    assert os.environ.get("db_host") == config.db_host
