from fastapi import APIRouter, Request
from app.services.telegram_bot_service import send_welcome
from app.database import get_db
from sqlalchemy.orm import Session
from app.models.telegram_user import TelegramUser

router = APIRouter()


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, db: Session = next(get_db())):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    msg = data["message"]
    text = msg.get("text", "")
    user = msg["from"]

    telegram_id = user["id"]

    # 绑定用户
    existing = db.query(TelegramUser).filter_by(telegram_id=telegram_id).first()
    if not existing:
        new_user = TelegramUser(
            telegram_id=telegram_id,
            username=user.get("username"),
            first_name=user.get("first_name"),
            last_name=user.get("last_name")
        )
        db.add(new_user)
        db.commit()

    if text == "/start":
        send_welcome({"telegram_id": telegram_id})

    return {"ok": True}

from app.services.leafpass_service import LEAFPASS_LEVELS
from app.models.user import User
def get_leafpass_status(db, telegram_id: int):
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        return None

    current = None
    next_level = None

    for i, lv in enumerate(LEAFPASS_LEVELS):
        if user.total_points >= lv["min"]:
            current = lv
            next_level = LEAFPASS_LEVELS[i + 1] if i + 1 < len(LEAFPASS_LEVELS) else None

    return {
        "level": current["level"],
        "name": current["name"],
        "points": user.total_points,
        "next": next_level
    }