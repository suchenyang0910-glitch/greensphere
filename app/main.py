from fastapi import FastAPI
from fastapi import Header, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.site import site_router


from app.api import health, waitlist
from app.core.database import Base, engine
from app.api.quests import router as quests_router
from app.api.me import router as me_router

from app.auth.telegram_webapp import parse_telegram_user_from_init_data

from app.models import waitlist as _waitlist_model  # noqa: F401
from app.models import rate_limit as _rate_limit_model  # noqa: F401
from fastapi.middleware.cors import CORSMiddleware
from routes import router as greensphere_router
from gs_db import init_gs_db
from app.api.site import site_router


def create_app() -> FastAPI:
    app = FastAPI(title="GreenSphere API")

    # 静态文件 & 模板
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")

    # Routers
    app.include_router(health.router, prefix="/api")
    app.include_router(waitlist.router, prefix="/api")
    app.include_router(greensphere_router) 
    # DB init
    @app.on_event("startup")
    def _startup_create_tables() -> None:
        Base.metadata.create_all(bind=engine)
        init_gs_db()


    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    return app



app = create_app()
app.include_router(site_router)
app.include_router(greensphere_router) 

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/api/auth/debug")
def auth_debug(x_telegram_init_data: str | None = Header(default=None)):
    if not x_telegram_init_data:
        return {"ok": False, "reason": "Missing X-Telegram-Init-Data"}
    u = parse_telegram_user_from_init_data(x_telegram_init_data)
    return {"ok": True, "user": u}

app.include_router(quests_router)
app.include_router(me_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://greensphere.world",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)