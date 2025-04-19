import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pandas as pd
import os
from telethon.tl.types import Channel, Message
from telethon.errors import FloodWaitError, SessionPasswordNeededError, ApiIdInvalidError

from auth import authenticate_client, get_env_value
from data_collector import collect_telegram_data, process_channel

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.is_user_authorized = AsyncMock(return_value=False)
    client.connect = AsyncMock(return_value=None)
    client.send_code_request = AsyncMock(return_value=MagicMock())
    client.sign_in = AsyncMock(return_value=MagicMock())
    client.iter_dialogs = AsyncMock()
    client.disconnect = AsyncMock(return_value=None)
    return client

@pytest.fixture
def mock_message():
    message = MagicMock(spec=Message)
    message.date = datetime.now()
    message.message = "Test message"
    message.views = 100
    message.forwards = 10
    return message

@pytest.fixture
def mock_channel():
    channel = MagicMock(spec=Channel)
    channel.id = 123456
    channel.title = "Test Channel"
    return channel

@pytest.mark.asyncio
async def test_authenticate_client_success(mock_client):
    """Тест успешной аутентификации клиента"""
    with patch('auth.TelegramClient', return_value=mock_client), \
         patch('builtins.input', side_effect=['12345', 'test_hash', '+79991234567', '12345']), \
         patch('os.getenv', return_value=None):
        try:
            client = await authenticate_client()
            assert client is not None
            assert mock_client.connect.called
            assert mock_client.send_code_request.called
        finally:
            await mock_client.disconnect()

@pytest.mark.asyncio
async def test_authenticate_client_flood_wait(mock_client):
    """Тест обработки ошибки FloodWaitError"""
    error = FloodWaitError(request=None)
    error.seconds = 30
    mock_client.send_code_request.side_effect = error
    
    with patch('auth.TelegramClient', return_value=mock_client), \
         patch('builtins.input', side_effect=['12345', 'test_hash', '+79991234567']), \
         patch('os.getenv', return_value=None):
        try:
            with pytest.raises(Exception):
                await authenticate_client()
        finally:
            await mock_client.disconnect()

@pytest.mark.asyncio
async def test_process_channel_success(mock_client, mock_channel, mock_message):
    """Тест успешной обработки канала"""
    mock_response = MagicMock()
    mock_response.messages = [mock_message]
    mock_client.return_value = mock_response
    
    stats = {
        'university': [],
        'publication_date': [],
        'message': [],
        'views': [],
        'forwards': []
    }
    
    try:
        await process_channel(mock_client, mock_channel, stats, "МГУ")
        
        assert len(stats['university']) == 1
        assert stats['university'][0] == "МГУ"
        assert stats['message'][0] == "Test message"
        assert stats['views'][0] == 100
        assert stats['forwards'][0] == 10
    finally:
        await mock_client.disconnect()

@pytest.mark.asyncio
async def test_collect_telegram_data_empty_channels(mock_client):
    """Тест сбора данных при отсутствии каналов"""
    mock_client.iter_dialogs.return_value = []
    
    try:
        await collect_telegram_data(mock_client)
        
        assert os.path.exists('telegram_stats.csv')
        df = pd.read_csv('telegram_stats.csv')
        assert len(df) == 0
    finally:
        await mock_client.disconnect()

@pytest.mark.asyncio
async def test_collect_telegram_data_with_messages(mock_client, mock_channel, mock_message):
    """Тест сбора данных с реальными сообщениями"""
    mock_client.iter_dialogs.return_value = [mock_channel]
    mock_response = MagicMock()
    mock_response.messages = [mock_message]
    mock_client.return_value = mock_response
    
    try:
        await collect_telegram_data(mock_client)
        
        assert os.path.exists('telegram_stats.csv')
        df = pd.read_csv('telegram_stats.csv')
        assert len(df) > 0
        assert os.path.exists('daily_posts.png')
    finally:
        await mock_client.disconnect()

def test_get_env_value_new_value():
    """Тест получения нового значения из окружения"""
    with patch('os.getenv', return_value=None):
        with patch('builtins.input', return_value='test_value'):
            value = get_env_value('TEST_KEY', 'Enter test value: ')
            assert value == 'test_value'

def test_get_env_value_existing_value():
    """Тест получения существующего значения из окружения"""
    with patch('os.getenv', return_value='existing_value'):
        value = get_env_value('TEST_KEY', 'Enter test value: ')
        assert value == 'existing_value'

@pytest.mark.asyncio
async def test_authenticate_client_2fa(mock_client):
    """Тест аутентификации с двухфакторной аутентификацией"""
    mock_client.sign_in.side_effect = [SessionPasswordNeededError(request=None), MagicMock()]
    
    with patch('auth.TelegramClient', return_value=mock_client), \
         patch('builtins.input', side_effect=['12345', 'test_hash', '+79991234567', '12345', '2fa_password']), \
         patch('os.getenv', return_value=None):
        try:
            client = await authenticate_client()
            assert client is not None
            assert mock_client.sign_in.called
        finally:
            await mock_client.disconnect()

@pytest.mark.asyncio
async def test_process_channel_error_handling(mock_client, mock_channel):
    """Тест обработки ошибок при обработке канала"""
    mock_client.side_effect = Exception("Test error")
    
    stats = {
        'university': [],
        'publication_date': [],
        'message': [],
        'views': [],
        'forwards': []
    }
    
    try:
        await process_channel(mock_client, mock_channel, stats, "МГУ")
        assert len(stats['university']) == 0
    finally:
        await mock_client.disconnect()

@pytest.mark.asyncio
async def test_collect_telegram_data_statistics(mock_client, mock_channel, mock_message):
    """Тест корректности сбора статистики"""
    mock_client.iter_dialogs.return_value = [mock_channel]
    mock_response = MagicMock()
    mock_response.messages = [mock_message]
    mock_client.return_value = mock_response
    
    try:
        await collect_telegram_data(mock_client)
        
        df = pd.read_csv('telegram_stats.csv')
        assert 'university' in df.columns
        assert 'publication_date' in df.columns
        assert 'message' in df.columns
        assert 'views' in df.columns
        assert 'forwards' in df.columns
    finally:
        await mock_client.disconnect() 