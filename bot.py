import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 加载 .env 中的 TELEGRAM_BOT_TOKEN
load_dotenv()
BOT_TOKEN = os.getenv("TG_COMMUNITY_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

WEBAPP_URL = os.getenv("GS_WEBAPP_URL", "https://greensphere.world/app")
OFFICIAL_CHANNEL_URL = os.getenv("GS_OFFICIAL_CHANNEL_URL", "https://t.me/GreenSphere_Official")
COMMUNITY_GROUP_URL = os.getenv("GS_COMMUNITY_GROUP_URL", "https://t.me/GreenSphere_Community")


if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment (.env)")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("打开 GreenSphere 小程序", web_app=WebAppInfo(url=WEBAPP_URL))],
        [
            InlineKeyboardButton("官方频道", url=OFFICIAL_CHANNEL_URL),
            InlineKeyboardButton("社区群组", url=COMMUNITY_GROUP_URL),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "欢迎来到 GreenSphere 🌱\n\n在这里你可以用每日小任务，积累自己的绿色档案与 LeafPass 徽章。",
        reply_markup=reply_markup,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "可用命令：\n"
        "/start 打开 WebApp\n"
        "/help 帮助\n\n"
        "提示：在 WebApp 里完成任务会获得 G-Points 与 Streak。"
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.run_polling()

if __name__ == "__main__":
    main()

