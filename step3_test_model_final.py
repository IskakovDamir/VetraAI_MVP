#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ФИНАЛЬНЫЙ Шаг 3: Тестирование файн-тюнинговой модели Vetra AI
Этот скрипт тестирует готовую модель и показывает как её использовать
"""

import json
import os
from openai import OpenAI

def get_openai_client():
    """Создаем клиент OpenAI"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        api_key = input("🔑 Введите ваш OpenAI API ключ: ").strip()
        if not api_key:
            print("❌ API ключ обязателен!")
            return None
    
    try:
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        print(f"❌ Ошибка создания клиента: {e}")
        return None

def get_fine_tuned_model():
    """Получаем имя файн-тюнинговой модели"""
    
    # Пробуем из файла
    if os.path.exists("model_name.txt"):
        with open("model_name.txt", "r") as f:
            model_name = f.read().strip()
        if model_name:
            print(f"✅ Найдена модель из файла: {model_name}")
            return model_name
    
    # Пробуем из JSON файла
    if os.path.exists("training_job_info.json"):
        try:
            with open("training_job_info.json", "r") as f:
                job_info = json.load(f)
            if "fine_tuned_model" in job_info:
                model_name = job_info["fine_tuned_model"]
                print(f"✅ Найдена модель из JSON: {model_name}")
                return model_name
        except:
            pass
    
    # Запрашиваем у пользователя
    print("❌ Имя модели не найдено в файлах")
    print("🔍 Найдите имя вашей модели на https://platform.openai.com/finetune")
    print("📝 Формат: ft:gpt-3.5-turbo-1106:your-org:vetra-ai-v1:xxxxxxxx")
    
    model_name = input("\n🎯 Введите полное имя вашей файн-тюнинговой модели: ").strip()
    
    if model_name and model_name.startswith("ft:"):
        # Сохраняем для будущего использования
        with open("model_name.txt", "w") as f:
            f.write(model_name)
        return model_name
    
    print("❌ Неправильный формат модели")
    return None

def test_model_with_examples(client, model_name):
    """Тестируем модель с примерами из вашего проекта"""
    
    print(f"\n🧪 ТЕСТИРОВАНИЕ МОДЕЛИ: {model_name}")
    print("=" * 70)
    
    # Тестовые примеры из вашего проекта Vetra AI
    test_cases = [
        # Простые события
        "встреча с клиентом завтра в 14:00",
        "позвонить маме сегодня в 18:00",
        "презентация проекта в пятницу в 10:00",
        
        # Множественные события (ваша специальность!)
        "встреча с клиентом в 10:00, обед с коллегами в 13:00",
        "запланируй мне два мероприятия Презентация проекта – 3 июня в 12:00 Встреча с командой – 5 июня в 9:00",
        
        # Временные диапазоны
        "работа с 9:00 до 17:00",
        "встреча с Лерой с 12:00 до 14:00",
        
        # Конкретные даты
        "встреча 26 мая в 14:00",
        "дедлайн 25.12.2024 в 23:59",
        
        # Сложные случаи
        "через час встреча с Дамиром",
        "послезавтра в 16:30 обед с партнерами",
        
        # НЕ-календарные сообщения (должны возвращать пустой объект)
        "привет как дела?",
        "что такое искусственный интеллект?",
    ]
    
    successful_tests = 0
    total_tests = len(test_cases)
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n{i:2d}. 🧪 Тест: '{test_input}'")
        
        try:
            # Делаем запрос к файн-тюнинговой модели
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": """Ты Vetra AI - умный календарный ассистент. Анализируй естественный язык (русский/английский) и возвращай структурированные данные календаря в JSON формате.

Для календарных событий возвращай объект с полями:
- title: название события
- date: дата (tomorrow, Friday, 15 мая, etc.)
- time: время в формате HH:MM
- type: "event" или "reminder" 
- recurrence: если событие повторяющееся
- reminder: время напоминания
- location: место (если указано)
- participants: участники (если указаны)
- duration: длительность (если указана)

