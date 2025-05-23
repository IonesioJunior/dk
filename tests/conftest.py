from pathlib import Path

import pytest


@pytest.fixture()
def test_data_dir() -> Path:
    """Return the path to the test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Mock environment variables for testing."""
    test_env = {
        "DEBUG": "true",
        "SYFTBOX_SERVER_URL": "http://localhost:8080",
        "TEST_MODE": "true",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env
