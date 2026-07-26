import asyncio
import json
import os
import random
from dotenv import load_dotenv
from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 💾 ЗАГРУЗКА СКРЫТЫХ ПЕРЕМЕННЫХ (.env)
load_dotenv()

# 🔐 Бот берет токен из скрытого файла системы
BOT_TOKEN = os.getenv("MY_SECRET_TOKEN")

# 📂 Настройка бессмертной папки для сохранения данных
DATA_DIR = os.getenv('DATA_DIR', '/app/data')
DATA_FILE = os.path.join(DATA_DIR, 'levels.json')
QUOTES_FILE = os.path.join(DATA_DIR, 'quotes.json')

username_to_id = {}
user_levels = {}
user_cars = {}      # Кастомные тачки продюсеров
user_roles = {}     # Скрытые роли (например, {ID: "director"})
chat_quotes = []    # База всех сообщений чата
active_chats = set() # Список ID активных чатов для авто-вбросов

# 💾 СОВЕРШЕННАЯ ЛОГИКА СОХРАНЕНИЯ И ЗАГРУЗКИ
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
                "roles": user_roles
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

# ==================== 🔗 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ СКЛЕЙКИ ====================

def join_by_letter_bridge(text_a: str, text_b: str) -> str:
    """Ищет слово в text_a, чья последняя буква совпадает с первой буквой слова в text_b"""
    words_a = text_a.split()
    words_b = text_b.split()
    
    for i, w1 in enumerate(words_a):
        clean_w1 = "".join(filter(str.isalnum, w1)).lower()
        if not clean_w1:
            continue
        last_char = clean_w1[-1]
        
        for j, w2 in enumerate(words_b):
            clean_w2 = "".join(filter(str.isalnum, w2)).lower()
            if not clean_w2:
                continue
            first_char = clean_w2[0]
            
            if last_char == first_char:
                part_a = words_a[:i+1]
                part_b = words_b[j:]
                return " ".join(part_a + part_b)
                
    mid_a = max(1, len(words_a) // 2)
    mid_b = max(0, len(words_b) // 2)
    return " ".join(words_a[:mid_a] + words_b[mid_b:])

def generate_raw_kasha() -> str:
    """Генерирует чистый гибридный текст без заголовков и авторов"""
    if len(chat_quotes) < 3:
        return ""

    q1, q2, q3 = random.sample(chat_quotes, 3)
    step1 = join_by_letter_bridge(q1["text"], q2["text"])
    return join_by_letter_bridge(step1, q3["text"])

# ==================== ⏰ ФОНОВЫЙ АВТО-ВБРОС ====================

async def auto_kasha_loop(app: Application):
    """Фоновый поток: раз в 8-14 часов присылает чистый текст мема в активные чаты"""
    while True:
        # Пауза от 8 до 14 часов (в секундах)
        wait_seconds = random.randint(8 * 3600, 14 * 3600)
        await asyncio.sleep(wait_seconds)

        raw_text = generate_raw_kasha()
        if not raw_text:
            continue

        for chat_id in list(active_chats):
            try:
                await app.bot.send_message(chat_id=chat_id, text=raw_text)
            except Exception as e:
                print(f"❌ Ошибка отправки авто-каши в чат {chat_id}: {e}")

async def post_init(app: Application):
    """Запускает фоновый таймер сразу после старта бота"""
    asyncio.create_task(auto_kasha_loop(app))

# ==================== 🛠️ ОБРАБОТКА СООБЩЕНИЙ И ПАСХАЛОК ====================

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        active_chats.add(update.effective_chat.id)

    user = update.effective_user
    if user and user.username:
        username_to_id[user.username.lower()] = user.id
    
    if update.message and update.message.text:
        text_lower = update.message.text.lower()
        
        is_msg_from_bot = user.is_bot if user else False
        is_command = update.message.text.startswith('/')
        
        if not is_command and not is_msg_from_bot:
            author_name = user.first_name if user else "Пользователь"
            chat_quotes.append({
                "author": author_name,
                "text": update.message.text
            })
            save_quotes()
        
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
                "• `/cite` — выдать случайное сообщение из истории! 💬\n"
                "• `/mix` — скрестить две случайные фразы! 🔀\n"
                "• `/kasha` — цепная склейка 3 фраз по буквам! 🥣\n"
                "• Просто тегни меня (`@`), чтобы вызвать это меню! 🤖"
            )
            await update.message.reply_text(help_text, parse_mode="Markdown")

async def get_user_status(chat_id, user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
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

# ==================== ⚙️ АДМИН-КОМАНДЫ ====================

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
        custom_title = " ".join(context.args) if context.args else "Директор"
        title = custom_title[:16]

        await context.bot.promote_chat_member(
            chat_id=chat_id, user_id=target_user.id,
            can_manage_chat=True, can_delete_messages=True,
            can_restrict_members=True, can_invite_users=True, can_pin_messages=True
        )
        await asyncio.sleep(1)
        
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=target_user.id, custom_title=title
        )
        
        user_roles[target_user.id] = "director"
        save_data()
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👑 *Особый статус активирован!*\n\nЮзер *{target_user.first_name}* наделен правами Директора.\nУстановлен статус: *{title}* 💎",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при назначении директора:\n`{e}`", parse_mode="Markdown")

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
        await update.message.reply_text(f"❌ Ошибка добавления продюсера:\n`{e}`", parse_mode="Markdown")

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
        if target_user.id in user_roles:
            del user_roles[target_user.id]
        save_data()
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📉 *{target_user.first_name}* снят с должности и переведен на *5 lvl*! 🎖️",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка увольнения: `{e}`", parse_mode="Markdown")

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
                await update.message.reply_text("❌ Напиши уровень: `/setlvl 5`", parse_mode="Markdown")
                return
            try:
                level = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Уровень должен быть числом.")
                return
            target_user = update.message.reply_to_message.from_user
            target_user_id = target_user.id
            target_user_name = target_user.first_name
        else:
            if len(context.args) < 2:
                await update.message.reply_text("❌ Формат: `/setlvl @username 5` или `/setlvl [ID] 5`", parse_mode="Markdown")
                return
            first_arg = context.args[0]
            try:
                level = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Уровень должен быть числом.")
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
                    await update.message.reply_text(f"❌ Я пока не знаю @{username_arg}. Пусть напишет любое сообщение в чат.")
                    return

        target_status = await get_user_status(chat_id, target_user_id, context)
        if target_status == "owner":
            await update.message.reply_text("❌ Ошибка! Менять уровень Создателю чата запрещено.")
            return

        if level < 5 or level > 20:
            await update.message.reply_text("❌ Можно устанавливать уровни только от 5 до 20.")
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
            text=f"🎉 *{target_user_name}* прокачал свой статус!\n\n📊 Новый уровень: *{title}*\n🏎️ Новая тачка: *{car_name}* 🔥",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка выдачи уровня: `{e}`", parse_mode="Markdown")

