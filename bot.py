import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"

# Временное хранилище уровней (в памяти)
user_levels = {}
username_to_id = {}

# Хэндлер для отслеживания юзернеймов
async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user and user.username:
        username_to_id[user.username.lower()] = user.id

# === ФУНКЦИЯ ПРОВЕРКИ ПРАВ (Считывание из Telegram) ===
async def get_user_status(chat_id, user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status == "creator":
            return "owner"
        if member.custom_title and member.custom_title.strip().lower().startswith("прод."):
            return "producer"
    except:
        pass
    return "regular"

# === 👑 КОМАНДА: ДОБАВИТЬ ПРОДЮСЕРА (Только Создатель) ===
async def add_producer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        # СТРОГАЯ ПРОВЕРКА: Только Создатель чата
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status != "owner":
            await update.message.reply_text("❌ Ошибка! Назначать продюсеров может только Создатель чата 👑")
            return
            
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение пользователя и напиши `/addprod [Имя]`")
            return
            
        # Проверка лимита (до 10 продюсеров)
        try:
            admins = await context.bot.get_chat_administrators(chat_id=chat_id)
            current_producers = sum(1 for a in admins if a.custom_title and a.custom_title.strip().lower().startswith("прод."))
            
            if current_producers >= 10:
                await update.message.reply_text(f"❌ Лимит! В чате уже {current_producers} продюсеров из 10.")
                return
        except Exception as e:
            print(f"Ошибка подсчета: {e}")

        target_user = update.message.reply_to_message.from_user
        custom_name = " ".join(context.args) if context.args else "продюсер"
        title = f"прод. {custom_name}"
        
        if len(title) > 16:
            await update.message.reply_text("❌ Слишком длинное имя! Максимум 16 symbols.")
            return
            
        try:
            await update.message.delete()
        except:
            pass

        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id, can_manage_chat=True, can_invite_users=True
        )
        await asyncio.sleep(1)
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title=title
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎬 *{target_user.first_name}* назначен новым Продюсером чата!\n"
                 f"Его статус: *{title}* 💎",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при добавлении: {e}")

# === 👑 КОМАНДА: СНЯТЬ ПРОДЮСЕРА (Только Создатель) ===
async def delete_producer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        # СТРОГАЯ ПРОВЕРКА: Только Создатель чата
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status != "owner":
            await update.message.reply_text("❌ Ошибка! Снимать продюсеров с должности может только Создатель чата 👑")
            return
            
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение продюсера и напиши `/delprod` чтобы уволить его.")
            return
            
        target_user = update.message.reply_to_message.from_user
        
        # Проверяем, а продюсер ли он?
        target_status = await get_user_status(chat_id, target_user.id, context)
        if target_status != "producer":
            await update.message.reply_text("❌ Этот пользователь не является продюсеромチャタ.")
            return
            
        try:
            await update.message.delete()
        except:
            pass
            
        # Полностью снимаем админ-права (это автоматически сотрет тег "прод. ...")
        await context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=target_user.id,
            can_manage_chat=False
        )
        
        # Стираем его уровень из временной памяти бота, если он там был
        if target_user.id in user_levels:
            del user_levels[target_user.id]
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📉 *{target_user.first_name}* официально снят с должности Продюсера и лишен всех полномочий!",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при увольнении: {e}")

