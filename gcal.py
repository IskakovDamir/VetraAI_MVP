from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import datetime
import os.path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_credentials():
    """Получить валидные учетные данные для Google Calendar API"""
    creds = None
    
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            logger.info("✅ Токен загружен из файла")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки токена: {e}")
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("🔄 Обновление истекшего токена...")
                creds.refresh(Request())
                logger.info("✅ Токен успешно обновлен")
            except Exception as e:
                logger.error(f"❌ Ошибка обновления токена: {e}")
                creds = None
        
        if not creds:
            logger.info("🔐 Начинаем полную авторизацию...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("✅ Авторизация завершена")
            except Exception as e:
                logger.error(f"❌ Ошибка авторизации: {e}")
                raise
        
        try:
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            logger.info("✅ Токен сохранен в файл")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения токена: {e}")
    
    return creds

def add_event_to_calendar(summary, start_datetime, end_datetime, timezone='Asia/Almaty'):
    """Добавить событие в Google Calendar"""
    try:
        creds = get_credentials()
        service = build('calendar', 'v3', credentials=creds)
        
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
            'description': f'✨ Создано через Vetra AI'
        }
        
        logger.info(f"📅 Создаем событие: {summary}")
        logger.info(f"⏰ Время: {start_datetime.isoformat()} - {end_datetime.isoformat()}")
        
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        
        logger.info(f"✅ Событие создано! ID: {event_result.get('id')}")
        return event_result
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания события: {e}")
        return None

if __name__ == "__main__":
    print("🧪 Тестирование подключения к календарю...")
    try:
        creds = get_credentials()
        service = build('calendar', 'v3', credentials=creds)
        calendar_list = service.calendarList().list().execute()
        
        print("📅 Доступные календари:")
        for calendar in calendar_list.get('items', []):
            print(f"  - {calendar['summary']} (ID: {calendar['id']})")
        print("✅ Подключение работает!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")