Для множественных событий возвращай массив объектов.
Для НЕ-календарных сообщений возвращай пустой объект {}."""
                    },
                    {
                        "role": "user", 
                        "content": test_input
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            # Получаем ответ
            result = response.choices[0].message.content
            
            # Пробуем распарсить JSON
            try:
                parsed_result = json.loads(result)
                print(f"    ✅ Результат: {json.dumps(parsed_result, ensure_ascii=False)}")
                successful_tests += 1
                
                # Анализируем качество ответа
                if isinstance(parsed_result, list):
                    print(f"    📊 Множественные события: {len(parsed_result)} шт.")
                elif isinstance(parsed_result, dict):
                    if parsed_result:
                        title = parsed_result.get('title', 'N/A')
                        time_val = parsed_result.get('time', 'N/A')
                        print(f"    📊 Событие: '{title}' в {time_val}")
                    else:
                        print(f"    📊 Пустой объект (НЕ-календарное сообщение)")
                        
            except json.JSONDecodeError:
                print(f"    ❌ Неправильный JSON: {result}")
                
        except Exception as e:
            print(f"    ❌ Ошибка API: {e}")
    
    # Статистика
    success_rate = (successful_tests / total_tests) * 100
    print(f"\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"   ✅ Успешных тестов: {successful_tests}/{total_tests}")
    print(f"   📈 Успешность: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print(f"   🎉 ОТЛИЧНО! Модель работает превосходно!")
    elif success_rate >= 70:
        print(f"   ✅ ХОРОШО! Модель работает стабильно!")
    elif success_rate >= 50:
        print(f"   ⚠️  НОРМАЛЬНО! Есть место для улучшений")
    else:
        print(f"   ❌ ПЛОХО! Нужно переобучение или больше данных")
    
    return success_rate

def interactive_test(client, model_name):
    """Интерактивное тестирование модели"""
    
    print(f"\n🎮 ИНТЕРАКТИВНОЕ ТЕСТИРОВАНИЕ")
    print("-" * 40)
    print("Введите свои запросы для тестирования модели")
    print("Введите 'quit' или 'выход' для завершения")
    
    while True:
        try:
            user_input = input("\n🎯 Ваш запрос: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'выход', 'q']:
                break
            
            if not user_input:
                continue
            
            print("🤖 Обрабатываю...")
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": """Ты Vetra AI - умный календарный ассистент. Анализируй естественный язык (русский/английский) и возвращай структурированные данные календаря в JSON формате.

Для календарных событий возвращай объект с полями:
- title: название события
- date: дата (tomorrow, Friday, 15 мая, etc.)
- time: время в формате HH:MM
- type: "event" или "reminder" 
- recurrence: если событие повторяющееся
- reminder: время напоминания
- location: место (если указано)
- participants: участники (если указаны)
- duration: длительность (если указана)

Для множественных событий возвращай массив объектов.
Для НЕ-календарных сообщений возвращай пустой объект {}."""
                    },
                    {
                        "role": "user", 
                        "content": user_input
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            result = response.choices[0].message.content
            
            try:
                parsed_result = json.loads(result)
                print(f"✅ Результат:")
                print(json.dumps(parsed_result, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print(f"❌ Неправильный JSON ответ:")
                print(result)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print("\n👋 Интерактивное тестирование завершено!")

def generate_integration_code(model_name):
    """Генерируем код для интеграции в основной проект"""
    
    integration_code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграция файн-тюнинговой модели Vetra AI в основной проект
Замените ваш parse_with_ai функцию этим кодом
"""

import json
from openai import OpenAI

# Ваша файн-тюнинговая модель
FINE_TUNED_MODEL = "{model_name}"

