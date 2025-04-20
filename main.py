import asyncio
from auth import authenticate_client
from data_collector import collect_telegram_data, create_visualization

async def main():
    try:
        # Аутентификация
        client = await authenticate_client()
        
        try:
            # Сбор данных
            df = await collect_telegram_data(client)
            
            # Создание визуализации, если есть данные
            if df is not None:
                create_visualization(df)
                
        finally:
            # Отключение клиента
            await client.disconnect()
            
    except Exception as e:
        print(f"\nОшибка: {str(e)}\n"
              "\nУбедитесь, что:\n"
              "1. Вы правильно ввели API_ID (должен быть числом)\n"
              "2. Вы правильно ввели API_HASH\n"
              "3. Вы правильно ввели номер телефона в формате +7XXXXXXXXXX\n"
              "4. У вас есть доступ к интернету\n"
              "5. Вы зарегистрировали приложение на https://my.telegram.org\n"
              "\nЕсли проблема сохраняется, попробуйте:\n"
              "1. Подождать несколько минут и запустить скрипт снова\n"
              "2. Проверить подключение к интернету\n"
              "3. Убедиться, что Telegram работает на вашем устройстве")

if __name__ == '__main__':
    asyncio.run(main()) 