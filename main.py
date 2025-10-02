import os
import time

print("=== ENVIRONMENT DEBUG ===")
print("Waiting 10 seconds for environment to load...")
time.sleep(10)

print("All environment variables:")
for key, value in os.environ.items():
    if 'BOT' in key or 'TOKEN' in key or 'ADMIN' in key:
        print(f"  {key}: {value}")

BOT_TOKEN = os.getenv('BOT_TOKEN')
print(f"BOT_TOKEN: {BOT_TOKEN}")

if BOT_TOKEN:
    print("✅ BOT_TOKEN is SET! Starting bot...")
    import logging
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    
    logging.basicConfig(level=logging.INFO)
    
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('✅ Бот работает на Amvera!')
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    print("🤖 Bot starting polling...")
    application.run_polling()
else:
    print("❌ BOT_TOKEN is NOT SET in environment!")
    print("Sleeping for 5 minutes to see logs...")
    time.sleep(300)
