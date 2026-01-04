# app/api/site.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from site_i18n import TEXTS, detect_lang

templates = Jinja2Templates(directory="templates")

site_router = APIRouter()


@site_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    accept_language = request.headers.get("Accept-Language")
    lang = detect_lang(accept_language)
    text = TEXTS.get(lang, TEXTS["en"])

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "t": text,        # 文案
            "lang": lang,     # 当前语言
        },
    )
