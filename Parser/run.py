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
from accounts import AccountStore

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


def run_worker_for_account(session_name: str):
    """Запустить парсер для конкретного аккаунта."""
    try:
        logger.info(f"Запуск парсера для сессии: {session_name}")
        asyncio.run(worker.main(session_name))
    except KeyboardInterrupt:
        logger.info("Парсер остановлен")
    except Exception as e:
        logger.error(f"Ошибка в парсере {session_name}: {e}")


def main():
    """Главная функция запуска обоих процессов."""
    logger.info("="*50)
    logger.info("Запуск Telegram-парсера лидов")
    logger.info("="*50)
    
    # Создаем процессы
    bot_process = Process(target=run_bot, name="AdminBot")
    # Один процесс бота + N процессов парсеров по активным аккаунтам
    active_accounts = AccountStore.active_accounts()
    worker_processes = [Process(target=run_worker_for_account, args=(a.get("session_file") or 'parser_session',), name=f"Parser-{a.get('id')}") for a in active_accounts]
    
    # Обработчик сигнала завершения
    def signal_handler(sig, frame):
        logger.info("\n\nПолучен сигнал остановки. Завершение работы...")
        bot_process.terminate()
        for p in worker_processes:
            p.terminate()
        bot_process.join()
        for p in worker_processes:
            p.join()
        logger.info("Все процессы остановлены")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Запускаем оба процесса
        logger.info("Запуск админ-панели...")
        bot_process.start()
        
        if not active_accounts:
            logger.info("Активных аккаунтов нет. Откройте 'Мои аккаунты' в боте и включите нужные.")
        else:
            for p in worker_processes:
                logger.info(f"Запуск парсера процесса: {p.name}")
                p.start()
        
        logger.info("\n" + "="*50)
        logger.info("Все сервисы запущены!")
        logger.info("Для остановки нажмите Ctrl+C")
        logger.info("="*50 + "\n")
        
        # Ожидаем завершения процессов
        bot_process.join()
        for p in worker_processes:
            p.join()
        
    except KeyboardInterrupt:
        logger.info("\n\nОстановка всех сервисов...")
        bot_process.terminate()
        for p in worker_processes:
            p.terminate()
        bot_process.join()
        for p in worker_processes:
            p.join()
        logger.info("Все сервисы остановлены")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        bot_process.terminate()
        for p in worker_processes:
            p.terminate()
        bot_process.join()
        for p in worker_processes:
            p.join()


if __name__ == "__main__":
    main()

