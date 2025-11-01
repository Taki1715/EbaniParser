"""
Модуль для работы с базой данных SQLite.
Управляет ключевыми словами, стоп-словами, черным списком, конфигом и историей лидов.
"""

import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime


logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с SQLite базой данных."""
    
    def __init__(self, db_path: str = "parser.db"):
        """
        Инициализация базы данных.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self) -> sqlite3.Connection:
        """Создать подключение к базе данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Создать все необходимые таблицы."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица ключевых слов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица стоп-слов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stopwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица черного списка
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица конфигурации
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL
            )
        """)
        
        # Таблица истории лидов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_chat TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                text TEXT,
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                chat_id INTEGER
            )
        """)
        
        # Таблица источников (для будущего функционала)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Инициализация конфига по умолчанию
        default_configs = {
            'working_status': 'false',
            'groups_enabled': 'true',
            'channels_enabled': 'true',
            'dialogs_enabled': 'false',
            'ignore_duplicates': 'true',
            'notification_chat_id': ''
        }
        
        for key, value in default_configs.items():
            cursor.execute("""
                INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)
            """, (key, value))
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    
    # ==================== КЛЮЧЕВЫЕ СЛОВА ====================
    
    def add_keyword(self, text: str) -> bool:
        """
        Добавить ключевое слово.
        
        Args:
            text: Текст ключевого слова
            
        Returns:
            True если добавлено успешно, False если уже существует
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO keywords (text) VALUES (?)", (text.strip(),))
            conn.commit()
            conn.close()
            logger.info(f"Добавлено ключевое слово: {text}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Ключевое слово уже существует: {text}")
            return False
    
    def remove_keyword(self, text: str) -> bool:
        """
        Удалить ключевое слово.
        
        Args:
            text: Текст ключевого слова
            
        Returns:
            True если удалено успешно
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM keywords WHERE text = ?", (text,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Удалено ключевое слово: {text}")
        return affected > 0
    
    def get_keywords(self, sort_alpha: bool = False) -> List[str]:
        """
        Получить список всех ключевых слов.
        
        Args:
            sort_alpha: Сортировать по алфавиту
            
        Returns:
            Список ключевых слов
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if sort_alpha:
            cursor.execute("SELECT text FROM keywords ORDER BY text COLLATE NOCASE")
        else:
            cursor.execute("SELECT text FROM keywords ORDER BY created_at DESC")
        
        keywords = [row['text'] for row in cursor.fetchall()]
        conn.close()
        return keywords
    
    def clear_keywords(self):
        """Удалить все ключевые слова."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM keywords")
        conn.commit()
        conn.close()
        logger.info("Все ключевые слова удалены")
    
    # ==================== СТОП-СЛОВА ====================
    
    def add_stopword(self, text: str) -> bool:
        """
        Добавить стоп-слово.
        
        Args:
            text: Текст стоп-слова
            
        Returns:
            True если добавлено успешно, False если уже существует
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO stopwords (text) VALUES (?)", (text.strip(),))
            conn.commit()
            conn.close()
            logger.info(f"Добавлено стоп-слово: {text}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Стоп-слово уже существует: {text}")
            return False
    
    def remove_stopword(self, text: str) -> bool:
        """
        Удалить стоп-слово.
        
        Args:
            text: Текст стоп-слова
            
        Returns:
            True если удалено успешно
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stopwords WHERE text = ?", (text,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Удалено стоп-слово: {text}")
        return affected > 0
    
    def get_stopwords(self, sort_alpha: bool = False) -> List[str]:
        """
        Получить список всех стоп-слов.
        
        Args:
            sort_alpha: Сортировать по алфавиту
            
        Returns:
            Список стоп-слов
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if sort_alpha:
            cursor.execute("SELECT text FROM stopwords ORDER BY text COLLATE NOCASE")
        else:
            cursor.execute("SELECT text FROM stopwords ORDER BY created_at DESC")
        
        stopwords = [row['text'] for row in cursor.fetchall()]
        conn.close()
        return stopwords
    
    def clear_stopwords(self):
        """Удалить все стоп-слова."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stopwords")
        conn.commit()
        conn.close()
        logger.info("Все стоп-слова удалены")
    
    # ==================== ЧЕРНЫЙ СПИСОК ====================
    
    def add_to_blacklist(self, user_id: int) -> bool:
        """
        Добавить пользователя в черный список.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            True если добавлено успешно, False если уже существует
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO blacklist (user_id) VALUES (?)", (user_id,))
            conn.commit()
            conn.close()
            logger.info(f"Добавлен в черный список: {user_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Пользователь уже в черном списке: {user_id}")
            return False
    
    def remove_from_blacklist(self, user_id: int) -> bool:
        """
        Удалить пользователя из черного списка.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            True если удалено успешно
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Удален из черного списка: {user_id}")
        return affected > 0
    
    def get_blacklist(self, sort_numeric: bool = False) -> List[int]:
        """
        Получить список всех пользователей в черном списке.
        
        Args:
            sort_numeric: Сортировать по числовому значению
            
        Returns:
            Список ID пользователей
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if sort_numeric:
            cursor.execute("SELECT user_id FROM blacklist ORDER BY user_id")
        else:
            cursor.execute("SELECT user_id FROM blacklist ORDER BY created_at DESC")
        
        blacklist = [row['user_id'] for row in cursor.fetchall()]
        conn.close()
        return blacklist
    
    def clear_blacklist(self):
        """Удалить всех пользователей из черного списка."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blacklist")
        conn.commit()
        conn.close()
        logger.info("Черный список очищен")
    
    def is_blacklisted(self, user_id: int) -> bool:
        """
        Проверить, находится ли пользователь в черном списке.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            True если в черном списке
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM blacklist WHERE user_id = ?", (user_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    # ==================== КОНФИГУРАЦИЯ ====================
    
    def set_config(self, key: str, value: str):
        """
        Установить значение конфига.
        
        Args:
            key: Ключ конфига
            value: Значение конфига
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
        """, (key, value))
        conn.commit()
        conn.close()
        logger.info(f"Конфиг обновлен: {key} = {value}")
    
    def get_config(self, key: str, default: str = '') -> str:
        """
        Получить значение конфига.
        
        Args:
            key: Ключ конфига
            default: Значение по умолчанию
            
        Returns:
            Значение конфига
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row['value']
        return default
    
    def get_all_config(self) -> Dict[str, str]:
        """
        Получить все настройки конфига.
        
        Returns:
            Словарь с настройками
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM config")
        config = {row['key']: row['value'] for row in cursor.fetchall()}
        conn.close()
        return config
    
    def toggle_config(self, key: str) -> str:
        """
        Переключить булево значение конфига (true/false).
        
        Args:
            key: Ключ конфига
            
        Returns:
            Новое значение ('true' или 'false')
        """
        current = self.get_config(key, 'false')
        new_value = 'false' if current == 'true' else 'true'
        self.set_config(key, new_value)
        return new_value
    
    # ==================== ИСТОРИЯ ЛИДОВ ====================
    
    def add_log(self, source_chat: str, message_id: int, text: str, 
                user_id: int, chat_id: int):
        """
        Добавить запись в историю лидов.
        
        Args:
            source_chat: Название чата-источника
            message_id: ID сообщения
            text: Текст сообщения
            user_id: ID автора
            chat_id: ID чата
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (source_chat, message_id, text, user_id, chat_id)
            VALUES (?, ?, ?, ?, ?)
        """, (source_chat, message_id, text, user_id, chat_id))
        conn.commit()
        conn.close()
        logger.info(f"Добавлен лог: {source_chat} - {message_id}")
    
    def get_recent_logs(self, limit: int = 10) -> List[Dict]:
        """
        Получить последние записи из истории лидов.
        
        Args:
            limit: Количество записей
            
        Returns:
            Список словарей с данными лидов
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs
    
    def check_duplicate(self, text: str, hours: int = 24) -> bool:
        """
        Проверить, есть ли дубликат сообщения за последние N часов.
        
        Args:
            text: Текст сообщения
            hours: Количество часов для проверки
            
        Returns:
            True если дубликат найден
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM logs 
            WHERE text = ? 
            AND datetime(timestamp) > datetime('now', '-{} hours')
            LIMIT 1
        """.format(hours), (text,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    # ==================== ИСТОЧНИКИ (для будущего) ====================
    
    def add_source(self, title: str, link: str) -> bool:
        """
        Добавить источник для парсинга.
        
        Args:
            title: Название источника
            link: Ссылка на источник
            
        Returns:
            True если добавлено успешно
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sources (title, link) VALUES (?, ?)
            """, (title, link))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_sources(self) -> List[Dict]:
        """
        Получить список всех источников.
        
        Returns:
            Список словарей с данными источников
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sources ORDER BY created_at DESC")
        sources = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return sources

