# telegram_utils.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None


async def send_telegram_message(chat_id: int, text: str) -> None:
    """
    调用 Telegram Bot API 给指定 chat_id 发消息。
    chat_id 对于私聊场景 == 用户的 telegram_id。
    """
    if not API_BASE:
        # 没配置 token 时静默跳过
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{API_BASE}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
    except Exception:
        # 忽略发送失败，避免影响主流程
        pass
