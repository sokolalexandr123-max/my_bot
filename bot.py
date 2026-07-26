import asyncio
import json
import os
import random  # Для случайного выбора эмодзи и рандомных цитат
from dotenv import load_dotenv
from telegram import Update, ReactionTypeEmoji  # ReactionTypeEmoji для реакций
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 💾 ЗАГРУЗКА СКРЫТЫХ ПЕРЕМЕННЫХ (.env)
load_dotenv()

# 🔐 Бот берет токен из скрытого файла системы
BOT_TOKEN = os.getenv("MY_SECRET_TOKEN")

# 📂 Настройка бессмертной папки для сохранения данных (требование хостинга)
DATA_DIR = os.getenv('DATA_DIR', '/app/data')
DATA_FILE = os.path.join(DATA_DIR, 'levels.json')
QUOTES_FILE = os.path.join(DATA_DIR, 'quotes.json')  # Файл для истории сообщений

username_to_id = {}
user_levels = {}
user_cars = {}  # Здесь хранятся кастомные тачки продюсеров
user_roles = {}  # 👈 Хранение скрытых ролей (например, {ID: "director"})
chat_quotes = []  # База всех сообщений чата

# 💾 СОВЕРШЕННАЯ ЛОГИКА СОХРАНЕНИЯ
def load_data():
    """Загрузка уровней, кастомных тачек, ролей и истории из файлов"""
    global user_levels, user_cars, chat_quotes, user_roles
    
    # 1. Загрузка уровней и ролей
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "levels" in data or "cars" in data or "roles" in data:
                    levels = data.get("levels", {})
                    cars = data.get("cars", {})
                    roles = data.get("roles", {})
                    user_levels = {int(k): v for k, v in levels.items()}
                    user_cars = {int(k): v for k, v in cars.items()}
                    user_roles = {int(k): v for k, v in roles.items()}
                else:
                    user_levels = {int(k): v for k, v in data.items()}
                    user_cars = {}
                    user_roles = {}
        except Exception as e:
            print(f"❌ Ошибка загрузки уровней: {e}")
    else:
        user_levels = {}
        user_cars = {}
        user_roles = {}

    # 2. Загрузка истории сообщений
    if os.path.exists(QUOTES_FILE):
        try:
            with open(QUOTES_FILE, "r", encoding="utf-8") as f:
                chat_quotes = json.load(f)
        except Exception as e:
            print(f"❌ Ошибка загрузки истории: {e}")
            chat_quotes = []
    else:
        chat_quotes = []

def save_data():
    """Сохранение данных уровней и ролей в файл"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            combined_data = {
                "levels": user_levels,
                "cars": user_cars,
                "roles": user_roles  # 👈 Записываем роли в файл
            }
            json.dump(combined_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Ошибка записи уровней: {e}")

def save_quotes():
    """Сохранение истории сообщений в файл"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(QUOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_quotes, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Ошибка записи истории: {e}")

# Загружаем всю базу данных при старте
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
    17: "Ламборгини",
    18: "Майбах",
    19: "Бугатти Широн",
    20: "Роллс-Royce Фантом"
}

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user and user.username:
        username_to_id[user.username.lower()] = user.id
    
    if update.message and update.message.text:
        text_lower = update.message.text.lower()
        
        # 📥 ЧИСТОЕ АВТО-СОХРАНЕНИЕ
        is_msg_from_bot = user.is_bot if user else False
        is_command = update.message.text.startswith('/')
        
        if not is_command and not is_msg_from_bot:
            author_name = user.first_name if user else "Пользователь"
            chat_quotes.append({
                "author": author_name,
                "text": update.message.text
            })
            save_quotes()
        
        # 😎 ХИТРЫЕ ПАСХАЛКИ НА СОЗДАТЕЛЯ
        if "thisisfun" in text_lower or "@thisisfun404xd" in text_lower:
            reactions = ["🔥", "😎", "👑", "🚀", "⚡", "🏆", "👍", "❤️"]
            chosen_emoji = random.choice(reactions)
            try:
                await update.message.set_reaction(reaction=ReactionTypeEmoji(emoji=chosen_emoji))
            except Exception as e:
                print(f"❌ Ошибка реакции: {e}")
                await update.message.reply_text(f"{chosen_emoji} Опа, создатель в здании! {chosen_emoji}")
            return
            
        bot_user = await context.bot.get_me()
        bot_username = bot_user.username.lower()
        
        if f"@{bot_username}" in text_lower:
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
                "• `/cite` — выдать абсолютно рандомное сообщение из истории чата! 💬\n"
                "• `/mix` — скрестить две случайные фразы из архива в микс! 🔀\n"
                "• `/kasha` — цепная склейка 3 фраз по совпадающим буквам! 🥣\n"
                "• Просто тегни меня (`@`), чтобы вызвать это меню! 🤖"
            )
            await update.message.reply_text(help_text, parse_mode="Markdown")

