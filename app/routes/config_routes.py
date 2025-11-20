from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from app.models.database import get_db
from app.models import Configuration
from app.constants import (
    VALID_CLIMATE_BUCKETS, MIN_APPLICATION_RATE, MAX_APPLICATION_RATE,
    MIN_SIZE_FRACTION, MAX_SIZE_FRACTION, MIN_CHEMISTRY_FACTOR, MAX_CHEMISTRY_FACTOR
)
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ConfigurationCreate(BaseModel):
    config_id: str = Field(..., min_length=1, max_length=100, description="Configuration ID")
    deposit_id: str = Field(..., min_length=1, max_length=100, description="Deposit ID")
    blend_code: Optional[str] = Field(None, max_length=100, description="Rock product name")
    size_fraction_mm: Optional[float] = Field(None, ge=MIN_SIZE_FRACTION, le=MAX_SIZE_FRACTION, description="Particle size in mm")
    application_rate_t_ha: Optional[float] = Field(None, ge=MIN_APPLICATION_RATE, le=MAX_APPLICATION_RATE, description="Application rate in t/ha")
    chemistry_factor_K: Optional[float] = Field(None, ge=MIN_CHEMISTRY_FACTOR, le=MAX_CHEMISTRY_FACTOR, description="Chemistry factor K")
    climate_bucket: Optional[str] = Field(None, description="Climate setting")
    is_candidate: bool = False

    @field_validator('climate_bucket')
    @classmethod
    def validate_climate_bucket(cls, v):
        if v is not None and v not in VALID_CLIMATE_BUCKETS:
            raise ValueError(f"climate_bucket must be one of {VALID_CLIMATE_BUCKETS}")
        return v


class ConfigurationUpdate(BaseModel):
    deposit_id: Optional[str] = Field(None, min_length=1, max_length=100)
    blend_code: Optional[str] = Field(None, max_length=100)
    size_fraction_mm: Optional[float] = Field(None, ge=MIN_SIZE_FRACTION, le=MAX_SIZE_FRACTION)
    application_rate_t_ha: Optional[float] = Field(None, ge=MIN_APPLICATION_RATE, le=MAX_APPLICATION_RATE)
    chemistry_factor_K: Optional[float] = Field(None, ge=MIN_CHEMISTRY_FACTOR, le=MAX_CHEMISTRY_FACTOR)
    climate_bucket: Optional[str] = None
    is_candidate: Optional[bool] = None

    @field_validator('climate_bucket')
    @classmethod
    def validate_climate_bucket(cls, v):
        if v is not None and v not in VALID_CLIMATE_BUCKETS:
            raise ValueError(f"climate_bucket must be one of {VALID_CLIMATE_BUCKETS}")
        return v


@router.post("/")
@limiter.limit("10/minute")
async def create_config(
    request: Request,
    config: ConfigurationCreate,
    db: Session = Depends(get_db)
):
    """Create a new configuration"""
    try:
        # Check if config already exists
        existing = db.query(Configuration).filter(
            Configuration.config_id == config.config_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Configuration {config.config_id} already exists")
        
        new_config = Configuration(
            config_id=config.config_id,
            deposit_id=config.deposit_id,
            blend_code=config.blend_code,
            size_fraction_mm=config.size_fraction_mm,
            application_rate_t_ha=config.application_rate_t_ha,
            chemistry_factor_K=config.chemistry_factor_K,
            climate_bucket=config.climate_bucket,
            is_candidate=config.is_candidate
        )
        
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        return {
            "status": "success",
            "config_id": new_config.config_id,
            "message": "Configuration created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating configuration: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while creating the configuration")


@router.get("/{config_id}")
@limiter.limit("30/minute")
async def get_config(
    request: Request,
    config_id: str,
    db: Session = Depends(get_db)
):
    """Get configuration by ID"""
    config = db.query(Configuration).filter(
        Configuration.config_id == config_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
    
    return {
        "config_id": config.config_id,
        "deposit_id": config.deposit_id,
        "blend_code": config.blend_code,
        "size_fraction_mm": config.size_fraction_mm,
        "application_rate_t_ha": config.application_rate_t_ha,
        "chemistry_factor_K": config.chemistry_factor_K,
        "climate_bucket": config.climate_bucket,
        "is_candidate": config.is_candidate
    }


@router.put("/{config_id}")
@limiter.limit("10/minute")
async def update_config(
    request: Request,
    config_id: str,
    config_update: ConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """Update configuration"""
    try:
        config = db.query(Configuration).filter(
            Configuration.config_id == config_id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Update only provided fields
        update_data = config_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        
        db.commit()
        db.refresh(config)
        
        return {
            "status": "success",
            "config_id": config.config_id,
            "message": "Configuration updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating configuration {config_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while updating the configuration")

