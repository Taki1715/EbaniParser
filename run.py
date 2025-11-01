"""
Скрипт для одновременного запуска бота и парсера.
Удобно для продакшн использования.
"""

import asyncio
import logging
import signal
import sys
from multiprocessing import Process

import bot
import worker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_bot():
    """Запустить админ-панель (бота)."""
    try:
        logger.info("Запуск админ-панели...")
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        logger.info("Админ-панель остановлена")
    except Exception as e:
        logger.error(f"Ошибка в админ-панели: {e}")


def run_worker():
    """Запустить парсер."""
    try:
        logger.info("Запуск парсера...")
        asyncio.run(worker.main())
    except KeyboardInterrupt:
        logger.info("Парсер остановлен")
    except Exception as e:
        logger.error(f"Ошибка в парсере: {e}")


def main():
    """Главная функция запуска обоих процессов."""
    logger.info("="*50)
    logger.info("Запуск Telegram-парсера лидов")
    logger.info("="*50)
    
    # Создаем процессы
    bot_process = Process(target=run_bot, name="AdminBot")
    worker_process = Process(target=run_worker, name="Parser")
    
    # Обработчик сигнала завершения
    def signal_handler(sig, frame):
        logger.info("\n\nПолучен сигнал остановки. Завершение работы...")
        bot_process.terminate()
        worker_process.terminate()
        bot_process.join()
        worker_process.join()
        logger.info("Все процессы остановлены")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Запускаем оба процесса
        logger.info("Запуск админ-панели...")
        bot_process.start()
        
        logger.info("Запуск парсера...")
        worker_process.start()
        
        logger.info("\n" + "="*50)
        logger.info("Все сервисы запущены!")
        logger.info("Для остановки нажмите Ctrl+C")
        logger.info("="*50 + "\n")
        
        # Ожидаем завершения процессов
        bot_process.join()
        worker_process.join()
        
    except KeyboardInterrupt:
        logger.info("\n\nОстановка всех сервисов...")
        bot_process.terminate()
        worker_process.terminate()
        bot_process.join()
        worker_process.join()
        logger.info("Все сервисы остановлены")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        bot_process.terminate()
        worker_process.terminate()
        bot_process.join()
        worker_process.join()


if __name__ == "__main__":
    main()

