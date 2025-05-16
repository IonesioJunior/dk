"""Periodic job scheduler for executing async tasks at regular intervals.

This module provides a singleton scheduler for registering and running periodic tasks.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from collections.abc import Coroutine

logger = logging.getLogger(__name__)


class PeriodicJobScheduler:
    """Singleton class for scheduling and executing periodic async jobs.

    This class ensures only one scheduler instance exists throughout the application
    and manages the scheduling and execution of periodic async tasks.
    """

    _instance: PeriodicJobScheduler | None = None
    _is_running: bool = False
    _jobs: dict[
        str,
        tuple[Callable[..., Coroutine[Any, Any, Any]], float, float, dict[str, Any]],
    ] = {}
    _tasks: list[asyncio.Task] = []

    def __new__(cls) -> PeriodicJobScheduler:
        """Ensure only one instance of PeriodicJobScheduler is created."""
        if cls._instance is None:
            instance = super().__new__(cls)
            cls._instance = instance
        return cls._instance

    def register_job(
        self,
        job_id: str,
        coroutine_func: Callable[..., Coroutine[Any, Any, Any]],
        interval: float,
        initial_delay: float = 0,
        **kwargs: Any,
    ) -> None:
        """Register a new periodic job.

        Args:
            job_id: Unique identifier for the job
            coroutine_func: Async function to execute periodically
            interval: Time in seconds between job executions
            initial_delay: Time in seconds to wait before first execution
            **kwargs: Additional arguments to pass to the coroutine function
        """
        if job_id in self._jobs:
            logger.warning(
                f"Job {job_id} already registered. Overwriting previous job.",
            )

        self._jobs[job_id] = (coroutine_func, interval, initial_delay, kwargs)
        logger.info(f"Registered periodic job '{job_id}' with interval {interval}s")

    def unregister_job(self, job_id: str) -> bool:
        """Unregister a job by its ID.

        Args:
            job_id: The ID of the job to unregister

        Returns:
            bool: True if the job was found and unregistered, False otherwise
        """
        if job_id in self._jobs:
            self._jobs.pop(job_id)
            logger.info(f"Unregistered periodic job '{job_id}'")
            return True
        return False

    def get_job(
        self,
        job_id: str,
    ) -> (
        tuple[Callable[..., Coroutine[Any, Any, Any]], float, float, dict[str, Any]]
        | None
    ):
        """Get a registered job by its ID.

        Args:
            job_id: The ID of the job to retrieve

        Returns:
            Optional job details or None if not found
        """
        return self._jobs.get(job_id)

    def list_jobs(
        self,
    ) -> dict[
        str,
        tuple[Callable[..., Coroutine[Any, Any, Any]], float, float, dict[str, Any]],
    ]:
        """List all registered jobs.

        Returns:
            Dictionary of job IDs to job details
        """
        return self._jobs.copy()

    async def _run_job(
        self,
        job_id: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        interval: float,
        kwargs: dict[str, Any],
    ) -> None:
        """Run a job periodically.

        Args:
            job_id: The job identifier
            func: The coroutine function to execute
            interval: Time in seconds between executions
            kwargs: Additional arguments to pass to the function
        """
        while self._is_running:
            start_time = time.time()
            try:
                await func(**kwargs)
            except asyncio.CancelledError:
                # Handle cancellation gracefully
                logger.info(f"Job '{job_id}' cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic job '{job_id}': {e}")

            # If we're no longer running, don't sleep
            if not self._is_running:
                break

            # Calculate sleep time, accounting for execution duration
            execution_time = time.time() - start_time
            sleep_time = max(0, interval - execution_time)

            if sleep_time > 0:
                try:
                    # Use a short sleep interval and check self._is_running
                    # frequently to allow for faster cancellation
                    sleep_increment = 0.1  # 100ms intervals
                    sleep_count = int(sleep_time / sleep_increment)

                    for _ in range(sleep_count):
                        if not self._is_running:
                            break
                        await asyncio.sleep(sleep_increment)

                    # Handle remaining sleep time
                    remaining_sleep = sleep_time - (sleep_count * sleep_increment)
                    if remaining_sleep > 0 and self._is_running:
                        await asyncio.sleep(remaining_sleep)
                except asyncio.CancelledError:
                    # Handle cancellation during sleep
                    logger.info(f"Job '{job_id}' sleep interrupted")
                    break

    async def start(self) -> None:
        """Start the scheduler and all registered jobs."""
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        self._is_running = True
        logger.info("Starting periodic job scheduler")

        # Start all registered jobs
        for job_id, (func, interval, initial_delay, kwargs) in self._jobs.items():
            if initial_delay > 0:
                # Schedule with initial delay
                task = asyncio.create_task(
                    self._schedule_with_delay(
                        job_id,
                        func,
                        interval,
                        initial_delay,
                        kwargs,
                    ),
                )
            else:
                # Schedule immediately
                task = asyncio.create_task(
                    self._run_job(job_id, func, interval, kwargs),
                )

            self._tasks.append(task)

    async def _schedule_with_delay(
        self,
        job_id: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        interval: float,
        delay: float,
        kwargs: dict[str, Any],
    ) -> None:
        """Schedule a job with an initial delay.

        Args:
            job_id: The job identifier
            func: The coroutine function to execute
            interval: Time in seconds between executions
            delay: Initial delay in seconds before first execution
            kwargs: Additional arguments to pass to the function
        """
        await asyncio.sleep(delay)
        await self._run_job(job_id, func, interval, kwargs)

    async def stop(self) -> None:
        """Stop the scheduler and all running jobs."""
        if not self._is_running:
            logger.warning("Scheduler is not running")
            return

        self._is_running = False
        logger.info("Stopping periodic job scheduler")

        # Cancel all running tasks with proper handling
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete cancellation with timeout
        if self._tasks:
            try:
                # Use a timeout to ensure we don't hang indefinitely
                await asyncio.wait(self._tasks, timeout=2.0)

                # Explicitly gather with return_exceptions
                # to handle any cancellation errors
                await asyncio.gather(*self._tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error during scheduler shutdown: {e}")

        # Clear tasks list
        self._tasks = []

        # Extra safety to ensure we're fully stopped
        await asyncio.sleep(0.1)

    def reset(self) -> None:
        """Reset the scheduler, clearing all registered jobs."""
        self._jobs.clear()
        logger.info("Scheduler reset, all jobs cleared")


# Provide a singleton instance
scheduler = PeriodicJobScheduler()
