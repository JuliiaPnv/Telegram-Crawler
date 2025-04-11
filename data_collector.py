from telethon.tl.functions.messages import GetHistoryRequest
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

async def process_channel(client, channel, stats, university):
    """Обработка канала и сбор статистики"""
    try:
        print(f"Собираем сообщения из {channel.title if hasattr(channel, 'title') else channel.name}...")
        # Получение сообщений за последние 30 дней
        messages = await client(GetHistoryRequest(
            peer=channel.id,
            offset_id=0,
            offset_date=datetime.now() - timedelta(days=30),
            add_offset=0,
            limit=100,
            max_id=0,
            min_id=0,
            hash=0
        ))
        
        print(f"Найдено {len(messages.messages)} сообщений")
        # Сбор статистики
        for message in messages.messages:
            stats['university'].append(university)
            stats['publication_date'].append(message.date)
            stats['message'].append(message.message)
            stats['views'].append(getattr(message, 'views', 0))
            stats['forwards'].append(getattr(message, 'forwards', 0))
    except Exception as e:
        print(f"Ошибка при обработке канала: {str(e)}")

async def collect_telegram_data(client):
    """Сбор данных из Telegram"""
    # Словарь с альтернативными названиями университетов
    universities = {
        'МГУ': [
            'МГУ',
            'Московский государственный университет',
            'МГУ им. Ломоносова',
            'Московский университет',
            'MSU',
            'Lomonosov Moscow State University'
        ],
        'СПбГУ': [
            'СПбГУ',
            'Санкт-Петербургский государственный университет',
            'Санкт-Петербургский университет',
            'СПб университет',
            'SPbU',
            'Saint Petersburg State University'
        ]
    }
    
    try:
        # Словарь для хранения статистики
        stats = {
            'university': [],
            'publication_date': [],
            'message': [],
            'views': [],
            'forwards': []
        }
        
        print("\nНачинаем поиск каналов и групп...")
        # Поиск каналов и групп
        for university, names in universities.items():
            print(f"\nИщем каналы и группы для {university}...")
            print(f"Варианты поиска: {', '.join(names)}")
            
            # Поиск каналов
            async for dialog in client.iter_dialogs():
                dialog_name = dialog.name.lower()
                # Проверяем все варианты названия университета
                if any(name.lower() in dialog_name for name in names):
                    print(f"Найден канал/группа: {dialog.name}")
                    await process_channel(client, dialog, stats, university)
        
        # Создание DataFrame
        df = pd.DataFrame(stats)
        
        # Сохранение данных в CSV
        df.to_csv('telegram_stats.csv', index=False)
        
        # Построение графика публикаций по дням
        df['date'] = pd.to_datetime(df['publication_date']).dt.date
        daily_posts = df.groupby(['university', 'date']).size().unstack(level=0)
        
        plt.figure(figsize=(15, 8))
        daily_posts.plot(kind='line', marker='o', linewidth=2, markersize=5)
        plt.title('Количество публикаций по дням', fontsize=14, pad=20)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Количество публикаций', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(title='Университет', fontsize=10)
        
        # Настройка формата дат на оси X
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d.%m.%Y'))
        plt.gcf().autofmt_xdate()  # Автоматический поворот дат для лучшей читаемости
        
        plt.tight_layout()  # Автоматическая настройка отступов
        plt.savefig('daily_posts.png', dpi=300, bbox_inches='tight')  # Сохраняем с высоким разрешением
        
        # Вывод общей статистики
        print("\nОбщая статистика:\n"
              f"Всего публикаций: {len(df)}\n"
              f"Количество уникальных каналов/групп: {df['university'].nunique()}\n"
              f"Среднее количество просмотров: {df['views'].mean():.2f}\n"
              f"Среднее количество репостов: {df['forwards'].mean():.2f}")
        
    except Exception as e:
        print(f"Ошибка при сборе данных: {str(e)}")
        raise 