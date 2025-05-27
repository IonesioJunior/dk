"""Triage management API endpoints."""

import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import get_websocket_service
from policies.triage_models import TriageUpdate
from policies.triage_repository import TriageRepository
from services.triage_notification_service import TriageNotificationService
from services.websocket_service import WebSocketService

logger = logging.getLogger(__name__)

router = APIRouter()


class TriageApprovalRequest(BaseModel):
    """Request model for approving a triage request."""

    reviewed_by: Optional[str] = "app_owner"


class TriageRejectionRequest(BaseModel):
    """Request model for rejecting a triage request."""

    reason: Optional[str] = None
    reviewed_by: Optional[str] = "app_owner"


@router.get("/triage/all")
async def list_all_triage() -> dict[str, Any]:
    """List all triage requests (pending, approved, and rejected)."""
    try:
        triage_repo = TriageRepository()

        # Get requests by status
        pending = triage_repo._list_by_status("pending")
        approved = triage_repo._list_by_status("approved")
        rejected = triage_repo._list_by_status("rejected")

        # Combine all requests
        all_requests = pending + approved + rejected

        # Sort by created_at descending
        all_requests.sort(key=lambda r: r.created_at, reverse=True)

        logger.info(f"Found {len(all_requests)} total triage requests")

        return {
            "status": "success",
            "total_count": len(all_requests),
            "pending_count": len(pending),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "requests": [r.to_dict() for r in all_requests],
        }

    except Exception as e:
        logger.error(f"Error listing all triage requests: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to list all triage requests"
        ) from e


@router.get("/triage/pending")
async def list_pending_triage() -> dict[str, Any]:
    """List all pending triage requests."""
    try:
        triage_repo = TriageRepository()
        pending = triage_repo.list_pending()

        logger.info(f"Found {len(pending)} pending triage requests")

        return {
            "status": "success",
            "pending_count": len(pending),
            "requests": [r.to_dict() for r in pending],
        }

    except Exception as e:
        logger.error(f"Error listing pending triage requests: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to list pending triage requests"
        ) from e


@router.get("/triage/{triage_id}")
async def get_triage_details(triage_id: str) -> dict[str, Any]:
    """Get detailed information about a triage request."""
    try:
        triage_repo = TriageRepository()
        triage_request = triage_repo.get(triage_id)

        if not triage_request:
            raise HTTPException(status_code=404, detail="Triage request not found")

        return {
            "status": "success",
            "request": triage_request.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting triage details: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get triage details"
        ) from e


@router.post("/triage/{triage_id}/approve")
async def approve_triage(
    triage_id: str,
    request: TriageApprovalRequest,
    websocket_service: Annotated[WebSocketService, Depends(get_websocket_service)],
) -> dict[str, Any]:
    """Approve a triage request and send response to user."""
    try:
        triage_repo = TriageRepository()
        triage_request = triage_repo.get(triage_id)

        if not triage_request:
            raise HTTPException(status_code=404, detail="Triage request not found")

        if triage_request.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Triage request already {triage_request.status}",
            )

        # Update status to approved
        update = TriageUpdate(
            status="approved",
            reviewed_by=request.reviewed_by,
        )
        updated_request = triage_repo.update_status(triage_id, update)

        if not updated_request:
            raise HTTPException(status_code=500, detail="Failed to update status")

        # Send the stored response via WebSocket to the user
        notification_service = TriageNotificationService(websocket_service)
        notification_sent = await notification_service.send_approval_notification(
            updated_request
        )

        if not notification_sent:
            logger.warning(
                f"Failed to send notification for approved triage {triage_id}"
            )

        logger.info(f"Approved triage request {triage_id} by {request.reviewed_by}")

        return {
            "status": "success",
            "message": "Triage request approved and response sent to user",
            "notification_sent": notification_sent,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving triage request: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to approve triage request"
        ) from e


@router.post("/triage/{triage_id}/reject")
async def reject_triage(
    triage_id: str,
    request: TriageRejectionRequest,
    websocket_service: Annotated[WebSocketService, Depends(get_websocket_service)],
) -> dict[str, Any]:
    """Reject a triage request."""
    try:
        triage_repo = TriageRepository()
        triage_request = triage_repo.get(triage_id)

        if not triage_request:
            raise HTTPException(status_code=404, detail="Triage request not found")

        if triage_request.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Triage request already {triage_request.status}",
            )

        # Update status to rejected
        update = TriageUpdate(
            status="rejected",
            reviewed_by=request.reviewed_by,
            rejection_reason=request.reason,
        )
        updated_request = triage_repo.update_status(triage_id, update)

        if not updated_request:
            raise HTTPException(status_code=500, detail="Failed to update status")

        # Send rejection message to user via WebSocket
        notification_service = TriageNotificationService(websocket_service)
        notification_sent = await notification_service.send_rejection_notification(
            updated_request
        )

        if not notification_sent:
            logger.warning(
                f"Failed to send notification for rejected triage {triage_id}"
            )

        logger.info(f"Rejected triage request {triage_id} by {request.reviewed_by}")

        return {
            "status": "success",
            "message": "Triage request rejected",
            "notification_sent": notification_sent,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting triage request: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to reject triage request"
        ) from e


@router.get("/triage/user/{user_id}")
async def get_user_triage_history(user_id: str) -> dict[str, Any]:
    """Get all triage requests for a specific user."""
    try:
        triage_repo = TriageRepository()
        requests = triage_repo.list_by_user(user_id)

        return {
            "status": "success",
            "count": len(requests),
            "requests": [r.to_dict() for r in requests],
        }

    except Exception as e:
        logger.error(f"Error getting user triage history: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get user triage history"
        ) from e


@router.get("/triage/api/{api_config_id}")
async def get_api_triage_history(api_config_id: str) -> dict[str, Any]:
    """Get all triage requests for a specific API configuration."""
    try:
        triage_repo = TriageRepository()
        requests = triage_repo.list_by_api_config(api_config_id)

        return {
            "status": "success",
            "count": len(requests),
            "requests": [r.to_dict() for r in requests],
        }

    except Exception as e:
        logger.error(f"Error getting API triage history: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get API triage history"
        ) from e


@router.delete("/triage/{triage_id}")
async def delete_triage(triage_id: str) -> dict[str, Any]:
    """Delete a triage request (only if already processed)."""
    try:
        triage_repo = TriageRepository()
        triage_request = triage_repo.get(triage_id)

        if not triage_request:
            raise HTTPException(status_code=404, detail="Triage request not found")

        if triage_request.status == "pending":
            raise HTTPException(
                status_code=400,
                detail="Cannot delete pending triage requests",
            )

        success = triage_repo.delete(triage_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete request")

        logger.info(f"Deleted triage request {triage_id}")

        return {
            "status": "success",
            "message": "Triage request deleted",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting triage request: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete triage request"
        ) from e


@router.post("/triage/cleanup")
async def cleanup_old_triage(days: int = 30) -> dict[str, Any]:
    """Clean up old processed triage requests."""
    try:
        triage_repo = TriageRepository()
        deleted_count = triage_repo.cleanup_old_requests(days)

        logger.info(f"Cleaned up {deleted_count} old triage requests")

        return {
            "status": "success",
            "message": f"Cleaned up {deleted_count} old triage requests",
        }

    except Exception as e:
        logger.error(f"Error cleaning up triage requests: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to clean up triage requests"
        ) from e
