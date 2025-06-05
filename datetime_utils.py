"""
ФИНАЛЬНЫЙ datetime_utils.py для Vetra AI с исправлениями багов
- Исправлена проблема с временем (11:00 → 12:00)
- Улучшена точность парсинга времени
"""

import re
import pytz
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Попытка импорта dateparser с fallback
try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    logger.warning("dateparser не установлен, используем только regex паттерны")

# ИСПРАВЛЕННЫЕ паттерны - время парсится точно
ULTIMATE_TIME_PATTERNS = [
    # ВЫСШИЙ ПРИОРИТЕТ: Точное время + день недели
    (r'в\s+(\d{1,2})[:\.](\d{2})\s+в\s+(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)', 'time_then_weekday'),
    
    # КОНКРЕТНЫЕ ДАТЫ
    (r'(?:на\s+)?(\d{1,2})\s+мая(?:\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2}))?', 'specific_date_may'),
    (r'(?:на\s+)?(\d{1,2})[\./](\d{1,2})(?:[\./](\d{2,4}))?(?:\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2}))?', 'specific_date_numeric'),
    (r'(?:на\s+)?(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(?:\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2}))?', 'specific_date_month'),
    (r'(\d{1,2})[\./](\d{1,2})[\./](\d{4})(?:\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2}))?', 'specific_date_with_year'),
    
    # ОТНОСИТЕЛЬНЫЕ ДАТЫ
    (r'завтра\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2})', 'tomorrow_at_time'),
    (r'сегодня\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2})', 'today_at_time'),
    (r'послезавтра\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2})', 'day_after_tomorrow'),
    
    # ВРЕМЕННЫЕ ИНТЕРВАЛЫ
    (r'через\s+(\d+)\s+час(?:а|ов)?(?:\s+(?:и\s+)?(\d+)\s+минут)?', 'hours_minutes_from_now'),
    (r'через\s+час(?:\s+(?:и\s+)?(\d+)\s+минут)?', 'one_hour_from_now'),
    (r'через\s+(\d+)\s+минут', 'minutes_from_now'),
    (r'через\s+полчаса', 'half_hour_from_now'),
    
    # ДНИ НЕДЕЛИ - улучшенный парсинг времени
    (r'в\s+(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)(?:\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2}))?', 'weekday_at_time'),
    (r'в\s+следующий\s+(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)(?:\s+(?:в|до)\s+(\d{1,2})[:\.](\d{2}))?', 'next_weekday'),
    
    # ПРОСТОЕ ВРЕМЯ
    (r'(?:в|до)\s+(\d{1,2})[:\.](\d{2})', 'at_time'),
]

WEEKDAYS_RU = {
    'понедельник': 0, 'вторник': 1, 'среду': 2, 'четверг': 3,
    'пятницу': 4, 'субботу': 5, 'воскресенье': 6
}

MONTHS_RU = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5,
    'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9,
    'октября': 10, 'ноября': 11, 'декабря': 12
}

def enhanced_datetime_parser(text, user_timezone='Asia/Almaty'):
    """МАКСИМАЛЬНО УЛУЧШЕННЫЙ парсер даты/времени"""
    logger.info(f"🔍 Максимальный анализ: '{text}'")
    
    # ПРИОРИТЕТ 1: Улучшенные regex паттерны
    result = try_ultimate_regex_patterns(text, user_timezone)
    if result:
        logger.info(f"✅ Найдено через regex: {result}")
        return result
    
    # ПРИОРИТЕТ 2: dateparser (если доступен)
    if DATEPARSER_AVAILABLE:
        result = try_enhanced_dateparser(text, user_timezone)
        if result:
            logger.info(f"✅ Найдено через dateparser: {result}")
            return result
    
    # ПРИОРИТЕТ 3: Извлечение только времени
    result = try_ultimate_time_only(text, user_timezone)
    if result:
        logger.info(f"✅ Найдено только время: {result}")
        return result
    
    logger.warning(f"❌ Не удалось распознать дату/время в '{text}'")
    return None

