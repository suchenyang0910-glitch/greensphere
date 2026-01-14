import sqlite3
from datetime import datetime
import os
import json
import secrets
import csv
from io import StringIO
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, BackgroundTasks, Request
from fastapi import Header
from fastapi import HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from gs_db import get_db

from models import (
    CompleteTaskRequest,
    UserInitRequest,
    get_today_str,
    calculate_stats,
    list_user_badges,
    list_recent_task_logs,
    list_next_rewards,
    list_challenges,
    list_user_challenge_ids,
    join_challenge,
    challenge_leaderboard,
    add_feed_event,
    list_feed,
    like_feed,
    comment_feed,
    list_rewards,
    create_redemption,
    unlock_eligible_badges,
    log_system_event,
    list_system_logs,
)
from telegram_utils import send_telegram_message, send_monitor_message
from app.middleware.admin_auth import admin_auth
from app.auth.telegram_webapp import parse_telegram_user_from_init_data
from gs_rate_limiter import increment_and_get_count

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@lru_cache(maxsize=1)
def _asset_version() -> str:
    v = (os.getenv("GS_ASSET_VERSION") or "").strip()
    if v:
        return v
    try:
        return str(int(max(Path("static/style.css").stat().st_mtime, Path("static/admin.css").stat().st_mtime)))
    except Exception:
        return "1"

REQUIRE_TG_INIT_DATA = (os.getenv("GS_REQUIRE_TG_INIT_DATA") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

def _normalize_lang(code: str | None) -> str:
    v = (code or "").strip().lower()
    if v.startswith("zh"):
        return "zh"
    if v.startswith("th"):
        return "th"
    if v.startswith("vi"):
        return "vi"
    if v.startswith("km") or v.startswith("kh"):
        return "km"
    return "en"


def _client_ip(request: Request) -> str:
    xf = request.headers.get("x-forwarded-for")
    if xf:
        return xf.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit_or_429(db: sqlite3.Connection, *, ip: str, key: str, limit: int, window_seconds: int = 60) -> None:
    cnt = increment_and_get_count(db, ip=ip, key=key, window_seconds=window_seconds)
    if cnt > int(limit):
        raise HTTPException(status_code=429, detail="Too Many Requests")


# 打卡 WebApp 页面（挂在 /app）
@router.get("/app", response_class=HTMLResponse)
def app_index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "asset_version": _asset_version()},
        headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"},
    )


@router.head("/app", include_in_schema=False)
def app_index_head():
    return Response(
        content=b"",
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "X-Robots-Tag": "noindex, nofollow",
            "Cache-Control": "no-store",
        },
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_index(request: Request):
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "asset_version": _asset_version()},
        headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"},
    )


@router.head("/admin", include_in_schema=False)
def admin_index_head():
    return Response(
        content=b"",
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "X-Robots-Tag": "noindex, nofollow",
            "Cache-Control": "no-store",
        },
    )


def _external_base_url(request: Request) -> str:
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    host = (request.headers.get("host") or request.url.hostname or "").strip()
    if proto == "http" and host and host not in {"127.0.0.1", "localhost"} and not host.startswith("127."):
        proto = "https"
    return f"{proto}://{host}"


def _ensure_public_profile(db: sqlite3.Connection, user_id: int) -> dict:
    c = db.cursor()
    c.execute("SELECT public_token, is_public FROM user_public_profiles WHERE user_id = ?;", (int(user_id),))
    row = c.fetchone()
    if row:
        return {"token": row["public_token"], "is_public": int(row["is_public"]) == 1}
    for _ in range(5):
        token = secrets.token_urlsafe(16)
        try:
            c.execute(
                """
                INSERT INTO user_public_profiles (user_id, public_token, is_public, updated_at)
                VALUES (?, ?, 1, ?);
                """,
                (int(user_id), token, datetime.utcnow().isoformat()),
            )
            db.commit()
            return {"token": token, "is_public": True}
        except sqlite3.IntegrityError:
            continue
    raise HTTPException(status_code=500, detail="Failed to generate token")


def _set_profile_public(db: sqlite3.Connection, user_id: int, is_public: bool) -> dict:
    p = _ensure_public_profile(db, user_id)
    c = db.cursor()
    c.execute(
        "UPDATE user_public_profiles SET is_public = ?, updated_at = ? WHERE user_id = ?;",
        (1 if is_public else 0, datetime.utcnow().isoformat(), int(user_id)),
    )
    db.commit()
    return {"token": p["token"], "is_public": bool(is_public)}


