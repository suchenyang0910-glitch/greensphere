# models.py
import sqlite3
from datetime import date, timedelta
from datetime import datetime
from pydantic import BaseModel
from app.db import get_db 


class CompleteTaskRequest(BaseModel):
    user_id: int | None = None
    task_id: int


class UserInitRequest(BaseModel):
    telegram_id: int | None = None
    username: str | None = None


def get_today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def calculate_stats(conn: sqlite3.Connection, user_id: int) -> dict:
    """计算总积分、连续天数、今日完成任务数、总任务数"""

    c = conn.cursor()

    # 总积分
    c.execute(
        """
        SELECT SUM(t.points) AS total_points
        FROM user_task_logs l
        JOIN tasks t ON l.task_id = t.id
        WHERE l.user_id = ?;
        """,
        (user_id,),
    )
    row = c.fetchone()
    total_points = row["total_points"] if row["total_points"] is not None else 0

    # 今日完成任务数
    today_str = get_today_str()
    c.execute(
        """
        SELECT COUNT(DISTINCT task_id) AS cnt
        FROM user_task_logs
        WHERE user_id = ? AND date = ?;
        """,
        (user_id, today_str),
    )
    row = c.fetchone()
    today_completed = row["cnt"] if row["cnt"] is not None else 0

    # 总任务数
    c.execute("SELECT COUNT(*) AS cnt FROM tasks;")
    row = c.fetchone()
    total_tasks = row["cnt"] if row["cnt"] is not None else 0

    c.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM user_task_logs
        WHERE user_id = ?;
        """,
        (user_id,),
    )
    row = c.fetchone()
    total_completions = row["cnt"] if row["cnt"] is not None else 0

    c.execute(
        """
        SELECT COUNT(DISTINCT date) AS cnt
        FROM user_task_logs
        WHERE user_id = ?;
        """,
        (user_id,),
    )
    row = c.fetchone()
    participation_days = row["cnt"] if row["cnt"] is not None else 0

    # 连续天数 streak
    streak = 0
    today = date.today()

    while True:
        day_str = (today - timedelta(days=streak)).strftime("%Y-%m-%d")
        c.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM user_task_logs
            WHERE user_id = ? AND date = ?;
            """,
            (user_id, day_str),
        )
            # row 是 sqlite3.Row，既支持下标也支持键访问
        row = c.fetchone()
        if row["cnt"] and row["cnt"] > 0:
            streak += 1
        else:
            break

    return {
        "total_points": total_points,
        "streak": streak,
        "today_completed": today_completed,
        "total_tasks": total_tasks,
        "total_completions": total_completions,
        "participation_days": participation_days,
    }


def _load_badges(conn: sqlite3.Connection) -> list[dict]:
    c = conn.cursor()
    c.execute("SELECT code, title, description, rule_type, threshold FROM badges ORDER BY id ASC;")
    return [dict(r) for r in c.fetchall()]


def _load_user_badge_codes(conn: sqlite3.Connection, user_id: int) -> set[str]:
    c = conn.cursor()
    c.execute("SELECT badge_code FROM user_badges WHERE user_id = ?;", (user_id,))
    return {r["badge_code"] for r in c.fetchall()}


