"""WebSocket message types and data structures using Pydantic"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal, List, Union
from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message structure for all WebSocket communications"""

    id: Optional[int] = Field(None, description="Unique message identifier")
    from_user: str = Field(..., alias="from", description="Sender's user ID")
    to: str = Field(
        ..., description="Recipient(s) - can be user ID, 'broadcast', or 'system'"
    )
    content: str = Field(..., description="Message content (plaintext or encrypted)")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp in UTC")
    status: Optional[str] = Field(
        None, description="Message status (verified, unsigned, etc.)"
    )
    signature: Optional[str] = Field(
        None, description="Base64 encoded message signature"
    )
    is_forward_message: bool = Field(
        False, description="Whether this is a forwarded message"
    )

    class Config:
        # Allow "from" as field name
        populate_by_name = True
        # Enable JSON schema generation
        json_schema_extra = {
            "example": {
                "from": "user123",
                "to": "user456",
                "content": "Hello!",
                "timestamp": "2024-01-01T12:00:00Z",
                "status": "verified",
                "signature": "base64signature==",
                "is_forward_message": False,
            }
        }


class PromptQueryMessage(BaseModel):
    """Message format for prompt queries sent in direct messages"""

    prompt_id: str = Field(
        ..., description="Unique identifier for tracking query/response pairs"
    )
    prompt: str = Field(..., description="The prompt/query text")
    documents: Optional[List[str]] = Field(
        None, description="Optional list of document references"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
                "prompt": "What is the weather today?",
                "documents": ["doc1.pdf", "doc2.txt"],
            }
        }

    # Example of how this would look when encrypted in a DirectMessage:
    # DirectMessage.content = encrypt(json.dumps({
    #     "content_type": "prompt_query",
    #     "content": {
    #         "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
    #         "prompt": "What is the weather today?",
    #         "documents": ["doc1.pdf", "doc2.txt"]
    #     }
    # }))


class PromptResponseMessage(BaseModel):
    """Message format for responses to prompt queries"""

    prompt_id: str = Field(
        ..., description="Unique identifier matching the original query"
    )
    response: str = Field(..., description="The response text")
    timestamp: str = Field(..., description="ISO format timestamp of the response")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
                "response": "The weather today is sunny with a high of 72°F.",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }


class ErrorMessage(BaseModel):
    """Message format for error responses"""

    prompt_id: Optional[str] = Field(
        None, description="Unique identifier matching the original query if available"
    )
    error: str = Field(..., description="The error message")
    timestamp: str = Field(..., description="ISO format timestamp of the error")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
                "error": "Failed to process prompt: Invalid model configuration",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }


# Available content types for decrypted messages
CONTENT_TYPE_PROMPT_QUERY = "prompt_query"
CONTENT_TYPE_PROMPT_RESPONSE = "prompt_response"
CONTENT_TYPE_ERROR = "error"

# Map of content types to their validators
CONTENT_TYPE_MAP = {
    CONTENT_TYPE_PROMPT_QUERY: PromptQueryMessage,
    CONTENT_TYPE_PROMPT_RESPONSE: PromptResponseMessage,
    CONTENT_TYPE_ERROR: ErrorMessage,
}


class DirectMessage(BaseMessage):
    """Direct message between two users (encrypted)"""

    message_type: Literal["direct"] = Field(
        "direct", description="Message type identifier"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message_type": "direct",
                "from": "user123",
                "to": "user456",
                "content": '{"ephemeral_public_key":"...","encrypted_content":"..."}',
                "timestamp": "2024-01-01T12:00:00Z",
                "signature": "base64signature==",
            }
        }


class BroadcastMessage(BaseMessage):
    """Broadcast message to all connected users"""

    message_type: Literal["broadcast"] = Field(
        "broadcast", description="Message type identifier"
    )
    to: Literal["broadcast"] = Field(
        "broadcast", description="Broadcast recipient identifier"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message_type": "broadcast",
                "from": "user123",
                "to": "broadcast",
                "content": "Hello everyone!",
                "timestamp": "2024-01-01T12:00:00Z",
                "signature": "base64signature==",
            }
        }


