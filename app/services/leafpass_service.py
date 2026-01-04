from app.models.leafpass import LeafPassStatus

LEVEL_RULES = [
    ("L4", "Forest", 1500),
    ("L3", "Grove", 500),
    ("L2", "Sprout", 100),
    ("L1", "Seed", 0),
]

LEAFPASS_LEVELS = [
    {"level": "L1", "min": 0, "name": "Seed"},
    {"level": "L2", "min": 100, "name": "Sprout"},
    {"level": "L3", "min": 500, "name": "Green"},
    {"level": "L4", "min": 1500, "name": "Planet"},
]

def calculate_level(total_points: int):
    for code, name, threshold in LEVEL_RULES:
        if total_points >= threshold:
            return code, name
    return "L1", "Seed"


def update_leafpass(db, telegram_id: int, points_delta: int):
    record = db.query(LeafPassStatus).filter_by(
        telegram_id=telegram_id
    ).first()

    if record:
        total = record.total_points + points_delta
    else:
        total = points_delta

    level_code, level_name = calculate_level(total)

    if record:
        record.total_points = total
        record.level = level_code
    else:
        record = LeafPassStatus(
            telegram_id=telegram_id,
            total_points=total,
            level=level_code
        )
        db.add(record)
    if new_level != old_level:
        db.add(LeafpassNFT(
            telegram_id=telegram_id,
            level=new_level,
            minted=False
        ))
    db.commit()
    return {
        "level": level_code,
        "total_points": total
    }
