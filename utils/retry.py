import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exception_types: Optional[tuple[type[Exception], ...]] = None,
    **kwargs: Any,
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: The async function to retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor to multiply the wait time by on each retry
        exception_types: Tuple of exception types to catch (default: all exceptions)
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the function call

    Raises:
        The last exception if all retries fail
    """
    if exception_types is None:
        exception_types = (Exception,)

    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except exception_types as e:
            last_exception = e

            if attempt == max_retries - 1:
                logger.error(
                    f"All {max_retries} retry attempts failed for {func.__name__}",
                )
                raise

            wait_time = backoff_factor**attempt
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                f"Retrying in {wait_time} seconds...",
            )
            await asyncio.sleep(wait_time)

    # This should never be reached, but satisfies type checkers
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected error in retry logic")
