from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
from app.models.database import get_db
from app.services.model_state_service import ModelStateService
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class UpdateStateRequest(BaseModel):
    config_id: str = Field(..., min_length=1, max_length=100, description="Configuration ID")


@router.post("/update-state")
@limiter.limit("5/minute")
async def update_state(
    request: Request,
    update_request: UpdateStateRequest,
    db: Session = Depends(get_db)
):
    """Update model state using Extended Kalman Filter"""
    service = ModelStateService(db)
    try:
        result = service.update_state(update_request.config_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating model state for {update_request.config_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while updating model state")

