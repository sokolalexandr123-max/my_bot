import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ⚠️ Вставь сюда токен своего бота от @BotFather
BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"

user_levels = {}
username_to_id = {}

# 🏎️ СПИСОК ТАЧЕК ПО УРОВНЯМ
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

# Хэндлер для отслеживания юзернеймов + Реакция на упоминание @bot
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
                "• `/clean` (ответом) — зачистить все права чела до базового 5 lvl. 🧹\n\n"
                "👥 *Для всех участников чата:*\n"
                "• `/my_level` — узнать свой уровень и тачку! 📊\n"
                "• Просто тегни меня (`@`), чтобы вызвать это меню! 🤖"
            )
            await update.message.reply_text(help_text, parse_mode="Markdown")

# Универсальная функция проверки статуса (owner / producer / regular)
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
# 1. ОБНОВЛЕННАЯ КОМАНДА /addprod (Защита от Right_forbidden)
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
        
        # Автоматически обрезаем до 16 символов (лимит Telegram), чтобы не было ошибок длины
        title = f"Прод {custom_name}"[:16]

        # Выдаем ТОЛЬКО самые главные права модератора (без видеочатов и тем),
        # чтобы у бота гарантированно хватило собственных прав поделиться ими.
        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id,
            can_manage_chat=True, 
            can_delete_messages=True,    # Удаление сообщений
            can_restrict_members=True,   # Бан и мут
            can_invite_users=True,       # Пригласительные ссылки
            can_pin_messages=True        # Закрепление сообщений
        )
        await asyncio.sleep(1)
        
        # Установка плашки
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title=title
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎬 *{target_user.first_name}* назначен Продюсером чата!\n"
                 f"Его статус: *{title}* 💎",
            parse_mode="Markdown"
        )
        
        # Удаляем команду автора только при 100% успехе
        try: await update.message.delete()
        except: pass

    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка Telegram API при добавлении продюсера:\n`{e}`\n\n"
            f"📌 **Чек-лист для исправления:**\n"
            f"1. Зайди в настройки группы -> Админы -> Нажми на бота и **включи ему ВСЕ тумблеры прав**.\n"
            f"2. Убедись, что юзер, на которого ты ответил — **обычный участник** (если он уже админ, сначала сними его через настройки чата).", 
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
            
        # Забираем права, оставляем минимум ради тега
        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id,
            can_manage_chat=True, can_change_info=False, can_delete_messages=False,
            can_restrict_members=False, can_invite_users=False, can_pin_messages=False,
            can_manage_video_chats=False, can_manage_topics=False
        )
        await asyncio.sleep(1)
        
        # Автоматический перевод на 5 уровень
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title="5 lvl"
        )
        user_levels[target_user.id] = 5
            
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
            try: level = int(context.args[0])
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
            try: level = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Уровень должен быть числом
