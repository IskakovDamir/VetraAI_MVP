"""
УПРОЩЕННАЯ система авторизации без копирования кодов
Использует веб-сервер для автоматического получения токенов
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
USERS_DIR = 'users'
# Веб-сервер для OAuth callback
REDIRECT_URI = 'http://localhost:8080/oauth2callback'

class SimplifiedAuthManager:
    def __init__(self):
        if not os.path.exists(USERS_DIR):
            os.makedirs(USERS_DIR)
            logger.info(f"✅ Создана папка для пользователей: {USERS_DIR}")
        
        # Активные сессии авторизации
        self.active_sessions = {}
        # Веб-сервер для callback
        self.server = None
        self.server_thread = None
        
    def start_callback_server(self):
        """Запустить веб-сервер для OAuth callback"""
        if self.server is None:
            try:
                self.server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
                self.server.auth_manager = self  # Передаем ссылку на менеджер
                
                self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.server_thread.start()
                
                logger.info("✅ OAuth callback сервер запущен на localhost:8080")
                return True
            except Exception as e:
                logger.error(f"❌ Ошибка запуска сервера: {e}")
                return False
        return True
    
    def stop_callback_server(self):
        """Остановить веб-сервер"""
        if self.server:
            self.server.shutdown()
            self.server = None
            logger.info("🛑 OAuth callback сервер остановлен")
    
    def get_user_token_path(self, user_id):
        return os.path.join(USERS_DIR, f"user_{user_id}_token.json")
    
    def get_user_info_path(self, user_id):
        return os.path.join(USERS_DIR, f"user_{user_id}_info.json")
    
    def is_user_authorized(self, user_id):
        """Проверить, авторизован ли пользователь"""
        token_path = self.get_user_token_path(user_id)
        
        if not os.path.exists(token_path):
            return False
        
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            if not creds:
                return False
            
            if creds.valid:
                return True
            
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.save_user_credentials(user_id, creds)
                    return True
                except Exception as e:
                    logger.error(f"❌ Ошибка обновления токена пользователя {user_id}: {e}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки авторизации пользователя {user_id}: {e}")
            return False
    
    def get_user_credentials(self, user_id):
        """Получить учетные данные пользователя"""
        token_path = self.get_user_token_path(user_id)
        
        if not os.path.exists(token_path):
            return None
        
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            if not creds:
                return None
            
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.save_user_credentials(user_id, creds)
                except Exception as e:
                    logger.error(f"❌ Ошибка автообновления токена: {e}")
                    return None
            
            return creds
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения учетных данных: {e}")
            return None
    
    def save_user_credentials(self, user_id, credentials):
        """Сохранить учетные данные пользователя"""
        token_path = self.get_user_token_path(user_id)
        
        try:
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            
            with open(token_path, 'w') as token_file:
                token_file.write(credentials.to_json())
            
            logger.info(f"✅ Токен пользователя {user_id} сохранен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения токена: {e}")
            return False
    
    def save_user_info(self, user_id, user_data):
        """Сохранить информацию о пользователе"""
        info_path = self.get_user_info_path(user_id)
        
        user_data['registered_at'] = datetime.now().isoformat()
        user_data['user_id'] = user_id
        user_data['last_updated'] = datetime.now().isoformat()
        
        try:
            os.makedirs(os.path.dirname(info_path), exist_ok=True)
            
            with open(info_path, 'w', encoding='utf-8') as info_file:
                json.dump(user_data, info_file, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Информация пользователя {user_id} сохранена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения информации: {e}")
            return False
    
    def get_user_info(self, user_id):
        """Получить информацию о пользователе"""
        info_path = self.get_user_info_path(user_id)
        
        if not os.path.exists(info_path):
            return None
        
        try:
            with open(info_path, 'r', encoding='utf-8') as info_file:
                return json.load(info_file)
        except Exception as e:
            logger.error(f"❌ Ошибка чтения информации: {e}")
            return None
    
    def get_google_user_profile(self, credentials):
        """Получить профиль пользователя Google"""
        try:
            service = build('calendar', 'v3', credentials=credentials)
            calendar_list = service.calendarList().list().execute()
            
            primary_calendar = None
            calendar_count = 0
            
            for calendar in calendar_list.get('items', []):
                calendar_count += 1
                if calendar.get('primary', False):
                    primary_calendar = {
                        'id': calendar['id'],
                        'summary': calendar.get('summary', 'Основной календарь'),
                        'timezone': calendar.get('timeZone', 'UTC'),
                        'access_role': calendar.get('accessRole', 'unknown')
                    }
            
            return {
                'primary_calendar': primary_calendar,
                'calendar_count': calendar_count,
                'calendars': calendar_list.get('items', [])[:5],
                'profile_fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения профиля: {e}")
            return None
    
    def create_authorization_url(self, user_id):
        """Создать ссылку авторизации с автоматическим callback"""
        try:
            # Запускаем callback сервер если не запущен
            if not self.start_callback_server():
                return None
            
            if not os.path.exists('credentials.json'):
                logger.error("❌ Файл credentials.json не найден")
                return None
            
            # Создаем flow
            flow = Flow.from_client_secrets_file(
                'credentials.json',
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            
            # Создаем URL авторизации
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            # Сохраняем сессию
            self.active_sessions[state] = {
                'user_id': user_id,
                'flow': flow,
                'created_at': datetime.now()
            }
            
            logger.info(f"✅ Создана ссылка авторизации для пользователя {user_id}")
            return auth_url
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания ссылки авторизации: {e}")
            return None
    
    def handle_oauth_callback(self, state, code):
        """Обработать callback от Google OAuth"""
        try:
            if state not in self.active_sessions:
                logger.error(f"❌ Неизвестная сессия: {state}")
                return None
            
            session = self.active_sessions[state]
            user_id = session['user_id']
            flow = session['flow']
            
            # Получаем токен
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            if not creds:
                logger.error(f"❌ Не удалось получить токен")
                return None
            
            # Сохраняем учетные данные
            if not self.save_user_credentials(user_id, creds):
                return None
            
            # Получаем профиль пользователя
            user_profile = self.get_google_user_profile(creds)
            if user_profile:
                self.save_user_info(user_id, user_profile)
            
            # Очищаем сессию
            del self.active_sessions[state]
            
            logger.info(f"✅ Авторизация пользователя {user_id} завершена")
            return user_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки callback: {e}")
            return None
    
    def revoke_user_authorization(self, user_id):
        """Отозвать авторизацию пользователя"""
        token_path = self.get_user_token_path(user_id)
        info_path = self.get_user_info_path(user_id)
        
        files_removed = 0
        for file_path in [token_path, info_path]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    files_removed += 1
                except Exception as e:
                    logger.error(f"❌ Ошибка удаления файла {file_path}: {e}")
        
        logger.info(f"✅ Авторизация пользователя {user_id} отозвана")
        return files_removed > 0

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Обработчик OAuth callback"""
    
    def do_GET(self):
        """Обработать GET запрос от Google OAuth"""
        try:
            # Парсим URL
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            if parsed_url.path == '/oauth2callback':
                # Получаем параметры
                state = query_params.get('state', [None])[0]
                code = query_params.get('code', [None])[0]
                error = query_params.get('error', [None])[0]
                
                if error:
                    self.send_error_response(f"Ошибка авторизации: {error}")
                    return
                
                if not state or not code:
                    self.send_error_response("Отсутствуют необходимые параметры")
                    return
                
                # Обрабатываем callback
                user_id = self.server.auth_manager.handle_oauth_callback(state, code)
                
                if user_id:
                    self.send_success_response(user_id)
                else:
                    self.send_error_response("Ошибка завершения авторизации")
            else:
                self.send_404()
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки callback: {e}")
            self.send_error_response(f"Внутренняя ошибка: {str(e)}")
    
    def send_success_response(self, user_id):
        """Отправить успешный ответ"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Авторизация завершена</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                       text-align: center; margin-top: 100px; background: #f5f5f5; }}
                .container {{ background: white; padding: 40px; border-radius: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: inline-block; }}
                .success {{ color: #28a745; font-size: 24px; margin-bottom: 20px; }}
                .message {{ color: #666; font-size: 16px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅ Авторизация успешно завершена!</div>
                <div class="message">
                    Теперь вы можете закрыть эту страницу и<br>
                    вернуться к боту в Telegram.
                </div>
            </div>
            <script>
                setTimeout(function() {{
                    window.close();
                }}, 3000);
            </script>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_error_response(self, error_message):
        """Отправить ответ с ошибкой"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ошибка авторизации</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                       text-align: center; margin-top: 100px; background: #f5f5f5; }}
                .container {{ background: white; padding: 40px; border-radius: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: inline-block; }}
                .error {{ color: #dc3545; font-size: 24px; margin-bottom: 20px; }}
                .message {{ color: #666; font-size: 16px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">❌ Ошибка авторизации</div>
                <div class="message">
                    {error_message}<br><br>
                    Попробуйте еще раз или обратитесь к администратору.
                </div>
            </div>
        </body>
        </html>
        """
        
        self.send_response(400)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_404(self):
        """Отправить 404 ответ"""
        self.send_response(404)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'404 Not Found')
    
    def log_message(self, format, *args):
        """Отключаем стандартное логирование HTTP сервера"""
        pass

# Глобальный экземпляр менеджера
simplified_auth_manager = SimplifiedAuthManager()

def get_user_calendar_service(user_id):
    """Получить сервис Google Calendar для конкретного пользователя"""
    try:
        creds = simplified_auth_manager.get_user_credentials(user_id)
        if not creds:
            return None
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Тестируем подключение
        try:
            service.calendarList().list(maxResults=1).execute()
            return service
        except HttpError as e:
            logger.error(f"❌ Ошибка тестирования сервиса: {e}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания сервиса: {e}")
        return None