from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_telegram_id
from app.models import PointTransaction, QuestSubmission, LeafpassStatus

router = APIRouter(prefix="/api", tags=["me"])

def calc_streak(db: Session, telegram_id: int) -> int:
    from datetime import date
    rows = db.execute(
        select(QuestSubmission.submit_date)
        .where(QuestSubmission.telegram_id == telegram_id)
        .group_by(QuestSubmission.submit_date)
        .order_by(QuestSubmission.submit_date.desc())
    ).all()
    days = [r[0] for r in rows if r[0] is not None]
    if not days:
        return 0
    streak = 0
    cur = date.today()
    s = set(days)
    while cur in s:
        streak += 1
        cur = date.fromordinal(cur.toordinal() - 1)
    return streak

@router.get("/me")
def me(telegram_id: int = Depends(get_telegram_id), db: Session = Depends(get_db)):
    total_points = db.execute(
        select(func.coalesce(func.sum(PointTransaction.points), 0)).where(PointTransaction.telegram_id == telegram_id)
    ).scalar_one()
    total_points = int(total_points)

    status = db.execute(select(LeafpassStatus).where(LeafpassStatus.telegram_id == telegram_id)).scalar_one_or_none()

    total_days = db.execute(
        select(func.count(func.distinct(QuestSubmission.submit_date))).where(QuestSubmission.telegram_id == telegram_id)
    ).scalar_one()
    total_days = int(total_days or 0)

    return {
        "telegram_id": telegram_id,
        "total_points": total_points,
        "streak": calc_streak(db, telegram_id),
        "leafpass_level": status.level if status else "seed",
        "participation_days": total_days,
    }
