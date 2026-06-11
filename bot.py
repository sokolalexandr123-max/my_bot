from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"
GROUP_ID = -1003705147912

LEVEL_TITLES = {
    1: "чепырка 🚗",
    3: "копейка 💨",
    5: "Логан 🔑",
    8: "Киа Рио 🔥",
    10: "вертолёт 🚁",
    15: "самолёт ✈️",
    20: "ракета 🚀",
}

# Хранилище уровней пользователей (в реальном проекте лучше использовать базу данных)
user_levels = {}

def get_title(level: int) -> str:
    for lvl in sorted(LEVEL_TITLES.keys(), reverse=True):
        if level >= lvl:
            return LEVEL_TITLES[lvl]
    return LEVEL_TITLES.get(1, "новичок")

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение пользователя и напиши /setlvl [уровень]")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Напиши уровень: /setlvl 8")
            return
        
        level = int(context.args[0])
        target_user = update.message.reply_to_message.from_user
        title = get_title(level)
        
        # Сохраняем уровень пользователя
        user_levels[target_user.id] = level
        
        # Удаляем команду
        try:
            await update.message.delete()
        except:
            pass
        
        # Отправляем анонс
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"🎉 *{target_user.first_name}* 🎉\n\n"
                 f"Ого, уже уровень {level}!\n"
                 f"Теперь ты *{title}*, а не чепырка! 🔥\n\n"
                 f"💡 Теперь другие могут узнать твой уровень командой:\n"
                 f"`/my_level`",
            parse_mode="Markdown"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Уровень должен быть числом, бро")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def my_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    level = user_levels.get(user_id, 1)
    title = get_title(level)
    
    await update.message.reply_text(
        f"📊 Твой уровень: *{level}*\n"
        f"🏆 Звание: *{title}*",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("setlvl", set_level))
    app.add_handler(CommandHandler("my_level", my_level))
    print("🤖 Бот запущен!\n"
          "📌 Команды:\n"
          "   /setlvl [уровень] - ответом на сообщение (только админы)\n"
          "   /my_level - узнать свой уровень")
    app.run_polling()

if __name__ == "__main__":
    main()
