from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.waitlist import WaitlistSubscriber
from app.services.monitor_service import notify_monitor
from app.services.rate_limit_service import is_rate_limited, record_action


router = APIRouter(tags=["waitlist"])


class WaitlistRequest(BaseModel):
    email: EmailStr
    region: str = Field(..., min_length=2, max_length=10)
    role: str = Field(..., min_length=2, max_length=32)
    phone: Optional[str] = Field(None, max_length=20)
    telegram: Optional[str] = Field(None, max_length=50)
    note: Optional[str] = Field(None, max_length=255)
    source: Optional[str] = Field(None, max_length=32)


@router.post("/waitlist")
def join_waitlist(
    data: WaitlistRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Join the waitlist.

    Rate-limited by IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    action = "waitlist_submit"

    if is_rate_limited(db, client_ip, action):
        raise HTTPException(status_code=429, detail="Too many requests")

    record_action(db, client_ip, action)

    existing = db.query(WaitlistSubscriber).filter_by(email=str(data.email)).first()
    if existing:
        return {"success": False, "message": "This email is already on the waitlist"}

    subscriber = WaitlistSubscriber(
        email=str(data.email),
        region=data.region,
        role=data.role,
        phone=data.phone,
        telegram=data.telegram,
        note=data.note,
        source=data.source,
    )

    db.add(subscriber)
    db.commit()

    notify_monitor(
        "🟢 <b>New Waitlist Signup</b>\n\n"
        f"📧 Email: {data.email}\n"
        f"🌍 Region: {data.region}\n"
        f"👤 Role: {data.role}\n"
        f"📱 Telegram: {data.telegram or '-'}\n"
        f"🕒 IP: {client_ip}"
    )

    return {"success": True, "message": "Joined successfully"}


@router.get("/waitlist")
def list_waitlist(db: Session = Depends(get_db)):
    rows = (
        db.query(WaitlistSubscriber)
        .order_by(WaitlistSubscriber.created_at.desc())
        .limit(200)
        .all()
    )

    return [
        {
            "email": r.email,
            "region": r.region,
            "role": r.role,
            "telegram": r.telegram,
            "source": r.source,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/waitlist/stats")
def waitlist_stats(db: Session = Depends(get_db)):
    total = db.query(WaitlistSubscriber).count()
    today = db.query(WaitlistSubscriber).filter(
        WaitlistSubscriber.created_at >= datetime.combine(date.today(), datetime.min.time())
    ).count()

    return {"waitlist_total": total, "waitlist_today": today}


@router.get("/waitlist/export")
def export_waitlist(db: Session = Depends(get_db)):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "Region", "Role", "Phone", "Telegram", "Source", "Created At"])

    rows = db.query(WaitlistSubscriber).order_by(WaitlistSubscriber.created_at.desc()).all()
    for r in rows:
        writer.writerow([r.email, r.region, r.role, r.phone, r.telegram, r.source, r.created_at])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=waitlist.csv"},
    )
