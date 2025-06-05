#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ФИНАЛЬНЫЙ Шаг 2: Запуск файн-тюнинга Vetra AI
Этот скрипт загружает данные в OpenAI и запускает обучение модели
Обновлено для новой OpenAI API
"""

import json
import os
import time
from openai import OpenAI

def get_openai_client():
    """Создаем клиент OpenAI с проверкой API ключа"""
    
    # Проверяем API ключ в переменных окружения
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден в переменных окружения!")
        print("\n🔧 РЕШЕНИЕ:")
        print("1. Экспортируйте ключ: export OPENAI_API_KEY='your-key-here'")
        print("2. Или добавьте в .env файл")
        print("3. Или введите ключ прямо сейчас")
        
        api_key = input("\n🔑 Введите ваш OpenAI API ключ: ").strip()
        if not api_key:
            print("❌ API ключ обязателен!")
            return None
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Тестируем подключение
        models = client.models.list()
        print(f"✅ Подключение к OpenAI успешно! Доступно моделей: {len(list(models))}")
        
        return client
        
    except Exception as e:
        print(f"❌ Ошибка подключения к OpenAI: {e}")
        print("🔧 Проверьте правильность API ключа и интернет соединение")
        return None

def upload_training_file(client):
    """Загружаем файл с данными в OpenAI"""
    
    training_file_path = "vetra_training_data.jsonl"
    
    if not os.path.exists(training_file_path):
        print(f"❌ Файл не найден: {training_file_path}")
        print("🔧 Сначала запустите: python step1_prepare_data_final.py")
        return None
    
    # Проверяем размер файла
    file_size = os.path.getsize(training_file_path)
    print(f"📊 Размер файла: {file_size / 1024:.1f} KB")
    
    if file_size > 100 * 1024 * 1024:  # 100MB лимит
        print(f"⚠️  ВНИМАНИЕ: Файл очень большой ({file_size / 1024 / 1024:.1f} MB)")
        print(f"📝 OpenAI может ограничить размер. Рекомендуется < 100MB")
    
    print(f"📤 Загружаем тренировочные данные: {training_file_path}")
    
    try:
        with open(training_file_path, "rb") as f:
            training_file = client.files.create(
                file=f,
                purpose="fine-tune"
            )
        
        print(f"✅ Файл успешно загружен в OpenAI!")
        print(f"📄 ID файла: {training_file.id}")
        print(f"📊 Размер: {training_file.bytes} байт")
        print(f"📅 Дата создания: {training_file.created_at}")
        print(f"🎯 Назначение: {training_file.purpose}")
        
        # Сохраняем ID файла для повторного использования
        with open("training_file_id.txt", "w") as f:
            f.write(training_file.id)
        print(f"💾 ID файла сохранен в training_file_id.txt")
        
        return training_file.id
        
    except Exception as e:
        print(f"❌ Ошибка загрузки файла: {e}")
        print("🔧 Возможные причины:")
        print("   • Неправильный API ключ")
        print("   • Недостаточно средств на аккаунте OpenAI")
        print("   • Файл поврежден или неправильного формата")
        print("   • Проблемы с интернетом")
        return None

def start_fine_tuning(client, training_file_id):
    """Запускаем файн-тюнинг"""
    
    print(f"\n🚀 ЗАПУСК ФАЙН-ТЮНИНГА МОДЕЛИ...")
    print("-" * 40)
    
    try:
        # Создаем задачу файн-тюнинга
        fine_tuning_job = client.fine_tuning.jobs.create(
            training_file=training_file_id,
            model="gpt-3.5-turbo-1106",  # Стабильная версия для файн-тюнинга
            hyperparameters={
                "n_epochs": 3,  # 3 эпохи оптимально для ваших данных
                "batch_size": 1,
                "learning_rate_multiplier": 2.0
            },
            suffix="vetra-ai-v1"  # Суффикс для имени модели
        )
        
        print(f"✅ Файн-тюнинг успешно запущен!")
        print(f"🆔 ID задачи: {fine_tuning_job.id}")
        print(f"📊 Статус: {fine_tuning_job.status}")
        print(f"🎯 Базовая модель: {fine_tuning_job.model}")
        print(f"📅 Время создания: {fine_tuning_job.created_at}")
        
        # Сохраняем ID задачи для отслеживания
        with open("training_job_id.txt", "w") as f:
            f.write(fine_tuning_job.id)
        print(f"💾 ID задачи сохранен в training_job_id.txt")
        
        # Сохраняем полную информацию о задаче
        job_info = {
            "job_id": fine_tuning_job.id,
            "status": fine_tuning_job.status,
            "model": fine_tuning_job.model,
            "created_at": fine_tuning_job.created_at,
            "training_file": training_file_id,
            "hyperparameters": {
                "n_epochs": 3,
                "batch_size": 1,
                "learning_rate_multiplier": 2.0
            }
        }
        
        with open("training_job_info.json", "w", encoding="utf-8") as f:
            json.dump(job_info, f, indent=2, ensure_ascii=False, default=str)
        print(f"📝 Детали задачи сохранены в training_job_info.json")
        
        return fine_tuning_job.id
        
    except Exception as e:
        print(f"❌ Ошибка запуска файн-тюнинга: {e}")
        print("🔧 Возможные причины:")
        print("   • Недостаточно средств на аккаунте ($)")
        print("   • Файл с данными содержит ошибки")
        print("   • Превышены лимиты API")
        print("   • Проблемы с интернетом")
        return None

def get_training_status(client, job_id):
    """Проверяем статус обучения"""
    
    try:
        job = client.fine_tuning.jobs.retrieve(job_id)
        
        print(f"\n📊 СТАТУС ФАЙН-ТЮНИНГА:")
        print("-" * 30)
        print(f"🆔 ID задачи: {job.id}")
        print(f"📈 Статус: {job.status}")
        print(f"🎯 Базовая модель: {job.model}")
        print(f"📅 Создано: {job.created_at}")
        
        if hasattr(job, 'estimated_finish') and job.estimated_finish:
            print(f"⏰ Ожидаемое завершение: {job.estimated_finish}")
        
        if job.fine_tuned_model:
            print(f"🎉 Готовая модель: {job.fine_tuned_model}")
            
            # Сохраняем имя готовой модели
            with open("model_name.txt", "w") as f:
                f.write(job.fine_tuned_model)
            print(f"💾 Имя модели сохранено в model_name.txt")
        
        # Показываем результаты обучения если есть
        if hasattr(job, 'result_files') and job.result_files:
            print(f"📊 Файлы результатов: {len(job.result_files)}")
        
        if job.status == "succeeded":
            print(f"\n🎉 ФАЙН-ТЮНИНГ ЗАВЕРШЕН УСПЕШНО!")
            print(f"✅ Модель готова к использованию: {job.fine_tuned_model}")
            return "succeeded"
        elif job.status == "failed":
            print(f"\n❌ ФАЙН-ТЮНИНГ ПРОВАЛИЛСЯ!")
            if hasattr(job, 'error') and job.error:
                print(f"🔥 Причина ошибки: {job.error}")
            print(f"🔧 Попробуйте:")
            print(f"   • Проверить данные на ошибки")
            print(f"   • Убедиться что на аккаунте достаточно средств")
            print(f"   • Запустить обучение заново")
            return "failed"
        elif job.status in ["validating_files", "queued", "running"]:
            print(f"\n⏳ ОБУЧЕНИЕ В ПРОЦЕССЕ...")
            if job.status == "validating_files":
                print(f"🔍 Проверяются файлы данных")
            elif job.status == "queued":
                print(f"📋 Задача в очереди на обучение")
            elif job.status == "running":
                print(f"🏃‍♂️ Модель обучается прямо сейчас!")
            
            print(f"🔄 Проверьте статус через 5-10 минут")
            return "in_progress"
        else:
            print(f"\n❓ Неизвестный статус: {job.status}")
            return "unknown"
            
    except Exception as e:
        print(f"❌ Ошибка получения статуса: {e}")
        return "error"

def list_fine_tuned_models(client):
    """Показываем все файн-тюн модели пользователя"""
    
    print(f"\n📋 ВАШИ ФАЙН-ТЮНИНГ ЗАДАЧИ:")
    print("-" * 40)
    
    try:
        jobs = client.fine_tuning.jobs.list(limit=10)
        
        if not jobs.data:
            print("📝 У вас пока нет задач файн-тюнинга")
            return
        
        for i, job in enumerate(jobs.data, 1):
            status_emoji = {
                "succeeded": "✅",
                "failed": "❌", 
                "running": "⏳",
                "queued": "🕒",
                "cancelled": "🚫",
                "validating_files": "🔍"
            }.get(job.status, "❓")
            
            model_name = job.fine_tuned_model or "N/A"
            print(f"{i:2d}. {status_emoji} {job.id[:15]}... | {job.status} | {model_name}")
            
    except Exception as e:
        print(f"❌ Ошибка получения списка: {e}")

def estimate_cost():
    """Примерная оценка стоимости файн-тюнинга"""
    
    training_file = "vetra_training_data.jsonl"
    if not os.path.exists(training_file):
        return
    
    # Подсчитываем количество примеров
    with open(training_file, 'r', encoding='utf-8') as f:
        examples = sum(1 for line in f if line.strip())
    
    # Приблизительный расчет стоимости
    # GPT-3.5-turbo файн-тюнинг: $0.008/1K tokens для обучения
    avg_tokens_per_example = 100  # примерно
    total_tokens = examples * avg_tokens_per_example * 3  # 3 эпохи
    estimated_cost = (total_tokens / 1000) * 0.008
    
    print(f"\n💰 ПРИМЕРНАЯ СТОИМОСТЬ ОБУЧЕНИЯ:")
    print(f"   • Примеров: {examples}")
    print(f"   • Примерно токенов: {total_tokens:,}")
    print(f"   • Ориентировочная стоимость: ${estimated_cost:.2f}")
    print(f"   • (Точную стоимость смотрите на platform.openai.com)")

if __name__ == "__main__":
    print("🚀 VETRA AI - ЗАПУСК ФАЙН-ТЮНИНГА")
    print("=" * 50)
    
    # Создаем клиент OpenAI
    client = get_openai_client()
    if not client:
        exit(1)
    
    # Показываем примерную стоимость
    estimate_cost()
    
    # Проверяем, есть ли уже запущенная задача
    if os.path.exists("training_job_id.txt"):
        with open("training_job_id.txt", "r") as f:
            existing_job_id = f.read().strip()
        
        print(f"\n📋 Найдена существующая задача: {existing_job_id}")
        print(f"🔍 Проверяем статус...")
        
        status = get_training_status(client, existing_job_id)
        
        if status == "succeeded":
            print(f"\n🎉 У ВАС УЖЕ ЕСТЬ ГОТОВАЯ МОДЕЛЬ!")