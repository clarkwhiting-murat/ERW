from sqlalchemy import Column, String, JSON
from app.models.database import Base


class RiskProfile(Base):
    """RiskProfile model"""
    __tablename__ = "risk_profiles"

    risk_id = Column(String, primary_key=True, index=True)
    parameters = Column(JSON, nullable=True)

