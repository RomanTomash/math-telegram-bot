import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка
BOT_TOKEN = os.getenv('BOT_TOKEN', '7587417908:AAEt19K7Z2CWro6sZc8ad8lF8fPYKYe05YM')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('✅ Бот работает на Amvera!')

def main():
    print("🚀 Starting Telegram Bot...")
    
    # Проверяем токен
    if not BOT_TOKEN or BOT_TOKEN == "7587417908:AAEt19K7Z2CWro6sZc8ad8lF8fPYKYe05YM":
        print("❌ BOT_TOKEN not set properly!")
        return
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        
        print("🤖 Bot starting polling...")
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
