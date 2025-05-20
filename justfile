# Clean up Python cache and virtual environment
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    rm -rf .venv
    rm -rf .ruff_cache
    rm -rf log.txt
    rm -rf cache

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
