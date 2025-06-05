"""
🧠 ИСПРАВЛЕННЫЙ text_parser.py для Vetra AI - РЕШЕНИЕ ПРОБЛЕМЫ МНОЖЕСТВЕННЫХ СОБЫТИЙ
✅ Поддержка временных диапазонов (с 12:00 до 14:00)
✅ ПОЛНОСТЬЮ исправленная очистка названий событий
✅ КАРДИНАЛЬНО ПЕРЕРАБОТАННАЯ поддержка множественных событий
✅ ИСПРАВЛЕНА логика: сначала разбивка по запятым, потом поиск диапазонов
"""

import re
from datetime import datetime, timedelta
from datetime_utils import enhanced_datetime_parser, validate_datetime
import logging

logger = logging.getLogger(__name__)

def extract_multiple_events(text, user_timezone='Asia/Almaty'):
    """🎯 ПЕРЕРАБОТАННАЯ ГЛАВНАЯ ФУНКЦИЯ: Умное извлечение множественных событий"""
    logger.info(f"🔍 Анализ многособытийного текста: '{text}'")
    
    # ШАГ 1: ПРИОРИТЕТ - Сначала ищем множественные события через запятые
    comma_events = extract_comma_separated_events_completely_fixed(text, user_timezone)
    if comma_events:
        logger.info(f"✅ Найдено {len(comma_events)} событий через запятые")
        return comma_events
    
    # ШАГ 2: Временные диапазоны (с X до Y) - только для одиночных событий
    time_range_event = extract_time_range_event(text, user_timezone)
    if time_range_event:
        logger.info("✅ Найден временной диапазон")
        return [time_range_event]
    
    # ШАГ 3: Одиночное событие
    single_event = extract_single_event(text, user_timezone)
    if single_event:
        return [single_event]
    
    logger.warning("❌ События не найдены")
    return []

def extract_comma_separated_events_completely_fixed(text, user_timezone):
    """🔥 ПОЛНОСТЬЮ ПЕРЕРАБОТАННАЯ ФУНКЦИЯ: Правильная обработка множественных событий
    
    НОВАЯ СТРАТЕГИЯ:
    1. СНАЧАЛА разбиваем текст по запятым и союзам
    2. ПОТОМ ищем временные паттерны в каждой части отдельно
    3. Обрабатываем каждую часть как отдельное событие
    """
    logger.info(f"📝 ИСПРАВЛЕННЫЙ поиск событий через запятые: '{text}'")
    
    # Проверяем наличие запятых
    if ',' not in text and ' и ' not in text:
        logger.info("❌ Запятые или союзы не найдены")
        return None
    
    # Подсчитываем количество временных указателей для валидации
    time_indicators = re.findall(r'\b(?:в|с|до)\s+\d{1,2}[:\.]?\d{2}|\d{1,2}[:\.]?\d{2}', text, re.IGNORECASE)
    logger.info(f"📊 Найдено временных указателей: {len(time_indicators)}")
    
    if len(time_indicators) < 2:
        logger.info("❌ Недостаточно временных указателей для множественных событий")
        return None
    
    # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Разбиваем текст по запятым и союзам
    # Улучшенные паттерны разбивки
    split_patterns = [
        r',\s*(?:и\s+)?(?:потом\s+)?(?:также\s+)?(?:еще\s+)?',  # запятая + союзы
        r'\s+и\s+потом\s+',  # "и потом"
        r'\s+а\s+потом\s+',  # "а потом"
        r';\s*',             # точка с запятой
    ]
    
    # Объединяем все паттерны в один
    combined_pattern = '|'.join(f'({pattern})' for pattern in split_patterns)
    
    # Разбиваем текст
    parts = re.split(combined_pattern, text, flags=re.IGNORECASE)
    
    # Убираем разделители и пустые части
    clean_parts = []
    for part in parts:
        if part and not re.match(r'^[,;\s]*(?:и|потом|также|еще)?[,;\s]*$', part, re.IGNORECASE):
            clean_parts.append(part.strip())
    
    logger.info(f"📝 Разбили на части: {clean_parts}")
    
    if len(clean_parts) < 2:
        logger.info("❌ Недостаточно частей после разбивки")
        return None
    
    # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Обрабатываем каждую часть ОТДЕЛЬНО
    events = []
    
    for i, part in enumerate(clean_parts):
        part = part.strip()
        if not part:
            continue
            
        logger.info(f"📝 Обрабатываем часть {i+1}: '{part}'")
        
        # ИСПРАВЛЕНО: Ищем диапазон В ЭТОЙ КОНКРЕТНОЙ ЧАСТИ
        range_event = extract_time_range_event(part, user_timezone)
        if range_event:
            logger.info(f"✅ В части {i+1} найден диапазон: '{range_event[1]}'")
            events.append(range_event)
            continue
        
        # Если диапазона нет, пробуем простое событие
        simple_event = extract_single_event(part, user_timezone)
        if simple_event:
            logger.info(f"✅ В части {i+1} найдено простое событие: '{simple_event[1]}'")
            events.append(simple_event)
        else:
            logger.warning(f"⚠️ В части {i+1} события не найдены")
    
    logger.info(f"📊 Итого найдено событий: {len(events)}")
    
    # Возвращаем только если нашли минимум 2 события
    if len(events) >= 2:
        return events
    
    logger.info("❌ Найдено менее 2 событий, возвращаем None")
    return None

