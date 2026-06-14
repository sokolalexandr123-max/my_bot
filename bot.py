import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"

# Временное хранилище уровней (в памяти)
user_levels = {}

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение пользователя и напиши /setlvl [уровень]")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Напиши уровень: /setlvl 5")
            return
        
        level = int(context.args[0])
        
        # === ПРОВЕРКА НА ДИАПАЗОН (ОТ 5 ДО 20) ===
        if level < 5 or level > 20:
            await update.message.reply_text("❌ Ошибка! Можно устанавливать только уровни от 5 до 20, бро.")
            return
            
        target_user = update.message.reply_to_message.from_user
        title = f"{level} лвл"
        
        # Сохраняем уровень пользователя
        user_levels[target_user.id] = level
        
        # Удаляем саму команду админа для чистоты чата
        try:
            await update.message.delete()
        except:
            pass
        
        # === ВЫДАЧА ПРАВ И ТЕГА В ТЕКУЩЕМ ЧАТЕ ===
        try:
            await context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=target_user.id,
                can_manage_chat=True,
                can_invite_users=True
            )
            
            await asyncio.sleep(1)
            
            await context.bot.set_chat_administrator_custom_title(
                chat_id=chat_id,
                user_id=target_user.id,
                custom_title=title
            )
            tag_status = "✅ Тег успешно установлен!"
        except Exception as e:
            tag_status = f"⚠️ Уровень изменен, но тег не повесился. Ошибка: {e}"

        # Отправляем анонс в тот же чат
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎉 *{target_user.first_name}* 🎉\n\n"
                 f"Твой новый статус: *{title}*! 🔥\n\n"
                 f"_{tag_status}_",
            parse_mode="Markdown"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Уровень должен быть числом, бро")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def my_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    level = user_levels.get(user_id, 1)
    
    await update.message.reply_text(
        f"📊 Твой уровень: *{level} лвл*",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("setlvl", set_level))
    app.add_handler(CommandHandler("my_level", my_level))
    print("🤖 Бот запущен! Включено ограничение на уровни от 5 до 20.")
    app.run_polling()

if __name__ == "__main__":
    main()
