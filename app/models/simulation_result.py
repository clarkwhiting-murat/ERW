from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class SimulationResult(BaseModel):
    """SimulationResult model"""
    __tablename__ = "simulation_results"

    config_id = Column(String, ForeignKey("configurations.config_id"), nullable=False, index=True)
    n_total = Column(Float, nullable=True)
    run_index = Column(Integer, nullable=True)

    # Relationships
    configuration = relationship("Configuration", back_populates="simulation_results")