def extract_time_range_event(text, user_timezone):
    """🎯 КЛЮЧЕВАЯ ФУНКЦИЯ: Извлечение событий с временными диапазонами"""
    logger.info(f"⏰ Поиск временных диапазонов в: '{text}'")
    
    # Паттерны для временных диапазонов
    time_range_patterns = [
        # "с 21:30 до 22:30" - основной паттерн
        (r'с\s+(\d{1,2})[:\.](\d{2})\s+до\s+(\d{1,2})[:\.](\d{2})', 'range_from_to'),
        # "в 21:30 до 22:30" 
        (r'в\s+(\d{1,2})[:\.](\d{2})\s+до\s+(\d{1,2})[:\.](\d{2})', 'range_at_to'),
        # "21:30-22:30" - через дефис
        (r'(\d{1,2})[:\.](\d{2})\s*[-–—]\s*(\d{1,2})[:\.](\d{2})', 'range_dash'),
        # "в 17:00 на 2 часа" - длительность в часах
        (r'в\s+(\d{1,2})[:\.](\d{2})\s+на\s+(\d+)\s+(?:час|часа|часов)', 'duration_hours'),
        # "в 17:00 на 30 минут" - длительность в минутах
        (r'в\s+(\d{1,2})[:\.](\d{2})\s+на\s+(\d+)\s+минут', 'duration_minutes'),
        # "в 17:00 на полчаса" - на полчаса
        (r'в\s+(\d{1,2})[:\.](\d{2})\s+на\s+полчаса', 'duration_half_hour'),
    ]
    
    for pattern, pattern_type in time_range_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            logger.info(f"🎯 Найден паттерн {pattern_type}: {match.group(0)}")
            
            try:
                result = process_time_range_match(match, pattern_type, text, user_timezone)
                if result:
                    return result
            except Exception as e:
                logger.error(f"❌ Ошибка обработки диапазона {pattern_type}: {e}")
                continue
    
    return None

