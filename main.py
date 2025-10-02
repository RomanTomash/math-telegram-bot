import os
import random
import logging
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


class SimpleDB:
    def __init__(self):
        self.conn = sqlite3.connect('bot.db', check_same_thread=False, 
                                   detect_types=sqlite3.PARSE_DECLTYPES)
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT DEFAULT 'student'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                exam_type TEXT DEFAULT 'ЕГЭ',
                category TEXT DEFAULT 'ФИПИ',
                exercises TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                variant_id INTEGER,
                exercise_id INTEGER,
                user_answer TEXT,
                is_correct BOOLEAN,
                answered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wrong_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                variant_id INTEGER,
                exercise_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, variant_id, exercise_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                student_name TEXT,
                lesson_time DATETIME,
                notified BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Обновляем тестовые варианты с разделением на ОГЭ/ЕГЭ
        test_variants = [
            # ЕГЭ ФИПИ варианты
            {
                "name": "Вариант 1 - Профильный уровень",
                "exam_type": "ЕГЭ",
                "category": "ФИПИ",
                "exercises": [
                    {
                        "id": 1, 
                        "question": "Решите уравнение: 2x + 5 = 15\n\nВведите значение x:", 
                        "correct_answer": "5"
                    },
                    {
                        "id": 2, 
                        "question": "Найдите площадь прямоугольника со сторонами 4 см и 6 см\n\nВведите площадь:", 
                        "correct_answer": "24"
                    }
                ]
            },
            {
                "name": "Вариант 2 - Базовый уровень", 
                "exam_type": "ЕГЭ",
                "category": "ФИПИ",
                "exercises": [
                    {
                        "id": 1,
                        "question": "Вычислите: 15 ÷ 3 + 4\n\nВведите ответ:",
                        "correct_answer": "9"
                    }
                ]
            },
            # ЕГЭ Ященко варианты
            {
                "name": "Вариант 1 - Тренировочный",
                "exam_type": "ЕГЭ",
                "category": "Ященко",
                "exercises": [
                    {
                        "id": 1,
                        "question": "Решите: 3² + 4²\n\nВведите ответ:",
                        "correct_answer": "25"
                    }
                ]
            },
            # ОГЭ ФИПИ варианты
            {
                "name": "ОГЭ Вариант 1 - Основной",
                "exam_type": "ОГЭ", 
                "category": "ФИПИ",
                "exercises": [
                    {
                        "id": 1,
                        "question": "Найдите значение выражения: 12 × 5 - 8\n\nВведите ответ:",
                        "correct_answer": "52"
                    },
                    {
                        "id": 2,
                        "question": "Решите уравнение: x/2 = 6\n\nВведите ответ:",
                        "correct_answer": "12"
                    }
                ]
            },
            {
                "name": "ОГЭ Вариант 2 - Геометрия",
                "exam_type": "ОГЭ",
                "category": "ФИПИ", 
                "exercises": [
                    {
                        "id": 1,
                        "question": "Найдите площадь круга с радиусом 3 см (π ≈ 3.14)\n\nВведите ответ:",
                        "correct_answer": "28.26"
                    }
                ]
            },
            # ОГЭ Ященко варианты
            {
                "name": "ОГЭ Вариант 1 - Тренировочный",
                "exam_type": "ОГЭ",
                "category": "Ященко",
                "exercises": [
                    {
                        "id": 1,
                        "question": "Вычислите: √64 + 5²\n\nВведите ответ:",
                        "correct_answer": "33"
                    }
                ]
            }
        ]
        
        cursor.execute('SELECT COUNT(*) FROM variants')
        if cursor.fetchone()[0] == 0:
            for variant in test_variants:
                cursor.execute(
                    'INSERT INTO variants (name, exam_type, category, exercises) VALUES (?, ?, ?, ?)',
                    (variant['name'], variant['exam_type'], variant['category'], json.dumps(variant['exercises']))
                )
        
        self.conn.commit()
        print("✅ База данных создана с разделением на ОГЭ/ЕГЭ!")
    
    def add_user(self, user_id, username, role='student'):
        """Добавляет пользователя в базу"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO users (id, username, role) VALUES (?, ?, ?)',
            (user_id, username, role)
        )
        self.conn.commit()

    def get_all_students(self):
        """Получает всех учеников"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, username FROM users WHERE role = "student"')
        return cursor.fetchall()
    
    def get_exam_types(self):
        """Получает все типы экзаменов"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT exam_type FROM variants ORDER BY exam_type')
        exam_types = [row[0] for row in cursor.fetchall()]
        return exam_types if exam_types else ['ЕГЭ', 'ОГЭ']
    
    def get_categories_by_exam(self, exam_type):
        """Получает категории для конкретного экзамена"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM variants WHERE exam_type = ? ORDER BY category', (exam_type,))
        categories = [row[0] for row in cursor.fetchall()]
        return categories if categories else ['ФИПИ', 'Ященко']
    
    def get_variants_by_exam_and_category(self, exam_type, category):
        """Получает варианты по типу экзамена и категории"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM variants WHERE exam_type = ? AND category = ? ORDER BY name', (exam_type, category))
        return cursor.fetchall()
    
    def get_variant_by_id(self, variant_id):
        """Получает вариант по ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM variants WHERE id = ?', (variant_id,))
        return cursor.fetchone()
    
    def add_variant(self, name, exam_type, category, exercises):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO variants (name, exam_type, category, exercises) VALUES (?, ?, ?, ?)',
            (name, exam_type, category, json.dumps(exercises))
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_variant(self, variant_id, name=None, exam_type=None, category=None, exercises=None):
        cursor = self.conn.cursor()
        
        if name and exam_type and category and exercises:
            cursor.execute(
                'UPDATE variants SET name = ?, exam_type = ?, category = ?, exercises = ? WHERE id = ?',
                (name, exam_type, category, json.dumps(exercises), variant_id)
            )
        elif name:
            cursor.execute(
                'UPDATE variants SET name = ? WHERE id = ?',
                (name, variant_id)
            )
        elif category:
            cursor.execute(
                'UPDATE variants SET category = ? WHERE id = ?',
                (category, variant_id)
            )
        elif exercises is not None:
            cursor.execute(
                'UPDATE variants SET exercises = ? WHERE id = ?',
                (json.dumps(exercises), variant_id)
            )
        
        self.conn.commit()
    
    def delete_variant(self, variant_id):
        """Удаляет вариант и все связанные данные"""
        cursor = self.conn.cursor()
        
        # Удаляем ответы студентов на этот вариант
        cursor.execute('DELETE FROM student_answers WHERE variant_id = ?', (variant_id,))
        
        # Удаляем неправильные ответы на этот вариант
        cursor.execute('DELETE FROM wrong_exercises WHERE variant_id = ?', (variant_id,))
        
        # Удаляем сам вариант
        cursor.execute('DELETE FROM variants WHERE id = ?', (variant_id,))
        
        self.conn.commit()
    
    def save_student_answer(self, student_id, variant_id, exercise_id, user_answer, is_correct):
        cursor = self.conn.cursor()
        cursor.execute(
            '''INSERT INTO student_answers 
            (student_id, variant_id, exercise_id, user_answer, is_correct) 
            VALUES (?, ?, ?, ?, ?)''',
            (student_id, variant_id, exercise_id, user_answer, is_correct)
        )
        
        if not is_correct:
            cursor.execute(
                '''INSERT OR IGNORE INTO wrong_exercises 
                (student_id, variant_id, exercise_id) 
                VALUES (?, ?, ?)''',
                (student_id, variant_id, exercise_id)
            )
        
        self.conn.commit()
    
    def get_student_statistics(self, student_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as total, SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM student_answers WHERE student_id = ?
        ''', (student_id,))
        stats = cursor.fetchone()
        
        if stats and stats[0] > 0:
            accuracy = (stats[1] / stats[0]) * 100
        else:
            accuracy = 0
            
        cursor.execute('SELECT COUNT(*) FROM wrong_exercises WHERE student_id = ?', (student_id,))
        wrong_count = cursor.fetchone()[0]
        
        return {
            'total_exercises': stats[0] if stats else 0,
            'correct_answers': stats[1] if stats else 0,
            'accuracy': round(accuracy, 2),
            'wrong_exercises': wrong_count
        }
    
    def get_wrong_exercises_stats(self, student_id):
        """Получает статистику по ошибкам ученика"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as total_wrong, 
                   COUNT(DISTINCT variant_id) as variants_with_errors
            FROM wrong_exercises 
            WHERE student_id = ?
        ''', (student_id,))
        result = cursor.fetchone()
        return {
            'total_wrong': result[0] if result else 0,
            'variants_with_errors': result[1] if result else 0
        }

    def get_wrong_exercises(self, student_id):
        """Получает все упражнения с ошибками для ученика"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT we.variant_id, we.exercise_id, v.name as variant_name, v.exercises
            FROM wrong_exercises we
            JOIN variants v ON we.variant_id = v.id
            WHERE we.student_id = ?
        ''', (student_id,))
        return cursor.fetchall()
    
    def add_lesson(self, student_id, student_name, lesson_time):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO schedule (student_id, student_name, lesson_time) VALUES (?, ?, ?)',
            (student_id, student_name, lesson_time)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_upcoming_lessons(self):
        cursor = self.conn.cursor()
        now = datetime.now()
        future = now + timedelta(days=7)
        cursor.execute('''
            SELECT id, student_id, student_name, lesson_time FROM schedule 
            WHERE lesson_time BETWEEN ? AND ? ORDER BY lesson_time
        ''', (now, future))
        return cursor.fetchall()
    
    def get_student_lessons(self, student_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, lesson_time FROM schedule 
            WHERE student_id = ? AND lesson_time > ? ORDER BY lesson_time
        ''', (student_id, datetime.now()))
        return cursor.fetchall()
    
    def get_lessons_for_notification(self):
        """Получает уроки, для которых нужно отправить уведомление"""
        cursor = self.conn.cursor()
        now = datetime.now()
        notification_time = now + timedelta(hours=1)
        
        # Ищем уроки, которые начнутся через час и еще не было уведомления
        cursor.execute('''
            SELECT id, student_id, student_name, lesson_time 
            FROM schedule 
            WHERE lesson_time BETWEEN ? AND ? 
            AND notified = 0 
            AND lesson_time > ?
        ''', (notification_time - timedelta(minutes=5), notification_time + timedelta(minutes=5), now))
        
        return cursor.fetchall()
    
    def mark_lesson_notified(self, lesson_id):
        """Помечает урок как уведомленный"""
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE schedule SET notified = 1 WHERE id = ?',
            (lesson_id,)
        )
        self.conn.commit()
    
    def delete_lesson(self, lesson_id):
        """Удаляет урок по ID"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM schedule WHERE id = ?', (lesson_id,))
        self.conn.commit()
        return cursor.rowcount > 0

