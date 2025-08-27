#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простая версия DearCraveBreaker Telegram Bot
Без использования проблемных импортов telegram.ext
"""

import asyncio
import logging
import os
import aiosqlite
from datetime import datetime, timedelta
import random
import json
from motivation_quotes import MotivationQuotesGenerator

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleDearCraveBreakerBot:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.db_path = "cravebreaker.db"
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Миграция: добавить новые колонки в существующие таблицы
            try:
                await db.execute("""
                    ALTER TABLE user_progress 
                    ADD COLUMN used_coaching_questions TEXT DEFAULT '[]'
                """)
            except:
                # Колонка уже существует
                pass
            await db.execute("""
                CREATE TABLE IF NOT EXISTS help_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Gamification tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER PRIMARY KEY,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    total_interventions INTEGER DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    last_intervention_date TEXT,
                    badges_earned TEXT DEFAULT '[]',
                    technique_counts TEXT DEFAULT '{}',
                    weekend_interventions INTEGER DEFAULT 0,
                    late_night_interventions INTEGER DEFAULT 0,
                    early_morning_interventions INTEGER DEFAULT 0,
                    coaching_used BOOLEAN DEFAULT 0,
                    used_coaching_questions TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_badges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    badge_id TEXT,
                    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    xp_awarded INTEGER DEFAULT 0,
                    UNIQUE(user_id, badge_id)
                )
            """)
            
            # Triggers tracking table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    trigger_name TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User states table for conversation flow
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    state TEXT,
                    data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            
            await db.commit()
    

    
    # User state management methods
    async def set_user_state(self, user_id: int, state: str, data: str = ""):
        """Set user conversation state"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_states (user_id, state, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, state, data))
            await db.commit()
    
    async def get_user_state(self, user_id: int):
        """Get user conversation state"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT state, data FROM user_states WHERE user_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            return result if result else (None, None)
    
    async def clear_user_state(self, user_id: int):
        """Clear user conversation state"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
            await db.commit()
            
    async def get_total_user_count(self):
        """Get total number of unique users for social proof (URD requirement)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM users")
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def record_trigger(self, user_id: int, trigger_name: str, description: str):
        """Record user trigger for analytics"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_triggers (user_id, trigger_name, description)
                VALUES (?, ?, ?)
            """, (user_id, trigger_name, description))
            await db.commit()

    

    
    async def get_user_triggers(self, user_id: int):
        """Get user's recorded triggers"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT trigger_name, description, created_at 
                FROM user_triggers 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 10
            """, (user_id,))
            return await cursor.fetchall()
    
    async def count_total_users(self):
        """Count total unique users who have used the bot"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM users")
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def ensure_user_exists(self, user_id: int, username: str | None = None):
        """Ensure user exists in database, create if not"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if user exists
            cursor = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            if not await cursor.fetchone():
                # Create user if doesn't exist
                await db.execute(
                    "INSERT INTO users (user_id, username) VALUES (?, ?)",
                    (user_id, username)
                )
                await db.commit()
                logger.info(f"Created new user: {user_id}")
    
    async def user_exists(self, user_id: int) -> bool:
        """Check if user exists in database"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            result = await cursor.fetchone()
            return result is not None
    
    # Gamification methods
    async def get_user_progress(self, user_id):
        """Get user progress without gamification"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT total_interventions, current_streak, longest_streak,
                   last_intervention_date, technique_counts, weekend_interventions,
                   late_night_interventions, early_morning_interventions, coaching_used, used_coaching_questions
                   FROM user_progress WHERE user_id = ?""",
                (user_id,)
            )
            result = await cursor.fetchone()
            
            if result is None:
                # Initialize new user progress
                await db.execute(
                    """INSERT INTO user_progress (user_id) VALUES (?)""",
                    (user_id,)
                )
                await db.commit()
                return {
                    "total_interventions": 0, "current_streak": 0,
                    "longest_streak": 0, "last_intervention_date": None,
                    "technique_counts": "{}", "weekend_interventions": 0,
                    "late_night_interventions": 0, "early_morning_interventions": 0,
                    "coaching_used": False, "used_coaching_questions": "[]"
                }
            
            return {
                "total_interventions": result[0], "current_streak": result[1],
                "longest_streak": result[2], "last_intervention_date": result[3],
                "technique_counts": result[4], "weekend_interventions": result[5],
                "late_night_interventions": result[6], "early_morning_interventions": result[7],
                "coaching_used": bool(result[8]), "used_coaching_questions": result[9] if len(result) > 9 else "[]"
            }
    
    async def update_user_progress(self, user_id, progress_data):
        """Update user progress without gamification"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE user_progress SET 
                   total_interventions = ?, current_streak = ?,
                   longest_streak = ?, last_intervention_date = ?,
                   technique_counts = ?, weekend_interventions = ?, late_night_interventions = ?,
                   early_morning_interventions = ?, coaching_used = ?, used_coaching_questions = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ?""",
                (
                    progress_data.get("total_interventions", 0),
                    progress_data.get("current_streak", 0),
                    progress_data.get("longest_streak", 0),
                    progress_data.get("last_intervention_date"),
                    progress_data.get("technique_counts", "{}"),
                    progress_data.get("weekend_interventions", 0),
                    progress_data.get("late_night_interventions", 0),
                    progress_data.get("early_morning_interventions", 0),
                    progress_data.get("coaching_used", False),
                    progress_data.get("used_coaching_questions", "[]"),
                    user_id
                )
            )
            await db.commit()
    
    # Badge system disabled
    
    # Level calculation disabled
    
    async def process_intervention_success(self, user_id, intervention_type="general"):
        """Process successful intervention"""
        progress = await self.get_user_progress(user_id)
        
        # Update intervention count
        progress["total_interventions"] += 1
        
        # Update streak
        today = datetime.now().date().isoformat()
        if progress["last_intervention_date"] is None:
            progress["current_streak"] = 1
            progress["longest_streak"] = 1
        else:
            last_date = datetime.fromisoformat(progress["last_intervention_date"]).date()
            current_date = datetime.now().date()
            days_diff = (current_date - last_date).days
            
            if days_diff == 1:
                progress["current_streak"] += 1
                progress["longest_streak"] = max(progress["longest_streak"], progress["current_streak"])
            elif days_diff > 1:
                progress["current_streak"] = 1
        
        progress["last_intervention_date"] = today
        
        # Update technique counts
        technique_counts = json.loads(progress["technique_counts"])
        technique_counts[intervention_type] = technique_counts.get(intervention_type, 0) + 1
        progress["technique_counts"] = json.dumps(technique_counts)
        
        # Update progress
        await self.update_user_progress(user_id, progress)
    
    async def send_message(self, chat_id, text, reply_markup=None):
        """Отправка сообщения через Telegram API"""
        import httpx
        
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=data)
                return response.json()
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                return None
    
    async def get_updates(self, offset=0):
        """Получение обновлений от Telegram"""
        import httpx
        
        url = f"{self.base_url}/getUpdates"
        params = {
            "offset": offset,
            "timeout": 10
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    # Handle 409 Conflict - usually means webhook is active or multiple instances
                    logger.warning("409 Conflict detected - attempting to resolve...")
                    # Try to delete webhook and wait a bit
                    await self.delete_webhook()
                    await asyncio.sleep(2)
                    return {"ok": True, "result": []}
                else:
                    logger.error(f"HTTP error {e.response.status_code}: {e}")
                    return {"ok": False, "result": []}
            except httpx.TimeoutException:
                logger.debug("Timeout получения обновлений (это нормально)")
                return {"ok": True, "result": []}
            except Exception as e:
                logger.error(f"Ошибка получения обновлений: {e}")
                return {"ok": False, "result": []}
    
    def get_main_menu_keyboard(self):
        """Клавиатура главного меню"""
        return {
            "inline_keyboard": [
                [{"text": "🆘 Срочная помощь", "callback_data": "emergency_help"}],
                [{"text": "🧠 Мои импульсы", "callback_data": "my_impulses"}],
                [{"text": "💫 Мотивация дня", "callback_data": "daily_motivation"}],
                [{"text": "👨‍💼 Мой персональный коуч", "callback_data": "coaching_session"}],
                [{"text": "📊 Моя статистика", "callback_data": "show_stats"}],
                [{"text": "📖 О DearCraveBreaker", "callback_data": "about"}, {"text": "❓ F.A.Q.", "callback_data": "faq"}]
            ]
        }
    
    def get_impulses_menu_keyboard(self):
        """Клавиатура выбора типа импульса"""
        return {
            "inline_keyboard": [
                [{"text": "🍰 Хочется сладкого", "callback_data": "impulse_sweets"}],
                [{"text": "🍷 Хочется выпить", "callback_data": "impulse_alcohol"}],
                [{"text": "🚬 Хочется курить", "callback_data": "impulse_smoking"}],
                [{"text": "📱 Хочется скроллить", "callback_data": "impulse_scrolling"}],
                [{"text": "😤 Хочется разозлиться", "callback_data": "impulse_anger"}],
                [{"text": "🍔 Хочется вредной еды", "callback_data": "impulse_junkfood"}],
                [{"text": "🛒 Хочется потратить деньги", "callback_data": "impulse_shopping"}],
                [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
            ]
        }
    
    def get_intervention_keyboard(self):
        """Клавиатура выбора интервенции"""
        return {
            "inline_keyboard": [
                [{"text": "🫁 Дыхательная техника", "callback_data": "intervention_breathing"}],
                [{"text": "🧘‍♀️ Медитация и осознанность", "callback_data": "intervention_meditation"}],
                [{"text": "🤔 Коучинговый вопрос", "callback_data": "intervention_coaching"}],
                [{"text": "🎮 Отвлекающая игра", "callback_data": "intervention_game"}],
                [{"text": "🔙 Назад в меню", "callback_data": "back_to_menu"}]
            ]
        }
    
    def get_breathing_exercise(self):
        """Получить дыхательную технику из коллекции 25 техник"""
        exercises = [
            # Классические техники (1-5)
            {"name": "4-7-8 дыхание", "instruction": """🫁 **Техника 4-7-8**\n\n1️⃣ Вдохните через нос на 4 счета\n2️⃣ Задержите дыхание на 7 счетов\n3️⃣ Выдохните через рот на 8 счетов\n4️⃣ Повторите 3-4 раза\n\nЭта техника помогает активировать парасимпатическую нервную систему и снизить стресс."""},
            {"name": "Квадратное дыхание", "instruction": """🟦 **Квадратное дыхание**\n\n1️⃣ Вдох на 4 счета\n2️⃣ Задержка на 4 счета\n3️⃣ Выдох на 4 счета\n4️⃣ Задержка на 4 счета\n🔄 Повторите 5-6 раз\n\nПредставьте, что рисуете квадрат дыханием."""},
            {"name": "Треугольное дыхание", "instruction": """🔺 **Треугольное дыхание**\n\n1️⃣ Вдох на 3 счета\n2️⃣ Задержка на 3 счета\n3️⃣ Выдох на 3 счета\n🔄 Повторите 7-8 раз\n\nПростая техника для быстрого успокоения."""},
            {"name": "Дыхание 5-5", "instruction": """⚖️ **Равномерное дыхание 5-5**\n\n1️⃣ Вдох на 5 счетов\n2️⃣ Выдох на 5 счетов\n🔄 Продолжайте 3-5 минут\n\nСинхронизирует работу сердца и легких."""},
            {"name": "Брюшное дыхание", "instruction": """🤱 **Диафрагмальное дыхание**\n\n1️⃣ Положите руку на живот\n2️⃣ Вдыхайте так, чтобы поднимался живот, не грудь\n3️⃣ Выдыхайте медленно через слегка сжатые губы\n🔄 Повторите 5-10 раз"""},
            
            # Успокаивающие техники (6-10)
            {"name": "Дыхание океана", "instruction": """🌊 **Удджайи (дыхание океана)**\n\n1️⃣ Дышите через нос\n2️⃣ Слегка сожмите горло, создавая тихий звук 'хх'\n3️⃣ Вдох и выдох должны быть одинаковой длины\n🔄 Продолжайте 2-3 минуты\n\nЗвук напоминает шум океана."""},
            {"name": "Дыхание пчелы", "instruction": """🐝 **Бхрамари (дыхание пчелы)**\n\n1️⃣ Закройте уши большими пальцами\n2️⃣ Вдохните носом\n3️⃣ На выдохе создайте звук 'ммм'\n🔄 Повторите 5-7 раз\n\nВибрация успокаивает нервную систему."""},
            {"name": "Лунное дыхание", "instruction": """🌙 **Чандра Бхедана (лунное дыхание)**\n\n1️⃣ Закройте правую ноздрю пальцем\n2️⃣ Дышите только левой ноздрей\n3️⃣ Вдох и выдох медленные\n🔄 Продолжайте 2-3 минуты\n\nОхлаждает и успокаивает."""},
            {"name": "Дыхание в счет 6", "instruction": """6️⃣ **Шестисчетное дыхание**\n\n1️⃣ Вдох на 6 счетов\n2️⃣ Задержка на 6 счетов\n3️⃣ Выдох на 6 счетов\n🔄 Повторите 6 циклов\n\nГармонизирует энергию."""},
            {"name": "Сердечное дыхание", "instruction": """❤️ **Дыхание сердцем**\n\n1️⃣ Положите руку на сердце\n2️⃣ Дышите в ритме сердцебиения\n3️⃣ Представьте, как дыхание входит и выходит через сердце\n🔄 Продолжайте 3-5 минут"""},
            
            # Энергизирующие техники (11-15)
            {"name": "Огненное дыхание", "instruction": """🔥 **Капалабхати (огненное дыхание)**\n\n1️⃣ Быстрые короткие выдохи через нос\n2️⃣ Вдохи происходят автоматически\n3️⃣ Активно работают мышцы живота\n🔄 30 быстрых выдохов, затем отдых\n\n⚠️ Не делайте при головокружении."""},
            {"name": "Солнечное дыхание", "instruction": """☀️ **Сурья Бхедана (солнечное дыхание)**\n\n1️⃣ Закройте левую ноздрю\n2️⃣ Дышите только правой ноздрей\n3️⃣ Активные, бодрящие вдохи-выдохи\n🔄 Продолжайте 1-2 минуты\n\nПовышает энергию и концентрацию."""},
            {"name": "Дыхание силы", "instruction": """💪 **Мощное дыхание**\n\n1️⃣ Резкий глубокий вдох через нос\n2️⃣ Задержка на 3 счета\n3️⃣ Мощный выдох через рот со звуком 'ХА!'\n🔄 Повторите 5 раз\n\nВысвобождает заблокированную энергию."""},
            {"name": "Ступенчатое дыхание", "instruction": """🪜 **Дыхание по ступеням**\n\n1️⃣ Вдыхайте порциями: 2 счета, пауза, еще 2 счета, пауза, еще 2\n2️⃣ Полный выдох одним потоком\n3️⃣ Повторите с выдохом по ступеням, вдохом одним потоком\n🔄 5-7 циклов каждого варианта"""},
            {"name": "Дыхание воина", "instruction": """⚔️ **Дыхание воина**\n\n1️⃣ Вдох - поднимите руки вверх\n2️⃣ Задержка - сожмите кулаки\n3️⃣ Выдох - резко опустите руки вниз\n🔄 Повторите 7 раз\n\nСочетает дыхание с движением."""},
            
            # Специальные техники (16-20)
            {"name": "Альтернативное дыхание", "instruction": """🔄 **Нади Шодхана (альтернативное дыхание)**\n\n1️⃣ Закройте правую ноздрю, вдохните левой\n2️⃣ Закройте левую, откройте правую, выдохните\n3️⃣ Вдохните правой\n4️⃣ Закройте правую, откройте левую, выдохните\n🔄 10 полных циклов\n\nБалансирует левое и правое полушария."""},
            {"name": "Дыхание льва", "instruction": """🦁 **Симхасана (дыхание льва)**\n\n1️⃣ Глубокий вдох через нос\n2️⃣ Широко откройте рот, высуньте язык\n3️⃣ Мощный выдох со звуком 'АААА'\n4️⃣ Смотрите вверх или в межбровье\n🔄 Повторите 3-5 раз\n\nСнимает напряжение лица и горла."""},
            {"name": "Дыхание волны", "instruction": """🌊 **Волновое дыхание**\n\n1️⃣ Представьте волну, поднимающуюся от живота к груди на вдохе\n2️⃣ На выдохе волна опускается от груди к животу\n3️⃣ Дыхание плавное, непрерывное\n🔄 Продолжайте 5-10 волн\n\nСоздает ощущение текучести."""},
            {"name": "Дыхание в цвете", "instruction": """🎨 **Цветное дыхание**\n\n1️⃣ Выберите успокаивающий цвет (голубой, зеленый)\n2️⃣ На вдохе представьте, что вдыхаете этот цвет\n3️⃣ На выдохе выдыхайте темный цвет (серый, черный)\n🔄 10-15 вдохов\n\nВизуализация усиливает эффект."""},
            {"name": "Дыхание со звуком", "instruction": """🎵 **Дыхание с мантрой**\n\n1️⃣ На вдохе мысленно произносите 'СО'\n2️⃣ На выдохе мысленно произносите 'ХАМ'\n3️⃣ Дыхание естественное, не форсированное\n🔄 Продолжайте 5-10 минут\n\n'Со Хам' означает 'Я есть то'."""},
            
            # Продвинутые техники (21-25)
            {"name": "Ретенционное дыхание", "instruction": """⏱️ **Дыхание с задержками**\n\n1️⃣ Вдох на 4 счета\n2️⃣ Задержка на полном вдохе - 16 счетов\n3️⃣ Выдох через рот на 8 счетов\n🔄 Начните с меньших пропорций 4-8-4\n\n⚠️ Не принуждайте себя."""},
            {"name": "Дыхание шипения", "instruction": """🐍 **Ситали (охлаждающее дыхание)**\n\n1️⃣ Сверните язык трубочкой\n2️⃣ Вдыхайте через свернутый язык со звуком 'ссс'\n3️⃣ Выдыхайте через нос\n🔄 10-15 вдохов\n\nОхлаждает тело и ум."""},
            {"name": "Дыхание свистка", "instruction": """💨 **Ситкари (свистящее дыхание)**\n\n1️⃣ Слегка разожмите губы\n2️⃣ Прижмите язык к зубам\n3️⃣ Вдыхайте со свистящим звуком\n4️⃣ Выдыхайте через нос\n🔄 10-12 вдохов\n\nТакже охлаждает."""},
            {"name": "Пранаяма 1-4-2", "instruction": """📐 **Классическая пропорция 1:4:2**\n\n1️⃣ Если вдох на 4 счета\n2️⃣ То задержка на 16 счетов\n3️⃣ А выдох на 8 счетов\n🔄 Начните с пропорции 1:2:1\n\nПостепенно увеличивайте время."""},
            {"name": "Дыхание освобождения", "instruction": """🕊️ **Освобождающее дыхание**\n\n1️⃣ Глубокий вдох с поднятием рук\n2️⃣ Задержка - представьте, что держите все проблемы\n3️⃣ Резкий выдох - 'отпускаете' все через руки\n4️⃣ Руки свободно падают\n🔄 Повторите 5-7 раз\n\nФизически отпускаете напряжение."""}
        ]
        return random.choice(exercises)

    def get_meditation_practice(self):
        """Получить практику медитации и осознанности из коллекции 50 практик"""
        practices = [
            # Базовые медитации (1-10)
            {"name": "Медитация дыхания", "instruction": """🫁 **Анапанасати (медитация на дыхании)**\n\n1️⃣ Сядьте удобно, закройте глаза\n2️⃣ Наблюдайте за естественным дыханием\n3️⃣ Когда ум отвлекается, мягко возвращайте внимание к дыханию\n🔄 Практикуйте 5-10 минут\n\nОснова всех медитативных практик."""},
            {"name": "Сканирование тела", "instruction": """🧘‍♀️ **Бодисканинг**\n\n1️⃣ Лягте или сядьте удобно\n2️⃣ Начните с пальцев ног, медленно поднимайтесь вверх\n3️⃣ Замечайте ощущения в каждой части тела\n4️⃣ Не пытайтесь изменить - просто наблюдайте\n🔄 15-20 минут полного сканирования"""},
            {"name": "Медитация ходьбы", "instruction": """🚶‍♀️ **Кинхин (медитация ходьбы)**\n\n1️⃣ Идите очень медленно (медленнее обычного в 3-4 раза)\n2️⃣ Сосредоточьтесь на ощущениях в стопах\n3️⃣ Чувствуйте каждый шаг: подъем, движение, опускание\n🔄 10-15 минут медленной ходьбы"""},
            {"name": "Медитация звуков", "instruction": """🎵 **Шротра дхарана (медитация звуков)**\n\n1️⃣ Закройте глаза, расслабьтесь\n2️⃣ Слушайте все звуки вокруг без оценки\n3️⃣ Не фокусируйтесь на одном звуке - принимайте все\n4️⃣ Когда ум начинает анализировать, возвращайтесь к слушанию\n🔄 10-15 минут"""},
            {"name": "Медитация на пламя", "instruction": """🕯️ **Тратака (медитация на свечу)**\n\n1️⃣ Зажгите свечу, сядьте на расстоянии 1-2 метра\n2️⃣ Смотрите на пламя, не моргая как можно дольше\n3️⃣ Когда глаза устанут, закройте их и видьте отпечаток пламени\n4️⃣ Повторите цикл\n🔄 15-20 минут практики"""},
            
            # Практики осознанности (11-20)
            {"name": "Осознанное питание", "instruction": """🍎 **Медитативное питание**\n\n1️⃣ Возьмите небольшой кусочек еды (изюм, орех)\n2️⃣ Рассмотрите его 1-2 минуты\n3️⃣ Медленно жуйте, замечая все ощущения\n4️⃣ Почувствуйте текстуру, вкус, как глотаете\n🔄 Превратите каждый прием пищи в медитацию"""},
            {"name": "Осознанное мытье посуды", "instruction": """🍽️ **Медитация в действии**\n\n1️⃣ Мойте посуду очень медленно и внимательно\n2️⃣ Чувствуйте температуру воды, текстуру мыла\n3️⃣ Наблюдайте за движениями рук\n4️⃣ Когда ум отвлекается, возвращайтесь к ощущениям\n🔄 Превратите рутину в практику"""},
            {"name": "Медитация эмоций", "instruction": """😌 **Наблюдение за эмоциями**\n\n1️⃣ Сядьте удобно, закройте глаза\n2️⃣ Вспомните легкую неприятную ситуацию\n3️⃣ Наблюдайте, где в теле чувствуете эмоцию\n4️⃣ Дышите в это место, не пытаясь изменить\n🔄 5-10 минут наблюдения"""},
            {"name": "Медитация мыслей", "instruction": """💭 **Випассана (наблюдение мыслей)**\n\n1️⃣ Сядьте в медитации, наблюдайте дыхание\n2️⃣ Когда приходит мысль, мысленно скажите 'мысль'\n3️⃣ Не развивайте мысль, не оценивайте - просто отметьте\n4️⃣ Вернитесь к дыханию\n🔄 15-20 минут практики"""},
            {"name": "Медитация благодарности", "instruction": """🙏 **Практика благодарности**\n\n1️⃣ Положите руку на сердце\n2️⃣ Вспомните 3 вещи, за которые благодарны\n3️⃣ Почувствуйте тепло благодарности в груди\n4️⃣ Пошлите это чувство всем, кто вам помог\n🔄 5-10 минут каждое утро"""},
            
            # Визуализации (21-30)
            {"name": "Медитация света", "instruction": """💡 **Джьоти медитация**\n\n1️⃣ Представьте золотой свет в области сердца\n2️⃣ С каждым вдохом свет становится ярче\n3️⃣ С выдохом свет распространяется по телу\n4️⃣ В конце пошлите свет всем существам\n🔄 10-15 минут визуализации"""},
            {"name": "Медитация горы", "instruction": """⛰️ **Практика устойчивости**\n\n1️⃣ Представьте себя величественной горой\n2️⃣ Основание глубоко в земле, вершина в облаках\n3️⃣ Наблюдайте, как вокруг меняется погода, но вы неподвижны\n4️⃣ Чувствуйте внутреннюю устойчивость и силу\n🔄 10-20 минут"""},
            {"name": "Медитация океана", "instruction": """🌊 **Практика спокойствия**\n\n1️⃣ Представьте себя глубоким океаном\n2️⃣ На поверхности могут быть волны (мысли, эмоции)\n3️⃣ Но в глубине всегда покой и тишина\n4️⃣ Опускайтесь в эти глубины сознания\n🔄 15-25 минут"""},
            {"name": "Медитация дерева", "instruction": """🌳 **Практика роста**\n\n1️⃣ Представьте себя деревом\n2️⃣ Корни глубоко в земле - ваша устойчивость\n3️⃣ Ствол - ваша сила и целостность\n4️⃣ Ветви тянутся к свету - ваше развитие\n🔄 10-15 минут"""},
            {"name": "Медитация цветка лотоса", "instruction": """🪷 **Падма медитация**\n\n1️⃣ Представьте лотос в области сердца\n2️⃣ С каждым вдохом лепестки медленно раскрываются\n3️⃣ В центре цветка - чистый свет сознания\n4️⃣ Почувствуйте, как раскрывается ваше сердце\n🔄 15-20 минут"""},
            
            # Мантра-медитации (31-40)
            {"name": "Мантра ОМ", "instruction": """🕉️ **Пранава мантра**\n\n1️⃣ Сядьте удобно, закройте глаза\n2️⃣ На выдохе произносите 'ОММММММммм'\n3️⃣ Чувствуйте вибрацию в груди и голове\n4️⃣ На вдохе тишина\n🔄 21 повтор или 10-15 минут"""},
            {"name": "Мантра Со Хам", "instruction": """🎵 **'Я есть то'**\n\n1️⃣ На вдохе мысленно 'СО'\n2️⃣ На выдохе мысленно 'ХАМ'\n3️⃣ Не контролируйте дыхание, следуйте за ним\n4️⃣ Ощутите единство с дыханием жизни\n🔄 15-30 минут"""},
            {"name": "Мантра покоя", "instruction": """☮️ **Шанти мантра**\n\n1️⃣ Повторяйте: 'ОМ ШАНТИ ШАНТИ ШАНТИ'\n2️⃣ Первое шанти - мир в теле\n3️⃣ Второе - мир в уме\n4️⃣ Третье - мир в окружающем мире\n🔄 108 повторов или 20 минут"""},
            {"name": "Мантра сострадания", "instruction": """💖 **Авалокитешвара мантра**\n\n1️⃣ Повторяйте: 'ОМ МАНИ ПАДМЕ ХУМ'\n2️⃣ Представляйте, как сострадание наполняет сердце\n3️⃣ Пошлите любовь всем существам\n4️⃣ Начните с близких, расширьте на всех\n🔄 108 повторов"""},
            {"name": "Мантра мудрости", "instruction": """🧠 **Гаятри мантра (упрощенная)**\n\n1️⃣ Повторяйте: 'ОМ НАМО ГУРУ ДЭВАЙЯ'\n2️⃣ 'Поклон учителю света внутри'\n3️⃣ Обращайтесь к высшей мудрости в себе\n4️⃣ Просите о ясности и понимании\n🔄 108 повторов"""},
            
            # Продвинутые практики (41-50)
            {"name": "Медитация пустоты", "instruction": """🕳️ **Шуньята медитация**\n\n1️⃣ Наблюдайте пространство между мыслями\n2️⃣ Замечайте паузы между вдохом и выдохом\n3️⃣ Погружайтесь в эту естественную пустоту\n4️⃣ Не пытайтесь создать пустоту - найдите ее\n🔄 20-30 минут"""},
            {"name": "Медитация свидетеля", "instruction": """👁️ **Сакши бхава**\n\n1️⃣ Наблюдайте за всем, что происходит в уме\n2️⃣ Мысли, эмоции, ощущения - как облака в небе\n3️⃣ Вы - неизменное небо, не облака\n4️⃣ Просто свидетельствуйте без участия\n🔄 25-40 минут"""},
            {"name": "Медитация 'Кто я?'", "instruction": """❓ **Атма вичара**\n\n1️⃣ Задавайте вопрос: 'Кто я?'\n2️⃣ Не ищите ответ умом\n3️⃣ Погружайтесь в чувство 'Я есть'\n4️⃣ Отбрасывайте все определения себя\n🔄 20-45 минут самоисследования"""},
            {"name": "Медитация единства", "instruction": """🌍 **Адвайта медитация**\n\n1️⃣ Начните чувствовать связь с окружающим\n2️⃣ Растворите границы между 'я' и 'не-я'\n3️⃣ Ощутите единое сознание во всем\n4️⃣ Нет медитирующего и медитации - есть только медитация\n🔄 30-60 минут"""},
            {"name": "Медитация тишины", "instruction": """🤫 **Маунам**\n\n1️⃣ Не используйте техники\n2️⃣ Просто сидите в полной тишине\n3️⃣ Не следуйте за мыслями, не отвергайте их\n4️⃣ Будьте тишиной, которая всегда присутствует\n🔄 От 20 минут до нескольких часов"""}
        ]
        return random.choice(practices)
    
    async def get_coaching_question(self, user_id):
        """Получить коучинговый вопрос без повторений"""
        # Полный список из 100 уникальных коучинговых вопросов
        all_questions = [
            # Вопросы о будущем (1-20)
            "🤔 Что я почувствую через 10 минут, если НЕ поддамся этому импульсу?",
            "🌟 Что я буду чувствовать завтра утром, если справлюсь с этим импульсом?",
            "⏰ Как я буду относиться к этому моменту через час?",
            "📅 Будет ли мне стыдно за это завтра?",
            "🎯 Приближает ли этот выбор меня к моей мечте?",
            "🔮 Каким человеком я стану, если продолжу сопротивляться?",
            "🌅 Что изменится в моей жизни, если я устою сегодня?",
            "📈 Как этот выбор повлияет на мой прогресс через неделю?",
            "🏆 Каким будет мой следующий уровень, если я не сдамся?",
            "✨ О чем я буду мечтать, если справлюсь с этим?",
            "🌱 Какие возможности откроются, если я устою?",
            "💫 Какую версию себя я хочу увидеть через месяц?",
            "🚀 К какой цели это меня приблизит?",
            "⭐ Что произойдет, если я стану сильнее этого импульса?",
            "🎪 Какой праздник я себе устрою, если справлюсь?",
            "🌈 Какое действие приблизит меня к тому человеку, которым я хочу стать?",
            "🎁 Какой подарок будущему себе я делаю прямо сейчас?",
            "🔥 Насколько горжусь собой буду через год?",
            "💎 Какой драгоценный опыт я получу, если устою?",
            "🎯 Как этот выбор соотносится с моими долгосрочными целями?",

            # Альтернативы и замещения (21-40)
            "💭 Какую альтернативу я могу выбрать прямо сейчас?",
            "🎁 Какой подарок я могу сделать себе вместо этого?",
            "🌿 Что полезного я могу сделать в эту минуту?",
            "📚 Чему новому я могу научиться вместо этого?",
            "🏃‍♂️ Какое движение поможет мне переключиться?",
            "🎨 Во что творческое я могу вложить эту энергию?",
            "📞 С кем я могу поговорить вместо этого?",
            "🎵 Какая музыка поможет мне изменить настрой?",
            "📝 Что важного я могу записать или спланировать?",
            "🌺 Что красивое я могу создать или увидеть?",
            "💧 Что освежающее я могу выпить или съесть?",
            "🧘‍♀️ Какое упражнение поможет мне расслабиться?",
            "📖 Что вдохновляющее я могу прочитать?",
            "🚶‍♀️ Куда я могу пойти, чтобы изменить обстановку?",
            "🧹 Что я могу привести в порядок вокруг себя?",
            "💌 Кому я могу написать приятное сообщение?",
            "🎯 На какой позитивной цели я могу сосредоточиться?",
            "🌱 Что я могу сделать для своего здоровья?",
            "💡 Какую идею я могу развить вместо этого?",
            "⏰ Могу ли я отложить это решение на 15 минут?",

            # Самоанализ и понимание (41-60)
            "🔍 Что на самом деле происходит со мной сейчас? Усталость? Стресс? Скука?",
            "🧘‍♀️ Что мое тело на самом деле пытается мне сказать?",
            "😌 Что бы я посоветовал близкому другу в такой ситуации?",
            "💭 Какие мысли привели меня к этому моменту?",
            "🎭 Какая эмоция скрывается за этим желанием?",
            "🌊 Что я на самом деле пытаюсь заглушить или избежать?",
            "🔥 От чего я пытаюсь убежать с помощью этой привычки?",
            "🎪 Какую потребность я пытаюсь удовлетворить таким образом?",
            "🌙 Что мне не хватает в жизни прямо сейчас?",
            "💝 Чего я на самом деле жажду?",
            "🗝️ Какой урок скрыт в этом моменте искушения?",
            "🎨 Какие чувства я пытаюсь изменить?",
            "🌱 Что этот импульс говорит о моих потребностях?",
            "🔮 Какую пустоту я пытаюсь заполнить?",
            "🎭 Какую роль играет эта привычка в моей жизни?",
            "🌊 Как долго длится это желание обычно?",
            "💡 Что запустило этот импульс сегодня?",
            "🎯 Каких ресурсов мне не хватает сейчас?",
            "🌿 Что мой организм действительно просит?",
            "🎪 Какой сигнал подает мне мое подсознание?",

            # Прошлый опыт и мотивация (61-80)
            "🏆 Когда я в последний раз гордился собой за то, что устоял?",
            "💪 Какая моя сильная сторона поможет мне сейчас устоять?",
            "🌟 Какой мой самый яркий момент победы над собой?",
            "🎯 Что помогло мне справиться в прошлый раз?",
            "❤️ Кто в меня верит и поддерживает?",
            "🔥 Какое мое самое важное 'почему'?",
            "🌈 За что я больше всего благодарен в жизни?",
            "💎 Какие мои главные ценности?",
            "🌟 Какие качества во мне восхищают других?",
            "🎪 Какой мой самый большой источник гордости?",
            "🌱 Какой прогресс я уже сделал?",
            "🏆 Какую победу над собой я помню лучше всего?",
            "💖 Кого я люблю настолько, чтобы стать лучше?",
            "🎯 Ради чего я готов меняться?",
            "✨ Какая моя суперсила в трудные моменты?",
            "🌊 Как я справлялся с этим раньше?",
            "🔥 Что дает мне силы продолжать?",
            "💪 В какие свои способности я точно верю?",
            "🎨 Что делает меня уникальным?",
            "🌟 Какой комплимент я себе больше всего заслуживаю?",

            # Долгосрочная перспектива и ценности (81-100)
            "❤️ Что важнее для меня в долгосрочной перспективе?",
            "🚀 Как я могу превратить этот момент в победу?",
            "🎯 Какие мои самые важные жизненные приоритеты?",
            "💖 Какую любовь к себе я могу проявить сейчас?",
            "🌱 Как этот выбор повлияет на мою самооценку?",
            "🎪 Какую историю о себе я хочу рассказывать?",
            "✨ Какой пример я подаю окружающим?",
            "🌊 Что значит для меня быть сильным человеком?",
            "💎 Какие принципы определяют мою личность?",
            "🔥 За что я хочу, чтобы меня помнили?",
            "🎨 Какой след я хочу оставить в мире?",
            "🌟 Что делает мою жизнь значимой?",
            "💫 Какой я хочу видеть свою историю?",
            "🎯 Какой вклад я хочу внести в жизни близких?",
            "🌈 Какой смысл я вкладываю в свои поступки?",
            "🏆 Какое наследие я хочу оставить?",
            "💪 Что означает для меня честность перед собой?",
            "🌱 Какие мои действия отражают мои истинные ценности?",
            "✨ Как я хочу чувствовать себя в конце дня?",
            "🎁 Какую версию себя я выбираю прямо сейчас?"
        ]
        
        # Получить данные о пользователе
        progress = await self.get_user_progress(user_id)
        used_questions = json.loads(progress.get("used_coaching_questions", "[]"))
        
        # Найти неиспользованные вопросы
        available_questions = [q for i, q in enumerate(all_questions) if i not in used_questions]
        
        # Если все вопросы использованы, сбросить список
        if not available_questions:
            available_questions = all_questions
            used_questions = []
        
        # Выбрать случайный вопрос из доступных
        selected_question = random.choice(available_questions)
        selected_index = all_questions.index(selected_question)
        
        # Добавить индекс в список использованных
        used_questions.append(selected_index)
        
        # Обновить прогресс пользователя
        progress["used_coaching_questions"] = json.dumps(used_questions)
        await self.update_user_progress(user_id, progress)
        
        return selected_question
    
    def get_mini_game(self):
        """Получить отвлекающую игру из коллекции 50 игр"""
        games = [
            # Математические игры (1-10)
            {"name": "Счет наоборот", "task": """🔢 **Обратный счет с правилами**\n\nСчитайте от 100 до 1, но:\n▪️ Пропускайте числа с цифрой 7\n▪️ Вместо чисел, кратных 5, говорите 'БУМ'\n▪️ При ошибке начинайте сначала\n\nПример: 100, 99, 98, 96, БУМ, 94..."""},
            {"name": "Таблица умножения", "task": """✖️ **Быстрые вычисления**\n\n1️⃣ Выберите число от 6 до 9\n2️⃣ Умножайте его на числа от 1 до 20\n3️⃣ Говорите ответы вслух как можно быстрее\n4️⃣ Засеките время - старайтесь улучшить результат"""},
            {"name": "Числовые последовательности", "task": """🔢 **Найди закономерность**\n\nПродолжите последовательности:\n• 2, 4, 8, 16, ?\n• 1, 4, 9, 16, 25, ?\n• 3, 6, 12, 24, ?\n• 1, 1, 2, 3, 5, 8, ?\n\nПридумайте свою последовательность!"""},
            {"name": "Математические загадки", "task": """🧮 **Задачки в уме**\n\n• У меня есть 64 рубля в монетах по 1, 5 и 10 рублей. Монет по 5 рублей в два раза больше, чем по 10. Сколько монет каждого вида?\n• Решите без калькулятора: 17 × 23 = ?"""},
            {"name": "Цифровые корни", "task": """🌱 **Игра с цифрами**\n\n1️⃣ Возьмите любое 3-значное число\n2️⃣ Сложите все его цифры\n3️⃣ Если получилось 2-значное число, снова сложите цифры\n4️⃣ Повторяйте, пока не получится 1 цифра\n\nПопробуйте с числами: 789, 456, 999"""},
            
            # Словесные игры (11-20)
            {"name": "Алфавитные категории", "task": """🔤 **Слова по алфавиту**\n\n1️⃣ Выберите категорию (города, животные, еда)\n2️⃣ Назовите слова на каждую букву алфавита\n3️⃣ Не повторяйтесь!\n4️⃣ Дошли до Я? Попробуйте в обратном порядке!"""},
            {"name": "Рифмы и созвучия", "task": """🎵 **Поэтическая игра**\n\n1️⃣ Возьмите слово 'солнце'\n2️⃣ Найдите 10 слов, которые с ним рифмуются\n3️⃣ Составьте из них короткое стихотворение\n4️⃣ Попробуйте со словами: море, дом, мечта"""},
            {"name": "Антонимы и синонимы", "task": """↔️ **Противоположности и сходства**\n\n1️⃣ К слову 'быстрый' найдите 5 синонимов и 5 антонимов\n2️⃣ Попробуйте со словами: умный, красивый, большой\n3️⃣ Составьте цепочки: быстрый → резвый → проворный..."""},
            {"name": "Ассоциативные цепочки", "task": """🔗 **Игра ассоциаций**\n\n1️⃣ Начните со слова 'море'\n2️⃣ Каждое следующее слово - ассоциация к предыдущему\n3️⃣ Постройте цепочку из 20 слов\n4️⃣ Попробуйте вернуться к исходному слову"""},
            {"name": "Палиндромы", "task": """🔄 **Слова-перевертыши**\n\nНайдите слова, которые читаются одинаково в обе стороны:\n• 3-буквенные: дед, шалаш, ...\n• 5-буквенные: казак, топот, ...\n• Составьте предложение из палиндромов!"""},
            
            # Визуальные игры (21-30)
            {"name": "Цветовая радуга", "task": """🌈 **Цветная медитация**\n\n1️⃣ Закройте глаза\n2️⃣ Представьте красный цвет - где его видите?\n3️⃣ Переходите: оранжевый → желтый → зеленый → голубой → синий → фиолетовый\n4️⃣ Для каждого цвета - 3 предмета"""},
            {"name": "Мысленная комната", "task": """🏠 **Архитектор воображения**\n\n1️⃣ Представьте идеальную комнату\n2️⃣ Мысленно расставьте мебель\n3️⃣ Выберите цвета стен, пола, потолка\n4️⃣ Добавьте детали: картины, растения, освещение\n5️⃣ 'Прогуляйтесь' по комнате"""},
            {"name": "Геометрические фигуры", "task": """📐 **3D-визуализация**\n\n1️⃣ Представьте куб\n2️⃣ Поверните его в уме на 90°\n3️⃣ Превратите в пирамиду\n4️⃣ Затем в сферу\n5️⃣ Попробуйте сложные фигуры: тетраэдр, додекаэдр"""},
            {"name": "Путешествие в воображении", "task": """✈️ **Мысленное путешествие**\n\n1️⃣ Выберите страну\n2️⃣ Представьте поездку туда во всех деталях\n3️⃣ Что видите в окне самолета?\n4️⃣ Какая погода? Люди? Еда?\n5️⃣ Спланируйте маршрут на неделю"""},
            {"name": "Лица и эмоции", "task": """😊 **Галерея эмоций**\n\n1️⃣ Представьте лицо близкого человека\n2️⃣ 'Нарисуйте' на нем разные эмоции:\n• Радость, грусть, удивление\n• Гнев, страх, отвращение\n3️⃣ Какие мышцы лица меняются?"""},
            
            # Физические упражнения (31-40)
            {"name": "Пальчиковая гимнастика", "task": """🤏 **Тренировка пальцев**\n\n1️⃣ Сожмите кулаки, разожмите (10 раз)\n2️⃣ Поочередно касайтесь большим пальцем всех остальных\n3️⃣ 'Играйте на пианино' в воздухе\n4️⃣ Сделайте 'замок' и потяните руки"""},
            {"name": "Дыхательная гимнастика", "task": """🫁 **Активное дыхание**\n\n1️⃣ 4 быстрых вдоха через нос\n2️⃣ 1 длинный выдох через рот\n3️⃣ Повторите 10 раз\n4️⃣ Затем 1 глубокий вдох и долгий выдох со звуком 'Аааа'"""},
            {"name": "Точечный массаж", "task": """👆 **Акупрессура**\n\n1️⃣ Помассируйте мочки ушей 30 секунд\n2️⃣ Точка между бровями - 30 секунд\n3️⃣ Точка в центре ладоней - по 30 секунд\n4️⃣ Помассируйте основание черепа"""},
            {"name": "Растяжка сидя", "task": """🧘‍♀️ **Мини-йога**\n\n1️⃣ Потяните руки вверх, затем в стороны\n2️⃣ Поверните корпус влево, вправо\n3️⃣ Наклоните голову к плечам\n4️⃣ Сделайте круги плечами\n5️⃣ Потяните спину, прогнувшись назад"""},
            {"name": "Упражнения для глаз", "task": """👀 **Гимнастика для глаз**\n\n1️⃣ Посмотрите вверх-вниз 10 раз\n2️⃣ Влево-вправо 10 раз\n3️⃣ По диагонали в обе стороны\n4️⃣ Нарисуйте глазами цифру 8\n5️⃣ Крепко зажмурьтесь, откройте глаза"""},
            
            # Креативные игры (41-50)
            {"name": "Изобретение предметов", "task": """💡 **Придумай устройство**\n\n1️⃣ Объедините два случайных предмета\n2️⃣ Придумайте, как это может работать\n3️⃣ Например: зонт + лампа = светящийся зонт для вечерних прогулок\n4️⃣ Попробуйте: телефон + растение, часы + подушка"""},
            {"name": "Альтернативное использование", "task": """🔄 **Необычное применение**\n\n1️⃣ Возьмите обычную скрепку\n2️⃣ Придумайте 20 способов ее использования\n3️⃣ Будьте креативны! (открывашка, украшение, инструмент...)\n4️⃣ Попробуйте с другими предметами"""},
            {"name": "Создание историй", "task": """📚 **Мини-роман**\n\n1️⃣ Выберите 3 случайных слова\n2️⃣ Придумайте историю, используя все три\n3️⃣ Ограничение: ровно 50 слов\n4️⃣ Попробуйте слова: космос, бабушка, пицца"""},
            {"name": "Дизайн логотипов", "task": """🎨 **Мысленный дизайн**\n\n1️⃣ Придумайте название новой компании\n2️⃣ Представьте логотип в деталях\n3️⃣ Какие цвета? Шрифт? Символы?\n4️⃣ Опишите логотип словами за 2 минуты"""},
            {"name": "Музыкальная композиция", "task": """🎵 **Внутренний композитор**\n\n1️⃣ Выберите эмоцию (радость, грусть, энергия)\n2️⃣ Представьте мелодию для нее\n3️⃣ Какие инструменты? Темп? Ритм?\n4️⃣ 'Напойте' мелодию в голове 2 минуты"""},
            {"name": "Планирование события", "task": """🎉 **Организатор праздника**\n\n1️⃣ Спланируйте идеальный день рождения\n2️⃣ Место, гости, еда, развлечения\n3️⃣ Бюджет 50,000 рублей\n4️⃣ Все детали от приглашений до подарков"""},
            {"name": "Архитектурный проект", "task": """🏛️ **Домик мечты**\n\n1️⃣ Спроектируйте дом на 100 кв.м\n2️⃣ Сколько комнат? Их назначение?\n3️⃣ Стиль: современный, классический, эко?\n4️⃣ Участок: сад, бассейн, гараж?"""},
            {"name": "Создание языка", "task": """🗣️ **Лингвист-изобретатель**\n\n1️⃣ Придумайте 10 слов на новом языке\n2️⃣ Для основных понятий: вода, еда, дом, любовь\n3️⃣ Как они звучат? Есть ли логика?\n4️⃣ Попробуйте составить простое предложение"""},
            {"name": "Рецепт блюда", "task": """👨‍🍳 **Кулинарный шедевр**\n\n1️⃣ Создайте новое блюдо\n2️⃣ Объедините продукты, которые обычно не сочетают\n3️⃣ Подробный рецепт с пропорциями\n4️⃣ Как подавать? С чем сочетается?"""},
            {"name": "Тренировка памяти", "task": """🧠 **Дворец памяти**\n\n1️⃣ Запомните список: молоко, ключи, зонт, книга, цветы, хлеб, телефон\n2️⃣ Создайте яркую историю, связывающую все предметы\n3️⃣ Через 5 минут воспроизведите список\n4️⃣ Попробуйте в обратном порядке!"""}
        ]
        return random.choice(games)
    
    def get_impulse_interventions(self, impulse_type):
        """Получить интервенции для конкретного типа импульса"""
        interventions = {
            "sweets": {
                "title": "🍰 Импульс к сладкому",
                "techniques": [
                    {
                        "name": "🥤 Замена напитком",
                        "instruction": "Выпейте стакан воды с лимоном или мятой. Часто жажда маскируется под тягу к сладкому."
                    },
                    {
                        "name": "⏰ Правило 10 минут",
                        "instruction": "Подождите 10 минут. Включите музыку или сделайте несколько упражнений. Импульс часто проходит сам."
                    },
                    {
                        "name": "🍎 Здоровая альтернатива",
                        "instruction": "Съешьте яблоко, банан или горсть орехов. Удовлетворите потребность в питательных веществах."
                    }
                ]
            },
            "alcohol": {
                "title": "🍷 Импульс к алкоголю",
                "techniques": [
                    {
                        "name": "🫧 Безалкогольная замена",
                        "instruction": "Приготовьте безалкогольный мохито или выпейте газированную воду с лаймом из красивого бокала."
                    },
                    {
                        "name": "🧘‍♂️ Техника СТОП",
                        "instruction": "СТОП - остановитесь. Сделайте глубокий вдох. Осознайте эмоцию. Подумайте о последствиях. Примите решение."
                    },
                    {
                        "name": "🏃‍♀️ Смена обстановки",
                        "instruction": "Выйдите на улицу на 15 минут. Прогуляйтесь или сделайте несколько приседаний."
                    }
                ]
            },
            "smoking": {
                "title": "🚬 Импульс к курению",
                "techniques": [
                    {
                        "name": "🫁 Дыхательная замена",
                        "instruction": "Имитируйте курение: глубоко вдохните воздух через сложенные трубочкой губы, задержите, медленно выдохните."
                    },
                    {
                        "name": "🥕 Жевательная замена",
                        "instruction": "Пожуйте морковку, сельдерей или жвачку без сахара. Занять рот - половина победы."
                    },
                    {
                        "name": "🤲 Занять руки",
                        "instruction": "Сожмите эспандер, покрутите ручку, порисуйте. Импульс курить часто связан с привычкой рук."
                    }
                ]
            },
            "scrolling": {
                "title": "📱 Импульс к скроллингу",
                "techniques": [
                    {
                        "name": "📵 Убрать телефон",
                        "instruction": "Положите телефон в другую комнату на 20 минут. Из виду - из сердца."
                    },
                    {
                        "name": "📚 Замена активности",
                        "instruction": "Откройте книгу, включите подкаст или начните делать что-то руками."
                    },
                    {
                        "name": "⏰ Техника помидора",
                        "instruction": "Поставьте таймер на 25 минут. Займитесь полезным делом. После сигнала - 5 минут можно скроллить."
                    }
                ]
            },
            "anger": {
                "title": "😤 Импульс к злости",
                "techniques": [
                    {
                        "name": "🧊 Холодная вода",
                        "instruction": "Умойтесь холодной водой или подержите кубик льда. Резкая смена температуры снижает агрессию."
                    },
                    {
                        "name": "🔢 Считаем до 10",
                        "instruction": "Медленно сосчитайте от 1 до 10, дыша глубоко. При сильной злости - до 100."
                    },
                    {
                        "name": "🏃‍♀️ Физическая разрядка",
                        "instruction": "Сделайте 10 отжиманий, приседаний или просто потрясите руками и ногами 30 секунд."
                    }
                ]
            },
            "junkfood": {
                "title": "🍔 Импульс к вредной еде",
                "techniques": [
                    {
                        "name": "🥗 Правило тарелки",
                        "instruction": "Сначала съешьте салат или овощи. Часто после этого тяга к вредному пропадает."
                    },
                    {
                        "name": "🦷 Почистить зубы",
                        "instruction": "Почистите зубы мятной пастой. После этого есть не захочется 20-30 минут."
                    },
                    {
                        "name": "🤔 Голод или эмоция?",
                        "instruction": "Спросите себя: 'Я действительно голоден или это эмоции?' Если эмоции - займитесь ими."
                    }
                ]
            },
            "shopping": {
                "title": "🛒 Импульс к трате денег",
                "techniques": [
                    {
                        "name": "🛒 Корзина желаний",
                        "instruction": "Добавьте товар в корзину, но не покупайте 24 часа. Часто желание проходит."
                    },
                    {
                        "name": "💰 Посчитайте в часах",
                        "instruction": "Переведите цену в часы работы: 'Это стоит 8 часов моей жизни. Оно того стоит?'"
                    },
                    {
                        "name": "📝 Список потребностей",
                        "instruction": "Запишите 3 вещи, которые вам реально нужны. Покупка есть в списке?"
                    }
                ]
            }
        }
        return interventions.get(impulse_type, interventions["sweets"])
    
    async def handle_message(self, message):
        """Обработка текстового сообщения"""
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "")
        
        # Simple message handling without trigger states
        
        if text.startswith("/start"):
            # Record new user for statistics
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR IGNORE INTO users (user_id, username, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, message["from"].get("username", "")))
                await db.commit()
            
            welcome_text = """🎉 **Добро пожаловать в DearCraveBreaker!**

Я ваш помощник в борьбе с навязчивыми привычками и импульсами.

🎯 **Что я умею:**
• 🆘 Экстренная поддержка при сильном импульсе
• 📊 Отслеживание вашего прогресса  
• 🧘‍♀️ Дыхательные техники и упражнения
• 🤔 Коучинговые вопросы для осознанности
• 🎮 Отвлекающие мини-игры

Готовы начать путь к лучшей версии себя?"""
            
            await self.send_message(chat_id, welcome_text, self.get_main_menu_keyboard())
        
        elif text.startswith("/help"):
            help_text = """❓ **Справка DearCraveBreaker**

🎯 **Основные команды:**
• /start - Начать работу с ботом
• /menu - Главное меню
• /help - Эта справка
• /stats - Ваша статистика

🆘 **В критический момент:**
Если вы чувствуете сильный импульс - сразу нажимайте "🆘 Экстренная помощь"

💪 **Помните:** Каждое 'нет' импульсу делает вас сильнее!"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🆘 Экстренная помощь", "callback_data": "emergency_help"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.send_message(chat_id, help_text, keyboard)
        
        elif text.startswith("/menu"):
            menu_text = """🏠 **Главное меню DearCraveBreaker**

