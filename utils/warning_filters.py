"""
Custom warning filters for external dependencies.

This module provides centralized warning management for known issues
in third-party libraries that we cannot fix directly.
"""

import warnings
from typing import Any


def filter_chromadb_warnings(  # noqa: PLR0913
    message: warnings.WarningMessage,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: Any = None,
    line: str | None = None,
) -> bool:
    """
    Filter known ChromaDB deprecation warnings.

    Returns True to suppress the warning, False to show it.

    Note: lineno, file, and line parameters are required by Python's
    warning filter protocol but are not used in our implementation.
    """
    # Mark unused parameters to satisfy linters
    _ = lineno, file, line

    # Suppress Pydantic deprecation warnings from ChromaDB
    if category is DeprecationWarning:
        str_message = str(message)

        # Check for known ChromaDB-related warnings and source
        return any(
            pattern in str_message
            for pattern in [
                "Support for class-based `config` is deprecated",
                "Accessing the 'model_fields' attribute on the instance",
                "model_fields",  # Catch variations
            ]
        ) and ("chromadb" in filename or "pydantic" in filename)

    return False


def setup_warning_filters() -> None:
    """Configure all warning filters for the application."""
    # Add our custom filter
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, message=".*model_fields.*"
    )
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, message=".*class-based.*config.*"
    )

    # Also filter by module for extra safety
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="chromadb.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.*")
