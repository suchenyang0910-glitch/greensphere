# app/api/site.py
import json
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from site_i18n import TEXTS, detect_lang
from gs_db import get_db as get_behavior_db
from app.services.news_service import list_latest_news
from app.core.database import get_db as get_sa_db
from app.models.waitlist import WaitlistSubscriber
from app.services.monitor_service import notify_monitor

templates = Jinja2Templates(directory="templates")

site_router = APIRouter()

@lru_cache(maxsize=1)
def _asset_version() -> str:
    override = (os.getenv("GS_ASSET_VERSION") or "").strip()
    if override:
        return override
    try:
        return str(int(Path("static/style_home.css").stat().st_mtime))
    except Exception:
        return "1"


def _external_base_url(request: Request) -> str:
    override = (os.getenv("GS_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if override:
        return override
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    host = (request.headers.get("host") or request.url.hostname or "").strip()
    if proto == "http" and host and host not in {"127.0.0.1", "localhost"} and not host.startswith("127."):
        proto = "https"
    return f"{proto}://{host}"


def _normalize_lang(v: str | None) -> str | None:
    if not v:
        return None
    s = v.strip().lower()
    if s in {"kh", "km"}:
        return "km"
    if s.startswith("zh"):
        return "zh"
    if s.startswith("th"):
        return "th"
    if s.startswith("vi"):
        return "vi"
    if s.startswith("en"):
        return "en"
    return None


def _seo_for_lang(lang: str) -> dict:
    seo = {
        "zh": {
            "title": "GreenSphere · 每日绿色行动打卡｜LeafPass & G-Points",
            "description": "GreenSphere 是一个通过每日小任务、积分和数字徽章，帮助你养成可持续生活习惯的平台。不炒币、不理财，只记录和奖励真实的绿色行动。",
            "og_title": "GreenSphere · 每日绿色行动打卡",
            "og_description": "用几分钟的小行动，积累真实的绿色影响力。LeafPass 徽章 & G-Points 积分，记录你的每一次环保选择。",
        },
        "en": {
            "title": "GreenSphere · Small Actions. Real Impact.",
            "description": "GreenSphere helps you build sustainable habits via simple daily quests, G-Points, and LeafPass badges.",
            "og_title": "GreenSphere · Small Actions. Real Impact.",
            "og_description": "Turn small daily actions into real green impact with quests, points, streaks, and LeafPass badges.",
        },
        "th": {
            "title": "GreenSphere · ภารกิจสีเขียวรายวัน | LeafPass & G‑Points",
            "description": "GreenSphere ช่วยสร้างนิสัยด้านสิ่งแวดล้อมผ่านภารกิจรายวัน คะแนน G‑Points และเหรียญ LeafPass.",
            "og_title": "GreenSphere · ภารกิจสีเขียวรายวัน",
            "og_description": "สะสมผลกระทบสีเขียวจริงจากการกระทำเล็ก ๆ ทุกวัน ผ่านภารกิจ คะแนน และเหรียญ LeafPass.",
        },
        "vi": {
            "title": "GreenSphere · Nhiệm vụ xanh hằng ngày | LeafPass & G‑Points",
            "description": "GreenSphere giúp bạn xây dựng thói quen bền vững qua nhiệm vụ hằng ngày, điểm G‑Points và huy hiệu LeafPass.",
            "og_title": "GreenSphere · Nhiệm vụ xanh hằng ngày",
            "og_description": "Biến hành động nhỏ mỗi ngày thành tác động xanh thực sự với nhiệm vụ, điểm và huy hiệu LeafPass.",
        },
        "km": {
            "title": "GreenSphere · ភារកិច្ចបៃតងប្រចាំថ្ងៃ | LeafPass & G‑Points",
            "description": "GreenSphere ជួយ​អ្នក​បង្កើត​ទម្លាប់ជីវិតបៃតង តាមរយៈភារកិច្ច​ប្រចាំថ្ងៃ ពិន្ទុ G‑Points និង徽章 LeafPass។",
            "og_title": "GreenSphere · ភារកិច្ចបៃតងប្រចាំថ្ងៃ",
            "og_description": "សកម្មភាពតូចៗរៀងរាល់ថ្ងៃ → ឥទ្ធិពលបៃតងពិតប្រាកដ ជាមួយភារកិច្ច ពិន្ទុ និង徽章 LeafPass។",
        },
    }
    return seo.get(lang, seo["en"])


def _og_locale(lang: str) -> str:
    return {
        "zh": "zh_CN",
        "en": "en_US",
        "th": "th_TH",
        "vi": "vi_VN",
        "km": "km_KH",
    }.get(lang, "en_US")


@site_router.get("/", response_class=HTMLResponse)
async def home(request: Request, lang: str | None = Query(default=None)):
    accept_language = request.headers.get("Accept-Language")
    explicit = _normalize_lang(lang)
    selected = explicit or detect_lang(accept_language)
    text = TEXTS.get(selected, TEXTS["en"])

    base_url = _external_base_url(request)
    canonical = f"{base_url}/" + (f"?lang={selected}" if explicit else "")
    alternates = {k: f"{base_url}/?lang={k}" for k in ["en", "zh", "th", "vi", "km"]}
    alternates["x-default"] = alternates["en"]
    seo = _seo_for_lang(selected)
    seo["canonical"] = canonical
    seo["og_image"] = f"{base_url}/static/og-greensphere.png"
    seo["site_name"] = "GreenSphere"
    seo["og_locale"] = _og_locale(selected)
    seo["og_locale_alternates"] = [_og_locale(k) for k in ["en", "zh", "th", "vi", "km"] if k != selected]
    seo["structured_data"] = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Organization",
                    "@id": f"{base_url}/#organization",
                    "name": "GreenSphere",
                    "url": f"{base_url}/",
                    "email": "hello@greensphere.earth",
                },
                {
                    "@type": "WebSite",
                    "@id": f"{base_url}/#website",
                    "name": "GreenSphere",
                    "url": f"{base_url}/",
                    "inLanguage": selected,
                    "publisher": {"@id": f"{base_url}/#organization"},
                },
            ],
        },
        ensure_ascii=False,
    )

    gen = get_db()
    behavior_gen = get_behavior_db()
    behavior_db = next(behavior_gen)
    news_items = list_latest_news(behavior_db, limit=10)
    behavior_gen.close()

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "t": text,
            "lang": selected,
            "seo": seo,
            "alternates": alternates,
            "news_items": news_items,
            "asset_version": _asset_version(),
        },
    )


