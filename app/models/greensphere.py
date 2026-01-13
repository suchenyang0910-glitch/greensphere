from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Date, Boolean, func
from app.core.database import Base

class TelegramUser(Base):
    __tablename__ = "telegram_users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    username = Column(String(64))
    first_name = Column(String(64))
    last_name = Column(String(64))
    created_at = Column(DateTime, server_default=func.current_timestamp())

class Quest(Base):
    __tablename__ = "quests"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    points = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.current_timestamp())

class QuestSubmission(Base):
    __tablename__ = "quest_submissions"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    quest_code = Column(String(50), nullable=False)
    submitted_at = Column(DateTime, server_default=func.current_timestamp())
    submit_date = Column(Date, nullable=True, index=True)

class PointTransaction(Base):
    __tablename__ = "point_transactions"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    points = Column(Integer, nullable=False)
    source = Column(String(50))
    created_at = Column(DateTime, server_default=func.current_timestamp())

class LeafpassStatus(Base):
    __tablename__ = "leafpass_status"
    telegram_id = Column(BigInteger, primary_key=True)
    level = Column(String(20), nullable=False)
    total_points = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.current_timestamp())