@router.get("/p/{token}", response_class=HTMLResponse)
def public_profile(token: str, request: Request, db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()
    c.execute(
        """
        SELECT u.id AS user_id, u.name AS name, p.is_public AS is_public
        FROM user_public_profiles p
        JOIN users u ON u.id = p.user_id
        WHERE p.public_token = ?;
        """,
        (token,),
    )
    row = c.fetchone()
    if not row or int(row["is_public"]) != 1:
        raise HTTPException(status_code=404, detail="Not found")
    user_id = int(row["user_id"])
    stats = calculate_stats(db, user_id)
    badges = list_user_badges(db, user_id)
    recent = list_recent_task_logs(db, user_id, limit=30)
    logs = [{"date": x.get("date"), "title": x.get("title"), "points": x.get("points")} for x in recent]
    return templates.TemplateResponse(
        "public_profile.html",
        {
            "request": request,
            "name": row["name"] or f"User {user_id}",
            "stats": stats,
            "badges": badges,
            "logs": logs,
            "asset_version": _asset_version(),
        },
        headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"},
    )


@router.post("/api/profile/share")
def profile_share(
    request: Request,
    body: dict,
    x_telegram_init_data: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="api:profile:share", limit=30)
    user_id = int(body.get("user_id") or 0)
    make_public = body.get("is_public")
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        user_id = int(u["telegram_id"])
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    if make_public is None:
        p = _ensure_public_profile(db, user_id)
    else:
        p = _set_profile_public(db, user_id, bool(make_public))
    base = _external_base_url(request)
    return {"ok": True, "token": p["token"], "is_public": p["is_public"], "url": f"{base}/p/{p['token']}"}


@router.get("/api/export/logs.csv")
def export_logs_csv(
    request: Request,
    user_id: int | None = None,
    x_telegram_init_data: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="api:export:logs", limit=60)
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        user_id = int(u["telegram_id"])
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    if user_id is None:
        user_id = 1
    rows = list_recent_task_logs(db, int(user_id), limit=500)
    output = StringIO()
    w = csv.writer(output)
    w.writerow(["date", "title", "points", "created_at"])
    for r in rows:
        w.writerow([r.get("date"), r.get("title"), r.get("points"), r.get("created_at")])
    csv_text = output.getvalue()
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="greensphere_logs.csv"'},
    )



# 用户初始化：用 Telegram 用户建立/获取内部 user_id
@router.post("/api/init_user")
def init_user(
    body: UserInitRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    x_telegram_init_data: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="api:init_user", limit=20)
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        body.telegram_id = int(u["telegram_id"])
        body.username = u.get("username") or body.username
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")

    c = db.cursor()

    # 直接用 telegram_id 作为 users.id
    if body.telegram_id is None:
        return {"ok": False, "reason": "Missing telegram_id"}
    c.execute("SELECT id FROM users WHERE id = ?;", (int(body.telegram_id),))
    row = c.fetchone()

    if row is None:
        c.execute(
            "INSERT INTO users (id, name, created_at) VALUES (?, ?, datetime('now'));",
            (int(body.telegram_id), body.username or "Telegram User"),
        )
        db.commit()
        user_id = int(body.telegram_id)
        log_system_event(
            db,
            level="info",
            event="user_registered",
            message=f"user={body.telegram_id}",
        )
        background_tasks.add_task(
            send_monitor_message,
            f"🆕 新用户注册\ntelegram_id: {body.telegram_id}\nname: {body.username or 'Telegram User'}\n来源：/api/init_user",
        )
    else:
        user_id = row["id"]

    return {"user_id": user_id}


