import asyncio
import json
import os
import random
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные окружения (.env)
load_dotenv()

BOT_TOKEN = os.getenv("MY_SECRET_TOKEN")
SECRET_PASSWORD = os.getenv("SECRET_PASSWORD", "default_secure_knock_99x")

# Настройки путей для Ботхоста
DATA_DIR = os.getenv('DATA_DIR', '/app/data')
DATA_FILE = os.path.join(DATA_DIR, 'levels.json')
CHATS_FILE = os.path.join(DATA_DIR, 'managed_chats.json')  
SECRETS_FILE = os.path.join(DATA_DIR, 'secrets.json')  
USERNAMES_FILE = os.path.join(DATA_DIR, 'usernames.json')

SUPER_ADMIN_ID = 0

# Глобальные кэш-словари
username_to_id = {}
user_levels = {}
user_cars = {}  
user_roles = {}  

# --- СИСТЕМА ПАМЯТИ И ЗАГРУЗКИ ДАННЫХ ---

def load_super_admin():
    global SUPER_ADMIN_ID
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                SUPER_ADMIN_ID = data.get("super_admin_id", 0)
        except:
            SUPER_ADMIN_ID = 0

def save_super_admin(user_id: int):
    global SUPER_ADMIN_ID
    SUPER_ADMIN_ID = user_id
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump({"super_admin_id": user_id}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Runtime error: {e}")

def load_usernames():
    global username_to_id
    if os.path.exists(USERNAMES_FILE):
        try:
            with open(USERNAMES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                username_to_id = {k: int(v) for k, v in data.items()}
        except:
            username_to_id = {}

def save_usernames():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(USERNAMES_FILE, "w", encoding="utf-8") as f:
            json.dump(username_to_id, f, ensure_ascii=False, indent=4)
    except Exception as e: 
        print(f"Runtime error: {e}")

load_super_admin()
load_usernames()

def load_managed_chats() -> dict:
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_managed_chats(chats_dict: dict):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump(chats_dict, f, ensure_ascii=False, indent=4)
    except Exception as e: 
        print(f"Runtime error: {e}")

def load_quotes(chat_id: int) -> list:
    file_path = os.path.join(DATA_DIR, f'quotes_{chat_id}.json')
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_quotes(chat_id: int, quotes_list: list):
    file_path = os.path.join(DATA_DIR, f'quotes_{chat_id}.json')
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(quotes_list, f, ensure_ascii=False, indent=4)
    except Exception as e: 
        print(f"Runtime error: {e}")

def load_data():
    global user_levels, user_cars, user_roles
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "levels" in data or "cars" in data or "roles" in data:
                    user_levels = {int(k): v for k, v in data.get("levels", {}).items()}
                    user_cars = {int(k): v for k, v in data.get("cars", {}).items()}
                    user_roles = {int(k): v for k, v in data.get("roles", {}).items()}
        except Exception as e: 
            print(f"Runtime error: {e}")

def save_data():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"levels": user_levels, "cars": user_cars, "roles": user_roles}, f, ensure_ascii=False, indent=4)
    except Exception as e: 
        print(f"Runtime error: {e}")

load_data()

# Ранги авто по уровням
CAR_RANKS = {
    5: "Чепырка (ВАЗ-2114)", 6: "Приора", 7: "Рено Логан", 8: "Киа Рио / Хендай Солярис",
    9: "Шкода Октавия", 10: "Тойота Камри 3.5", 11: "БМВ Е39", 12: "Мерседес C-Класс",
    13: "БМВ Х5", 14: "Порше Кайен", 15: "Гелик (Mercedes G-Class)", 16: "Ауди R8",
    17: "Ламборгини", 18: "Майбах", 19: "Бугатти Широн", 20: "Роллс-Royce Фантом"
}

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ЛОГИКИ ---

def get_active_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_chat.type == "private":
        return context.user_data.get('active_chat_id', 0)
    return update.effective_chat.id

async def get_user_status(chat_id, user_id, context: ContextTypes.DEFAULT_TYPE):
    if SUPER_ADMIN_ID and user_id == SUPER_ADMIN_ID:
        return "owner"  
    try:
        if user_roles.get(user_id) == "director": return "director"
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status == "creator": return "owner"
        if member.custom_title and member.custom_title.strip().lower().startswith("прод"): return "producer"
    except: pass
    return "regular"

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """
    Умный поиск цели: Сначала проверяет явный @тег или цифровой ID в аргументах.
    Если аргументов нет, но есть Reply (ответ на сообщение) — берет автора сообщения.
    """
    if context.args:
        first_arg = context.args[0]
        
        if first_arg.startswith("@"):
            uname = first_arg.replace("@", "").lower()
            if uname in username_to_id:
                return username_to_id[uname], first_arg, context.args[1:]
            return None, first_arg, context.args[1:]
            
        if first_arg.isdigit() and len(first_arg) > 4:
            uid = int(first_arg)
            try:
                m = await context.bot.get_chat_member(chat_id=chat_id, user_id=uid)
                return uid, m.user.first_name, context.args[1:]
            except:
                return uid, "User", context.args[1:]

    if update.message and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        return target.id, target.first_name, context.args
        
    return None, None, []

# --- ГЕНЕРАТОРЫ ИНТЕРФЕЙСА ЛС ---

def get_main_menu_text() -> str:
    chats = load_managed_chats()
    text = "🎛 *ГЛАВНОЕ МЕНЮ СУПЕР-АДМИНА*\n\nВыбери чат для подключения (пришли цифру):\n"
    if not chats:
        return text + "_Пока нет доступных чатов. Добавь бота в группу и напиши туда любое сообщение!_"
    
    for i, (chat_id, chat_name) in enumerate(chats.items()):
        text += f"{i+1}. *{chat_name}* (ID: `{chat_id}`)\n"
    return text

