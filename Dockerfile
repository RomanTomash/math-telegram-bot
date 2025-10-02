FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Простейшая команда которая точно работает
CMD ["python", "-c", "print('=== CONTAINER IS RUNNING ==='); import time; time.sleep(300)"]
