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
    client.iter_messages = AsyncMock()
    client.disconnect = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_message():
    message = MagicMock(spec=Message)
    message.date = datetime.now()
    message.text = "Test message"
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
    # Настраиваем асинхронный итератор для iter_messages
    async def async_message_iterator():
        yield mock_message
    mock_client.iter_messages.return_value = async_message_iterator()

    try:
        result = await process_channel(mock_client, mock_channel)
        
        assert len(result) == 1
        assert result[0]['university'] == mock_channel.title
        assert result[0]['message'] == mock_message.text
        assert result[0]['views'] == mock_message.views
        assert result[0]['forwards'] == mock_message.forwards
    finally:
        await mock_client.disconnect()


@pytest.mark.asyncio
async def test_collect_telegram_data_empty_channels(mock_client):
    """Тест сбора данных при отсутствии каналов"""
    # Настраиваем асинхронный итератор для пустого списка диалогов
    async def async_dialog_iterator():
        for _ in []:
            yield _
    mock_client.iter_dialogs.return_value = async_dialog_iterator()

    try:
        result = await collect_telegram_data(mock_client)
        assert result is None
    finally:
        await mock_client.disconnect()


@pytest.mark.asyncio
async def test_collect_telegram_data_with_messages(mock_client, mock_channel, mock_message):
    """Тест сбора данных с реальными сообщениями"""
    # Настраиваем асинхронные итераторы
    async def async_dialog_iterator():
        yield mock_channel
    mock_client.iter_dialogs.return_value = async_dialog_iterator()
    
    async def async_message_iterator():
        yield mock_message
    mock_client.iter_messages.return_value = async_message_iterator()

    try:
        result = await collect_telegram_data(mock_client)
        assert result is not None
        assert len(result) > 0
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
    mock_client.iter_messages.side_effect = Exception("Test error")

    try:
        result = await process_channel(mock_client, mock_channel)
        assert len(result) == 0
    finally:
        await mock_client.disconnect()


@pytest.mark.asyncio
async def test_collect_telegram_data_statistics(mock_client, mock_channel, mock_message):
    """Тест корректности сбора статистики"""
    # Настраиваем асинхронные итераторы
    async def async_dialog_iterator():
        yield mock_channel
    mock_client.iter_dialogs.return_value = async_dialog_iterator()
    
    async def async_message_iterator():
        yield mock_message
    mock_client.iter_messages.return_value = async_message_iterator()

    try:
        result = await collect_telegram_data(mock_client)
        assert result is not None
        assert 'university' in result.columns
        assert 'publication_date' in result.columns
        assert 'message' in result.columns
        assert 'views' in result.columns
        assert 'forwards' in result.columns
    finally:
        await mock_client.disconnect() 