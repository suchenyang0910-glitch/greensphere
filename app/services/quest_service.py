from sqlalchemy.orm import Session
from app.models.quest import Quest
from app.models.quest_submission import QuestSubmission
from app.services.leafpass_service import update_leafpass
from app.services.point_service import add_points


def submit_quest(db: Session, telegram_id: int, quest_code: str):
    quest = db.query(Quest).filter_by(code=quest_code, active=True).first()
    if not quest:
        return {"success": False, "message": "Quest not found"}

    submission = QuestSubmission(
        telegram_id=telegram_id,
        quest_code=quest_code
    )

    try:
        # 1️⃣ 记录任务完成
        db.add(submission)
        db.commit()

        # 2️⃣ 统一走积分 Service（重要）
        add_points(
            db=db,
            telegram_id=telegram_id,
            points=quest.points,
            source=quest_code
        )

        # 3️⃣ 🔥 更新 LeafPass（就在这里）
        leafpass = update_leafpass(
            db=db,
            telegram_id=telegram_id,
            points_delta=quest.points
        )

        return {
            "success": True,
            "points": quest.points,
            "leafpass": leafpass
        }

    except Exception:
        db.rollback()
        return {
            "success": False,
            "message": "Already completed today"
        }