@site_router.post("/", include_in_schema=False)
async def home_submit(request: Request, db: Session = Depends(get_sa_db)):
    content_type = (request.headers.get("content-type") or "").lower()
    payload: dict[str, str] = {}
    if "application/json" in content_type:
        data = await request.json()
        if isinstance(data, dict):
            payload = {str(k): "" if v is None else str(v) for k, v in data.items()}
    else:
        raw = (await request.body()).decode("utf-8", errors="ignore")
        parsed = parse_qs(raw, keep_blank_values=True)
        payload = {k: (v[0] if v else "") for k, v in parsed.items()}

    email = (payload.get("email") or "").strip()
    if not email:
        return Response(content='{"detail":"Missing email"}', media_type="application/json", status_code=400)

    name = (payload.get("name") or "").strip()
    telegram = (payload.get("telegram") or "").strip()
    topics = (payload.get("topics") or "").strip()
    role = (payload.get("role") or "").strip() or "individual"
    region = (payload.get("region") or "").strip() or "SEA"

    note_parts = []
    if name:
        note_parts.append(f"name={name}")
    if topics:
        note_parts.append(f"topics={topics}")
    note = "; ".join(note_parts)[:255] if note_parts else None

    existing = db.query(WaitlistSubscriber).filter_by(email=email).first()
    if not existing:
        db.add(
            WaitlistSubscriber(
                email=email,
                region=region[:8],
                role=role[:32],
                telegram=telegram[:50] if telegram else None,
                note=note,
                source="home_form",
            )
        )
        db.commit()
        client_ip = request.client.host if request.client else "unknown"
        notify_monitor(
            "🟢 <b>New Waitlist Signup</b>\n\n"
            f"📧 Email: {email}\n"
            f"🌍 Region: {region}\n"
            f"👤 Role: {role}\n"
            f"📱 Telegram: {telegram or '-'}\n"
            f"📝 Note: {note or '-'}\n"
            f"🕒 IP: {client_ip}"
        )

    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept or "application/json" in content_type:
        return {"success": True}

    q = request.url.query
    base = "/" + (f"?{q}&submitted=1" if q else "?submitted=1")
    return RedirectResponse(url=base + "#pioneer", status_code=303)


