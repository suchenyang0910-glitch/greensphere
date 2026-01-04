# app/api/site.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from site_i18n import TEXTS, detect_lang

templates = Jinja2Templates(directory="templates")

site_router = APIRouter()


@site_router.get("/", response_class=HTMLResponse)

async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@site_router.get("/pioneer", response_class=HTMLResponse)
async def pioneer(request: Request):
    return templates.TemplateResponse("pioneer.html", {"request": request})

@site_router.get("/for-companies", response_class=HTMLResponse)
async def for_companies(request: Request):
    return templates.TemplateResponse("for_companies.html", {"request": request})

@site_router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})