import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from agent.agent import Agent

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize the agent with default configuration
agent = Agent()

# Define cookie name for conversation ID
CONVERSATION_COOKIE = "syft_chat_session"


@router.post("/query")
async def query(
    request: Request,
    response: Response,
    conversation_id: Optional[str] = Cookie(default=None, alias=CONVERSATION_COOKIE),
) -> StreamingResponse:
    """Handle chat query with streaming response and conversation history"""
    try:
        # Parse the request body
        data = await request.json()
        message = data.get("message", "")

        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        # Create or retrieve conversation
        if not conversation_id or conversation_id not in agent.conversations:
            conversation_id = agent.create_conversation()
            logger.info(f"Created new conversation: {conversation_id}")

        # Stream the response from the LLM
        async def generate() -> AsyncGenerator[str, None]:
            try:
                # First, send a success status with conversation ID
                yield (
                    json.dumps(
                        {
                            "status": "success",
                            "type": "start",
                            "conversation_id": conversation_id,
                        },
                    )
                    + "\n"
                )

                # Get streaming response from the agent with conversation history
                async for chunk in agent.send_streaming_message_with_history(
                    conversation_id=conversation_id,
                    message=message,
                ):
                    yield json.dumps({"type": "chunk", "content": chunk}) + "\n"

                # Send completion signal
                yield json.dumps({"type": "complete"}) + "\n"

            except Exception as e:
                logger.error(f"Error in streaming response: {e!s}", exc_info=True)
                yield json.dumps({"status": "error", "message": str(e)}) + "\n"

        # Create streaming response
        streaming_response = StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

        # Set cookie for conversation persistence
        streaming_response.set_cookie(
            key=CONVERSATION_COOKIE,
            value=conversation_id,
            max_age=86400,  # 24 hours
            httponly=True,
            samesite="lax",
        )

        return streaming_response

    except Exception as e:
        logger.error(f"Error in query endpoint: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query_peers")
async def query_peers(data: dict[str, Any]) -> dict[str, Any]:
    """POST query_peers endpoint"""
    # Implementation placeholder
    return {"peers": "peers_query_response", "query": data}


@router.post("/query_network")
async def query_network(data: dict[str, Any]) -> dict[str, Any]:
    """POST query_network endpoint"""
    # Implementation placeholder
    return {"network": "network_query_response", "query": data}


@router.post("/chat")
async def chat(
    request: Request,
    response: Response,
    conversation_id: Optional[str] = Cookie(default=None, alias=CONVERSATION_COOKIE),
) -> StreamingResponse:
    """Handle chat requests with streaming response - same as query"""
    return await query(request, response, conversation_id)


@router.post("/clear-conversation")
async def clear_conversation(
    response: Response,
    conversation_id: Optional[str] = Cookie(default=None, alias=CONVERSATION_COOKIE),
) -> dict[str, Any]:
    """Clear the current conversation history and start fresh"""
    try:
        # Clear the conversation if it exists
        if conversation_id and conversation_id in agent.conversations:
            del agent.conversations[conversation_id]
            logger.info(f"Cleared conversation: {conversation_id}")

        # Clear the cookie
        response.delete_cookie(key=CONVERSATION_COOKIE)

        return {
            "status": "success",
            "message": "Conversation cleared",
        }
    except Exception as e:
        logger.error(f"Error clearing conversation: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation-history")
async def get_conversation_history(
    conversation_id: Optional[str] = Cookie(default=None, alias=CONVERSATION_COOKIE),
) -> dict[str, Any]:
    """Get the current conversation history"""
    try:
        if not conversation_id or conversation_id not in agent.conversations:
            return {
                "status": "success",
                "history": [],
                "conversation_id": None,
            }

        history = agent.get_conversation_history(conversation_id)
        return {
            "status": "success",
            "history": history,
            "conversation_id": conversation_id,
        }
    except Exception as e:
        logger.error(f"Error getting conversation history: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))