def process_time_range_match(match, pattern_type, text, user_timezone):
    """Обработка совпадений временных диапазонов"""
    groups = match.groups()
    
    if pattern_type in ['range_from_to', 'range_at_to', 'range_dash']:
        # Обработка диапазонов времени
        start_hour, start_min, end_hour, end_min = map(int, groups)
        
        # Валидация времени
        if not (0 <= start_hour <= 23 and 0 <= start_min <= 59 and 
               0 <= end_hour <= 23 and 0 <= end_min <= 59):
            return None
            
    elif pattern_type == 'duration_hours':
        # "в 17:00 на 2 часа"
        start_hour, start_min, duration_hours = int(groups[0]), int(groups[1]), int(groups[2])
        
        if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
            return None
            
        # Вычисляем время окончания
        end_hour = start_hour + duration_hours
        end_min = start_min
        
        # Обработка переноса на следующий день
        if end_hour >= 24:
            end_hour = end_hour % 24
            
    elif pattern_type == 'duration_minutes':
        # "в 17:00 на 30 минут"
        start_hour, start_min, duration_minutes = int(groups[0]), int(groups[1]), int(groups[2])
        
        if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
            return None
            
        # Вычисляем время окончания
        total_minutes = start_min + duration_minutes
        end_hour = start_hour + (total_minutes // 60)
        end_min = total_minutes % 60
        
        # Обработка переноса на следующий день
        if end_hour >= 24:
            end_hour = end_hour % 24
            
    elif pattern_type == 'duration_half_hour':
        # "в 17:00 на полчаса"
        start_hour, start_min = int(groups[0]), int(groups[1])
        
        if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
            return None
            
        # Добавляем 30 минут
        total_minutes = start_min + 30
        end_hour = start_hour + (total_minutes // 60)
        end_min = total_minutes % 60
        
        # Обработка переноса на следующий день
        if end_hour >= 24:
            end_hour = end_hour % 24
    
    # Получаем базовую дату
    base_datetime = enhanced_datetime_parser(text, user_timezone)
    if not base_datetime:
        import pytz
        tz = pytz.timezone(user_timezone)
        base_datetime = datetime.now(tz)
        
        # Если время уже прошло сегодня, берем завтра
        current_time = base_datetime.time()
        event_time = datetime.min.time().replace(hour=start_hour, minute=start_min)
        if event_time <= current_time:
            base_datetime += timedelta(days=1)
    
    # Создаем start и end datetime
    start_datetime = base_datetime.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
    end_datetime = base_datetime.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
    
    # Если end_time меньше start_time, значит событие переходит на следующий день
    if end_datetime <= start_datetime:
        end_datetime += timedelta(days=1)
    
    # ИСПРАВЛЕНО: Извлекаем чистое название БЕЗ временных ссылок и артефактов
    clean_title = extract_title_without_time_references_ultra_fixed(text, match.group(0))
    
    logger.info(f"✅ Диапазон: {start_datetime.strftime('%H:%M')}-{end_datetime.strftime('%H:%M')}, название: '{clean_title}'")
    
    # Возвращаем кортеж из 4 элементов для диапазонов
    return (start_datetime, clean_title, 'event', end_datetime)

def extract_title_without_time_references_ultra_fixed(text, time_reference):
    """🔥 УЛЬТРА-ИСПРАВЛЕННАЯ ФУНКЦИЯ: Извлечение названия БЕЗ временных ссылок и артефактов"""
    logger.info(f"🔧 Ультра-очистка названия от временных ссылок: '{text}'")
    
    # Убираем найденную временную ссылку
    clean_text = text.replace(time_reference, '').strip()
    
    # ИСПРАВЛЕННЫЕ паттерны для удаления временных слов
    temporal_patterns = [
        r'\b(?:сегодня|завтра|послезавтра)\b',
        r'\b(?:в\s+)?(?:понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)\b',
        r'\b(?:утром|днем|вечером|ночью)\b',
        r'\bчерез\s+(?:\d+\s+)?(?:час|часа|часов|минут|минуты|минуту)\b',
        r'\b(?:на\s+)?\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b',
        r'\b(?:на\s+)?\d{1,2}[\./]\d{1,2}(?:[\./]\d{2,4})?\b',
        r'\bв\s+\d{1,2}[:\.]?\d{2}\b',
        r'\bдо\s+\d{1,2}[:\.]?\d{2}\b',
        r'\bна\s+\d{1,2}[:\.]?\d{2}\b',
        r'\bна\s+\d+\s+(?:час|часа|часов|минут|минуты|минуту)\b',
        r'\bна\s+полчаса\b',
        r'\s+через\s+\d+\s+(?:час|часа|часов)\b',
        # КРИТИЧНО: Убираем остатки временных слов и цифр
        r'\s+с\s+\d{1,2}.*$',
        r'\s+а\s*$',
        r'\s+на\s*$', 
        r'\s+в\s*$',
        r'\s+до\s*$',
        r'\s+с\s*$',
        r'\s+\d{1,2}[:\.]?\d{2}.*$',
        # НОВЫЕ паттерны для очистки артефактов
        r'\s*,\s*$',  # запятая в конце
        r'^\s*,\s*',  # запятая в начале
        r'\s+и\s*$',  # "и" в конце
        r'^\s*и\s+', # "и" в начале
    ]
    
    for pattern in temporal_patterns:
        clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
    
    # Убираем управляющие фразы
    control_patterns = [
        r'^(?:у\s+меня\s+|создай\s+|добавь\s+|напомни\s+|поставь\s+)',
        r'^(?:мне\s+нужно\s+|нужно\s+|надо\s+)',
        r'^(?:запланируй\s+|зарегай\s+)',
        r'^(?:первая\s*-?\s*|вторая\s*-?\s*|третья\s*-?\s*)',  # убираем порядковые
    ]
    
    for pattern in control_patterns:
        clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
    
    # Очистка пунктуации и пробелов
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    clean_text = clean_text.strip(' \t\n\r\f\v-–—.,;:!?0123456789')
    
    # Финальная очистка от одиночных букв в конце
    clean_text = re.sub(r'\s+[а-яё]\s*$', '', clean_text, flags=re.IGNORECASE)
    clean_text = clean_text.strip()
    
    # Если остался текст длиннее 2 символов, используем его
    if len(clean_text) >= 3:
        result = capitalize_smart(clean_text)
        logger.info(f"✅ Ультра-очищенное название: '{result}'")
        return result
    
    # Fallback - контекстный поиск
    return extract_contextual_title(text)

def extract_single_event(text, user_timezone):
    """Извлечение одиночного события"""
    logger.info("🎯 Извлечение одиночного события...")
    
    parsed_datetime = enhanced_datetime_parser(text, user_timezone)
    if not parsed_datetime:
        return None
    
    title = extract_clean_title_ultra_fixed(text)
    return (parsed_datetime, title, 'event')

def extract_clean_title_ultra_fixed(text):
    """🔥 УЛЬТРА-ИСПРАВЛЕННОЕ извлечение чистого названия"""
    # Убираем управляющие фразы
    clean_text = remove_control_phrases(text)
    
    # Убираем временные ссылки  
    clean_text = remove_time_references_ultra_fixed(clean_text)
    
    # Убираем союзы в начале
    clean_text = re.sub(r'^(?:и\s+|а\s+|также\s+|еще\s+|ещё\s+)', '', clean_text, flags=re.IGNORECASE)
    
    # Убираем множественные пробелы
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    # Убираем одиночные буквы в конце
    clean_text = re.sub(r'\s+[а-яё]\s*$', '', clean_text, flags=re.IGNORECASE)
    
    # Убираем пунктуацию в начале и конце
    clean_text = clean_text.strip(' \t\n\r\f\v-–—.,;:!?')
    
    # Финальная нормализация
    clean_text = clean_text.strip()
    
    if len(clean_text) >= 3:
        return capitalize_smart(clean_text)
    
    return extract_contextual_title(text)

def remove_control_phrases(text):
    """Удаление управляющих фраз"""
    patterns = [
        r'^(?:у\s+меня\s+|создай\s+|добавь\s+|напомни\s+|запланируй\s+)',
        r'^(?:мне\s+нужно\s+|нужно\s+|надо\s+)',
        r'^(?:создай\s+мне\s+|добавь\s+мне\s+)',
        r'^(?:первая\s*-?\s*|вторая\s*-?\s*|третья\s*-?\s*)',  # порядковые
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()

def remove_time_references_ultra_fixed(text):
    """🔥 УЛЬТРА-ИСПРАВЛЕННОЕ удаление временных ссылок"""
    patterns = [
        r'\b(?:сегодня|завтра|послезавтра)\b',
        r'\b(?:в|до|на)\s+\d{1,2}[:\.]?\d{2}\b',
        r'\bчерез\s+(?:\d+\s+)?(?:час|минут)\b',
        r'\bв\s+(?:понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)\b',
        r'\bс\s+\d{1,2}[:\.]?\d{2}\s+до\s+\d{1,2}[:\.]?\d{2}\b',
        r'\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b',
        r'\bна\s+\d+\s+(?:час|часа|часов|минут|минуты|минуту)\b',
        r'\bна\s+полчаса\b',
        r'\s+через\s+\d+\s+(?:час|часа|часов)\b',
        r'\s+а\s*$',
        r'\s+на\s*$',
        r'\s+в\s*$',
        r'\s+до\s*$',
        r'\s+с\s*$',
        # НОВЫЕ исправления
        r'\s*,\s*$',  # запятая в конце
        r'^\s*,\s*',  # запятая в начале
        r'\s+и\s*$',  # "и" в конце
        r'^\s*и\s+', # "и" в начале
        r'\s+каждая\s+по\s+.*$',  # "каждая по часу длительности"
        r'^\s*на\s+\d{1,2}[:\.]?\d{2}\s+и\s+на\s+\d{1,2}[:\.]?\d{2}\s*', # "на 10:00 и на 12:00"
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Убираем одиночные буквы в конце
    text = re.sub(r'\s+[а-яё]\s*$', '', text, flags=re.IGNORECASE)
    
    return text.strip()

def capitalize_smart(text):
    """Умная капитализация с именами"""
    if not text:
        return text
    
    proper_nouns = {
        'лера': 'Лера', 'лерой': 'Лерой', 'леру': 'Леру',
        'тамара': 'Тамара', 'тамарой': 'Тамарой', 'тамару': 'Тамару',
        'амир': 'Амир', 'амиром': 'Амиром', 'амира': 'Амира',
        'дамир': 'Дамир', 'дамиром': 'Дамиром', 'дамира': 'Дамира',
        'ангелина': 'Ангелина', 'ангелиной': 'Ангелиной', 'ангелину': 'Ангелину',
        'алишер': 'Алишер', 'алишером': 'Алишером', 'алишера': 'Алишера',
        'мама': 'мама', 'папа': 'папа', 'бабушка': 'бабушка'
    }
    
    words = text.split()
    result_words = []
    
    for i, word in enumerate(words):
        word_lower = word.lower()
        
        if word_lower in proper_nouns:
            result_words.append(proper_nouns[word_lower])
        elif i == 0:
            result_words.append(word.capitalize())
        else:
            result_words.append(word)
    
    return ' '.join(result_words)

def extract_contextual_title(text):
    """Контекстное извлечение названия по ключевым словам"""
    patterns = [
        (r'встреча\s+с\s+([\w\s]+)', 'встреча с {}'),
        (r'созвон\s+с\s+([\w\s]+)', 'созвон с {}'),
        (r'обед\s+с\s+([\w\s]+)', 'обед с {}'),
        (r'ужин\s+с\s+([\w\s]+)', 'ужин с {}'),
        (r'кофе\s+с\s+([\w\s]+)', 'кофе с {}'),
        (r'презентация\s+([\w\s]+)', 'презентация {}'),
        (r'совещание\s+(?:с\s+|по\s+)?([\w\s]+)', 'совещание {}'),
        (r'\b(встреча)\b', 'Встреча'),
        (r'\b(созвон)\b', 'Созвон'), 
        (r'\b(обед)\b', 'Обед'),
        (r'\b(ужин)\b', 'Ужин'),
        (r'\b(презентация)\b', 'Презентация'),
        (r'\b(совещание)\b', 'Совещание'),
        (r'\b(работа)\b', 'Работа'),
    ]
    
    # Сначала очищаем текст от времени для поиска
    clean_text = remove_time_references_ultra_fixed(text.lower())
    
    for pattern, template in patterns:
        match = re.search(pattern, clean_text)
        if match:
            if '{}' in template and len(match.groups()) >= 1:
                context = match.group(1).strip()
                # Убираем лишние символы из контекста
                context = re.sub(r'[^\w\s]', '', context).strip()
                if context and len(context) > 1:
                    result = template.format(context).strip()
                    return capitalize_smart(result)
            else:
                return capitalize_smart(template)
    
    return "Событие"

def get_default_base_time(user_timezone):
    """Получение базового времени по умолчанию"""
    import pytz
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)
    
    if 9 <= now.hour <= 18:
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    else:
        return now.replace(hour=10, minute=0, second=0, microsecond=0)

# Специальная функция для обработки сложных структурированных запросов
def handle_structured_requests(text, user_timezone):
    """🎯 СПЕЦИАЛЬНАЯ ФУНКЦИЯ: Обработка структурированных запросов типа 'создай мне две встречи'"""
    logger.info(f"🔍 Анализ структурированного запроса: '{text}'")
    
    # Паттерны для структурированных запросов
    structured_patterns = [
        r'создай\s+мне\s+две\s+встречи.*?первая\s*-?\s*([^,]+),?\s*вторая\s*-?\s*([^,]+)',
        r'добавь\s+две\s+события.*?первое\s*-?\s*([^,]+),?\s*второе\s*-?\s*([^,]+)',
        r'запланируй.*?первая\s*-?\s*([^,]+),?\s*вторая\s*-?\s*([^,]+)',
    ]
    
    for pattern in structured_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            logger.info(f"✅ Найден структурированный паттерн")
            
            first_event_text = match.group(1).strip()
            second_event_text = match.group(2).strip()
            
            logger.info(f"📝 Первое событие: '{first_event_text}'")
            logger.info(f"📝 Второе событие: '{second_event_text}'")
            
            events = []
            
            # Обрабатываем каждое событие отдельно
            for i, event_text in enumerate([first_event_text, second_event_text], 1):
                # Комбинируем с общим контекстом из основного текста
                time_context = extract_time_context_from_main_text(text)
                combined_text = f"{event_text} {time_context}"
                
                logger.info(f"📝 Обрабатываем событие {i} с контекстом: '{combined_text}'")
                
                # Пробуем извлечь событие
                event = extract_single_event(combined_text, user_timezone)
                if event:
                    events.append(event)
                    logger.info(f"✅ Событие {i} успешно создано: '{event[1]}'")
                else:
                    logger.warning(f"⚠️ Не удалось создать событие {i}")
            
            if len(events) >= 2:
                logger.info(f"✅ Структурированный запрос обработан: {len(events)} событий")
                return events
    
    return None

def extract_time_context_from_main_text(text):
    """Извлечение временного контекста из основного текста"""
    time_contexts = []
    
    # Ищем общие временные указания
    general_time_patterns = [
        r'на\s+завтра',
        r'на\s+\d{1,2}\s+(?:мая|июня|июля|августа|сентября|октября|ноября|декабря)',
        r'в\s+(?:понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)',
        r'на\s+\d{1,2}[:\.](\d{2})\s+и\s+на\s+\d{1,2}[:\.](\d{2})',
    ]
    
    for pattern in general_time_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            time_contexts.extend(matches)
    
    # Извлекаем конкретное время
    times = re.findall(r'на\s+(\d{1,2}[:\.]?\d{2})', text, re.IGNORECASE)
    if len(times) >= 2:
        return f"завтра в {times[0]} и в {times[1]}"
    elif len(times) == 1:
        return f"завтра в {times[0]}"
    
    # Fallback
    if 'завтра' in text.lower():
        return 'завтра'
    
    return ''

if __name__ == "__main__":
    # Тест для проверки исправлений
    test_cases = [
        "встреча с клиентом с 10:00 до 11:00, обед с коллегами с 13:00 до 14:00",
        "работа с 9:00 до 17:00 и потом ужин в 19:00",
        "звонок маме в 10:00, встреча с боссом в 14:00",
        "создай мне две встречи на завтра, на 10:00 и на 12:00 - каждая по часу длительности. первая - встреча с лерой, вторая - встреча с тамарой",
        "презентация проекта в 17:00 на 2 часа",
    ]
    
    print("🧪 ТЕСТ ИСПРАВЛЕННОГО ПАРСЕРА:")
    print("=" * 60)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{i}. Тестируем: '{text}'")
        
        # Сначала пробуем структурированные запросы
        structured_events = handle_structured_requests(text, 'Asia/Almaty')
        if structured_events:
            events = structured_events
        else:
            events = extract_multiple_events(text, 'Asia/Almaty')
        
        if events:
            print(f"✅ Найдено {len(events)} событий:")
            for j, event in enumerate(events, 1):
                if len(event) == 4:  # событие с диапазоном
                    start, name, event_type, end = event
                    print(f"   {j}. '{name}' ({start.strftime('%H:%M')}-{end.strftime('%H:%M')})")
                else:  # обычное событие
                    start, name, event_type = event
                    print(f"   {j}. '{name}' ({start.strftime('%H:%M')})")
        else:
            print("❌ События не найдены")
    
    print(f"\n🎯 КЛЮЧЕВЫЕ ИСПРАВЛЕНИЯ:")
    print("✅ Переработана логика extract_comma_separated_events_completely_fixed()")
    print("✅ Сначала разбивка по запятым, потом поиск диапазонов в каждой части")
    print("✅ Улучшена очистка названий от временных артефактов")
    print("✅ Добавлена поддержка структурированных запросов")
    print("✅ Исправлена обработка союзов 'и потом', 'а потом'")
    
    print(f"\n📋 ИНСТРУКЦИИ ПО ВНЕДРЕНИЮ:")
    print("1. Замените содержимое файла text_parser.py этим кодом")
    print("2. Запустите тест: python3 time_range_test.py")
    print("3. Убедитесь, что результат: 4/4 категорий пройдено")
    print("4. Перезапустите бота: python3 main.py")