def parse_with_fine_tuned_ai(text, user_timezone='Asia/Almaty'):
    """
    Парсинг текста с помощью файн-тюнинговой модели Vetra AI
    
    Args:
        text: Входной текст пользователя
        user_timezone: Часовой пояс пользователя
        
    Returns:
        dict или list: Структурированные данные календаря
    """
    
    try:
        # Создаем клиент OpenAI
        client = OpenAI()  # API ключ должен быть в переменных окружения
        
        # Делаем запрос к файн-тюнинговой модели
        response = client.chat.completions.create(
            model=FINE_TUNED_MODEL,
            messages=[
                {{
                    "role": "system", 
                    "content": """Ты Vetra AI - умный календарный ассистент. Анализируй естественный язык (русский/английский) и возвращай структурированные данные календаря в JSON формате.

Для календарных событий возвращай объект с полями:
- title: название события
- date: дата (tomorrow, Friday, 15 мая, etc.)
- time: время в формате HH:MM
- type: "event" или "reminder" 
- recurrence: если событие повторяющееся
- reminder: время напоминания
- location: место (если указано)
- participants: участники (если указаны)
- duration: длительность (если указана)

Для множественных событий возвращай массив объектов.
Для НЕ-календарных сообщений возвращай пустой объект {{}}."""
                }},
                {{
                    "role": "user", 
                    "content": text
                }}
            ],
            max_tokens=800,
            temperature=0.1
        )
        
        # Парсим результат
        result = response.choices[0].message.content
        parsed_result = json.loads(result)
        
        # Обрабатываем результат под ваш формат
        if isinstance(parsed_result, list):
            # Множественные события
            events = []
            for event_data in parsed_result:
                processed_event = process_event_data(event_data, user_timezone)
                if processed_event:
                    events.append(processed_event)
            return events
            
        elif isinstance(parsed_result, dict) and parsed_result:
            # Одиночное событие
            processed_event = process_event_data(parsed_result, user_timezone)
            return [processed_event] if processed_event else []
            
        else:
            # НЕ-календарное сообщение
            return []
            
    except Exception as e:
        print(f"❌ Ошибка файн-тюнинговой модели: {{e}}")
        # Fallback на старую логику
        return fallback_parse(text, user_timezone)

def process_event_data(event_data, user_timezone):
    """
    Обрабатываем данные события в формат вашего проекта
    """
    try:
        from datetime_utils import enhanced_datetime_parser, validate_datetime
        
        # Извлекаем основные поля
        title = event_data.get('title', 'Событие')
        date_str = event_data.get('date', '')
        time_str = event_data.get('time', '')
        event_type = event_data.get('type', 'event')
        
        # Создаем полный текст для парсинга даты
        full_text = f"{{title}} {{date_str}} в {{time_str}}"
        
        # Парсим дату/время
        parsed_datetime = enhanced_datetime_parser(full_text, user_timezone)
        if not parsed_datetime:
            return None
        
        # Валидируем
        validated_datetime = validate_datetime(parsed_datetime, user_timezone)
        if not validated_datetime:
            return None
        
        return (validated_datetime, title, event_type)
        
    except Exception as e:
        print(f"❌ Ошибка обработки события: {{e}}")
        return None

def fallback_parse(text, user_timezone):
    """
    Fallback на старую логику если файн-тюнинг не работает
    """
    try:
        from text_parser import extract_multiple_events
        return extract_multiple_events(text, user_timezone)
    except:
        return []

# Пример использования в main.py:
# 
# В функции handle_message() замените строку:
# events = enhanced_extract_multiple_events_integrated(user_text, DEFAULT_TIMEZONE)
# 
# На:
# events = parse_with_fine_tuned_ai(user_text, DEFAULT_TIMEZONE)
'''
    
    # Сохраняем код интеграции
    with open("vetra_ai_integration.py", "w", encoding="utf-8") as f:
        f.write(integration_code)
    
    print(f"\n📝 КОД ИНТЕГРАЦИИ СОХРАНЕН: vetra_ai_integration.py")
    print(f"🔧 Используйте этот код для замены парсера в main.py")

if __name__ == "__main__":
    print("🧪 VETRA AI - ТЕСТИРОВАНИЕ ФАЙН-ТЮНИНГОВОЙ МОДЕЛИ")
    print("=" * 60)
    
    # Создаем клиент OpenAI
    client = get_openai_client()
    if not client:
        exit(1)
    
    # Получаем имя модели
    model_name = get_fine_tuned_model()
    if not model_name:
        exit(1)
    
    # Тестируем модель
    success_rate = test_model_with_examples(client, model_name)
    
    # Генерируем код интеграции
    generate_integration_code(model_name)
    
    # Предлагаем интерактивное тестирование
    print(f"\n❓ Хотите протестировать модель интерактивно? (y/n): ", end="")
    try:
        choice = input().lower().strip()
        if choice in ['y', 'yes', 'да', '']:
            interactive_test(client, model_name)
    except KeyboardInterrupt:
        pass
    
    print(f"\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print(f"📊 Успешность модели: {success_rate:.1f}%")
    print(f"📝 Код интеграции: vetra_ai_integration.py")
    print(f"🚀 Теперь можете интегрировать модель в main.py!")
    print("=" * 60)