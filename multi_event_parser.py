"""
🎯 СПЕЦИАЛЬНЫЙ ПАРСЕР для множественных событий Vetra AI
Решает проблему объединения событий в одно
"""

import re
from datetime import datetime, timedelta
from datetime_utils import enhanced_datetime_parser, validate_datetime
import logging

logger = logging.getLogger(__name__)

def parse_structured_events(text, user_timezone='Asia/Almaty'):
    """
    🔥 НОВАЯ ФУНКЦИЯ: Парсинг структурированных событий
    Специально для случаев типа:
    "3 мероприятия
     Презентация проекта – 3 июня в 12:00
     Обед с клиентами – 31 мая в 14:30
     Встреча с командой – 5 июня в 9:00"
    """
    logger.info(f"🎯 Парсинг структурированных событий: '{text}'")
    
    # Убираем лишние пробелы и переносы
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Ищем паттерны множественных событий
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
                clean_title = clean_event_title(title_part)
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
                clean_title = extract_title_from_line(line)
                if clean_title:
                    events.append((parsed_datetime, clean_title, 'event'))
                    logger.info(f"✅ Из строки добавлено: '{clean_title}' в {parsed_datetime}")
    
    # МЕТОД 3: Поиск временных меток и разбивка по ним
    if not events:
        time_markers = list(re.finditer(r'\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+в\s+\d{1,2}:\d{2}', text, re.IGNORECASE))
        
        if len(time_markers) >= 2:
            logger.info(f"✅ Найдено {len(time_markers)} временных меток")
            
            for i, marker in enumerate(time_markers):
                # Определяем границы события
                start_pos = time_markers[i-1].end() if i > 0 else 0
                end_pos = marker.end()
                
                event_text = text[start_pos:end_pos].strip()
                
                # Очищаем текст
                if event_text.startswith('мероприятия') or event_text.startswith('мероприятий'):
                    continue
                    
                parsed_datetime = enhanced_datetime_parser(event_text, user_timezone)
                if parsed_datetime:
                    clean_title = extract_title_from_text_chunk(event_text)
                    if clean_title:
                        events.append((parsed_datetime, clean_title, 'event'))
                        logger.info(f"✅ По временной метке: '{clean_title}' в {parsed_datetime}")
    
    logger.info(f"📊 Итого найдено структурированных событий: {len(events)}")
    return events if events else None

def clean_event_title(title):
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

def extract_title_from_line(line):
    """Извлечение названия из строки"""
    # Убираем дату/время
    line = re.sub(r'\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+в\s+\d{1,2}:\d{2}', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\d{1,2}\.\d{1,2}\s+в\s+\d{1,2}:\d{2}', '', line)
    line = re.sub(r'в\s+\d{1,2}:\d{2}', '', line)
    
    # Убираем тире и лишние символы
    line = re.sub(r'^[–\-\s]+|[–\-\s]+$', '', line)
    line = line.strip()
    
    return clean_event_title(line)

def extract_title_from_text_chunk(text):
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
                return clean_event_title(match.group(1))
    
    # Fallback - первые слова
    words = text.split()[:3]
    return clean_event_title(' '.join(words)) if words else None

def enhanced_extract_multiple_events(text, user_timezone='Asia/Almaty'):
    """
    🔥 УЛУЧШЕННАЯ главная функция извлечения событий
    Сначала пытается структурированный парсинг, потом обычный
    """
    logger.info(f"🔍 Улучшенный анализ текста: '{text}'")
    
    # ПРИОРИТЕТ 1: Структурированные события
    structured_events = parse_structured_events(text, user_timezone)
    if structured_events and len(structured_events) >= 2:
        logger.info(f"✅ Найдено {len(structured_events)} структурированных событий")
        return structured_events
    
    # ПРИОРИТЕТ 2: Обычная логика (уже существующая)
    try:
        from text_parser import extract_multiple_events
        regular_events = extract_multiple_events(text, user_timezone)
        if regular_events:
            logger.info(f"✅ Найдено {len(regular_events)} обычных событий")
            return regular_events
    except:
        pass
    
    # ПРИОРИТЕТ 3: Если ничего не нашли, возвращаем структурированные (даже если 1)
    if structured_events:
        logger.info(f"✅ Возвращаем {len(structured_events)} найденных событий")
        return structured_events
    
    logger.warning("❌ События не найдены")
    return []

def test_structured_parsing():
    """Тест структурированного парсинга"""
    test_cases = [
        "запланируй мне два мероприятия Презентация проекта - 3 июня в 12:00 Встреча с командой - 5 июня в 9:00",
        "3 мероприятия Презентация проекта – 3 июня в 12:00 Обед с клиентами – 31 мая в 14:30 Встреча с командой – 5 июня в 9:00",
        "Презентация проекта - 3 июня в 12:00\nВстреча с командой - 5 июня в 9:00",
        "создай встречу с клиентом – 15 мая в 10:00 и обед с партнерами – 16 мая в 13:00"
    ]
    
    print("🎯 ТЕСТ СТРУКТУРИРОВАННОГО ПАРСИНГА")
    print("=" * 50)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{i}. Тест: '{text}'")
        events = parse_structured_events(text)
        
        if events:
            print(f"✅ Найдено {len(events)} событий:")
            for j, (dt, title, event_type) in enumerate(events, 1):
                print(f"   {j}. '{title}' - {dt.strftime('%d.%m в %H:%M')}")
        else:
            print("❌ События не найдены")

if __name__ == "__main__":
    test_structured_parsing()