# 获取任务列表 + 今日完成情况 + 统计
@router.get("/api/tasks")
def get_tasks(
    request: Request,
    user_id: int | None = None,
    x_telegram_init_data: str | None = Header(default=None),
    x_gs_lang: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="api:tasks", limit=120)
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        user_id = int(u["telegram_id"])
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    if user_id is None:
        user_id = 1
    c = db.cursor()

    # 所有任务
    c.execute("SELECT id, title, points, i18n_json FROM tasks;")
    raw_tasks = [dict(row) for row in c.fetchall()]
    locale = _normalize_lang(x_gs_lang) if x_gs_lang else _normalize_lang(request.headers.get("accept-language"))
    tasks = []
    for t in raw_tasks:
        title = t.get("title")
        i18n_json = t.get("i18n_json")
        if i18n_json:
            try:
                m = json.loads(i18n_json)
                if isinstance(m, dict):
                    title = m.get(locale) or m.get("en") or title
            except Exception:
                pass
        tasks.append({"id": t.get("id"), "title": title, "points": t.get("points")})

    # 今天已完成的任务
    today_str = get_today_str()
    c.execute(
        """
        SELECT task_id FROM user_task_logs
        WHERE user_id = ? AND date = ?;
        """,
        (user_id, today_str),
    )
    done_today_ids = {row["task_id"] for row in c.fetchall()}

    for t in tasks:
        t["completed_today"] = t["id"] in done_today_ids

    stats = calculate_stats(db, user_id)
    badges = list_user_badges(db, user_id)

    recent = list_recent_task_logs(db, user_id, limit=12)
    recent_logs = []
    for x in recent:
        title = x.get("title")
        i18n_json = x.get("i18n_json")
        if i18n_json:
            try:
                m = json.loads(i18n_json)
                if isinstance(m, dict):
                    title = m.get(locale) or m.get("en") or title
            except Exception:
                pass
        recent_logs.append({"date": x.get("date"), "title": title, "points": x.get("points")})

    next_rewards = list_next_rewards(db, user_id, limit=3)
    challenges = list_challenges(db)
    joined_ids = list_user_challenge_ids(db, user_id)
    challenge_rows = []
    for ch in challenges:
        challenge_rows.append(
            {
                "id": ch["id"],
                "code": ch["code"],
                "title": ch["title"],
                "description": ch.get("description"),
                "start_date": ch["start_date"],
                "end_date": ch["end_date"],
                "status": ch["status"],
                "joined": int(ch["id"]) in joined_ids,
            }
        )
    rewards = list_rewards(db)
    feed = list_feed(db, limit=20)
    return {
        "tasks": tasks,
        "stats": stats,
        "badges": badges,
        "recent_logs": recent_logs,
        "next_rewards": next_rewards,
        "challenges": challenge_rows,
        "rewards": rewards,
        "feed": feed,
    }


