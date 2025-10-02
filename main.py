import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ХАРДКОД правильного токена
BOT_TOKEN = "7587417908:AAEt19K7Z2CWro6sZc8ad8lF8fPYKYe05YM"
ADMIN_IDS = [452601108]

print("=== BOT STARTING ===")
print("✅ Using correct token")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🎉 Бот РАБОТАЕТ на Amvera!')

try:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    print("🤖 Bot starting polling...")
    application.run_polling()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
