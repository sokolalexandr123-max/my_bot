from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"
GROUP_ID = -5014543190

LEVEL_TITLES = {
    1: "чепырка 🚗",
    3: "копейка 💨",
    5: "Логан 🔑",
    8: "Киа Рио 🔥",
    10: "вертолёт 🚁",
    15: "самолёт ✈️",
    20: "ракета 🚀",
}

def get_title(level: int) -> str:
    for lvl in sorted(LEVEL_TITLES.keys(), reverse=True):
        if level >= lvl:
            return LEVEL_TITLES[lvl]
    return LEVEL_TITLES.get(1, "новичок")

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Проверка reply
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение пользователя")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Напиши уровень: /setlvl 8")
            return
        
        level = int(context.args[0])
        target_user = update.message.reply_to_message.from_user
        title = get_title(level)
        
        # Пытаемся удалить команду
        try:
            await update.message.delete()
            print("✅ Команда удалена")
        except Exception as e:
            print(f"❌ Ошибка удаления: {e}")
        
        # Пытаемся сменить описание (тег)
        try:
            await context.bot.set_chat_administrator_custom_title(
                chat_id=GROUP_ID,
                user_id=target_user.id,
                custom_title=title
            )
            print(f"✅ Тег изменен на {title}")
        except Exception as e:
            print(f"❌ Ошибка смены тега: {e}")
            await update.message.reply_text(f"❌ Не могу сменить тег: {e}")
            return
        
        # Пытаемся отправить анонс
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"🎉 *{target_user.first_name}* 🎉\n\n"
                     f"Ого, уже уровень {level}!\n"
                     f"Теперь ты *{title}*, а не чепырка! 🔥",
                parse_mode="Markdown"
            )
            print("✅ Анонс отправлен")
        except Exception as e:
            print(f"❌ Ошибка отправки анонса: {e}")
            await update.message.reply_text(f"❌ Не могу отправить анонс: {e}")
        
    except ValueError:
        await update.message.reply_text("❌ Уровень должен быть числом")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        print(f"❌ Общая ошибка: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("setlvl", set_level))
    print("🤖 Бот запущен (отладочная версия)")
    app.run_polling()

if __name__ == "__main__":
    main()
