from telethon import TelegramClient
from telethon.errors import AuthRestartError, FloodWaitError, SessionPasswordNeededError
import time
import os
from dotenv import load_dotenv

def get_env_value(key, prompt):
    """Получает значение из .env или запрашивает у пользователя"""
    value = os.getenv(key)
    if not value or value == f'your_{key.lower()}_here' or value == 'your_phone_number_here':
        value = input(prompt)
        # Обновляем .env файл
        with open('.env', 'r') as file:
            lines = file.readlines()
        with open('.env', 'w') as file:
            for line in lines:
                if line.startswith(f'{key}='):
                    file.write(f'{key}={value}\n')
                else:
                    file.write(line)
    return value

async def authenticate_client():
    """Аутентификация клиента Telegram"""
    # Загрузка переменных окружения
    load_dotenv()
    
    # Получение данных для авторизации
    api_id = get_env_value('API_ID', 'Введите ваш API_ID (число): ')
    api_hash = get_env_value('API_HASH', 'Введите ваш API_HASH (строка): ')
    phone = get_env_value('PHONE', 'Введите ваш номер телефона в формате +7XXXXXXXXXX: ')

    # Проверка корректности всех введенных значений
    try:
        api_id = int(api_id)
        if not api_id:
            raise ValueError("API_ID не может быть пустым")
    except ValueError:
        raise ValueError("API_ID должен быть числом")

    if not api_hash or api_hash == 'your_api_hash_here':
        raise ValueError("API_HASH не может быть пустым")

    if not phone or phone == 'your_phone_number_here':
        raise ValueError("Номер телефона не может быть пустым")
    elif not phone.startswith('+7') or len(phone) != 12:
        raise ValueError("Номер телефона должен быть в формате +7XXXXXXXXXX")

    print("Подключаемся к Telegram API...")
    
    # Создание клиента
    client = TelegramClient('session_name', api_id, api_hash)
    
    max_retries = 3
    retry_count = 0
    wait_time = 30  # время ожидания между попытками в секундах
    
    while retry_count < max_retries:
        try:
            print(f"\nПопытка авторизации {retry_count + 1} из {max_retries}...")
            
            # Подключение к Telegram
            await client.connect()
            
            if not await client.is_user_authorized():
                try:
                    print("Отправляем запрос на получение кода...")
                    await client.send_code_request(phone)
                    print("Запрос на код отправлен успешно")
                    
                    print("\nВнимание! Код подтверждения может прийти:\n"
                          "1. В виде SMS на указанный номер телефона\n"
                          "2. В виде сообщения в Telegram (если у вас есть активная сессия)\n"
                          "3. В виде push-уведомления в приложении Telegram\n"
                          "\nЕсли код не пришел в течение 1-2 минут:\n"
                          "1. Проверьте все возможные места получения кода\n"
                          "2. Убедитесь, что номер телефона введен правильно\n"
                          "3. Попробуйте запросить код повторно через 5 минут\n"
                          "4. Проверьте, не заблокирован ли ваш номер в Telegram")
                    
                    # Ждем ввода кода
                    code = input("\nВведите код из Telegram/SMS: ")
                    
                    try:
                        # Пытаемся войти с кодом
                        await client.sign_in(phone, code)
                        print("Авторизация успешна!")
                    except SessionPasswordNeededError:
                        print("\nВключена двухфакторная аутентификация!\n"
                              "Введите пароль двухфакторной аутентификации:")
                        password = input("Пароль: ")
                        await client.sign_in(password=password)
                        print("Авторизация успешна!")
                except FloodWaitError as e:
                    print(f"\nСлишком много попыток входа. Подождите {e.seconds} секунд.")
                    # Вместо повторной попытки, выходим с ошибкой
                    raise
                except Exception as e:
                    print(f"\nОшибка при отправке кода: {str(e)}")
                    raise
            else:
                print("Уже авторизованы!")
            
            return client
                
        except AuthRestartError:
            retry_count += 1
            if retry_count < max_retries:
                print(f"\nОшибка авторизации. Подождите {wait_time} секунд перед следующей попыткой...")
                time.sleep(wait_time)
                wait_time *= 2  # Увеличиваем время ожидания с каждой попыткой
            else:
                raise Exception("Не удалось авторизоваться после нескольких попыток. Попробуйте позже.")
        except Exception as e:
            print(f"Произошла ошибка: {str(e)}")
            raise Exception(f"Ошибка при авторизации: {str(e)}") 