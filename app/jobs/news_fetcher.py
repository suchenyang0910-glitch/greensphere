import os
import threading
import time
from datetime import datetime, timedelta, timezone

from gs_db import get_db
from models import log_system_event
from app.services.news_service import fetch_top_news_items, upsert_news_items


_started = False
_lock = threading.Lock()


def _next_run_utc(hour: int, minute: int) -> datetime:
    now = datetime.now(timezone.utc)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


def _worker() -> None:
    hour = int(os.getenv("GS_NEWS_FETCH_UTC_HOUR") or "3")
    minute = int(os.getenv("GS_NEWS_FETCH_UTC_MINUTE") or "0")
    run_on_start = (os.getenv("GS_NEWS_FETCH_ON_START") or "1").strip().lower() in {"1", "true", "yes", "on"}

    if run_on_start:
        try:
            gen = get_db()
            db = next(gen)
            items = fetch_top_news_items()
            inserted = upsert_news_items(db, items)
            log_system_event(db, level="info", event="news_fetch", message=f"inserted={inserted} total={len(items)}")
            gen.close()
        except Exception as e:
            try:
                gen = get_db()
                db = next(gen)
                log_system_event(db, level="error", event="news_fetch_error", message=str(e))
                gen.close()
            except Exception:
                pass

    while True:
        try:
            target = _next_run_utc(hour, minute)
            sleep_s = max(1, int((target - datetime.now(timezone.utc)).total_seconds()))
            time.sleep(sleep_s)
            gen = get_db()
            db = next(gen)
            items = fetch_top_news_items()
            inserted = upsert_news_items(db, items)
            log_system_event(db, level="info", event="news_fetch", message=f"inserted={inserted} total={len(items)}")
            gen.close()
        except Exception as e:
            try:
                gen = get_db()
                db = next(gen)
                log_system_event(db, level="error", event="news_fetch_error", message=str(e))
                gen.close()
            except Exception:
                pass
            time.sleep(60)


def start_news_fetcher() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True
    t = threading.Thread(target=_worker, name="news_fetcher", daemon=True)
    t.start()