💪 Каждое 'нет' импульсу - это 'да' лучшей версии себя!

Выберите действие:"""
            await self.send_message(chat_id, menu_text, self.get_main_menu_keyboard())
        
        elif text.startswith("/stats"):
            # Показать статистику пользователя
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT total_interventions, current_streak, longest_streak, level, xp
                    FROM user_progress 
                    WHERE user_id = ?
                """, (user_id,))
                progress = await cursor.fetchone()
                
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM interventions 
                    WHERE user_id = ? AND success = 1
                """, (user_id,))
                total_successes = await cursor.fetchone()
                success_count = total_successes[0] if total_successes else 0
            
            if progress:
                stats_text = f"""📊 **Ваша статистика**

🏆 **Общие показатели:**
• Уровень: {progress[3]} 
• Опыт: {progress[4]} XP
• Всего интервенций: {progress[0]}
• Успешных: {success_count}

🔥 **Серии успехов:**
• Текущая серия: {progress[1]} дней
• Лучшая серия: {progress[2]} дней

💪 Продолжайте в том же духе!"""
            else:
                stats_text = """📊 **Ваша статистика**

🎯 Пока статистики нет. Начните использовать техники борьбы с импульсами, и здесь появится ваш прогресс!

💡 Нажмите "🆘 Экстренная помощь", когда почувствуете импульс."""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🆘 Экстренная помощь", "callback_data": "emergency_help"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.send_message(chat_id, stats_text, keyboard)
            
        else:
            # Показываем главное меню для любого другого сообщения
            menu_text = """🏠 **Главное меню DearCraveBreaker**

