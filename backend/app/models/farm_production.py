from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class FarmProduction(Base):
    __tablename__ = "farm_productions"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    crop_type = Column(String, nullable=False)
    season = Column(String, nullable=False)
    location = Column(String, nullable=True)
    planted_date = Column(Date, nullable=False)
    expected_harvest_date = Column(Date, nullable=True)
    actual_harvest_date = Column(Date, nullable=True)
    expected_quantity_kg = Column(Float, nullable=False)
    actual_quantity_kg = Column(Float, nullable=True)
    quality_grade = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    logged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cooperative = relationship("Cooperative")
    logger = relationship("User")
