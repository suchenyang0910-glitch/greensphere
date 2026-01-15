import os
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from gs_db import get_db
from models import log_system_event


@dataclass(frozen=True)
class Co2Point:
    date: str
    value: float


def _co2_source_url() -> str:
    return (
        os.getenv("GS_CO2_SOURCE_URL")
        or "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_daily_mlo.txt"
    ).strip()


def _parse_noaa_daily_mlo(text: str) -> list[Co2Point]:
    points: list[Co2Point] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 5:
            continue
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            v = float(parts[4])
        except Exception:
            continue
        if v <= 0:
            continue
        points.append(Co2Point(date=f"{y:04d}-{m:02d}-{d:02d}", value=v))
    return points


def fetch_latest_co2_points(limit: int = 7) -> list[Co2Point]:
    url = _co2_source_url()
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        r = client.get(url, headers={"User-Agent": "GreenSphere/1.0"})
        r.raise_for_status()
        text = r.text
    all_points = _parse_noaa_daily_mlo(text)
    if not all_points:
        return []
    return all_points[-limit:]


def upsert_points_to_db(points: list[Co2Point], source: str) -> int:
    if not points:
        return 0
    gen = get_db()
    db = next(gen)
    try:
        c = db.cursor()
        fetched_at = datetime.now(timezone.utc).isoformat()
        inserted = 0
        for p in points:
            c.execute(
                """
                INSERT INTO co2_daily(date, value, source, fetched_at_utc)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                  value=excluded.value,
                  source=excluded.source,
                  fetched_at_utc=excluded.fetched_at_utc;
                """,
                (p.date, p.value, source, fetched_at),
            )
            inserted += 1
        db.commit()
        return inserted
    finally:
        gen.close()


def update_co2_db(limit: int = 7) -> list[Co2Point]:
    source = _co2_source_url()
    points = fetch_latest_co2_points(limit=limit)
    inserted = upsert_points_to_db(points, source)
    try:
        gen = get_db()
        db = next(gen)
        log_system_event(db, level="info", event="co2_fetch", message=f"inserted={inserted} total={len(points)} source={source}")
        gen.close()
    except Exception:
        pass
    return points


def get_latest_points_from_db(limit: int = 7) -> list[Co2Point]:
    gen = get_db()
    db = next(gen)
    try:
        c = db.cursor()
        c.execute(
            "SELECT date, value FROM co2_daily ORDER BY date DESC LIMIT ?;",
            (limit,),
        )
        rows = c.fetchall()
        pts = [Co2Point(date=r["date"], value=float(r["value"])) for r in rows]
        return list(reversed(pts))
    finally:
        gen.close()

def get_co2_points_from_db() -> list[Co2Point]:
    return get_latest_points_from_db(limit=7)


def render_trend_svg(points: list[Co2Point]) -> str:
    title = "近 7 天大气 CO₂ 趋势（NOAA GML · MLO Daily）"
    if not points:
        w, h = 980, 380
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="rgba(255,255,255,0.08)"/>
      <stop offset="1" stop-color="rgba(255,255,255,0.04)"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#38f2c6"/>
      <stop offset="1" stop-color="#1fd19c"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="{w}" height="{h}" rx="22" fill="url(#bg)" stroke="rgba(255,255,255,0.14)"/>
  <text x="56" y="34" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="16" font-weight="800" fill="rgba(231,245,239,0.92)">{title}</text>
  <text x="56" y="56" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="12" font-weight="650" fill="rgba(231,245,239,0.70)">暂无数据，等待每日 01:00（UTC+7）写入数据库后展示</text>
  <rect x="56" y="92" width="868" height="240" rx="18" fill="rgba(0,0,0,0.14)" stroke="rgba(255,255,255,0.10)"/>
  <rect x="90" y="140" width="460" height="14" rx="7" fill="rgba(231,245,239,0.14)"/>
  <rect x="90" y="170" width="520" height="12" rx="6" fill="rgba(231,245,239,0.10)"/>
  <rect x="90" y="214" width="600" height="14" rx="7" fill="rgba(231,245,239,0.14)"/>
  <rect x="90" y="244" width="380" height="12" rx="6" fill="rgba(231,245,239,0.10)"/>
  <rect x="90" y="288" width="260" height="14" rx="7" fill="url(#accent)" opacity="0.75"/>
