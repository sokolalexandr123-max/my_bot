from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"
GROUP_ID = -1003705147912

async def test_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Проверяем наличие нового метода
        if hasattr(context.bot, 'set_chat_member_tag'):
            await update.message.reply_text("✅ Метод set_chat_member_tag ПОДДЕРЖИВАЕТСЯ!\n\nМожно делать теги без прав админа!")
        else:
            await update.message.reply_text("❌ Метод не найден. Будем использовать старый способ.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Временная заглушка, чтобы не падал
    await update.message.reply_text("Бот работает! Используй /test_tag для проверки тегов.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("test_tag", test_tag))
    app.add_handler(CommandHandler("setlvl", set_level))
    print("🤖 Бот запущен. Отключи privacy mode у бота через @BotFather!")
    app.run_polling()

if __name__ == "__main__":
    main()
