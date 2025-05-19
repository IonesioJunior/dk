import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from agent.agent import Agent
from dependencies import get_websocket_client

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# The agent will be injected during startup
agent = None

# Define cookie name for conversation ID
CONVERSATION_COOKIE = "syft_chat_session"


def set_agent(agent_instance: Agent) -> None:
    """Set the agent instance for this module."""
    global agent
    agent = agent_instance


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
async def query_peers(
    request: Request,
    response: Response,
    conversation_id: Optional[str] = Cookie(default=None, alias=CONVERSATION_COOKIE),
) -> dict[str, Any]:
    """Handle chat query with peers mentions and return query ID"""
    try:
        # Parse the request body
        data = await request.json()
        message = data.get("message", "")
        peers = data.get("peers", [])

        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        # Log the received prompt and peers
        logger.info(f"Received peer query - Message: {message}, Peers: {peers}")

        # Create or retrieve conversation
        if not conversation_id or conversation_id not in agent.conversations:
            conversation_id = agent.create_conversation()
            logger.info(f"Created new conversation: {conversation_id}")

        # Send the message to each peer
        logger.info(f"Forwarding message to peers: {peers}")

        # Import the DirectMessage class from websocket_types
        import uuid
        from datetime import datetime, timezone

        from services.websocket_types import (
            CONTENT_TYPE_PROMPT_QUERY,
            DirectMessage,
            PromptQueryMessage,
        )

        # Get the WebSocket client
        ws_client = get_websocket_client()
        if not ws_client:
            logger.error("WebSocket client not available")
            raise HTTPException(status_code=503, detail="WebSocket not connected")

        # Get the user ID from the WebSocket client
        user_id = ws_client.user_id if ws_client else "anonymous"

        # Generate a unique prompt ID for this query (same for all peers)
        prompt_id = str(uuid.uuid4())
        logger.info(f"Generated prompt ID: {prompt_id}")

        # Create direct messages for each peer using proper message type
        for peer in peers:
            # Create a PromptQueryMessage for the content with prompt_id
            prompt_content = PromptQueryMessage(
                prompt_id=prompt_id,
                prompt=message,
                documents=data.get(
                    "documents",
                    None,
                ),  # Optional documents from request
            )

            # Create the JSON content that will be encrypted
            content_to_encrypt = json.dumps(
                {
                    "content_type": CONTENT_TYPE_PROMPT_QUERY,
                    "content": prompt_content.model_dump(),
                },
            )

            # Create a DirectMessage instance
            direct_msg = DirectMessage(
                from_user=user_id,
                to=peer,
                content=content_to_encrypt,  # This will be encrypted by the client
                timestamp=datetime.now(timezone.utc),  # Ensure UTC timestamp
                message_type="direct",  # Explicitly set the message type
            )

            # Convert to dict for the client (the client expects Message dataclass)
            # We'll use the client's Message class from_dict to convert
            from client.client import Message

            client_msg = Message.from_dict(direct_msg.model_dump(by_alias=True))

            logger.info(
                f"Creating direct message to {peer}: {direct_msg.model_dump_json()}",
            )

            # Send via WebSocket client (will be encrypted in the write pump)
            try:
                await ws_client.send_message(client_msg)
                logger.info(f"Successfully sent direct message to {peer}")
            except Exception as e:
                logger.error(f"Failed to send message to {peer}: {e}")

        # Set cookie for conversation persistence
        response.set_cookie(
            key=CONVERSATION_COOKIE,
            value=conversation_id,
            max_age=86400,  # 24 hours
            httponly=True,
            samesite="lax",
        )

        # Return the prompt ID for later retrieval
        return {
            "status": "success",
            "prompt_id": prompt_id,
            "conversation_id": conversation_id,
            "message": "Query sent to peers successfully",
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in query_peers endpoint: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/prompt-responses/{prompt_id}")
async def get_prompt_responses(prompt_id: str) -> dict[str, Any]:
    """Get aggregated responses for a specific prompt ID"""
    try:
        from dependencies import get_websocket_service

        ws_service = get_websocket_service()
        if not ws_service:
            raise HTTPException(
                status_code=503,
                detail="WebSocket service not available",
            )

        responses = await ws_service.get_aggregated_responses(prompt_id)

        return {"status": "success", **responses}
    except Exception as e:
        logger.error(f"Error getting prompt responses: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt-responses")
async def list_prompt_responses() -> dict[str, Any]:
    """List all prompt IDs that have aggregated responses"""
    try:
        from dependencies import get_websocket_service

        ws_service = get_websocket_service()
        if not ws_service:
            raise HTTPException(
                status_code=503,
                detail="WebSocket service not available",
            )

        prompt_ids = await ws_service.get_all_prompt_ids()

        return {"status": "success", "prompt_ids": prompt_ids}
    except Exception as e:
        logger.error(f"Error listing prompt responses: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/prompt-responses/{prompt_id}")
async def clear_prompt_responses(prompt_id: str) -> dict[str, Any]:
    """Clear aggregated responses for a specific prompt ID"""
    try:
        from dependencies import get_websocket_service

        ws_service = get_websocket_service()
        if not ws_service:
            raise HTTPException(
                status_code=503,
                detail="WebSocket service not available",
            )

        cleared = await ws_service.clear_aggregated_responses(prompt_id)

        if not cleared:
            raise HTTPException(status_code=404, detail="Prompt ID not found")

        return {
            "status": "success",
            "message": f"Cleared responses for prompt {prompt_id}",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error clearing prompt responses: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize")
async def summarize_responses(
    request: Request,
    response: Response,
    conversation_id: Optional[str] = Cookie(default=None, alias=CONVERSATION_COOKIE),
) -> StreamingResponse:
    """Summarize aggregated responses from peers"""
    try:
        # Parse the request body
        data = await request.json()
        responses = data.get("responses", [])

        if not responses:
            raise HTTPException(status_code=400, detail="Responses are required")

        # Extract all response texts
        response_texts = []
        for resp in responses:
            if resp.get("type") == "response":
                response_texts.append(
                    f"Response from {resp.get('from_peer', 'unknown')}: "
                    f"{resp.get('response', '')}",
                )
            elif resp.get("type") == "error":
                response_texts.append(
                    f"Error from {resp.get('from_peer', 'unknown')}: "
                    f"{resp.get('error', '')}",
                )

        if not response_texts:
            raise HTTPException(
                status_code=400,
                detail="No valid responses to summarize",
            )

        # Create a comprehensive summary prompt
        summary_prompt = f"""Based on the following responses from different users,
            provide a comprehensive summary and consensus:

{chr(10).join(response_texts)}

Please provide:
1. A general consensus or common themes across the responses
2. Any notable differences or disagreements
3. Key insights or recommendations based on the collective feedback
4. An overall summary of the responses"""

        # Create or retrieve conversation
        if not conversation_id or conversation_id not in agent.conversations:
            conversation_id = agent.create_conversation()
            logger.info(
                f"Created new conversation for summarization: {conversation_id}",
            )

        # Add the original peer responses to conversation history
        agent.add_message_to_conversation(
            conversation_id,
            "user",
            f"Peer responses:\n{chr(10).join(response_texts)}",
        )

        # Stream the summary response
        async def generate() -> AsyncGenerator[str, None]:
            try:
                # Send start signal
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
                    message=summary_prompt,
                ):
                    yield json.dumps({"type": "chunk", "content": chunk}) + "\n"

                # Send completion signal
                yield json.dumps({"type": "complete"}) + "\n"

            except Exception as e:
                logger.error(f"Error in summarization: {e!s}", exc_info=True)
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

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in summarize endpoint: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-users")
async def active_users() -> dict[str, Any]:
    """Proxy endpoint to fetch active users from distributedknowledge.org"""
    import aiohttp

    # Get the current user ID from the WebSocket client
    ws_client = get_websocket_client()
    current_user_id = ws_client.user_id if ws_client else None

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get("https://distributedknowledge.org/active-users") as response,
        ):
            if response.status == 200:
                data = await response.json()
                # Add current user ID to the response
                data["current_user_id"] = current_user_id
                return data
            logger.error(f"Failed to fetch active users: HTTP {response.status}")
            return {"online": [], "offline": [], "current_user_id": current_user_id}
    except Exception as e:
        logger.error(f"Error fetching active users: {e}")
        return {"online": [], "offline": [], "current_user_id": current_user_id}