💪 Каждое 'нет' импульсу - это 'да' лучшей версии себя!

Выберите действие:"""
            await self.send_message(chat_id, menu_text, self.get_main_menu_keyboard())
    
    async def handle_callback_query(self, callback_query):
        """Обработка callback запросов"""
        chat_id = callback_query["message"]["chat"]["id"]
        user_id = callback_query["from"]["id"]
        data = callback_query["data"]
        message_id = callback_query["message"]["message_id"]
        
        # DEBUG: Log ALL callback data to trace the routing issue
        logger.info(f"CALLBACK DEBUG: user_id={user_id}, callback_data='{data}'")
        
        # Ответ на callback query
        await self.answer_callback_query(callback_query["id"])
        
        if data == "emergency_help":
            text = "🆘 **Экстренная помощь активирована!**\n\nВыберите тип поддержки:"
            await self.edit_message(chat_id, message_id, text, self.get_intervention_keyboard())
            
            # Логируем обращение за помощью
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("INSERT INTO help_requests (user_id) VALUES (?)", (user_id,))
                await db.commit()
                

        
        elif data == "my_impulses":
            text = """🧠 **Мои импульсы**

Выберите тип импульса, с которым столкнулись прямо сейчас.

💡 **Помните:** Обращение за помощью - это уже проявление силы воли!

