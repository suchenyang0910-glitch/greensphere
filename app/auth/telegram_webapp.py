import os, hmac, hashlib, urllib.parse
from fastapi import HTTPException

def _get_bot_token() -> str:
    return (
        os.getenv("TG_COMMUNITY_BOT_TOKEN")
        or os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("TG_MONITOR_BOT_TOKEN")
        or ""
    ).strip()

def verify_init_data(init_data: str, bot_token: str) -> dict:
    data = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
    if "hash" not in data:
        raise HTTPException(status_code=401, detail="initData missing hash")

    received_hash = data.pop("hash")
    pairs = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(pairs)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash != received_hash:
        raise HTTPException(status_code=401, detail="initData signature invalid")

    # parse user JSON if present
    if "user" in data:
        import json
        try:
            data["user"] = json.loads(data["user"])
        except Exception:
            pass

    return data

def parse_telegram_user_from_init_data(init_data: str) -> dict:
    bot_token = _get_bot_token()
    if not bot_token:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not set")

    payload = verify_init_data(init_data, bot_token)
    user = payload.get("user")
    if not isinstance(user, dict) or "id" not in user:
        raise HTTPException(status_code=401, detail="initData missing user.id")

    return {
        "telegram_id": int(user["id"]),
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
    }
