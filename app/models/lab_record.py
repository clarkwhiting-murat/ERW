from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class LabRecord(BaseModel):
    """LabRecord model"""
    __tablename__ = "lab_records"

    config_id = Column(String, ForeignKey("configurations.config_id"), nullable=False, index=True)
    time_months = Column(Float, nullable=False)
    co2_uptake_t_per_t = Column(Float, nullable=False)

    # Relationships
    configuration = relationship("Configuration", back_populates="lab_records")

