# 📝 Примеры использования

Этот файл содержит примеры использования API базы данных и различных компонентов парсера.

## 🗄️ Работа с базой данных

### Инициализация

```python
from database import Database

db = Database("parser.db")
```

### Ключевые слова

```python
# Добавить ключевое слово
db.add_keyword("продам+айфон")

# Получить все ключевые слова
keywords = db.get_keywords()
print(keywords)

# Получить с сортировкой по алфавиту
keywords = db.get_keywords(sort_alpha=True)

# Удалить ключевое слово
db.remove_keyword("продам+айфон")

# Очистить все ключевые слова
db.clear_keywords()
```

### Стоп-слова

```python
# Добавить стоп-слово
db.add_stopword("барахолка")

# Получить все стоп-слова
stopwords = db.get_stopwords()

# Удалить стоп-слово
db.remove_stopword("барахолка")

# Очистить все стоп-слова
db.clear_stopwords()
```

### Черный список

```python
# Добавить в черный список
db.add_to_blacklist(123456789)

# Проверить, в черном ли списке
is_blocked = db.is_blacklisted(123456789)
print(is_blocked)  # True

# Получить весь черный список
blacklist = db.get_blacklist()

# Удалить из черного списка
db.remove_from_blacklist(123456789)

# Очистить черный список
db.clear_blacklist()
```

### Конфигурация

```python
# Установить значение
db.set_config('working_status', 'true')

# Получить значение
status = db.get_config('working_status')
print(status)  # 'true'

# Получить значение с default
value = db.get_config('some_key', default='default_value')

# Переключить булево значение
new_value = db.toggle_config('working_status')
print(new_value)  # 'false'

# Получить весь конфиг
config = db.get_all_config()
print(config)
```

### История лидов

```python
# Добавить запись
db.add_log(
    source_chat="Форум программистов",
    message_id=12345,
    text="Продам айфон 15 Pro",
    user_id=123456789,
    chat_id=-1001234567890
)

# Получить последние 10 лидов
logs = db.get_recent_logs(10)
for log in logs:
    print(f"{log['timestamp']}: {log['text']}")

# Проверить дубликат
is_duplicate = db.check_duplicate("Продам айфон 15 Pro", hours=24)
print(is_duplicate)  # True если уже было такое сообщение за последние 24 часа
```

## 🔍 Фильтрация сообщений

### Использование MessageFilter

```python
from worker import MessageFilter

# Проверка ключевого слова
text = "Продам айфон 15 pro, новый, в упаковке"

# Обычное слово
result = MessageFilter.check_keyword(text, "айфон")
print(result)  # True

# Точное слово
result = MessageFilter.check_keyword(text, "_айфон_")
print(result)  # True

# Комбинация слов
result = MessageFilter.check_keyword(text, "продам+айфон")
print(result)  # True

result = MessageFilter.check_keyword(text, "куплю+айфон")
print(result)  # False (нет слова "куплю")
```

### Проверка списка ключевых слов

```python
keywords = ["продам+айфон", "продам+телефон", "_iphone_"]
text = "Продам айфон 15 pro"

has_keyword = MessageFilter.check_keywords(text, keywords)
print(has_keyword)  # True
```

### Проверка стоп-слов

```python
stopwords = ["барахолка", "обмен", "куплю"]
text = "Продам айфон, рассмотрю обмен"

has_stopword = MessageFilter.check_stopwords(text, stopwords)
print(has_stopword)  # True (есть слово "обмен")
```

## 🤖 Примеры настройки парсера

### Пример 1: Парсинг предложений о работе

```python
# Ключевые слова
keywords = [
    "ищу+программиста",
    "нужен+разработчик",
    "вакансия+python",
    "_удаленка_+программист",
    "ищем+frontend",
    "требуется+backend"
]

# Стоп-слова
stopwords = [
    "бесплатно",
    "стажер",
    "практика",
    "без+оплаты",
    "за+опыт"
]

for keyword in keywords:
    db.add_keyword(keyword)

for stopword in stopwords:
    db.add_stopword(stopword)
```

### Пример 2: Поиск недвижимости

