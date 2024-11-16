from dataclasses import dataclass


@dataclass
class TestConfig:
    """Test configuration class that mimics the real ConfigManager"""
    env_name: str = "test"
    database_url: str = "postgresql+asyncpg://test_user:test_pass@test_host:1234/test_db"
    log_level: str = "DEBUG"
    log_stdout: bool = True
    log_file: str = "./.logs/test.log"
    sqlalchemy_log_all: bool = False
    gcp_project: str = "test-project"
    gcs_bucket: str = "test-bucket"
    gcs_datasets_path: str = "test-datasets"
    api_v1_prefix: str = "/v1"
    ui_url: str = "http://test.example.com"
    ui_url_settings: str = "/settings"
    use_api_ui: bool = False
    base_domain_name: str = "test.example.com"
    run_with_scheduler: bool = True
    scheduler_zen_url: str = "http://test-scheduler:5200"
    auth0_client_id: str = "test-client-id"
    auth0_client_secret: str = "test-client-secret"
    auth0_domain: str = "test.auth0.com"
    app_secret_key: str = "test-secret-key"
    stripe_secret_key: str = "test-stripe-key"
    stripe_webhook_secret: str = "test-webhook-secret"
    fine_tuning_job_min_credits: int = 5
    new_user_credits: int = 5


def pytest_configure(config):
    """
    Pytest hook that runs before test collection.
    This allows us to mock the config before any tests or fixtures are loaded.
    """
    import sys

    # Create a mock module for config_manager
    from types import ModuleType
    mock_config_module = ModuleType('app.core.config_manager')
    mock_config_module.config = TestConfig()

    # Add it to sys.modules so subsequent imports will use our mock
    sys.modules['app.core.config_manager'] = mock_config_module