# Инициализация
db = SimpleDB()
user_states = {}

class NotificationManager:
    """Менеджер уведомлений о предстоящих уроках"""
    
    @staticmethod
    async def send_lesson_notification(context: ContextTypes.DEFAULT_TYPE):
        """Отправляет уведомления о предстоящих уроках"""
        try:
            lessons_to_notify = db.get_lessons_for_notification()
            
            for lesson_id, student_id, student_name, lesson_time in lessons_to_notify:
                # Форматируем время для сообщения
                if isinstance(lesson_time, str):
                    lesson_time = datetime.fromisoformat(lesson_time)
                
                time_str = lesson_time.strftime("%d.%m.%Y в %H:%M")
                
                # Сообщение для ученика
                student_message = (
                    f"🔔 Напоминание о уроке!\n\n"
                    f"У вас урок с репетитором по математике через 1 час:\n"
                    f"📅 {time_str}\n\n"
                    f"Будьте готовы! 📚"
                )
                
                # Сообщение для репетитора
                tutor_message = (
                    f"🔔 Напоминание о уроке!\n\n"
                    f"У вас урок с учеником {student_name} через 1 час:\n"
                    f"📅 {time_str}\n\n"
                    f"ID ученика: {student_id}"
                )
                
                # Отправляем уведомление ученику
                try:
                    await context.bot.send_message(
                        chat_id=student_id,
                        text=student_message
                    )
                    print(f"✅ Уведомление отправлено ученику {student_name} ({student_id})")
                except Exception as e:
                    print(f"❌ Не удалось отправить уведомление ученику {student_id}: {e}")
                
                # Отправляем уведомление всем репетиторам
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=tutor_message
                        )
                        print(f"✅ Уведомление отправлено репетитору {admin_id}")
                    except Exception as e:
                        print(f"❌ Не удалось отправить уведомление репетитору {admin_id}: {e}")
                
                # Помечаем урок как уведомленный
                db.mark_lesson_notified(lesson_id)
                print(f"✅ Урок {lesson_id} помечен как уведомленный")
                
        except Exception as e:
            print(f"❌ Ошибка в отправке уведомлений: {e}")

class SimpleStudentStats:
    @staticmethod
    async def show_complete_stats(update: Update, user_id: int):
        """Показывает полную статистику ученика с учетом экзаменов"""
        try:
            stats = db.get_student_statistics(user_id)
            
            # Статистика по экзаменам и категориям
            cursor = db.conn.cursor()
            cursor.execute('''
                SELECT v.exam_type, v.category, 
                       COUNT(sa.id) as total,
                       SUM(CASE WHEN sa.is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM student_answers sa
                JOIN variants v ON sa.variant_id = v.id
                WHERE sa.student_id = ?
                GROUP BY v.exam_type, v.category
                ORDER BY v.exam_type, v.category
            ''', (user_id,))
            
            exam_stats = cursor.fetchall()
            
            stats_text = "📊 ВАША СТАТИСТИКА\n\n"
            
            # Общая статистика
            stats_text += f"📈 ОБЩИЕ РЕЗУЛЬТАТЫ:\n"
            stats_text += f"• Всего решено: {stats['total_exercises']} заданий\n"
            stats_text += f"• Правильных ответов: {stats['correct_answers']}\n"
            stats_text += f"• Точность: {stats['accuracy']}%\n"
            stats_text += f"• Ошибок для повторения: {stats['wrong_exercises']}\n\n"
            
            # Статистика по экзаменам и категориям
            if exam_stats:
                current_exam = None
                for exam_type, category, total, correct in exam_stats:
                    if exam_type != current_exam:
                        stats_text += f"🎯 {exam_type}:\n"
                        current_exam = exam_type
                    
                    accuracy = (correct / total * 100) if total > 0 else 0
                    stats_text += f"  • {category}: {correct}/{total} ({accuracy:.1f}%)\n"
                
                stats_text += f"\n"
            else:
                stats_text += f"📚 Статистика по экзаменам появится после решения вариантов\n\n"
            
            # Мотивационное сообщение
            if stats['total_exercises'] == 0:
                stats_text += "🎯 Начните решать варианты, чтобы увидеть свою статистику!"
            elif stats['accuracy'] >= 80:
                stats_text += "🎉 Отличные результаты! Так держать!"
            elif stats['accuracy'] >= 60:
                stats_text += "💪 Хорошие результаты! Продолжайте в том же духе!"
            else:
                stats_text += "📚 Есть над чем поработать! Используйте 'Повторить ошибки'."
            
            await update.message.reply_text(stats_text)
            
        except Exception as e:
            print(f"Ошибка в show_complete_stats: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке статистики")