async def get_user_status(chat_id, user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Первым делом проверяем нашу базу на скрытые роли (директор)
        if user_roles.get(user_id) == "director":
            return "director"
            
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status == "creator":
            return "owner"
        if member.custom_title and member.custom_title.strip().lower().startswith("прод"):
            return "producer"
    except:
        pass
    return "regular"

# 🤫 СЕКРЕТНАЯ КОМАНДА ДЛЯ ДИРЕКТОРА (БУЛАТА)
async def set_bulat_director(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status != "owner":
            await update.message.reply_text("❌ Ошибка! Активировать этот статус может только Создатель чата 👑")
            return
            
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение директора и напиши `/setbulat [Название должности]`")
            return

        target_user = update.message.reply_to_message.from_user
        # Если должность не указана, по дефолту ставим "Директор"
        custom_title = " ".join(context.args) if context.args else "Директор"
        title = custom_title[:16]

        # Выдаем полные админ-права
        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id,
            can_manage_chat=True, can_delete_messages=True,
            can_restrict_members=True, can_invite_users=True, can_pin_messages=True
        )
        await asyncio.sleep(1)
        
        # Ставим кастомный чистый тайтл БЕЗ слова "Прод"
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title=title
        )
        
        # Заносим ID в базу данных как директора
        user_roles[target_user.id] = "director"
        save_data()
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👑 *Особый статус активирован!*\n\nЮзер *{target_user.first_name}* успешно наделен правами Директора.\nУстановлен чистый статус: *{title}* 💎",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка Telegram API при назначении директора:\n`{e}`", parse_mode="Markdown")

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
        await update.message.reply_text(f"❌ Ошибка Telegram API при добавлении продюсера:\n`{e}`", parse_mode="Markdown")

async def delete_producer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status != "owner":
            await update.message.reply_text("❌ Ошибка! Снимать админов может только Создатель чата 👑")
            return
            
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение админа и напиши `/delprod`")
            return
            
        target_user = update.message.reply_to_message.from_user
            
        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id,
            can_manage_chat=True, can_change_info=False, can_delete_messages=False,
            can_restrict_members=False, can_invite_users=False, can_pin_messages=False
        )
        await asyncio.sleep(1)
        
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title="5 lvl"
        )
        user_levels[target_user.id] = 5
        if target_user.id in user_cars:
            del user_cars[target_user.id]
        if target_user.id in user_roles:  # Сбрасываем роль директора, если уволили
            del user_roles[target_user.id]
        save_data()
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📉 *{target_user.first_name}* снят с должности и автоматически переведен на *5 lvl*! 🎖️",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при увольнении: `{e}`", parse_mode="Markdown")

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status not in ["owner", "producer", "director"]:
            await update.message.reply_text("❌ Менять уровни могут только Продюсеры, Директор или Создатель чата.")
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

async def set_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        user_status = await get_user_status(chat_id, user.id, context)
        if user_status not in ["owner", "producer", "director"]:
            await update.message.reply_text("❌ Эта команда доступна только Продюсерам, Директору и Создателю чата, бро!")
            return
            
        if not context.args:
            await update.message.reply_text("❌ Напиши название транспорта: `/setcar Межгалактический Крейсер`")
            return
            
        custom_car = " ".join(context.args)
        user_cars[user.id] = custom_car
        save_data()
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚀 *{user.first_name}* обновил свой личный транспорт!\nТеперь твой аппарат: *{custom_car}* 🔥",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка установки кастомной тачки: `{e}`", parse_mode="Markdown")

async def clean_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status not in ["owner", "producer", "director"]:
            await update.message.reply_text("❌ Ошибка! Чистить права могут только Продюсеры, Директор или Создатель чата.")
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
            can_restrict_members=False, can_invite_users=False, can_pin_messages=False
        )
        await asyncio.sleep(1)
        
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title="5 lvl"
        )
        user_levels[target_user.id] = 5
        if target_user.id in user_cars:
            del user_cars[target_user.id]
        if target_user.id in user_roles:  # Стираем скрытую роль при зачистке
            del user_roles[target_user.id]
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
        if user_status not in ["owner", "producer", "director"]:
            await update.message.reply_text("❌ Эта команда доступна только Продюсерам и Директору чата, бро!")
            return
            
        if not context.args:
            await update.message.reply_text("❌ Напиши имя после команды, например: `/setname DoReMi`")
            return
            
        custom_name = " ".join(context.args)
        
        # 🔥 УМНОЕ РАЗДЕЛЕНИЕ СТАТУСОВ:
        if user_status == "director":
            title = custom_name[:16]  # Чистый статус без приписки "Прод"
        else:
            title = f"Прод {custom_name}"[:16]  # Обычный продюсерский статус
            
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=user.id, custom_title=title
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎬 Статус успешно обновлен:\nТеперь в чате ты: *{title}* 💎",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка смены тега: `{e}`", parse_mode="Markdown")

async def my_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_cars:
        car_info = f"\n🏎 Личный транспорт: *{user_cars[user_id]}* 🔥"
        level_info = "Админ-статус"
    else:
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

# ==================== 💬 ВЫЗОВ СЛУЧАЙНОГО ВОСПОМИНАНИЯ ====================

