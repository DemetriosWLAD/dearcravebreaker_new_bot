#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с базой данных SQLite
Хранение данных пользователей, статистики и триггеров
"""

import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "cravebreaker.db"):
        self.db_path = db_path
    
    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица триггеров пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    trigger_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица обращений за помощью
            await db.execute("""
                CREATE TABLE IF NOT EXISTS help_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица результатов интервенций
            await db.execute("""
                CREATE TABLE IF NOT EXISTS intervention_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # User progress (no gamification)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER PRIMARY KEY,
                    total_interventions INTEGER DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    last_intervention_date TEXT,
                    technique_counts TEXT DEFAULT '{}',
                    weekend_interventions INTEGER DEFAULT 0,
                    late_night_interventions INTEGER DEFAULT 0,
                    early_morning_interventions INTEGER DEFAULT 0,
                    coaching_used BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await db.commit()
            logger.info("База данных инициализирована")
    
    async def user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
            )
            result = await cursor.fetchone()
            return result is not None
    
    async def create_user(self, user_id: int, username: str) -> bool:
        """Создание нового пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO users (user_id, username) VALUES (?, ?)",
                    (user_id, username)
                )
                await db.commit()
                logger.info(f"Создан новый пользователь: {user_id} ({username})")
                return True
        except Exception as e:
            logger.error(f"Ошибка создания пользователя {user_id}: {e}")
            return False
    
    async def update_last_activity(self, user_id: int):
        """Обновление времени последней активности пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
    
    async def add_user_trigger(self, user_id: int, trigger_name: str) -> bool:
        """Добавление триггера пользователю"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем, нет ли уже такого триггера
                cursor = await db.execute(
                    "SELECT 1 FROM user_triggers WHERE user_id = ? AND trigger_name = ?",
                    (user_id, trigger_name)
                )
                exists = await cursor.fetchone()
                
                if not exists:
                    await db.execute(
                        "INSERT INTO user_triggers (user_id, trigger_name) VALUES (?, ?)",
                        (user_id, trigger_name)
                    )
                    await db.commit()
                    logger.info(f"Добавлен триггер '{trigger_name}' для пользователя {user_id}")
                    return True
                else:
                    logger.info(f"Триггер '{trigger_name}' уже существует для пользователя {user_id}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка добавления триггера для {user_id}: {e}")
            return False
    
    async def get_user_triggers(self, user_id: int) -> List[str]:
        """Получение списка триггеров пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT trigger_name FROM user_triggers WHERE user_id = ? ORDER BY created_at",
                (user_id,)
            )
            results = await cursor.fetchall()
            return [row[0] for row in results]
    
    async def log_help_request(self, user_id: int):
        """Логирование обращения за помощью"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO help_requests (user_id) VALUES (?)",
                (user_id,)
            )
            await db.commit()
            await self.update_last_activity(user_id)
    
    async def log_intervention_outcome(self, user_id: int, success: bool):
        """Логирование результата интервенции"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO intervention_outcomes (user_id, success) VALUES (?, ?)",
                (user_id, success)
            )
            await db.commit()
            await self.update_last_activity(user_id)
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Получение статистики пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Общая статистика обращений
            cursor = await db.execute(
                "SELECT COUNT(*) FROM help_requests WHERE user_id = ?",
                (user_id,)
            )
            total_requests = (await cursor.fetchone())[0]
            
            # Статистика интервенций
            cursor = await db.execute(
                "SELECT COUNT(*) FROM intervention_outcomes WHERE user_id = ?",
                (user_id,)
            )
            total_interventions = (await cursor.fetchone())[0]
            
            cursor = await db.execute(
                "SELECT COUNT(*) FROM intervention_outcomes WHERE user_id = ? AND success = 1",
                (user_id,)
            )
            successful_interventions = (await cursor.fetchone())[0]
            
            # Статистика за последние 7 дней
            week_ago = datetime.now() - timedelta(days=7)
            cursor = await db.execute(
                "SELECT COUNT(*) FROM help_requests WHERE user_id = ? AND created_at > ?",
                (user_id, week_ago.isoformat())
            )
            weekly_requests = (await cursor.fetchone())[0]
            
            cursor = await db.execute(
                "SELECT COUNT(*) FROM intervention_outcomes WHERE user_id = ? AND success = 1 AND created_at > ?",
                (user_id, week_ago.isoformat())
            )
            weekly_successes = (await cursor.fetchone())[0]
            
            # Триггеры пользователя
            triggers = await self.get_user_triggers(user_id)
            
            # Дата регистрации
            cursor = await db.execute(
                "SELECT created_at FROM users WHERE user_id = ?",
                (user_id,)
            )
            registration_date = (await cursor.fetchone())[0]
            
            return {
                'total_requests': total_requests,
                'total_interventions': total_interventions,
                'successful_interventions': successful_interventions,
                'weekly_requests': weekly_requests,
                'weekly_successes': weekly_successes,
                'triggers': triggers,
                'registration_date': registration_date,
                'success_rate': (successful_interventions / total_interventions * 100) if total_interventions > 0 else 0
            }
    
    async def get_daily_stats(self, user_id: int, days: int = 7) -> List[Tuple[str, int, int]]:
        """Получение ежедневной статистики за последние N дней"""
        stats = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            async with aiosqlite.connect(self.db_path) as db:
                # Количество обращений за день
                cursor = await db.execute(
                    """SELECT COUNT(*) FROM help_requests 
                       WHERE user_id = ? AND DATE(created_at) = ?""",
                    (user_id, date_str)
                )
                requests = (await cursor.fetchone())[0]
                
                # Количество успешных интервенций за день
                cursor = await db.execute(
                    """SELECT COUNT(*) FROM intervention_outcomes 
                       WHERE user_id = ? AND success = 1 AND DATE(created_at) = ?""",
                    (user_id, date_str)
                )
                successes = (await cursor.fetchone())[0]
                
                stats.append((date_str, requests, successes))
        
        return list(reversed(stats))  # От старых к новым
    
    async def cleanup_old_data(self, days: int = 90):
        """Очистка старых данных (старше N дней)"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM help_requests WHERE created_at < ?",
                (cutoff_date.isoformat(),)
            )
            await db.execute(
                "DELETE FROM intervention_outcomes WHERE created_at < ?",
                (cutoff_date.isoformat(),)
            )
            await db.commit()
            logger.info(f"Очищены данные старше {days} дней")
    
    # User progress methods (no gamification)
    async def get_user_progress(self, user_id: int) -> Dict:
        """Get user progress without gamification"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT total_interventions, current_streak, longest_streak,
                   last_intervention_date, technique_counts, weekend_interventions,
                   late_night_interventions, early_morning_interventions, coaching_used
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
                    "coaching_used": False
                }
            
            return {
                "total_interventions": result[0], "current_streak": result[1],
                "longest_streak": result[2], "last_intervention_date": result[3],
                "technique_counts": result[4], "weekend_interventions": result[5],
                "late_night_interventions": result[6], "early_morning_interventions": result[7],
                "coaching_used": bool(result[8])
            }
    
    async def update_user_progress(self, user_id: int, progress_data: Dict):
        """Update user progress without gamification"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE user_progress SET 
                   total_interventions = ?, current_streak = ?,
                   longest_streak = ?, last_intervention_date = ?,
                   technique_counts = ?, weekend_interventions = ?, late_night_interventions = ?,
                   early_morning_interventions = ?, coaching_used = ?, updated_at = CURRENT_TIMESTAMP
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
                    user_id
                )
            )
            await db.commit()
    
    # Badge methods removed - no gamification