class WrongExercisesManager:
    """Управление повторением ошибочных упражнений"""
    
    @staticmethod
    async def start_wrong_exercises(update: Update, user_id: int):
        """Начинает повторение ошибок"""
        wrong_exercises = db.get_wrong_exercises(user_id)
        
        if not wrong_exercises:
            await update.message.reply_text(
                "🎉 У вас нет ошибок для повторения!",
                reply_markup=get_main_keyboard(is_admin=False)
            )
            return None
        
        # Собираем все упражнения с ошибками
        all_exercises = []
        for variant_id, exercise_id, variant_name, exercises_json in wrong_exercises:
            exercises_list = json.loads(exercises_json)
            for exercise in exercises_list:
                if exercise['id'] == exercise_id:
                    # Добавляем информацию о варианте
                    exercise['variant_id'] = variant_id
                    exercise['variant_name'] = variant_name
                    all_exercises.append(exercise)
        
        if not all_exercises:
            await update.message.reply_text("❌ Не удалось загрузить упражнения")
            return None
        
        # Перемешиваем упражнения
        random.shuffle(all_exercises)
        
        # Создаем состояние для повторения ошибок
        state = {
            'mode': 'solving_wrong_exercise',
            'exercises': all_exercises,
            'current_index': 0,
            'correct_answers': 0
        }
        
        await update.message.reply_text(
            f"🔁 Начинаем повторение ошибок!\n"
            f"Всего упражнений: {len(all_exercises)}\n\n"
            f"Первое упражнение:",
            reply_markup=get_back_keyboard()
        )
        
        # Отправляем первое упражнение
        await WrongExercisesManager.send_next_exercise(update, user_id, state)
        return state
    
    @staticmethod
    async def send_next_exercise(update: Update, user_id: int, state):
        """Отправляет следующее упражнение для повторения"""
        index = state['current_index']
        exercises = state['exercises']
        
        if index >= len(exercises):
            await WrongExercisesManager.finish_wrong_exercises(update, user_id, state)
            return
        
        exercise = exercises[index]
        
        await update.message.reply_text(
            f"📝 Упражнение {index + 1} из {len(exercises)}\n"
            f"📄 Вариант: {exercise['variant_name']}\n\n"
            f"{exercise['question']}\n\n"
            f"💡 Введите ваш ответ:",
            reply_markup=get_back_keyboard()
        )
    
    @staticmethod
    async def finish_wrong_exercises(update: Update, user_id: int, state):
        """Завершает повторение ошибок"""
        total_exercises = len(state['exercises'])
        correct_answers = state['correct_answers']
        accuracy = (correct_answers / total_exercises) * 100 if total_exercises > 0 else 0
        
        await update.message.reply_text(
            f"🏁 Повторение ошибок завершено!\n\n"
            f"📊 Результаты:\n"
            f"• Правильных ответов: {correct_answers} из {total_exercises}\n"
            f"• Точность: {round(accuracy, 2)}%\n\n"
            f"{'🎉 Отличный результат!' if accuracy > 80 else '💪 Продолжайте работать!'}",
            reply_markup=get_main_keyboard(is_admin=False)
        )
        
        # Удаляем состояние
        if user_id in user_states:
            del user_states[user_id]

def get_exam_keyboard():
    """Клавиатура для выбора экзамена"""
    return ReplyKeyboardMarkup([
        ['ЕГЭ', 'ОГЭ'],
        ['🔙 Назад']
    ], resize_keyboard=True)

def get_main_keyboard(is_admin=False):
    if is_admin:
        return ReplyKeyboardMarkup([
            ['👥 Ученики', '📚 Варианты'],
            ['➕ Создать вариант', '📅 Расписание'],
            ['❓ Помощь']
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ['📚 Решать вариант'],
            ['📊 Моя статистика', '🔁 Повторить ошибки'],
            ['📅 Мои уроки', '❓ Помощь']
        ], resize_keyboard=True)

