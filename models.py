# models.py
import sqlite3
from datetime import date, timedelta
from pydantic import BaseModel
from app.db import get_db 


class CompleteTaskRequest(BaseModel):
    user_id: int
    task_id: int


class UserInitRequest(BaseModel):
    telegram_id: int
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
    }