# 完成任务（打卡）
@router.post("/api/complete")
def complete_task(
    body: CompleteTaskRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    x_telegram_init_data: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    ip = _client_ip(request)
    _rate_limit_or_429(db, ip=ip, key="api:complete", limit=60)
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        body.user_id = int(u["telegram_id"])
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    if body.user_id is None:
        return {"ok": False, "reason": "Missing user_id"}
    c = db.cursor()
    today_str = get_today_str()

    _rate_limit_or_429(db, ip=ip, key=f"api:complete:user:{int(body.user_id)}", limit=30)

    c.execute("SELECT id FROM tasks WHERE id = ?;", (body.task_id,))
    if c.fetchone() is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # 检查当天是否已完成过
    c.execute(
        """
        SELECT id FROM user_task_logs
        WHERE user_id = ? AND task_id = ? AND date = ?;
        """,
        (int(body.user_id), body.task_id, today_str),
    )
    if c.fetchone() is not None:
        log_system_event(
            db,
            level="info",
            event="task_complete_duplicate",
            message=f"user={body.user_id} task={body.task_id}",
        )
        return {"ok": True, "duplicate": True}

    # 插入记录
    c.execute(
        """
        INSERT INTO user_task_logs (user_id, task_id, date, created_at)
        VALUES (?, ?, ?, ?);
        """,
        (body.user_id, body.task_id, today_str, datetime.utcnow().isoformat()),
    )
    db.commit()

    # 查任务标题用于提示
    c.execute("SELECT title FROM tasks WHERE id = ?;", (body.task_id,))
    row = c.fetchone()
    task_title = row["title"] if row else "绿色任务"

    # 后台给用户发一条打卡成功消息
    msg = f"✅ 你已完成今天的绿色任务：{task_title}"
    background_tasks.add_task(send_telegram_message, body.user_id, msg)
    log_system_event(
        db,
        level="info",
        event="task_completed",
        message=f"user={body.user_id} task={body.task_id}",
    )
    try:
        add_feed_event(db, int(body.user_id), "task_completed", f"✅ 完成任务：{task_title}")
    except Exception:
        pass

    newly_unlocked = unlock_eligible_badges(db, body.user_id)
    if newly_unlocked:
        titles = "、".join([x["title"] for x in newly_unlocked])
        background_tasks.add_task(
            send_telegram_message,
            body.user_id,
            f"🏅 解锁新徽章：{titles}\n去「LeafPass」看看你的绿色档案吧。",
        )
        background_tasks.add_task(
            send_monitor_message,
            f"🏅 徽章解锁\nuser: {body.user_id}\nbadges: {', '.join([x['code'] for x in newly_unlocked])}\n来源：/api/complete",
        )
        log_system_event(
            db,
            level="info",
            event="badge_unlocked",
            message=f"user={body.user_id} badges={','.join([x['code'] for x in newly_unlocked])}",
        )

    return {"ok": True, "duplicate": False, "new_badges": newly_unlocked}


@router.post("/api/challenges/join")
def api_join_challenge(
    request: Request,
    body: dict,
    x_telegram_init_data: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    ip = _client_ip(request)
    _rate_limit_or_429(db, ip=ip, key="api:challenges:join", limit=30)
    user_id = int(body.get("user_id") or 0)
    challenge_id = int(body.get("challenge_id") or 0)
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        user_id = int(u["telegram_id"])
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    if not user_id or not challenge_id:
        raise HTTPException(status_code=400, detail="Missing user_id/challenge_id")
    join_challenge(db, challenge_id, user_id)
    try:
        add_feed_event(db, user_id, "challenge_joined", f"🎯 加入挑战：{challenge_id}")
    except Exception:
        pass
    return {"ok": True}


@router.get("/api/challenges/{challenge_id}/leaderboard")
def api_challenge_leaderboard(
    request: Request,
    challenge_id: int,
    limit: int = 50,
    db: sqlite3.Connection = Depends(get_db),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="api:challenges:leaderboard", limit=120)
    return {"rows": challenge_leaderboard(db, int(challenge_id), limit=int(limit))}


@router.post("/api/feed/like")
def api_feed_like(
    request: Request,
    body: dict,
    x_telegram_init_data: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="api:feed:like", limit=120)
    user_id = int(body.get("user_id") or 0)
    feed_id = int(body.get("feed_id") or 0)
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        user_id = int(u["telegram_id"])
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    if not user_id or not feed_id:
        raise HTTPException(status_code=400, detail="Missing user_id/feed_id")
    like_feed(db, feed_id, user_id)
    return {"ok": True}


@router.post("/api/feed/comment")
def api_feed_comment(
    request: Request,
    body: dict,
    x_telegram_init_data: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="api:feed:comment", limit=60)
    user_id = int(body.get("user_id") or 0)
    feed_id = int(body.get("feed_id") or 0)
    text = (body.get("text") or "").strip()
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        user_id = int(u["telegram_id"])
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    if not user_id or not feed_id or not text:
        raise HTTPException(status_code=400, detail="Missing user_id/feed_id/text")
    comment_feed(db, feed_id, user_id, text)
    return {"ok": True}


@router.post("/api/rewards/redeem")
def api_redeem_reward(
    request: Request,
    body: dict,
    x_telegram_init_data: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="api:rewards:redeem", limit=20)
    user_id = int(body.get("user_id") or 0)
    reward_id = int(body.get("reward_id") or 0)
    note = (body.get("note") or "").strip()
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        user_id = int(u["telegram_id"])
    elif REQUIRE_TG_INIT_DATA:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    if not user_id or not reward_id:
        raise HTTPException(status_code=400, detail="Missing user_id/reward_id")
    rid = create_redemption(db, reward_id, user_id, note=note)
    try:
        add_feed_event(db, user_id, "reward_redeem", f"🎁 提交兑换申请：reward={reward_id}")
    except Exception:
        pass
    return {"ok": True, "id": rid}


@router.get("/api/admin/logs")
def admin_logs(
    request: Request,
    limit: int = 100,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:logs", limit=120)
    return {"logs": list_system_logs(db, limit=int(limit))}


@router.get("/api/admin/tasks")
def admin_list_tasks(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:tasks", limit=120)
    c = db.cursor()
    c.execute("SELECT id, title, points, i18n_json FROM tasks ORDER BY id ASC;")
    return {"tasks": [dict(r) for r in c.fetchall()]}


@router.post("/api/admin/tasks")
def admin_create_task(
    request: Request,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:tasks:write", limit=60)
    title = (body.get("title") or "").strip()
    points = int(body.get("points") or 0)
    if not title:
        return {"ok": False, "reason": "Missing title"}
    c = db.cursor()
    c.execute("INSERT INTO tasks (title, points) VALUES (?, ?);", (title, points))
    db.commit()
    return {"ok": True, "task_id": c.lastrowid}


@router.put("/api/admin/tasks/{task_id}")
def admin_update_task(
    task_id: int,
    request: Request,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:tasks:write", limit=60)
    title = (body.get("title") or "").strip()
    points = int(body.get("points") or 0)
    c = db.cursor()
    c.execute("UPDATE tasks SET title = ?, points = ? WHERE id = ?;", (title, points, task_id))
    db.commit()
    return {"ok": True}


@router.delete("/api/admin/tasks/{task_id}")
def admin_delete_task(
    task_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:tasks:write", limit=60)
    c = db.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
    db.commit()
    return {"ok": True}


@router.get("/api/admin/users")
def admin_list_users(
    request: Request,
    limit: int = 100,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:users", limit=120)
    c = db.cursor()
    c.execute(
        """
        SELECT u.id, u.name, u.created_at,
               COALESCE(SUM(t.points), 0) AS total_points,
               COALESCE(COUNT(l.id), 0) AS total_completions
        FROM users u
        LEFT JOIN user_task_logs l ON l.user_id = u.id
        LEFT JOIN tasks t ON t.id = l.task_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        LIMIT ?;
        """,
        (int(limit),),
    )
    return {"users": [dict(r) for r in c.fetchall()]}


@router.get("/api/admin/users/{user_id}")
def admin_user_detail(
    user_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:user_detail", limit=120)
    c = db.cursor()
    c.execute("SELECT id, name, created_at FROM users WHERE id = ?;", (user_id,))
    u = c.fetchone()
    if not u:
        return {"ok": False, "reason": "User not found"}
    stats = calculate_stats(db, user_id)
    badges = list_user_badges(db, user_id)
    return {"ok": True, "user": dict(u), "stats": stats, "badges": badges}


@router.get("/api/admin/badges")
def admin_list_badges(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:badges", limit=120)
    c = db.cursor()
    c.execute(
        """
        SELECT b.code, b.title, b.description, b.rule_type, b.threshold,
               (SELECT COUNT(*) FROM user_badges ub WHERE ub.badge_code = b.code) AS unlocked_count
        FROM badges b
        ORDER BY b.id ASC;
        """
    )
    return {"badges": [dict(r) for r in c.fetchall()]}


@router.get("/api/admin/challenges")
def admin_list_challenges(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:challenges", limit=120)
    c = db.cursor()
    c.execute(
        """
        SELECT id, code, title, description, start_date, end_date, status, created_at
        FROM challenges
        ORDER BY id DESC;
        """
    )
    challenges = [dict(r) for r in c.fetchall()]
    for ch in challenges:
        c.execute(
            """
            SELECT ct.task_id AS task_id, t.title AS title, t.points AS points
            FROM challenge_tasks ct
            JOIN tasks t ON t.id = ct.task_id
            WHERE ct.challenge_id = ?
            ORDER BY ct.task_id ASC;
            """,
            (int(ch["id"]),),
        )
        ch["tasks"] = [dict(r) for r in c.fetchall()]
        c.execute("SELECT COUNT(*) AS cnt FROM challenge_participants WHERE challenge_id = ?;", (int(ch["id"]),))
        ch["participants"] = c.fetchone()["cnt"] or 0
    return {"challenges": challenges}


@router.post("/api/admin/challenges")
def admin_create_challenge(
    request: Request,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:challenges:write", limit=60)
    code = (body.get("code") or "").strip()
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    start_date = (body.get("start_date") or "").strip()
    end_date = (body.get("end_date") or "").strip()
    status = (body.get("status") or "draft").strip()
    if not (code and title and start_date and end_date):
        raise HTTPException(status_code=400, detail="Missing fields")
    c = db.cursor()
    c.execute(
        """
        INSERT INTO challenges (code, title, description, start_date, end_date, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (code, title, description, start_date, end_date, status, datetime.utcnow().isoformat()),
    )
    db.commit()
    return {"ok": True, "id": c.lastrowid}


@router.post("/api/admin/challenges/{challenge_id}/tasks")
def admin_set_challenge_tasks(
    challenge_id: int,
    request: Request,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:challenges:write", limit=60)
    task_ids = body.get("task_ids") or []
    if not isinstance(task_ids, list):
        raise HTTPException(status_code=400, detail="task_ids must be list")
    ids = [int(x) for x in task_ids if str(x).strip().isdigit()]
    c = db.cursor()
    c.execute("DELETE FROM challenge_tasks WHERE challenge_id = ?;", (int(challenge_id),))
    for tid in ids:
        c.execute(
            "INSERT OR IGNORE INTO challenge_tasks (challenge_id, task_id) VALUES (?, ?);",
            (int(challenge_id), int(tid)),
        )
    db.commit()
    return {"ok": True}


@router.get("/api/admin/rewards")
def admin_list_rewards(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:rewards", limit=120)
    c = db.cursor()
    c.execute(
        """
        SELECT id, code, title, description, cost_points, status, created_at
        FROM rewards
        ORDER BY id DESC;
        """
    )
    return {"rewards": [dict(r) for r in c.fetchall()]}


@router.post("/api/admin/rewards")
def admin_create_reward(
    request: Request,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:rewards:write", limit=60)
    code = (body.get("code") or "").strip()
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    cost_points = int(body.get("cost_points") or 0)
    status = (body.get("status") or "active").strip()
    if not (code and title and cost_points > 0):
        raise HTTPException(status_code=400, detail="Missing fields")
    c = db.cursor()
    c.execute(
        """
        INSERT INTO rewards (code, title, description, cost_points, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (code, title, description, int(cost_points), status, datetime.utcnow().isoformat()),
    )
    db.commit()
    return {"ok": True, "id": c.lastrowid}


@router.get("/api/admin/redemptions")
def admin_list_redemptions(
    request: Request,
    limit: int = 200,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:redemptions", limit=120)
    c = db.cursor()
    c.execute(
        """
        SELECT rr.id, rr.status, rr.note, rr.created_at,
               rr.user_id, u.name AS user_name,
               rr.reward_id, r.title AS reward_title, r.cost_points AS cost_points
        FROM reward_redemptions rr
        LEFT JOIN users u ON u.id = rr.user_id
        LEFT JOIN rewards r ON r.id = rr.reward_id
        ORDER BY rr.id DESC
        LIMIT ?;
        """,
        (int(limit),),
    )
    return {"redemptions": [dict(r) for r in c.fetchall()]}


@router.post("/api/admin/redemptions/{redemption_id}")
def admin_update_redemption(
    redemption_id: int,
    request: Request,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:redemptions:write", limit=60)
    status = (body.get("status") or "").strip()
    note = (body.get("note") or "").strip()
    if status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    c = db.cursor()
    c.execute(
        "UPDATE reward_redemptions SET status = ?, note = ? WHERE id = ?;",
        (status, note[:255], int(redemption_id)),
    )
    db.commit()
    return {"ok": True}


# 管理侧：每日统计
@router.get("/api/admin/daily-stats")
def daily_stats(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _auth: None = Depends(admin_auth),
):
    _rate_limit_or_429(db, ip=_client_ip(request), key="admin:daily_stats", limit=120)
    c = db.cursor()
    today = get_today_str()

    # 今日活跃用户数
    c.execute(
        """
        SELECT COUNT(DISTINCT user_id) AS cnt
        FROM user_task_logs
        WHERE date = ?;
        """,
        (today,),
    )
    active_today = c.fetchone()["cnt"] or 0

    # 总用户数
    c.execute("SELECT COUNT(*) AS cnt FROM users;")
    total_users = c.fetchone()["cnt"] or 0

    # 今日新用户（按 created_at 日期粗略统计）
    c.execute(
        """
        SELECT COUNT(*) AS cnt FROM users
        WHERE DATE(created_at) = DATE('now');
        """
    )
    new_today = c.fetchone()["cnt"] or 0

    # 今日任务完成次数
    c.execute(
        """
        SELECT COUNT(*) AS cnt FROM user_task_logs
        WHERE date = ?;
        """,
        (today,),
    )
    completions_today = c.fetchone()["cnt"] or 0

    return {
        "date": today,
        "active_today": active_today,
        "new_today": new_today,
        "completions_today": completions_today,
        "total_users": total_users,
    }
