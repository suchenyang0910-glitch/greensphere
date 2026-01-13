from __future__ import annotations

import time
import sqlite3


def _window_id(window_seconds: int) -> str:
    return str(int(time.time() // window_seconds))


def increment_and_get_count(
    conn,
    *,
    ip: str,
    key: str,
    window_seconds: int,
) -> int:
    ip = (ip or "").strip() or "unknown"
    key = (key or "").strip() or "unknown"
    win = _window_id(int(window_seconds))
    for attempt in range(5):
        try:
            c = conn.cursor()
            c.execute(
                """
                INSERT OR IGNORE INTO rate_limits (ip, key, window, count, created_at)
                VALUES (?, ?, ?, 0, datetime('now'));
                """,
                (ip, key, win),
            )
            c.execute(
                """
                UPDATE rate_limits
                SET count = count + 1
                WHERE ip = ? AND key = ? AND window = ?;
                """,
                (ip, key, win),
            )
            conn.commit()
            c.execute(
                """
                SELECT count
                FROM rate_limits
                WHERE ip = ? AND key = ? AND window = ?;
                """,
                (ip, key, win),
            )
            row = c.fetchone()
            return int(row["count"] if row and row["count"] is not None else 0)
        except sqlite3.OperationalError as e:
            if "locked" not in str(e).lower() or attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))