</svg>"""
    values = [p.value for p in points]
    vmin = min(values)
    vmax = max(values)
    if vmax - vmin < 0.01:
        vmax = vmin + 0.01

    w, h = 980, 380
    pad_l, pad_r, pad_t, pad_b = 56, 18, 54, 54
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b

    def x(i: int) -> float:
        if len(points) == 1:
            return pad_l + plot_w / 2
        return pad_l + (plot_w * i) / (len(points) - 1)

    def y(v: float) -> float:
        return pad_t + (plot_h * (vmax - v)) / (vmax - vmin)

    pts_xy = [(x(i), y(p.value)) for i, p in enumerate(points)]
    pts = " ".join([f"{px:.2f},{py:.2f}" for px, py in pts_xy])
    last = points[-1]
    last_x = x(len(points) - 1)
    last_y = y(last.value)
    vmin_label = f"{vmin:.2f} ppm"
    vmax_label = f"{vmax:.2f} ppm"
    last_label = f"{last.date} · {last.value:.2f} ppm"

    ticks = 4
    y_lines = []
    y_labels = []
    for i in range(ticks + 1):
        t = i / ticks
        yy = pad_t + plot_h * t
        vv = vmax - (vmax - vmin) * t
        y_lines.append(f'<line x1="{pad_l}" y1="{yy:.2f}" x2="{w - pad_r}" y2="{yy:.2f}" stroke="rgba(255,255,255,0.06)"/>')
        y_labels.append(
            f'<text x="{pad_l - 10}" y="{yy + 4:.2f}" text-anchor="end" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="11" fill="rgba(231,245,239,0.70)">{vv:.2f}</text>'
        )

    x_labels = []
    for i, p in enumerate(points):
        if i in (0, len(points) - 1) or len(points) <= 5 or i % 2 == 0:
            label = p.date[5:]
            x_labels.append(
                f'<text x="{x(i):.2f}" y="{pad_t + plot_h + 28:.2f}" text-anchor="middle" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="11" fill="rgba(231,245,239,0.70)">{label}</text>'
            )

    dots = []
    for i, p in enumerate(points):
        px, py = pts_xy[i]
        dots.append(
            f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4.2" fill="rgba(56,242,198,0.92)"><title>{p.date} · {p.value:.2f} ppm</title></circle>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="rgba(255,255,255,0.08)"/>
      <stop offset="1" stop-color="rgba(255,255,255,0.04)"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#38f2c6"/>
      <stop offset="1" stop-color="#1fd19c"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="{w}" height="{h}" rx="22" fill="url(#bg)" stroke="rgba(255,255,255,0.14)"/>
  <text x="{pad_l}" y="34" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="16" font-weight="800" fill="rgba(231,245,239,0.92)">{title}</text>
  <text x="{pad_l}" y="52" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="12" font-weight="650" fill="rgba(231,245,239,0.70)">{last_label}</text>

  <g>
    {''.join(y_lines)}
    <line x1="{pad_l}" y1="{pad_t}" x2="{w - pad_r}" y2="{pad_t}" stroke="rgba(255,255,255,0.10)"/>
    <line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{w - pad_r}" y2="{pad_t + plot_h}" stroke="rgba(255,255,255,0.10)"/>
    <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="rgba(255,255,255,0.10)"/>
  </g>

  <g>
    {''.join(y_labels)}
    {''.join(x_labels)}
  </g>

  <polyline fill="none" stroke="rgba(56,242,198,0.18)" stroke-width="8" points="{pts}" stroke-linecap="round" stroke-linejoin="round"/>
  <polyline fill="none" stroke="url(#accent)" stroke-width="3.5" points="{pts}" stroke-linecap="round" stroke-linejoin="round"/>
  <g>
    {''.join(dots)}
    <circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="6" fill="#38f2c6" opacity="0.95"/>
  </g>
</svg>"""