```python
# Ключевые слова
keywords = [
    "сдам+квартиру",
    "сдается+_однушка_",
    "сдаю+комнату",
    "аренда+квартира",
    "_студия_+сдам"
]

# Стоп-слова
stopwords = [
    "снять",
    "сниму",
    "ищу",
    "агентство",
    "посредник"
]

for keyword in keywords:
    db.add_keyword(keyword)

for stopword in stopwords:
    db.add_stopword(stopword)
```

### Пример 3: Продажа техники

```python
# Ключевые слова
keywords = [
    "продам+айфон",
    "продам+_iphone_",
    "продаю+macbook",
    "_ipad_+новый",
    "apple+watch"
]

# Стоп-слова
stopwords = [
    "куплю",
    "ищу",
    "нужен",
    "барахолка",
    "б/у",
    "битый"
]

for keyword in keywords:
    db.add_keyword(keyword)

for stopword in stopwords:
    db.add_stopword(stopword)
```

## 🧪 Тестирование фильтров

```python
from database import Database
from worker import MessageFilter

db = Database("parser.db")

# Настройка фильтров
db.add_keyword("продам+айфон")
db.add_stopword("битый")

# Тестовые сообщения
test_messages = [
    "Продам айфон 15 Pro, новый",  # ✅ Пройдет
    "Куплю айфон недорого",         # ❌ Нет ключевого слова "продам"
    "Продам айфон, битый экран",    # ❌ Есть стоп-слово "битый"
    "Продам телефон Samsung"        # ❌ Нет слова "айфон"
]

keywords = db.get_keywords()
stopwords = db.get_stopwords()

for msg in test_messages:
    has_keyword = MessageFilter.check_keywords(msg, keywords)
    has_stopword = MessageFilter.check_stopwords(msg, stopwords)
    
    will_pass = has_keyword and not has_stopword
    
    print(f"{'✅' if will_pass else '❌'} {msg}")
    print(f"   Ключевое слово: {has_keyword}, Стоп-слово: {has_stopword}\n")
```

## 🔧 Продвинутые примеры

### Массовое добавление ключевых слов

```python
keywords_list = """
продам+айфон
продам+iphone
продаю+телефон
_apple_+новый
macbook+pro
""".strip().split('\n')

for keyword in keywords_list:
    if keyword.strip():
        db.add_keyword(keyword.strip())
        print(f"Добавлено: {keyword.strip()}")
```

### Экспорт/импорт конфигурации

```python
import json

# Экспорт
config_export = {
    'keywords': db.get_keywords(),
    'stopwords': db.get_stopwords(),
    'blacklist': db.get_blacklist(),
    'config': db.get_all_config()
}

with open('config_backup.json', 'w', encoding='utf-8') as f:
    json.dump(config_export, f, ensure_ascii=False, indent=2)

# Импорт
with open('config_backup.json', 'r', encoding='utf-8') as f:
    config_import = json.load(f)

for keyword in config_import['keywords']:
    db.add_keyword(keyword)

for stopword in config_import['stopwords']:
    db.add_stopword(stopword)

for user_id in config_import['blacklist']:
    db.add_to_blacklist(user_id)
```

### Статистика лидов

```python
from collections import Counter

# Получить последние 100 лидов
logs = db.get_recent_logs(100)

# Статистика по чатам
chat_stats = Counter(log['source_chat'] for log in logs)
print("Топ-5 чатов по лидам:")
for chat, count in chat_stats.most_common(5):
    print(f"  {chat}: {count} лидов")

# Статистика по пользователям
user_stats = Counter(log['user_id'] for log in logs)
print("\nТоп-5 пользователей:")
for user_id, count in user_stats.most_common(5):
    print(f"  User {user_id}: {count} сообщений")
```

## 🎯 Оптимизация

### Очистка старых логов

```python
import sqlite3
from database import Database

db = Database("parser.db")

# Удалить логи старше 30 дней
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("""
    DELETE FROM logs 
    WHERE datetime(timestamp) < datetime('now', '-30 days')
""")
deleted = cursor.rowcount
conn.commit()
conn.close()

print(f"Удалено старых логов: {deleted}")
```

### Проверка размера базы данных

```python
import os

db_path = "parser.db"
size_bytes = os.path.getsize(db_path)
size_mb = size_bytes / (1024 * 1024)

print(f"Размер базы данных: {size_mb:.2f} MB")
```

---

**Больше примеров смотрите в документации проекта!**

