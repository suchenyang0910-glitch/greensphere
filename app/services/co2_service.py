import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


@dataclass(frozen=True)
class Co2Point:
    date: str
    value: float


def _cache_path() -> Path:
    raw = (os.getenv("GS_CO2_CACHE_PATH") or "").strip()
    if raw:
        return Path(raw)
    return Path("data") / "co2_daily_cache.json"


def _co2_source_url() -> str:
    return (
        os.getenv("GS_CO2_SOURCE_URL")
        or "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_daily_mlo.txt"
    ).strip()


def _local_date_utc_plus7() -> str:
    now = datetime.now(timezone.utc) + timedelta(hours=7)
    return now.date().strftime("%Y-%m-%d")


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
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        r = client.get(url, headers={"User-Agent": "GreenSphere/1.0"})
        r.raise_for_status()
        text = r.text
    all_points = _parse_noaa_daily_mlo(text)
    if not all_points:
        return []
    return all_points[-limit:]


def load_cached_points() -> list[Co2Point]:
    path = _cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        pts = data.get("points") if isinstance(data, dict) else None
        if not isinstance(pts, list):
            return []
        out: list[Co2Point] = []
        for p in pts:
            if not isinstance(p, dict):
                continue
            d = p.get("date")
            v = p.get("value")
            if not isinstance(d, str):
                continue
            try:
                fv = float(v)
            except Exception:
                continue
            out.append(Co2Point(date=d, value=fv))
        return out
    except Exception:
        return []


def update_co2_cache() -> list[Co2Point]:
    points = fetch_latest_co2_points(limit=7)
    if not points:
        return load_cached_points()
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": _co2_source_url(),
        "updated_local_date_utc_plus7": _local_date_utc_plus7(),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "points": [{"date": p.date, "value": p.value} for p in points],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return points


def get_co2_points_cached_or_fetch() -> list[Co2Point]:
    path = _cache_path()
    pts = load_cached_points()
    if pts:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            last = data.get("updated_local_date_utc_plus7") if isinstance(data, dict) else None
            if isinstance(last, str) and last == _local_date_utc_plus7():
                return pts
        except Exception:
            pass
    try:
        return update_co2_cache()
    except Exception:
        return pts


def render_trend_svg(points: list[Co2Point]) -> str:
    title = "近 7 天大气 CO₂ 趋势（NOAA GML · MLO Daily）"
    if not points:
        points = [
            Co2Point(date="2026-01-01", value=420.0),
            Co2Point(date="2026-01-02", value=420.2),
            Co2Point(date="2026-01-03", value=420.1),
            Co2Point(date="2026-01-04", value=420.4),
            Co2Point(date="2026-01-05", value=420.3),
            Co2Point(date="2026-01-06", value=420.6),
            Co2Point(date="2026-01-07", value=420.7),
        ]
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

    pts = " ".join([f"{x(i):.2f},{y(p.value):.2f}" for i, p in enumerate(points)])
    last = points[-1]
    last_x = x(len(points) - 1)
    last_y = y(last.value)
    vmin_label = f"{vmin:.2f} ppm"
    vmax_label = f"{vmax:.2f} ppm"
    last_label = f"{last.date} · {last.value:.2f} ppm"

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

  <line x1="{pad_l}" y1="{pad_t}" x2="{w - pad_r}" y2="{pad_t}" stroke="rgba(255,255,255,0.08)"/>
  <line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{w - pad_r}" y2="{pad_t + plot_h}" stroke="rgba(255,255,255,0.08)"/>
  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="rgba(255,255,255,0.08)"/>

  <text x="{pad_l - 10}" y="{pad_t + 4}" text-anchor="end" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="11" fill="rgba(231,245,239,0.70)">{vmax_label}</text>
  <text x="{pad_l - 10}" y="{pad_t + plot_h}" text-anchor="end" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="11" fill="rgba(231,245,239,0.70)">{vmin_label}</text>

  <polyline fill="none" stroke="rgba(56,242,198,0.18)" stroke-width="8" points="{pts}" stroke-linecap="round" stroke-linejoin="round"/>
  <polyline fill="none" stroke="url(#accent)" stroke-width="3.5" points="{pts}" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="6" fill="#38f2c6" opacity="0.95"/>
</svg>"""
