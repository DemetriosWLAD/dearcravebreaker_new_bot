#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Personalized Daily Motivation Quotes Generator for CraveBreaker
Generates contextual motivational quotes based on user progress and current state
"""

import random
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# OpenAI integration for advanced personalization
try:
    from openai import OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except ImportError:
    openai_client = None

class MotivationQuotesGenerator:
    """Generates personalized motivational quotes based on user context"""
    
    def __init__(self):
        self.base_quotes = self._initialize_base_quotes()
        self.streak_quotes = self._initialize_streak_quotes()
        self.milestone_quotes = self._initialize_milestone_quotes()
        self.time_based_quotes = self._initialize_time_based_quotes()
        self.comeback_quotes = self._initialize_comeback_quotes()
        
    def _initialize_base_quotes(self) -> List[str]:
        """Base motivational quotes for general use"""
        return [
            "💪 Каждое 'нет' привычке - это 'да' лучшей версии себя!",
            "🌟 Сила воли - это мышца. Каждый день ты делаешь её сильнее.",
            "🎯 Не сила привычки определяет тебя, а сила твоего выбора.",
            "🚀 Маленькие шаги каждый день ведут к большим переменам.",
            "🔥 Ты уже сделал самое сложное - решил измениться!",
            "⚡ Победа не в отсутствии импульсов, а в их осознанном контроле.",
            "🌱 Как садовник терпеливо выращивает цветы, так ты растишь новые привычки.",
            "🏆 Каждый миг осознанности - это победа над автопилотом.",
            "💎 Твоя истинная сила проявляется в моменты искушения.",
            "🌈 После каждой бури наступает радуга. Продолжай идти!",
            "🧠 Ты переписываешь код своего мозга каждым правильным выбором.",
            "🎪 Жизнь - это не борьба с собой, а танец с новыми возможностями.",
            "🔮 Будущее создается сегодняшними решениями.",
            "🌸 Терпение и постоянство превращают лист тутовника в шёлк.",
            "⭐ Ты не тот, кем был вчера. Ты становишься тем, кем хочешь быть.",
            "🌊 Океан состоит из капель, а успех - из маленьких побед.",
            "🔥 Твоя решимость горит ярче любого искушения.",
            "🎪 В цирке жизни ты - артист, владеющий своими номерами.",
            "🌟 Каждый рассвет - это новый шанс изменить свою историю.",
            "💪 Сила не в том, чтобы не падать, а в том, чтобы подниматься.",
            "🎯 Фокус на цели делает препятствия незаметными.",
            "🚀 Ты не пассажир своей жизни, ты её капитан.",
            "🏔️ Вершина кажется недосягаемой только снизу.",
            "🌱 Рост происходит за пределами зоны комфорта.",
            "⚡ Энергия для изменений уже внутри тебя.",
            "🎨 Ты художник своей судьбы и архитектор счастья.",
            "🔑 Ключ к успеху - в твоих руках, используй его.",
            "🌈 После шторма всегда наступает солнечный день.",
            "💎 Под давлением рождаются алмазы характера.",
            "🎵 Жизнь - это музыка, где ты выбираешь мелодию.",
            "🏆 Чемпионом становятся не за день, а каждый день.",
            "🌸 Цвети там, где посажен, но стремись к свету.",
            "⭐ Твоя уникальность - это твоя сверхспособность.",
            "🚪 Каждый выбор - это дверь в новую реальность.",
            "🎪 Жонглируй возможностями, не проблемами.",
            "🌟 Звёзды светят ярче в самые тёмные ночи.",
            "💪 Мышцы воли растут от тренировок, как и любые другие.",
            "🎯 Цель без плана - просто мечта с дедлайном.",
            "🚀 Орбита успеха требует постоянного ускорения.",
            "🏔️ Каждый шаг вверх приближает к вершине.",
            "🌱 Семена изменений прорастают в почве решимости.",
            "⚡ Молния вдохновения попадает в подготовленных.",
            "🎨 Раскрась серые дни яркими решениями.",
            "🔑 Отмыкай замки привычек ключом осознанности.",
            "🌈 Мост между мечтой и реальностью строится действиями.",
            "💎 Шлифуй характер ежедневным выбором.",
            "🎵 Настройся на частоту успеха и побед.",
            "🏆 Медали достаются тем, кто финиширует гонку с собой.",
            "🌸 Цветение личности происходит круглый год.",
            "⭐ Сияй собственным светом, не отражай чужой.",
            "🚪 Открывай двери возможностей смелостью попробовать.",
            "🎪 Баланс жизни - искусство, которому можно научиться.",
            "🌟 Внутренний свет освещает путь к переменам.",
            "💪 Сопротивление укрепляет, как физические упражнения.",
            "🎯 Меткость приходит с практикой и терпением.",
            "🚀 Запуск новой жизни происходит здесь и сейчас.",
            "🏔️ Покоряй вершины по одной скале за раз.",
            "🌱 Корни изменений питаются водой постоянства.",
            "⚡ Заряжайся энергией каждого нового дня.",
            "🎨 Добавляй краски радости в палитру будней.",
            "🔑 Найди ключ к мотивации в глубине души.",
            "🌈 Радуга появляется после дождя, а успех - после трудностей.",
            "💎 Ограни грани таланта упорным трудом.",
            "🎵 Ритм жизни задаёшь ты, а не обстоятельства.",
            "🏆 Первое место в жизни - быть лучшей версией себя.",
            "🌸 Аромат победы источают те, кто не сдаётся.",
            "⭐ Созвездие мечт складывается из звёзд решений.",
            "🚪 Выход из лабиринта проблем находится внутри тебя.",
            "🎪 Жизнь - представление, где ты и режиссёр, и актёр.",
            "🌟 Блеск в глазах - отражение горящего сердца.",
            "💪 Мускулы духа качаются подъёмами после падений.",
            "🎯 Цели - это маяки в океане возможностей.",
            "🚀 Траектория полёта к мечте корректируется ежедневно.",
            "🏔️ Альпинист жизни поднимается по склонам испытаний.",
            "🌱 Сад души требует постоянного полива вниманием.",
            "⚡ Искра перемен зажигается одним смелым поступком.",
            "🎨 Кисть судьбы в твоих руках, пиши шедевр.",
            "🔑 Дверь к счастью открывается изнутри.",
            "🌈 Спектр возможностей шире, чем кажется на первый взгляд.",
            "💎 Бриллианты характера огранены опытом.",
            "🎵 Симфония жизни звучит в ритме твоего сердца.",
            "🏆 Кубок победителя достаётся финишировавшему последним препятствие.",
            "🌸 Сад успеха цветёт круглый год при правильном уходе.",
            "⭐ Путеводная звезда - это твоя внутренняя мудрость.",
            "🚪 Пороги новых возможностей переступаются смело.",
            "🎪 Цирк жизни восхитителен, когда ты управляешь представлением.",
            "🌟 Сияние души не тускнеет от внешних бурь.",
            "💪 Мощь характера измеряется не силой удара, а стойкостью.",
            "🎯 Мишень достижений попадает в поле зрения решительных.",
            "🚀 Космос возможностей бесконечен для исследователей.",
            "🏔️ Горная вершина - символ преодоления себя.",
            "🌱 Росток будущего пробивается сквозь асфальт привычек.",
            "⚡ Заряд мотивации подпитывается от генератора веры в себя.",
            "🎨 Палитра эмоций богаче, когда выбираешь краски сознательно.",
            "🔑 Код к изменениям записан в ДНК твоей души.",
            "🌈 Радужные перспективы открываются после дождя испытаний.",
            "💎 Огранка личности происходит в мастерской опыта.",
            "🎵 Мелодия счастья звучит на частоте благодарности.",
            "🏆 Медаль мужества вручается за честность с собой.",
            "🌸 Цветок уверенности распускается в почве самопринятия.",
            "⭐ Созвездие побед складывается из звёздочек маленьких шагов.",
            "🚪 Коридор возможностей имеет множество дверей.",
            "🎪 Акробатика жизни требует гибкости и равновесия.",
            "🌟 Внутренний свет не нуждается во внешних источниках.",
            "💪 Тренажёрный зал характера работает круглосуточно.",
            "🎯 Лучник судьбы целится в будущее, стоя в настоящем.",
            "🚀 Стартовая площадка перемен находится в сегодняшнем дне.",
            "🏔️ Базовый лагерь изменений разбивается в зоне решимости.",
            "🌱 Оранжерея мечт согревается теплом веры в себя.",
            "⚡ Генератор энергии работает на топливе из собственных целей.",
            "🎨 Мольберт жизни ждёт твоих смелых мазков.",
            "🔑 Связка ключей к успеху висит на поясе настойчивости.",
            "🌈 Призма восприятия разлагает проблемы на спектр решений.",
            "💎 Сокровищница души хранит богатства, накопленные опытом.",
            "🎵 Оркестр перемен настраивается по камертону внутренней гармонии.",
            "🏆 Подиум достижений построен из ступенек ежедневных усилий.",
            "🌸 Букет побед собирается из цветков преодоления.",
            "⭐ Навигатор судьбы настроен на координаты мечты.",
            "🚪 Вестибюль возможностей открыт для посетителей с билетом решимости.",
            "🎪 Арена жизни аплодирует тем, кто не боится выступать.",
            "🌟 Маяк надежды светит даже в самом густом тумане сомнений."
        ]
    
    def _initialize_streak_quotes(self) -> Dict[str, List[str]]:
        """Quotes based on streak length"""
        return {
            "new_streak": [
                "🌱 Первый день - самый важный! Ты уже на правильном пути.",
                "🚪 Каждое большое путешествие начинается с первого шага.",
                "💫 Сегодня ты выбираешь себя. Это прекрасное начало!",
            ],
            "short_streak": [  # 2-6 days
                "🔥 Твоя серия растёт! Импульс изменений уже в движении.",
                "📈 День за днём ты строишь новую версию себя.",
                "⚡ Каждый день без поддавания - это день победы!",
                "🎯 Ты в потоке! Продолжай в том же духе.",
            ],
            "medium_streak": [  # 7-20 days
                "👑 Неделя силы! Ты доказываешь себе, что можешь всё.",
                "🏆 Твоя дисциплина впечатляет. Ты на верном пути!",
                "💪 Привычка самоконтроля становится частью тебя.",
                "🌟 Ты создаёшь новую реальность своей жизни.",
            ],
            "long_streak": [  # 21+ days
                "🦾 Ты легенда дисциплины! Твоя сила воли - пример для всех.",
                "👑 Месяц побед! Ты доказал, что невозможное возможно.",
                "🏅 Ты не просто изменился - ты трансформировался!",
                "🌊 Ты в состоянии потока. Это уже твоя новая природа.",
            ]
        }
    
    def _initialize_milestone_quotes(self) -> Dict[str, List[str]]:
        """Quotes for achievement milestones"""
        return {
            "first_intervention": [
                "🎉 Поздравляю с первой интервенцией! Ты сделал важнейший шаг.",
                "🌟 Первая победа - самая сладкая. Ты на правильном пути!",
                "💪 Ты перешёл от намерений к действиям. Это сила!",
            ],
            "interventions_10": [
                "🏆 10 побед! Ты доказываешь, что самоконтроль - это навык.",
                "🚀 Десятка интервенций! Твоя сила воли крепнет с каждым днём.",
                "⭐ 10 раз ты выбрал себя вместо импульса. Впечатляет!",
            ],
            "interventions_50": [
                "🎯 50 интервенций! Ты настоящий мастер самоконтроля.",
                "💎 Полсотни побед! Каждая из них формирует нового тебя.",
                "🔥 50 раз ты сказал 'нет' привычке и 'да' своей мечте!",
            ],
            "interventions_100": [
                "👑 СОТНЯ! Ты легенда CraveBreaker! Твоя дисциплина вдохновляет.",
                "🏆 100 интервенций - это не просто цифра, это образ жизни!",
                "🌟 Сто побед над собой. Ты кардинально изменил свою жизнь!",
            ],
            "growth": [
                "📈 Твой рост! Ты развиваешься каждый день.",
                "⬆️ Прогресс! Твое развитие заслуживает признания.",
                "🎊 Сила! Ты становишься сильнее с каждой победой.",
            ]
        }
    
    def _initialize_time_based_quotes(self) -> Dict[str, List[str]]:
        """Quotes based on time of day"""
        return {
            "morning": [
                "🌅 Доброе утро! Новый день - новые возможности быть лучше.",
                "☀️ Утро - время закладывать фундамент успешного дня.",
                "🐦 Ранняя пташка ловит червячка! Отличное начало дня.",
                "🌱 Каждое утро ты можешь заново выбрать, кем быть сегодня.",
            ],
            "afternoon": [
                "🌞 День в разгаре! Помни о своих целях в каждом решении.",
                "⚡ Середина дня - время подтвердить утренние намерения.",
                "🎯 Как дела с целями? Каждый момент - шанс их укрепить.",
                "💪 День продолжается, и твоя сила воли тоже!",
            ],
            "evening": [
                "🌆 Вечер - время подвести итоги дня. Чем ты гордишься?",
                "🌙 Завершая день, помни: каждая маленькая победа важна.",
                "⭐ Вечерняя рефлексия: что сегодня сделало тебя сильнее?",
                "🌃 День подходит к концу. Ты молодец, что работаешь над собой!",
            ],
            "night": [
                "🌙 Поздний вечер - время для спокойствия и самопрощения.",
                "🌟 Ночь мудрее дня. Завтра будет новая возможность расти.",
                "😴 Отдых - это не лень, а инвестиция в завтрашние победы.",
                "🌌 Спокойной ночи! Завтра ты проснёшься ещё сильнее.",
            ]
        }
    
    def _initialize_comeback_quotes(self) -> List[str]:
        """Quotes for users returning after a break"""
        return [
            "🔄 Добро пожаловать обратно! Каждое возвращение - это новое начало.",
            "🌅 Ты вернулся! Это показывает твою настойчивость и силу духа.",
            "💪 Падение - не поражение, если ты встаёшь. И ты встал!",
            "🚀 Новый старт! Прошлое не определяет будущее.",
            "⭐ Ты здесь, значит, не сдался. Это уже победа!",
            "🌱 Как феникс из пепла - ты возрождаешься сильнее.",
            "🎯 Каждый новый день - чистый лист для новых побед.",
        ]
    
    def get_personalized_morning_quote(self, user_progress: Dict) -> str:
        """Generate personalized morning motivation quote"""
        current_streak = user_progress.get("current_streak", 0)
        total_interventions = user_progress.get("total_interventions", 0)
        level = user_progress.get("level", 1)
        
        # Check if it's a comeback (last intervention was more than 2 days ago)
        last_date = user_progress.get("last_intervention_date")
        is_comeback = False
        if last_date:
            last_intervention = datetime.fromisoformat(last_date).date()
            days_since = (datetime.now().date() - last_intervention).days
            is_comeback = days_since > 2
        
        if is_comeback:
            base_quote = random.choice(self.comeback_quotes)
        elif current_streak == 0:
            base_quote = random.choice(self.streak_quotes["new_streak"])
        elif current_streak <= 6:
            base_quote = random.choice(self.streak_quotes["short_streak"])
        elif current_streak <= 20:
            base_quote = random.choice(self.streak_quotes["medium_streak"])
        else:
            base_quote = random.choice(self.streak_quotes["long_streak"])
        
        # Add personalized stats
        stats_addition = self._get_stats_addition(user_progress)
        
        return f"{base_quote}\n\n{stats_addition}"
    
    def get_contextual_quote(self, user_progress: Dict, context: str = "general") -> str:
        """Get quote based on current context"""
        hour = datetime.now().hour
        
        if context == "success":
            quotes = [
                "🎉 Отличная работа! Каждая победа укрепляет твою силу воли.",
                "⭐ Ты справился! Это доказательство твоей внутренней силы.",
                "💪 Ещё одна победа! Ты строишь привычку к успеху.",
                "🏆 Браво! Каждое 'нет' импульсу - это 'да' своей мечте.",
            ]
        elif context == "milestone":
            milestone_type = self._detect_milestone(user_progress)
            if milestone_type in self.milestone_quotes:
                quotes = self.milestone_quotes[milestone_type]
            else:
                quotes = self.base_quotes
        elif context == "evening_reflection":
            quotes = self.time_based_quotes["evening"]
        elif 5 <= hour < 12:
            quotes = self.time_based_quotes["morning"]
        elif 12 <= hour < 17:
            quotes = self.time_based_quotes["afternoon"]
        elif 17 <= hour < 22:
            quotes = self.time_based_quotes["evening"]
        else:
            quotes = self.time_based_quotes["night"]
        
        base_quote = random.choice(quotes)
        stats_addition = self._get_stats_addition(user_progress)
        
        return f"{base_quote}\n\n{stats_addition}"
    
    def _detect_milestone(self, user_progress: Dict) -> str:
        """Detect if user just reached a milestone"""
        total = user_progress.get("total_interventions", 0)
        
        if total == 1:
            return "first_intervention"
        elif total == 10:
            return "interventions_10"
        elif total == 50:
            return "interventions_50"
        elif total == 100:
            return "interventions_100"
        else:
            return "general"
    
    def _get_stats_addition(self, user_progress: Dict) -> str:
        """Add personalized stats to quote"""
        current_streak = user_progress.get("current_streak", 0)
        total_interventions = user_progress.get("total_interventions", 0)
        
        if current_streak > 0:
            streak_text = f"🔥 Серия: {current_streak} дн."
        else:
            streak_text = "🌱 Начни новую серию сегодня!"
        
        return f"📊 {streak_text} • Интервенций: {total_interventions}"
    
    # Achievement quotes removed - gamification disabled
    
    def get_daily_challenge_quote(self) -> str:
        """Get daily challenge motivational quote"""
        challenges = [
            "🎯 **Вызов дня:** Перед каждым решением спроси себя: 'Это приближает меня к цели?'",
            "🧘‍♀️ **Практика дня:** Сделай 3 глубоких вдоха перед любым импульсивным действием.",
            "💭 **Осознанность дня:** Замечай каждый момент выбора. В них твоя сила!",
            "🏆 **Цель дня:** Превратить хотя бы один импульс в осознанное решение.",
            "🌟 **Фокус дня:** Не на том, от чего отказываешься, а на том, что получаешь взамен.",
            "🎪 **Игра дня:** Представь себя режиссёром своей жизни. Какую сцену снимешь сегодня?",
            "🔥 **Энергия дня:** Каждое 'нет' привычке заряжает тебя энергией для 'да' мечте!",
        ]
        
        return random.choice(challenges)
    
    async def get_ai_personalized_quote(self, user_progress: Dict, context: str = "general") -> Optional[str]:
        """Generate AI-powered personalized quote using OpenAI"""
        if not openai_client:
            return None
            
        try:
            # Prepare user context for AI
            level = user_progress.get("level", 1)
            current_streak = user_progress.get("current_streak", 0)
            total_interventions = user_progress.get("total_interventions", 0)
            recent_badges = user_progress.get("recent_badges", [])
            
            # Create personalized prompt
            prompt = f"""Создай мотивационную цитату на русском языке для пользователя приложения по борьбе с вредными привычками.

