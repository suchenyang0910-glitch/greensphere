from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(191), unique=True, index=True, nullable=False)
    country = Column(String(32), nullable=True)
    industry = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    emissions = relationship("CompanyEmission", back_populates="company", cascade="all, delete-orphan")
    offsets = relationship("CompanyOffset", back_populates="company", cascade="all, delete-orphan")


class CompanyEmission(Base):
    __tablename__ = "company_emissions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    scope1_tco2e = Column(Float, nullable=True)
    scope2_tco2e = Column(Float, nullable=True)
    scope3_tco2e = Column(Float, nullable=True)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="emissions")


class CompanyOffset(Base):
    __tablename__ = "company_offsets"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    purchased_at = Column(Date, nullable=False, default=date.today)
    amount_tco2e = Column(Float, nullable=False)
    cost_usd = Column(Float, nullable=True)
    provider = Column(String(64), nullable=True)
    reference = Column(String(255), nullable=True)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="offsets")

