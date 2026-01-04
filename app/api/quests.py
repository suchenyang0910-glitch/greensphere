from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import LeafpassStatus

from app.db import get_db
from app.deps import get_telegram_id
from app.models import Quest, QuestSubmission, PointTransaction, LeafpassStatus, TelegramUser

router = APIRouter(prefix="/api", tags=["quests"])

# 你可以按需要改等级阈值
LEVELS = [
    ("seed", 0),
    ("sprout", 50),
    ("leaf", 150),
    ("tree", 300),
]

def calc_level(total_points: int) -> str:
    lvl = LEVELS[0][0]
    for name, threshold in LEVELS:
        if total_points >= threshold:
            lvl = name
    return lvl

def calc_streak(db: Session, telegram_id: int) -> int:
    # 取所有参与日期（去重）
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

@router.get("/quests")
def list_quests(db: Session = Depends(get_db)):
    # active=1 且未过期（expires_at is null or > now）
    q = select(Quest).where(
        Quest.active == True,
        (Quest.expires_at.is_(None)) | (Quest.expires_at > func.now())
    ).order_by(Quest.id.asc())
    quests = db.execute(q).scalars().all()
    return [
        {
            "id": x.id,
            "code": x.code,
            "title": x.title,
            "description": x.description,
            "points": x.points,
        }
        for x in quests
    ]

@router.post("/quests/{quest_id}/complete")
def complete_quest(
    quest_id: int,
    telegram_id: int = Depends(get_telegram_id),
    db: Session = Depends(get_db),
):
    quest = db.execute(select(Quest).where(Quest.id == quest_id)).scalar_one_or_none()
    if not quest or not quest.active:
        raise HTTPException(status_code=404, detail="Quest not found")

    # 确保用户存在（A 阶段：只靠 telegram_id）
    user = db.execute(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)).scalar_one_or_none()
    if not user:
        user = TelegramUser(telegram_id=telegram_id)
        db.add(user)
        db.flush()

    # 写 submission（依赖 uniq_user_quest_day 防重复）
    from datetime import datetime
    sub = QuestSubmission(
        telegram_id=telegram_id,
        quest_code=quest.code,
        submitted_at=datetime.utcnow(),  # 或 datetime.now()
    )

    db.add(sub)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        total_points = db.execute(
            select(func.coalesce(func.sum(PointTransaction.points), 0)).where(PointTransaction.telegram_id == telegram_id)
        ).scalar_one()
        total_points = int(total_points)

        status = db.execute(
            select(LeafpassStatus).where(LeafpassStatus.telegram_id == telegram_id)
        ).scalar_one_or_none()

        return {
            "ok": True,
            "already_completed": True,
            "total_points": total_points,
            "streak": calc_streak(db, telegram_id),
            "leafpass_level": status.level if status else "seed",
        }

    # 写积分流水
    db.add(PointTransaction(
        telegram_id=telegram_id,
        points=int(quest.points or 0),
        source=f"quest:{quest.code}"
    ))
    db.flush()
    # 计算总积分
    total_points = db.execute(
        select(func.coalesce(func.sum(PointTransaction.points), 0)).where(PointTransaction.telegram_id == telegram_id)
    ).scalar_one()
    total_points = int(total_points)

    # upsert leafpass_status（MyISAM 没事务，这里用“先查后写”）
    level = calc_level(total_points)
    status = db.execute(select(LeafpassStatus).where(LeafpassStatus.telegram_id == telegram_id)).scalar_one_or_none()
    if not status:
        status = LeafpassStatus(telegram_id=telegram_id, level=level, total_points=total_points)
        db.add(status)
    else:
        status.level = level
        status.total_points = total_points

    db.commit()

    return {
        "ok": True,
        "already_completed": False,
        "quest": {"id": quest.id, "code": quest.code, "points": int(quest.points or 0)},
        "total_points": total_points,
        "streak": calc_streak(db, telegram_id),
        "leafpass_level": level,
    }
