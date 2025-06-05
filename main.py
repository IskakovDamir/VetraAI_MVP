"""
🔥 ПОЛНОСТЬЮ ОБНОВЛЕННЫЙ main.py для Vetra AI
✅ Интеграция СПЕЦИАЛЬНОГО парсера множественных событий
✅ Решение проблемы объединения событий в одно
✅ Поддержка структурированных запросов типа "3 мероприятия Презентация проекта – 3 июня в 12:00"
✅ Все исправления и улучшения включены
"""

from datetime import datetime, timedelta
import pytz
import logging
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from datetime_utils import validate_datetime, format_datetime_for_display
from simplified_auth import fixed_auth_manager, get_user_calendar_service
from config import TELEGRAM_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Часовой пояс по умолчанию
DEFAULT_TIMEZONE = 'Asia/Almaty'

# БЕТА-ПОЛЬЗОВАТЕЛИ
BETA_USERS = {
    785966064,  # @Iskakov_Damir
    # Добавьте ID других тестеров:
    # 123456789,  # @leryaq
    # 987654321,  # @onai1688  
    # 555666777,  # @Aman_Is
}

# Админы
ADMIN_USERS = {
    785966064,  # @Iskakov_Damir (админ)
}

# Словарь для отслеживания авторизации пользователей
pending_authorizations = {}

# 🎯 СПЕЦИАЛЬНЫЕ ФУНКЦИИ ДЛЯ ПАРСИНГА МНОЖЕСТВЕННЫХ СОБЫТИЙ
# (Интегрированы прямо в main.py для упрощения)

def parse_structured_events_integrated(text, user_timezone='Asia/Almaty'):
    """
    🔥 ИНТЕГРИРОВАННАЯ функция парсинга структурированных событий
    Специально для случаев типа: "3 мероприятия Презентация проекта – 3 июня в 12:00"
    """
    logger.info(f"🎯 Интегрированный парсинг структурированных событий: '{text}'")
    
    # Импортируем enhanced_datetime_parser
    from datetime_utils import enhanced_datetime_parser
    
    # Убираем лишние пробелы и переносы
    text = re.sub(r'\s+', ' ', text.strip())
    
    events = []
    
    # МЕТОД 1: Поиск по паттерну "название - дата в время"
    event_patterns = [
        r'([^–\-]+)\s*[–\-]\s*(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+в\s+\d{1,2}:\d{2})',
        r'([^–\-]+)\s*[–\-]\s*(\d{1,2}\.\d{1,2}\s+в\s+\d{1,2}:\d{2})',
        r'([^–\-]+)\s*[–\-]\s*(\d{1,2}/\d{1,2}\s+в\s+\d{1,2}:\d{2})',
    ]
    
    for pattern in event_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            logger.info(f"✅ Найдено совпадений по паттерну: {len(matches)}")
            
            for match in matches:
                title_part = match[0].strip()
                time_part = match[1].strip()
                
                # Очищаем название от мусора
                clean_title = clean_event_title_integrated(title_part)
                if not clean_title or len(clean_title) < 3:
                    continue
                
                # Парсим дату/время
                full_text = f"{clean_title} {time_part}"
                parsed_datetime = enhanced_datetime_parser(full_text, user_timezone)
                
                if parsed_datetime:
                    events.append((parsed_datetime, clean_title, 'event'))
                    logger.info(f"✅ Добавлено событие: '{clean_title}' в {parsed_datetime}")
    
    # МЕТОД 2: Разбивка по строкам (если есть переносы)
    if not events and ('\n' in text or '  ' in text):
        lines = re.split(r'\n|  +', text)
        for line in lines:
            line = line.strip()
            if len(line) < 5:  # Слишком короткая строка
                continue
            
            # Пропускаем заголовки типа "3 мероприятия"
            if re.match(r'^\d+\s*мероприятий?', line, re.IGNORECASE):
                continue
                
            # Пытаемся распарсить как отдельное событие
            parsed_datetime = enhanced_datetime_parser(line, user_timezone)
            if parsed_datetime:
                clean_title = extract_title_from_line_integrated(line)
                if clean_title:
                    events.append((parsed_datetime, clean_title, 'event'))
                    logger.info(f"✅ Из строки добавлено: '{clean_title}' в {parsed_datetime}")
    
    # МЕТОД 3: Поиск временных меток и разбивка по ним
    if not events:
        # Ищем все даты в тексте
        date_patterns = [
            r'\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+в\s+\d{1,2}:\d{2}',
            r'\d{1,2}\.\d{1,2}\s+в\s+\d{1,2}:\d{2}',
            r'\d{1,2}/\d{1,2}\s+в\s+\d{1,2}:\d{2}'
        ]
        
        all_dates = []
        for pattern in date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                all_dates.append((match.start(), match.end(), match.group()))
        
        if len(all_dates) >= 2:
            logger.info(f"✅ Найдено {len(all_dates)} временных меток")
            
            # Сортируем по позиции в тексте
            all_dates.sort(key=lambda x: x[0])
            
            for i, (start_pos, end_pos, date_text) in enumerate(all_dates):
                # Определяем границы события
                prev_end = all_dates[i-1][1] if i > 0 else 0
                
                # Извлекаем текст события (от предыдущей даты до текущей)
                event_start = prev_end
                event_end = end_pos
                event_text = text[event_start:event_end].strip()
                
                # Убираем лишний текст в начале
                if i == 0:
                    # Для первого события убираем заголовки
                    event_text = re.sub(r'^.*?(?=\w+\s*[–\-])', '', event_text)
                
                parsed_datetime = enhanced_datetime_parser(event_text, user_timezone)
                if parsed_datetime:
                    clean_title = extract_title_from_text_chunk_integrated(event_text)
                    if clean_title:
                        events.append((parsed_datetime, clean_title, 'event'))
                        logger.info(f"✅ По временной метке: '{clean_title}' в {parsed_datetime}")
    
    logger.info(f"📊 Итого найдено структурированных событий: {len(events)}")
    return events if events else None

