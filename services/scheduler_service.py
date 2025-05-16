import asyncio
import logging
from typing import Optional

from config.settings import Settings
from syftbox.scheduler import scheduler

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing the task scheduler."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.scheduler = scheduler
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the scheduler service."""
        try:
            logger.info("Starting scheduler service")
            await self.scheduler.start()
            logger.info("Scheduler service started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler service: {e}")
            raise

    async def start_in_background(self) -> None:
        """Start the scheduler in a background task."""
        if self._task and not self._task.done():
            logger.warning("Scheduler already running")
            return

        self._task = asyncio.create_task(self.start())
        logger.info("Scheduler started in background")

    async def stop(self) -> None:
        """Stop the scheduler service."""
        try:
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

            await self.scheduler.stop()
            logger.info("Scheduler service stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler service: {e}")

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._task is not None and not self._task.done()