Каждый тип импульса требует особого подхода:"""
            await self.edit_message(chat_id, message_id, text, self.get_impulses_menu_keyboard())
        
        elif data.startswith("impulse_failed"):
            # DEBUG: Log the callback data to understand the issue
            logger.info(f"IMPULSE_FAILED DEBUG: callback_data='{data}'")
            parts = data.split("_")
            logger.info(f"IMPULSE_FAILED DEBUG: parts={parts}")
            
            if len(parts) >= 3:
                # Extract impulse type from callback data: impulse_failed_[TYPE]
                impulse_type = parts[2]
                logger.info(f"IMPULSE_FAILED DEBUG: extracted impulse_type='{impulse_type}'")
            else:
                # Fallback - should never happen with correct button creation
                impulse_type = "sweets"
                logger.warning(f"IMPULSE_FAILED DEBUG: Using fallback impulse_type='sweets', parts={parts}")
            
            # Store current impulse context to maintain routing
            await self.set_user_state(user_id, "current_impulse", impulse_type)
            logger.info(f"IMPULSE_FAILED DEBUG: stored impulse_type='{impulse_type}' for user {user_id}")
            
            text = f"""😌 **Эта техника не подошла**

Не переживайте! Поиск подходящей техники - это нормальный процесс.

🧠 **Что важно понимать:**
• Сам факт попытки - уже прогресс
• Вы тренируете навык осознанности  
• Каждая попытка приближает к успеху

