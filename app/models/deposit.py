from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import relationship
from app.models.database import Base


class Deposit(Base):
    """Deposit model"""
    __tablename__ = "deposits"

    deposit_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    geochem_summary = Column(JSON, nullable=True)
    climate_bucket = Column(String, nullable=True)

    # Relationships
    configurations = relationship("Configuration", back_populates="deposit", cascade="all, delete-orphan")

