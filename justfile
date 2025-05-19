# Clean up Python cache and virtual environment
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    rm -rf .venv
    rm -rf .ruff_cache
    rm -rf vectordb
    rm -rf log.txt