💡 **Давайте попробуем другую технику для того же импульса**"""
            
            # FIXED: Always return to the SAME impulse type, not defaulting to sweets
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔄 Другая техника", "callback_data": f"impulse_{impulse_type}"}],
                    [{"text": "🆘 Срочная помощь", "callback_data": "emergency_help"}],
                    [{"text": "🧠 Другой тип импульса", "callback_data": "my_impulses"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
        
        elif data.startswith("impulse_success"):
            # Extract impulse type if provided
            impulse_type = ""
            if "_" in data:
                impulse_type = data.split("_", 2)[2] if len(data.split("_")) > 2 else ""
            # Update database record to successful
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE interventions 
                    SET success = 1 
                    WHERE user_id = ? AND id = (
                        SELECT MAX(id) FROM interventions WHERE user_id = ?
                    )
                """, (user_id, user_id))
                await db.commit()
            
            # Process successful intervention with gamification
            new_badges = await self.process_intervention_success(user_id, "impulse")
            
            text = """🎉 **Отлично! Техника сработала!**

Поздравляю! Вы успешно справились с импульсом.

💎 **Отличная работа!**

"""
            
            # Add badge notifications if any
            if new_badges:
                text += "🏆 **НОВЫЕ ДОСТИЖЕНИЯ!**\n"
                for badge_name, xp_reward in new_badges:
                    text += f"• {badge_name}\n"
                    # Try AI-enhanced achievement celebration first
                    progress = await self.get_user_progress(user_id)
                    ai_celebration = await MotivationQuotesGenerator().get_ai_achievement_celebration(badge_name, progress)
                    if ai_celebration:
                        text += f"\n💫 *{ai_celebration}*\n"
                    else:
                        # Fallback to curated achievement quote
                        achievement_quote = MotivationQuotesGenerator().get_achievement_quote(badge_name, xp_reward)
                        text += f"\n💫 *{achievement_quote}*\n"
            
            text += """
• Успешно справились с желанием

📈 **Ваш мозг учится:** каждая победа укрепляет нейронные пути самоконтроля.

Продолжайте в том же духе!"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📊 Моя статистика", "callback_data": "show_stats"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data.startswith("impulse_"):
            impulse_type = data.replace("impulse_", "")
            interventions = self.get_impulse_interventions(impulse_type)
            
            text = f"""{interventions['title']}

