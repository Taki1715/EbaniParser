"""
Модуль конфигурации проекта.
Загрузка переменных окружения и базовых параметров.
"""

import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

# Токен бота для админ-панели (aiogram)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# API данные для Telethon (парсер)
API_ID = os.getenv("API_ID", "")
API_HASH = os.getenv("API_HASH", "")

# Session string для Telethon (можно сгенерировать отдельно)
SESSION_STRING = os.getenv("SESSION_STRING", "")

# ID администраторов бота (через запятую)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Путь к базе данных
DATABASE_PATH = os.getenv("DATABASE_PATH", "parser.db")

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

