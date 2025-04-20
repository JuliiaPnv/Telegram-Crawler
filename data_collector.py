from telethon.tl.functions.messages import GetHistoryRequest
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
from asyncio import iscoroutine
import pytz
import os

async def process_channel(client, channel):
    """Обработка одного канала/группы"""
    try:
        print(f"\nОбработка {channel.title}...")
        stats = []
        
        # Устанавливаем московскую временную зону
        moscow_tz = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(moscow_tz)
        offset_date = current_time - timedelta(days=30)
        
        # Получаем сообщения за последние 30 дней
        async for message in client.iter_messages(channel, offset_date=offset_date):
            if message.text:  # Пропускаем сообщения без текста
                # Конвертируем время в московское
                message_time = message.date.astimezone(moscow_tz)
                stats.append({
                    'university': channel.title,
                    'publication_date': message_time,
                    'message': message.text,
                    'views': message.views or 0,
                    'forwards': message.forwards or 0
                })
        
        print(f"Найдено {len(stats)} сообщений")
        return stats
    except Exception as e:
        print(f"Ошибка при обработке канала {channel.title}: {str(e)}")
        return []

async def collect_telegram_data(client):
    """Сбор данных из Telegram"""
    try:
        # Словарь с альтернативными названиями университетов
        universities = {
            'МГУ': [
                'мгу',
                'московский государственный университет',
                'мгу им. ломоносова',
                'московский университет',
                'msu',
                'lomonosov moscow state university'
            ],
            'СПбГУ': [
                'спбгу',
                'санкт-петербургский государственный университет',
                'санкт-петербургский университет',
                'спб университет',
                'spbu',
                'saint petersburg state university'
            ]
        }
        
        print("\nНачинаем поиск каналов и групп...")
        stats = []
        
        # Поиск каналов и групп
        async for dialog in client.iter_dialogs():
            dialog_title = dialog.title.lower() if hasattr(dialog, 'title') else dialog.name.lower()
            
            # Проверяем, относится ли канал к одному из университетов
            for uni, keywords in universities.items():
                if any(keyword in dialog_title for keyword in keywords):
                    print(f"Найден канал/группа: {dialog.title if hasattr(dialog, 'title') else dialog.name}")
                    channel_stats = await process_channel(client, dialog)
                    stats.extend(channel_stats)
                    break  # Если нашли совпадение, переходим к следующему каналу
        
        # Создание DataFrame
        if stats:
            df = pd.DataFrame(stats)
            try:
                df.to_csv('telegram_stats.csv', index=False)
                print("\nДанные успешно сохранены в telegram_stats.csv")
            except PermissionError:
                print("\nОшибка: Невозможно сохранить файл telegram_stats.csv. Возможно, он открыт в другой программе.")
                return None
            except Exception as e:
                print(f"\nОшибка при сохранении данных в CSV: {str(e)}")
                return None
            return df
        else:
            print("\nНе найдено сообщений для анализа")
            return None
    except Exception as e:
        print(f"Ошибка при сборе данных: {str(e)}")
        return None

def create_visualization(df):
    """Создание визуализации данных"""
    if df is None or df.empty:
        print("Нет данных для построения графика")
        return
    
    try:
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
        
        try:
            plt.savefig('daily_posts.png', dpi=300, bbox_inches='tight')
            print("\nГрафик сохранен в daily_posts.png")
        except PermissionError:
            print("\nОшибка: Невозможно сохранить файл daily_posts.png. Возможно, он открыт в другой программе.")
        except Exception as e:
            print(f"\nОшибка при сохранении графика: {str(e)}")
        
        # Вывод общей статистики
        try:
            print("\nОбщая статистика:\n"
                  f"Всего публикаций: {len(df)}\n"
                  f"Количество уникальных каналов/групп: {df['university'].nunique()}\n"
                  f"Среднее количество просмотров: {df['views'].mean():.2f}\n"
                  f"Среднее количество репостов: {df['forwards'].mean():.2f}")
        except Exception as e:
            print(f"\nОшибка при подсчете статистики: {str(e)}")
            
    except Exception as e:
        print(f"\nОшибка при создании визуализации: {str(e)}\n"
              "Проверьте, что:\n"
              "1. Данные содержат правильные значения\n"
              "2. Достаточно свободного места на диске\n"
              "3. У программы есть права на запись в текущую директорию") 