Выберите технику, которая кажется вам наиболее подходящей сейчас:"""
            
            keyboard = {
                "inline_keyboard": []
            }
            
            # Добавляем кнопки для каждой техники
            for i, technique in enumerate(interventions['techniques']):
                keyboard["inline_keyboard"].append([{
                    "text": technique['name'], 
                    "callback_data": f"technique_{impulse_type}_{i}"
                }])
            
            # Добавляем навигационные кнопки
            keyboard["inline_keyboard"].extend([
                [{"text": "🔙 Другой импульс", "callback_data": "my_impulses"}],
                [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
            ])
            
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data.startswith("technique_"):
            parts = data.split("_")
            if len(parts) < 3:
                logger.error(f"Invalid technique callback data: {data}")
                return
            impulse_type = parts[1]
            try:
                technique_index = int(parts[2])
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing technique index from callback data '{data}': {e}")
                return
            
            interventions = self.get_impulse_interventions(impulse_type)
            technique = interventions['techniques'][technique_index]
            
            text = f"""🎯 **{technique['name']}**

{technique['instruction']}

⏰ **Попробуйте прямо сейчас!**

После выполнения техники оцените результат:"""
            
            # DEBUG: Log button creation
            failed_callback = f"impulse_failed_{impulse_type}"
            logger.info(f"BUTTON DEBUG: Creating 'Не сработало' button with callback_data='{failed_callback}'")
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "✅ Помогло!", "callback_data": f"impulse_success_{impulse_type}"}],
                    [{"text": "❌ Не сработало", "callback_data": failed_callback}],
                    [{"text": "🔄 Другая техника", "callback_data": f"impulse_{impulse_type}"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            
            # Записываем попытку интервенции
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("INSERT INTO interventions (user_id, success) VALUES (?, ?)", (user_id, False))
                await db.commit()
            
            await self.edit_message(chat_id, message_id, text, keyboard)
                
        elif data == "intervention_breathing":
            exercise = self.get_breathing_exercise()
            text = f"🫁 **{exercise['name']}**\n\n{exercise['instruction']}\n\n_Следуйте инструкциям и дышите спокойно..._"
            keyboard = {
                "inline_keyboard": [
                    [{"text": "✅ Упражнение завершено", "callback_data": "outcome_success"}],
                    [{"text": "❌ Не помогло", "callback_data": "outcome_failed"}],
                    [{"text": "🫁 Другая техника", "callback_data": "intervention_breathing"}],
                    [{"text": "🔙 Назад", "callback_data": "emergency_help"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "intervention_meditation":
            practice = self.get_meditation_practice()
            text = f"🧘‍♀️ **{practice['name']}**\n\n{practice['instruction']}\n\n_Найдите тихое место и следуйте инструкциям..._"
            keyboard = {
                "inline_keyboard": [
                    [{"text": "✅ Практика завершена", "callback_data": "outcome_success"}],
                    [{"text": "❌ Не подошла", "callback_data": "outcome_failed"}],
                    [{"text": "🧘‍♀️ Другая практика", "callback_data": "intervention_meditation"}],
                    [{"text": "🔙 Назад", "callback_data": "emergency_help"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "intervention_coaching":
            # Получить коучинговый вопрос из интервенций
            question = await self.get_coaching_question(user_id)
            text = f"🤔 **Коучинговый вопрос**\n\n{question}\n\n💭 _Подумайте над этим вопросом несколько минут..._"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "✅ Помогло осознать", "callback_data": "outcome_success"}],
                    [{"text": "❌ Не подошел", "callback_data": "outcome_failed"}], 
                    [{"text": "🔄 Следующий вопрос", "callback_data": "intervention_coaching"}],
                    [{"text": "🔙 Назад", "callback_data": "emergency_help"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "intervention_game":
            game = self.get_mini_game()
            text = f"🎮 **{game['name']}**\n\n{game['task']}"
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎯 Игра завершена", "callback_data": "outcome_success"}],
                    [{"text": "😔 Не отвлекло", "callback_data": "outcome_failed"}],
                    [{"text": "🎲 Другая игра", "callback_data": "intervention_game"}],
                    [{"text": "🔙 Назад", "callback_data": "emergency_help"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data.startswith("outcome_"):
            # DEBUG: Log outcome callback
            logger.info(f"OUTCOME DEBUG: callback_data='{data}'")
            success = data == "outcome_success"
            
            # Record result in interventions table
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("INSERT INTO interventions (user_id, success) VALUES (?, ?)", (user_id, success))
                await db.commit()
            
            if success:
                # Process successful intervention with gamification
                new_badges = await self.process_intervention_success(user_id, "emergency")
                
                text = "🎉 **Отлично!**\n\nВы справились с импульсом! Это большая победа.\n\n💎 **Отличная работа!**"
                
                # Add badge notifications if any
                if new_badges:
                    text += "\n\n🏆 **НОВЫЕ ДОСТИЖЕНИЯ!**\n"
                    for badge_name, xp_reward in new_badges:
                        text += f"• {badge_name}\n"
                
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "📊 Моя статистика", "callback_data": "show_stats"}],
                        [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                    ]
                }
            else:
                text = "😔 **Ничего страшного!**\n\nБорьба с привычками - это процесс. Попробуйте другой метод.\n\n📊 Эта попытка тоже засчитана."
                
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🆘 Попробовать снова", "callback_data": "emergency_help"}],
                        [{"text": "📊 Моя статистика", "callback_data": "show_stats"}],
                        [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                    ]
                }
            
            await self.edit_message(chat_id, message_id, text, keyboard)
        
            
        elif data == "daily_motivation":
            progress = await self.get_user_progress(user_id)
            
            # Get AI-enhanced personalized quote
            enhanced_quote = MotivationQuotesGenerator().get_enhanced_personalized_quote(progress, "morning")
            
            # Get daily challenge
            daily_challenge = MotivationQuotesGenerator().get_daily_challenge_quote()
            
            text = f"""💫 **ПЕРСОНАЛЬНАЯ МОТИВАЦИЯ**