class ForwardedMessage(BaseMessage):
    """Forwarded message from another user"""

    message_type: Literal["forwarded"] = Field(
        "forwarded", description="Message type identifier"
    )
    is_forward_message: Literal[True] = Field(
        True, description="Always True for forwarded messages"
    )
    original_sender: Optional[str] = Field(None, description="Original message sender")

    class Config:
        json_schema_extra = {
            "example": {
                "message_type": "forwarded",
                "from": "forwarder_user",
                "to": "recipient_user",
                "content": "Forwarded content",
                "is_forward_message": True,
                "original_sender": "original_user",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }


class SystemMessage(BaseMessage):
    """System message from the server"""

    message_type: Literal["system"] = Field(
        "system", description="Message type identifier"
    )
    from_user: Literal["system"] = Field(
        "system", description="System sender identifier"
    )
    status: Optional[str] = Field("info", description="System message status/severity")

    class Config:
        json_schema_extra = {
            "example": {
                "message_type": "system",
                "from": "system",
                "to": "user123",
                "content": "User user456 has connected",
                "status": "info",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }


class EncryptedMessageEnvelope(BaseModel):
    """Structure for encrypted message envelope used in direct messages"""

    ephemeral_public_key: str = Field(
        ..., description="Base64 encoded ephemeral public key"
    )
    key_nonce: str = Field(..., description="Base64 encoded nonce for key encryption")
    encrypted_key: str = Field(
        ..., description="Base64 encoded encrypted symmetric key"
    )
    data_nonce: str = Field(..., description="Base64 encoded nonce for data encryption")
    encrypted_content: str = Field(
        ..., description="Base64 encoded encrypted message content"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ephemeral_public_key": "base64key==",
                "key_nonce": "base64nonce==",
                "encrypted_key": "base64encrypted==",
                "data_nonce": "base64datanonce==",
                "encrypted_content": "base64content==",
            }
        }


# Message status constants
class MessageStatus:
    """Possible message status values"""

    PENDING = "pending"
    VERIFIED = "verified"
    UNSIGNED = "unsigned"
    UNVERIFIED = "unverified"
    INVALID_SIGNATURE = "invalid_signature"
    DECRYPTION_FAILED = "decryption_failed"
    DELIVERED = "delivered"
    ERROR = "error"


# Type mapping for message deserialization
MESSAGE_TYPE_MAP = {
    "direct": DirectMessage,
    "broadcast": BroadcastMessage,
    "forwarded": ForwardedMessage,
    "system": SystemMessage,
}


def create_message(data: Dict[str, Any]) -> BaseMessage:
    """Factory function to create appropriate message type from dict"""
    # Determine message type based on content
    is_forward = data.get("is_forward_message", False)
    from_user = data.get("from", "")
    to_user = data.get("to", "")

    if is_forward:
        return ForwardedMessage(**data)
    elif from_user == "system":
        return SystemMessage(**data)
    elif to_user == "broadcast":
        return BroadcastMessage(**data)
    else:
        return DirectMessage(**data)


def validate_message(message_json: str) -> BaseMessage:
    """Validate and deserialize a JSON message string"""
    import json

    try:
        data = json.loads(message_json)
        return create_message(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ValueError(f"Invalid message format: {e}")


def validate_decrypted_content(
    content: Union[str, Dict[str, Any]], content_type: Optional[str] = None
) -> Union[BaseModel, str]:
    """
    Validate decrypted message content based on content type.

    Args:
        content: The decrypted content (string or dict)
        content_type: Optional content type hint

    Returns:
        Validated content model or string if no special handling needed
    """
    if isinstance(content, dict):
        # Auto-detect content type if not provided
        if content_type is None:
            if "prompt" in content and "prompt_id" in content:
                content_type = CONTENT_TYPE_PROMPT_QUERY
            elif (
                "response" in content
                and "timestamp" in content
                and "prompt_id" in content
            ):
                content_type = CONTENT_TYPE_PROMPT_RESPONSE
            elif "error" in content and "timestamp" in content:
                content_type = CONTENT_TYPE_ERROR

        # Validate based on content type
        if content_type in CONTENT_TYPE_MAP:
            validator_class = CONTENT_TYPE_MAP[content_type]
            return validator_class(**content)

    return content


def parse_decrypted_message_content(
    decrypted_json: str,
) -> Union[BaseModel, str, Dict[str, Any]]:
    """
    Parse and validate decrypted message content from JSON string.

    Args:
        decrypted_json: The decrypted JSON string

    Returns:
        Parsed and validated content
    """
    import json

    try:
        # Try to parse as JSON
        content = json.loads(decrypted_json)

        # Check if it has a content_type field
        content_type = content.get("content_type")

        # If it has a nested content field, use that
        if "content" in content:
            return validate_decrypted_content(content["content"], content_type)

        # Otherwise validate the whole object
        return validate_decrypted_content(content, content_type)

    except json.JSONDecodeError:
        # If it's not valid JSON, return as plain string
        return decrypted_json
