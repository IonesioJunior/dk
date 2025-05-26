"""Service for sending triage notifications via WebSocket."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from policies.triage_models import TriageRequest
from services.websocket_types import (
    CONTENT_TYPE_ERROR,
    CONTENT_TYPE_PROMPT_RESPONSE,
    ErrorMessage,
    PromptResponseMessage,
)

logger = logging.getLogger(__name__)


class TriageNotificationService:
    """Service to handle triage notifications."""

    def __init__(self, websocket_service: Any) -> None:
        """Initialize with WebSocket service dependency."""
        self.websocket_service = websocket_service

    async def send_approval_notification(self, triage_request: TriageRequest) -> bool:
        """Send the approved response to the user."""
        try:
            # Create validated response message with prompt_id
            prompt_response = PromptResponseMessage(
                prompt_id=triage_request.prompt_id,
                response=triage_request.generated_response,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # Create the response data structure
            response_data = {
                "content_type": CONTENT_TYPE_PROMPT_RESPONSE,
                "content": prompt_response.model_dump(),
            }

            # Convert to JSON string for sending
            response_json = json.dumps(response_data)

            # Create message with Message class from client
            from client.client import Message as ClientMessage

            msg = ClientMessage(
                from_user="",  # Let the client set this for proper signing
                to=triage_request.user_id,
                content=response_json,
                # Don't set timestamp - let the client handle it for proper signing
            )

            # Send via WebSocket client
            if self.websocket_service.client:
                await self.websocket_service.client.send_message(msg)
                logger.info(
                    f"Sent approved triage response to {triage_request.user_id} "
                    f"for prompt {triage_request.prompt_id}"
                )
                return True
            logger.error("WebSocket client not available")
            return False

        except Exception as e:
            logger.error(f"Error sending approval notification: {e}", exc_info=True)
            return False

    async def send_rejection_notification(self, triage_request: TriageRequest) -> bool:
        """Send rejection message to the user."""
        try:
            # Build rejection message
            rejection_message = (
                f"Your request has been reviewed and rejected. "
                f"Reason: {triage_request.rejection_reason or 'Not specified'}"
            )

            # Create validated error message with prompt_id
            error_msg = ErrorMessage(
                prompt_id=triage_request.prompt_id,
                error=rejection_message,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # Create the error data structure
            error_data = {
                "content_type": CONTENT_TYPE_ERROR,
                "content": error_msg.model_dump(),
            }

            # Convert to JSON string for sending
            error_json = json.dumps(error_data)

            # Create message with Message class from client
            from client.client import Message as ClientMessage

            msg = ClientMessage(
                from_user="",  # Let the client set this for proper signing
                to=triage_request.user_id,
                content=error_json,
                # Don't set timestamp - let the client handle it for proper signing
            )

            # Send via WebSocket client
            if self.websocket_service.client:
                await self.websocket_service.client.send_message(msg)
                logger.info(
                    f"Sent rejection notification to {triage_request.user_id} "
                    f"for prompt {triage_request.prompt_id}"
                )
                return True
            logger.error("WebSocket client not available")
            return False

        except Exception as e:
            logger.error(f"Error sending rejection notification: {e}", exc_info=True)
            return False
