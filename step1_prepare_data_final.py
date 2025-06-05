#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ФИНАЛЬНЫЙ Шаг 1: Подготовка данных для файн-тюнинга Vetra AI
Этот скрипт объединяет все JSONL файлы и конвертирует их в формат OpenAI
Обновлено для работы с новой OpenAI API
"""

import json
import os
from openai import OpenAI

def prepare_training_data():
    """Объединяем все JSONL файлы и готовим для файн-тюнинга"""
    
    print("🔄 VETRA AI - Подготовка данных для файн-тюнинга...")
    print("=" * 60)
    
    # Список всех файлов с тренировочными данными
    training_files = [
        "#1_calendar_training_data.txt",
        "#2_recurring_calendar_training_data.txt", 
        "#3_reminder_training_data.txt",
        "#4_multi_event_training_data.txt",
        "#5_edge_case_training_data.txt",
        "#6_people_places_training_data.txt",
        "#7_event_updates_training_data.txt",
        "#8_noisy_input_training_data.txt",
        "#9_student_freelancer_related_training_data.txt",
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
- duration: длительность (если указана)

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
                        
                        # Конвертируем в формат OpenAI для fine-tuning
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
        print("\n🔧 ВОЗМОЖНЫЕ ПРОБЛЕМЫ:")
        print("1. Файлы с данными не найдены в текущей папке")
        print("2. Неправильный формат данных в файлах")
        print("3. Проблемы с кодировкой файлов")
        return None
    
    # Сохраняем подготовленные данные
    output_file = 'vetra_training_data.jsonl'
    
    print(f"\n💾 Сохраняем {len(all_data)} примеров в {output_file}...")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in all_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"✅ Данные успешно подготовлены!")
        print(f"📊 Итого примеров: {len(all_data)}")
        print(f"📁 Файл сохранен: {output_file}")
        
        # Показываем статистику по типам данных
        print(f"\n📈 СТАТИСТИКА:")
        print(f"   • Всего примеров: {len(all_data)}")
        print(f"   • Файлов обработано: {len([f for f in training_files if os.path.exists(f)])}")
        print(f"   • Размер файла: {os.path.getsize(output_file) / 1024:.1f} KB")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении: {e}")
        return None

def validate_training_data(file_path):
    """Валидируем подготовленные данные"""
    
    print(f"\n🔍 ВАЛИДАЦИЯ ДАННЫХ: {file_path}")
    print("-" * 40)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            line_count = 0
            valid_count = 0
            system_msgs = 0
            user_msgs = 0
            assistant_msgs = 0
            
            sample_examples = []
            
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
                        
                        messages = data["messages"]
                        
                        # Проверяем роли
                        if (messages[0]["role"] == "system" and
                            messages[1]["role"] == "user" and  
                            messages[2]["role"] == "assistant"):
                            
                            valid_count += 1
                            system_msgs += 1
                            user_msgs += 1
                            assistant_msgs += 1
                            
                            # Сохраняем первые 3 примера для показа
                            if len(sample_examples) < 3:
                                sample_examples.append({
                                    'user': messages[1]["content"][:100] + "..." if len(messages[1]["content"]) > 100 else messages[1]["content"],
                                    'assistant': messages[2]["content"][:150] + "..." if len(messages[2]["content"]) > 150 else messages[2]["content"]
                                })
                        else:
                            print(f"⚠️  Неверные роли в строке {line_num}")
                    else:
                        print(f"⚠️  Неверная структура в строке {line_num}")
                        
                except json.JSONDecodeError:
                    print(f"❌ JSON ошибка в строке {line_num}")
            
            print(f"📊 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ:")
            print(f"   • Всего строк: {line_count}")
            print(f"   • Валидных примеров: {valid_count}")
            print(f"   • System сообщений: {system_msgs}")
            print(f"   • User сообщений: {user_msgs}")
            print(f"   • Assistant сообщений: {assistant_msgs}")
            print(f"   • Успешность: {(valid_count/line_count)*100:.1f}%")
            
            # Показываем примеры
            if sample_examples:
                print(f"\n📝 ПРИМЕРЫ ДАННЫХ:")
                for i, example in enumerate(sample_examples, 1):
                    print(f"   {i}. User: '{example['user']}'")
                    print(f"      Assistant: '{example['assistant']}'")
                    print()
            
            if valid_count >= 100:  # Минимум для файн-тюнинга
                print("🎉 ДАННЫЕ ГОТОВЫ ДЛЯ ФАЙН-ТЮНИНГА!")
                print(f"✅ Достаточно примеров ({valid_count} >= 100)")
                return True
            else:
                print("❌ НЕДОСТАТОЧНО ДАННЫХ ДЛЯ ФАЙН-ТЮНИНГА!")
                print(f"🔧 Нужно минимум 100 примеров, у вас: {valid_count}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка валидации: {e}")
        return False

def show_file_info():
    """Показываем информацию о необходимых файлах"""
    print(f"\n📋 НЕОБХОДИМЫЕ ФАЙЛЫ ДЛЯ ОБУЧЕНИЯ:")
    print("-" * 50)
    
    required_files = [
        "#1_calendar_training_data.txt",
        "#2_recurring_calendar_training_data.txt", 
        "#3_reminder_training_data.txt",
        "#4_multi_event_training_data.txt",
        "#5_edge_case_training_data.txt",
        "#6_people_places_training_data.txt",
        "#7_event_updates_training_data.txt",
        "#8_noisy_input_training_data.txt",
        "#9_student_freelancer_related_training_data.txt",
        "#10_duration_multiday_range_training_data.txt"
    ]
    
    found_files = 0
    
    for i, file_name in enumerate(required_files, 1):
        if os.path.exists(file_name):
            print(f"✅ {i:2d}. {file_name}")
            found_files += 1
        else:
            print(f"❌ {i:2d}. {file_name} - НЕ НАЙДЕН")
    
    print(f"\n📊 Найдено файлов: {found_files}/{len(required_files)}")
    
    if found_files == 0:
        print(f"\n🚨 НИ ОДНОГО ФАЙЛА НЕ НАЙДЕНО!")
        print(f"🔧 РЕШЕНИЕ:")
        print(f"   1. Убедитесь, что файлы находятся в той же папке что и этот скрипт")
        print(f"   2. Проверьте правильность названий файлов")
        print(f"   3. Если файлы не готовы, создайте их или попросите помощи")
    elif found_files < len(required_files):
        print(f"\n⚠️  НЕ ВСЕ ФАЙЛЫ НАЙДЕНЫ!")
        print(f"🔧 Обучение возможно, но качество модели может быть ниже")
    else:
        print(f"\n🎉 ВСЕ ФАЙЛЫ НАЙДЕНЫ! ГОТОВО К ОБУЧЕНИЮ!")

if __name__ == "__main__":
    print("🚀 VETRA AI - ПОДГОТОВКА ДАННЫХ ДЛЯ ФАЙН-ТЮНИНГА")
    print("=" * 60)
    
    # Проверяем наличие файлов
    show_file_info()
    
    # Спрашиваем подтверждение
    print(f"\n❓ Продолжить подготовку данных? (y/n): ", end="")
    try:
        choice = input().lower().strip()
        if choice not in ['y', 'yes', 'да', '']:
            print("❌ Отменено пользователем")
            exit(0)
    except KeyboardInterrupt:
        print("\n❌ Отменено пользователем")
        exit(0)
    
    # Шаг 1: Подготавливаем данные
    output_file = prepare_training_data()
    
    if output_file:
        # Шаг 2: Валидируем данные
        if validate_training_data(output_file):
            print(f"\n🎉 ВСЁ ГОТОВО ДЛЯ ФАЙН-ТЮНИНГА!")
            print(f"📁 Файл для загрузки: {output_file}")
            print(f"🎯 Следующий шаг: python step2_start_training.py")
            print(f"=" * 60)
        else:
            print(f"\n❌ ПРОБЛЕМЫ С ДАННЫМИ")
            print(f"🔧 Проверьте ошибки выше и исправьте файлы")
    else:
        print(f"\n❌ НЕ УДАЛОСЬ ПОДГОТОВИТЬ ДАННЫЕ")
        print(f"🔧 Проверьте наличие файлов и их формат")