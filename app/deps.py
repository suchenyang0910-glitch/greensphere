from fastapi import Header, HTTPException
from app.auth.telegram_webapp import parse_telegram_user_from_init_data

def get_telegram_id(
    x_telegram_init_data: str | None = Header(default=None),
    x_telegram_id: str | None = Header(default=None),
):
    # ✅ 优先：Telegram WebApp initData
    if x_telegram_init_data:
        u = parse_telegram_user_from_init_data(x_telegram_init_data)
        return int(u["telegram_id"])

    # ✅ 兜底：开发手动传 ID
    if not x_telegram_id:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data or X-Telegram-Id")

    try:
        return int(x_telegram_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Telegram-Id header")
