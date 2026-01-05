import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from gs_db import get_db

from models import CompleteTaskRequest, UserInitRequest, get_today_str, calculate_stats
from telegram_utils import send_telegram_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# 打卡 WebApp 页面（挂在 /app）
@router.get("/app", response_class=HTMLResponse)
def app_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



# 用户初始化：用 Telegram 用户建立/获取内部 user_id
@router.post("/api/init_user")
def init_user(body: UserInitRequest, db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    # 直接用 telegram_id 作为 users.id
    c.execute("SELECT id FROM users WHERE id = ?;", (body.telegram_id,))
    row = c.fetchone()

    if row is None:
        c.execute(
            "INSERT INTO users (id, name, created_at) VALUES (?, ?, datetime('now'));",
            (body.telegram_id, body.username or "Telegram User"),
        )
        db.commit()
        user_id = body.telegram_id
    else:
        user_id = row["id"]

    return {"user_id": user_id}


# 获取任务列表 + 今日完成情况 + 统计
@router.get("/api/tasks")
def get_tasks(user_id: int = 1, db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    # 所有任务
    c.execute("SELECT id, title, points FROM tasks;")
    tasks = [dict(row) for row in c.fetchall()]

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
    return {"tasks": tasks, "stats": stats}


# 完成任务（打卡）
@router.post("/api/complete")
def complete_task(
    body: CompleteTaskRequest,
    background_tasks: BackgroundTasks,
    db: sqlite3.Connection = Depends(get_db),
):
    c = db.cursor()
    today_str = get_today_str()

    # 检查当天是否已完成过
    c.execute(
        """
        SELECT id FROM user_task_logs
        WHERE user_id = ? AND task_id = ? AND date = ?;
        """,
        (body.user_id, body.task_id, today_str),
    )
    if c.fetchone() is not None:
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

    return {"ok": True, "duplicate": False}


# 管理侧：每日统计
@router.get("/api/admin/daily-stats")
def daily_stats(db: sqlite3.Connection = Depends(get_db)):
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
