import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Переменные уже установлены в панели
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = os.getenv('ADMIN_IDS')

print("=== BOT STARTING ===")
print(f"BOT_TOKEN from env: {'✅ SET' if BOT_TOKEN else '❌ NOT SET'}")
print(f"ADMIN_IDS from env: {ADMIN_IDS}")

if not BOT_TOKEN:
    print("❌ FATAL: BOT_TOKEN not in environment!")
    print("💡 Even though it's set in panel, it's not reaching the container")
    exit(1)

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🎉 Бот работает на Amvera!')

try:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    print("🤖 Bot starting polling...")
    application.run_polling()
except Exception as e:
    print(f"❌ Bot error: {e}")
    import traceback
    traceback.print_exc()
