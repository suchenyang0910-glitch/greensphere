from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class WaitlistRateLimit(Base):
    __tablename__ = "waitlist_rate_limits"
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), index=True, nullable=False)
    action = Column(String(50), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)