def get_categories_keyboard(exam_type=None):
    """Клавиатура для выбора категории с учетом типа экзамена"""
    if exam_type:
        categories = db.get_categories_by_exam(exam_type)
    else:
        categories = ['ФИПИ', 'Ященко']
    
    keyboard = [[category] for category in categories]
    keyboard.append(['🔙 Назад'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_variants_keyboard(exam_type, category, for_admin=False):
    """Клавиатура для выбора вариантов с учетом экзамена и категории"""
    variants = db.get_variants_by_exam_and_category(exam_type, category)
    keyboard = []
    for variant in variants:
        variant_id, name, exam_type_db, category_db, exercises, created_at = variant
        display_text = f"{name}"
        if for_admin:
            display_text = f"📄 {name}"
        keyboard.append([display_text])
    
    if for_admin:
        keyboard.append(['🔙 Назад'])
    else:
        keyboard.append(['🔙 К категориям'])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_variant_management_keyboard():
    return ReplyKeyboardMarkup([
        ['👁️ Просмотреть вариант', '✏️ Редактировать название'],
        ['🔄 Изменить категорию', '✏️ Управление номерами'],
        ['🗑️ Удалить вариант', '🔙 К вариантам']
    ], resize_keyboard=True)

def get_exercise_management_keyboard():
    return ReplyKeyboardMarkup([
        ['➕ Добавить номер', '✏️ Изменить номер'],
        ['🗑️ Удалить номер', '🔙 К управлению']
    ], resize_keyboard=True)

def get_back_keyboard():
    return ReplyKeyboardMarkup([['🔙 Назад']], resize_keyboard=True)

def get_schedule_keyboard():
    return ReplyKeyboardMarkup([
        ['📅 Предстоящие уроки', '➕ Добавить урок'],
        ['🗑️ Удалить урок', '🔙 Назад']
    ], resize_keyboard=True)

def get_lesson_deletion_keyboard():
    return ReplyKeyboardMarkup([
        ['✅ Да, удалить', '❌ Нет, отменить'],
        ['🔙 Назад']
    ], resize_keyboard=True)

def parse_datetime(date_str, time_str):
    try:
        date_parts = date_str.split('.')
        time_parts = time_str.split(':')
        
        if len(date_parts) != 3 or len(time_parts) != 2:
            return None
            
        day, month, year = map(int, date_parts)
        hour, minute = map(int, time_parts)
        
        if year < 100:
            year += 2000
            
        lesson_time = datetime(year, month, day, hour, minute)
        
        if lesson_time <= datetime.now():
            return None
            
        return lesson_time
    except:
        return None

def normalize_number(answer):
    if not answer:
        return answer
    normalized = answer.strip().replace(',', '.').replace(' ', '')
    if '.' in normalized:
        normalized = normalized.rstrip('0').rstrip('.')
    return normalized

def check_answer(user_answer, correct_answer):
    user_normalized = normalize_number(user_answer)
    correct_normalized = normalize_number(correct_answer)
    return user_normalized == correct_normalized

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS
    db.add_user(user.id, user.username, 'admin' if is_admin else 'student')
    
    # Всегда очищаем состояние при старте
    if user.id in user_states:
        del user_states[user.id]
    
    if is_admin:
        text = f"👋 Добро пожаловать, репетитор {user.first_name}!"
    else:
        text = f"👋 Привет, {user.first_name}! Я бот-репетитор по математике!"
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard(is_admin))

async def handle_exercise_answer(update: Update, user_id: int, user_answer: str):
    """Обрабатывает ответ на упражнение"""
    if user_answer == '🔙 Назад':
        await update.message.reply_text(
            "❌ Решение варианта прервано.",
            reply_markup=get_main_keyboard(is_admin=False)
        )
        if user_id in user_states:
            del user_states[user_id]
        return
    
    state = user_states[user_id]
    index = state['current_index']
    exercise = state['exercises'][index]
    
    # Проверяем ответ
    is_correct = check_answer(user_answer, exercise['correct_answer'])
    
    # Сохраняем в базу
    db.save_student_answer(
        user_id, 
        state['variant_id'], 
        exercise['id'], 
        user_answer, 
        is_correct
    )
    
    # Увеличиваем счетчик правильных ответов
    if is_correct:
        state['correct_answers'] += 1
    
    # Отправляем результат
    if is_correct:
        await update.message.reply_text("✅ Правильно! 🎉")
    else:
        await update.message.reply_text(f"❌ Неправильно. Правильный ответ: {exercise['correct_answer']}")
    
    # Переходим к следующему упражнению
    state['current_index'] += 1
    
    # Ждем немного перед следующим вопросом
    await asyncio.sleep(1)
    
    await send_next_exercise(update, user_id)

async def send_next_exercise(update: Update, user_id: int):
    """Отправляет следующее упражнение"""
    state = user_states[user_id]
    index = state['current_index']
    exercises = state['exercises']
    
    if index >= len(exercises):
        await finish_variant(update, user_id)
        return
    
    exercise = exercises[index]
    
    await update.message.reply_text(
        f"📝 Упражнение {index + 1} из {len(exercises)}\n\n"
        f"{exercise['question']}\n\n"
        f"💡 Введите ваш ответ (можно использовать запятую для дробей):",
        reply_markup=get_back_keyboard()
    )

async def finish_variant(update: Update, user_id: int):
    """Завершает вариант и показывает статистику"""
    state = user_states[user_id]
    total_exercises = len(state['exercises'])
    correct_answers = state['correct_answers']
    accuracy = (correct_answers / total_exercises) * 100 if total_exercises > 0 else 0
    
    await update.message.reply_text(
        f"🏁 Вариант '{state['variant_name']}' завершен!\n\n"
        f"📊 Результаты:\n"
        f"• Правильных ответов: {correct_answers} из {total_exercises}\n"
        f"• Точность: {round(accuracy, 2)}%\n\n"
        f"{'🎉 Отличный результат!' if accuracy > 80 else '💪 Продолжайте работать!'}",
        reply_markup=get_main_keyboard(is_admin=False)
    )
    
    if user_id in user_states:
        del user_states[user_id]

async def handle_wrong_exercise_solving(update: Update, user_id: int, text: str):
    """Обрабатывает решение упражнений с ошибками"""
    if text == '🔙 Назад':
        await update.message.reply_text(
            "❌ Повторение ошибок прервано.",
            reply_markup=get_main_keyboard(is_admin=False)
        )
        if user_id in user_states:
            del user_states[user_id]
        return
    
    state = user_states[user_id]
    index = state['current_index']
    exercise = state['exercises'][index]
    
    # Проверяем ответ
    is_correct = check_answer(text, exercise['correct_answer'])
    
    if is_correct:
        # Удаляем из wrong_exercises если ответ правильный
        cursor = db.conn.cursor()
        cursor.execute(
            'DELETE FROM wrong_exercises WHERE student_id = ? AND variant_id = ? AND exercise_id = ?',
            (user_id, exercise['variant_id'], exercise['id'])
        )
        db.conn.commit()
        
        state['correct_answers'] += 1
        await update.message.reply_text("✅ Правильно! 🎉")
    else:
        await update.message.reply_text(f"❌ Неправильно. Правильный ответ: {exercise['correct_answer']}")
    
    # Переходим к следующему упражнению
    state['current_index'] += 1
    await asyncio.sleep(1)
    await WrongExercisesManager.send_next_exercise(update, user_id, state)

async def handle_lesson_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):    
    """Обрабатывает создание урока"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        await update.message.reply_text(
            "❌ Создание урока отменено.",
            reply_markup=get_main_keyboard(is_admin=True)
        )
        if user_id in user_states:
            del user_states[user_id]
        return
    
    if 'step' not in state:
        students = db.get_all_students()
        if not students:
            await update.message.reply_text("❌ Нет учеников для записи")
            if user_id in user_states:
                del user_states[user_id]
            return
        
        students_text = "👥 Выберите ученика:\n\n"
        for i, (student_id, username) in enumerate(students, 1):
            students_text += f"{i}. {username or 'Без имени'}\n"
        
        state['step'] = 'choose_student'
        state['students'] = students
        await update.message.reply_text(students_text + "\nВведите номер ученика:")
    
    elif state['step'] == 'choose_student':
        try:
            student_index = int(text) - 1
            if 0 <= student_index < len(state['students']):
                student_id, username = state['students'][student_index]
                state['selected_student_id'] = student_id
                state['selected_student_name'] = username or 'Ученик'
                state['step'] = 'choose_date'
                
                today = datetime.now().strftime("%d.%m.%Y")
                await update.message.reply_text(
                    f"📅 Выбран ученик: {state['selected_student_name']}\n\n"
                    f"Введите дату урока в формате ДД.ММ.ГГГГ\n"
                    f"Например: {today}"
                )
            else:
                await update.message.reply_text("❌ Неверный номер ученика. Попробуйте снова:")
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите номер ученика:")
    
    elif state['step'] == 'choose_date':
        state['lesson_date'] = text.strip()
        state['step'] = 'choose_time'
        
        await update.message.reply_text(
            f"🕐 Дата: {state['lesson_date']}\n\n"
            f"Введите время урока в формате ЧЧ:ММ\n"
            f"Например: 14:30 или 09:00"
        )
    
    elif state['step'] == 'choose_time':
        lesson_time_str = text.strip()
        lesson_time = parse_datetime(state['lesson_date'], lesson_time_str)
        
        if lesson_time:
            # Сохраняем урок в базу
            lesson_id = db.add_lesson(
                state['selected_student_id'],
                state['selected_student_name'],
                lesson_time
            )
            
            time_str = lesson_time.strftime("%d.%m.%Y в %H:%M")
            
            # Отправляем подтверждение ученику
            try:
                student_message = (
                    f"✅ Урок успешно запланирован!\n\n"
                    f"📅 Дата и время: {time_str}\n"
                    f"👤 Репетитор: Математика с Сашей\n\n"
                    f"🔔 Вы получите уведомление за 1 час до начала урока."
                )
                await context.bot.send_message(
                    chat_id=state['selected_student_id'],
                    text=student_message
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение ученику: {e}")
            
            await update.message.reply_text(
                f"✅ Урок успешно добавлен!\n\n"
                f"👤 Ученик: {state['selected_student_name']}\n"
                f"📅 Время: {time_str}\n\n"
                f"🔔 Уведомления будут отправлены за 1 час до урока.",
                reply_markup=get_main_keyboard(is_admin=True)
            )
        else:
            await update.message.reply_text(
                "❌ Неверный формат даты или времени.\n\n"
                "Пожалуйста, введите время в формате ЧЧ:ММ\n"
                "Например: 14:30"
            )
            return
        
        if user_id in user_states:
            del user_states[user_id]

async def handle_lesson_deletion(update: Update, user_id: int, text: str):
    """Обрабатывает удаление урока"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        await update.message.reply_text(
            "❌ Удаление урока отменено.",
            reply_markup=get_schedule_keyboard()
        )
        if user_id in user_states:
            del user_states[user_id]
        return
    
    if 'step' not in state:
        # Показываем список уроков для удаления
        lessons = db.get_upcoming_lessons()
        if not lessons:
            await update.message.reply_text(
                "📭 Нет предстоящих уроков для удаления.",
                reply_markup=get_schedule_keyboard()
            )
            if user_id in user_states:
                del user_states[user_id]
            return
        
        lessons_text = "🗑️ Выберите урок для удаления:\n\n"
        for i, (lesson_id, student_id, student_name, lesson_time) in enumerate(lessons, 1):
            # Преобразуем строку в datetime если нужно
            if isinstance(lesson_time, str):
                lesson_time = datetime.fromisoformat(lesson_time)
            time_str = lesson_time.strftime("%d.%m.%Y в %H:%M")
            lessons_text += f"{i}. {student_name} - {time_str}\n"
        
        state['step'] = 'choose_lesson'
        state['lessons'] = lessons
        
        await update.message.reply_text(
            lessons_text + "\nВведите номер урока для удаления:",
            reply_markup=get_back_keyboard()
        )
    
    elif state['step'] == 'choose_lesson':
        try:
            lesson_index = int(text) - 1
            if 0 <= lesson_index < len(state['lessons']):
                lesson_id, student_id, student_name, lesson_time = state['lessons'][lesson_index]
                
                # Преобразуем строку в datetime если нужно
                if isinstance(lesson_time, str):
                    lesson_time = datetime.fromisoformat(lesson_time)
                
                time_str = lesson_time.strftime("%d.%m.%Y в %H:%M")
                state['selected_lesson_id'] = lesson_id
                state['selected_lesson_info'] = f"{student_name} - {time_str}"
                state['selected_student_id'] = student_id
                state['step'] = 'confirm_deletion'
                
                await update.message.reply_text(
                    f"🗑️ Вы уверены, что хотите удалить урок?\n\n"
                    f"👤 Ученик: {student_name}\n"
                    f"📅 Время: {time_str}\n\n"
                    f"Это действие нельзя отменить!",
                    reply_markup=get_lesson_deletion_keyboard()
                )
            else:
                await update.message.reply_text("❌ Неверный номер урока. Попробуйте снова:")
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите номер урока:")
    
    elif state['step'] == 'confirm_deletion':
        if text == '✅ Да, удалить':
            # Удаляем урок
            success = db.delete_lesson(state['selected_lesson_id'])
            
            if success:
                await update.message.reply_text(
                    f"✅ Урок успешно удален!\n\n"
                    f"{state['selected_lesson_info']}",
                    reply_markup=get_main_keyboard(is_admin=True)
                )
            else:
                await update.message.reply_text(
                    "❌ Не удалось удалить урок. Возможно, он уже был удален.",
                    reply_markup=get_main_keyboard(is_admin=True)
                )
            
            if user_id in user_states:
                del user_states[user_id]
        
        elif text == '❌ Нет, отменить':
            await update.message.reply_text(
                "❌ Удаление урока отменено.",
                reply_markup=get_schedule_keyboard()
            )
            if user_id in user_states:
                del user_states[user_id]
        
        else:
            await update.message.reply_text(
                "❌ Пожалуйста, выберите действие:",
                reply_markup=get_lesson_deletion_keyboard()
            )