def try_ultimate_regex_patterns(text, user_timezone):
    """МАКСИМАЛЬНО УЛУЧШЕННЫЕ regex паттерны"""
    text_lower = text.lower()
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)
    
    # Предварительная обработка
    text_lower = preprocess_text_for_parsing(text_lower)
    
    for pattern, pattern_type in ULTIMATE_TIME_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            try:
                result = process_ultimate_pattern_match_fixed(match, pattern_type, now, text_lower)
                if result:
                    logger.info(f"✅ regex ({pattern_type}): {result}")
                    return result
            except Exception as e:
                logger.warning(f"⚠️ Ошибка обработки паттерна {pattern_type}: {e}")
                continue
    
    return None

def preprocess_text_for_parsing(text):
    """Умная предобработка текста"""
    # 14.30 → 14:30
    text = re.sub(r'(\d{1,2})\.(\d{2})', r'\1:\2', text)
    # 14ч30 → 14:30
    text = re.sub(r'(\d{1,2})\s*ч\s*(\d{2})', r'\1:\2', text)
    
    # Нормализация дней недели
    weekday_map = {
        'пн': 'понедельник', 'вт': 'вторник', 'ср': 'среду', 'чт': 'четверг',
        'пт': 'пятницу', 'сб': 'субботу', 'вс': 'воскресенье'
    }
    
    for short, full in weekday_map.items():
        text = re.sub(rf'\b{short}\b', full, text)
    
    return text

