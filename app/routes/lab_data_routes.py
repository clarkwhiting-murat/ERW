from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from app.models.database import get_db
from app.models import LabRecord, Configuration
from app.constants import MIN_TIME_MONTHS, MAX_TIME_MONTHS, MIN_CO2_UPTAKE, MAX_CO2_UPTAKE
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class LabRecordCreate(BaseModel):
    config_id: str = Field(..., min_length=1, max_length=100, description="Configuration ID")
    time_months: float = Field(..., ge=MIN_TIME_MONTHS, le=MAX_TIME_MONTHS, description="Time in months")
    co2_uptake_t_per_t: float = Field(..., ge=MIN_CO2_UPTAKE, le=MAX_CO2_UPTAKE, description="CO2 uptake in t/t")


class LabDataIngest(BaseModel):
    records: List[LabRecordCreate] = Field(..., min_length=1, max_length=10000, description="List of lab records")

    @field_validator('records')
    @classmethod
    def validate_records(cls, v):
        if not v:
            raise ValueError("At least one record is required")
        return v


@router.post("/ingest")
@limiter.limit("20/minute")
async def ingest_lab_data(
    request: Request,
    data: LabDataIngest,
    db: Session = Depends(get_db)
):
    """Ingest lab data records"""
    try:
        lab_records = []
        
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
            
            lab_record = LabRecord(
                config_id=record.config_id,
                time_months=record.time_months,
                co2_uptake_t_per_t=record.co2_uptake_t_per_t
            )
            lab_records.append(lab_record)
        
        db.add_all(lab_records)
        db.commit()
        
        return {
            "status": "success",
            "records_ingested": len(lab_records),
            "message": f"Successfully ingested {len(lab_records)} lab records"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting lab data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while ingesting lab data")

