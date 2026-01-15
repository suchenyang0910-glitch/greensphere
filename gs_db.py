# gs_db.py
import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import Iterator
import json

DB_PATH_DEFAULT = "data/greensphere_behavior.db"


def _behavior_db_path() -> str:
    raw = (os.getenv("GS_BEHAVIOR_DB_PATH") or "").strip()
    path = raw or DB_PATH_DEFAULT
    if path.endswith("/") or path.endswith("\\") or os.path.isdir(path):
        return os.path.join(path, "greensphere_behavior.db")
    return path


def get_db() -> Iterator[sqlite3.Connection]:
    db_path = _behavior_db_path()
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    try:
        yield conn
    finally:
        conn.close()


def init_gs_db() -> None:
    """初始化打卡用的 SQLite 数据库（行为层专用）"""
    db_path = _behavior_db_path()
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
    c = conn.cursor()
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass

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
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN i18n_json TEXT;")
    except sqlite3.OperationalError:
        pass

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
    c.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_task_unique
        ON user_task_logs(user_id, task_id, date);
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            rule_type TEXT NOT NULL,
            threshold INTEGER NOT NULL,
            created_at TEXT
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            badge_code TEXT NOT NULL,
            unlocked_at TEXT NOT NULL,
            UNIQUE(user_id, badge_code)
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
            event TEXT NOT NULL,
            message TEXT,
            meta_json TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS co2_daily (
            date TEXT PRIMARY KEY,
            value REAL NOT NULL,
            source TEXT,
            fetched_at_utc TEXT NOT NULL
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS challenge_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            UNIQUE(challenge_id, task_id)
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS challenge_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            UNIQUE(challenge_id, user_id)
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            meta_json TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS feed_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(feed_id, user_id)
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS feed_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            cost_points INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reward_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_public_profiles (
            user_id INTEGER PRIMARY KEY,
            public_token TEXT NOT NULL UNIQUE,
            is_public INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            source TEXT,
            published_at TEXT,
            fetched_at TEXT NOT NULL
        );
        """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_items_fetched_at
        ON news_items(fetched_at);
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            key TEXT NOT NULL,
            window TEXT NOT NULL,
            count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(ip, key, window)
        );
        """
    )

    try:
        c.execute("DELETE FROM rate_limits WHERE created_at < datetime('now', '-2 days');")
    except Exception:
        pass
    try:
        c.execute("DELETE FROM news_items WHERE fetched_at < datetime('now', '-30 days');")
    except Exception:
        pass

    # 示例任务
    c.execute("SELECT COUNT(*) AS cnt FROM tasks;")
    row = c.fetchone()
    if row[0] == 0:
        sample_tasks = [
            (
                "今天步行 5000 步以上",
                10,
                json.dumps(
                    {
                        "zh": "今天步行 5,000 步以上",
                        "en": "Walk 5,000+ steps today",
                        "th": "เดิน 5,000 ก้าวขึ้นไปวันนี้",
                        "vi": "Đi bộ 5.000+ bước hôm nay",
                        "km": "ដើរ 5,000 ជំហានឡើងទៅថ្ងៃនេះ",
                    },
                    ensure_ascii=False,
                ),
            ),
            (
                "今天不用一次性塑料袋",
                10,
                json.dumps(
                    {
                        "zh": "今天不用一次性塑料袋",
                        "en": "Skip single-use plastic bags today",
                        "th": "งดใช้ถุงพลาสติกใช้ครั้งเดียววันนี้",
                        "vi": "Không dùng túi nhựa dùng một lần hôm nay",
                        "km": "មិនប្រើថង់ប្លាស្ទិកប្រើតែម្តងថ្ងៃនេះ",
                    },
                    ensure_ascii=False,
                ),
            ),
            (
                "关灯节能 30 分钟以上",
                10,
                json.dumps(
                    {
                        "zh": "关灯节能 30 分钟以上",
                        "en": "Save energy: lights off for 30+ minutes",
                        "th": "ประหยัดพลังงาน: ปิดไฟ 30 นาทีขึ้นไป",
                        "vi": "Tiết kiệm điện: tắt đèn 30+ phút",
                        "km": "សន្សំថាមពល៖ បិទភ្លើង 30 នាទីឡើងទៅ",
                    },
                    ensure_ascii=False,
                ),
            ),
        ]
        c.executemany(
            "INSERT INTO tasks (title, points, i18n_json) VALUES (?, ?, ?);",
            sample_tasks,
        )
    else:
        task_i18n_by_title = {
            "今天步行 5000 步以上": json.dumps(
                {
                    "zh": "今天步行 5,000 步以上",
                    "en": "Walk 5,000+ steps today",
                    "th": "เดิน 5,000 ก้าวขึ้นไปวันนี้",
                    "vi": "Đi bộ 5.000+ bước hôm nay",
                    "km": "ដើរ 5,000 ជំហានឡើងទៅថ្ងៃនេះ",
                },
                ensure_ascii=False,
            ),
            "今天不用一次性塑料袋": json.dumps(
                {
                    "zh": "今天不用一次性塑料袋",
                    "en": "Skip single-use plastic bags today",
                    "th": "งดใช้ถุงพลาสติกใช้ครั้งเดียววันนี้",
                    "vi": "Không dùng túi nhựa dùng một lần hôm nay",
                    "km": "មិនប្រើថង់ប្លាស្ទិកប្រើតែម្តងថ្ងៃនេះ",
                },
                ensure_ascii=False,
            ),
            "关灯节能 30 分钟以上": json.dumps(
                {
                    "zh": "关灯节能 30 分钟以上",
                    "en": "Save energy: lights off for 30+ minutes",
                    "th": "ประหยัดพลังงาน: ปิดไฟ 30 นาทีขึ้นไป",
                    "vi": "Tiết kiệm điện: tắt đèn 30+ phút",
                    "km": "សន្សំថាមពល៖ បិទភ្លើង 30 នាទីឡើងទៅ",
                },
                ensure_ascii=False,
            ),
        }
        for title, i18n_json in task_i18n_by_title.items():
            c.execute(
                """
                UPDATE tasks
                SET i18n_json = ?
                WHERE title = ? AND (i18n_json IS NULL OR i18n_json = '');
                """,
                (i18n_json, title),
            )

    c.execute("SELECT COUNT(*) AS cnt FROM badges;")
    row = c.fetchone()
    if row[0] == 0:
        now = datetime.utcnow().isoformat()
        sample_badges = [
            ("new_leaf_3", "New Leaf", "连续 3 天参与", "streak", 3, now),
            ("sprout_7", "Sprout", "连续 7 天参与", "streak", 7, now),
            ("pioneer_14", "Pioneer", "连续 14 天参与", "streak", 14, now),
            ("steady_30", "Steady Green", "连续 30 天参与", "streak", 30, now),
            ("points_100", "Green Starter", "累计获得 100 G-Points", "total_points", 100, now),
            ("points_500", "Green Builder", "累计获得 500 G-Points", "total_points", 500, now),
            ("actions_30", "Action Maker", "累计完成 30 次任务", "total_completions", 30, now),
            ("actions_100", "Impact Driver", "累计完成 100 次任务", "total_completions", 100, now),
        ]
        c.executemany(
            """
            INSERT INTO badges (code, title, description, rule_type, threshold, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            sample_badges,
        )

    c.execute("SELECT COUNT(*) AS cnt FROM rewards;")
    row = c.fetchone()
    if row[0] == 0:
        now = datetime.utcnow().isoformat()
        sample_rewards = [
            ("reward_sticker_pack", "Sticker Pack", "一组 GreenSphere 贴纸", 200, "active", now),
            ("reward_badge_gold", "Gold Leaf Badge", "限定徽章（审核后发放）", 500, "active", now),
            ("reward_coupon_partner", "Partner Coupon", "合作商家优惠券（审核后发放）", 800, "active", now),
        ]
        c.executemany(
            """
            INSERT INTO rewards (code, title, description, cost_points, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            sample_rewards,
        )

    c.execute("SELECT COUNT(*) AS cnt FROM challenges;")
    row = c.fetchone()
    if row[0] == 0:
        now = datetime.utcnow().isoformat()
        today = date.today()
        start = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=5)).strftime("%Y-%m-%d")
        c.execute(
            """
            INSERT INTO challenges (code, title, description, start_date, end_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "pioneer_7d",
                "Pioneer 7-Day Challenge",
                "连续 7 天完成每日任务，解锁里程碑徽章。",
                start,
                end,
                "active",
                now,
            ),
        )
        challenge_id = c.lastrowid
        c.execute("SELECT id FROM tasks ORDER BY id ASC LIMIT 3;")
        for r in c.fetchall():
            c.execute(
                "INSERT OR IGNORE INTO challenge_tasks (challenge_id, task_id) VALUES (?, ?);",
                (challenge_id, int(r[0])),
            )

    conn.commit()
    conn.close()
