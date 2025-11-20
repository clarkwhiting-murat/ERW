from sqlalchemy import Column, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.database import Base


class Configuration(Base):
    """Configuration model"""
    __tablename__ = "configurations"

    config_id = Column(String, primary_key=True, index=True)
    deposit_id = Column(String, ForeignKey("deposits.deposit_id"), nullable=False, index=True)
    blend_code = Column(String, nullable=True)
    size_fraction_mm = Column(Float, nullable=True)
    application_rate_t_ha = Column(Float, nullable=True)
    chemistry_factor_K = Column(Float, nullable=True)
    climate_bucket = Column(String, nullable=True)
    is_candidate = Column(Boolean, default=False, nullable=False)

    # Relationships
    deposit = relationship("Deposit", back_populates="configurations")
    lab_records = relationship("LabRecord", back_populates="configuration", cascade="all, delete-orphan")
    field_records = relationship("FieldRecord", back_populates="configuration", cascade="all, delete-orphan")
    state_posteriors = relationship("StatePosterior", back_populates="configuration", cascade="all, delete-orphan")
    simulation_results = relationship("SimulationResult", back_populates="configuration", cascade="all, delete-orphan")