async def handle_variant_creation(update: Update, user_id: int, text: str):
    """Обрабатывает создание варианта с учетом экзамена"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        if user_id in user_states:
            del user_states[user_id]
        await update.message.reply_text("🔙 Главное меню", reply_markup=get_main_keyboard(is_admin=True))
        return
    
    if state['step'] == 'choose_exam':
        exam_types = db.get_exam_types()
        if text in exam_types:
            state['selected_exam'] = text
            state['step'] = 'choose_category'
            await update.message.reply_text(
                f"✅ Экзамен: {text}\n\n"
                f"Выберите категорию:",
                reply_markup=get_categories_keyboard(text)
            )
        else:
            await update.message.reply_text("❌ Пожалуйста, выберите экзамен из списка:")
    
    elif state['step'] == 'choose_category':
        categories = db.get_categories_by_exam(state['selected_exam'])
        if text in categories:
            state['selected_category'] = text
            state['step'] = 'enter_name'
            await update.message.reply_text(
                f"✅ Экзамен: {state['selected_exam']}\n"
                f"✅ Категория: {text}\n\n"
                f"Введите название варианта:\n"
                f"Например: 'Вариант 3 - Профильный уровень'"
            )
        else:
            await update.message.reply_text("❌ Пожалуйста, выберите категорию из списка:")
    
    elif state['step'] == 'enter_name':
        state['variant_name'] = text
        state['step'] = 'enter_exercises'
        state['exercises'] = []
        state['current_exercise'] = 1
        
        await update.message.reply_text(
            f"✅ Название варианта: {text}\n\n"
            f"Теперь введите упражнения. Для каждого упражнения введите вопрос, а затем правильный ответ.\n\n"
            f"Введите вопрос для упражнения 1:"
        )
    
    elif state['step'] == 'enter_exercises':
        # Проверяем, не хочет ли пользователь завершить
        if text.lower() == 'готово':
            if state['exercises']:
                db.add_variant(
                    state['variant_name'], 
                    state['selected_exam'], 
                    state['selected_category'], 
                    state['exercises']
                )
                
                await update.message.reply_text(
                    f"🎉 Вариант успешно создан!\n\n"
                    f"📁 Экзамен: {state['selected_exam']}\n"
                    f"📁 Категория: {state['selected_category']}\n"
                    f"📝 Название: {state['variant_name']}\n"
                    f"📊 Упражнений: {len(state['exercises'])}\n\n"
                    f"Теперь ученики могут решать этот вариант!",
                    reply_markup=get_main_keyboard(is_admin=True)
                )
            else:
                await update.message.reply_text(
                    "❌ Нельзя создать вариант без упражнений",
                    reply_markup=get_main_keyboard(is_admin=True)
                )
            
            if user_id in user_states:
                del user_states[user_id]
            return
        
        # Если это не команда "готово", продолжаем добавлять упражнения
        if 'current_question' not in state:
            # Сохраняем вопрос
            state['current_question'] = text
            await update.message.reply_text(
                f"❓ Вопрос: {text}\n\n"
                f"Введите правильный ответ:"
            )
        else:
            # Сохраняем ответ и добавляем упражнение
            exercise = {
                'id': state['current_exercise'],
                'question': state['current_question'],
                'correct_answer': text
            }
            state['exercises'].append(exercise)
            
            # Подготовка к следующему упражнению
            state['current_exercise'] += 1
            del state['current_question']
            
            await update.message.reply_text(
                f"✅ Упражнение {exercise['id']} добавлено!\n\n"
                f"Добавить еще одно упражнение?\n"
                f"Введите следующий вопрос или 'готово' чтобы завершить:"
            )

async def handle_variant_selection(update: Update, user_id: int, text: str):
    """Обрабатывает выбор варианта учеником"""
    if text == '🔙 К категориям':
        # Возвращаемся к выбору категории
        state = user_states[user_id]
        state['mode'] = 'choosing_category'
        state['purpose'] = 'solving'
        await update.message.reply_text(
            "📚 Выберите категорию вариантов:",
            reply_markup=get_categories_keyboard(state.get('selected_exam'))
        )
        return
    
    state = user_states[user_id]
    
    # Ищем выбранный вариант
    selected_variant = None
    for variant in state['variants']:
        variant_id, name, exam_type, category, exercises, created_at = variant
        if text == name:
            selected_variant = variant
            break

    if selected_variant:
        variant_id, name, exam_type, category, exercises, created_at = selected_variant
        exercises_list = json.loads(exercises)

        # Устанавливаем состояние решения варианта
        user_states[user_id] = {
            'mode': 'solving_variant',
            'variant_id': variant_id,
            'variant_name': name,
            'exercises': exercises_list,
            'current_index': 0,
            'correct_answers': 0
        }

        # Отправляем первое упражнение
        await send_next_exercise(update, user_id)
    else:
        await update.message.reply_text(
            "❌ Вариант не найден. Выберите из списка:",
            reply_markup=get_variants_keyboard(state['selected_exam'], state['selected_category'], for_admin=False)
        )

async def handle_variant_management(update: Update, user_id: int, text: str):
    """Обрабатывает управление вариантами для админа"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        # Возврат к выбору экзамена
        state['mode'] = 'choosing_exam'
        state['purpose'] = 'managing'
        await update.message.reply_text(
            "📚 Управление вариантами\n\nВыберите экзамен:",
            reply_markup=get_exam_keyboard()
        )
        return
    
    # Поиск выбранного варианта
    selected_variant = None
    for variant in state['variants']:
        variant_id, name, exam_type, category, exercises, created_at = variant
        if text == f"📄 {name}":
            selected_variant = variant
            break
    
    if selected_variant:
        variant_id, name, exam_type, category, exercises, created_at = selected_variant
        state['selected_variant'] = selected_variant
        state['selected_variant_id'] = variant_id
        state['mode'] = 'managing_variant'
        
        # Показываем информацию о варианте и меню управления
        exercises_list = json.loads(exercises)
        variant_info = f"📄 Вариант: {name}\n"
        variant_info += f"📁 Экзамен: {exam_type}\n"
        variant_info += f"📁 Категория: {category}\n"
        variant_info += f"📊 Упражнений: {len(exercises_list)}\n\n"
        
        variant_info += "📝 Упражнения:\n"
        for i, exercise in enumerate(exercises_list, 1):
            question_preview = exercise['question'][:50] + "..." if len(exercise['question']) > 50 else exercise['question']
            variant_info += f"{i}. {question_preview}\n"
        
        await update.message.reply_text(
            variant_info,
            reply_markup=get_variant_management_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Вариант не найден. Выберите из списка:",
            reply_markup=get_variants_keyboard(state['selected_exam'], state['selected_category'], for_admin=True)
        )

