import json
import logging
from datetime import datetime
from typing import Any, Optional

from agent.agent import Agent
from config.settings import Settings
from services.websocket_types import (
    CONTENT_TYPE_ERROR,
    CONTENT_TYPE_PROMPT_RESPONSE,
    DirectMessage,
    ErrorMessage,
    PromptQueryMessage,
    PromptResponseMessage,
)

logger = logging.getLogger(__name__)


class PromptService:
    """Service for handling prompt queries received via WebSocket messages."""

    def __init__(self, settings: Settings, agent: Agent) -> None:
        self.settings = settings
        self.agent = agent
        self.active_conversations: dict[str, dict[str, Any]] = {}

    async def handle_prompt_query_message(
        self,
        prompt_query: PromptQueryMessage,
        original_message: DirectMessage,
        websocket_service: Any,
    ) -> None:
        """
        Handle a PromptQueryMessage received through WebSocket.

        Args:
            prompt_query: The parsed PromptQueryMessage
            original_message: The original DirectMessage containing the prompt
            websocket_service: The WebSocket service for sending responses
        """
        try:
            # Extract sender information
            from_user = original_message.from_user
            logger.info(
                f"Processing prompt query from {from_user}: {prompt_query.prompt}",
            )
            logger.info(f"Prompt ID: {prompt_query.prompt_id}")

            # Create or update conversation context
            conversation_key = f"{from_user}_conversation"
            if conversation_key not in self.active_conversations:
                self.active_conversations[conversation_key] = {
                    "user_id": from_user,
                    "started": datetime.utcnow(),
                    "messages": [],
                }

            # Add the prompt to conversation history
            self.active_conversations[conversation_key]["messages"].append(
                {
                    "role": "user",
                    "content": prompt_query.prompt,
                    "timestamp": datetime.utcnow(),
                    "documents": prompt_query.documents,
                    "prompt_id": prompt_query.prompt_id,  # Store prompt_id in history
                },
            )

            # Process the prompt with the agent
            response = await self._process_prompt_with_agent(
                prompt_query.prompt,
                prompt_query.documents,
                conversation_key,
            )

            # Send response back to the user with prompt_id
            await self._send_response(
                response,
                from_user,
                websocket_service,
                prompt_id=prompt_query.prompt_id,  # Pass prompt_id to response
            )

            # Update conversation history with response
            self.active_conversations[conversation_key]["messages"].append(
                {
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.utcnow(),
                    "prompt_id": prompt_query.prompt_id,  # Store prompt_id in history
                },
            )

        except Exception as e:
            logger.error(f"Error handling prompt query: {e}", exc_info=True)
            # Send error response to user with prompt_id
            await self._send_error_response(
                str(e),
                original_message.from_user,
                websocket_service,
                prompt_id=prompt_query.prompt_id
                if "prompt_query" in locals()
                else None,
            )

    async def _process_prompt_with_agent(
        self,
        prompt: str,
        documents: Optional[list[str]],
        conversation_key: str,
    ) -> str:
        """
        Process the prompt using the agent.

        Args:
            prompt: The user's prompt
            documents: Optional list of documents to reference
            conversation_key: Key for tracking conversation context

        Returns:
            The agent's response
        """
        try:
            # Get conversation history for context
            conversation = self.active_conversations.get(conversation_key, {})
            messages = conversation.get("messages", [])

            # Build conversation history for agent
            conversation_history = []
            for msg in messages[:-1]:  # Exclude the current message
                conversation_history.append(
                    {"role": msg["role"], "content": msg["content"]},
                )

            # Include documents in the prompt if provided
            enhanced_prompt = prompt
            if documents:
                enhanced_prompt = (
                    f"{prompt}\n\nRelevant documents: {', '.join(documents)}"
                )

            # Process with agent
            return await self.agent.process_message(
                conversation_id=conversation_key,
                user_message=enhanced_prompt,
                conversation_history=conversation_history,
            )

        except Exception as e:
            logger.error(f"Error processing prompt with agent: {e}")
            raise

    async def _send_response(
        self,
        response: str,
        recipient: str,
        websocket_service: Any,
        prompt_id: str,
    ) -> None:
        """
        Send a response back to the user via WebSocket.

        Args:
            response: The response content
            recipient: The recipient user ID
            websocket_service: The WebSocket service for sending messages
            prompt_id: The unique identifier from the original prompt query
        """
        try:
            # Create validated response message with prompt_id
            prompt_response = PromptResponseMessage(
                prompt_id=prompt_id,
                response=response,
                timestamp=datetime.utcnow().isoformat(),
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
                to=recipient,
                content=response_json,
                # Don't set timestamp - let the client handle it for proper signing
            )

            # Send via WebSocket client
            if websocket_service.client:
                await websocket_service.client.send_message(msg)
                logger.info(f"Sent response to {recipient}")
            else:
                logger.error("WebSocket client not available")

        except Exception as e:
            logger.error(f"Error sending response: {e}")
            raise

    async def _send_error_response(
        self,
        error_message: str,
        recipient: str,
        websocket_service: Any,
        prompt_id: Optional[str] = None,
    ) -> None:
        """
        Send an error response to the user.

        Args:
            error_message: The error message
            recipient: The recipient user ID
            websocket_service: The WebSocket service for sending messages
            prompt_id: Optional unique identifier from the original prompt query
        """
        try:
            # Create validated error message with optional prompt_id
            error_msg = ErrorMessage(
                prompt_id=prompt_id,
                error=error_message,
                timestamp=datetime.utcnow().isoformat(),
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
                to=recipient,
                content=error_json,
                # Don't set timestamp - let the client handle it for proper signing
            )

            if websocket_service.client:
                await websocket_service.client.send_message(msg)
                logger.info(f"Sent error response to {recipient}")

        except Exception as e:
            logger.error(f"Error sending error response: {e}")

    def get_conversation_history(self, user_id: str) -> Optional[dict[str, Any]]:
        """
        Get conversation history for a specific user.

        Args:
            user_id: The user ID

        Returns:
            The conversation history or None if not found
        """
        conversation_key = f"{user_id}_conversation"
        return self.active_conversations.get(conversation_key)

    def clear_conversation_history(self, user_id: str) -> bool:
        """
        Clear conversation history for a specific user.

        Args:
            user_id: The user ID

        Returns:
            True if cleared, False if not found
        """
        conversation_key = f"{user_id}_conversation"
        if conversation_key in self.active_conversations:
            del self.active_conversations[conversation_key]
            logger.info(f"Cleared conversation history for {user_id}")
            return True
        return False

    async def close(self) -> None:
        """Clean up resources when shutting down."""
        # Clear all active conversations
        self.active_conversations.clear()
        logger.info("PromptService shut down")
