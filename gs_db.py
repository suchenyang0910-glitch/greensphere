# gs_db.py
import sqlite3
from datetime import datetime
from typing import Iterator

DB_PATH = "greensphere_behavior.db"


def get_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_gs_db() -> None:
    """初始化打卡用的 SQLite 数据库（行为层专用）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 用户表
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            created_at TEXT
        );
        """
    )

    # 任务表
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            points INTEGER
        );
        """
    )

    # 用户任务日志表
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id INTEGER,
            date TEXT,
            created_at TEXT
        );
        """
    )

    # 默认一个示例用户（如果你需要，可以不插）
    c.execute("SELECT id FROM users WHERE id = 1;")
    if c.fetchone() is None:
        c.execute(
            "INSERT INTO users (id, name, created_at) VALUES (1, ?, ?);",
            ("Demo User", datetime.utcnow().isoformat()),
        )

    # 示例任务
    c.execute("SELECT COUNT(*) AS cnt FROM tasks;")
    row = c.fetchone()
    if row[0] == 0:
        sample_tasks = [
            ("今天步行 5000 步以上", 10),
            ("今天不用一次性塑料袋", 10),
            ("关灯节能 30 分钟以上", 10),
        ]
        c.executemany(
            "INSERT INTO tasks (title, points) VALUES (?, ?);",
            sample_tasks,
        )

    conn.commit()
    conn.close()
