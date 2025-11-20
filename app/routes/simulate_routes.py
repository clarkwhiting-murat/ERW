from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
from app.models.database import get_db
from app.services.simulation_service import SimulationService
from app.constants import MIN_N_RUNS, MAX_N_RUNS
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class SimulateRequest(BaseModel):
    config_id: str = Field(..., min_length=1, max_length=100, description="Configuration ID")
    n_runs: int = Field(..., ge=MIN_N_RUNS, le=MAX_N_RUNS, description="Number of simulation runs")
    risk_profile: Optional[str] = Field(None, max_length=100, description="Optional risk profile ID")


@router.post("/")
@limiter.limit("3/minute")
async def simulate(
    request: Request,
    simulate_request: SimulateRequest,
    db: Session = Depends(get_db)
):
    """Run simulation for a configuration"""
    service = SimulationService(db)
    try:
        result = service.simulate(
            simulate_request.config_id,
            simulate_request.n_runs,
            simulate_request.risk_profile
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running simulation for {simulate_request.config_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while running simulation")

