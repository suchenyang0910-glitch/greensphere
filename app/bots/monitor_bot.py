import os
from dotenv import load_dotenv
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()
MONITOR_BOT_TOKEN = os.getenv("TELEGRAM_MONITOR_BOT_TOKEN")
API_BASE_URL = "http://127.0.0.1:8000"  # 上线后改成你的正式域名
ADMIN_CHAT_ID = int(os.getenv("GS_ADMIN_CHAT_ID", "0"))  # 你的 Telegram ID

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{API_BASE_URL}/api/admin/daily-stats")
        data = r.json()
    text = (
        f"📊 GreenSphere 今日数据（{data['date']}）\n"
        f"- 新用户：{data['new_today']}\n"
        f"- 活跃用户：{data['active_today']}\n"
        f"- 完成任务次数：{data['completions_today']}\n"
        f"- 总用户数：{data['total_users']}\n"
    )
    await update.message.reply_text(text)

async def push_today_stats(app):
    # 也可以写成每天定时推送给 ADMIN_CHAT_ID
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{API_BASE_URL}/api/admin/daily-stats")
        data = r.json()
    text = (
        f"📊 今日数据（{data['date']}）\n"
        f"- 新用户：{data['new_today']}\n"
        f"- 活跃用户：{data['active_today']}\n"
        f"- 完成任务次数：{data['completions_today']}\n"
        f"- 总用户数：{data['total_users']}\n"
    )
    if ADMIN_CHAT_ID:
        await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stats(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(MONITOR_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("stats", stats))
    app.run_polling()
