import os
import threading
import time
from datetime import datetime, timedelta, timezone

from app.services.co2_service import update_co2_db
from gs_db import get_db
from models import log_system_event


_started = False
_lock = threading.Lock()


def _tz_offset_hours() -> int:
    raw = (os.getenv("GS_CO2_FETCH_TZ_OFFSET_HOURS") or "7").strip()
    try:
        return int(raw)
    except Exception:
        return 7


def _local_hour() -> int:
    raw = (os.getenv("GS_CO2_FETCH_LOCAL_HOUR") or "1").strip()
    try:
        v = int(raw)
        if 0 <= v <= 23:
            return v
        return 1
    except Exception:
        return 1


def _local_minute() -> int:
    raw = (os.getenv("GS_CO2_FETCH_LOCAL_MINUTE") or "0").strip()
    try:
        v = int(raw)
        if 0 <= v <= 59:
            return v
        return 0
    except Exception:
        return 0


def _next_run_local_time_utc(offset_hours: int, hour: int, minute: int) -> datetime:
    now_utc = datetime.now(timezone.utc)
    local = now_utc + timedelta(hours=offset_hours)
    candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local:
        candidate = candidate + timedelta(days=1)
    return candidate - timedelta(hours=offset_hours)


def _worker() -> None:
    offset = _tz_offset_hours()
    hour = _local_hour()
    minute = _local_minute()
    run_on_start = (os.getenv("GS_CO2_FETCH_ON_START") or "0").strip().lower() in {"1", "true", "yes", "on"}

    if run_on_start:
        try:
            pts = update_co2_db(limit=14)
            gen = get_db()
            db = next(gen)
            log_system_event(db, level="info", event="co2_fetch_on_start", message=f"points={len(pts)}")
            gen.close()
        except Exception as e:
            try:
                gen = get_db()
                db = next(gen)
                log_system_event(db, level="error", event="co2_fetch_error", message=str(e))
                gen.close()
            except Exception:
                pass

    while True:
        try:
            target = _next_run_local_time_utc(offset, hour, minute)
            sleep_s = max(1, int((target - datetime.now(timezone.utc)).total_seconds()))
            time.sleep(sleep_s)
            pts = update_co2_db(limit=14)
            gen = get_db()
            db = next(gen)
            log_system_event(db, level="info", event="co2_fetch_scheduled", message=f"points={len(pts)} local={offset:+d}h {hour:02d}:{minute:02d}")
            gen.close()
        except Exception as e:
            try:
                gen = get_db()
                db = next(gen)
                log_system_event(db, level="error", event="co2_fetch_error", message=str(e))
                gen.close()
            except Exception:
                pass
            time.sleep(60)


def start_co2_fetcher() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True
    t = threading.Thread(target=_worker, name="co2_fetcher", daemon=True)
    t.start()

