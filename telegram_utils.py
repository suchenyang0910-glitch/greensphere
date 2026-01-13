# telegram_utils.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

COMMUNITY_BOT_TOKEN = os.getenv("TG_COMMUNITY_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
MONITOR_BOT_TOKEN = os.getenv("TG_MONITOR_BOT_TOKEN") or os.getenv("TELEGRAM_MONITOR_BOT_TOKEN")
MONITOR_CHAT_ID = os.getenv("TG_MONITOR_CHAT_ID") or os.getenv("TELEGRAM_MONITOR_CHAT_ID")

COMMUNITY_API_BASE = (
    f"https://api.telegram.org/bot{COMMUNITY_BOT_TOKEN}" if COMMUNITY_BOT_TOKEN else None
)
MONITOR_API_BASE = f"https://api.telegram.org/bot{MONITOR_BOT_TOKEN}" if MONITOR_BOT_TOKEN else None


async def send_telegram_message(chat_id: int, text: str) -> None:
    """
    调用 Telegram Bot API 给指定 chat_id 发消息。
    chat_id 对于私聊场景 == 用户的 telegram_id。
    """
    if not COMMUNITY_API_BASE:
        # 没配置 token 时静默跳过
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{COMMUNITY_API_BASE}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
    except Exception:
        # 忽略发送失败，避免影响主流程
        pass


async def send_monitor_message(text: str) -> None:
    if not (MONITOR_API_BASE and MONITOR_CHAT_ID):
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{MONITOR_API_BASE}/sendMessage",
                json={"chat_id": int(MONITOR_CHAT_ID), "text": text},
            )
    except Exception:
        pass
