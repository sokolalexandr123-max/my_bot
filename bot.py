from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"
GROUP_ID = -1003705147912

async def test_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Пробуем новый метод (если он есть)
        if hasattr(context.bot, 'set_chat_member_tag'):
            await update.message.reply_text("✅ Метод set_chat_member_tag ПОДДЕРЖИВАЕТСЯ!")
        else:
            await update.message.reply_text("❌ Метод set_chat_member_tag НЕ поддерживается")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("test_tag", test_tag))
    print("Бот запущен. Напиши /test_tag")
    app.run_polling()

if __name__ == "__main__":
    main()
