import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from xml.etree import ElementTree as ET

import requests


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str | None
    published_at: str | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_text(node) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _parse_pub_date(v: str) -> str | None:
    s = (v or "").strip()
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except Exception:
        return None


def parse_rss(xml_text: str, *, source_name: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []
    items: list[NewsItem] = []
    for it in channel.findall("item"):
        title = _safe_text(it.find("title"))
        link = _safe_text(it.find("link"))
        pub = _parse_pub_date(_safe_text(it.find("pubDate")))
        if not title or not link:
            continue
        items.append(NewsItem(title=title, url=link, source=source_name, published_at=pub))
    return items


def default_rss_urls() -> list[str]:
    env = (os.getenv("GS_NEWS_RSS_URLS") or "").strip()
    if env:
        return [u.strip() for u in env.splitlines() if u.strip()]
    return [
        "https://news.google.com/rss/search?q=carbon%20emissions&hl=en-US&gl=US&ceid=US:en",
    ]


def fetch_top_news_items() -> list[NewsItem]:
    urls = default_rss_urls()
    all_items: list[NewsItem] = []
    for url in urls:
        r = requests.get(url, timeout=15, headers={"User-Agent": "GreenSphereBot/1.0 (+https://greensphere.earth)"})
        r.raise_for_status()
        all_items.extend(parse_rss(r.text, source_name="rss"))

    seen: set[str] = set()
    unique: list[NewsItem] = []
    for it in all_items:
        if it.url in seen:
            continue
        seen.add(it.url)
        unique.append(it)

    def sort_key(x: NewsItem):
        return x.published_at or ""

    unique.sort(key=sort_key, reverse=True)
    return unique[:10]


def upsert_news_items(conn: sqlite3.Connection, items: Iterable[NewsItem]) -> int:
    fetched_at = _now_iso()
    c = conn.cursor()
    inserted = 0
    for it in items:
        try:
            c.execute(
                """
                INSERT OR IGNORE INTO news_items (title, url, source, published_at, fetched_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (it.title, it.url, it.source, it.published_at, fetched_at),
            )
            if c.rowcount:
                inserted += 1
        except Exception:
            continue
    conn.commit()
    return inserted


def list_latest_news(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    c = conn.cursor()
    c.execute(
        """
        SELECT title, url, source, published_at, fetched_at
        FROM news_items
        ORDER BY COALESCE(published_at, fetched_at) DESC
        LIMIT ?;
        """,
        (int(limit),),
    )
    return [dict(r) for r in c.fetchall()]

