import argparse
import json
import os
import time
import hmac
import hashlib
import urllib.parse
from datetime import datetime

import requests


def normalize_lang(code: str) -> str:
    v = (code or "").lower()
    if v.startswith("zh"):
        return "zh"
    if v.startswith("th"):
        return "th"
    if v.startswith("vi"):
        return "vi"
    if v.startswith("km") or v.startswith("kh"):
        return "km"
    return "en"


def build_telegram_init_data(*, bot_token: str, user_id: int, language_code: str) -> str:
    user = {"id": int(user_id), "username": f"u{user_id}", "language_code": language_code}
    data = {
        "auth_date": str(int(time.time())),
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
        "query_id": "AAEAAAEAAAE",
    }
    pairs = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(pairs)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    data["hash"] = calculated_hash
    return urllib.parse.urlencode(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--user-id", type=int, default=10001)
    ap.add_argument("--lang", default="zh-CN", help="zh-CN/th/vi/km/en etc.")
    ap.add_argument("--use-telegram-init-data", action="store_true")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    lang = normalize_lang(args.lang)

    headers = {"X-GS-Lang": lang}
    if args.use_telegram_init_data:
        bot_token = (os.getenv("TG_COMMUNITY_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
        if not bot_token:
            raise SystemExit("Missing TG_COMMUNITY_BOT_TOKEN/TELEGRAM_BOT_TOKEN for initData generation")
        init_data = build_telegram_init_data(bot_token=bot_token, user_id=args.user_id, language_code=lang)
        headers["X-Telegram-Init-Data"] = init_data

    s = requests.Session()

    r = s.get(f"{base}/", headers={"Accept-Language": args.lang})
    print("GET /", r.status_code, len(r.text))
    if r.status_code != 200:
        return 2

    r = s.get(f"{base}/app")
    print("GET /app", r.status_code, len(r.text))
    if r.status_code != 200:
        return 2

    r = s.post(
        f"{base}/api/init_user",
        headers={**headers, "Content-Type": "application/json"},
        json={"telegram_id": args.user_id, "username": f"User{args.user_id}"},
        timeout=10,
    )
    print("POST /api/init_user", r.status_code, r.text[:200])
    if r.status_code != 200:
        return 3
    user_id = r.json().get("user_id")

    r = s.get(f"{base}/api/tasks", params={"user_id": user_id}, headers=headers, timeout=10)
    print("GET /api/tasks", r.status_code)
    if r.status_code != 200:
        return 3
    data = r.json()
    tasks = data.get("tasks") or []
    if not tasks:
        print("No tasks returned")
        return 4

    first = tasks[0]
    r = s.post(
        f"{base}/api/complete",
        headers={**headers, "Content-Type": "application/json"},
        json={"user_id": user_id, "task_id": int(first["id"])},
        timeout=10,
    )
    print("POST /api/complete", r.status_code, r.text[:240])
    if r.status_code not in (200, 429):
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

