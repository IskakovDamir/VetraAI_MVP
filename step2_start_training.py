#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Шаг 2: Запуск файн-тюнинга Vetra AI
Этот скрипт загружает данные в OpenAI и запускает обучение модели
"""

import json
import os
import time
from openai import OpenAI

# Устанавливаем API ключ
os.environ["OPENAI_API_KEY"] = "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"

# Инициализируем клиент OpenAI
client = OpenAI()

def upload_training_file():
    """Загружаем файл с данными в OpenAI"""
    
    training_file_path = "vetra_training_data.jsonl"
    
    if not os.path.exists(training_file_path):
        print(f"❌ Файл не найден: {training_file_path}")
        print("🔧 Сначала запустите prepare_data.py")
        return None
    
    print(f"📤 Загружаем тренировочные данные: {training_file_path}")
    
    try:
        with open(training_file_path, "rb") as f:
            training_file = client.files.create(
                file=f,
                purpose="fine-tune"
            )
        
        print(f"✅ Файл успешно загружен!")
        print(f"📄 ID файла: {training_file.id}")
        print(f"📊 Размер: {training_file.bytes} байт")
        print(f"📅 Дата: {training_file.created_at}")
        
        return training_file.id
        
    except Exception as e:
        print(f"❌ Ошибка загрузки файла: {e}")
        return None

def start_fine_tuning(training_file_id):
    """Запускаем файн-тюнинг"""
    
    print(f"\n🚀 Запускаем файн-тюнинг модели...")
    
    try:
        fine_tuning_job = client.fine_tuning.jobs.create(
            training_file=training_file_id,
            model="gpt-3.5-turbo-1106",  # Последняя стабильная версия
            hyperparameters={
                "n_epochs": 3,  # 3 эпохи - хорошо для вашего размера данных
                "batch_size": 1,
                "learning_rate_multiplier": 2
            },
            suffix="vetra-ai"  # Суффикс для имени модели
        )
        
        print(f"✅ Файн-тюнинг запущен!")
        print(f"🆔 ID задачи: {fine_tuning_job.id}")
        print(f"📊 Статус: {fine_tuning_job.status}")
        print(f"🎯 Модель: {fine_tuning_job.model}")
        
        # Сохраняем ID задачи для отслеживания
        with open("training_job_id.txt", "w") as f:
            f.write(fine_tuning_job.id)
        
        print(f"💾 ID задачи сохранен в training_job_id.txt")
        
        return fine_tuning_job.id
        
    except Exception as e:
        print(f"❌ Ошибка запуска файн-тюнинга: {e}")
        return None

def get_training_status(job_id):
    """Проверяем статус обучения"""
    
    try:
        job = client.fine_tuning.jobs.retrieve(job_id)
        
        print(f"\n📊 СТАТУС ОБУЧЕНИЯ:")
        print(f"🆔 ID задачи: {job.id}")
        print(f"📈 Статус: {job.status}")
        print(f"🎯 Базовая модель: {job.model}")
        print(f"📅 Создано: {job.created_at}")
        
        if job.fine_tuned_model:
            print(f"🎉 Готовая модель: {job.fine_tuned_model}")
            
            # Сохраняем имя модели
            with open("model_name.txt", "w") as f:
                f.write(job.fine_tuned_model)
            print(f"💾 Имя модели сохранено в model_name.txt")
        
        if job.status == "succeeded":
            print(f"🎉 ОБУЧЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            return "succeeded"
        elif job.status == "failed":
            print(f"❌ ОБУЧЕНИЕ ПРОВАЛИЛОСЬ!")
            if hasattr(job, 'error') and job.error:
                print(f"🔥 Ошибка: {job.error}")
            return "failed"
        elif job.status in ["validating_files", "queued", "running"]:
            print(f"⏳ Обучение в процессе... Проверьте позже")
            return "in_progress"
        else:
            print(f"❓ Неизвестный статус: {job.status}")
            return "unknown"
            
    except Exception as e:
        print(f"❌ Ошибка получения статуса: {e}")
        return "error"

def list_fine_tuned_models():
    """Показываем все файн-тюн модели"""
    
    print(f"\n📋 Ваши файн-тюн модели:")
    
    try:
        jobs = client.fine_tuning.jobs.list(limit=10)
        
        for job in jobs.data:
            status_emoji = {
                "succeeded": "✅",
                "failed": "❌", 
                "running": "⏳",
                "queued": "🕒",
                "cancelled": "🚫"
            }.get(job.status, "❓")
            
            print(f"{status_emoji} {job.id} | {job.status} | {job.fine_tuned_model or 'N/A'}")
            
    except Exception as e:
        print(f"❌ Ошибка получения списка: {e}")

if __name__ == "__main__":
    print("🚀 Vetra AI - Запуск файн-тюнинга")
    print("=" * 50)
    
    # Проверяем, есть ли уже запущенная задача
    if os.path.exists("training_job_id.txt"):
        with open("training_job_id.txt", "r") as f:
            existing_job_id = f.read().strip()
        
        print(f"📋 Найдена существующая задача: {existing_job_id}")
        print(f"🔍 Проверяем статус...")
        
        status = get_training_status(existing_job_id)
        
        if status == "succeeded":
            print(f"\n🎉 У вас уже есть готовая модель!")
            print(f"🎯 Следующий шаг: запустите test_model.py")
        elif status == "in_progress":
            print(f"\n⏳ Обучение еще идет, подождите...")
            print(f"🔄 Запустите этот скрипт позже для проверки")
        elif status in ["failed", "error"]:
            print(f"\n🔄 Предыдущее обучение провалилось, запускаем новое...")
            # Продолжаем с новым обучением
        
        if status in ["succeeded", "in_progress"]:
            exit(0)
    
    # Запускаем новое обучение
    print(f"\n🚀 Запускаем новое обучение...")
    
    # Шаг 1: Загружаем файл
    training_file_id = upload_training_file()
    
    if not training_file_id:
        print(f"❌ Не удалось загрузить файл")
        exit(1)
    
    # Шаг 2: Запускаем обучение
    job_id = start_fine_tuning(training_file_id)
    
    if not job_id:
        print(f"❌ Не удалось запустить обучение")
        exit(1)
    
    # Шаг 3: Начальная проверка статуса
    print(f"\n⏳ Проверяем начальный статус...")
    time.sleep(2)  # Небольшая пауза
    
    status = get_training_status(job_id)
    
    # Инструкции для пользователя
    print(f"\n" + "="*50)
    print(f"📋 ЧТО ДАЛЬШЕ:")
    print(f"⏳ Обучение займет 20-60 минут")
    print(f"🔄 Запускайте этот скрипт каждые 10-15 минут для проверки статуса")
    print(f"📱 Или проверяйте на сайте: https://platform.openai.com/finetune")
    print(f"🎯 Когда статус станет 'succeeded', запустите test_model.py")
    print(f"="*50)
    
    # Показываем все модели
    list_fine_tuned_models()
