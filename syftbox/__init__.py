"""Syftbox module for Syft-Core integration.

This module provides a singleton SyftClient for interacting with the Syft-Core package
and a PeriodicJobScheduler for executing async tasks at regular intervals.
"""

from .client import SyftClient, syft_client
from .scheduler import PeriodicJobScheduler, scheduler

__all__ = ["PeriodicJobScheduler", "SyftClient", "scheduler", "syft_client"]
