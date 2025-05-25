import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from agent.agent import Agent
from api_configs.manager import APIConfigManager
from config.settings import Settings
from database.vector_db_manager import QueryParams, VectorDBManager
from services.api_config_service import APIConfigService
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
        self.vector_db = VectorDBManager()
        self.api_config_manager = APIConfigManager()
        self.api_config_service = APIConfigService()

    async def _get_related_documents(
        self, user_id: str, prompt: str
    ) -> tuple[list[str], Optional[str]]:
        """
        Get related documents for a user's prompt.

        Args:
            user_id: The user's ID
            prompt: The prompt to find related documents for

        Returns:
            A tuple of (related documents list, user policy ID if exists)
        """
        # Get user's policy for filtering documents
        user_policy_id = self.api_config_manager.get_policy_for_user(user_id)
        related_documents = []

        if not user_policy_id:
            logger.info(
                f"No policy found for user {user_id}, skipping document retrieval"
            )
            return related_documents, user_policy_id

        try:
            # Create QueryParams object with policy filter
            query_params = QueryParams(
                collection_name="documents",
                query_texts=[prompt],
                n_results=3,
                include=["documents", "metadatas", "distances"],
                where={user_policy_id: True},
            )

            logger.info(
                f"Filtering documents for user {user_id} with policy {user_policy_id}"
            )
            query_results = self.vector_db.query(query_params)

            # Extract documents from query results if they exist
            if (
                query_results
                and "documents" in query_results
                and query_results["documents"]
            ):
                # query_results["documents"] is a list of lists, we need the first list
                for doc in query_results["documents"][0]:
                    if doc:  # Make sure the document is not empty
                        related_documents.append(doc)

            logger.info(
                f"Retrieved {len(related_documents)} related documents from vector DB"
            )
        except Exception as e:
            logger.warning(f"Error retrieving documents from vector DB: {e}")
            # Continue without related documents if query fails

        return related_documents, user_policy_id

    @dataclass
    class ConversationHistoryUpdate:
        """Parameters for updating conversation history"""

        conversation_key: str
        role: str
        content: str
        prompt_id: str
        documents: Optional[list[str]] = None

    async def _update_conversation_history(
        self,
        params: ConversationHistoryUpdate,
    ) -> None:
        """
        Update the conversation history with a new message.

        Args:
            params: ConversationHistoryUpdate containing the conversation update details
        """
        entry = {
            "role": params.role,
            "content": params.content,
            "timestamp": datetime.now(timezone.utc),
            "prompt_id": params.prompt_id,
        }

        if params.documents and params.role == "user":
            entry["documents"] = params.documents

        self.active_conversations[params.conversation_key]["messages"].append(entry)

    async def _track_api_usage(
        self, user_policy_id: str, user_id: str, input_prompt: str, output_prompt: str
    ) -> None:
        """
        Track API usage for a user.

        Args:
            user_policy_id: The user's policy ID
            user_id: The user's ID
            input_prompt: The input prompt
            output_prompt: The output prompt (response)
        """
        if not user_policy_id:
            return

        try:
            # Track usage with the API config service
            self.api_config_service.track_api_usage(
                api_config_id=user_policy_id,
                user_id=user_id,
                input_prompt=input_prompt,
                output_prompt=output_prompt,
            )
            logger.info(
                f"Tracked API usage for user {user_id} with policy {user_policy_id}"
            )
        except Exception as e:
            # Log error but continue with the response
            logger.error(f"Error tracking API usage: {e}", exc_info=True)

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
                f"Processing prompt query from {from_user}: {prompt_query.prompt}"
            )
            logger.info(f"Prompt ID: {prompt_query.prompt_id}")

            # Create or update conversation context
            conversation_key = f"{from_user}_conversation"
            if conversation_key not in self.active_conversations:
                self.active_conversations[conversation_key] = {
                    "user_id": from_user,
                    "started": datetime.now(timezone.utc),
                    "messages": [],
                }

            # Get related documents and user policy
            related_documents, user_policy_id = await self._get_related_documents(
                from_user, prompt_query.prompt
            )

            # Enforce policy before processing
            if user_policy_id:
                # Import here to avoid circular dependency
                from policies.enforcer import PolicyEnforcer

                policy_enforcer = PolicyEnforcer()

                try:
                    policy_result = await policy_enforcer.enforce_policy(
                        api_config_id=user_policy_id,
                        user_id=from_user,
                        request_context={
                            "path": "/websocket/prompt",
                            "method": "WEBSOCKET",
                            "prompt_id": prompt_query.prompt_id,
                        },
                    )

                    if not policy_result.allowed:
                        # Build error message from policy violations
                        error_messages = []
                        for rule in policy_result.violated_rules:
                            if rule.message:
                                error_messages.append(rule.message)
                            else:
                                error_messages.append(
                                    f"Policy limit exceeded: {rule.metric_key}"
                                )

                        error_msg = (
                            "Policy violation: " + "; ".join(error_messages)
                            if error_messages
                            else "Request denied due to policy limits"
                        )

                        # Log the policy violation
                        logger.warning(
                            f"Policy violation for user {from_user}: {error_msg}"
                        )

                        # Send error response
                        await self._send_error_response(
                            error_msg,
                            from_user,
                            websocket_service,
                            prompt_id=prompt_query.prompt_id,
                        )
                        return  # Don't process further

                except Exception as e:
                    logger.error(f"Error enforcing policy: {e}", exc_info=True)
                    # In case of policy enforcement error, continue with processing
                    # This ensures the service remains available
                    # even if policy checks fail
            else:
                # No policy found for user, deny access
                logger.warning(f"No API configuration found for user {from_user}")
                await self._send_error_response(
                    "Access denied: No API configuration found for your account. "
                    "Please contact an administrator.",
                    from_user,
                    websocket_service,
                    prompt_id=prompt_query.prompt_id,
                )
                return

            # Add the prompt to conversation history
            update_params = self.ConversationHistoryUpdate(
                conversation_key=conversation_key,
                role="user",
                content=prompt_query.prompt,
                prompt_id=prompt_query.prompt_id,
                documents=prompt_query.documents,
            )
            await self._update_conversation_history(update_params)

            # Combine user-provided documents with retrieved documents
            all_documents = prompt_query.documents or []
            all_documents.extend(related_documents)

            # Process the prompt with the agent
            response = await self._process_prompt_with_agent(
                prompt_query.prompt,
                all_documents if all_documents else None,
                conversation_key,
            )

            # Track API usage
            await self._track_api_usage(
                user_policy_id, from_user, prompt_query.prompt, response
            )

            # Send response back to the user with prompt_id
            await self._send_response(
                response,
                from_user,
                websocket_service,
                prompt_id=prompt_query.prompt_id,
            )

            # Update conversation history with response
            assistant_params = self.ConversationHistoryUpdate(
                conversation_key=conversation_key,
                role="assistant",
                content=response,
                prompt_id=prompt_query.prompt_id,
            )
            await self._update_conversation_history(assistant_params)

        except Exception as e:
            logger.error(f"Error handling prompt query: {e}", exc_info=True)
            # Send error response to user with prompt_id
            await self._send_error_response(
                str(e),
                original_message.from_user,
                websocket_service,
                prompt_id=(
                    prompt_query.prompt_id if "prompt_query" in locals() else None
                ),
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

            # Prepare system prompt to restrict answers to provided documents
            system_prompt = (
                "You are a helpful assistant. IMPORTANT: You must ONLY answer "
                "questions "
                "based on the documents provided to you. Do not use any external "
                "knowledge "
                "or information not present in the provided documents. If the "
                "provided documents "
                "do not contain enough information to properly answer the question, "
                "you must "
                "respond with: 'I don't have enough context to provide a good "
                "answer for this "
                "question.' Be precise and only cite information that is "
                "explicitly present "
                "in the provided documents."
            )

            # Include documents in the prompt if provided
            enhanced_prompt = prompt
            if documents:
                document_context = "\n\nRelevant documents:\n"
                for i, doc in enumerate(documents, 1):
                    document_context += f"\n{i}. {doc}"
                enhanced_prompt = f"{prompt}{document_context}"
            else:
                # No documents provided, instruct agent accordingly
                enhanced_prompt = (
                    f"{prompt}\n\nNote: No documents were provided for this query. "
                    "Please respond with: 'I don't have enough context to provide "
                    "a good answer for this question.'"
                )

            # Add system message to conversation history
            enhanced_conversation_history = [
                {"role": "system", "content": system_prompt},
                *conversation_history,
            ]

            # Process with agent
            return await self.agent.process_message(
                conversation_id=conversation_key,
                user_message=enhanced_prompt,
                conversation_history=enhanced_conversation_history,
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
                to=recipient,
                content=error_json,
                # Don't set timestamp - let the client handle it for proper signing
            )

            if websocket_service.client:
                await websocket_service.client.send_message(msg)
                logger.info(f"Sent error response to {recipient}")

        except Exception as e:
            logger.error(f"Error sending error response: {e}")

    async def close(self) -> None:
        """Clean up resources when shutting down."""
        # Clear all active conversations
        self.active_conversations.clear()
        logger.info("PromptService shut down")
