from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.models.database import get_db
from app.services.results_service import ResultsService
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class SaveResultsRequest(BaseModel):
    result_id: str
    results: Dict[str, Any]


@router.post("/")
@limiter.limit("20/minute")
async def save_results(
    request: Request,
    save_request: SaveResultsRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Save simulation or analysis results"""
    service = ResultsService(db)
    try:
        result = service.save_results(save_request.result_id, save_request.results)
        return result
    except Exception as e:
        logger.error(f"Error saving results {save_request.result_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while saving results")


@router.get("/summarize/{config_id}")
@limiter.limit("30/minute")
async def summarize(
    request: Request,
    config_id: str,
    target: Optional[float] = Query(None, description="Target value for P_hit calculation"),
    n_runs: Optional[int] = Query(None, description="Number of runs if simulation needs to be run"),
    risk_profile: Optional[str] = Query(None, description="Risk profile ID if simulation needs to be run"),
    db: Session = Depends(get_db)
):
    """Summarize simulation results for a configuration"""
    service = ResultsService(db)
    try:
        result = service.summarize(config_id, target, n_runs, risk_profile)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in results operation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing results")


@router.get("/")
@limiter.limit("30/minute")
async def list_results(
    request: Request,
    config_id: Optional[str] = Query(None, description="Filter by configuration ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=500, description="Number of results per page (max 500)"),
    db: Session = Depends(get_db)
):
    """List all results with optional filters and pagination"""
    service = ResultsService(db)
    try:
        filters = {}
        if config_id:
            filters["config_id"] = config_id
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        results = service.list_results(filters if filters else None, offset=offset, limit=page_size)
        total_count = service.count_results(filters if filters else None)
        
        return {
            "items": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0,
                "has_next": offset + page_size < total_count,
                "has_prev": page > 1
            }
        }
    except Exception as e:
        logger.error(f"Error listing results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while listing results")


@router.get("/{config_id}")
@limiter.limit("30/minute")
async def get_results(
    request: Request,
    config_id: str,
    db: Session = Depends(get_db)
):
    """Get results summary for a configuration"""
    service = ResultsService(db)
    try:
        result = service.summarize(config_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in results operation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing results")


@router.delete("/{result_id}")
@limiter.limit("10/minute")
async def delete_results(
    request: Request,
    result_id: str,
    db: Session = Depends(get_db)
):
    """Delete results by ID"""
    service = ResultsService(db)
    try:
        result = service.delete_results(result_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{result_id}/export")
@limiter.limit("20/minute")
async def export_results(
    request: Request,
    result_id: str,
    format: str = "json",
    db: Session = Depends(get_db)
):
    """Export results in specified format"""
    service = ResultsService(db)
    try:
        result = service.export_results(result_id, format)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