Контекст пользователя:
- Уровень: {level}
- Текущая серия дней: {current_streak}
- Всего успешных интервенций: {total_interventions}
- Недавние достижения: {', '.join(recent_badges) if recent_badges else 'пока нет'}
- Ситуация: {context}

Требования к цитате:
1. Длина: 20-40 слов
2. Тон: поддерживающий, мотивирующий, но не навязчивый
3. Персонализация: учти текущий прогресс пользователя
4. Формат: одно предложение с эмодзи в начале
5. Избегай банальностей, будь оригинальным

Примеры хороших цитат:
"🌟 На уровне {level} ты уже не новичок - каждое твоё решение формирует нового себя!"
"🚀 {current_streak} дней подряд - это не случайность, это твоя новая сила!"

Создай уникальную цитату именно для этого пользователя:"""

            response = openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {"role": "system", "content": "Ты эксперт по мотивационному коучингу. Создаешь персонализированные цитаты для людей, борющихся с вредными привычками."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.8
            )
            
            ai_quote = response.choices[0].message.content
            return ai_quote.strip() if ai_quote else None
            
        except Exception as e:
            print(f"Error generating AI quote: {e}")
            return None
    
    async def get_enhanced_personalized_quote(self, user_progress: Dict, context: str = "general") -> str:
        """Get enhanced personalized quote with AI fallback to curated quotes"""
        # Try AI-generated quote first
        if openai_client:
            ai_quote = await self.get_ai_personalized_quote(user_progress, context)
            if ai_quote:
                stats_addition = self._get_stats_addition(user_progress)
                return f"{ai_quote}\n\n{stats_addition}"
        
        # Fallback to curated contextual quotes
        return self.get_contextual_quote(user_progress, context)
    
    async def get_ai_achievement_celebration(self, badge_name: str, user_progress: Dict) -> Optional[str]:
        """Generate AI-powered achievement celebration message"""
        if not openai_client:
            return None
            
        try:
            level = user_progress.get("level", 1)
            total_interventions = user_progress.get("total_interventions", 0)
            
            prompt = f"""Создай поздравительное сообщение на русском языке для пользователя, который получил достижение в приложении по борьбе с вредными привычками.

Достижение: {badge_name}
Уровень пользователя: {level}
Всего интервенций: {total_interventions}

Требования:
1. Длина: 15-30 слов
2. Тон: радостный, празднующий успех
3. Персонализация: учти конкретное достижение
4. Формат: одно вдохновляющее предложение
5. Начни с подходящего эмодзи

Примеры:
"🎉 Первые 10 интервенций - это фундамент твоей новой жизни!"
"🏆 Неделя дисциплины! Ты доказал себе, что можешь всё!"

Создай уникальное поздравление:"""

            response = openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {"role": "system", "content": "Ты мотивационный коуч, который празднует достижения людей в борьбе с вредными привычками."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,
                temperature=0.9
            )
            
            ai_message = response.choices[0].message.content
            return ai_message.strip() if ai_message else None
            
        except Exception as e:
            print(f"Error generating AI achievement message: {e}")
            return None

# Global instance
motivation_generator = MotivationQuotesGenerator()