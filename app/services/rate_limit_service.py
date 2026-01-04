from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.rate_limit import WaitlistRateLimit

def is_rate_limited(
    db: Session,
    ip: str,
    action: str,
    limit: int = 3,
    minutes: int = 5
) -> bool:
    since = datetime.utcnow() - timedelta(minutes=minutes)
    count = (
        db.query(WaitlistRateLimit)
        .filter(
            WaitlistRateLimit.ip_address == ip,
            WaitlistRateLimit.action == action,
            WaitlistRateLimit.created_at >= since
        )
        .count()
    )

    return count >= limit
def record_action(db: Session, ip: str, action: str):
    record = WaitlistRateLimit(
    ip_address=ip,
    action=action
    )
    db.add(record)
    db.commit()