async def handle_variant_actions(update: Update, user_id: int, text: str):
    """Обрабатывает действия с вариантом"""
    state = user_states[user_id]
    
    if text == '🔙 К вариантам':
        # Возврат к списку вариантов
        state['mode'] = 'managing_variants'
        await update.message.reply_text(
            f"🔧 Управление вариантами\nКатегория: {state['selected_category']}\n\nВыберите вариант:",
            reply_markup=get_variants_keyboard(state['selected_exam'], state['selected_category'], for_admin=True)
        )
        return
    
    if text == '👁️ Просмотреть вариант':
        # Показываем детальную информацию о варианте
        variant = state['selected_variant']
        variant_id, name, exam_type, category, exercises, created_at = variant
        exercises_list = json.loads(exercises)
        
        variant_info = f"📄 Вариант: {name}\n"
        variant_info += f"📁 Экзамен: {exam_type}\n"
        variant_info += f"📁 Категория: {category}\n\n"
        
        variant_info += "📝 Упражнения:\n\n"
        for i, exercise in enumerate(exercises_list, 1):
            variant_info += f"{i}. {exercise['question']}\n"
            variant_info += f"   Ответ: {exercise['correct_answer']}\n\n"
        
        await update.message.reply_text(variant_info)
    
    elif text == '✏️ Редактировать название':
        state['mode'] = 'editing_variant_name'
        await update.message.reply_text(
            "✏️ Введите новое название варианта:",
            reply_markup=get_back_keyboard()
        )
    
    elif text == '🔄 Изменить категорию':
        state['mode'] = 'editing_variant_category'
        await update.message.reply_text(
            "🔄 Выберите новую категорию:",
            reply_markup=get_categories_keyboard(state['selected_variant'][2])
        )
    
    elif text == '✏️ Управление номерами':
        state['mode'] = 'managing_exercises'
        await show_exercises_management(update, user_id)
    
    elif text == '🗑️ Удалить вариант':
        state['mode'] = 'deleting_variant'
        variant_name = state['selected_variant'][1]
        await update.message.reply_text(
            f"🗑️ Вы уверены, что хотите удалить вариант '{variant_name}'?\n\n"
            f"Это действие нельзя отменить!\n"
            f"Введите 'да' для подтверждения или 'нет' для отмены:",
            reply_markup=get_back_keyboard()
        )

async def show_exercises_management(update: Update, user_id: int):
    """Показывает управление номерами варианта"""
    state = user_states[user_id]
    variant = state['selected_variant']
    exercises_list = json.loads(variant[4])
    
    exercises_text = f"📝 Управление номерами варианта:\n{state['selected_variant'][1]}\n\n"
    
    if exercises_list:
        exercises_text += "📋 Текущие номера:\n\n"
        for i, exercise in enumerate(exercises_list, 1):
            exercises_text += f"{i}. {exercise['question'][:60]}...\n"
    else:
        exercises_text += "📭 В варианте пока нет номеров\n"
    
    await update.message.reply_text(
        exercises_text,
        reply_markup=get_exercise_management_keyboard()
    )

async def handle_exercise_management(update: Update, user_id: int, text: str):
    """Обрабатывает управление номерами варианта"""
    state = user_states[user_id]
    
    if text == '➕ Добавить номер':
        state['mode'] = 'adding_exercise'
        state['exercise_step'] = 'waiting_question'
        await update.message.reply_text(
            "📝 Добавление нового номера\n\nВведите вопрос для нового номера:",
            reply_markup=get_back_keyboard()
        )
    
    elif text == '✏️ Изменить номер':
        variant = state['selected_variant']
        exercises_list = json.loads(variant[4])
        
        if not exercises_list:
            await update.message.reply_text("❌ В варианте нет номеров для изменения")
            return
        
        exercises_text = "📝 Выберите номер для изменения:\n\n"
        for i, exercise in enumerate(exercises_list, 1):
            exercises_text += f"{i}. {exercise['question'][:50]}...\n"
        
        state['mode'] = 'editing_exercise'
        state['exercise_step'] = 'choosing_exercise'
        state['exercises_list'] = exercises_list
        
        await update.message.reply_text(
            exercises_text + "\nВведите номер упражнения для изменения:",
            reply_markup=get_back_keyboard()
        )
    
    elif text == '🗑️ Удалить номер':
        variant = state['selected_variant']
        exercises_list = json.loads(variant[4])
        
        if not exercises_list:
            await update.message.reply_text("❌ В варианте нет номеров для удаления")
            return
        
        exercises_text = "🗑️ Выберите номер для удаления:\n\n"
        for i, exercise in enumerate(exercises_list, 1):
            exercises_text += f"{i}. {exercise['question'][:50]}...\n"
        
        state['mode'] = 'deleting_exercise'
        state['exercises_list'] = exercises_list
        
        await update.message.reply_text(
            exercises_text + "\nВведите номер упражнения для удаления:",
            reply_markup=get_back_keyboard()
        )
    
    elif text == '🔙 К управлению':
        state['mode'] = 'managing_variant'
        await update.message.reply_text(
            "🔙 Возврат к управлению вариантом",
            reply_markup=get_variant_management_keyboard()
        )

async def handle_adding_exercise(update: Update, user_id: int, text: str):
    """Обрабатывает добавление нового номера"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        state['mode'] = 'managing_exercises'
        await show_exercises_management(update, user_id)
        return
    
    if state['exercise_step'] == 'waiting_question':
        state['new_question'] = text
        state['exercise_step'] = 'waiting_answer'
        await update.message.reply_text(
            "✅ Вопрос сохранен!\n\nТеперь введите правильный ответ:",
            reply_markup=get_back_keyboard()
        )
    
    elif state['exercise_step'] == 'waiting_answer':
        new_answer = text
        variant = state['selected_variant']
        exercises_list = json.loads(variant[4])
        
        # Создаем новый номер
        new_exercise = {
            'id': len(exercises_list) + 1,
            'question': state['new_question'],
            'correct_answer': new_answer
        }
        
        exercises_list.append(new_exercise)
        
        # Сохраняем в базу
        db.update_variant(state['selected_variant_id'], exercises=exercises_list)
        
        await update.message.reply_text(
            "✅ Новый номер успешно добавлен в вариант!",
            reply_markup=get_exercise_management_keyboard()
        )
        
        # Обновляем состояние
        state['selected_variant'] = db.get_variant_by_id(state['selected_variant_id'])
        state['mode'] = 'managing_exercises'

async def handle_editing_exercise(update: Update, user_id: int, text: str):
    """Обрабатывает изменение номера"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        state['mode'] = 'managing_exercises'
        await show_exercises_management(update, user_id)
        return
    
    if state['exercise_step'] == 'choosing_exercise':
        try:
            exercise_num = int(text) - 1
            if 0 <= exercise_num < len(state['exercises_list']):
                state['selected_exercise_index'] = exercise_num
                state['exercise_step'] = 'editing_question'
                
                exercise = state['exercises_list'][exercise_num]
                await update.message.reply_text(
                    f"✏️ Редактирование номера {text}\n\n"
                    f"Текущий вопрос: {exercise['question']}\n\n"
                    f"Введите новый вопрос:",
                    reply_markup=get_back_keyboard()
                )
            else:
                await update.message.reply_text("❌ Неверный номер упражнения")
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите номер упражнения")
    
    elif state['exercise_step'] == 'editing_question':
        state['exercises_list'][state['selected_exercise_index']]['question'] = text
        state['exercise_step'] = 'editing_answer'
        
        exercise = state['exercises_list'][state['selected_exercise_index']]
        await update.message.reply_text(
            f"✅ Вопрос обновлен!\n\n"
            f"Текущий ответ: {exercise['correct_answer']}\n\n"
            f"Введите новый правильный ответ:",
            reply_markup=get_back_keyboard()
        )
    
    elif state['exercise_step'] == 'editing_answer':
        state['exercises_list'][state['selected_exercise_index']]['correct_answer'] = text
        
        # Сохраняем в базу
        db.update_variant(state['selected_variant_id'], exercises=state['exercises_list'])
        
        await update.message.reply_text(
            "✅ Номер успешно обновлен!",
            reply_markup=get_exercise_management_keyboard()
        )
        
        # Обновляем состояние
        state['selected_variant'] = db.get_variant_by_id(state['selected_variant_id'])
        state['mode'] = 'managing_exercises'

async def handle_deleting_exercise(update: Update, user_id: int, text: str):
    """Обрабатывает удаление номера"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        state['mode'] = 'managing_exercises'
        await show_exercises_management(update, user_id)
        return
    
    try:
        exercise_num = int(text) - 1
        if 0 <= exercise_num < len(state['exercises_list']):
            # Удаляем упражнение
            deleted_exercise = state['exercises_list'].pop(exercise_num)
            
            # Обновляем ID оставшихся упражнений
            for i, exercise in enumerate(state['exercises_list']):
                exercise['id'] = i + 1
            
            # Сохраняем в базу
            db.update_variant(state['selected_variant_id'], exercises=state['exercises_list'])
            
            await update.message.reply_text(
                f"✅ Номер {text} успешно удален!",
                reply_markup=get_exercise_management_keyboard()
            )
            
            # Обновляем состояние
            state['selected_variant'] = db.get_variant_by_id(state['selected_variant_id'])
            state['mode'] = 'managing_exercises'
        else:
            await update.message.reply_text("❌ Неверный номер упражнения")
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите номер упражнения")

async def handle_variant_name_edit(update: Update, user_id: int, text: str):
    """Обрабатывает изменение названия варианта"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        state['mode'] = 'managing_variant'
        await update.message.reply_text(
            "🔙 Возврат к управлению вариантом",
            reply_markup=get_variant_management_keyboard()
        )
        return
    
    # Обновляем название варианта
    variant_id = state['selected_variant_id']
    db.update_variant(variant_id, name=text)
    
    await update.message.reply_text(
        f"✅ Название варианта обновлено на: {text}",
        reply_markup=get_variant_management_keyboard()
    )
    
    # Возвращаемся к управлению вариантом
    state['mode'] = 'managing_variant'

