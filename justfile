# Clean up Python cache and virtual environment
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    rm -rf .venv
    rm -rf .ruff_cache
    rm -rf log.txt
    rm -rf cache
    rm -rf config.json


# Run pre-commit hooks on all files (except bandit)
lint:
    SKIP=bandit uv run pre-commit run --all-files

# Run bandit security checks
bandit:
    uv run bandit -r agent api rpc syftbox database -c pyproject.toml

# Create a new Python 3.12 venv and install dependencies with UV including dev dependencies
setup:
    # python3.12 -m venv .venv
    uv venv -p 3.12 .venv
    uv pip install --upgrade pip
    uv pip install -e ".[dev]"
    uv run pre-commit install

# Run all tests
test:
    uv run pytest tests/ -v

# Run tests with coverage
test-cov:
    uv run pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Run only unit tests
test-unit:
    uv run pytest tests/unit/ -v

# Run only integration tests
test-integration:
    uv run pytest tests/integration/ -v