def get_chat_menu_text(chat_name: str) -> str:
    return (
        f"📂 *Управление чатом:* {chat_name}\n\n"
        f"Выбери действие (пришли цифру):\n"
        f"1. 📥 *Скачать историю сообщений* (.json)\n"
        f"2. 🎛 *Войти в консоль админа* (управление)\n"
        f"3. 🔙 *Назад к списку чатов*"
    )

# --- ДЕЖУРНЫЕ ОБРАБОТЧИКИ (МЕНЕДЖЕРЫ ТЕКСТА) ---

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or not user: return
    
    # Запоминаем связку юзернейм -> ID в глобальную базу
    if user.username:
        uname_lower = user.username.lower()
        if username_to_id.get(uname_lower) != user.id:
            username_to_id[uname_lower] = user.id
            save_usernames()
    
    if chat.type != "private" and update.message and update.message.text:
        chats = load_managed_chats()
        chat_id_str = str(chat.id)
        if chat_id_str not in chats or chats[chat_id_str] != chat.title:
            chats[chat_id_str] = chat.title or "Безымянная группа"
            save_managed_chats(chats)

        # Логируем текст в цитатник, только если это обычное общение (НЕ команда бота)
        if not update.message.text.startswith('/') and not user.is_bot:
            quotes = load_quotes(chat.id)
            quotes.append({"author": user.first_name, "text": update.message.text})
            save_quotes(chat.id, quotes)
            
            # Интерактивный Хелп-меню вместо старой фразы
            bot_user = await context.bot.get_me()
            if f"@{bot_user.username.lower()}" in update.message.text.lower():
                help_text = (
                    "🤖 *Система управления активна!*\n\n"
                    "📊 *Команды для игроков:*\n"
                    "• `/my_level` — узнать свой уровень и транспорт.\n"
                    "• `/cite` — вызвать случайный флешбэк (цитату) из чата.\n\n"
                    "👑 *Команды для администрации (через Reply или @тег):*\n"
                    "• `/setlvl [уровень]` — выдать уровень (5-20) и авто.\n"
                    "• `/addprod [имя]` — назначить Продюсером.\n"
                    "• `/delprod` — разжаловать продюсера.\n"
                    "• `/clean` — полная зачистка прав и сброс на 5 lvl.\n\n"
                    "💡 _Управлять этим чатом можно удаленно прямо из Консоли в ЛС бота!_"
                )
                await update.message.reply_text(help_text, parse_mode="Markdown")

async def handle_private_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SUPER_ADMIN_ID
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Стейдж 0: Первая авторизация создателя
    if SUPER_ADMIN_ID == 0:
        if text == SECRET_PASSWORD:
            save_super_admin(user_id)
            context.user_data['state'] = 'WAIT_CHAT_CHOICE'
            await update.message.reply_text(
                "👑 *ИНИЦИАЛИЗАЦИЯ УСПЕШНА!*\n\n"
                "Твой Telegram ID успешно привязан на сервере и скрыт от чужих глаз.\n"
                "Пароль аннулирован. Добро пожаловать, Создатель. 🕶", parse_mode="Markdown"
            )
            await update.message.reply_text(get_main_menu_text(), parse_mode="Markdown")
        return

    # Защита ЛС от посторонних юзеров
    if user_id != SUPER_ADMIN_ID:
        return

    state = context.user_data.get('state', 'WAIT_CHAT_CHOICE')

    if text == "/start":
        context.user_data['state'] = 'WAIT_CHAT_CHOICE'
        await update.message.reply_text(get_main_menu_text(), parse_mode="Markdown")
        return

    # Стейдж 1: Выбор чата
    if state == 'WAIT_CHAT_CHOICE':
        chats = load_managed_chats()
        indexed_chats = {i+1: (int(cid), name) for i, (cid, name) in enumerate(chats.items())}
        
        if text.isdigit() and int(text) in indexed_chats:
            choice = int(text)
            chat_id, chat_name = indexed_chats[choice]
            context.user_data['active_chat_id'] = chat_id
            context.user_data['active_chat_name'] = chat_name
            context.user_data['state'] = 'CHAT_MENU'
            await update.message.reply_text(get_chat_menu_text(chat_name), parse_mode="Markdown")
        else:
            await update.message.reply_text("🔢 Пришли корректную цифру чата из списка!")

    # Стейдж 2: Меню действий внутри чата
    elif state == 'CHAT_MENU':
        chat_id = context.user_data.get('active_chat_id')
        chat_name = context.user_data.get('active_chat_name')

        if text == "1":
            quotes = load_quotes(chat_id)
            if not quotes:
                await update.message.reply_text("❌ База данных этого чата пуста.")
                return
            file_path = os.path.join(DATA_DIR, f'quotes_{chat_id}.json')
            with open(file_path, "rb") as file:
                await context.bot.send_document(
                    chat_id=user_id, document=file, filename=f"history_{chat_name}.json",
                    caption=f"📦 Вся история сообщений из чата: *{chat_name}*"
                )
        elif text == "2":
            context.user_data['state'] = 'ADMIN_CONSOLE'
            await update.message.reply_text(
                f"📟 *КОНСОЛЬ АДМИНА АКТИВИРОВАНА ДЛЯ:* {chat_name}\n\n"
                f"Любая команда выполнится в группе удаленно от лица Создателя.\n\n"
                f"🔙 Выйти обратно в меню: `/back`", parse_mode="Markdown"
            )
        elif text == "3":
            context.user_data['state'] = 'WAIT_CHAT_CHOICE'
            await update.message.reply_text(get_main_menu_text(), parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Введи цифру 1, 2 или 3.")