async def handle_variant_category_edit(update: Update, user_id: int, text: str):
    """Обрабатывает изменение категории варианта"""
    state = user_states[user_id]
    
    if text == '🔙 Назад':
        state['mode'] = 'managing_variant'
        await update.message.reply_text(
            "🔙 Возврат к управлению вариантом",
            reply_markup=get_variant_management_keyboard()
        )
        return
    
    categories = db.get_categories_by_exam(state['selected_variant'][2])
    if text in categories:
        # Обновляем категорию варианта
        variant_id = state['selected_variant_id']
        db.update_variant(variant_id, category=text)
        
        await update.message.reply_text(
            f"✅ Категория варианта изменена на: {text}",
            reply_markup=get_variant_management_keyboard()
        )
        
        # Возвращаемся к управлению вариантом
        state['mode'] = 'managing_variant'
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите категорию из списка:",
            reply_markup=get_categories_keyboard(state['selected_variant'][2])
        )

async def handle_variant_deletion(update: Update, user_id: int, text: str):
    """Обрабатывает удаление варианта"""
    state = user_states[user_id]
    
    if text.lower() in ['нет', 'отмена', '🔙 назад']:
        state['mode'] = 'managing_variant'
        await update.message.reply_text(
            "❌ Удаление отменено",
            reply_markup=get_variant_management_keyboard()
        )
        return
    
    if text.lower() in ['да', 'удалить']:
        # Удаляем вариант
        variant_id = state['selected_variant_id']
        variant_name = state['selected_variant'][1]
        
        db.delete_variant(variant_id)
        
        await update.message.reply_text(
            f"✅ Вариант '{variant_name}' удален!",
            reply_markup=get_main_keyboard(is_admin=True)
        )
        
        # Выходим из состояния
        if user_id in user_states:
            del user_states[user_id]
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, подтвердите удаление: 'да' или 'нет'"
        )

async def handle_admin_message(update: Update, text: str, user_id: int):
    """Обрабатывает сообщения администратора"""
    if text == '🔙 Назад':
        if user_id in user_states:
            del user_states[user_id]
        await update.message.reply_text("🔙 Главное меню", reply_markup=get_main_keyboard(is_admin=True))
        return
    
    if text == '📚 Варианты':
        user_states[user_id] = {
            'mode': 'choosing_exam',
            'purpose': 'managing'
        }
        await update.message.reply_text(
            "📚 Управление вариантами\n\nВыберите экзамен:",
            reply_markup=get_exam_keyboard()
        )
    
    elif text == '➕ Создать вариант':
        user_states[user_id] = {
            'mode': 'creating_variant',
            'step': 'choose_exam'
        }
        await update.message.reply_text(
            "📝 Создание нового варианта\n\n"
            "Выберите тип экзамена:",
            reply_markup=get_exam_keyboard()
        )
    
    elif text == '👥 Ученики':
        students = db.get_all_students()
        if students:
            students_text = "👥 Список учеников:\n\n"
            for i, (student_id, username) in enumerate(students, 1):
                stats = db.get_student_statistics(student_id)
                students_text += f"{i}. {username or 'Без имени'}\n"
                students_text += f"   📊 Решено: {stats['total_exercises']} | Точность: {stats['accuracy']}%\n\n"
            await update.message.reply_text(students_text)
        else:
            await update.message.reply_text("👥 Пока нет учеников")
    
    elif text == '📅 Расписание':
        await update.message.reply_text("📅 Управление расписанием:", reply_markup=get_schedule_keyboard())
    
    elif text == '📅 Предстоящие уроки':
        lessons = db.get_upcoming_lessons()
        if lessons:
            lessons_text = "📅 Предстоящие уроки:\n\n"
            for lesson_id, student_id, student_name, lesson_time in lessons:
                if isinstance(lesson_time, str):
                    lesson_time = datetime.fromisoformat(lesson_time)
                time_str = lesson_time.strftime("%d.%m.%Y в %H:%M")
                lessons_text += f"• {student_name} - {time_str}\n"
            await update.message.reply_text(lessons_text)
        else:
            await update.message.reply_text("📅 Нет предстоящих уроков")
    
    elif text == '➕ Добавить урок':
        user_states[user_id] = {
            'mode': 'adding_lesson',
            'step': 'choose_student'
        }
        
        students = db.get_all_students()
        if not students:
            await update.message.reply_text("❌ Нет учеников для записи")
            if user_id in user_states:
                del user_states[user_id]
            return

        students_text = "👥 Выберите ученика:\n\n"
        for i, (student_id, username) in enumerate(students, 1):
            students_text += f"{i}. {username or 'Без имени'}\n"

        state = user_states[user_id]
        state['students'] = students

        await update.message.reply_text(students_text + "\nВведите номер ученика:")
    
    elif text == '🗑️ Удалить урок':
        user_states[user_id] = {
            'mode': 'deleting_lesson'
        }
        await handle_lesson_deletion(update, user_id, "")
    
    elif text == '❓ Помощь':
        help_text = (
            "❓ ПОМОЩЬ ДЛЯ РЕПЕТИТОРА\n\n"
            "👥 Ученики - список всех учеников и их прогресс\n"
            "📚 Варианты - управление вариантами (создание, редактирование, удаление)\n"
            "➕ Создать вариант - создать новый вариант\n"
            "📅 Расписание - управление расписанием уроков\n\n"
            "Для управления вариантами:\n"
            "• Выберите экзамен и категорию\n"
            "• Можно просматривать, редактировать названия и категории\n"
            "• Управлять номерами (добавлять, изменять, удалять)\n"
            "• Удалять варианты полностью\n\n"
            "Для записи на уроки:\n"
            "• Выберите ученика из списка\n"
            "• Укажите дату и время урока\n\n"
            "🗑️ Удалить урок - отменить запланированный урок"
        )
        await update.message.reply_text(help_text)
    
    else:
        await update.message.reply_text("Не понимаю команду 😊")