# === КОМАНДА: Смена уровня (/setlvl) ===
async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status not in ["owner", "producer"]:
            await update.message.reply_text("❌ Менять уровни могут только Продюсеры или Создатель чата.")
            return

        target_user_id = None
        target_user_name = "Пользователь"
        level = None

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
        else:
            if len(context.args) < 2:
                await update.message.reply_text("❌ Формат: `/setlvl @username 5` или `/setlvl [ID] 5`")
                return
            first_arg = context.args[0]
            try:
                level = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Уровень должен быть числом, бро")
                return

            if first_arg.isdigit():
                target_user_id = int(first_arg)
                try:
                    chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=target_user_id)
                    target_user_name = chat_member.user.first_name
                except:
                    await update.message.reply_text("❌ Юзер не найден в этом чате.")
                    return
            elif first_arg.startswith("@"):
                username_arg = first_arg.replace("@", "").lower()
                if username_arg in username_to_id:
                    target_user_id = username_to_id[username_arg]
                    try:
                        chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=target_user_id)
                        target_user_name = chat_member.user.first_name
                    except:
                        target_user_name = f"@{username_arg}"
                else:
                    await update.message.reply_text(f"❌ Я пока не знаю @{username_arg}. Пусть черканет в чат.")
                    return
            else:
                await update.message.reply_text("❌ Введи @юзернейм или цифровой ID!")
                return

        # Защита иерархии
        target_status = await get_user_status(chat_id, target_user_id, context)
        if sender_status == "producer" and target_status in ["owner", "producer"]:
            await update.message.reply_text("❌ Как продюсер, ты не можешь менять уровень Создателю или другим Продюсерам!")
            return

        if level < 5 or level > 20:
            await update.message.reply_text("❌ Можно устанавливать только уровни от 5 до 20, бро.")
            return

        title = f"{level} лвл"
        user_levels[target_user_id] = level
        
        try:
            await update.message.delete()
        except:
            pass
        
        try:
            await context.bot.promote_chat_member(
                chat_id=chat_id, user_id=target_user_id, can_manage_chat=True, can_invite_users=True
            )
            await asyncio.sleep(1)
            await context.bot.set_chat_administrator_custom_title(
                chat_id=chat_id, user_id=target_user_id, custom_title=title
            )
            tag_status = "✅ Тег успешно установлен!"
        except Exception as e:
            tag_status = f"⚠️ Уровень изменен, но тег не повесился. Ошибка: {e}"

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎉 *{target_user_name}* 🎉\n\n"
                 f"Твой новый статус: *{title}*! 🔥\n\n"
                 f"_{tag_status}_",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Системная ошибка: {e}")

# === КОМАНДА: Смена ника продюсера (/setname) ===
async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        user_status = await get_user_status(chat_id, user.id, context)
        if user_status not in ["owner", "producer"]:
            await update.message.reply_text("❌ Эта команда доступна только Продюсерам чата, бро!")
            return
            
        if not context.args:
            await update.message.reply_text("❌ Напиши имя после команды, например: `/setname DoReMi`")
            return
            
        custom_name = " ".join(context.args)
        title = f"прод. {custom_name}"
        
        if len(title) > 16:
            await update.message.reply_text(f"❌ Слишком длинно. Лимит — 16 символов.")
            return
            
        try:
            await update.message.delete()
        except:
            pass
            
        try:
            await context.bot.promote_chat_member(
                chat_id=chat_id, user_id=user.id, can_manage_chat=True, can_invite_users=True
            )
            await asyncio.sleep(1)
            await context.bot.set_chat_administrator_custom_title(
                chat_id=chat_id, user_id=user.id, custom_title=title
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎬 *{user.first_name}* обновил свой продюсерский статус:\n"
                     f"Теперь в чате ты: *{title}* 💎",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка смены тега: {e}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка в setname: {e}")

async def my_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    level = user_levels.get(user_id, 1)
    await update.message.reply_text(f"📊 Твой уровень: *{level} лвл*", parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_users))
    
    # Регистрация всех команд
    app.add_handler(CommandHandler("addprod", add_producer))
    app.add_handler(CommandHandler("delprod", delete_producer)) # Новая команда для увольнения!
    app.add_handler(CommandHandler("setlvl", set_level))
    app.add_handler(CommandHandler("setname", set_name))
    app.add_handler(CommandHandler("my_level", my_level))
    
    print("🤖 Бот запущен! Права управления продюсерами переданы Создателю чата.")
    app.run_polling()

if __name__ == "__main__":
    main()