@site_router.head("/", include_in_schema=False)
async def home_head():
    return Response(content=b"", headers={"Content-Type": "text/html; charset=utf-8"})
@site_router.get("/pioneer", include_in_schema=False)
async def pioneer_redirect(lang: str | None = Query(default=None)):
    q = f"?lang={_normalize_lang(lang)}" if _normalize_lang(lang) else ""
    return RedirectResponse(url=f"/{q}#pioneer", status_code=307)


@site_router.get("/for-companies", include_in_schema=False)
async def for_companies_redirect(lang: str | None = Query(default=None)):
    q = f"?lang={_normalize_lang(lang)}" if _normalize_lang(lang) else ""
    return RedirectResponse(url=f"/{q}#why-for-whom", status_code=307)


@site_router.get("/about", include_in_schema=False)
async def about_redirect(lang: str | None = Query(default=None)):
    q = f"?lang={_normalize_lang(lang)}" if _normalize_lang(lang) else ""
    return RedirectResponse(url=f"/{q}#why-for-whom", status_code=307)


@site_router.get("/robots.txt", include_in_schema=False)
async def robots(request: Request):
    base_url = _external_base_url(request)
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /api/",
            "Disallow: /admin",
            "Disallow: /app",
            "",
            f"Sitemap: {base_url}/sitemap.xml",
            "",
        ]
    )
    return Response(content=body, media_type="text/plain; charset=utf-8", headers={"Cache-Control": "public, max-age=3600"})


@site_router.head("/robots.txt", include_in_schema=False)
async def robots_head(request: Request):
    base_url = _external_base_url(request)
    headers = {"Cache-Control": "public, max-age=3600"}
    headers["Content-Type"] = "text/plain; charset=utf-8"
    headers["X-Sitemap"] = f"{base_url}/sitemap.xml"
    return Response(content=b"", headers=headers)


@site_router.get("/sitemap.xml", include_in_schema=False)
async def sitemap(request: Request):
    base_url = _external_base_url(request)
    urls = [f"{base_url}/"] + [f"{base_url}/?lang={k}" for k in ["en", "zh", "th", "vi", "km"]]
    lastmod = request.headers.get("x-build-date") or None
    if not lastmod:
        lastmod = None

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for loc in urls:
        parts.append("<url>")
        parts.append(f"<loc>{loc}</loc>")
        if lastmod:
            parts.append(f"<lastmod>{lastmod}</lastmod>")
        for hreflang, href in ({"x-default": f"{base_url}/", "en": f"{base_url}/?lang=en", "zh": f"{base_url}/?lang=zh", "th": f"{base_url}/?lang=th", "vi": f"{base_url}/?lang=vi", "km": f"{base_url}/?lang=km"}).items():
            parts.append(f'<xhtml:link rel="alternate" hreflang="{hreflang}" href="{href}"/>')
        parts.append("<changefreq>daily</changefreq>")
        parts.append("<priority>1.0</priority>")
        parts.append("</url>")
    parts.append("</urlset>")
    body = "\n".join(parts) + "\n"
    return Response(content=body, media_type="application/xml; charset=utf-8", headers={"Cache-Control": "public, max-age=3600"})


@site_router.head("/sitemap.xml", include_in_schema=False)
async def sitemap_head(request: Request):
    headers = {"Cache-Control": "public, max-age=3600"}
    headers["Content-Type"] = "application/xml; charset=utf-8"
    return Response(content=b"", headers=headers)


@site_router.get("/api/news", include_in_schema=False)
async def api_news(request: Request, limit: int = 10):
    gen = get_db()
    db = next(gen)
    items = list_latest_news(db, limit=int(limit))
    gen.close()
    return {"items": items}
