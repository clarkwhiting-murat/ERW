from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class StatePosterior(BaseModel):
    """StatePosterior model"""
    __tablename__ = "state_posteriors"

    config_id = Column(String, ForeignKey("configurations.config_id"), nullable=False, index=True)
    eta_r0_mean = Column(Float, nullable=True)
    eta_r0_var = Column(Float, nullable=True)
    eta_phi0_mean = Column(Float, nullable=True)
    eta_phi0_var = Column(Float, nullable=True)
    alpha_r = Column(Float, nullable=True)
    alpha_phi = Column(Float, nullable=True)
    sigma_r = Column(Float, nullable=True)
    sigma_phi = Column(Float, nullable=True)

    # Relationships
    configuration = relationship("Configuration", back_populates="state_posteriors")

