from telegram.ext import Updater, CommandHandler

BOT_TOKEN = "8534700798:AAF2EJMfjpDEv5Y0fCyJIBqC33PPLb86mM0"

def start(update, context):
    update.message.reply_text("Бот жив!")

def main():
    updater = Updater(BOT_TOKEN)
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.start_polling()
    print("Бот запущен")
    updater.idle()

if __name__ == "__main__":
    main()
