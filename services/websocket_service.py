import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from client.client import Client, Message, new_client
from config.settings import Settings
from services.prompt_service import PromptService
from services.websocket_types import (
    BroadcastMessage,
    DirectMessage,
    ErrorMessage,
    ForwardedMessage,
    MessageStatus,
    PromptQueryMessage,
    PromptResponseMessage,
    SystemMessage,
    create_message,
    parse_decrypted_message_content,
)
from syftbox.jobs import set_websocket_service

logger = logging.getLogger(__name__)


class WebSocketService:
    """Service for managing WebSocket connections to distributedknowledge.org."""

    def __init__(self, settings: Settings, agent: Any = None) -> None:
        self.settings = settings
        self.client = None
        self.private_key = None
        self.public_key = None
        self.agent = agent
        self.prompt_service = None

        # Response aggregation structures - no timeouts, collect indefinitely
        self.response_aggregator: dict[str, list[dict]] = defaultdict(list)
        self.aggregator_lock = asyncio.Lock()
        # Track metadata about queries
        self.query_metadata: dict[str, dict] = {}

    async def initialize(self) -> None:
        """Initialize the WebSocket service."""
        logger.info(
            f"WebSocket service initialization started for user: "
            f"{self.settings.syftbox_username}"
        )
        try:
            # Load or generate keys
            logger.info("Loading or generating keys...")
            self.private_key, self.public_key = await self._load_or_generate_keys()

            # Create client
            logger.info("Creating WebSocket client...")
            self.client = await self._create_client()

            # Register and login
            logger.info("Registering and logging in...")
            await self._register_and_login()

            # Connect
            logger.info("Connecting to WebSocket server...")
            await self.client.connect()
            logger.info(
                f"Connected to {self.settings.websocket_server_url} as "
                f"{self.settings.syftbox_username}",
            )

            # Initialize PromptService if agent is available
            if self.agent:
                self.prompt_service = PromptService(self.settings, self.agent)
                logger.info("PromptService initialized")

            # Set the service for message processing job
            set_websocket_service(self)
            logger.info("WebSocket service set for async job processing")

            # Keep the connection alive
            await self._keep_alive()

        except Exception as e:
            logger.error(f"Failed to initialize WebSocket service: {e}")
            raise

    async def _keep_alive(self) -> None:
        """Keep the WebSocket connection alive."""
        while True:
            try:
                if self.client and hasattr(self.client, "ws") and self.client.ws:
                    # Just check connection state silently
                    pass
                else:
                    logger.error("WebSocket client or connection is None")
                    break
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Keep-alive error: {e}")
                break

    def get_client(self) -> Client:
        """Get the WebSocket client instance."""
        return self.client

    async def _load_or_generate_keys(
        self,
    ) -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Load existing keys or generate new ones."""
        key_dir = self.settings.key_directory
        key_dir.mkdir(parents=True, exist_ok=True)

        private_key_path = key_dir / self.settings.private_key_filename
        public_key_path = key_dir / self.settings.public_key_filename

        if private_key_path.exists() and public_key_path.exists():
            # Load existing keys
            with private_key_path.open("rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend(),
                )
            with public_key_path.open("rb") as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend(),
                )
            logger.info("Loaded existing WebSocket keys")
        else:
            # Generate new keys
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            # Save keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            with private_key_path.open("wb") as f:
                f.write(private_pem)
            with public_key_path.open("wb") as f:
                f.write(public_pem)

            logger.info("Generated new WebSocket keys")

        return private_key, public_key

    async def _create_client(self) -> None:
        """Create WebSocket client instance."""
        # Determine user ID
        user_id = self.settings.syftbox_username
        if self.settings.syftbox_email:
            user_id = self.settings.syftbox_email

        return new_client(
            self.settings.websocket_server_url,
            user_id,
            self.private_key,
            self.public_key,
        )

    async def _register_and_login(self) -> None:
        """Register and login to the WebSocket server."""
        try:
            await self.client.register(self.settings.syftbox_username)
            logger.info("Successfully registered with WebSocket server")
        except Exception:
            # Registration may fail if user already exists
            logger.debug("Registration failed (user may already exist)")

        await self.client.login()
        logger.info("Successfully logged in to WebSocket server")

    async def close(self) -> None:
        """Close the WebSocket connection."""
        # Close PromptService if available
        if self.prompt_service:
            try:
                await self.prompt_service.close()
                logger.info("PromptService closed")
            except Exception as e:
                logger.error(f"Error closing PromptService: {e}")

        # Close WebSocket client
        if self.client:
            try:
                await self.client.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket connection: {e}")

    async def message_handler(self, message: Message) -> None:
        """Handle an incoming WebSocket message and route it to appropriate handler."""
        try:
            # Convert the client Message to our typed message
            message_dict = message.to_dict()
            typed_message = create_message(message_dict)

            # Route based on message type
            if isinstance(typed_message, DirectMessage):
                await self._handle_direct_message(typed_message, message)
            elif isinstance(typed_message, BroadcastMessage):
                await self._handle_broadcast_message(typed_message, message)
            elif isinstance(typed_message, ForwardedMessage):
                await self._handle_forwarded_message(typed_message, message)
            elif isinstance(typed_message, SystemMessage):
                await self._handle_system_message(typed_message, message)
            else:
                logger.warning(f"Unknown message type: {type(typed_message).__name__}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def _handle_direct_message(
        self,
        typed_msg: DirectMessage,
        original_msg: Message,
    ) -> None:
        """Handle direct messages between users."""
        logger.info(
            f"Handling direct message from {typed_msg.from_user} to {typed_msg.to}",
        )
        logger.debug(f"Direct message content preview: {typed_msg.content[:100]}...")
        logger.debug(f"Message status: {original_msg.status}")
        logger.debug(f"Message timestamp: {typed_msg.timestamp}")

        # Log encryption status and handle failed decryption
        if original_msg.status == MessageStatus.DECRYPTION_FAILED:
            logger.error(f"Failed to decrypt message from {typed_msg.from_user}")
            return
        if original_msg.status == MessageStatus.VERIFIED:
            logger.info(f"Message signature verified for {typed_msg.from_user}")
            await self._handle_verified_direct_message(typed_msg, original_msg)

        # TODO: Implement additional direct message processing
        # - Store in conversation history
        # - Update UI with new message

    async def _handle_verified_direct_message(
        self,
        typed_msg: DirectMessage,
        original_msg: Message,  # noqa: ARG002
    ) -> None:
        """Handle verified direct messages with decrypted content."""
        try:
            # Parse the decrypted content to check for nested message types
            decrypted_content = parse_decrypted_message_content(typed_msg.content)

            # Dispatch to the appropriate content handler
            await self._dispatch_content_handler(decrypted_content, typed_msg)

        except Exception as e:
            logger.error(f"Error parsing decrypted content: {e}")
            logger.debug(f"Raw content: {typed_msg.content}")

    async def _dispatch_content_handler(
        self,
        content: Any,
        typed_msg: DirectMessage,
    ) -> None:
        """Dispatch message to the appropriate content handler based on type."""
        if isinstance(content, PromptQueryMessage):
            await self._handle_prompt_query(content, typed_msg)
        elif isinstance(content, PromptResponseMessage):
            await self._handle_prompt_response(content, typed_msg)
        elif isinstance(content, ErrorMessage):
            await self._handle_error_message(content, typed_msg)
        elif isinstance(content, dict):
            await self._handle_dict_content(content, typed_msg)
        else:
            await self._handle_plain_text(content, typed_msg)

    async def _handle_prompt_query(
        self,
        content: PromptQueryMessage,
        typed_msg: DirectMessage,
    ) -> None:
        """Handle prompt query messages."""
        logger.info(f"Received PromptQueryMessage from {typed_msg.from_user}")
        logger.info(f"Prompt ID: {content.prompt_id}")
        logger.debug(f"Prompt: {content.prompt}")
        if content.documents:
            logger.debug(f"Documents: {content.documents}")

        # Route to PromptService if available
        if self.prompt_service:
            await self.prompt_service.handle_prompt_query_message(
                content,
                typed_msg,
                self,
            )
        else:
            logger.warning("PromptService not available to handle PromptQueryMessage")

    async def _handle_prompt_response(
        self,
        content: PromptResponseMessage,
        typed_msg: DirectMessage,
    ) -> None:
        """Handle prompt response messages."""
        logger.info(f"Received PromptResponseMessage from {typed_msg.from_user}")
        logger.info(f"Prompt ID: {content.prompt_id}")
        logger.debug(f"Response: {content.response[:100]}...")
        logger.debug(f"Response timestamp: {content.timestamp}")

        # Aggregate the response
        await self._aggregate_response(
            prompt_id=content.prompt_id,
            response_message=content,
            from_peer=typed_msg.from_user,
        )

    async def _handle_error_message(
        self,
        content: ErrorMessage,
        typed_msg: DirectMessage,
    ) -> None:
        """Handle error messages."""
        logger.warning(f"Received ErrorMessage from {typed_msg.from_user}")
        if content.prompt_id:
            logger.warning(f"Prompt ID: {content.prompt_id}")
            # Aggregate error response if it has a prompt_id
            await self._aggregate_response(
                prompt_id=content.prompt_id,
                response_message=content,
                from_peer=typed_msg.from_user,
            )
        logger.warning(f"Error: {content.error}")
        logger.debug(f"Error timestamp: {content.timestamp}")

    async def _handle_dict_content(
        self,
        content: dict,
        typed_msg: DirectMessage,
    ) -> None:
        """Handle dictionary content messages."""
        logger.info(f"Received dict content from {typed_msg.from_user}")
        if "content_type" in content:
            logger.debug(f"Content type: {content.get('content_type')}")
        # TODO: Handle other content types

    async def _handle_plain_text(
        self,
        content: Any,  # noqa: ARG002
        typed_msg: DirectMessage,
    ) -> None:
        """Handle plain text or other content messages."""
        logger.info(f"Received plain text message from {typed_msg.from_user}")
        # TODO: Handle plain text messages

    async def _handle_broadcast_message(
        self,
        typed_msg: BroadcastMessage,
        original_msg: Message,  # noqa: ARG002
    ) -> None:
        """Handle broadcast messages sent to all users."""
        logger.info(f"Handling broadcast message from {typed_msg.from_user}")
        logger.debug(f"Broadcast content: {typed_msg.content}")
        logger.debug(f"Message timestamp: {typed_msg.timestamp}")

        # Log verification status
        if typed_msg.signature:
            logger.debug(
                f"Broadcast message has signature: {typed_msg.signature[:20]}...",
            )

        # TODO: Implement broadcast message processing
        # - Display in UI
        # - Store in broadcast history
        # - Notify relevant handlers

    async def _handle_forwarded_message(
        self,
        typed_msg: ForwardedMessage,
        original_msg: Message,  # noqa: ARG002
    ) -> None:
        """Handle forwarded messages."""
        logger.info(
            f"Handling forwarded message from {typed_msg.from_user} to {typed_msg.to}",
        )
        logger.debug(f"Original sender: {typed_msg.original_sender}")
        logger.debug(f"Forwarded content preview: {typed_msg.content[:100]}...")
        logger.debug(f"Message timestamp: {typed_msg.timestamp}")

        # Forwarded messages are not encrypted/signed
        logger.debug("Forwarded message (no encryption/signature verification)")

        # TODO: Implement forwarded message processing
        # - Store with forwarding metadata
        # - Display forwarding chain in UI
        # - Notify recipient

    async def _handle_system_message(
        self,
        typed_msg: SystemMessage,
        original_msg: Message,  # noqa: ARG002
    ) -> None:
        """Handle system messages from the server."""
        logger.info(f"Handling system message: {typed_msg.content}")
        logger.debug(f"System message status: {typed_msg.status}")
        logger.debug(f"Message timestamp: {typed_msg.timestamp}")

        # System messages might contain important events
        if "connected" in typed_msg.content.lower():
            logger.info(f"User connection event: {typed_msg.content}")
        elif "disconnected" in typed_msg.content.lower():
            logger.info(f"User disconnection event: {typed_msg.content}")

        # TODO: Implement system message processing
        # - Update user status
        # - Display system notifications
        # - Trigger relevant actions

    async def _aggregate_response(
        self,
        prompt_id: str,
        response_message: Union[PromptResponseMessage, ErrorMessage],
        from_peer: str,
    ) -> None:
        """Aggregate responses for a given prompt ID."""
        async with self.aggregator_lock:
            response_dict = {
                "from_peer": from_peer,
                "timestamp": response_message.timestamp,
                "received_at": datetime.now(timezone.utc).isoformat(),
            }

            if isinstance(response_message, PromptResponseMessage):
                response_dict.update(
                    {"type": "response", "response": response_message.response},
                )
            elif isinstance(response_message, ErrorMessage):
                response_dict.update({"type": "error", "error": response_message.error})

            self.response_aggregator[prompt_id].append(response_dict)

            # Update metadata if this is the first response
            if prompt_id not in self.query_metadata:
                self.query_metadata[prompt_id] = {
                    "first_response_at": datetime.now(timezone.utc).isoformat(),
                    "response_count": 0,
                }

            self.query_metadata[prompt_id]["response_count"] += 1
            self.query_metadata[prompt_id]["last_response_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            logger.info(
                f"Aggregated response for prompt {prompt_id} from {from_peer}. "
                f"Total responses: {self.query_metadata[prompt_id]['response_count']}",
            )

    async def get_aggregated_responses(self, prompt_id: str) -> dict[str, Any]:
        """Get all aggregated responses for a given prompt ID."""
        async with self.aggregator_lock:
            return {
                "prompt_id": prompt_id,
                "responses": self.response_aggregator.get(prompt_id, []),
                "metadata": self.query_metadata.get(prompt_id, {}),
            }

    async def clear_aggregated_responses(self, prompt_id: str) -> bool:
        """Clear aggregated responses for a given prompt ID."""
        async with self.aggregator_lock:
            if prompt_id in self.response_aggregator:
                del self.response_aggregator[prompt_id]
                if prompt_id in self.query_metadata:
                    del self.query_metadata[prompt_id]
                logger.info(f"Cleared aggregated responses for prompt {prompt_id}")
                return True
            return False

    async def get_all_prompt_ids(self) -> list[str]:
        """Get all prompt IDs that have aggregated responses."""
        async with self.aggregator_lock:
            return list(self.response_aggregator.keys())

    async def store_query_metadata(self, prompt_id: str, metadata: dict) -> None:
        """Store metadata about a query for later retrieval."""
        async with self.aggregator_lock:
            self.query_metadata[prompt_id] = metadata
            logger.info(f"Stored metadata for prompt {prompt_id}: {metadata}")
