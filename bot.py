import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 加载 .env 中的 TELEGRAM_BOT_TOKEN
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

WEBAPP_URL = "https://app.greensphere.world/"

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment (.env)")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("打开 GreenSphere 小程序", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("欢迎来到 GreenSphere 🌱", reply_markup=reply_markup)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()

