"""Python client implementation equivalent to client.go"""

import asyncio
import base64
import json
import logging
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Optional

import aiohttp
import websockets
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from nacl.public import (
    Box,
)
from nacl.public import (
    PrivateKey as X25519PrivateKey,
)
from nacl.public import (
    PublicKey as X25519PublicKey,
)
from nacl.utils import random

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Message structure for communication"""

    from_user: str
    to: str
    content: str
    timestamp: Optional[datetime] = None
    status: Optional[str] = None
    signature: Optional[str] = None
    is_forward_message: bool = False
    id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for JSON serialization"""
        data = {
            "from": self.from_user,
            "to": self.to,
            "content": self.content,
            "is_forward_message": self.is_forward_message,
        }
        if self.id is not None:
            data["id"] = self.id
        if self.timestamp:
            # Ensure timestamp is in RFC3339 format with timezone
            if self.timestamp.tzinfo is None:
                # If no timezone info, assume UTC
                timestamp_utc = self.timestamp.replace(tzinfo=timezone.utc)
                data["timestamp"] = timestamp_utc.isoformat()
            else:
                data["timestamp"] = self.timestamp.isoformat()
        if self.status:
            data["status"] = self.status
        if self.signature:
            data["signature"] = self.signature
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create message from dictionary"""
        timestamp = None
        if "timestamp" in data:
            try:
                timestamp = datetime.fromisoformat(
                    data["timestamp"].replace("Z", "+00:00"),
                )
            except (ValueError, KeyError, TypeError):
                timestamp = datetime.now(timezone.utc)

        return cls(
            from_user=data.get("from", ""),
            to=data.get("to", ""),
            content=data.get("content", ""),
            timestamp=timestamp,
            status=data.get("status"),
            signature=data.get("signature"),
            is_forward_message=data.get("is_forward_message", False),
            id=data.get("id"),
        )


@dataclass
class EncryptedMessage:
    """Structure for encrypted message envelope"""

    ephemeral_public_key: str
    key_nonce: str
    encrypted_key: str
    data_nonce: str
    encrypted_content: str

    def to_dict(self) -> dict[str, str]:
        return {
            "ephemeral_public_key": self.ephemeral_public_key,
            "key_nonce": self.key_nonce,
            "encrypted_key": self.encrypted_key,
            "data_nonce": self.data_nonce,
            "encrypted_content": self.encrypted_content,
        }


@dataclass
class UserStatusResponse:
    """Response structure for active users endpoint"""

    online: list[str] = field(default_factory=list)
    offline: list[str] = field(default_factory=list)


class Client:
    """WebSocket client for encrypted messaging"""

    def __init__(
        self,
        server_url: str,
        user_id: str,
        private_key: ed25519.Ed25519PrivateKey,
        public_key: ed25519.Ed25519PublicKey,
    ) -> None:
        self.server_url = server_url
        self.user_id = user_id
        self.private_key = private_key
        self.public_key = public_key

        # WebSocket connection
        self.ws = None
        self.conn_lock = RLock()

        # JWT token for authentication
        self.jwt_token: Optional[str] = None

        # Message channels
        self.recv_queue = asyncio.Queue(maxsize=100)
        self.send_queue = asyncio.Queue(maxsize=100)

        # Control
        self.done = asyncio.Event()
        self.reconnect_interval = 5  # seconds

        # Public key cache
        self.pub_key_cache: dict[str, ed25519.Ed25519PublicKey] = {}
        self.pub_key_cache_lock = RLock()

        # SSL verification
        self.insecure = False

        # Tasks
        self.read_task = None
        self.write_task = None

        # Add own public key to cache
        self.pub_key_cache[user_id] = public_key

    def token(self) -> Optional[str]:
        """Get current JWT token"""
        return self.jwt_token

    def set_reconnect_interval(self, interval: float) -> None:
        """Set reconnection interval in seconds"""
        self.reconnect_interval = interval

    def set_insecure(self, insecure: bool) -> None:
        """Set SSL verification mode"""
        self.insecure = insecure

    def _get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Get SSL context based on insecure flag"""
        if self.insecure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        return None

    async def get_user_descriptions(self, user_id: str) -> list[str]:
        """Get descriptions for a specific user"""
        endpoint = f"{self.server_url}/user/descriptions/{user_id}"

        async with aiohttp.ClientSession() as session:
            ssl_context = self._get_ssl_context()
            async with session.get(endpoint, ssl=ssl_context) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(
                        f"Failed to get user descriptions: {text} "
                        f"(status {resp.status})",
                    )

                return await resp.json()

    async def set_user_descriptions(self, descriptions: list[str]) -> None:
        """Set descriptions for current user"""
        if not descriptions:
            raise ValueError("descriptions list cannot be empty")

        if not self.jwt_token:
            raise Exception("JWT token is not set; please login first")

        endpoint = f"{self.server_url}/user/descriptions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt_token}",
        }

        async with aiohttp.ClientSession() as session:
            ssl_context = self._get_ssl_context()
            async with session.post(
                endpoint,
                json=descriptions,
                headers=headers,
                ssl=ssl_context,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(
                        f"Failed to set descriptions: {text} (status {resp.status})",
                    )

    async def get_active_users(self) -> UserStatusResponse:
        """Get list of active and inactive users"""
        endpoint = f"{self.server_url}/active-users"
        headers = {}

        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        async with aiohttp.ClientSession() as session:
            ssl_context = self._get_ssl_context()
            async with session.get(endpoint, headers=headers, ssl=ssl_context) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Unexpected status code {resp.status}: {text}")

                data = await resp.json()
                return UserStatusResponse(
                    online=data.get("online", []),
                    offline=data.get("offline", []),
                )

    def _sign_message(self, msg: Message) -> None:
        """Sign a message with private key"""
        if not msg.timestamp:
            msg.timestamp = datetime.now(timezone.utc)

        # Create canonical representation for signing
        timestamp_nano = int(msg.timestamp.timestamp() * 1e9)
        canonical_msg = f"{msg.from_user}|{msg.to}|{timestamp_nano}|{msg.content}"

        # Sign the message
        signature = self.private_key.sign(canonical_msg.encode())
        msg.signature = base64.b64encode(signature).decode("utf-8")

    def _verify_message_signature(
        self,
        msg: Message,
        sender_pub_key: ed25519.Ed25519PublicKey,
    ) -> bool:
        """Verify message signature"""
        if not msg.signature:
            return False

        try:
            # Use provided timestamp
            timestamp_nano = int(msg.timestamp.timestamp() * 1e9)

            # Create same canonical representation
            canonical_msg = f"{msg.from_user}|{msg.to}|{timestamp_nano}|{msg.content}"

            # Decode signature
            signature = base64.b64decode(msg.signature)

            # Verify signature
            sender_pub_key.verify(signature, canonical_msg.encode())
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            logger.error(f"Failed to verify signature: {e}")
            return False

    async def get_user_public_key(self, user_id: str) -> ed25519.Ed25519PublicKey:
        """Get user's public key, with caching"""
        # Check cache first
        with self.pub_key_cache_lock:
            if user_id in self.pub_key_cache:
                return self.pub_key_cache[user_id]

        # Fetch from server
        endpoint = f"{self.server_url}/auth/users/{user_id}"
        headers = {}

        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        async with aiohttp.ClientSession() as session:
            ssl_context = self._get_ssl_context()
            async with session.get(endpoint, headers=headers, ssl=ssl_context) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Failed to get user public key: {text}")

                data = await resp.json()
                pub_key_bytes = base64.b64decode(data["public_key"])
                pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_key_bytes)

                # Cache the key
                with self.pub_key_cache_lock:
                    self.pub_key_cache[user_id] = pub_key

                return pub_key

    async def register(self, username: str) -> None:
        """Register new user"""
        endpoint = f"{self.server_url}/auth/register"
        payload = {
            "user_id": self.user_id,
            "username": username,
            "public_key": base64.b64encode(
                self.public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                ),
            ).decode("utf-8"),
        }

        async with aiohttp.ClientSession() as session:
            ssl_context = self._get_ssl_context()
            async with session.post(endpoint, json=payload, ssl=ssl_context) as resp:
                if resp.status != 201:
                    text = await resp.text()
                    raise Exception(f"Registration failed: {text}")

    async def login(self) -> None:
        """Perform challenge-response authentication"""
        login_url = f"{self.server_url}/auth/login"

        async with aiohttp.ClientSession() as session:
            ssl_context = self._get_ssl_context()

            # Step 1: Get challenge
            async with session.post(
                login_url,
                json={"user_id": self.user_id},
                ssl=ssl_context,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Login challenge failed: {text}")

                data = await resp.json()
                challenge = data.get("challenge")
                if not challenge:
                    raise Exception("Challenge not found in response")

            # Step 2: Sign challenge and verify
            signature = self.private_key.sign(challenge.encode())
            sig_b64 = base64.b64encode(signature).decode("utf-8")

            verify_url = f"{login_url}?verify=true"
            verify_payload = {"user_id": self.user_id, "signature": sig_b64}

            async with session.post(
                verify_url,
                json=verify_payload,
                ssl=ssl_context,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Login verification failed: {text}")

                data = await resp.json()
                token = data.get("token")
                if not token:
                    raise Exception("Token not found in response")

                self.jwt_token = token

    async def connect(self) -> None:
        """Connect to WebSocket server"""
        # Parse URL and convert to WebSocket scheme
        ws_url = f"{self.server_url}/ws?token={self.jwt_token}"
        ws_url = ws_url.replace("https://", "wss://").replace("http://", "ws://")

        ssl_context = self._get_ssl_context()

        # For wss:// connections, use ssl=True if no custom context
        if ws_url.startswith("wss://") and ssl_context is None:
            ssl_param = True
        else:
            ssl_param = ssl_context

        # Connect to WebSocket
        # The server sends pings from its side
        # The websockets library should automatically respond with pongs
        self.ws = await websockets.connect(
            ws_url,
            ssl=ssl_param,
            ping_interval=20,  # Send client pings every 20 seconds as backup
            ping_timeout=10,  # Wait 10 seconds for pong
            max_size=10485760,  # 10MB max message size
        )

        logger.info(f"WebSocket connected to {ws_url}")

        # Start read and write pumps
        self.read_task = asyncio.create_task(self._read_pump())
        self.write_task = asyncio.create_task(self._write_pump())

    async def _read_pump(self) -> None:
        """Read messages from WebSocket"""
        try:
            while not self.done.is_set():
                if self.ws is None:
                    return

                try:
                    # Set shorter timeout to ensure we check connection state regularly
                    msg_data = await asyncio.wait_for(self.ws.recv(), timeout=5)

                    # Try to parse as JSON
                    try:
                        msg_dict = json.loads(msg_data)
                        msg = Message.from_dict(msg_dict)

                        # Skip decryption/verification for system and forward messages
                        if msg.from_user == "system" or msg.is_forward_message:
                            await self.recv_queue.put(msg)
                            continue

                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON: {msg_data}")
                        continue

                    # Verify message signature if present
                    if msg.signature:
                        try:
                            sender_pub_key = await self.get_user_public_key(
                                msg.from_user,
                            )
                            if not self._verify_message_signature(msg, sender_pub_key):
                                logger.warning(
                                    f"Invalid signature for message from "
                                    f"{msg.from_user}",
                                )
                                msg.status = "invalid_signature"
                            elif msg.status in ("", "pending", None):
                                msg.status = "verified"
                        except Exception as e:
                            logger.error(
                                f"Failed to get public key for user "
                                f"{msg.from_user}: {e}",
                            )
                            msg.status = "unverified"
                    elif not msg.status:
                        msg.status = "unsigned"

                    # Decrypt direct messages
                    if msg.to == self.user_id:
                        try:
                            plaintext = await self._decrypt_direct_message(msg.content)
                            msg.content = plaintext
                        except Exception as e:
                            logger.error(
                                f"Failed to decrypt message from {msg.from_user}: {e}",
                            )
                            msg.status = "decryption_failed"

                    await self.recv_queue.put(msg)

                except asyncio.TimeoutError:
                    # Check if connection is still alive
                    if self.ws and hasattr(self.ws, "state") and self.ws.state != 1:
                        logger.error(
                            f"WebSocket connection not open, "
                            f"state: {self.ws.state}",
                        )
                        await self._handle_reconnect()
                        return
                    continue
                except websockets.exceptions.ConnectionClosed as e:
                    logger.error(f"WebSocket connection closed: {e}")
                    await self._handle_reconnect()
                    return
                except Exception as e:
                    logger.error(f"Read pump error: {e}")
                    continue
        except Exception as e:
            logger.error(f"Fatal read pump error: {e}")
        finally:
            logger.debug("Read pump exiting")

    async def _write_pump(self) -> None:
        """Write messages to WebSocket"""
        try:
            while not self.done.is_set():
                if self.ws is None:
                    return

                try:
                    # Wait for message with timeout
                    msg = await asyncio.wait_for(self.send_queue.get(), timeout=1.0)

                    # Skip encryption and signing for forward messages
                    if not msg.is_forward_message:
                        # Encrypt direct messages
                        if msg.to != "broadcast":
                            try:
                                recipient_pub = await self.get_user_public_key(msg.to)
                                encrypted_content = await self._encrypt_direct_message(
                                    msg.content,
                                    recipient_pub,
                                )
                                msg.content = encrypted_content
                            except Exception as e:
                                logger.error(f"Failed to encrypt message: {e}")
                                continue

                        # Sign the message
                        self._sign_message(msg)

                    # Add timestamp if not present
                    if not msg.timestamp:
                        msg.timestamp = datetime.now(timezone.utc)

                    # Send message
                    await self.ws.send(json.dumps(msg.to_dict()))

                except asyncio.TimeoutError:
                    # No messages to send, continue
                    continue
                except Exception as e:
                    logger.error(f"Write pump error: {e}")
                    await self._handle_reconnect()
                    return
        except Exception as e:
            logger.error(f"Fatal write pump error: {e}")
        finally:
            logger.debug("Write pump exiting")

    async def send_message(self, msg: Message) -> None:
        """Send a message"""
        msg.from_user = self.user_id
        if not msg.timestamp:
            msg.timestamp = datetime.now(timezone.utc)

        await self.send_queue.put(msg)

    async def broadcast_message(self, content: str) -> None:
        """Send a broadcast message"""
        msg = Message(
            from_user=self.user_id,
            to="broadcast",
            content=content,
            timestamp=datetime.now(timezone.utc),
        )
        await self.send_message(msg)

    async def messages(self) -> Message:
        """Get next received message"""
        return await self.recv_queue.get()

    async def disconnect(self) -> None:
        """Disconnect from server"""
        self.done.set()

        if self.ws:
            await self.ws.close()
            self.ws = None

        if self.read_task:
            self.read_task.cancel()
        if self.write_task:
            self.write_task.cancel()

    async def _handle_reconnect(self) -> None:
        """Handle reconnection with exponential backoff"""
        if self.ws:
            await self.ws.close()
            self.ws = None

        interval = self.reconnect_interval
        while not self.done.is_set():
            logger.info("Attempting to reconnect...")
            try:
                await self.connect()
                logger.info("Reconnected successfully")
                return
            except Exception as e:
                logger.error(f"Reconnect failed: {e}")
                await asyncio.sleep(interval)
                if interval < 60:
                    interval *= 2

    # Encryption/decryption helper methods

    @staticmethod
    def _convert_ed25519_to_x25519_public(
        ed_pub: ed25519.Ed25519PublicKey,
    ) -> X25519PublicKey:
        """Convert Ed25519 public key to X25519"""
        ed_pub_bytes = ed_pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        # Use nacl library for conversion
        from nacl.signing import VerifyKey

        verify_key = VerifyKey(ed_pub_bytes)
        return verify_key.to_curve25519_public_key()

    @staticmethod
    def _convert_ed25519_to_x25519_private(
        ed_priv: ed25519.Ed25519PrivateKey,
    ) -> X25519PrivateKey:
        """Convert Ed25519 private key to X25519"""
        # Get the seed (first 32 bytes)
        ed_priv_bytes = ed_priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        seed = ed_priv_bytes[:32]

        # Use nacl library for conversion
        from nacl.signing import SigningKey

        signing_key = SigningKey(seed)
        return signing_key.to_curve25519_private_key()

    async def _encrypt_direct_message(
        self,
        plaintext: str,
        recipient_ed_pub: ed25519.Ed25519PublicKey,
    ) -> str:
        """Encrypt a direct message using hybrid encryption"""
        # Generate symmetric key
        sym_key = random(32)

        # Encrypt plaintext with AES-GCM
        aes_gcm = AESGCM(sym_key)
        data_nonce = random(12)
        ciphertext = aes_gcm.encrypt(data_nonce, plaintext.encode(), None)

        # Convert recipient's Ed25519 to X25519
        recipient_x25519 = self._convert_ed25519_to_x25519_public(recipient_ed_pub)

        # Generate ephemeral key pair using NaCl
        ephemeral_priv = X25519PrivateKey.generate()
        ephemeral_pub = ephemeral_priv.public_key

        # Encrypt symmetric key with NaCl box
        box = Box(ephemeral_priv, recipient_x25519)
        key_nonce = random(24)
        # encrypt() returns combined nonce + ciphertext, so we slice off the nonce
        encrypted = box.encrypt(sym_key, key_nonce)
        encrypted_key = encrypted[
            24:
        ]  # Remove nonce prefix since we store it separately

        # Create envelope
        envelope = EncryptedMessage(
            ephemeral_public_key=base64.b64encode(bytes(ephemeral_pub)).decode("utf-8"),
            key_nonce=base64.b64encode(key_nonce).decode("utf-8"),
            encrypted_key=base64.b64encode(encrypted_key).decode("utf-8"),
            data_nonce=base64.b64encode(data_nonce).decode("utf-8"),
            encrypted_content=base64.b64encode(ciphertext).decode("utf-8"),
        )

        return json.dumps(envelope.to_dict())

    async def _decrypt_direct_message(self, encrypted_envelope: str) -> str:
        """Decrypt a direct message"""
        # Parse envelope
        envelope_dict = json.loads(encrypted_envelope)
        envelope = EncryptedMessage(**envelope_dict)

        # Decode ephemeral public key
        ephemeral_pub_bytes = base64.b64decode(envelope.ephemeral_public_key)
        ephemeral_pub = X25519PublicKey(ephemeral_pub_bytes)

        # Convert our Ed25519 private key to X25519
        our_x25519_priv = self._convert_ed25519_to_x25519_private(self.private_key)

        # Decrypt symmetric key
        box = Box(our_x25519_priv, ephemeral_pub)
        key_nonce = base64.b64decode(envelope.key_nonce)
        encrypted_key = base64.b64decode(envelope.encrypted_key)

        # NaCl box decrypt returns combined nonce+ciphertext,
        # so we need to reconstruct it
        combined = key_nonce + encrypted_key
        sym_key = box.decrypt(combined)

        # Decrypt content with AES-GCM
        aes_gcm = AESGCM(sym_key)
        data_nonce = base64.b64decode(envelope.data_nonce)
        encrypted_content = base64.b64decode(envelope.encrypted_content)

        plaintext = aes_gcm.decrypt(data_nonce, encrypted_content, None)
        return plaintext.decode("utf-8")


# Factory function to create client
def new_client(
    server_url: str,
    user_id: str,
    private_key: ed25519.Ed25519PrivateKey,
    public_key: ed25519.Ed25519PublicKey,
) -> Client:
    """Create new client instance"""
    return Client(server_url, user_id, private_key, public_key)
