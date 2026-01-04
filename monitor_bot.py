import os
from dotenv import load_dotenv
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

MONITOR_BOT_TOKEN = os.getenv("TG_MONITOR_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TG_MONITOR_CHAT_ID")
API_BASE_URL = os.getenv("GS_API_BASE_URL", "http://127.0.0.1:8000")  # 也可以改成 https://app.greensphere.world

if not MONITOR_BOT_TOKEN:
    raise RuntimeError("TG_MONITOR_BOT_TOKEN not set in .env")

async def fetch_stats() -> dict:
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{API_BASE_URL}/api/admin/daily-stats")
        r.raise_for_status()
        return r.json()

def format_stats(data: dict) -> str:
    return (
        f"📊 GreenSphere 今日数据（{data.get('date')}）\n"
        f"- 新用户：{data.get('new_today')}\n"
        f"- 活跃用户：{data.get('active_today')}\n"
        f"- 完成任务次数：{data.get('completions_today')}\n"
        f"- 总用户数：{data.get('total_users')}\n"
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await fetch_stats()
    await update.message.reply_text(format_stats(data))

async def push_today_stats(app):
    """可供将来定时任务调用的推送函数"""
    if not ADMIN_CHAT_ID:
        return
    data = await fetch_stats()
    text = format_stats(data)
    await app.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=text)

def main():
    app = ApplicationBuilder().token(MONITOR_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", stats_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))

    app.run_polling()

if __name__ == "__main__":
    main()