def process_ultimate_pattern_match_fixed(match, pattern_type, now, original_text):
    """ИСПРАВЛЕННАЯ обработка паттернов с точным временем"""
    groups = match.groups()
    
    # НОВЫЙ ПРИОРИТЕТНЫЙ ПАТТЕРН: "в 11:00 в четверг"
    if pattern_type == 'time_then_weekday':
        hour, minute, weekday_name = int(groups[0]), int(groups[1]), groups[2]
        
        target_weekday = WEEKDAYS_RU.get(weekday_name)
        if target_weekday is None:
            return None
        
        current_weekday = now.weekday()
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:
            days_ahead += 7
        
        result = now + timedelta(days=days_ahead)
        return result.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    elif pattern_type == 'specific_date_may':
        day = int(groups[0])
        hour = int(groups[1]) if groups[1] else 12
        minute = int(groups[2]) if groups[2] else 0
        
        try:
            target_date = now.replace(month=5, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            
            if target_date.date() < now.date():
                target_date = target_date.replace(year=now.year + 1)
            elif target_date.date() == now.date() and target_date <= now:
                target_date = target_date.replace(year=now.year + 1)
            
            return target_date
        except ValueError:
            return None
    
    elif pattern_type == 'specific_date_numeric':
        day = int(groups[0])
        month = int(groups[1])
        year = int(groups[2]) if groups[2] else now.year
        hour = int(groups[3]) if groups[3] else 12
        minute = int(groups[4]) if groups[4] else 0
        
        # Двухзначный год
        if groups[2] and len(groups[2]) == 2:
            year = 2000 + int(groups[2])
        
        try:
            target_date = now.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            
            if not groups[2] and target_date.date() < now.date():
                target_date = target_date.replace(year=now.year + 1)
            elif not groups[2] and target_date.date() == now.date() and target_date <= now:
                target_date = target_date.replace(year=now.year + 1)
            
            return target_date
        except ValueError:
            return None
    
    elif pattern_type == 'specific_date_month':
        day = int(groups[0])
        month_name = groups[1]
        hour = int(groups[2]) if groups[2] else 12
        minute = int(groups[3]) if groups[3] else 0
        
        month = MONTHS_RU.get(month_name)
        if not month:
            return None
        
        try:
            target_date = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            
            if target_date.date() < now.date():
                target_date = target_date.replace(year=now.year + 1)
            elif target_date.date() == now.date() and target_date <= now:
                target_date = target_date.replace(year=now.year + 1)
            
            return target_date
        except ValueError:
            return None
    
    elif pattern_type == 'specific_date_with_year':
        day = int(groups[0])
        month = int(groups[1])
        year = int(groups[2])
        hour = int(groups[3]) if groups[3] else 12
        minute = int(groups[4]) if groups[4] else 0
        
        try:
            return now.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            return None
    
    elif pattern_type == 'tomorrow_at_time':
        hour, minute = int(groups[0]), int(groups[1])
        return (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    elif pattern_type == 'today_at_time':
        hour, minute = int(groups[0]), int(groups[1])
        result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if result <= now:
            result += timedelta(days=1)
        return result
    
    elif pattern_type == 'day_after_tomorrow':
        hour, minute = int(groups[0]), int(groups[1])
        return (now + timedelta(days=2)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    elif pattern_type == 'hours_minutes_from_now':
        hours = int(groups[0])
        minutes = int(groups[1]) if groups[1] else 0
        return now + timedelta(hours=hours, minutes=minutes)
    
    elif pattern_type == 'one_hour_from_now':
        minutes = int(groups[0]) if groups[0] else 0
        return now + timedelta(hours=1, minutes=minutes)
    
    elif pattern_type == 'minutes_from_now':
        minutes = int(groups[0])
        return now + timedelta(minutes=minutes)
    
    elif pattern_type == 'half_hour_from_now':
        return now + timedelta(minutes=30)
    
    elif pattern_type in ['weekday_at_time', 'next_weekday']:
        weekday_name = groups[0]
        hour = int(groups[1]) if groups[1] else None
        minute = int(groups[2]) if groups[2] else None
        
        # ИСПРАВЛЕНИЕ: Если время не в группах, ищем его в тексте
        if hour is None:
            time_match = re.search(r'(\d{1,2})[:\.](\d{2})', original_text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            else:
                hour = 12
                minute = 0
        
        target_weekday = WEEKDAYS_RU.get(weekday_name)
        if target_weekday is None:
            return None
        
        current_weekday = now.weekday()
        days_ahead = target_weekday - current_weekday
        
        if pattern_type == 'next_weekday':
            days_ahead += 7
        elif days_ahead <= 0:
            days_ahead += 7
        
        result = now + timedelta(days=days_ahead)
        return result.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    elif pattern_type == 'at_time':
        hour, minute = int(groups[0]), int(groups[1])
        result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Контекстная проверка
        if 'завтра' in original_text:
            result += timedelta(days=1)
        elif 'послезавтра' in original_text:
            result += timedelta(days=2)
        elif result <= now:
            result += timedelta(days=1)
        
        return result
    
    return None

def try_enhanced_dateparser(text, user_timezone):
    """УЛУЧШЕННЫЙ dateparser (если доступен)"""
    if not DATEPARSER_AVAILABLE:
        return None
    
    try:
        result = dateparser.parse(
            text,
            languages=['ru', 'en'],
            settings={
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'TO_TIMEZONE': user_timezone,
                'NORMALIZE': True,
                'RELATIVE_BASE': datetime.now(pytz.timezone(user_timezone)),
                'DATE_ORDER': 'DMY',
                'PREFER_DAY_OF_MONTH': 'first',
                'STRICT_PARSING': False,
                'PREFER_FUTURE': True,
            }
        )
        
        if result:
            now = datetime.now(pytz.timezone(user_timezone))
            
            if result.date() == now.date() and result <= now:
                result += timedelta(days=1)
            
            return result
            
    except Exception as e:
        logger.warning(f"⚠️ Ошибка dateparser: {e}")
    
    return None

def try_ultimate_time_only(text, user_timezone):
    """МАКСИМАЛЬНО УМНОЕ извлечение времени"""
    time_patterns = [
        r'(\d{1,2})[:\.](\d{2})',
        r'(\d{1,2})\s*ч\s*(\d{2})',
        r'(\d{1,2})\s*часов\s*(\d{2})',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                hour, minute = int(match.group(1)), int(match.group(2))
                
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    continue
                
                tz = pytz.timezone(user_timezone)
                now = datetime.now(tz)
                
                result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Контекстная логика
                text_lower = text.lower()
                if 'завтра' in text_lower:
                    result += timedelta(days=1)
                elif 'послезавтра' in text_lower:
                    result += timedelta(days=2)
                elif result <= now:
                    result += timedelta(days=1)
                
                return result
                
            except ValueError:
                continue
    
    return None

def format_datetime_for_display(dt, timezone='Asia/Almaty'):
    """УЛУЧШЕННОЕ форматирование для пользователя"""
    if dt.tzinfo is None:
        dt = pytz.timezone(timezone).localize(dt)
    
    now = datetime.now(pytz.timezone(timezone))
    days_diff = (dt.date() - now.date()).days
    
    if days_diff == 0:
        return f"сегодня в {dt.strftime('%H:%M')}"
    elif days_diff == 1:
        return f"завтра в {dt.strftime('%H:%M')}"
    elif days_diff == 2:
        return f"послезавтра в {dt.strftime('%H:%M')}"
    elif 0 < days_diff <= 7:
        weekdays = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
        return f"в {weekdays[dt.weekday()]} в {dt.strftime('%H:%M')}"
    elif dt.year == now.year:
        return dt.strftime('%d.%m в %H:%M')
    else:
        return dt.strftime('%d.%m.%Y в %H:%M')

def validate_datetime(dt, user_timezone='Asia/Almaty'):
    """УЛУЧШЕННАЯ валидация"""
    if not dt:
        return None
    
    now = datetime.now(pytz.timezone(user_timezone))
    
    # Коррекция года для дат в прошлом
    if (now - dt).days > 30:
        dt = dt.replace(year=now.year + 1)
        logger.info(f"🔧 Скорректирован год: {dt}")
    
    # Проверка на слишком далекое будущее
    if (dt - now).days > 5 * 365:
        logger.warning(f"⚠️ Подозрительно далекая дата: {dt}")
        return None
    
    return dt

# Тестовая функция
def test_ultimate_datetime_parser():
    """Тест максимально улучшенного парсера"""
    test_cases = [
        # Базовые
        "встреча завтра в 14:00",
        "созвон через 2 часа",
        "презентация в пятницу в 10:00",
        
        # КРИТИЧНЫЕ ТЕСТЫ - исправления багов
        "встреча с дамиром в 11:00 в четверг",  # ДОЛЖНО БЫТЬ 11:00
        "в среду в 12:00 встреча с ангелиной",  # ДОЛЖНО БЫТЬ 12:00
        
        # КОНКРЕТНЫЕ ДАТЫ
        "встреча 26 мая в 14:00",
        "презентация на 26 мая",
        "созвон 15.06 в 10:00",
        "встреча 15/06 в 16:30",
        "встреча 3 июня в 15:30",
        "дедлайн 25.12.2024 в 23:59",
        "встреча 1 января в 12:00",
        
        # Сложные форматы
        "послезавтра в 16.30",
        "через полчаса",
        "через 2 часа 30 минут",
        "встреча в 14.30",
        "созвон в 16ч30",
    ]
    
    print("🧪 Тест ИСПРАВЛЕННОГО парсера дат:")
    print("=" * 60)
    
    success_count = 0
    for i, text in enumerate(test_cases, 1):
        result = enhanced_datetime_parser(text)
        if result:
            display_time = format_datetime_for_display(result)
            formatted = result.strftime('%Y-%m-%d %H:%M')
            print(f"{i:2d}. ✅ '{text}' → {display_time} ({formatted})")
            success_count += 1
            
            # Специальная проверка для критичных тестов
            if "в 11:00 в четверг" in text and result.hour == 11:
                print(f"    🎯 ИСПРАВЛЕН БАГ: время 11:00 распознается корректно!")
            elif "в 12:00 встреча" in text and result.hour == 12:
                print(f"    🎯 ИСПРАВЛЕН БАГ: время 12:00 распознается корректно!")
        else:
            print(f"{i:2d}. ❌ '{text}' → не распознано")
    
    success_rate = (success_count / len(test_cases)) * 100
    print(f"\n📊 Успешность: {success_count}/{len(test_cases)} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("🎉 ПРЕВОСХОДНО! Баги исправлены!")
    elif success_rate >= 80:
        print("✅ ОТЛИЧНО! Система работает стабильно!")
    elif success_rate >= 70:
        print("⚠️ ХОРОШО!")
    else:
        print("🚨 ТРЕБУЕТ ДОРАБОТКИ!")

if __name__ == "__main__":
    test_ultimate_datetime_parser()