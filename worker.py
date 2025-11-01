"""
Worker - парсер сообщений на Telethon.
Слушает группы, каналы и диалоги, фильтрует по ключевым словам.
"""

import asyncio
import logging
import re
from typing import List, Optional

from telethon import TelegramClient, events
from telethon.tl.types import User, Channel, Chat
from telethon.sessions import StringSession

import config
from database import Database

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database(config.DATABASE_PATH)


class MessageFilter:
    """Класс для фильтрации сообщений по ключевым словам и стоп-словам."""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Нормализовать текст для поиска.
        
        Args:
            text: Исходный текст
            
        Returns:
            Нормализованный текст
        """
        return text.lower().strip()
    
    @staticmethod
    def check_keyword(text: str, keyword: str) -> bool:
        """
        Проверить наличие ключевого слова в тексте.
        
        Поддерживает:
        - _слово_ - поиск слова как отдельного
        - слово1+слово2 - все слова должны присутствовать
        - обычное слово - поиск подстроки
        
        Args:
            text: Текст для проверки
            keyword: Ключевое слово с возможными модификаторами
            
        Returns:
            True если ключевое слово найдено
        """
        text = MessageFilter.normalize_text(text)
        keyword = keyword.strip()
        
        # Проверка на комбинацию слов (слово1+слово2)
        if '+' in keyword:
            words = [MessageFilter.normalize_text(w) for w in keyword.split('+')]
            return all(word in text for word in words)
        
        # Проверка на точное слово (_слово_)
        if keyword.startswith('_') and keyword.endswith('_'):
            word = MessageFilter.normalize_text(keyword[1:-1])
            # Поиск слова с границами
            pattern = r'\b' + re.escape(word) + r'\b'
            return bool(re.search(pattern, text, re.IGNORECASE))
        
        # Обычный поиск подстроки
        keyword_normalized = MessageFilter.normalize_text(keyword)
        return keyword_normalized in text
    
    @staticmethod
    def check_keywords(text: str, keywords: List[str]) -> bool:
        """
        Проверить, содержит ли текст хотя бы одно ключевое слово.
        
        Args:
            text: Текст для проверки
            keywords: Список ключевых слов
            
        Returns:
            True если найдено хотя бы одно ключевое слово
        """
        if not keywords:
            return False
        
        for keyword in keywords:
            if MessageFilter.check_keyword(text, keyword):
                return True
        
        return False
    
    @staticmethod
    def check_stopwords(text: str, stopwords: List[str]) -> bool:
        """
        Проверить, содержит ли текст стоп-слова.
        
        Args:
            text: Текст для проверки
            stopwords: Список стоп-слов
            
        Returns:
            True если найдено стоп-слово
        """
        if not stopwords:
            return False
        
        for stopword in stopwords:
            if MessageFilter.check_keyword(text, stopword):
                return True
        
        return False


class TelegramParser:
    """Класс для парсинга сообщений из Telegram."""
    
    def __init__(self):
        """Инициализация парсера."""
        self.client: Optional[TelegramClient] = None
        self.bot_client: Optional[TelegramClient] = None
        self.me = None
    
    async def init_client(self):
        """Инициализировать Telegram клиент."""
        try:
            # Основной клиент для парсинга (user-mode)
            if config.SESSION_STRING:
                self.client = TelegramClient(
                    StringSession(config.SESSION_STRING),
                    config.API_ID,
                    config.API_HASH
                )
            else:
                # Если нет session string, создаем обычную сессию
                self.client = TelegramClient(
                    'parser_session',
                    config.API_ID,
                    config.API_HASH
                )
            
            await self.client.start()
            self.me = await self.client.get_me()
            logger.info(f"Клиент подключен: {self.me.phone if self.me else 'Unknown'}")
            
            # Клиент-бот для отправки уведомлений
            if config.BOT_TOKEN:
                self.bot_client = await TelegramClient(
                    'bot_session',
                    config.API_ID,
                    config.API_HASH
                ).start(bot_token=config.BOT_TOKEN)
                logger.info("Бот-клиент подключен для отправки уведомлений")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации клиента: {e}")
            raise
    
    async def should_process_message(self, event) -> bool:
        """
        Проверить, нужно ли обрабатывать сообщение.
        
        Args:
            event: Событие нового сообщения
            
        Returns:
            True если сообщение нужно обработать
        """
        # Получаем конфиг
        conf = db.get_all_config()
        
        # Проверка, включен ли парсер
        if conf.get('working_status') != 'true':
            return False
        
        # Проверка на бота
        sender = await event.get_sender()
        if sender and getattr(sender, 'bot', False):
            logger.debug("Пропуск сообщения от бота")
            return False
        
        # Проверка типа чата
        chat = await event.get_chat()
        
        if isinstance(chat, Channel):
            # Канал
            if chat.broadcast:
                if conf.get('channels_enabled') != 'true':
                    return False
            # Супергруппа
            else:
                if conf.get('groups_enabled') != 'true':
                    return False
        elif isinstance(chat, Chat):
            # Обычная группа
            if conf.get('groups_enabled') != 'true':
                return False
        elif isinstance(chat, User):
            # Личный диалог
            if conf.get('dialogs_enabled') != 'true':
                return False
        
        return True
    
    async def filter_message(self, text: str, sender_id: int) -> tuple[bool, str]:
        """
        Фильтровать сообщение по ключевым словам и правилам.
        
        Args:
            text: Текст сообщения
            sender_id: ID отправителя
            
        Returns:
            Tuple (should_forward, reason)
        """
        if not text:
            return False, "Пустое сообщение"
        
        # Проверка черного списка
        if db.is_blacklisted(sender_id):
            logger.debug(f"Отправитель {sender_id} в черном списке")
            return False, "Отправитель в черном списке"
        
        # Получаем ключевые слова и стоп-слова
        keywords = db.get_keywords()
        stopwords = db.get_stopwords()
        
        # Проверка ключевых слов
        if not MessageFilter.check_keywords(text, keywords):
            logger.debug("Ключевые слова не найдены")
            return False, "Ключевые слова не найдены"
        
        # Проверка стоп-слов
        if MessageFilter.check_stopwords(text, stopwords):
            logger.debug("Найдены стоп-слова")
            return False, "Найдены стоп-слова"
        
        # Проверка дубликатов
        conf = db.get_all_config()
        if conf.get('ignore_duplicates') == 'true':
            if db.check_duplicate(text, hours=24):
                logger.debug("Дубликат сообщения")
                return False, "Дубликат"
        
        return True, "Прошел фильтры"
    
    async def send_lead_notification(self, event, reason: str = ""):
        """
        Отправить уведомление о новом лиде.
        
        Args:
            event: Событие сообщения
            reason: Причина выбора (опционально)
        """
        try:
            conf = db.get_all_config()
            notification_chat_id = conf.get('notification_chat_id', '')
            
            if not notification_chat_id:
                logger.warning("ID чата для уведомлений не установлен")
                return
            
            # Получаем информацию о сообщении
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            sender_id = sender.id if sender else 0
            chat_title = getattr(chat, 'title', getattr(chat, 'first_name', 'Неизвестно'))
            chat_id = event.chat_id
            message_id = event.message.id
            text = event.message.text or "[медиа]"
            
            # Создаем ссылку на сообщение
            if hasattr(chat, 'username') and chat.username:
                message_link = f"https://t.me/{chat.username}/{message_id}"
            else:
                # Для приватных чатов/групп
                message_link = f"https://t.me/c/{str(chat_id)[4:]}/{message_id}"
            
            # Формируем текст уведомления
            notification_text = (
                "🔥 <b>Новое сообщение</b>\n\n"
                f"ID пользователя: <code>{sender_id}</code>\n"
                f"Сообщение переслано из чата: <b>{chat_title}</b>\n"
                f"ID чата: <code>{chat_id}</code>\n"
                f"<a href=\"{message_link}\">Ссылка на сообщение</a>\n\n"
            )
            
            # Отправляем уведомление
            notification_chat_id_int = int(notification_chat_id)
            
            # Отправляем текст уведомления
            if self.bot_client:
                await self.bot_client.send_message(
                    notification_chat_id_int,
                    notification_text,
                    parse_mode='html',
                    link_preview=False
                )
            else:
                await self.client.send_message(
                    notification_chat_id_int,
                    notification_text,
                    parse_mode='html',
                    link_preview=False
                )
            
            # Пересылаем оригинальное сообщение
            await self.client.forward_messages(
                notification_chat_id_int,
                event.message
            )
            
            # Сохраняем в историю
            db.add_log(
                source_chat=chat_title,
                message_id=message_id,
                text=text,
                user_id=sender_id,
                chat_id=chat_id
            )
            
            logger.info(f"Лид отправлен: {chat_title} - {sender_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
    
    async def handle_new_message(self, event):
        """
        Обработать новое сообщение.
        
        Args:
            event: Событие нового сообщения
        """
        try:
            # Проверяем, нужно ли обрабатывать
            if not await self.should_process_message(event):
                return
            
            # Получаем текст и отправителя
            text = event.message.text
            if not text:
                return
            
            sender = await event.get_sender()
            sender_id = sender.id if sender else 0
            
            # Фильтруем сообщение
            should_forward, reason = await self.filter_message(text, sender_id)
            
            if should_forward:
                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', getattr(chat, 'first_name', 'Неизвестно'))
                logger.info(f"Найден лид в {chat_title}: {text[:50]}...")
                
                # Отправляем уведомление
                await self.send_lead_notification(event, reason)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
    
    async def start(self):
        """Запустить парсер."""
        logger.info("Запуск парсера...")
        
        # Инициализируем клиент
        await self.init_client()
        
        # Регистрируем обработчик новых сообщений
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            await self.handle_new_message(event)
        
        logger.info("Парсер запущен и слушает сообщения")
        
        # Запускаем клиент
        await self.client.run_until_disconnected()
    
    async def stop(self):
        """Остановить парсер."""
        logger.info("Остановка парсера...")
        
        if self.client:
            await self.client.disconnect()
        
        if self.bot_client:
            await self.bot_client.disconnect()
        
        logger.info("Парсер остановлен")


async def main():
    """Главная функция."""
    parser = TelegramParser()
    
    try:
        await parser.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await parser.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Парсер остановлен пользователем")

