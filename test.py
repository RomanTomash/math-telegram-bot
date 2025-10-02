print("=== BASIC TEST ===")
print("If you see this, container is running!")
import sys
print(f"Python: {sys.version}")
import os
print(f"Workdir: {os.getcwd()}")
print(f"Files: {os.listdir('.')}")

# Проверяем зависимости
try:
    import telegram
    print("✅ telegram: OK")
except ImportError as e:
    print(f"❌ telegram: {e}")

try:
    import sqlite3  
    print("✅ sqlite3: OK")
except ImportError as e:
    print(f"❌ sqlite3: {e}")

print("=== TEST COMPLETE ===")

# Держим скрипт активным
import time
time.sleep(300)  # 5 минут
