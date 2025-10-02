import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = os.getenv('ADMIN_IDS', '452601108')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

print("=== BOT STARTUP ===")
print(f"BOT_TOKEN: {'SET' if BOT_TOKEN else 'NOT SET'}")
print(f"ADMIN_IDS: {ADMIN_IDS}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('✅ Бот работает на Amvera!')

def main():
    print("🚀 Starting Telegram Bot...")
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN is not set in environment variables!")
        print("💡 Set BOT_TOKEN in Amvera panel → Environment Variables")
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