async def set_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        user_status = await get_user_status(chat_id, user.id, context)
        if user_status not in ["owner", "producer", "director"]:
            await update.message.reply_text("❌ Эта команда доступна только Продюсерам, Директору и Создателю чата.")
            return
            
        if not context.args:
            await update.message.reply_text("❌ Напиши название транспорта: `/setcar Межгалактический Крейсер`", parse_mode="Markdown")
            return
            
        custom_car = " ".join(context.args)
        user_cars[user.id] = custom_car
        save_data()
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚀 *{user.first_name}* обновил свой транспорт!\nТеперь твой аппарат: *{custom_car}* 🔥",
            parse_mode="Markdown"
        )
        try: await update.message.delete()
        except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка установки тачки: `{e}`", parse_mode="Markdown")

async def clean_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id
        
        sender_status = await get_user_status(chat_id, sender_id, context)
        if sender_status not in ["owner", "producer", "director"]:
            await update.message.reply_text("❌ Ошибка! Чистить права могут только Продюсеры, Директор или Создатель чата.")
            return
            
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение пользователя и напиши `/clean`", parse_mode="Markdown")
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
        if target_user.id in user_roles:
            del user_roles[target_user.id]
        save_data()
            
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🧹 Все права пользователя *{target_user.first_name}* аннулированы. Он сброшен до *5 lvl*.",
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
            await update.message.reply_text("❌ Команда доступна только Продюсерам и Директору чата.")
            return
            
        if not context.args:
            await update.message.reply_text("❌ Напиши имя после команды: `/setname DoReMi`", parse_mode="Markdown")
            return
            
        custom_name = " ".join(context.args)
        
        if user_status == "director":
            title = custom_name[:16]
        else:
            title = f"Прод {custom_name}"[:16]
            
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id, user_id=user.id, custom_title=title
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎬 Статус обновлен:\nТеперь в чате ты: *{title}* 💎",
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

# ==================== 💬 ИГРОВЫЕ И ТЕКСТОВЫЕ КОМАНДЫ ====================

async def cite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not chat_quotes:
            await update.message.reply_text("📋 История чата пуста! Напишите сначала несколько обычных сообщений.")
            return
            
        random_quote = random.choice(chat_quotes)
        
        await update.message.reply_text(
            f"💬 *Случайный флешбэк из архива:*\n\n"
            f"«_{random_quote['text']}_»\n\n"
            f"© *{random_quote['author']}*", 
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка вызова цитаты: `{e}`")

async def mix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(chat_quotes) < 2:
            await update.message.reply_text("🧪 Для микса нужно хотя бы 2 сообщения в истории!")
            return

        quote_a, quote_b = random.sample(chat_quotes, 2)

        words_a = quote_a["text"].split()
        words_b = quote_b["text"].split()

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

async def kasha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(chat_quotes) < 3:
            await update.message.reply_text("🥣 Чтобы заварить кашу, нужно хотя бы 3 сообщения в истории!")
            return

        q1, q2, q3 = random.sample(chat_quotes, 3)

        step1 = join_by_letter_bridge(q1["text"], q2["text"])
        final_kasha = join_by_letter_bridge(step1, q3["text"])

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

# ==================== 🚀 ЗАПУСК ПРИЛОЖЕНИЯ ====================

def main():
    # Собираем приложение с фоновым таймером post_init
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Регистрация хэндлеров
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
    
    # Секретные хэндлеры
    app.add_handler(CommandHandler("setbulat", set_bulat_director))
    
    print("🤖 Бот запущен! Фоновый авто-вброс подключен.")
    app.run_polling()

if __name__ == "__main__":
    main()
