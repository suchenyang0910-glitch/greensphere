from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base


class WaitlistSubscriber(Base):
    __tablename__ = "waitlist_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(191), unique=True, index=True, nullable=False)
    region = Column(String(8), nullable=True)
    role = Column(String(32), nullable=True)
    phone = Column(String(20), nullable=True)
    telegram = Column(String(50), nullable=True)
    note = Column(String(255), nullable=True)
    source = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)