{enhanced_quote}

---

{daily_challenge}

🌟 **Помни:** Каждый день - новая возможность стать лучше!"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔄 Новая цитата", "callback_data": "daily_motivation"}],
                    [{"text": "🎯 Вечерняя рефлексия", "callback_data": "evening_reflection"}],
                    [{"text": "🆘 Нужна поддержка", "callback_data": "emergency_help"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "evening_reflection":
            progress = await self.get_user_progress(user_id)
            
            # Get AI-enhanced evening reflection quote
            reflection_quote = MotivationQuotesGenerator().get_enhanced_personalized_quote(progress, "evening_reflection")
            
            text = f"""🌅 **ВЕЧЕРНЯЯ РЕФЛЕКСИЯ**

{reflection_quote}

🤔 **Вопросы для размышления:**
• Что сегодня получилось особенно хорошо?
• Какой момент был самым сложным?
• За что я благодарен(а) себе сегодня?
• Что завтра сделаю по-другому?

💭 *Размышления помогают интегрировать опыт и планировать рост.*"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔄 Другая цитата", "callback_data": "evening_reflection"}],
                    [{"text": "💫 Утренняя мотивация", "callback_data": "daily_motivation"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "show_stats":
            # Получаем статистику пользователя
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM help_requests WHERE user_id = ?", (user_id,))
                result = await cursor.fetchone()
                total_requests = result[0] if result else 0
                
                cursor = await db.execute("SELECT COUNT(*) FROM interventions WHERE user_id = ?", (user_id,))
                result = await cursor.fetchone()
                total_interventions = result[0] if result else 0
                
                cursor = await db.execute("SELECT COUNT(*) FROM interventions WHERE user_id = ? AND success = 1", (user_id,))
                result = await cursor.fetchone()
                successful = result[0] if result else 0
            
            success_rate = (successful / total_interventions * 100) if total_interventions > 0 else 0
            
            text = f"""📊 **Ваша статистика**

🆘 **Всего обращений за помощью:** {total_requests}
💪 **Интервенций проведено:** {total_interventions}
✅ **Успешных сопротивлений:** {successful}
📈 **Процент успеха:** {success_rate:.1f}%

💡 **Совет:** Каждое обращение ко мне вместо поддавания импульсу - уже победа!"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔄 Обновить", "callback_data": "show_stats"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "coaching_session":
            text = """👨‍💼 **Мой персональный коуч**

👋 **Привет! Я SpotCoach** - сертифицированный коуч, который поможет тебе разобраться с привычками и достичь целей.

🚀 **Выбери, что тебе нужно:**

🎯 **Записаться на сессию** - глубокая работа с привычками
💬 **Получить онлайн-консультацию** - быстрый совет по ситуации  
🗣️ **Чисто отвести душу** - просто поговорить и выговориться
📺 **Перейти в канал пользы** - полезные материалы каждый день

Что выберешь?"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎯 Записаться на сессию", "url": "https://forms.gle/C8Bo6N43AsKMBb2f9"}],
                    [{"text": "💬 Получить онлайн-консультацию", "callback_data": "contact_coach"}],
                    [{"text": "🗣️ Чисто отвести душу", "callback_data": "just_talk"}],
                    [{"text": "📺 Перейти в канал пользы", "url": "https://t.me/SpotCoach"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "book_session":
            text = """📅 **Запись на персональную коуч-сессию**

🎯 **Что тебя ждет:**
• Глубокий анализ твоих привычек и паттернов
• Персональный план изменений
• Практические инструменты и техники  
• Поддержка на пути к цели

⏰ **Длительность:** 60-90 минут
💰 **Стоимость:** обсуждается индивидуально

📝 **Для записи заполни форму или напиши напрямую:**

🎁 **Бонус:** первая консультация 15 минут - бесплатно!"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📝 Заполнить форму записи", "url": "https://forms.gle/C8Bo6N43AsKMBb2f9"}],
                    [{"text": "✍️ Написать @SpotCoach", "url": "https://t.me/SpotCoach"}],
                    [{"text": "💬 Связаться онлайн", "callback_data": "contact_coach"}],
                    [{"text": "🔙 К коучинговым услугам", "callback_data": "coaching_session"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "contact_coach":
            text = """💬 **Получить онлайн-консультацию**

🎯 **Быстрая помощь от SpotCoach**

**Когда это подходит:**
• Нужен быстрый совет по конкретной ситуации
• Возник срочный вопрос о привычках
• Хочешь получить обратную связь
• Нужна мотивация прямо сейчас

📱 **Как получить консультацию:**
Напиши коучу в личку @CoaCerto с пометкой "Онлайн-консультация"

⚡ **Обычно отвечаю в течение нескольких часов**

💡 **Совет:** опиши ситуацию максимально конкретно - так я смогу дать более точный совет"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💌 Написать коучу", "url": "https://t.me/CoaCerto"}],
                    [{"text": "🔙 К персональному коучу", "callback_data": "coaching_session"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "just_talk":
            text = """🗣️ **Чисто отвести душу**

😌 **Иногда просто нужно выговориться...**

Знаю это чувство - когда все наваливается, привычки берут верх, а поделиться не с кем. 

**Здесь безопасное пространство:**
• Без осуждений и советов (если не просишь)
• Можешь просто выплеснуть эмоции
• Расскажи, что на душе
• Я выслушаю и пойму

💭 **Напиши коучу @CoaCerto** с пометкой "Просто поговорить"

🤗 **Помни:** ты не одинок в своих переживаниях, и то, что ты чувствуешь - нормально"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💭 Написать коучу", "url": "https://t.me/CoaCerto"}],
                    [{"text": "🔙 К персональному коучу", "callback_data": "coaching_session"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)

        elif data == "faq":
            text = """❓ **F.A.Q. - Часто задаваемые вопросы**

🎯 **Как работает система прогресса?**
• **Серии**: Дни подряд с успешными интервенциями (обнуляются при пропуске дня)
• **Статистика**: Отслеживание всех ваших интервенций и их успешности

🧠 **Как формируются новые привычки?**
1. **21 день** - начинают формироваться нейронные пути
2. **66 дней** - привычка становится автоматической (в среднем)
3. **90 дней** - устойчивая привычка, сложно сломать

💪 **К чему вы идете?**
• **Самоконтроль становится автоматическим**
• **Стресс-реакции ослабевают**
• **Появляется "пауза" между импульсом и действием**
• **Уверенность в своих силах растет**

💡 **Дополнительные возможности:**
Изучите статистику использования техник."""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📊 Моя статистика", "callback_data": "show_stats"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
        

        

            

            


        elif data == "about":
            count = await self.get_total_user_count()
            
            # Get total user count for social proof
            total_users = await self.get_total_user_count()
            
            text = f"""📖 **О DearCraveBreaker**

🎯 **Миссия:**
Помочь людям обрести контроль над своими импульсами и привычками через поддержку в критические моменты.

📊 **DearCraveBreaker уже использовали: {total_users} человек** 💪

🧠 **Научная основа:**
Бот использует проверенные методы:
• Техники осознанности (mindfulness)
• Когнитивно-поведенческие интервенции
• Дыхательные практики для снижения стресса
• Отвлечение внимания в критические моменты

👥 **Кому помогает:**
• Борющимся с перееданием
• Бросающим курить
• Ограничивающим алкоголь
• Контролирующим время в соцсетях
• Преодолевающим прокрастинацию

**Помните:** Сила воли - это навык, который можно тренировать! 💪

👨‍💼 **Разработано в партнерстве с @SpotCoach, сертифицированным лайф- и бизнес-коучем Международной Федерации Коучинга, и @Irinamaximoff, сертифицированным лайф-коучем ICU.**"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎯 Коучинговые услуги", "callback_data": "coaching_session"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            await self.edit_message(chat_id, message_id, text, keyboard)
            

            
        elif data.startswith("helped_"):
            # Parse technique type from callback
            technique_info = data.replace("helped_", "")
            
            # Update intervention as successful
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE interventions SET success = 1 WHERE user_id = ? AND success = 0 ORDER BY created_at DESC LIMIT 1", (user_id,))
                await db.commit()
            
            # Process successful intervention
            await self.process_intervention_success(user_id, technique_info)
            progress = await self.get_user_progress(user_id)
            
            text = f"""🎉 **Превосходно! Техника сработала!**

Вы успешно справились с импульсом и показали, что можете контролировать свои реакции.

💪 **Ваши результаты:**
• Успешных интервенций: {progress['total_interventions']}
• Текущая серия: {progress['current_streak']} дней 🔥

🧠 **Важно помнить:** Каждая успешная интервенция укрепляет вашу способность к самоконтролю. Вы становитесь сильнее!"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💫 Получить мотивацию", "callback_data": "daily_motivation"}],
                    [{"text": "📝 Записать заметку об успехе", "callback_data": "add_note"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data.startswith("not_helped_"):
            # Parse technique type from callback
            technique_info = data.replace("not_helped_", "")
            
            text = """💙 **Не расстраивайтесь! Это нормально.**

Не каждая техника подходит каждому человеку в каждой ситуации. Это важный опыт!

🔍 **Что можно попробовать:**
• Другую технику из того же раздела
• Техники из другой категории  
• Комбинацию нескольких методов
• Изменить обстановку и попробовать снова

💪 **Главное:** Вы обратились за помощью вместо того, чтобы сразу поддаться импульсу. Это уже победа!"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔄 Попробовать другую технику", "callback_data": "emergency_help"}],
                    [{"text": "🆘 Экстренная помощь", "callback_data": "emergency_help"}],
                    [{"text": "👨‍💼 Связаться с коучем", "callback_data": "contact_coach"}],
                    [{"text": "📝 Записать что не сработало", "callback_data": "add_note"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_menu"}]
                ]
            }
            
            await self.edit_message(chat_id, message_id, text, keyboard)
            
        elif data == "back_to_menu":
            menu_text = """🏠 **Главное меню DearCraveBreaker**

💪 Каждое 'нет' импульсу - это 'да' лучшей версии себя!

Выберите действие:"""
            await self.edit_message(chat_id, message_id, menu_text, self.get_main_menu_keyboard())
    
    async def answer_callback_query(self, callback_query_id):
        """Ответ на callback query"""
        import httpx
        
        url = f"{self.base_url}/answerCallbackQuery"
        data = {"callback_query_id": callback_query_id}
        
        async with httpx.AsyncClient() as client:
            await client.post(url, json=data)
    
    async def delete_webhook(self):
        """Delete any active webhook to resolve 409 conflicts"""
        import httpx
        
        url = f"{self.base_url}/deleteWebhook"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url)
                logger.info("Webhook deleted to resolve conflict")
                return response.json()
            except Exception as e:
                logger.error(f"Error deleting webhook: {e}")
                return None
    
    async def edit_message(self, chat_id, message_id, text, reply_markup=None):
        """Редактирование сообщения с улучшенным обработкой ошибок"""
        import httpx
        
        url = f"{self.base_url}/editMessageText"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=data)
                response_data = response.json()
                if not response_data.get('ok', False):
                    logger.error(f"Ошибка Telegram API: {response_data}")
                return response_data
            except Exception as e:
                logger.error(f"Ошибка редактирования сообщения: {e}")
                return None
    
    async def run_bot(self):
        """Запуск бота для app.py"""
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не найден!")
            return
        
        logger.info("Запуск Simple DearCraveBreaker Bot...")
        await self.init_db()
        
        offset = 0
        
        while True:
            try:
                updates = await self.get_updates(offset)
                
                if updates.get("ok"):
                    for update in updates.get("result", []):
                        offset = update["update_id"] + 1
                        
                        if "message" in update:
                            await self.handle_message(update["message"])
                        elif "callback_query" in update:
                            await self.handle_callback_query(update["callback_query"])
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        """Запуск бота (совместимость с прямым запуском)"""
        await self.run_bot()

async def main():
    bot = SimpleDearCraveBreakerBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")


    