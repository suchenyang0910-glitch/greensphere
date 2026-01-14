import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_COMMUNITY_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id: int, text: str):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(f"{API_URL}/sendMessage", json=payload)


def send_welcome(user):
    official_url = (os.getenv("GS_OFFICIAL_CHANNEL_URL") or "").strip()
    community_url = (os.getenv("GS_COMMUNITY_GROUP_URL") or "").strip()
    links = ""
    if official_url:
        links += f"\n📢 官方频道：{official_url}"
    if community_url:
        links += f"\n💬 社区群组：{community_url}"
    text = (
        "🌱 <b>欢迎来到 GreenSphere™</b>\n\n"
        "这是一个记录真实绿色行为、连接东南亚制造业与个人的绿色影响网络。\n\n"
        "👉 你可以从这里开始：\n"
        "• 加入 Waitlist\n"
        "• 关注官方频道\n"
        "• 成为首批 Pioneer\n\n"
        + (links or "📢 官方频道：@GreenSphere_Official\n💬 社区群组：@GreenSphere_Community")
    )
    send_message(user["telegram_id"], text)
