# bot_with_variant_management.py
import random
import logging
import os
import sys
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue
import sqlite3
import json
import asyncio
from datetime import datetime, timedelta

# ⚠️ БЕЗОПАСНОСТЬ: Используем переменные окружения!
BOT_TOKEN = os.getenv('BOT_TOKEN', '7587417908:AAEt19K7Z2CWro6sZc8ad8lF8fPYKYe05YM')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '452601108').split(',')]

# Настройка логирования для хостинга
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()  # Важно для Amvera
    ]
)
logger = logging.getLogger(__name__)

print("=== BOT STARTING ===")
print(f"Token: {BOT_TOKEN[:10]}...")
print(f"Admin IDs: {ADMIN_IDS}")

# ... (остальной ваш код БЕЗ ИЗМЕНЕНИЙ) ...

def main():
    if BOT_TOKEN == "7587417908:AAEt19K7Z2CWro6sZc8ad8lF8fPYKYe05YM":
        print("❌ Using test token - make sure BOT_TOKEN env var is set!")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Добавляем задачу для уведомлений
        job_queue = application.job_queue
        job_queue.run_repeating(send_lesson_notification, interval=60, first=10)
        
        print("🤖 Бот запущен!")
        print("✅ Исправленная система:")
        print("   - Работает управление вариантами")
        print("   - Работает решение вариантов")
        print("   - Исправлена навигация")
        print("🔔 Система уведомлений активирована!")
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        print("🚀 Starting Telegram Bot...")
        main()
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("💤 Waiting 60 seconds...")
        import time
        time.sleep(60)
