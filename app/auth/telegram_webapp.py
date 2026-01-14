import os, hmac, hashlib, urllib.parse
from fastapi import HTTPException

def _get_bot_tokens() -> list[str]:
    raw = (os.getenv("TG_WEBAPP_BOT_TOKENS") or "").strip()
    tokens: list[str] = []
    if raw:
        for part in raw.replace(";", ",").split(","):
            t = part.strip()
            if t:
                tokens.append(t)
    for key in [
        "TG_WEBAPP_BOT_TOKEN",
        "TG_OFFICIAL_BOT_TOKEN",
        "TG_COMMUNITY_BOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "TG_MONITOR_BOT_TOKEN",
    ]:
        v = (os.getenv(key) or "").strip()
        if v:
            tokens.append(v)
    deduped: list[str] = []
    seen = set()
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        deduped.append(t)
    return deduped


def _get_initdata_max_age_seconds() -> int:
    raw = (os.getenv("TG_INITDATA_MAX_AGE_SECONDS") or "").strip()
    if not raw:
        return 0
    try:
        v = int(raw)
        return v if v > 0 else 0
    except Exception:
        return 0

def verify_init_data(init_data: str, bot_token: str) -> dict:
    init_data = (init_data or "").lstrip("?").strip()
    data = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
    if "hash" not in data:
        raise HTTPException(status_code=401, detail="initData missing hash")

    received_hash = data.pop("hash")
    pairs = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(pairs)

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="initData signature invalid")

    max_age = _get_initdata_max_age_seconds()
    if max_age and "auth_date" in data:
        try:
            auth_date = int(data["auth_date"])
            import time
            if int(time.time()) - auth_date > max_age:
                raise HTTPException(status_code=401, detail="initData expired")
        except HTTPException:
            raise
        except Exception:
            pass

    # parse user JSON if present
    if "user" in data:
        import json
        try:
            data["user"] = json.loads(data["user"])
        except Exception:
            pass

    return data

def parse_telegram_user_from_init_data(init_data: str) -> dict:
    tokens = _get_bot_tokens()
    if not tokens:
        raise HTTPException(status_code=500, detail="Telegram bot token not set")

    payload = None
    for token in tokens:
        try:
            payload = verify_init_data(init_data, token)
            break
        except HTTPException as e:
            if e.status_code == 401 and e.detail == "initData signature invalid":
                continue
            raise
    if payload is None:
        raise HTTPException(status_code=401, detail="initData signature invalid")
    user = payload.get("user")
    if not isinstance(user, dict) or "id" not in user:
        raise HTTPException(status_code=401, detail="initData missing user.id")

    return {
        "telegram_id": int(user["id"]),
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
    }
