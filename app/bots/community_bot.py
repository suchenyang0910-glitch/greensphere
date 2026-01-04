@bot.message_handler(commands=['leafpass'])
def leafpass_handler(message):
    telegram_id = message.from_user.id
    db = SessionLocal()

    status = get_leafpass_status(db, telegram_id)
    if not status:
        bot.reply_to(message, "🌱 你还没有 LeafPass，先完成一个绿色任务吧！")
        return

    text = f"""
🌿 *LeafPass 身份卡*

等级：*{status['level']} · {status['name']}*
积分：*{status['points']}*

"""

    if status["next"]:
        need = status["next"]["min"] - status["points"]
        text += f"🚀 距离 {status['next']['level']} 还差 *{need}* 分"
    else:
        text += "🏆 你已达到最高等级！"

    bot.reply_to(message, text, parse_mode="Markdown")