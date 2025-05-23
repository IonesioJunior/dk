def test_example() -> None:
    """Example test to verify test setup is working."""
    assert True


def test_with_fixture(mock_env: dict[str, str]) -> None:
    """Test using a fixture from conftest.py."""
    assert mock_env["TEST_MODE"] == "true"
    assert mock_env["DEBUG"] == "true"
