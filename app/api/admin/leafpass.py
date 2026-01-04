from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/admin/leafpass")

@router.get("/stats")
def leafpass_stats(db: Session = Depends(get_db)):
    total = db.query(User).count()
    by_level = (
        db.query(User.leafpass_level, func.count())
        .group_by(User.leafpass_level)
        .all()
    )

    return {
        "total_users": total,
        "by_level": {lv: c for lv, c in by_level}
    }

@router.post("/add-points")
def admin_add_points(
    telegram_id: int,
    points: int,
    db: Session = Depends(get_db)
):
    add_points(db, telegram_id, points, source="admin")
    update_leafpass(db, telegram_id, points)

    return {"success": True}