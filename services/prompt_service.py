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

    @dataclass
    class PolicyCheckResult:
        """Result of policy enforcement check."""

        allowed: bool
        requires_triage: bool
        triage_rule_id: Optional[str]
        triage_message: Optional[str]
        error_message: Optional[str]

    @dataclass
    class ProcessContext:
        """Context for processing a prompt query."""

        prompt_query: PromptQueryMessage
        from_user: str
        conversation_key: str
        related_documents: list[str]
        user_policy_id: str
        policy_check: "PromptService.PolicyCheckResult"
        websocket_service: Any

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
            from_user = original_message.from_user
            self._log_prompt_processing(from_user, prompt_query)

            # Initialize conversation
            conversation_key = self._init_conversation(from_user)

            # Get documents and check policy
            related_documents, user_policy_id = await self._get_related_documents(
                from_user, prompt_query.prompt
            )

            if not user_policy_id:
                await self._handle_no_policy_error(
                    from_user, websocket_service, prompt_query.prompt_id
                )
                return

            # Check policy enforcement
            policy_check = await self._check_policy_enforcement(
                user_policy_id, from_user, prompt_query.prompt_id
            )

            if not policy_check.allowed and not policy_check.requires_triage:
                await self._send_error_response(
                    policy_check.error_message,
                    from_user,
                    websocket_service,
                    prompt_id=prompt_query.prompt_id,
                )
                return

            # Process the request
            context = self.ProcessContext(
                prompt_query=prompt_query,
                from_user=from_user,
                conversation_key=conversation_key,
                related_documents=related_documents,
                user_policy_id=user_policy_id,
                policy_check=policy_check,
                websocket_service=websocket_service,
            )
            await self._process_and_respond(context)

        except Exception as e:
            logger.error(f"Error handling prompt query: {e}", exc_info=True)
            await self._send_error_response(
                str(e),
                original_message.from_user,
                websocket_service,
                prompt_id=getattr(prompt_query, "prompt_id", None),
            )

    def _log_prompt_processing(
        self, from_user: str, prompt_query: PromptQueryMessage
    ) -> None:
        """Log prompt processing information."""
        logger.info(f"Processing prompt query from {from_user}: {prompt_query.prompt}")
        logger.info(f"Prompt ID: {prompt_query.prompt_id}")

    def _init_conversation(self, from_user: str) -> str:
        """Initialize or get conversation context."""
        conversation_key = f"{from_user}_conversation"
        if conversation_key not in self.active_conversations:
            self.active_conversations[conversation_key] = {
                "user_id": from_user,
                "started": datetime.now(timezone.utc),
                "messages": [],
            }
        return conversation_key

    async def _handle_no_policy_error(
        self, from_user: str, websocket_service: Any, prompt_id: str
    ) -> None:
        """Handle case when no policy is found for user."""
        logger.warning(f"No API configuration found for user {from_user}")
        await self._send_error_response(
            "Access denied: No API configuration found for your account. "
            "Please contact an administrator.",
            from_user,
            websocket_service,
            prompt_id=prompt_id,
        )

    async def _check_policy_enforcement(
        self, user_policy_id: str, from_user: str, prompt_id: str
    ) -> PolicyCheckResult:
        """Check policy enforcement for the request."""
        from policies.enforcer import PolicyEnforcer

        policy_enforcer = PolicyEnforcer()

        try:
            policy_result = await policy_enforcer.enforce_policy(
                api_config_id=user_policy_id,
                user_id=from_user,
                request_context={
                    "path": "/websocket/prompt",
                    "method": "WEBSOCKET",
                    "prompt_id": prompt_id,
                },
            )

            if not policy_result.allowed:
                if policy_result.metadata.get("requires_triage"):
                    logger.info(f"Request from {from_user} requires triage review")
                    return self.PolicyCheckResult(
                        allowed=True,
                        requires_triage=True,
                        triage_rule_id=policy_result.metadata.get("triage_rule_id"),
                        triage_message=policy_result.metadata.get("triage_message"),
                        error_message=None,
                    )

                error_msg = self._build_policy_error_message(policy_result)
                logger.warning(f"Policy violation for user {from_user}: {error_msg}")
                return self.PolicyCheckResult(
                    allowed=False,
                    requires_triage=False,
                    triage_rule_id=None,
                    triage_message=None,
                    error_message=error_msg,
                )

            return self.PolicyCheckResult(
                allowed=True,
                requires_triage=False,
                triage_rule_id=None,
                triage_message=None,
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Error enforcing policy: {e}", exc_info=True)
            # Continue with processing on policy error
            return self.PolicyCheckResult(
                allowed=True,
                requires_triage=False,
                triage_rule_id=None,
                triage_message=None,
                error_message=None,
            )

    def _build_policy_error_message(self, policy_result: Any) -> str:
        """Build error message from policy violations."""
        error_messages = []
        for rule in policy_result.violated_rules:
            if rule.message:
                error_messages.append(rule.message)
            else:
                error_messages.append(f"Policy limit exceeded: {rule.metric_key}")

        return (
            "Policy violation: " + "; ".join(error_messages)
            if error_messages
            else "Request denied due to policy limits"
        )

    async def _process_and_respond(self, context: ProcessContext) -> None:
        """Process the prompt and send response."""
        # Update conversation history
        await self._update_conversation_history(
            self.ConversationHistoryUpdate(
                conversation_key=context.conversation_key,
                role="user",
                content=context.prompt_query.prompt,
                prompt_id=context.prompt_query.prompt_id,
                documents=context.prompt_query.documents,
            )
        )

        # Combine documents
        all_documents = (
            context.prompt_query.documents or []
        ) + context.related_documents

        # Process with agent
        response = await self._process_prompt_with_agent(
            context.prompt_query.prompt,
            all_documents if all_documents else None,
            context.conversation_key,
        )

        # Handle triage if needed
        if context.policy_check.requires_triage:
            await self._handle_triage_request(
                context,
                all_documents,
                response,
            )
            return

        # Normal response flow
        await self._track_api_usage(
            context.user_policy_id,
            context.from_user,
            context.prompt_query.prompt,
            response,
        )

        await self._send_response(
            response,
            context.from_user,
            context.websocket_service,
            prompt_id=context.prompt_query.prompt_id,
        )

        # Update conversation with response
        await self._update_conversation_history(
            self.ConversationHistoryUpdate(
                conversation_key=context.conversation_key,
                role="assistant",
                content=response,
                prompt_id=context.prompt_query.prompt_id,
            )
        )

    async def _handle_triage_request(
        self,
        context: ProcessContext,
        all_documents: list[str],
        response: str,
    ) -> None:
        """Handle triage request for policy-flagged prompts."""
        from policies.triage_models import TriageRequest
        from policies.triage_repository import TriageRepository

        triage_repo = TriageRepository()
        triage_request = TriageRequest(
            user_id=context.from_user,
            prompt_id=context.prompt_query.prompt_id,
            api_config_id=context.user_policy_id,
            policy_rule_id=context.policy_check.triage_rule_id,
            prompt_query=context.prompt_query.prompt,
            documents_retrieved=all_documents,
            generated_response=response,
            conversation_key=context.conversation_key,
        )

        triage_repo.create(triage_request)

        # Send pending message
        await self._send_response(
            "Your request has been submitted for review. "
            "You will be notified once it's processed.",
            context.from_user,
            context.websocket_service,
            prompt_id=context.prompt_query.prompt_id,
        )

        # Track usage even for triage
        await self._track_api_usage(
            context.user_policy_id,
            context.from_user,
            context.prompt_query.prompt,
            response,
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
