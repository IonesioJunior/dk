"""
Early warning suppression for third-party libraries.

This module should be imported before any other imports to ensure
warnings are suppressed as early as possible.
"""

import warnings

# Suppress all deprecation warnings from chromadb and pydantic modules
warnings.filterwarnings("ignore", category=DeprecationWarning, module="chromadb.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.*")

# Also use message-based filtering with simpler patterns
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*model_fields.*"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*class-based.*"
)

# For extra safety, filter specific known messages
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message="Accessing the 'model_fields' attribute on the instance is deprecated",
)

# Install custom filter
warnings.filterwarnings("ignore", category=DeprecationWarning)
