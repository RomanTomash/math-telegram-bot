print("=== TELEGRAM BOT DIAGNOSTICS ===")
import sys, os
print(f"Python: {sys.version}")
print(f"Workdir: {os.getcwd()}")
print(f"Files: {os.listdir('.')}")

try:
    import sqlite3
    print("✅ SQLite3: OK")
    
    # Test DB
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO test (name) VALUES ('test')")
    conn.commit()
    conn.close()
    print("✅ Database: OK")
    
except Exception as e:
    print(f"❌ Database error: {e}")

try:
    import telegram
    print("✅ python-telegram-bot: OK")
except Exception as e:
    print(f"❌ Telegram bot error: {e}")

print("=== DIAGNOSTICS COMPLETE ===")
