@echo off
REM Скрипт для быстрого запуска парсера на Windows

echo ================================================
echo Telegram Lead Parser - Запуск
echo ================================================
echo.

REM Проверка наличия .env файла
if not exist ".env" (
    echo [ОШИБКА] Файл .env не найден!
    echo.
    echo Создайте файл .env на основе env.example:
    echo   copy env.example .env
    echo.
    echo Затем заполните необходимые данные в .env
    pause
    exit /b 1
)

REM Проверка наличия виртуального окружения
if not exist "venv" (
    echo Виртуальное окружение не найдено.
    echo Создание виртуального окружения...
    python -m venv venv
    echo.
)

REM Активация виртуального окружения
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo Проверка зависимостей...
pip install -r requirements.txt --quiet

echo.
echo ================================================
echo Запуск парсера...
echo ================================================
echo.
echo Для остановки нажмите Ctrl+C
echo.

REM Запуск
python run.py

pause

