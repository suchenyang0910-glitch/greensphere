import sqlite3
from datetime import datetime
import os
import json

from fastapi import APIRouter, Depends, BackgroundTasks, Request
from fastapi import Header
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from gs_db import get_db

from models import (
    CompleteTaskRequest,
    UserInitRequest,
    get_today_str,
    calculate_stats,
    list_user_badges,
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
        {"request": request},
        headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"},
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_index(request: Request):
    return templates.TemplateResponse(
        "admin.html",
        {"request": request},
        headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"},
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
            f"🆕 新用户注册\n- telegram_id: {body.telegram_id}\n- name: {body.username or 'Telegram User'}",
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
    return {"tasks": tasks, "stats": stats, "badges": badges}


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
            f"🏅 徽章解锁\n- user: {body.user_id}\n- badges: {', '.join([x['code'] for x in newly_unlocked])}",
        )
        log_system_event(
            db,
            level="info",
            event="badge_unlocked",
            message=f"user={body.user_id} badges={','.join([x['code'] for x in newly_unlocked])}",
        )

    return {"ok": True, "duplicate": False, "new_badges": newly_unlocked}


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
