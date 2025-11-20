from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from app.models.database import get_db
from app.models import FieldRecord, Configuration
from app.constants import MIN_WINDOW_MONTH, MAX_WINDOW_MONTH, MIN_CO2_REMOVED, MAX_CO2_REMOVED
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class FieldRecordCreate(BaseModel):
    config_id: str = Field(..., min_length=1, max_length=100, description="Configuration ID")
    window_start: int = Field(..., ge=MIN_WINDOW_MONTH, le=MAX_WINDOW_MONTH, description="Window start month")
    window_end: int = Field(..., ge=MIN_WINDOW_MONTH, le=MAX_WINDOW_MONTH, description="Window end month")
    co2_removed_t_ha: float = Field(..., ge=MIN_CO2_REMOVED, le=MAX_CO2_REMOVED, description="CO2 removed in t/ha")

    @field_validator('window_end')
    @classmethod
    def validate_window_end(cls, v, info):
        if 'window_start' in info.data and v <= info.data['window_start']:
            raise ValueError("window_end must be greater than window_start")
        return v


class FieldDataIngest(BaseModel):
    records: List[FieldRecordCreate] = Field(..., min_length=1, max_length=10000, description="List of field records")

    @field_validator('records')
    @classmethod
    def validate_records(cls, v):
        if not v:
            raise ValueError("At least one record is required")
        return v


@router.post("/ingest")
@limiter.limit("20/minute")
async def ingest_field_data(
    request: Request,
    data: FieldDataIngest,
    db: Session = Depends(get_db)
):
    """Ingest field data records"""
    try:
        field_records = []
        
        for record in data.records:
            # Verify configuration exists
            config = db.query(Configuration).filter(
                Configuration.config_id == record.config_id
            ).first()
            
            if not config:
                raise HTTPException(
                    status_code=400,
                    detail=f"Configuration {record.config_id} not found"
                )
            
            field_record = FieldRecord(
                config_id=record.config_id,
                window_start=record.window_start,
                window_end=record.window_end,
                co2_removed_t_ha=record.co2_removed_t_ha
            )
            field_records.append(field_record)
        
        db.add_all(field_records)
        db.commit()
        
        return {
            "status": "success",
            "records_ingested": len(field_records),
            "message": f"Successfully ingested {len(field_records)} field records"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting field data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while ingesting field data")