async def cite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cite"""
    try:
        if not chat_quotes:
            await update.message.reply_text("📋 История чата пока пуста! Напишите сначала несколько обычных сообщений.")
            return
            
        random_quote = random.choice(chat_quotes)
        
        await update.message.reply_text(
            f"💬 *Случайный флешбэк из архива чата:*\n\n"
            f"«_{random_quote['text']}_»\n\n"
            f"© *{random_quote['author']}*", 
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка вызова цитаты: `{e}`")

# ==================== 🔀 ГЕНЕРАТОР ШИЗО-КОМБО ====================

async def mix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mix — скрещивает 2 случайные фразы из истории чата"""
    try:
        if len(chat_quotes) < 2:
            await update.message.reply_text("🧪 Для создания микса нужно хотя бы 2 сообщения в истории чата! Напишите ещё что-нибудь.")
            return

        # Выбираем 2 случайных сообщения из базы
        quote_a, quote_b = random.sample(chat_quotes, 2)

        words_a = quote_a["text"].split()
        words_b = quote_b["text"].split()

        # Берем первую половину первой фразы и вторую половину второй
        half_a = words_a[:max(1, len(words_a) // 2)]
        half_b = words_b[len(words_b) // 2:]

        mixed_text = " ".join(half_a + half_b)

        author_a = quote_a["author"]
        author_b = quote_b["author"]
        authors_str = f"{author_a} × {author_b}" if author_a != author_b else author_a

        await update.message.reply_text(
            f"🔀 *Шизо-комбо из архива:*\n\n"
            f"«_{mixed_text}_»\n\n"
            f"🧪 *Скрестили:* {authors_str}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка генерации микса: `{e}`", parse_mode="Markdown")

# ==================== 🔗 Вспомогательная функция стыковки ====================

def join_by_letter_bridge(text_a: str, text_b: str) -> str:
    """Ищет слово в text_a, чья последняя буква совпадает с первой буквой слова в text_b"""
    words_a = text_a.split()
    words_b = text_b.split()
    
    for i, w1 in enumerate(words_a):
        # Очищаем слово от знаков препинания для точного поиска буквы
        clean_w1 = "".join(filter(str.isalnum, w1)).lower()
        if not clean_w1:
            continue
        last_char = clean_w1[-1]
        
        for j, w2 in enumerate(words_b):
            clean_w2 = "".join(filter(str.isalnum, w2)).lower()
            if not clean_w2:
                continue
            first_char = clean_w2[0]
            
            # 🔥 Нашли совпадение на стыке!
            if last_char == first_char:
                part_a = words_a[:i+1]
                part_b = words_b[j:]
                return " ".join(part_a + part_b)
                
    # Страховка: если общих букв не нашлось, режем пополам
    mid_a = max(1, len(words_a) // 2)
    mid_b = max(0, len(words_b) // 2)
    return " ".join(words_a[:mid_a] + words_b[mid_b:])

# ==================== 🥣 ГЕНЕРАТОР КАШИ (ЦЕПНАЯ СКЛЕЙКА) ====================

async def kasha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /kasha — цепная склейка 3 фраз по совпадающим буквам"""
    try:
        if len(chat_quotes) < 3:
            await update.message.reply_text("🥣 Чтобы заварить кашу, нужно хотя бы 3 сообщения в истории чата!")
            return

        # Берем 3 случайных сообщения
        q1, q2, q3 = random.sample(chat_quotes, 3)

        # 1. Состыковываем 1-е и 2-е сообщения
        step1 = join_by_letter_bridge(q1["text"], q2["text"])
        
        # 2. Состыковываем результат с 3-им сообщением
        final_kasha = join_by_letter_bridge(step1, q3["text"])

        # Собираем список авторов
        authors = list(dict.fromkeys([q1["author"], q2["author"], q3["author"]]))
        authors_str = " + ".join(authors)

        await update.message.reply_text(
            f"🥣 *Цепная каша (склейка по буквам):*\n\n"
            f"«_{final_kasha}_»\n\n"
            f"👨‍🍳 *Поварята:* {authors_str}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при варке каши: `{e}`", parse_mode="Markdown")

# ==================== ЗАПУСК БОТА ====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_users))
    app.add_handler(CommandHandler("addprod", add_producer))
    app.add_handler(CommandHandler("delprod", delete_producer))
    app.add_handler(CommandHandler("setlvl", set_level))
    app.add_handler(CommandHandler("setname", set_name))
    app.add_handler(CommandHandler("setcar", set_car))
    app.add_handler(CommandHandler("clean", clean_user))
    app.add_handler(CommandHandler("my_level", my_level))
    app.add_handler(CommandHandler("cite", cite_command))
    app.add_handler(CommandHandler("mix", mix_command))
    app.add_handler(CommandHandler("kasha", kasha_command))
    
    # 🤫 СЕКРЕТНЫЕ ХЕНДЛЕРЫ
    app.add_handler(CommandHandler("setbulat", set_bulat_director))
    
    print("🤖 Бот успешно запущен на стабильной конфигурации!")
    app.run_polling()

if __name__ == "__main__":
    main()
