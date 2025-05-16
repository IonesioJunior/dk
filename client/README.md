# Python Client for Syft Agent

This is a Python implementation of the WebSocket client, equivalent to the Go client.go implementation.

## Features

- Ed25519 key-based authentication and signatures
- Hybrid encryption using NaCl box + AES-GCM
- WebSocket communication with JWT authentication
- HTTP endpoints for registration, login, and user data
- Message signing/verification and encryption/decryption
- Automatic reconnection with exponential backoff

## Usage

```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from client import new_client, Message

# Generate key pair
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Create client
client = new_client("https://server.example.com", "user_id", private_key, public_key)

# Register and login
await client.register("username")
await client.login()

# Connect to WebSocket
await client.connect()

# Send messages
await client.broadcast_message("Hello everyone!")

# Send direct message
msg = Message(from_user="user_id", to="recipient_id", content="Hello!")
await client.send_message(msg)

# Receive messages
while True:
    msg = await client.messages()
    print(f"From {msg.from_user}: {msg.content}")
```

## Client Methods

### Core Methods
- `new_client(server_url, user_id, private_key, public_key)`: Create client instance
- `register(username)`: Register new user
- `login()`: Authenticate with server
- `connect()`: Start WebSocket connection
- `disconnect()`: Close connection

### Messaging
- `send_message(msg)`: Send a message
- `broadcast_message(content)`: Send broadcast message
- `messages()`: Get next received message

### User Management
- `get_active_users()`: Get online/offline users
- `get_user_descriptions(user_id)`: Get user descriptions
- `set_user_descriptions(descriptions)`: Set user descriptions
- `get_user_public_key(user_id)`: Get user's public key

### Configuration
- `set_insecure(insecure)`: Enable/disable SSL verification
- `set_reconnect_interval(interval)`: Set reconnection interval

## Message Structure

```python
@dataclass
class Message:
    from_user: str
    to: str  # "broadcast" for broadcast messages
    content: str
    timestamp: Optional[datetime] = None
    status: Optional[str] = None  # "verified", "unsigned", etc.
    signature: Optional[str] = None
    is_forward_message: bool = False
    id: Optional[int] = None
```

## Security Features

1. **Authentication**: Ed25519 key-based challenge-response
2. **Message Signatures**: All messages are signed with sender's private key
3. **Encryption**: Direct messages use hybrid encryption (NaCl box + AES-GCM)
4. **Key Management**: Automatic caching of user public keys

## Requirements

- Python 3.7+
- aiohttp
- websockets
- cryptography
- pynacl

## Testing

See `test_client.py` for a complete example of client usage.