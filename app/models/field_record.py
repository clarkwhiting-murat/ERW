from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class FieldRecord(BaseModel):
    """FieldRecord model"""
    __tablename__ = "field_records"

    config_id = Column(String, ForeignKey("configurations.config_id"), nullable=False, index=True)
    window_start = Column(Integer, nullable=False)
    window_end = Column(Integer, nullable=False)
    co2_removed_t_ha = Column(Float, nullable=False)

    # Relationships
    configuration = relationship("Configuration", back_populates="field_records")