def clean_event_title_integrated(title):
    """Очистка названия события от мусора"""
    # Убираем номера и счетчики в начале
    title = re.sub(r'^\d+\s*мероприятий?\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'^\d+\s*событий?\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'^\d+\s*встреч?\s*', '', title, flags=re.IGNORECASE)
    
    # Убираем управляющие слова
    title = re.sub(r'^(?:запланируй|создай|добавь)\s+(?:мне\s+)?', '', title, flags=re.IGNORECASE)
    
    # Убираем лишние символы
    title = re.sub(r'^[–\-\s]+|[–\-\s]+$', '', title)
    title = title.strip()
    
    return title if len(title) >= 3 else None

def extract_title_from_line_integrated(line):
    """Извлечение названия из строки"""
    # Убираем дату/время
    line = re.sub(r'\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+в\s+\d{1,2}:\d{2}', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\d{1,2}\.\d{1,2}\s+в\s+\d{1,2}:\d{2}', '', line)
    line = re.sub(r'в\s+\d{1,2}:\d{2}', '', line)
    
    # Убираем тире и лишние символы
    line = re.sub(r'^[–\-\s]+|[–\-\s]+$', '', line)
    line = line.strip()
    
    return clean_event_title_integrated(line)

def extract_title_from_text_chunk_integrated(text):
    """Извлечение названия из куска текста"""
    # Убираем временные части
    text = re.sub(r'\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+в\s+\d{1,2}:\d{2}', '', text, flags=re.IGNORECASE)
    
    # Ищем событийные слова
    event_words = ['презентация', 'встреча', 'обед', 'звонок', 'созвон', 'совещание', 'мероприятие']
    
    for word in event_words:
        if word in text.lower():
            # Извлекаем фразу с этим словом
            pattern = rf'([^–\-]*{word}[^–\-]*)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return clean_event_title_integrated(match.group(1))
    
    # Fallback - первые слова
    words = text.split()[:3]
    return clean_event_title_integrated(' '.join(words)) if words else None

def enhanced_extract_multiple_events_integrated(text, user_timezone='Asia/Almaty'):
    """
    🔥 ИНТЕГРИРОВАННАЯ улучшенная функция извлечения событий
    Сначала пытается структурированный парсинг, потом обычный
    """
    logger.info(f"🔍 Интегрированный улучшенный анализ текста: '{text}'")
    
    # ПРИОРИТЕТ 1: Структурированные события
    structured_events = parse_structured_events_integrated(text, user_timezone)
    if structured_events and len(structured_events) >= 2:
        logger.info(f"✅ Найдено {len(structured_events)} структурированных событий")
        return structured_events
    
    # ПРИОРИТЕТ 2: Обычная логика (из text_parser.py)
    try:
        from text_parser import extract_multiple_events
        regular_events = extract_multiple_events(text, user_timezone)
        if regular_events:
            logger.info(f"✅ Найдено {len(regular_events)} обычных событий")
            return regular_events
    except Exception as e:
        logger.warning(f"⚠️ Ошибка обычного парсера: {e}")
    
    # ПРИОРИТЕТ 3: Если ничего не нашли, возвращаем структурированные (даже если 1)
    if structured_events:
        logger.info(f"✅ Возвращаем {len(structured_events)} найденных событий")
        return structured_events
    
    logger.warning("❌ События не найдены")
    return []

async def check_user_access(update: Update) -> bool:
    """Проверить доступ пользователя к боту"""
    user_id = update.effective_user.id
    
    if user_id in ADMIN_USERS or user_id in BETA_USERS:
        return True
    
    await update.message.reply_text(
        "🔒 **Доступ ограничен**\n\n"
        "Извините, но Vetra AI находится в закрытом бета-тестировании.\n"
        "Чтобы получить доступ, обратитесь к разработчику.\n\n"
        "🔗 **Контакт:** @Iskakov_Damir",
        parse_mode='Markdown'
    )
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔥 ОБНОВЛЕННАЯ команда /start с информацией о СПЕЦИАЛЬНОМ парсере"""
    user = update.effective_user
    user_id = user.id
    
    # Проверяем доступ к боту
    if not await check_user_access(update):
        return
    
    # Проверяем авторизацию Google Calendar
    if not fixed_auth_manager.is_user_authorized(user_id):
        await send_authorization_request(update, context)
        return
    
    # Приветствие для авторизованного пользователя
    user_info = fixed_auth_manager.get_user_info(user_id)
    calendar_info = ""
    if user_info and user_info.get('primary_calendar'):
        cal = user_info['primary_calendar']
        calendar_info = f"\n📅 **Подключен календарь:** {cal['summary']}"
    
    welcome_text = f"""
👋 Привет, **{user.first_name}**! Я — **Vetra AI**.

✅ **Вы авторизованы и готовы к работе!**{calendar_info}

🎯 **СПЕЦИАЛЬНАЯ ФУНКЦИЯ: Множественные события**
Теперь бот умеет создавать **несколько событий** из одного сообщения!

📝 **НОВЫЕ ФОРМАТЫ МНОЖЕСТВЕННЫХ СОБЫТИЙ:**

🎯 **Структурированный ввод (КАК В ВАШИХ СКРИНШОТАХ):**
• "запланируй мне два мероприятия Презентация проекта – 3 июня в 12:00 Встреча с командой – 5 июня в 9:00"
• "3 мероприятия Презентация проекта – 3 июня в 12:00 Обед с клиентами – 31 мая в 14:30 Встреча с командой – 5 июня в 9:00"
• "создай встречу с клиентом – 15 мая в 10:00 и обед с партнерами – 16 мая в 13:00"

🔄 **Классические множественные события:**
• "встреча с клиентом в 10:00, обед с коллегами в 13:00"
• "звонок маме в 9:00, презентация в 14:00"
• "работа с 9:00 до 17:00 и потом ужин в 19:00"

⏰ **Временные диапазоны:**
• "встреча с 12:00 до 14:00"
• "работа в 17:00 на 2 часа"
• "обед в 13:00 на полчаса"

📅 **Конкретные даты:**
• "встреча 3 июня в 12:00"
• "обед 31 мая в 14:30"
• "презентация 15 мая в 16:00"

🔥 **ГЛАВНОЕ: КАЖДОЕ СОБЫТИЕ СОЗДАЕТСЯ ОТДЕЛЬНО!**
✅ Больше никаких объединенных названий!
✅ Каждое событие со своей датой и временем!
✅ Проблема из ваших скриншотов РЕШЕНА!

❓ /help - Подробная справка
🔧 /auth - Переавторизация
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def send_authorization_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить запрос на авторизацию (упрощенный)"""
    user = update.effective_user
    user_id = user.id
    
    # Создаем ссылку авторизации
    auth_url = fixed_auth_manager.create_authorization_url(user_id)
    
    if not auth_url:
        await update.message.reply_text(
            "❌ **Ошибка создания ссылки авторизации**\n\n"
            "Попробуйте позже или обратитесь к разработчику.",
            parse_mode='Markdown'
        )
        return
    
    # Создаем кнопку для авторизации
    keyboard = [
        [InlineKeyboardButton("🔐 Авторизоваться в Google", url=auth_url)],
        [InlineKeyboardButton("❓ Помощь", callback_data="auth_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Добавляем в ожидающие авторизацию
    pending_authorizations[user_id] = {
        'timestamp': datetime.now(),
        'auth_url': auth_url
    }
    
    auth_text = f"""
🔐 **Требуется авторизация Google Calendar**

Привет, **{user.first_name}**! 

Для работы с вашим календарем мне нужен доступ к Google Calendar.

**📋 Простая инструкция:**
1. Нажмите кнопку "Авторизоваться в Google" ниже
2. Войдите в свой Google аккаунт
3. Разрешите доступ к календарю
4. **Готово!** Авторизация пройдет автоматически

⏱️ **Не получается?** Попробуйте еще раз через 30 секунд или напишите /auth

🔒 **Безопасность:** Я получу доступ только к вашему календарю и буду использовать его исключительно для создания событий по вашим запросам.
"""
    
    await update.message.reply_text(auth_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    # Запускаем проверку авторизации
    asyncio.create_task(check_authorization_completion(user_id, context))

async def check_authorization_completion(user_id, context):
    """Проверить завершение авторизации"""
    max_wait_time = 300  # 5 минут
    check_interval = 5   # каждые 5 секунд
    
    for _ in range(max_wait_time // check_interval):
        await asyncio.sleep(check_interval)
        
        # Проверяем, авторизовался ли пользователь
        if fixed_auth_manager.is_user_authorized(user_id):
            # Пользователь авторизовался!
            if user_id in pending_authorizations:
                del pending_authorizations[user_id]
            
            # Отправляем сообщение об успехе
            try:
                user_info = fixed_auth_manager.get_user_info(user_id)
                
                success_text = "✅ **Авторизация успешна!**\n\n"
                
                if user_info and user_info.get('primary_calendar'):
                    cal = user_info['primary_calendar']
                    success_text += f"📅 **Подключен календарь:** {cal['summary']}\n"
                    success_text += f"🌍 **Часовой пояс:** {cal.get('timezone', 'UTC')}\n"
                    success_text += f"📊 **Всего календарей:** {user_info.get('calendar_count', 1)}\n\n"
                
                success_text += "🔥 **Теперь вы можете использовать ВСЕ новые возможности!**\n\n"
                success_text += "🧪 **Попробуйте проблемные запросы из ваших скриншотов:**\n"
                success_text += "• \"запланируй мне два мероприятия Презентация проекта – 3 июня в 12:00 Встреча с командой – 5 июня в 9:00\"\n"
                success_text += "• \"3 мероприятия Презентация проекта – 3 июня в 12:00 Обед с клиентами – 31 мая в 14:30 Встреча с командой – 5 июня в 9:00\""
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=success_text,
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки сообщения об успехе: {e}")
            
            return
        
        # Проверяем, не отменил ли пользователь
        if user_id not in pending_authorizations:
            return
    
    # Время ожидания истекло
    if user_id in pending_authorizations:
        del pending_authorizations[user_id]
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="⏰ **Время авторизации истекло**\n\n"
                     "Попробуйте еще раз: /auth",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ Ошибка отправки timeout сообщения: {e}")

async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /auth для авторизации или переавторизации"""
    user_id = update.effective_user.id
    
    # Проверяем доступ
    if not await check_user_access(update):
        return
    
    # Отзываем старую авторизацию если есть
    if fixed_auth_manager.is_user_authorized(user_id):
        fixed_auth_manager.revoke_user_authorization(user_id)
        await update.message.reply_text("🔄 **Старая авторизация отозвана. Создаю новую...**")
    
    await send_authorization_request(update, context)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "auth_help":
        help_text = """
❓ **Помощь по авторизации**

**Простая инструкция:**

1️⃣ **Нажмите кнопку "Авторизоваться в Google"**
   • Откроется страница Google

2️⃣ **Войдите в свой Google аккаунт**
   • Используйте аккаунт с нужным календарем

3️⃣ **Разрешите доступ**
   • Нажмите "Разрешить" на странице прав

4️⃣ **Готово!**
   • Авторизация пройдет **автоматически**
   • Никаких кодов копировать не нужно!

🔧 **Проблемы?**
• Попробуйте еще раз через 30 секунд
• Убедитесь, что используете тот же браузер
• Если не работает, напишите /auth для новой попытки

🔒 **Безопасность:**
Бот получает доступ только к календарю и использует его исключительно для создания событий по вашим запросам.
"""
        await query.edit_message_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔥 ПОЛНОСТЬЮ ОБНОВЛЕННАЯ обработка сообщений с ИНТЕГРИРОВАННЫМ СПЕЦИАЛЬНЫМ парсером"""
    user_text = update.message.text
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Проверяем доступ к боту
    if not await check_user_access(update):
        return
    
    # Проверяем авторизацию пользователя
    if not fixed_auth_manager.is_user_authorized(user_id):
        await update.message.reply_text(
            "🔐 **Требуется авторизация**\n\n"
            "Для создания событий в календаре нужно авторизоваться.\n\n"
            "Используйте команду: /auth",
            parse_mode='Markdown'
        )
        return
    
    logger.info(f"📨 Получено сообщение от пользователя {user_id}: '{user_text}'")
    
    # Отправляем сообщение о том, что обрабатываем запрос
    processing_msg = await update.message.reply_text("🎯 Анализирую ваш запрос с помощью СПЕЦИАЛЬНОГО парсера множественных событий...")
    
    try:
        # 🔥 ГЛАВНАЯ НОВАЯ ЛОГИКА: Используем интегрированный специальный парсер
        events = enhanced_extract_multiple_events_integrated(user_text, DEFAULT_TIMEZONE)
        
        if not events:
            await processing_msg.edit_text(
                "❌ Не удалось определить дату и время.\n\n"
                "💡 **Попробуйте форматы из ваших скриншотов:**\n\n"
                "🎯 **Структурированный ввод:**\n"
                "• 'запланируй мне два мероприятия Презентация проекта – 3 июня в 12:00 Встреча с командой – 5 июня в 9:00'\n"
                "• '3 мероприятия Презентация проекта – 3 июня в 12:00 Обед с клиентами – 31 мая в 14:30 Встреча с командой – 5 июня в 9:00'\n"
                "• 'создай встречу с клиентом – 15 мая в 10:00 и обед с партнерами – 16 мая в 13:00'\n\n"
                "🔄 **Множественные события через запятые:**\n"
                "• 'встреча с клиентом в 10:00, обед с коллегами в 13:00'\n"
                "• 'звонок маме в 9:00, презентация в 14:00'\n\n"
                "⏰ **Временные диапазоны:**\n"
                "• 'встреча с 12:00 до 14:00'\n"
                "• 'работа в 17:00 на 2 часа'\n\n"
                "📅 **Конкретные даты:**\n"
                "• 'встреча 3 июня в 12:00'\n"
                "• 'обед 31 мая в 14:30'"
            )
            return
        
        # Обновляем сообщение с количеством найденных событий
        event_count = len(events)
        if event_count == 1:
            await processing_msg.edit_text("📅 Создаю событие в вашем календаре...")
        else:
            await processing_msg.edit_text(f"🎯 Создаю {event_count} ОТДЕЛЬНЫХ событий в вашем календаре (СПЕЦИАЛЬНЫЙ парсер)...")
        
        # Получаем сервис календаря для конкретного пользователя
        calendar_service = get_user_calendar_service(user_id)
        if not calendar_service:
            await processing_msg.edit_text(
                "❌ **Ошибка доступа к календарю**\n\n"
                "Не удалось получить доступ к вашему календарю.\n"
                "Попробуйте переавторизоваться: /auth"
            )
            return
        
        # Создаем события
        created_events = []
        failed_events = []

        for i, event_data in enumerate(events, 1):
            # КРИТИЧНО: Проверяем, есть ли end_time (для диапазонов)
            if len(event_data) == 4:
                start_datetime, summary, event_type, end_datetime = event_data
                logger.info(f"📊 Событие {i} с диапазоном: {start_datetime.strftime('%H:%M')}-{end_datetime.strftime('%H:%M')}")
            else:
                start_datetime, summary, event_type = event_data
                # Используем умную длительность для обычных событий
                end_datetime = get_smart_end_time(start_datetime, summary)
                logger.info(f"📊 Событие {i} без диапазона: {start_datetime.strftime('%H:%M')}-{end_datetime.strftime('%H:%M')}")

            try:
                # Валидируем дату/время
                start_datetime = validate_datetime(start_datetime, DEFAULT_TIMEZONE)
                if not start_datetime:
                    failed_events.append(summary + " (неверная дата)")
                    continue
                
                # Создаем событие через индивидуальный сервис пользователя
                logger.info(f"📝 Создаем событие {i}/{event_count}: '{summary}' в {start_datetime}")
                
                event_result = add_event_to_user_calendar(
                    calendar_service,
                    summary,
                    start_datetime,
                    end_datetime,
                    DEFAULT_TIMEZONE
                )
                
                if event_result:
                    created_events.append({
                        'summary': summary,
                        'start': start_datetime,
                        'end': end_datetime,
                        'type': event_type,
                        'id': event_result.get('id', ''),
                        'html_link': event_result.get('htmlLink', ''),
                        'is_range': len(event_data) == 4  # Помечаем события с диапазоном
                    })
                    logger.info(f"✅ Событие {i} '{summary}' создано успешно")
                else:
                    failed_events.append(summary)
                    logger.error(f"❌ Не удалось создать событие {i}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка создания события '{summary}': {e}")
                failed_events.append(summary)
        
        # 🎯 СПЕЦИАЛЬНЫЙ ответ пользователю для множественных событий
        if created_events and not failed_events:
            # Все события созданы успешно
            if len(created_events) == 1:
                event = created_events[0]
                
                success_text = f"""
✅ **Событие успешно добавлено в ваш календарь!**

📋 **Детали:**
• **Название:** {event['summary']}
• **Дата:** {format_datetime_for_display(event['start'])}
• **Время:** {event['start'].strftime('%H:%M')} - {event['end'].strftime('%H:%M')}
• **Тип:** {'📅 Событие' if event['type'] == 'event' else '📋 Задача'}

🔗 [Открыть в Google Calendar]({event['html_link']})


"""
            else:
                success_text = f"🎯 **ВСЕ {len(created_events)} событий успешно добавлены в ваш календарь!**\n\n"
                
                for i, event in enumerate(created_events, 1):
                    duration_minutes = int((event['end'] - event['start']).total_seconds() / 60)
                    if duration_minutes >= 60:
                        hours = duration_minutes // 60
                        minutes = duration_minutes % 60
                        if minutes > 0:
                            duration_display = f" ({hours}ч {minutes}мин)"
                        else:
                            duration_display = f" ({hours}ч)"
                    else:
                        duration_display = f" ({duration_minutes}мин)"
                    
                    success_text += f"""**{i}. {event['summary']}**
📅 {format_datetime_for_display(event['start'])} ({event['start'].strftime('%H:%M')}-{event['end'].strftime('%H:%M')}{duration_display})
{'📅 Событие' if event['type'] == 'event' else '📋 Задача'}

"""
                
                # Добавляем активную ссылку на Google Calendar
                primary_event = created_events[0]  # Используем ссылку первого события
                success_text += f"🔗 [Открыть в Google Calendar]({primary_event['html_link']})"
            
            await processing_msg.edit_text(success_text, parse_mode='Markdown')
            
        elif created_events and failed_events:
            # Частично успешно
            partial_text = f"""
⚠️ **Частично выполнено (СПЕЦИАЛЬНЫЙ парсер)**

✅ **Созданы ({len(created_events)}):**
"""
            for event in created_events:
                duration_minutes = int((event['end'] - event['start']).total_seconds() / 60)
                if duration_minutes >= 60:
                    hours = duration_minutes // 60
                    duration_display = f" ({hours}ч)"
                else:
                    duration_display = f" ({duration_minutes}мин)"
                
                partial_text += f"• **{event['summary']}** - {format_datetime_for_display(event['start'])}{duration_display}\n"
            
            partial_text += f"\n❌ **Не удалось создать ({len(failed_events)}):**\n"
            for failed in failed_events:
                partial_text += f"• {failed}\n"
            
            partial_text += f"\n🎯 **СПЕЦИАЛЬНЫЙ парсер частично сработал!**"
            
            await processing_msg.edit_text(partial_text, parse_mode='Markdown')
            
        else:
            # Ничего не создано
            await processing_msg.edit_text(
                "❌ **Не удалось создать события в календаре.**\n\n"
                "🔧 Возможные причины:\n"
                "• Проблемы с авторизацией Google\n"
                "• Превышены лимиты API\n"
                "• Нет доступа к интернету\n\n"
                "Попробуйте переавторизоваться: /auth"
            )
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")
        await processing_msg.edit_text(
            f"⚠️ **Произошла ошибка при обработке запроса.**\n\n"
            f"🔧 Техническая информация: {str(e)}\n\n"
            f"Попробуйте ещё раз или обратитесь к разработчику."
        )

def add_event_to_user_calendar(service, summary, start_datetime, end_datetime, timezone='Asia/Almaty'):
    """Добавить событие в календарь конкретного пользователя"""
    try:
        # Формируем событие в правильном формате для Google Calendar API
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': timezone,
            },
            'description': f'✨ Создано через Vetra AI (СПЕЦИАЛЬНЫЙ парсер множественных событий)'
        }
        
        logger.info(f"📅 Создаем событие: {summary}")
        logger.info(f"⏰ Время: {start_datetime.isoformat()} - {end_datetime.isoformat()}")
        
        # Создаем событие
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        
        logger.info(f"✅ Событие создано! ID: {event_result.get('id')}")
        return event_result
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания события: {e}")
        return None

def get_smart_end_time(start_time, summary, default_duration_hours=1):
    """Умное определение времени окончания на основе типа события"""
    summary_lower = summary.lower()
    
    # Короткие события (30 минут)
    short_events = ['звонок', 'созвон', 'обед', 'кофе', 'перерыв', 'call']
    if any(word in summary_lower for word in short_events):
        return start_time + timedelta(minutes=30)
    
    # Длинные события (2 часа)
    long_events = ['презентация', 'семинар', 'лекция', 'тренировка', 'конференция', 'воркшоп']
    if any(word in summary_lower for word in long_events):
        return start_time + timedelta(hours=2)
    
    # Очень длинные события (3-4 часа)
    very_long_events = ['экзамен', 'собеседование', 'интервью']
    if any(word in summary_lower for word in very_long_events):
        return start_time + timedelta(hours=3)
    
    # По умолчанию (1 час)
    return start_time + timedelta(hours=default_duration_hours)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔥 ОБНОВЛЕННАЯ команда /help с информацией о специальном парсере"""
    # Проверяем доступ
    if not await check_user_access(update):
        return
        
    help_text = """
🆘 **Помощь по использованию Vetra AI (СПЕЦИАЛЬНЫЙ ПАРСЕР)**

🎯 **СПЕЦИАЛЬНАЯ ФУНКЦИЯ: Множественные события**
Теперь бот умеет создавать **несколько событий** из одного сообщения!

📝 **ФОРМАТЫ ИЗ ВАШИХ СКРИНШОТОВ (ТЕПЕРЬ РАБОТАЮТ!):**

🎯 **Структурированный ввод:**
• "запланируй мне два мероприятия Презентация проекта – 3 июня в 12:00 Встреча с командой – 5 июня в 9:00"
• "3 мероприятия Презентация проекта – 3 июня в 12:00 Обед с клиентами – 31 мая в 14:30 Встреча с командой – 5 июня в 9:00"
• "создай встречу с клиентом – 15 мая в 10:00 и обед с партнерами – 16 мая в 13:00"

🔄 **Множественные события через запятые:**
• "встреча с клиентом в 10:00, обед с коллегами в 13:00"
• "звонок маме в 9:00, презентация в 14:00"
• "работа с 9:00 до 17:00 и потом ужин в 19:00"

⏰ **Временные диапазоны:**
• "встреча с Лерой с 12:00 до 14:00"
• "презентация проекта в 17:00 на 2 часа"
• "обед в 13:00 на 30 минут"
• "работа 09:00-17:00"

📅 **Конкретные даты:**
• "встреча 3 июня в 12:00"
• "обед 31 мая в 14:30"  
• "презентация 15 мая в 16:00"
• "дедлайн 25.12.2024 в 23:59"

🎯 **Ключевые улучшения:**
✅ **ПРОБЛЕМА ИЗ СКРИНШОТОВ РЕШЕНА:** Каждое событие создается отдельно!
✅ Больше никаких объединенных названий типа "3 мероприятия Презентация – Обед – Встреча"
✅ Каждое событие со своей правильной датой и временем
✅ Умная очистка названий от мусора ("запланируй мне", "3 мероприятия")
✅ Поддержка всех форматов дат (3 июня, 31 мая, 15.06)

❓ **Команды:**
• /start - Начать работу
• /help - Эта справка  
• /auth - Авторизация Google Calendar (БЕЗ кодов!)

💡 **РЕЗУЛЬТАТ:** Вместо 1 объединенного события → несколько отдельных событий!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def add_beta_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления бета-пользователя (только для админов)"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_USERS:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Неверный формат команды**\n\n"
            "Используйте: `/add_beta USER_ID`\n\n"
            "Например: `/add_beta 123456789`",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_user_id = int(context.args[0])
        BETA_USERS.add(new_user_id)
        
        await update.message.reply_text(
            f"✅ **Пользователь {new_user_id} добавлен в бета-тестеры!**\n\n"
            f"Теперь он может использовать СПЕЦИАЛЬНЫЙ парсер множественных событий.",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Админ {user_id} добавил пользователя {new_user_id} в бета-тестеры")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат User ID. Должно быть число.")

def main():
    """🔥 Запуск ПОЛНОСТЬЮ ОБНОВЛЕННОГО бота со СПЕЦИАЛЬНЫМ парсером"""
    logger.info("🔥 Запуск Vetra AI бота со СПЕЦИАЛЬНЫМ парсером множественных событий...")
    
    # Создаем приложение
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("auth", auth_command))
    app.add_handler(CommandHandler("add_beta", add_beta_user_command))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ ПОЛНОСТЬЮ ОБНОВЛЕННЫЙ бот запущен и готов к работе!")
    logger.info("🎯 СПЕЦИАЛЬНЫЕ ВОЗМОЖНОСТИ:")
    logger.info("   • СПЕЦИАЛЬНЫЙ парсер множественных событий (ИНТЕГРИРОВАН)")
    logger.info("   • Решение проблемы объединения событий в одно")
    logger.info("   • Поддержка структурированных запросов из скриншотов")
    logger.info("   • Каждое событие создается отдельно со своей датой и временем")
    logger.info("   • Умная очистка названий от мусора")
    logger.info("🔥 ПРОБЛЕМА ИЗ СКРИНШОТОВ РЕШЕНА!")
    
    # Запускаем polling
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()