def unlock_eligible_badges(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    stats = calculate_stats(conn, user_id)
    badges = _load_badges(conn)
    owned = _load_user_badge_codes(conn, user_id)

    eligible: list[dict] = []
    for b in badges:
        if b["code"] in owned:
            continue
        rule = b["rule_type"]
        threshold = int(b["threshold"])
        ok = False
        if rule == "streak":
            ok = int(stats["streak"]) >= threshold
        elif rule == "total_points":
            ok = int(stats["total_points"]) >= threshold
        elif rule == "total_completions":
            ok = int(stats["total_completions"]) >= threshold
        elif rule == "participation_days":
            ok = int(stats["participation_days"]) >= threshold
        if ok:
            eligible.append(b)

    if not eligible:
        return []

    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    for b in eligible:
        c.execute(
            """
            INSERT OR IGNORE INTO user_badges (user_id, badge_code, unlocked_at)
            VALUES (?, ?, ?);
            """,
            (user_id, b["code"], now),
        )
    conn.commit()
    return eligible


def list_user_badges(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    c = conn.cursor()
    c.execute(
        """
        SELECT b.code, b.title, b.description, b.rule_type, b.threshold, ub.unlocked_at
        FROM user_badges ub
        JOIN badges b ON b.code = ub.badge_code
        WHERE ub.user_id = ?
        ORDER BY ub.unlocked_at DESC;
        """,
        (user_id,),
    )
    return [dict(r) for r in c.fetchall()]


def list_recent_task_logs(conn: sqlite3.Connection, user_id: int, limit: int = 10) -> list[dict]:
    c = conn.cursor()
    c.execute(
        """
        SELECT l.date, l.created_at, t.title, t.points, t.i18n_json
        FROM user_task_logs l
        JOIN tasks t ON t.id = l.task_id
        WHERE l.user_id = ?
        ORDER BY l.date DESC, l.created_at DESC
        LIMIT ?;
        """,
        (int(user_id), int(limit)),
    )
    return [dict(r) for r in c.fetchall()]


def list_next_rewards(conn: sqlite3.Connection, user_id: int, limit: int = 3) -> list[dict]:
    stats = calculate_stats(conn, user_id)
    badges = _load_badges(conn)
    owned = _load_user_badge_codes(conn, user_id)

    def current_value(rule_type: str) -> int:
        if rule_type == "streak":
            return int(stats.get("streak") or 0)
        if rule_type == "total_points":
            return int(stats.get("total_points") or 0)
        if rule_type == "total_completions":
            return int(stats.get("total_completions") or 0)
        if rule_type == "participation_days":
            return int(stats.get("participation_days") or 0)
        return 0

    candidates: list[dict] = []
    for b in badges:
        if b["code"] in owned:
            continue
        rule = b["rule_type"]
        threshold = int(b["threshold"])
        cur = current_value(rule)
        remaining = max(0, threshold - cur)
        if remaining <= 0:
            continue
        candidates.append(
            {
                "code": b["code"],
                "title": b["title"],
                "description": b.get("description"),
                "rule_type": rule,
                "threshold": threshold,
                "current": cur,
                "remaining": remaining,
            }
        )

    candidates.sort(key=lambda x: (x["remaining"], x["threshold"], x["code"]))
    return candidates[: int(limit)]


def list_challenges(conn: sqlite3.Connection) -> list[dict]:
    c = conn.cursor()
    c.execute(
        """
        SELECT id, code, title, description, start_date, end_date, status, created_at
        FROM challenges
        ORDER BY id DESC;
        """
    )
    return [dict(r) for r in c.fetchall()]


def list_user_challenge_ids(conn: sqlite3.Connection, user_id: int) -> set[int]:
    c = conn.cursor()
    c.execute("SELECT challenge_id FROM challenge_participants WHERE user_id = ?;", (int(user_id),))
    return {int(r["challenge_id"]) for r in c.fetchall()}


def join_challenge(conn: sqlite3.Connection, challenge_id: int, user_id: int) -> None:
    c = conn.cursor()
    c.execute(
        """
        INSERT OR IGNORE INTO challenge_participants (challenge_id, user_id, joined_at)
        VALUES (?, ?, ?);
        """,
        (int(challenge_id), int(user_id), datetime.utcnow().isoformat()),
    )
    conn.commit()


def challenge_leaderboard(conn: sqlite3.Connection, challenge_id: int, limit: int = 50) -> list[dict]:
    c = conn.cursor()
    c.execute("SELECT start_date, end_date FROM challenges WHERE id = ?;", (int(challenge_id),))
    ch = c.fetchone()
    if not ch:
        return []
    start_date = ch["start_date"]
    end_date = ch["end_date"]
    c.execute(
        """
        WITH t AS (
            SELECT task_id FROM challenge_tasks WHERE challenge_id = ?
        ),
        s AS (
            SELECT l.user_id AS user_id, COUNT(*) AS actions, COALESCE(SUM(tt.points), 0) AS points
            FROM user_task_logs l
            JOIN t ON t.task_id = l.task_id
            JOIN tasks tt ON tt.id = l.task_id
            WHERE l.date >= ? AND l.date <= ?
            GROUP BY l.user_id
        )
        SELECT s.user_id, u.name AS name, s.actions, s.points
        FROM s
        LEFT JOIN users u ON u.id = s.user_id
        ORDER BY s.points DESC, s.actions DESC
        LIMIT ?;
        """,
        (int(challenge_id), start_date, end_date, int(limit)),
    )
    return [dict(r) for r in c.fetchall()]


def add_feed_event(conn: sqlite3.Connection, user_id: int, type: str, message: str, meta_json: str | None = None) -> int:
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO activity_feed (user_id, type, message, meta_json, created_at)
        VALUES (?, ?, ?, ?, ?);
        """,
        (int(user_id), str(type), str(message), meta_json, datetime.utcnow().isoformat()),
    )
    conn.commit()
    return int(c.lastrowid)


def list_feed(conn: sqlite3.Connection, limit: int = 30) -> list[dict]:
    c = conn.cursor()
    c.execute(
        """
        SELECT f.id, f.user_id, u.name AS name, f.type, f.message, f.meta_json, f.created_at
        FROM activity_feed f
        LEFT JOIN users u ON u.id = f.user_id
        ORDER BY f.id DESC
        LIMIT ?;
        """,
        (int(limit),),
    )
    rows = [dict(r) for r in c.fetchall()]
    if not rows:
        return []
    feed_ids = [int(r["id"]) for r in rows]
    placeholders = ",".join(["?"] * len(feed_ids))
    c.execute(
        f"SELECT feed_id, COUNT(*) AS cnt FROM feed_likes WHERE feed_id IN ({placeholders}) GROUP BY feed_id;",
        feed_ids,
    )
    like_map = {int(r["feed_id"]): int(r["cnt"]) for r in c.fetchall()}
    c.execute(
        f"SELECT feed_id, COUNT(*) AS cnt FROM feed_comments WHERE feed_id IN ({placeholders}) GROUP BY feed_id;",
        feed_ids,
    )
    comment_map = {int(r["feed_id"]): int(r["cnt"]) for r in c.fetchall()}
    for r in rows:
        fid = int(r["id"])
        r["like_count"] = like_map.get(fid, 0)
        r["comment_count"] = comment_map.get(fid, 0)
    return rows


def like_feed(conn: sqlite3.Connection, feed_id: int, user_id: int) -> None:
    c = conn.cursor()
    c.execute(
        """
        INSERT OR IGNORE INTO feed_likes (feed_id, user_id, created_at)
        VALUES (?, ?, ?);
        """,
        (int(feed_id), int(user_id), datetime.utcnow().isoformat()),
    )
    conn.commit()


def comment_feed(conn: sqlite3.Connection, feed_id: int, user_id: int, text: str) -> None:
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO feed_comments (feed_id, user_id, text, created_at)
        VALUES (?, ?, ?, ?);
        """,
        (int(feed_id), int(user_id), str(text)[:500], datetime.utcnow().isoformat()),
    )
    conn.commit()


def list_rewards(conn: sqlite3.Connection) -> list[dict]:
    c = conn.cursor()
    c.execute(
        """
        SELECT id, code, title, description, cost_points, status, created_at
        FROM rewards
        WHERE status = 'active'
        ORDER BY cost_points ASC, id ASC;
        """
    )
    return [dict(r) for r in c.fetchall()]


def create_redemption(conn: sqlite3.Connection, reward_id: int, user_id: int, note: str | None = None) -> int:
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO reward_redemptions (reward_id, user_id, status, note, created_at)
        VALUES (?, ?, ?, ?, ?);
        """,
        (int(reward_id), int(user_id), "pending", (note or "")[:255], datetime.utcnow().isoformat()),
    )
    conn.commit()
    return int(c.lastrowid)


def log_system_event(
    conn: sqlite3.Connection,
    *,
    level: str,
    event: str,
    message: str | None = None,
    meta_json: str | None = None,
) -> None:
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO system_logs (level, event, message, meta_json, created_at)
        VALUES (?, ?, ?, ?, ?);
        """,
        (level, event, message, meta_json, datetime.utcnow().isoformat()),
    )
    conn.commit()


def list_system_logs(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    c = conn.cursor()
    c.execute(
        """
        SELECT id, level, event, message, meta_json, created_at
        FROM system_logs
        ORDER BY id DESC
        LIMIT ?;
        """,
        (int(limit),),
    )
    return [dict(r) for r in c.fetchall()]