async def handle_student_message(update: Update, text: str, user_id: int):
    """Обрабатывает сообщения ученика"""
    if text == '📚 Решать вариант':
        exam_types = db.get_exam_types()
        if not exam_types:
            await update.message.reply_text("📭 Пока нет доступных вариантов")
            return
        
        user_states[user_id] = {
            'mode': 'choosing_exam',
            'purpose': 'solving'
        }
        
        await update.message.reply_text(
            "📚 Выберите экзамен:",
            reply_markup=get_exam_keyboard()
        )
    
    elif text == '📊 Моя статистика':
        await SimpleStudentStats.show_complete_stats(update, user_id)
    
    elif text == '🔁 Повторить ошибки':
        # Показываем статистику ошибок
        stats = db.get_wrong_exercises_stats(user_id)
        
        if stats['total_wrong'] == 0:
            await update.message.reply_text(
                "🎉 У вас пока нет ошибок для повторения!\n\n"
                "Решайте варианты, и если будут ошибки, вы сможете вернуться к ним здесь.",
                reply_markup=get_main_keyboard(is_admin=False)
            )
        else:
            stats_text = (
                f"📊 Ваши ошибки:\n\n"
                f"• Всего ошибок: {stats['total_wrong']}\n"
                f"• Вариантов с ошибками: {stats['variants_with_errors']}\n"
            )
            
            stats_text += "\nНачать повторение ошибок?"
            
            # Создаем клавиатуру для подтверждения
            keyboard = ReplyKeyboardMarkup([
                ['✅ Начать повторение'],
                ['🔙 Назад']
            ], resize_keyboard=True)
            
            await update.message.reply_text(stats_text, reply_markup=keyboard)
            
            # Устанавливаем состояние ожидания подтверждения
            user_states[user_id] = {
                'mode': 'confirm_wrong_exercises',
                'stats': stats
            }
    
    elif text == '📅 Мои уроки':
        lessons = db.get_student_lessons(user_id)
        if lessons:
            lessons_text = "📅 Ваши уроки:\n\n"
            for lesson_id, lesson_time in lessons:
                if isinstance(lesson_time, str):
                    lesson_time = datetime.fromisoformat(lesson_time)
                time_str = lesson_time.strftime("%d.%m.%Y в %H:%M")
                lessons_text += f"• {time_str}\n"
            await update.message.reply_text(lessons_text)
        else:
            await update.message.reply_text("📅 У вас нет запланированных уроков")
    
    elif text == '❓ Помощь':
        help_text = (
            "❓ ПОМОЩЬ ДЛЯ УЧЕНИКА\n\n"
            "📚 Решать вариант - выбрать экзамен и решить вариант\n"
            "📊 Моя статистика - посмотреть результаты всех решенных заданий\n"
            "🔁 Повторить ошибки - заново решить задания, где были ошибки\n"
            "📅 Мои уроки - посмотреть расписание занятий\n\n"
            "Доступные экзамены:\n"
            "• ЕГЭ - варианты для подготовки к ЕГЭ\n"
            "• ОГЭ - варианты для подготовки к ОГЭ\n\n"
            "В каждом экзамене доступны категории:\n"
            "• ФИПИ - официальные варианты\n" 
            "• Ященко - тренировочные варианты\n\n"
            "💡 Советы:\n"
            "• Используйте запятую для дробных чисел (0,5 вместо 0.5)\n"
            "• Внимательно читайте условия задач\n"
            "• Анализируйте ошибки в статистике\n\n"
            "По всем вопросам обращайтесь к репетитору."
        )
        await update.message.reply_text(help_text)
    
    elif text == '🔙 Назад':
        if user_id in user_states:
            del user_states[user_id]
        await update.message.reply_text("🔙 Главное меню", reply_markup=get_main_keyboard(is_admin=False))
    
    else:
        await update.message.reply_text("Не понимаю команду 😊")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    user_id = user.id
    is_admin = user_id in ADMIN_IDS
    
    print(f"📨 Получено сообщение от {user_id} ({user.first_name}): {text}")

    # Проверяем состояния пользователя
    if user_id in user_states:
        state = user_states[user_id]
        
        # Обработка состояний выбора экзамена
        if state.get('mode') == 'choosing_exam':
            if text in ['ЕГЭ', 'ОГЭ']:
                state['selected_exam'] = text
                state['mode'] = 'choosing_category'
                
                await update.message.reply_text(
                    f"📚 {text}\n\nВыберите категорию:",
                    reply_markup=get_categories_keyboard(text)
                )
                return
            elif text == '🔙 Назад':
                if user_id in user_states:
                    del user_states[user_id]
                await update.message.reply_text("🔙 Главное меню", reply_markup=get_main_keyboard(is_admin=is_admin))
                return
            else:
                await update.message.reply_text("❌ Пожалуйста, выберите экзамен из списка:")
                return
        
        # Обработка состояний выбора категории
        elif state.get('mode') == 'choosing_category':
            if text == '🔙 Назад':
                state['mode'] = 'choosing_exam'
                await update.message.reply_text(
                    "📚 Выберите экзамен:",
                    reply_markup=get_exam_keyboard()
                )
                return
            
            # Проверяем, что выбранная категория существует для этого экзамена
            categories = db.get_categories_by_exam(state['selected_exam'])
            if text in categories:
                state['selected_category'] = text
                
                if state.get('purpose') == 'solving':
                    # Ученик выбирает вариант для решения
                    state['mode'] = 'choosing_variant'
                    variants = db.get_variants_by_exam_and_category(state['selected_exam'], text)
                    state['variants'] = variants
                    
                    if not variants:
                        await update.message.reply_text(
                            f"📭 В категории '{text}' пока нет вариантов",
                            reply_markup=get_categories_keyboard(state['selected_exam'])
                        )
                        return
                    
                    await update.message.reply_text(
                        f"📚 {state['selected_exam']} - {text}\n\nВыберите вариант:",
                        reply_markup=get_variants_keyboard(state['selected_exam'], text, for_admin=False)
                    )
                elif state.get('purpose') == 'managing':
                    # Админ выбирает вариант для управления
                    state['mode'] = 'managing_variants'
                    variants = db.get_variants_by_exam_and_category(state['selected_exam'], text)
                    state['variants'] = variants
                    
                    await update.message.reply_text(
                        f"🔧 Управление вариантами\n{state['selected_exam']} - {text}\n\nВыберите вариант:",
                        reply_markup=get_variants_keyboard(state['selected_exam'], text, for_admin=True)
                    )
                return
            else:
                await update.message.reply_text("❌ Пожалуйста, выберите категорию из списка:")
                return
        
        elif state.get('mode') == 'choosing_variant':
            await handle_variant_selection(update, user_id, text)
            return
        
        elif state.get('mode') == 'managing_variants':
            await handle_variant_management(update, user_id, text)
            return
        
        elif state.get('mode') == 'managing_variant':
            await handle_variant_actions(update, user_id, text)
            return
        
        elif state.get('mode') == 'managing_exercises':
            if text in ['➕ Добавить номер', '✏️ Изменить номер', '🗑️ Удалить номер', '🔙 К управлению']:
                await handle_exercise_management(update, user_id, text)
            else:
                await show_exercises_management(update, user_id)
            return
        
        elif state.get('mode') == 'adding_exercise':
            await handle_adding_exercise(update, user_id, text)
            return
        
        elif state.get('mode') == 'editing_exercise':
            await handle_editing_exercise(update, user_id, text)
            return
        
        elif state.get('mode') == 'deleting_exercise':
            await handle_deleting_exercise(update, user_id, text)
            return
        
        elif state.get('mode') == 'editing_variant_name':
            await handle_variant_name_edit(update, user_id, text)
            return
        
        elif state.get('mode') == 'editing_variant_category':
            await handle_variant_category_edit(update, user_id, text)
            return
        
        elif state.get('mode') == 'deleting_variant':
            await handle_variant_deletion(update, user_id, text)
            return
        
        # Обработка создания варианта
        elif state.get('mode') == 'creating_variant':
            await handle_variant_creation(update, user_id, text)
            return
        
        # Обработка подтверждения повторения ошибок
        elif state.get('mode') == 'confirm_wrong_exercises':
            if text == '✅ Начать повторение':
                state = await WrongExercisesManager.start_wrong_exercises(update, user_id)
                if state:
                    user_states[user_id] = state
            elif text == '🔙 Назад':
                if user_id in user_states:
                    del user_states[user_id]
                await update.message.reply_text("🔙 Главное меню", reply_markup=get_main_keyboard(is_admin=False))
            return
        
        # Обработка решения варианта
        elif state.get('mode') == 'solving_variant':
            await handle_exercise_answer(update, user_id, text)
            return
        
        # Обработка решения ошибок
        elif state.get('mode') == 'solving_wrong_exercise':
            await handle_wrong_exercise_solving(update, user_id, text)
            return
        
        # Обработка создания урока
        elif state.get('mode') == 'adding_lesson':
            await handle_lesson_creation(update, context, user_id, text)
            return
        
        # Обработка удаления урока
        elif state.get('mode') == 'deleting_lesson':
            await handle_lesson_deletion(update, user_id, text)
            return
    
    # Если нет активного состояния, обрабатываем основные команды
    if is_admin:
        await handle_admin_message(update, text, user_id)
    else:
        await handle_student_message(update, text, user_id)

async def send_lesson_notification(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет уведомления о предстоящих уроках"""
    await NotificationManager.send_lesson_notification(context)

def main():
    if BOT_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ ЗАМЕНИТЕ BOT_TOKEN НА РЕАЛЬНЫЙ ТОКЕН!")
        return
    
    if ADMIN_IDS == [123456789]:
        print("❌ ЗАМЕНИТЕ ADMIN_IDS НА ВАШ ID!")
        return
    
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

if __name__ == '__main__':
    main()