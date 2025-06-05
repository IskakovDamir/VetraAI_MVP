#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Шаг 1: Подготовка данных для файн-тюнинга Vetra AI
Этот скрипт объединяет все JSONL файлы и конвертирует их в формат OpenAI
"""

import json
import os
import openai
from openai import OpenAI

# Устанавливаем API ключ
os.environ["OPENAI_API_KEY"] = "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"

# Инициализируем клиент OpenAI
client = OpenAI()

def prepare_training_data():
    """Объединяем все JSONL файлы и готовим для файн-тюнинга"""
    
    print("🔄 Начинаем подготовку данных для файн-тюнинга...")
    
    # Список всех файлов с тренировочными данными
    training_files = [
        "#1_recurring_calendar_training_data.txt",
        "#2_recurring_calendar_training_data.txt", 
        "#3_reminder_training_data.txt",
        "#4_multi_event_training_data.txt",
        "#5_edge_case_training_data.txt",
        "#6_people_places_training_data.txt",
        "#7_event_updates_training_data.txt",
        "#8_noisy_input_training_data.txt",
        "#9_student_freelancer_remote_training_data.txt",
        "#10_duration_multiday_range_training_data.txt"
    ]
    
    all_data = []
    total_processed = 0
    
    # Системное сообщение для модели
    system_message = """Ты Vetra AI - умный календарный ассистент. Анализируй естественный язык (русский/английский) и возвращай структурированные данные календаря в JSON формате. 

Для календарных событий возвращай объект с полями:
- title: название события
- date: дата (tomorrow, Friday, 15 мая, etc.)
- time: время в формате HH:MM
- type: "event" или "reminder"
- recurrence: если событие повторяющееся
- reminder: время напоминания
- location: место (если указано)
- participants: участники (если указаны)

Для множественных событий возвращай массив объектов.
Для НЕ-календарных сообщений возвращай пустой объект {}."""

    # Обрабатываем каждый файл
    for file_path in training_files:
        if not os.path.exists(file_path):
            print(f"⚠️  Файл не найден: {file_path}")
            continue
            
        print(f"📖 Обрабатываем файл: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_count = 0
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # Парсим исходные данные
                        data = json.loads(line)
                        
                        if "input" not in data or "output" not in data:
                            print(f"⚠️  Пропускаем строку {line_num} в {file_path}: нет input/output")
                            continue
                        
                        # Конвертируем в формат OpenAI
                        formatted_data = {
                            "messages": [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": data["input"]},
                                {"role": "assistant", "content": json.dumps(data["output"], ensure_ascii=False)}
                            ]
                        }
                        
                        all_data.append(formatted_data)
                        file_count += 1
                        total_processed += 1
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON ошибка в {file_path} строка {line_num}: {e}")
                    except Exception as e:
                        print(f"❌ Ошибка в {file_path} строка {line_num}: {e}")
                
                print(f"✅ Из {file_path} обработано: {file_count} примеров")
                
        except FileNotFoundError:
            print(f"❌ Файл не найден: {file_path}")
        except Exception as e:
            print(f"❌ Ошибка при чтении {file_path}: {e}")
    
    if not all_data:
        print("❌ Не удалось обработать ни одного файла!")
        return None
    
    # Сохраняем подготовленные данные
    output_file = 'vetra_training_data.jsonl'
    
    print(f"💾 Сохраняем {len(all_data)} примеров в {output_file}...")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in all_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"✅ Данные успешно подготовлены!")
        print(f"📊 Итого примеров: {len(all_data)}")
        print(f"📁 Файл сохранен: {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении: {e}")
        return None

def validate_training_data(file_path):
    """Валидируем подготовленные данные"""
    
    print(f"\n🔍 Валидируем файл: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            line_count = 0
            valid_count = 0
            
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                line_count += 1
                
                try:
                    data = json.loads(line)
                    
                    # Проверяем структуру
                    if ("messages" in data and 
                        isinstance(data["messages"], list) and 
                        len(data["messages"]) == 3):
                        valid_count += 1
                    else:
                        print(f"⚠️  Неверная структура в строке {line_num}")
                        
                except json.JSONDecodeError:
                    print(f"❌ JSON ошибка в строке {line_num}")
            
            print(f"📊 Проверено строк: {line_count}")
            print(f"✅ Валидных примеров: {valid_count}")
            print(f"📈 Успешность: {(valid_count/line_count)*100:.1f}%")
            
            if valid_count > 100:  # Минимум для файн-тюнинга
                print("🎉 Данные готовы для файн-тюнинга!")
                return True
            else:
                print("❌ Недостаточно данных для файн-тюнинга (нужно минимум 100)")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка валидации: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Vetra AI - Подготовка данных для файн-тюнинга")
    print("=" * 50)
    
    # Шаг 1: Подготавливаем данные
    output_file = prepare_training_data()
    
    if output_file:
        # Шаг 2: Валидируем данные
        if validate_training_data(output_file):
            print(f"\n✅ ВСЕ ГОТОВО!")
            print(f"📁 Файл для загрузки: {output_file}")
            print(f"🎯 Следующий шаг: запустите start_training.py")
        else:
            print(f"\n❌ Проблемы с данными, проверьте ошибки выше")
    else:
        print(f"\n❌ Не удалось подготовить данные")
