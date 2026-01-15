import os
import threading
import time
from datetime import datetime, timedelta, timezone

from gs_db import get_db
from models import log_system_event
from app.services.monitor_service import notify_monitor


_started = False
_lock = threading.Lock()


def _tz_offset_hours() -> int:
    raw = (os.getenv("GS_DAILY_REPORT_TZ_OFFSET_HOURS") or "7").strip()
    try:
        return int(raw)
    except Exception:
        return 7


def _next_run_local_midnight_utc(offset_hours: int) -> datetime:
    now_utc = datetime.now(timezone.utc)
    local = now_utc + timedelta(hours=offset_hours)
    next_local_midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if next_local_midnight <= local:
        next_local_midnight = next_local_midnight + timedelta(days=1)
    return next_local_midnight - timedelta(hours=offset_hours)


def _report_date_str(offset_hours: int) -> str:
    local = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    d = local.date() - timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _build_daily_message(date_str: str, new_users: int, active_users: int, completed: int, total_users: int) -> str:
    return (
        f"📊 GreenSphere 今日数据（{date_str}）\n"
        f" - 新用户：{new_users}\n"
        f" - 活跃用户：{active_users}\n"
        f" - 完成任务次数：{completed}\n"
        f" - 总用户数：{total_users}"
    )


def _compute_daily_stats(date_str: str, offset_hours: int) -> dict:
    gen = get_db()
    db = next(gen)
    try:
        c = db.cursor()
        c.execute("SELECT COUNT(*) AS cnt FROM users;")
        total_users = int(c.fetchone()["cnt"] or 0)

        c.execute("SELECT COUNT(*) AS cnt FROM users WHERE date(created_at, ?) = ?;", (f"+{offset_hours} hours", date_str))
        new_users = int(c.fetchone()["cnt"] or 0)

        c.execute("SELECT COUNT(DISTINCT user_id) AS cnt FROM user_task_logs WHERE date = ?;", (date_str,))
        active_users = int(c.fetchone()["cnt"] or 0)

        c.execute("SELECT COUNT(*) AS cnt FROM user_task_logs WHERE date = ?;", (date_str,))
        completed = int(c.fetchone()["cnt"] or 0)

        return {
            "total_users": total_users,
            "new_users": new_users,
            "active_users": active_users,
            "completed": completed,
        }
    finally:
        gen.close()


def _worker() -> None:
    offset = _tz_offset_hours()
    run_on_start = (os.getenv("GS_DAILY_REPORT_ON_START") or "0").strip().lower() in {"1", "true", "yes", "on"}

    if run_on_start:
        try:
            date_str = _report_date_str(offset)
            stats = _compute_daily_stats(date_str, offset)
            msg = _build_daily_message(date_str, stats["new_users"], stats["active_users"], stats["completed"], stats["total_users"])
            notify_monitor(msg)
        except Exception as e:
            try:
                gen = get_db()
                db = next(gen)
                log_system_event(db, level="error", event="daily_report_error", message=str(e))
                gen.close()
            except Exception:
                pass

    while True:
        try:
            target = _next_run_local_midnight_utc(offset)
            sleep_s = max(1, int((target - datetime.now(timezone.utc)).total_seconds()))
            time.sleep(sleep_s)

            date_str = _report_date_str(offset)
            stats = _compute_daily_stats(date_str, offset)
            msg = _build_daily_message(date_str, stats["new_users"], stats["active_users"], stats["completed"], stats["total_users"])
            notify_monitor(msg)

            gen = get_db()
            db = next(gen)
            log_system_event(db, level="info", event="daily_report", message=f"date={date_str} new={stats['new_users']} active={stats['active_users']} completed={stats['completed']} total={stats['total_users']}")
            gen.close()
        except Exception as e:
            try:
                gen = get_db()
                db = next(gen)
                log_system_event(db, level="error", event="daily_report_error", message=str(e))
                gen.close()
            except Exception:
                pass
            time.sleep(60)


def start_daily_reporter() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True
    t = threading.Thread(target=_worker, name="daily_reporter", daemon=True)
    t.start()

