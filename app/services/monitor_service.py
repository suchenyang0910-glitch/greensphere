import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TG_MONITOR_BOT_TOKEN")
)
CHAT_ID = (
    os.getenv("TELEGRAM_MONITOR_CHAT_ID")
    or os.getenv("TG_MONITOR_CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def notify_monitor(message: str):
    if not BOT_TOKEN or not CHAT_ID:
        return

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        requests.post(TELEGRAM_API, json=payload, timeout=5)
    except Exception as e:
        print("Telegram notify failed:", e)