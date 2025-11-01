"""
Скрипт для генерации session string для Telethon.
Используйте этот скрипт, если хотите создать SESSION_STRING для .env файла.
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# Введите ваши данные
API_ID = input("Введите API_ID: ")
API_HASH = input("Введите API_HASH: ")

async def main():
    """Генерация session string."""
    # Создаем клиент с пустой строкой сессии
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        print("\n" + "="*50)
        print("Ваш SESSION_STRING:")
        print("="*50)
        print(client.session.save())
        print("="*50)
        print("\nСкопируйте строку выше и вставьте в .env файл")
        print("в переменную SESSION_STRING\n")

if __name__ == "__main__":
    print("="*50)
    print("Генератор SESSION_STRING для Telethon")
    print("="*50)
    print("\nВам понадобится:")
    print("1. API_ID и API_HASH (получить на https://my.telegram.org)")
    print("2. Номер телефона технического аккаунта")
    print("3. Код подтверждения из Telegram")
    print("4. Пароль 2FA (если включен)\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nОперация отменена пользователем")
    except Exception as e:
        print(f"\n\nОшибка: {e}")

