"""WebSocket message handler for SyftBox integration.

This module provides a class-based approach to handle websocket messages.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WebSocketMessageHandler:
    """WebSocket message handler.

    This class encapsulates the websocket service instance used for message handling.
    It provides a cleaner approach than using global variables.
    """

    _instance: Optional['WebSocketMessageHandler'] = None

    def __new__(cls) -> 'WebSocketMessageHandler':
        """Ensure singleton behavior."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._websocket_service = None
        return cls._instance

    @property
    def websocket_service(self) -> Any:
        """Get the websocket service instance."""
        return self._websocket_service

    @websocket_service.setter
    def websocket_service(self, service: Any) -> None:
        """Set the websocket service instance."""
        self._websocket_service = service
        logger.info("WebSocket service set for message handling")

    async def process_messages(self) -> None:
        """Process incoming websocket messages.

        This method continuously processes messages from the websocket client queue
        using the WebSocketService message handler.
        """
        if self._websocket_service is None or self._websocket_service.client is None:
            return

        try:
            # Use wait_for to avoid blocking indefinitely
            import asyncio

            msg = await asyncio.wait_for(
                self._websocket_service.client.messages(),
                timeout=0.1
            )

            # Process the message using the WebSocketService message handler
            await self._websocket_service.message_handler(msg)

        except asyncio.TimeoutError:
            # No messages available, this is normal
            pass
        except Exception as e:
            logger.error(f"Error processing websocket message: {e}")


# Create singleton instance
message_handler = WebSocketMessageHandler()
