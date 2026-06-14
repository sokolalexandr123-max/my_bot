import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"

# Временные хранилища (в оперативной памяти)
user_levels = {}
username_to_id = {}  # База для связи юзернейма с ID пользователя

# Функция, которая запоминает людей, когда они пишут в чат
async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user and user.username:
        # Сохраняем юзернейм в нижнем регистре без знака @ для удобства поиска
        username_to_id[user.username.lower()] = user.id

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        target_user_id = None
        target_user_name = "Пользователь"
        level = None

        # === ВАРИАНТ 1: Команда отправлена ответом на сообщение ===
        if update.message.reply_to_message:
            if not context.args:
                await update.message.reply_text("❌ Напиши уровень: /setlvl 5")
                return
            
            try:
                level = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Уровень должен быть числом, бро")
                return
            
            target_user = update.message.reply_to_message.from_user
            target_user_id = target_user.id
            target_user_name = target_user.first_name

        # === ВАРИАНТ 2: Команда отправлена через @user [уровень] ===
        else:
            if len(context.args) < 2:
                await update.message.reply_text("❌ Используй: `/setlvl @username 5` или ответь командой на сообщение!")
                return
            
            # Очищаем юзернейм от @ и переводим в нижний регистр
            username_arg = context.args[0].replace("@", "").lower()
            
            try:
                level = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Уровень должен быть числом, бро")
                return
            
            # Ищем ID пользователя в нашей базе кэша
            if username_arg in username_to_id:
                target_user_id = username_to_id[username_arg]
                # Пытаемся узнать его имя в чате для красивого вывода
                try:
                    chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=target_user_id)
                    target_user_name = chat_member.user.first_name
                except:
                    target_user_name = f"@{username_arg}"
            else:
                await update.message.reply_text(
                    f"❌ Я пока не знаю пользователя @{username_arg}.\n"
                    f"Ему нужно написать хотя бы одно сообщение в чат, чтобы я его запомнил, "
                    f"либо используй команду ответом на его сообщение!"
                )
                return

        # === ОБЩАЯ ПРОВЕРКА НА ДИАПАЗОН (ОТ 5 ДО 20) ===
        if level < 5 or level > 20:
            await update.message.reply_text("❌ Ошибка! Можно устанавливать только уровни от 5 до 20, бро.")
            return

        title = f"{level} лвл"
        
        # Сохраняем уровень пользователя
        user_levels[target_user_id] = level
        
        # Удаляем саму команду админа для чистоты чата
        try:
            await update.message.delete()
        except:
            pass
        
        # === ВЫДАЧА ПРАВ И ТЕГА ===
        try:
            await context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=target_user_id,
                can_manage_chat=True,
                can_invite_users=True
            )
            
            await asyncio.sleep(1)
            
            await context.bot.set_chat_administrator_custom_title(
                chat_id=chat_id,
                user_id=target_user_id,
                custom_title=title
            )
            tag_status = "✅ Тег успешно установлен!"
        except Exception as e:
            tag_status = f"⚠️ Уровень изменен, но тег не повесился. Ошибка: {e}"

        # Отправляем анонс в чат
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎉 *{target_user_name}* 🎉\n\n"
                 f"Твой новый статус: *{title}*! 🔥\n\n"
                 f"_{tag_status}_",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Системная ошибка: {e}")

async def my_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    level = user_levels.get(user_id, 1)
    
    await update.message.reply_text(
        f"📊 Твой уровень: *{level} лвл*",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Хэндлер для отслеживания сообщений (чтобы знать юзернеймы)
    # filters.TEXT & ~filters.COMMAND означает: ловим обычный текст, игнорируем команды
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_users))
    
    app.add_handler(CommandHandler("setlvl", set_level))
    app.add_handler(CommandHandler("my_level", my_level))
    
    print("🤖 Бот запущен! Поддерживает два формата ввода и ограничение 5-20.")
    app.run_polling()

if __name__ == "__main__":
    main()
