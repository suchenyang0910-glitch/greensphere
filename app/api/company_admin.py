from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.admin_auth import admin_auth
from app.models.company_carbon import Company, CompanyEmission, CompanyOffset


router = APIRouter(tags=["company"], prefix="/api/admin")


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=191)
    country: Optional[str] = Field(None, max_length=32)
    industry: Optional[str] = Field(None, max_length=64)


class EmissionCreate(BaseModel):
    company_id: int
    period_start: date
    period_end: date
    scope1_tco2e: Optional[float] = None
    scope2_tco2e: Optional[float] = None
    scope3_tco2e: Optional[float] = None
    note: Optional[str] = Field(None, max_length=255)


class OffsetCreate(BaseModel):
    company_id: int
    purchased_at: date = Field(default_factory=date.today)
    amount_tco2e: float
    cost_usd: Optional[float] = None
    provider: Optional[str] = Field(None, max_length=64)
    reference: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = Field(None, max_length=255)


@router.get("/companies")
def list_companies(
    request: Request,
    limit: int = 200,
    db: Session = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    rows = db.query(Company).order_by(Company.id.desc()).limit(int(limit)).all()
    return {
        "companies": [
            {
                "id": r.id,
                "name": r.name,
                "country": r.country,
                "industry": r.industry,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    }


@router.post("/companies")
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    existing = db.query(Company).filter_by(name=data.name).first()
    if existing:
        return {"ok": True, "company_id": existing.id}
    c = Company(name=data.name, country=data.country, industry=data.industry)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"ok": True, "company_id": c.id}


@router.get("/emissions")
def list_emissions(
    company_id: Optional[int] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    q = db.query(CompanyEmission)
    if company_id:
        q = q.filter(CompanyEmission.company_id == int(company_id))
    rows = q.order_by(CompanyEmission.period_end.desc(), CompanyEmission.id.desc()).limit(int(limit)).all()
    return {
        "emissions": [
            {
                "id": r.id,
                "company_id": r.company_id,
                "period_start": r.period_start,
                "period_end": r.period_end,
                "scope1_tco2e": r.scope1_tco2e,
                "scope2_tco2e": r.scope2_tco2e,
                "scope3_tco2e": r.scope3_tco2e,
                "note": r.note,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    }


@router.post("/emissions")
def create_emission(
    data: EmissionCreate,
    db: Session = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    c = db.query(Company).filter_by(id=int(data.company_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    if data.period_end < data.period_start:
        raise HTTPException(status_code=400, detail="period_end must be >= period_start")
    r = CompanyEmission(
        company_id=int(data.company_id),
        period_start=data.period_start,
        period_end=data.period_end,
        scope1_tco2e=data.scope1_tco2e,
        scope2_tco2e=data.scope2_tco2e,
        scope3_tco2e=data.scope3_tco2e,
        note=data.note,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"ok": True, "id": r.id}


@router.get("/offsets")
def list_offsets(
    company_id: Optional[int] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    q = db.query(CompanyOffset)
    if company_id:
        q = q.filter(CompanyOffset.company_id == int(company_id))
    rows = q.order_by(CompanyOffset.purchased_at.desc(), CompanyOffset.id.desc()).limit(int(limit)).all()
    return {
        "offsets": [
            {
                "id": r.id,
                "company_id": r.company_id,
                "purchased_at": r.purchased_at,
                "amount_tco2e": r.amount_tco2e,
                "cost_usd": r.cost_usd,
                "provider": r.provider,
                "reference": r.reference,
                "note": r.note,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    }


@router.post("/offsets")
def create_offset(
    data: OffsetCreate,
    db: Session = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    c = db.query(Company).filter_by(id=int(data.company_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    if data.amount_tco2e <= 0:
        raise HTTPException(status_code=400, detail="amount_tco2e must be > 0")
    r = CompanyOffset(
        company_id=int(data.company_id),
        purchased_at=data.purchased_at,
        amount_tco2e=float(data.amount_tco2e),
        cost_usd=float(data.cost_usd) if data.cost_usd is not None else None,
        provider=data.provider,
        reference=data.reference,
        note=data.note,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"ok": True, "id": r.id}

