"""
Управление множеством Telegram-аккаунтов (технические профили) через локальный JSON.

Каждый аккаунт:
{
  "id": "acc_1",
  "phone": "+79990000000",
  "session_file": "session_acc_1",
  "notify_chat_id": "",
  "status": false
}
"""

import json
import os
import threading
from typing import Dict, List, Optional


ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "accounts.json")


class AccountStore:
    _lock = threading.Lock()

    @staticmethod
    def _load() -> Dict:
        if not os.path.exists(ACCOUNTS_FILE):
            return {"accounts": [], "current_id": None}
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _save(data: Dict) -> None:
        with AccountStore._lock:
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def list_accounts() -> List[Dict]:
        return AccountStore._load().get("accounts", [])

    @staticmethod
    def get_account(acc_id: str) -> Optional[Dict]:
        for acc in AccountStore.list_accounts():
            if acc.get("id") == acc_id:
                return acc
        return None

    @staticmethod
    def add_account(acc_id: str, phone: str, session_file: str) -> Dict:
        data = AccountStore._load()
        accounts = data.setdefault("accounts", [])
        if any(a.get("id") == acc_id for a in accounts):
            raise ValueError("Account with this id already exists")
        account = {
            "id": acc_id,
            "phone": phone,
            "username": "",
            "session_file": session_file,
            "notify_chat_id": "",
            "status": False,
        }
        accounts.append(account)
        # Если это первый аккаунт — делаем его текущим
        if not data.get("current_id"):
            data["current_id"] = acc_id
        AccountStore._save(data)
        return account

    @staticmethod
    def remove_account(acc_id: str) -> bool:
        data = AccountStore._load()
        before = len(data.get("accounts", []))
        data["accounts"] = [a for a in data.get("accounts", []) if a.get("id") != acc_id]
        if data.get("current_id") == acc_id:
            data["current_id"] = data["accounts"][0]["id"] if data["accounts"] else None
        AccountStore._save(data)
        return len(data["accounts"]) < before

    @staticmethod
    def update(acc_id: str, **fields) -> Optional[Dict]:
        data = AccountStore._load()
        for a in data.get("accounts", []):
            if a.get("id") == acc_id:
                a.update({k: v for k, v in fields.items() if v is not None})
                AccountStore._save(data)
                return a
        return None

    @staticmethod
    def find_by_session_file(session_file: str) -> Optional[Dict]:
        for a in AccountStore.list_accounts():
            if a.get("session_file") == session_file:
                return a
        return None

    @staticmethod
    def active_accounts() -> List[Dict]:
        return [a for a in AccountStore.list_accounts() if a.get("status")]

    @staticmethod
    def ensure_default_account() -> Optional[Dict]:
        """Если нет ни одного аккаунта, но есть локальная сессия или SESSION_STRING,
        создаём "default" для обратной совместимости.
        """
        data = AccountStore._load()
        accounts = data.get("accounts", [])
        if accounts:
            return None
        # Ищем дефолтную сессию Telethon в нескольких местах
        here = os.path.dirname(__file__)
        parent = os.path.abspath(os.path.join(here, os.pardir))
        candidates = [
            os.path.join(here, 'parser_session.session'),
            os.path.join(parent, 'parser_session.session'),
        ]
        # Если рядом есть любые .session — возьмём первый
        for d in (here, parent):
            for name in os.listdir(d):
                if name.endswith('.session') and os.path.isfile(os.path.join(d, name)):
                    candidates.append(os.path.join(d, name))
        default_session = next((p for p in candidates if os.path.exists(p)), None)
        if default_session:
            sess_name = os.path.splitext(os.path.basename(default_session))[0]
            acc = {
                "id": "default",
                "phone": "(локальная сессия)",
                "session_file": sess_name,
                "notify_chat_id": "",
                "status": True,
            }
            data["accounts"] = [acc]
            data["current_id"] = acc["id"]
            AccountStore._save(data)
            return acc
        # Если ничего не нашли — ничего не делаем
        return None

    @staticmethod
    def get_current_id() -> Optional[str]:
        data = AccountStore._load()
        cid = data.get("current_id")
        # Автовыбор первого аккаунта, если current_id не задан, но аккаунты есть
        if not cid and data.get("accounts"):
            cid = data["accounts"][0]["id"]
            AccountStore._save({**data, "current_id": cid})
        return cid

    @staticmethod
    def set_current_id(acc_id: str) -> None:
        data = AccountStore._load()
        if any(a.get("id") == acc_id for a in data.get("accounts", [])):
            data["current_id"] = acc_id
            AccountStore._save(data)

    @staticmethod
    def get_current_account() -> Optional[Dict]:
        cid = AccountStore.get_current_id()
        if not cid:
            return None
        return AccountStore.get_account(cid)

    @staticmethod
    def find_by_session(session_file: str) -> Optional[Dict]:
        for a in AccountStore.list_accounts():
            if a.get("session_file") == session_file:
                return a
        return None

    @staticmethod
    def update_identity_by_session(session_file: str, phone: Optional[str] = None, username: Optional[str] = None) -> None:
        data = AccountStore._load()
        changed = False
        for a in data.get("accounts", []):
            if a.get("session_file") == session_file:
                if phone is not None and phone != a.get("phone"):
                    a["phone"] = phone
                    changed = True
                if username is not None and username != a.get("username"):
                    a["username"] = username
                    changed = True
                break
        if changed:
            AccountStore._save(data)


