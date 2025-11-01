"""
Telegram бот - админ-панель для управления парсером.
Использует aiogram 3.x для создания интерфейса.
"""

import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import config
from database import Database
from accounts import AccountStore

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
db = Database(config.DATABASE_PATH)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
router = Router()


# ==================== СОСТОЯНИЯ ====================

class Form(StatesGroup):
    """Состояния для FSM."""
    waiting_keyword = State()
    waiting_stopword = State()
    waiting_blacklist_id = State()
    waiting_chat_id = State()


# ==================== КЛАВИАТУРЫ ====================

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню."""
    keyboard = [
        [InlineKeyboardButton(text="👤 Мои аккаунты", callback_data="accounts")],
        [InlineKeyboardButton(text="📊 Парсер / Лидогенератор", callback_data="parser_settings")],
        [InlineKeyboardButton(text="📜 История лидов", callback_data="lead_history")],
        [InlineKeyboardButton(text="📥 Импорт источников", callback_data="import_sources")],
        [InlineKeyboardButton(text="📤 Исходящие сообщения", callback_data="outbox")],
        [InlineKeyboardButton(text="❓ Помощь / Инструкция", callback_data="help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def parser_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек парсера."""
    conf = db.get_all_config()
    
    # Статусы (эмодзи)
    working = "🟢" if conf.get('working_status') == 'true' else "🔴"
    groups = "🟢" if conf.get('groups_enabled') == 'true' else "🔴"
    channels = "🟢" if conf.get('channels_enabled') == 'true' else "🔴"
    dialogs = "🟢" if conf.get('dialogs_enabled') == 'true' else "🔴"
    duplicates = "🟢" if conf.get('ignore_duplicates') == 'true' else "🔴"
    
    keyboard = [
        # Статус работы
        [InlineKeyboardButton(text=f"{working} Работает", callback_data="toggle_working")],
        [InlineKeyboardButton(text=f"{groups} Группы", callback_data="toggle_groups"),
         InlineKeyboardButton(text=f"{channels} Каналы", callback_data="toggle_channels")],
        [InlineKeyboardButton(text=f"{dialogs} Диалоги (в будущем)", callback_data="toggle_dialogs"),
         InlineKeyboardButton(text=f"{duplicates} Игнор дублей", callback_data="toggle_duplicates")],
        # Фильтры
        [InlineKeyboardButton(text="🔑 Ключ-слова", callback_data="keywords")],
        [InlineKeyboardButton(text="⛔ Стоп-слова", callback_data="stopwords")],
        [InlineKeyboardButton(text="🚫 Чёрный список", callback_data="blacklist")],
        # Доставка
        [InlineKeyboardButton(text="📢 Чат для уведомлений", callback_data="notification_chat")],
        # Навигация
        [InlineKeyboardButton(text="⬅ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def keywords_keyboard(page: int = 0, sort_alpha: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура управления ключевыми словами."""
    keywords = db.get_keywords(sort_alpha=sort_alpha)
    per_page = 10
    start = page * per_page
    end = start + per_page
    page_keywords = keywords[start:end]
    
    keyboard = []
    
    # Кнопки с ключевыми словами
    for kw in page_keywords:
        keyboard.append([InlineKeyboardButton(
            text=f"❌ {kw}", 
            callback_data=f"del_kw:{kw}"
        )])
    
    # Навигация по страницам
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀", callback_data=f"kw_page:{page-1}:{int(sort_alpha)}"))
    if end < len(keywords):
        nav_row.append(InlineKeyboardButton(text="▶", callback_data=f"kw_page:{page+1}:{int(sort_alpha)}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Управление
    keyboard.append([
        InlineKeyboardButton(text="🔤 Сортировать", callback_data=f"kw_sort:{page}:{int(not sort_alpha)}")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🧾 Скопировать все", callback_data="kw_copy_all"),
        InlineKeyboardButton(text="❌ Удалить все", callback_data="kw_delete_all")
    ])
    keyboard.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="parser_settings")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def stopwords_keyboard(page: int = 0, sort_alpha: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура управления стоп-словами."""
    stopwords = db.get_stopwords(sort_alpha=sort_alpha)
    per_page = 10
    start = page * per_page
    end = start + per_page
    page_stopwords = stopwords[start:end]
    
    keyboard = []
    
    # Кнопки со стоп-словами
    for sw in page_stopwords:
        keyboard.append([InlineKeyboardButton(
            text=f"❌ {sw}", 
            callback_data=f"del_sw:{sw}"
        )])
    
    # Навигация по страницам
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀", callback_data=f"sw_page:{page-1}:{int(sort_alpha)}"))
    if end < len(stopwords):
        nav_row.append(InlineKeyboardButton(text="▶", callback_data=f"sw_page:{page+1}:{int(sort_alpha)}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Управление
    keyboard.append([
        InlineKeyboardButton(text="🔤 Сортировать", callback_data=f"sw_sort:{page}:{int(not sort_alpha)}")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🧾 Скопировать все", callback_data="sw_copy_all"),
        InlineKeyboardButton(text="❌ Удалить все", callback_data="sw_delete_all")
    ])
    keyboard.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="parser_settings")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def blacklist_keyboard(page: int = 0, sort_numeric: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура управления черным списком."""
    blacklist = db.get_blacklist(sort_numeric=sort_numeric)
    per_page = 10
    start = page * per_page
    end = start + per_page
    page_blacklist = blacklist[start:end]
    
    keyboard = []
    
    # Кнопки с ID пользователей
    for user_id in page_blacklist:
        keyboard.append([InlineKeyboardButton(
            text=f"❌ {user_id}", 
            callback_data=f"del_bl:{user_id}"
        )])
    
    # Навигация по страницам
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀", callback_data=f"bl_page:{page-1}:{int(sort_numeric)}"))
    if end < len(blacklist):
        nav_row.append(InlineKeyboardButton(text="▶", callback_data=f"bl_page:{page+1}:{int(sort_numeric)}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Управление
    keyboard.append([
        InlineKeyboardButton(text="🔢 Сортировать", callback_data=f"bl_sort:{page}:{int(not sort_numeric)}")
    ])
    keyboard.append([
        InlineKeyboardButton(text="❌ Очистить список", callback_data="bl_delete_all")
    ])
    keyboard.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="parser_settings")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_to_parser_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата к настройкам парсера."""
    keyboard = [
        [InlineKeyboardButton(text="⬅ Назад", callback_data="parser_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    keyboard = [
        [InlineKeyboardButton(text="⬅ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== АККАУНТЫ ====================

def accounts_keyboard() -> InlineKeyboardMarkup:
    accounts = AccountStore.list_accounts()
    current_id = AccountStore.get_current_id()
    keyboard = []
    if not accounts:
        keyboard.append([InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="acc_add")])
        keyboard.append([InlineKeyboardButton(text="⬅ Назад", callback_data="main_menu")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    for acc in accounts:
        title = acc.get('phone') or acc.get('session_file') or acc.get('id')
        is_current = " 🟦 (текущий)" if acc.get("id") == current_id else ""
        label = f"Аккаунт: {title}{is_current}"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"acc_set_current:{acc.get('id')}")])
    keyboard.append([InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="acc_add")])
    keyboard.append([InlineKeyboardButton(text="⬅ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.callback_query(F.data == "accounts")
async def show_accounts(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # Автодобавление дефолтной сессии, если аккаунтов нет
    AccountStore.ensure_default_account()
    current = AccountStore.get_current_account()
    header = (
        "👤 <b>МОИ АККАУНТЫ</b>\n\n"
        f"Текущий: <code>{(current.get('phone') if current else None) or (current.get('session_file') if current else 'не выбран')}</code>\n\n"
        "Выберите аккаунт для управления или добавьте новый."
    )
    await callback.message.edit_text(header, reply_markup=accounts_keyboard(), parse_mode="HTML")
    await callback.answer()

class AccForm(StatesGroup):
    waiting_phone = State()
    waiting_session = State()

@router.callback_query(F.data == "acc_add")
async def add_account_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AccForm.waiting_phone)
    await callback.message.edit_text("Введите номер телефона аккаунта (в формате +7...):", reply_markup=back_to_main_keyboard())
    await callback.answer()

@router.message(StateFilter(AccForm.waiting_phone))
async def add_account_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(AccForm.waiting_session)
    await message.answer("Введите имя session-файла Telethon (без .session), например: acc1", reply_markup=back_to_main_keyboard())

@router.message(StateFilter(AccForm.waiting_session))
async def add_account_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone")
    session_file = message.text.strip()
    acc_id = session_file
    try:
        AccountStore.add_account(acc_id=acc_id, phone=phone, session_file=session_file)
        await message.answer("✅ Аккаунт добавлен", reply_markup=accounts_keyboard())
    except Exception as e:
        await message.answer(f"❌ Не удалось добавить: {e}")
    await state.clear()

@router.callback_query(F.data.startswith("acc_toggle:"))
async def acc_toggle(callback: CallbackQuery):
    acc_id = callback.data.split(":",1)[1]
    acc = AccountStore.get_account(acc_id)
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return
    AccountStore.update(acc_id, status=not acc.get("status"))
    await callback.message.edit_reply_markup(reply_markup=accounts_keyboard())
    await callback.answer("Готово")

@router.callback_query(F.data.startswith("acc_del:"))
async def acc_delete(callback: CallbackQuery):
    acc_id = callback.data.split(":",1)[1]
    AccountStore.remove_account(acc_id)
    await callback.message.edit_reply_markup(reply_markup=accounts_keyboard())
    await callback.answer("Удалено")

@router.callback_query(F.data.startswith("acc_open:"))
async def acc_open(callback: CallbackQuery):
    # Упрощаем: нажатие по аккаунту сразу делает его текущим
    acc_id = callback.data.split(":",1)[1]
    AccountStore.set_current_id(acc_id)
    await callback.message.edit_text(
        "👤 <b>МОИ АККАУНТЫ</b>\n\nТекущий аккаунт обновлён.",
        reply_markup=accounts_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Установлен текущим")

@router.callback_query(F.data.startswith("acc_set_current:"))
async def acc_set_current(callback: CallbackQuery):
    acc_id = callback.data.split(":",1)[1]
    AccountStore.set_current_id(acc_id)
    await callback.message.edit_text(
        "👤 <b>МОИ АККАУНТЫ</b>\n\nТекущий аккаунт обновлён.\n\nВыберите аккаунт для управления или добавьте новый.",
        reply_markup=accounts_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Текущий аккаунт установлен")


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_parser_status_text() -> str:
    """Получить текст карточки статуса парсера."""
    conf = db.get_all_config()
    keywords_count = len(db.get_keywords())
    stopwords_count = len(db.get_stopwords())
    notification_chat = conf.get('notification_chat_id', 'не установлен')

    AccountStore.ensure_default_account()
    current = AccountStore.get_current_account()
    if current:
        phone = current.get('phone') or current.get('session_file') or 'выбран'
    else:
        phone = 'не выбран'

    text = (
        "⚙️ <b>НАСТРОЙКА ПАРСЕРА</b>\n\n"
        f"📱 Аккаунт: <code>{phone}</code>\n"
        f"📢 ID чата для уведомлений: <code>{notification_chat}</code>\n"
        f"🔑 Кол-во ключевых слов: <b>{keywords_count}</b>\n"
        f"⛔ Кол-во стоп-слов: <b>{stopwords_count}</b>\n\n"
        "Выберите действие:"
    )
    return text


def get_keywords_text(page: int = 0, sort_alpha: bool = False) -> str:
    """Получить текст для модуля ключевых слов."""
    keywords = db.get_keywords(sort_alpha=sort_alpha)
    count = len(keywords)
    
    text = (
        f"🔑 <b>КЛЮЧЕВЫЕ СЛОВА</b>\n\n"
        f"Кол-во ключ-слов: <b>{count}</b>\n\n"
        "Для удаления нажмите на слово.\n"
        "Чтобы добавить — отправьте его в чат.\n\n"
        "<i>_слово_ = искать слово как отдельное\n"
        "+ = обязательные несколько слов\n"
        "Пример: продам+айфон</i>"
    )
    return text


def get_stopwords_text(page: int = 0, sort_alpha: bool = False) -> str:
    """Получить текст для модуля стоп-слов."""
    stopwords = db.get_stopwords(sort_alpha=sort_alpha)
    count = len(stopwords)
    
    text = (
        f"⛔ <b>СТОП-СЛОВА</b>\n\n"
        f"Кол-во стоп-слов: <b>{count}</b>\n\n"
        "Эти слова исключают сообщения.\n"
        "Для удаления нажмите на слово.\n"
        "Чтобы добавить — отправьте его в чат.\n\n"
        "<i>_слово_ = искать как отдельное\n"
        "+ = комбинация слов</i>"
    )
    return text


def get_blacklist_text(page: int = 0, sort_numeric: bool = False) -> str:
    """Получить текст для модуля черного списка."""
    blacklist = db.get_blacklist(sort_numeric=sort_numeric)
    count = len(blacklist)
    
    text = (
        f"🚫 <b>ЧЁРНЫЙ СПИСОК</b>\n\n"
        f"Кол-во заблокированных: <b>{count}</b>\n\n"
        "Для удаления нажмите на ID.\n"
        "Чтобы добавить — отправьте ID числом.\n\n"
        "<i>ID можно узнать через бота @username_to_id_bot</i>"
    )
    return text


# ==================== ОБРАБОТЧИКИ КОМАНД ====================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    
    text = (
        "👋 <b>Добро пожаловать в Telegram-парсер лидов!</b>\n\n"
        "Этот бот поможет вам находить потенциальных клиентов "
        "в группах и каналах Telegram по заданным ключевым словам.\n\n"
        "Выберите действие из меню ниже:"
    )
    
    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


# ==================== ГЛАВНОЕ МЕНЮ ====================

@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    """Показать главное меню."""
    await state.clear()
    
    text = (
        "📋 <b>ГЛАВНОЕ МЕНЮ</b>\n\n"
        "Выберите нужный раздел:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== НАСТРОЙКИ ПАРСЕРА ====================

@router.callback_query(F.data == "parser_settings")
async def show_parser_settings(callback: CallbackQuery, state: FSMContext):
    """Показать настройки парсера."""
    await state.clear()
    
    text = get_parser_status_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=parser_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# Тумблеры статусов
@router.callback_query(F.data.startswith("toggle_"))
async def toggle_setting(callback: CallbackQuery):
    """Переключить настройку."""
    setting = callback.data.split("_", 1)[1]
    
    setting_map = {
        "working": "working_status",
        "groups": "groups_enabled",
        "channels": "channels_enabled",
        "dialogs": "dialogs_enabled",
        "duplicates": "ignore_duplicates"
    }
    
    config_key = setting_map.get(setting)
    if config_key:
        new_value = db.toggle_config(config_key)
        status = "включено" if new_value == "true" else "выключено"
        
        # Обновить клавиатуру
        text = get_parser_status_text()
        await callback.message.edit_text(
            text,
            reply_markup=parser_settings_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer(f"✅ {status.capitalize()}")
    else:
        await callback.answer("❌ Неизвестная настройка")


# ==================== МОДУЛЬ КЛЮЧЕВЫХ СЛОВ ====================

@router.callback_query(F.data == "keywords")
async def show_keywords(callback: CallbackQuery, state: FSMContext):
    """Показать модуль ключевых слов."""
    await state.set_state(Form.waiting_keyword)
    
    text = get_keywords_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=keywords_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("kw_page:"))
async def keywords_page(callback: CallbackQuery):
    """Переключить страницу ключевых слов."""
    _, page, sort = callback.data.split(":")
    page = int(page)
    sort_alpha = bool(int(sort))
    
    text = get_keywords_text(page, sort_alpha)
    
    await callback.message.edit_text(
        text,
        reply_markup=keywords_keyboard(page, sort_alpha),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("kw_sort:"))
async def keywords_sort(callback: CallbackQuery):
    """Сортировать ключевые слова."""
    _, page, sort = callback.data.split(":")
    page = int(page)
    sort_alpha = bool(int(sort))
    
    text = get_keywords_text(0, sort_alpha)  # Сброс на первую страницу
    
    await callback.message.edit_text(
        text,
        reply_markup=keywords_keyboard(0, sort_alpha),
        parse_mode="HTML"
    )
    await callback.answer("✅ Отсортировано")


@router.callback_query(F.data.startswith("del_kw:"))
async def delete_keyword(callback: CallbackQuery):
    """Удалить ключевое слово."""
    keyword = callback.data.split(":", 1)[1]
    db.remove_keyword(keyword)
    
    text = get_keywords_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=keywords_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ Удалено: {keyword}")


@router.callback_query(F.data == "kw_copy_all")
async def copy_all_keywords(callback: CallbackQuery):
    """Скопировать все ключевые слова."""
    keywords = db.get_keywords()
    
    if keywords:
        text = "\n".join(keywords)
        await callback.message.answer(f"📋 <b>Все ключевые слова:</b>\n\n{text}", parse_mode="HTML")
        await callback.answer("✅ Список отправлен")
    else:
        await callback.answer("❌ Список пуст")


@router.callback_query(F.data == "kw_delete_all")
async def delete_all_keywords(callback: CallbackQuery):
    """Удалить все ключевые слова."""
    db.clear_keywords()
    
    text = get_keywords_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=keywords_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("✅ Все ключевые слова удалены")


@router.message(StateFilter(Form.waiting_keyword))
async def add_keyword(message: Message, state: FSMContext):
    """Добавить ключевое слово."""
    keyword = message.text.strip()
    
    if db.add_keyword(keyword):
        await message.answer(f"✅ Ключевое слово добавлено: {keyword}")
    else:
        await message.answer(f"❌ Ключевое слово уже существует: {keyword}")
    
    # Обновить список
    text = get_keywords_text()
    await message.answer(text, reply_markup=keywords_keyboard(), parse_mode="HTML")


# ==================== МОДУЛЬ СТОП-СЛОВ ====================

@router.callback_query(F.data == "stopwords")
async def show_stopwords(callback: CallbackQuery, state: FSMContext):
    """Показать модуль стоп-слов."""
    await state.set_state(Form.waiting_stopword)
    
    text = get_stopwords_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=stopwords_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sw_page:"))
async def stopwords_page(callback: CallbackQuery):
    """Переключить страницу стоп-слов."""
    _, page, sort = callback.data.split(":")
    page = int(page)
    sort_alpha = bool(int(sort))
    
    text = get_stopwords_text(page, sort_alpha)
    
    await callback.message.edit_text(
        text,
        reply_markup=stopwords_keyboard(page, sort_alpha),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sw_sort:"))
async def stopwords_sort(callback: CallbackQuery):
    """Сортировать стоп-слова."""
    _, page, sort = callback.data.split(":")
    page = int(page)
    sort_alpha = bool(int(sort))
    
    text = get_stopwords_text(0, sort_alpha)
    
    await callback.message.edit_text(
        text,
        reply_markup=stopwords_keyboard(0, sort_alpha),
        parse_mode="HTML"
    )
    await callback.answer("✅ Отсортировано")


@router.callback_query(F.data.startswith("del_sw:"))
async def delete_stopword(callback: CallbackQuery):
    """Удалить стоп-слово."""
    stopword = callback.data.split(":", 1)[1]
    db.remove_stopword(stopword)
    
    text = get_stopwords_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=stopwords_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ Удалено: {stopword}")


@router.callback_query(F.data == "sw_copy_all")
async def copy_all_stopwords(callback: CallbackQuery):
    """Скопировать все стоп-слова."""
    stopwords = db.get_stopwords()
    
    if stopwords:
        text = "\n".join(stopwords)
        await callback.message.answer(f"📋 <b>Все стоп-слова:</b>\n\n{text}", parse_mode="HTML")
        await callback.answer("✅ Список отправлен")
    else:
        await callback.answer("❌ Список пуст")


@router.callback_query(F.data == "sw_delete_all")
async def delete_all_stopwords(callback: CallbackQuery):
    """Удалить все стоп-слова."""
    db.clear_stopwords()
    
    text = get_stopwords_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=stopwords_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("✅ Все стоп-слова удалены")


@router.message(StateFilter(Form.waiting_stopword))
async def add_stopword(message: Message, state: FSMContext):
    """Добавить стоп-слово."""
    stopword = message.text.strip()
    
    if db.add_stopword(stopword):
        await message.answer(f"✅ Стоп-слово добавлено: {stopword}")
    else:
        await message.answer(f"❌ Стоп-слово уже существует: {stopword}")
    
    # Обновить список
    text = get_stopwords_text()
    await message.answer(text, reply_markup=stopwords_keyboard(), parse_mode="HTML")


# ==================== МОДУЛЬ ЧЕРНОГО СПИСКА ====================

@router.callback_query(F.data == "blacklist")
async def show_blacklist(callback: CallbackQuery, state: FSMContext):
    """Показать модуль черного списка."""
    await state.set_state(Form.waiting_blacklist_id)
    
    text = get_blacklist_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=blacklist_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bl_page:"))
async def blacklist_page(callback: CallbackQuery):
    """Переключить страницу черного списка."""
    _, page, sort = callback.data.split(":")
    page = int(page)
    sort_numeric = bool(int(sort))
    
    text = get_blacklist_text(page, sort_numeric)
    
    await callback.message.edit_text(
        text,
        reply_markup=blacklist_keyboard(page, sort_numeric),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bl_sort:"))
async def blacklist_sort(callback: CallbackQuery):
    """Сортировать черный список."""
    _, page, sort = callback.data.split(":")
    page = int(page)
    sort_numeric = bool(int(sort))
    
    text = get_blacklist_text(0, sort_numeric)
    
    await callback.message.edit_text(
        text,
        reply_markup=blacklist_keyboard(0, sort_numeric),
        parse_mode="HTML"
    )
    await callback.answer("✅ Отсортировано")


@router.callback_query(F.data.startswith("del_bl:"))
async def delete_from_blacklist(callback: CallbackQuery):
    """Удалить из черного списка."""
    user_id = int(callback.data.split(":", 1)[1])
    db.remove_from_blacklist(user_id)
    
    text = get_blacklist_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=blacklist_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ Удалено: {user_id}")


@router.callback_query(F.data == "bl_delete_all")
async def clear_blacklist(callback: CallbackQuery):
    """Очистить черный список."""
    db.clear_blacklist()
    
    text = get_blacklist_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=blacklist_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("✅ Черный список очищен")


@router.message(StateFilter(Form.waiting_blacklist_id))
async def add_to_blacklist(message: Message, state: FSMContext):
    """Добавить в черный список."""
    try:
        user_id = int(message.text.strip())
        
        if db.add_to_blacklist(user_id):
            await message.answer(f"✅ Добавлен в черный список: {user_id}")
        else:
            await message.answer(f"❌ Пользователь уже в черном списке: {user_id}")
        
        # Обновить список
        text = get_blacklist_text()
        await message.answer(text, reply_markup=blacklist_keyboard(), parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Ошибка: отправьте корректный ID (число)")


# ==================== МОДУЛЬ ЧАТ ДЛЯ УВЕДОМЛЕНИЙ ====================

@router.callback_query(F.data == "notification_chat")
async def show_notification_chat(callback: CallbackQuery, state: FSMContext):
    """Показать модуль настройки чата уведомлений."""
    await state.set_state(Form.waiting_chat_id)
    
    current_chat = db.get_config('notification_chat_id', 'не установлен')
    
    text = (
        "📢 <b>ЧАТ ДЛЯ УВЕДОМЛЕНИЙ</b>\n\n"
        f"Текущий ID чата: <code>{current_chat}</code>\n\n"
        "Отправьте новый ID чата, чтобы обновить.\n\n"
        "<i>Чтобы узнать ID чата:\n"
        "1. Добавьте бота @username_to_id_bot в чат\n"
        "2. Отправьте команду /id\n"
        "3. Скопируйте полученный ID и отправьте сюда</i>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_parser_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(StateFilter(Form.waiting_chat_id))
async def set_notification_chat(message: Message, state: FSMContext):
    """Установить чат для уведомлений."""
    try:
        chat_id = message.text.strip()
        
        # Проверка, что это похоже на ID (число или начинается с -)
        if chat_id.lstrip('-').isdigit():
            db.set_config('notification_chat_id', chat_id)
            await message.answer(f"✅ ID чата для уведомлений обновлен: {chat_id}")
            
            # Вернуться к настройкам парсера
            await state.clear()
            text = get_parser_status_text()
            await message.answer(text, reply_markup=parser_settings_keyboard(), parse_mode="HTML")
        else:
            await message.answer("❌ Ошибка: отправьте корректный ID чата (число)")
    except Exception as e:
        logger.error(f"Ошибка при установке chat_id: {e}")
        await message.answer("❌ Произошла ошибка")


# ==================== ИСТОРИЯ ЛИДОВ ====================

@router.callback_query(F.data == "lead_history")
async def show_lead_history(callback: CallbackQuery):
    """Показать историю лидов."""
    logs = db.get_recent_logs(10)
    
    if not logs:
        text = "📜 <b>ИСТОРИЯ ЛИДОВ</b>\n\nЛиды пока не найдены."
    else:
        text = "📜 <b>ИСТОРИЯ ЛИДОВ</b>\n\n"
        text += "Последние 10 найденных сообщений:\n\n"
        
        for log in logs:
            timestamp = log['timestamp']
            source = log['source_chat']
            user_id = log['user_id']
            msg_text = log['text'][:50] + "..." if log['text'] and len(log['text']) > 50 else log['text']
            
            text += (
                f"🕐 <code>{timestamp}</code>\n"
                f"📱 Чат: <b>{source}</b>\n"
                f"👤 User ID: <code>{user_id}</code>\n"
                f"💬 Текст: <i>{msg_text}</i>\n\n"
            )
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ЗАГЛУШКИ БУДУЩИХ ФУНКЦИЙ ====================

@router.callback_query(F.data == "import_sources")
async def import_sources_stub(callback: CallbackQuery):
    """Заглушка для импорта источников."""
    text = (
        "📥 <b>ИМПОРТ ИСТОЧНИКОВ</b>\n\n"
        "⚠️ Функция автоподписки на группы пока в разработке.\n\n"
        "В будущих версиях здесь можно будет:\n"
        "• Добавлять ссылки на группы и каналы\n"
        "• Автоматически подписываться на них\n"
        "• Управлять списком источников"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "outbox")
async def outbox_stub(callback: CallbackQuery):
    """Заглушка для исходящих сообщений."""
    text = (
        "📤 <b>ИСХОДЯЩИЕ СООБЩЕНИЯ</b>\n\n"
        "⚠️ Модуль исходящих сообщений появится в следующих обновлениях.\n\n"
        "Планируемый функционал:\n"
        "• Автоматическая рассылка по найденным лидам\n"
        "• Шаблоны сообщений\n"
        "• Управление очередью отправки"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ПОМОЩЬ ====================

@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Показать помощь."""
    text = (
        "❓ <b>ПОМОЩЬ / ИНСТРУКЦИЯ</b>\n\n"
        "<b>Как работает бот:</b>\n\n"
        "1️⃣ Настройте ключевые слова — это слова, по которым "
        "будет идти поиск сообщений.\n\n"
        "2️⃣ Добавьте стоп-слова (опционально) — сообщения с этими "
        "словами будут исключены.\n\n"
        "3️⃣ Укажите ID чата для уведомлений — сюда будут приходить "
        "найденные лиды.\n\n"
        "4️⃣ Включите парсер кнопкой «🟢 Работает».\n\n"
        "5️⃣ Парсер начнет анализировать все группы и каналы, "
        "на которые подписан технический аккаунт.\n\n"
        "<b>Дополнительные возможности:</b>\n"
        "• Черный список — блокировка конкретных пользователей\n"
        "• Игнор дублей — не показывать повторяющиеся сообщения\n"
        "• История лидов — просмотр последних найденных сообщений\n\n"
        "<b>Поддержка:</b>\n"
        "Если возникли вопросы, обращайтесь к администратору."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ЗАПУСК БОТА ====================

async def main():
    """Главная функция запуска бота."""
    dp.include_router(router)
    
    logger.info("Бот запущен")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")

