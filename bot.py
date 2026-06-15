import asyncio
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ⚠️ Вставь сюда токен своего бота от @BotFather
BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"
DATA_FILE = "levels.json"

username_to_id = {}
user_levels = {}
user_cars = {}  # Здесь хранятся кастомные тачки продюсеров

# 💾 СОВЕРШЕННАЯ ЛОГИКА СХРАНЕНИЯ (С ПОДДЕРЖКОЙ КАСТОМНЫХ ТАЧЕК)
def load_data():
    """Загрузка уровней и кастомных тачек из файла"""
    global user_levels, user_cars
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Проверяем структуру файла (новая комбинированная или старая плоская)
                if "levels" in data or "cars" in data:
                    levels = data.get("levels", {})
                    cars = data.get("cars", {})
                    user_levels = {int(k): v for k, v in levels.items()}
                    user_cars = {int(k): v for k, v in cars.items()}
                else:
                    # Старый формат: файл содержал только уровни
                    user_levels = {int(k): v for k, v in data.items()}
                    user_cars = {}
                return
        except Exception as e:
            print(f"❌ Ошибка загрузки данных: {e}")
    
    # Если файла нет, оставляем пустыми
    user_levels = {}
    user_cars = {}

def save_data():
    """Сохранение всех данных в один файл"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            combined_data = {
                "levels": user_levels,
                "cars": user_cars
            }
            json.dump(combined_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Ошибка записи данных: {e}")

# Загружаем базу данных при старте
load_data()

# 🏎️ СПИСОК СТАНДАРТНЫХ ТАЧЕК ПО УРОВНЯМ
CAR_RANKS = {
    5: "Чепырка (ВАЗ-2114)",
    6: "Приора",
    7: "Рено Логан",
    8: "Киа Рио / Хендай Солярис",
    9: "Шкода Октавия",
    10: "Тойота Камри 3.5",
    11: "БМВ Е39",
    12: "Мерседес C-Класс",
    13: "БМВ Х5",
    14: "Порше Кайен",
    15: "Гелик (Mercedes G-Class)",
    16: "Ауди R8",
    17: "Майбах (Maybach)",
    18: "Ламборгини / Феррари",
    19: "Бугатти Широн",
    20: "Роллс-Ройс Фантом"
}

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user and user.username:
        username_to_id[user.username.lower()] = user.id
    
    if update.message and update.message.text:
        bot_user = await context.bot.get_me()
        bot_username = bot_user.username.lower()
        
        if f"@{bot_username}" in update.message.text.lower():
            help_text = (
                "📋 *СПРАВКА ПО КОМАНДАМ БОТА*\n\n"
                "👑 *Только для Создателя чата:*\n"
                "• `/addprod [Имя]` (ответом) — назначить Продюсера. 🔥\n"
                "• `/delprod` (ответом) — снять Продюсера (авто-сброс на 5 lvl). 📉\n\n"
                "🎬 *Для Продюсеров и Создателя:*\n"
                "• `/setlvl [5-20]` (ответом, по @username или ID) — выдать уровень и тачку. 🏎️\n"
                "• `/setname [Имя]` — изменить своё продюсерское имя в теге. 💎\n"
                "• `/setcar [Название]` — поставить себе ЛЮБУЮ кастомную тачку! 🚀\n"
                "• `/clean` (ответом) — зачистить все права чела до базового 5 lvl. 🧹\n\n"
                "👥 *Для всех участников чата:*\n"
                "• `/my_level` — узнать свой уровень и тачку! 📊\n"
                "• Просто тегни меня (`@`), чтобы вызвать это меню! 🤖"
            )
            await update.message.reply_text(help_text, parse_mode="Markdown")

async def get_user_status(chat_id, user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status == "creator":
            return "owner"
        if member.custom_title and member.custom_title.strip().lower().startswith("прод"):
            return "producer"
    except:
        pass
    return "regular"

# ========================================================
# 1. КОМАНДА /addprod
# ========================================================
async def add_producer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status != "owner":
            await update.message.reply_text("❌ Ошибка! Назначать продюсеров может только Создатель чата 👑")
            return
            
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение пользователя и напиши `/addprod [Имя]`")
            return

        target_user = update.message.reply_to_message.from_user
        custom_name = " ".join(context.args) if context.args else target_user.first_name
        
        title = f"Прод {custom_name}"[:16]

        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id,
            can_manage_chat=True, can_delete_messages=True,
            can_restrict_members=True, can_invite_users=True, can_pin_messages=True
        )
        await asyncio.sleep(1)
        
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title=title
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎬 *{target_user.first_name}* назначен Продюсером чата!\nЕго статус: *{title}* 💎",
            parse_mode="Markdown"
        )
        
        try: await update.message.delete()
        except: pass

    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка Telegram API при добавлении продюсера:\n`{e}`\n\n"
            f"📌 **Чек-лист для исправления:**\n"
            f"1. Зайди в настройки группы -> Админы -> Нажми на бота и **включи ему ВСЕ тумблеры прав**.\n"
            f"2. Убедись, что юзер, на которого ты ответил — **обычный участник**.", 
            parse_mode="Markdown"
        )

# ========================================================
# 2. КОМАНДА /delprod 
# ========================================================
async def delete_producer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status != "owner":
            await update.message.reply_text("❌ Ошибка! Снимать продюсеров может только Создатель чата 👑")
            return
            
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение продюсера и напиши `/delprod`")
            return
            
        target_user = update.message.reply_to_message.from_user
            
        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id,
            can_manage_chat=True, can_change_info=False, can_delete_messages=False,
            can_restrict_members=False, can_invite_users=False, can_pin_messages=False,
            can_manage_video_chats=False, can_manage_topics=False
        )
        await asyncio.sleep(1)
        
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title="5 lvl"
        )
        user_levels[target_user.id] = 5
        # Удаляем кастомную тачку, если она была
        if target_user.id in user_cars:
            del user_cars[target_user.id]
        save_data()
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📉 *{target_user.first_name}* снят с должности Продюсера и автоматически переведен на *5 lvl*! 🎖️",
            parse_mode="Markdown"
        )
        
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при увольнении: `{e}`", parse_mode="Markdown")

# ========================================================
# 3. КОМАНДА /setlvl
# ========================================================
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
                    await update.message.reply_text(f"❌ Я пока не знаю @{username_arg}. Пусть черканет любое смс в чат.")
                    return

        target_status = await get_user_status(chat_id, target_user_id, context)
        if target_status == "owner":
            await update.message.reply_text("❌ Ошибка! Менять уровень Создателю чата строго запрещено.")
            return

        if level < 5 or level > 20:
            await update.message.reply_text("❌ Можно устанавливать только уровни от 5 до 20, бро.")
            return

        title = f"{level} lvl"
        user_levels[target_user_id] = level
        save_data()
        
        car_name = CAR_RANKS.get(level, "Неизвестное авто")
        
        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user_id, can_manage_chat=True
        )
        await asyncio.sleep(1)
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user_id, custom_title=title
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎉 *{target_user_name}* прокачал свой статус! 🎉\n\n📊 Новый уровень: *{title}*\n🏎️ Твоя новая тачка: *{car_name}* 🔥",
            parse_mode="Markdown"
        )
        
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось выдать уровень: `{e}`", parse_mode="Markdown")

# ========================================================
# 4. КОМАНДА /setcar (КАСТОМНАЯ ТАЧКА ДЛЯ АДМИНОВ)
# ========================================================
async def set_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        user_status = await get_user_status(chat_id, user.id, context)
        if user_status not in ["owner", "producer"]:
            await update.message.reply_text("❌ Эта команда доступна только Продюсерам и Создателю чата, бро!")
            return
            
        if not context.args:
            await update.message.reply_text("❌ Напиши название транспорта после команды, например: `/setcar Межгалактический Крейсер`")
            return
            
        custom_car = " ".join(context.args)
        user_cars[user.id] = custom_car
        save_data()
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚀 Продюсер *{user.first_name}* обновил свой личный транспорт!\nТеперь твой аппарат: *{custom_car}* 🔥",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка установки кастомной тачки: `{e}`", parse_mode="Markdown")

# ========================================================
# 5. КОМАНДА /clean 
# ========================================================
async def clean_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status not in ["owner", "producer"]:
            await update.message.reply_text("❌ Ошибка! Чистить права могут только Продюсеры или Создатель чата.")
            return
            
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение пользователя реплаем и напиши `/clean`")
            return
            
        target_user = update.message.reply_to_message.from_user
        target_status = await get_user_status(chat_id, target_user.id, context)
        if target_status == "owner":
            await update.message.reply_text("❌ Ошибка! Нельзя зачистить права Создателю чата.")
            return
            
        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id,
            can_manage_chat=True, can_change_info=False, can_delete_messages=False,
            can_restrict_members=False, can_invite_users=False, can_pin_messages=False,
            can_manage_video_chats=False, can_manage_topics=False
        )
        await asyncio.sleep(1)
        
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title="5 lvl"
        )
        user_levels[target_user.id] = 5
        if target_user.id in user_cars:
            del user_cars[target_user.id]
        save_data()
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🧹 Все административные права пользователя *{target_user.first_name}* аннулированы. Он сброшен до базового *5 lvl*.",
            parse_mode="Markdown"
        )
        
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при очистке: `{e}`", parse_mode="Markdown")

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
        title = f"Прод {custom_name}"[:16]
            
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=user.id, custom_title=title
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎬 *{user.first_name}* обновил свой продюсерский статус:\nТеперь в чате ты: *{title}* 💎",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка смены тега: `{e}`", parse_mode="Markdown")

async def my_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 🏎️ Проверяем, есть ли у пользователя кастомная тачка
    if user_id in user_cars:
        car_info = f"\n🏎️ Личный транспорт Продюсера: *{user_cars[user_id]}* 🔥"
        level_info = "Админ-статус"
    else:
        # Если кастомной нет, берем стандартный левел
        level = user_levels.get(user_id, 1)
        level_info = f"{level} lvl"
        if level in CAR_RANKS:
            car_info = f"\n🏎️ Твоя тачка в гараже: *{CAR_RANKS[level]}*"
        else:
            car_info = f"\n🚲 Пока гоняешь на велике, копи на Чепырку (нужен 5 lvl!)"

    await update.message.reply_text(
        f"📊 Твой текущий статус: *{level_info}*{car_info}", 
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_users))
    app.add_handler(CommandHandler("addprod", add_producer))
    app.add_handler(CommandHandler("delprod", delete_producer))
    app.add_handler(CommandHandler("setlvl", set_level))
    app.add_handler(CommandHandler("setname", set_name))
    app.add_handler(CommandHandler("setcar", set_car))
    app.add_handler(CommandHandler("clean", clean_user))
    app.add_handler(CommandHandler("my_level", my_level))
    
    print("🤖 Бот успешно запущен на стабильной конфигурации!")
    app.run_polling()

if __name__ == "__main__":
    main()
