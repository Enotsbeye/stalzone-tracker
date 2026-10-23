# -*- coding: utf-8 -*-
"""
STALZONE — трекер лотов ниже рынка.

Что делает:
  * раз в N минут смотрит лоты на аукционе для твоего списка предметов
    (через официальный API EXBO);
  * считает рыночную цену как медиану реальных сделок за последние часы;
  * если кто-то выставил лот заметно дешевле рынка — пишет в консоль
    и (если настроено) в Telegram.

Чего НЕ делает: ничего не покупает сам. Автопокупка через игровой клиент —
это бот, за такое банят. Этот скрипт только смотрит и сообщает.

Запуск:
  python stalzone_tracker.py --selftest   # проверка логики без интернета
  python stalzone_tracker.py --once       # один проход и выход
  python stalzone_tracker.py              # работать постоянно
"""

import argparse
import json
import logging
import math
import os
import re
import sqlite3
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:  # подсказка новичку вместо непонятной ошибки
    print("Не установлен модуль requests. Выполни:  pip install requests")
    sys.exit(1)

# ============================ НАСТРОЙКИ ============================
CONFIG = {
    # Боевой API. Для теста на демо-данных поставь "https://dapi.stalzone.com" —
    # ключи для демо уже встроены (публичные, из документации EXBO).
    "base_url": "https://eapi.stalzone.com",
    "region": "ru",

    # Доступ к API: client_id + client_secret (выдаёт @stalzone_api_bot
    # после одобрения заявки). app_token — только если EXBO выдала готовый токен.
    "client_id": "",
    "client_secret": "",
    "app_token": "",

    # Что отслеживать: названия как в игре или id предметов.
    "watch": [
        "Морфин",
        "Янтарная полынь",
        "Хлорид алюминия",
        "Теломераза",
        "Мутаген",
    ],
    # True — вдобавок к списку проверять ВСЕ артефакты из базы игры (~100 шт.).
    "all_artifacts": False,
    # Какие категории проверять целиком: artefact, armor, weapon, parts, tools.
    "auto_categories": [],

    # Особо редкие находки — отдельный звук и сообщение. Редкие: артефакты с качеством
    # от rare_quality (0 обычный … 4 исключительный, 5 легендарный), снаряжение ранга «Легенда»
    # и предметы из rare_items. Для них свой порог прибыли.
    "rare_enabled": True,
    "rare_quality": 4,
    "rare_items": [],
    "rare_min_profit": 5000,

    # Когда сообщать о лоте:
    "discount": 0.15,       # дешевле рынка минимум на 15%
    "min_profit": 15000,    # и перепродажа даст минимум 15 000 ₽ после комиссии 5%
    "fee": 0.05,            # комиссия аукциона

    # Как считать рыночную цену:
    "history_hours": 48,    # сделки за последние 48 часов
    "min_sales": 5,         # меньше сделок — цене не доверяем, лот пропускаем
    "history_refresh_minutes": 10,  # как часто докачивать новые сделки
    "history_keep_days": 14,  # сколько дней хранить сделки в своей базе (market.db)

    "poll_minutes": 1,      # как часто проверять лоты (новый проход — не раньше, чем через столько минут)

    # Режим ставок: лоты, которые скоро заканчиваются, а текущая ставка
    # сильно ниже рынка. Тут задержка API почти не мешает — лоты висят часами.
    "bids": True,
    "bid_window_minutes": 60,   # сообщать о лотах, которые закончатся в ближайший час
    "bid_min_left_minutes": 3,  # но не о тех, где осталось меньше 3 минут

    # Уведомления в Telegram (необязательно). Пусто — только консоль.
    "telegram_token": "",
    "telegram_chat_id": "",
}
# ===================================================================

LISTING_URL = ("https://raw.githubusercontent.com/EXBO-Studio/"
               "stalzone-database/main/{region}/listing.json")
BARTER_URL = ("https://raw.githubusercontent.com/EXBO-Studio/"
              "stalzone-database/main/{region}/barter_recipes.json")   # что получают бартером у торговцев
OAUTH_URL = "https://exbo.net/oauth/token"
# Публичные ключи демо-API из документации EXBO (eapi.stalzone.net/auth.html).
# Работают только с dapi.stalzone.com, там тестовые данные, не настоящий аукцион.
DEMO_CLIENT_ID = "1"
DEMO_CLIENT_SECRET = "E98cm6J9NNjTQopph0c2eIXNKafg4R1Cjz0TZh2D"
HISTORY_PAGES = 10           # страниц истории по 100 сделок на предмет (популярные артефакты — сотни в час)
LOT_PAGES = 5                # страниц лотов по 100 на предмет
UNDERCUT = 0.99              # чтобы продать, ставишь чуть дешевле самого дешёвого конкурента
STALE_MINUTES = 60           # лот висит дольше и его не купили — вероятно, есть подвох
LONG_DAYS = 7                # если за history_hours сделок мало — смотрим столько дней из своей базы
FETCH_THREADS = 6            # столько запросов к API могут идти одновременно
FETCH_AHEAD = 12             # на сколько предметов вперёд заранее запрашивать данные
RATE_SHARE = 0.85            # какую долю лимита API тратить (остальное — запас)
HERE = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(HERE, "seen_lots.json")
TOKEN_FILE = os.path.join(HERE, "api_token.json")  # старые версии хранили тут токен — удаляем
ID_RE = re.compile(r"^[0-9a-z]{4,5}$")

log = logging.getLogger("tracker")


# ----------------------------- Предметы -----------------------------
def norm(name):
    return name.lower().replace("ё", "е").replace("«", "").replace("»", "").strip()


def _listing(region):
    """Список предметов из официальной базы EXBO (скачивается раз в неделю)."""
    path = os.path.join(HERE, f"listing_{region}.json")
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > 7 * 86400:
        log.info("Скачиваю справочник предметов…")
        r = requests.get(LISTING_URL.format(region=region), timeout=60)
        r.raise_for_status()
        with open(path, "w", encoding="utf-8") as f:
            f.write(r.text)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _id_and_name(it):
    item_id = str(it.get("data", "")).rsplit("/", 1)[-1].replace(".json", "")
    ru = (it.get("name") or {}).get("lines", {}).get("ru")
    return item_id, ru


def load_listing(region):
    """Справочник id → русское название."""
    names = {}
    for it in _listing(region):
        item_id, ru = _id_and_name(it)
        if ru:
            names[item_id] = ru
    return names


def load_artifacts(region):
    """Все артефакты из базы игры: [(id, название)] по алфавиту."""
    arts = []
    for it in _listing(region):
        if "/artefact/" in str(it.get("data", "")):
            item_id, ru = _id_and_name(it)
            if ru:
                arts.append((item_id, ru))
    return sorted(arts, key=lambda a: a[1].lower())


# Категории предметов. Запчасти и инструменты в базе игры лежат вместе с прочими материалами,
# их отличаем по названию («Дешевые запчасти», «Продвинутые инструменты» …).
CATEGORY_NAMES = {
    "artefact": "Артефакты", "armor": "Броня", "weapon": "Оружие", "parts": "Запчасти", "tools": "Инструменты",
    "attachment": "Обвесы", "misc": "Материалы", "supply": "Расходники", "bullet": "Патроны",
    "containers": "Контейнеры", "backpacks": "Рюкзаки", "grenade": "Гранаты", "other": "Прочее",
}
AUTO_CATEGORIES = ("artefact", "armor", "weapon", "parts", "tools")   # можно отслеживать целиком
CATEGORY_IN_LINE = {"artefact": "все артефакты", "armor": "вся броня", "weapon": "всё оружие",
                    "parts": "все запчасти", "tools": "все инструменты"}
RANK_NAMES = {"RANK_NEWBIE": "Новичок", "RANK_STALKER": "Сталкер", "RANK_VETERAN": "Ветеран",
              "RANK_MASTER": "Мастер", "RANK_LEGEND": "Легенда"}
NOT_TRADED = ("PERSONAL_ON_GET", "PERSONAL_DROP_ON_GET")   # личные сразу — на аукцион не попадают


def item_category(it, ru=None):
    cat = str(it.get("data", "")).split("/")[2] if str(it.get("data", "")).count("/") >= 3 else "other"
    name = (ru or "").lower()
    if cat in ("other", "misc") and "запчаст" in name:
        return "parts"
    if cat in ("other", "misc") and "инструмент" in name:
        return "tools"
    return {"medicine": "supply", "device": "other", "weapon_modules": "attachment"}.get(cat, cat)


_barter_cache = {}
_barter_failed = {"at": 0.0}


def barter_ids(region):
    """id предметов, которые получают бартером у торговцев (из базы EXBO, обновляется раз в неделю).
    Такие предметы трекер не берёт в «категории целиком»: их делает кто угодно, на аукционе это не
    редкость из ящиков. None — список не удалось получить (тогда ничего не исключаем)."""
    path = os.path.join(HERE, f"barter_{region}.json")
    stale = not os.path.exists(path) or time.time() - os.path.getmtime(path) > 7 * 86400
    if stale and not os.environ.get("STALZONE_OFFLINE") and time.time() - _barter_failed["at"] > 600:
        try:
            r = requests.get(BARTER_URL.format(region=region), timeout=30)
            r.raise_for_status()
            json.loads(r.text)
            with open(path + ".tmp", "w", encoding="utf-8") as f:
                f.write(r.text)
            os.replace(path + ".tmp", path)
        except (requests.RequestException, ValueError, OSError) as e:
            _barter_failed["at"] = time.time()
            log.info("Список бартерных предметов не скачался (%s) — бартерные пока не отделяю", type(e).__name__)
    if not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    cached = _barter_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    ids = set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for place in data if isinstance(data, list) else []:
            for recipe in (place.get("recipes") or []) if isinstance(place, dict) else []:
                if isinstance(recipe, dict) and recipe.get("item"):
                    ids.add(str(recipe["item"]))
    except (OSError, ValueError, AttributeError):
        return None
    _barter_cache[path] = (mtime, ids)
    return ids


def load_catalog(region):
    """Все предметы: [{id, name, cat, rank, trade, barter}] — для поиска по категориям и «категорий целиком».
    trade — может попасть на аукцион; barter — получают бартером у торговцев."""
    barter = barter_ids(region) or set()
    out = []
    for it in _listing(region):
        item_id, ru = _id_and_name(it)
        if not ru:
            continue
        cat = item_category(it, ru)
        out.append({"id": item_id, "name": ru, "cat": cat if cat in CATEGORY_NAMES else "other",
                    "rank": str(it.get("color") or "DEFAULT"),
                    "trade": (it.get("status") or {}).get("state") not in NOT_TRADED,
                    "barter": item_id in barter})
    return out


def auto_categories(cfg):
    """Какие категории проверять целиком (старая галочка «все артефакты» тоже считается)."""
    cats = [c for c in (cfg.get("auto_categories") or []) if c in AUTO_CATEGORIES]
    if cfg.get("all_artifacts") and "artefact" not in cats:
        cats.insert(0, "artefact")
    return cats


def db_line(stats):
    """«База сделок: 12 345 сделок по 40 предметам за 3,2 дн., 4,1 МБ»."""
    if not stats.get("sales"):
        return "База сделок пока пустая — начнёт копиться с этой проверки"
    days = f"{stats['days']:.1f}".replace(".", ",")
    return (f"База сделок: {fmt_num(stats['sales'])} сделок по {stats['items']} предм. за {days} дн., "
            f"{str(stats['mb']).replace('.', ',')} МБ")


def watching_line(items, auto, cats=("artefact",)):
    """«Слежу за: …» — без сотен названий, если включены категории целиком."""
    own = [name for item_id, name in items if item_id not in auto]
    text = "Слежу за: " + (", ".join(own) if own else "—")
    if auto:
        what = ", ".join(CATEGORY_IN_LINE.get(c, c) for c in cats) or "все артефакты"
        text += f" + {what} ({len(auto)} шт.)"
    return text


def watch_items(cfg, names):
    """Что проверять: список из настроек + (если включено) категории целиком.
    Возвращает (предметы [(id, название)], id предметов, добавленных автоматически)."""
    items, have = [], set()
    for item_id, name in resolve_watch(cfg["watch"], names):
        if item_id not in have:
            have.add(item_id)
            items.append((item_id, name))
    auto = set()
    cats = auto_categories(cfg)
    if cats:
        catalog = sorted(load_catalog(cfg["region"]), key=lambda e: (cats.index(e["cat"]) if e["cat"] in cats else 99,
                                                                    e["name"].lower()))
        for entry in catalog:   # только то, что продаётся и не делается бартером
            if entry["cat"] in cats and entry["trade"] and not entry["barter"] and entry["id"] not in have:
                have.add(entry["id"])
                auto.add(entry["id"])
                items.append((entry["id"], entry["name"]))
    return items, auto


def resolve_watch(watch, names):
    by_name = {}
    for item_id, ru in names.items():
        by_name.setdefault(norm(ru), item_id)
    result = []
    for w in watch:
        if ID_RE.match(w) and w in names:
            result.append((w, names[w]))
        elif norm(w) in by_name:
            item_id = by_name[norm(w)]
            result.append((item_id, names[item_id]))
        else:
            log.warning("Не нашёл предмет «%s» — проверь написание", w)
    return result


# ------------------------------- API -------------------------------
class AuthError(Exception):
    pass


class ApiError(RuntimeError):
    """API ответил ошибкой 4xx (кроме входа). status — код ответа."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def remove_old_token_file():
    """Старые версии хранили токен в api_token.json. Теперь токен живёт только
    в памяти, а лишний файл с доступом к API на диске держать незачем."""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            log.info("Удалил старый файл api_token.json — токен больше не хранится на диске")
    except OSError:
        pass


class Api:
    """Запросы к официальному API EXBO с учётом лимитов.

    Как входим:
      * демо (dapi) — встроенные публичные демо-ключи; поле «Токен» — только если заполнено;
      * боевой API — заголовки Client-Id / Client-Secret. Если API ответил 401/403,
        один раз меняем ключи на токен через EXBO и повторяем запрос;
      * на боевом API без ключей, но с «Токеном» — вход по токену.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.base = str(cfg["base_url"]).rstrip("/")
        self.demo = "://dapi." in self.base
        self.client_id = str(cfg.get("client_id") or "").strip()
        self.client_secret = str(cfg.get("client_secret") or "").strip()
        self.app_token = str(cfg.get("app_token") or "").strip()
        self.s = requests.Session()
        # запросы идут из нескольких потоков — пул соединений побольше
        self.s.mount("https://", requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=FETCH_THREADS + 4))
        self.min_gap = 0.3          # до 200 запросов в минуту, пока окно лимита не подтвердилось
        self._lock = threading.Lock()       # темп общий для всех потоков
        self._auth_lock = threading.Lock()
        self._next_slot = 0.0               # когда можно отправить следующий запрос
        self._resets = []           # моменты сброса лимита из ответов API — по ним узнаём его окно
        self.paced = False
        self.bearer = None          # токен от EXBO — только в памяти
        self.oauth_tried = False
        remove_old_token_file()
        self.mode = self._pick_mode()

    # --- вход ---
    def _pick_mode(self):
        if self.demo:
            if self.app_token:
                log.info("Вход: демо-API, токен из настроек")
                return "token"
            log.info("Вход: демо-API, встроенные демо-ключи (тестовые данные, не настоящий аукцион)")
            return "demo"
        if self.client_id and self.client_secret:
            if self.app_token:
                log.info("Поле «Токен» не использую: на боевом API вход по Client ID и Client Secret")
            log.info("Вход: боевой API, Client ID и Client Secret")
            return "keys"
        if self.app_token:
            log.info("Вход: боевой API, токен из настроек")
            return "token"
        raise AuthError("Нет ключей API: вставь Client ID и Client Secret в настройках "
                        "(их присылает @stalzone_api_bot после одобрения заявки).")

    def _headers(self):
        if self.mode == "demo":
            return {"Client-Id": DEMO_CLIENT_ID, "Client-Secret": DEMO_CLIENT_SECRET}
        if self.mode == "token":
            return {"Authorization": f"Bearer {self.app_token}"}
        if self.bearer:
            return {"Authorization": f"Bearer {self.bearer}"}
        return {"Client-Id": self.client_id, "Client-Secret": self.client_secret}

    def _get_oauth_token(self):
        """Запасной путь: обменять ключи на токен приложения. Токен или None."""
        try:
            r = requests.post(OAUTH_URL, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "",
            }, timeout=30)
        except requests.RequestException as e:
            log.warning("Сервер входа EXBO не ответил (%s)", type(e).__name__)
            return None
        if r.status_code in (400, 401):
            log.warning("EXBO не принял Client ID / Client Secret (ответ %s)", r.status_code)
            return None
        if r.status_code >= 400:
            log.warning("Сервер входа EXBO ответил %s", r.status_code)
            return None
        try:
            token = r.json().get("access_token")
        except (ValueError, AttributeError):
            token = None
        if not token:
            log.warning("EXBO не прислал токен")
            return None
        log.info("Получил токен от EXBO — дальше вхожу по нему")
        return token

    def _auth_hint(self, code):
        if self.mode == "demo":
            return (f"Демо-API не пустил по встроенным ключам (ответ {code}). Возможно, EXBO сменила "
                    "демо-ключи — выключи «Демо-режим» и вставь свои Client ID и Client Secret.")
        if self.mode == "token":
            if self.demo:
                return (f"Демо-API не принял токен из настроек (ответ {code}). Очисти поле «Токен» — "
                        "для демо ключи уже встроены.")
            return (f"API не принял токен из настроек (ответ {code}). Вставь Client ID и Client Secret "
                    "из @stalzone_api_bot, а поле «Токен» очисти.")
        return (f"API не пустил по ключам (ответ {code}). Проверь в настройках: Client ID и Client Secret "
                "скопированы целиком, без лишних символов; если сбрасывал секрет в @stalzone_api_bot — "
                "вставь новый; заявка в боте одобрена.")

    # --- запрос с учётом лимитов ---
    def _wait_turn(self):
        """Очередь на отправку: запросы из всех потоков идут не чаще, чем раз в min_gap."""
        with self._lock:
            now = time.time()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self.min_gap
        if slot > now:
            time.sleep(slot - now)

    def _try_oauth(self, sent, code):
        """Ключи в заголовках не приняли — один раз (на все потоки) пробуем токен EXBO.
        True — можно повторить запрос."""
        if self.mode != "keys":
            return False
        with self._auth_lock:
            if self.bearer and "Authorization" not in sent:
                return True   # другой поток уже получил токен — просто повторим
            if self.oauth_tried:
                return False
            self.oauth_tried = True
            log.info("API не принял ключи в заголовках (ответ %s) — пробую войти через токен EXBO", code)
            self.bearer = self._get_oauth_token()
            return bool(self.bearer)

    def get(self, path, params):
        url = f"{self.base}/{path}"
        delay = 5
        for _ in range(6):
            self._wait_turn()
            headers = self._headers()
            try:
                r = self.s.get(url, params=params, headers=headers, timeout=30)
            except requests.RequestException as e:
                log.warning("Сеть: %s — повтор через %s с", type(e).__name__, delay)
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            self._respect_ratelimit(r)
            if r.status_code in (401, 403):
                if self._try_oauth(headers, r.status_code):
                    continue
                raise AuthError(self._auth_hint(r.status_code))
            if r.status_code == 429 or r.status_code >= 500:
                log.warning("API ответил %s — жду %s с", r.status_code, delay)
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            if r.status_code >= 400:
                try:  # API объясняет ошибку в поле title, например «Invalid item id: …»
                    why = str(r.json().get("title") or "")[:120]
                except (ValueError, AttributeError):
                    why = ""
                raise ApiError(r.status_code, f"API ответил {r.status_code}" + (f" ({why})" if why else "")
                               + f" на запрос {path}")
            self._adapt_pace(r)
            try:
                return r.json()
            except ValueError:
                raise RuntimeError(f"API прислал непонятный ответ на запрос {path}") from None
        raise RuntimeError(f"API не отвечает: {path}")

    def _adapt_pace(self, r):
        """Ускоряемся, когда точно знаем лимит: если момент сброса лимита сдвигается ровно
        на минуту, окно — минута, и можно тратить до 85% лимита (400/мин → запрос раз в ~0,18 с).
        Остаток лимита всё равно проверяется в каждом ответе (_respect_ratelimit)."""
        if self.paced:
            return
        try:
            limit = int(float(r.headers.get("x-ratelimit-limit")))
            reset = float(r.headers.get("x-ratelimit-reset"))
        except (TypeError, ValueError):
            return
        if reset > 1e12:
            reset /= 1000
        with self._lock:
            if self.paced or (self._resets and abs(reset - self._resets[-1]) < 1):
                return
            self._resets = self._resets[-4:] + [reset]
            if len(self._resets) >= 2 and 55 <= self._resets[-1] - self._resets[-2] <= 65 and limit >= 100:
                self.min_gap = max(0.15, 60 / (limit * RATE_SHARE))
                self.paced = True
            else:
                return
        log.info("Лимит API: %s запросов в минуту — проверяю быстрее (запрос раз в %.2f с)",
                 limit, self.min_gap)

    def _respect_ratelimit(self, r):
        """Если лимит почти исчерпан — все потоки ждут до его сброса."""
        remaining = r.headers.get("x-ratelimit-remaining")
        reset = r.headers.get("x-ratelimit-reset")
        if remaining is None or reset is None:
            return
        try:
            if int(float(remaining)) > 2:
                return
            val = float(reset)
            if val > 1e12:  # API присылает момент сброса в миллисекундах
                val /= 1000
            sleep_for = val - time.time() if val > 1e9 else val
        except ValueError:
            try:
                dt = datetime.fromisoformat(reset.replace("Z", "+00:00"))
                sleep_for = (dt - datetime.now(timezone.utc)).total_seconds()
            except ValueError:
                sleep_for = 30
        sleep_for = max(1.0, min(sleep_for, 90.0))
        with self._lock:
            already = self._next_slot > time.time() + sleep_for - 1
            self._next_slot = max(self._next_slot, time.time() + sleep_for)
        if not already:
            log.info("Лимит запросов почти исчерпан — пауза %.0f с", sleep_for)
        time.sleep(sleep_for)

    def lots(self, region, item_id, sort, order):
        return self.get(f"{region}/auction/{item_id}/lots", {
            "limit": 100, "offset": 0, "sort": sort, "order": order, "additional": "true",
        }).get("lots", [])

    def lots_all(self, region, item_id, max_pages=LOT_PAGES):
        """Все лоты предмета (до max_pages × 100), от дешёвого выкупа к дорогому.
        Нужны все: перепродать дороже самого дешёвого такого же лота не получится."""
        out = []
        for page in range(max_pages):
            data = self.get(f"{region}/auction/{item_id}/lots", {
                "limit": 100, "offset": page * 100, "sort": "buyout_price", "order": "asc",
                "additional": "true",
            })
            lots = data.get("lots", [])
            out.extend(lots)
            total = int(_num(data.get("total")))
            if len(lots) < 100 or (total and len(out) >= total):
                break
        return out

    def history(self, region, item_id, since, max_pages=HISTORY_PAGES):
        out = []
        for page in range(max_pages):
            data = self.get(f"{region}/auction/{item_id}/history", {
                "limit": 100, "offset": page * 100, "additional": "true",
            })
            prices = data.get("prices", [])
            out.extend(prices)
            if len(prices) < 100 or any(parse_time(p["time"]) < since for p in prices):
                break
        return [p for p in out if parse_time(p["time"]) >= since]

    def history_since(self, region, item_id, stop_ts, max_pages=HISTORY_PAGES):
        """Сделки от новых к старым, пока не дойдём до момента stop_ts (дальше — уже известные)
        или до лимита страниц. Возвращает (сделки, итог): итог "end" — история кончилась
        (у нас всё, что есть), "stop" — дошли до stop_ts, "cap" — упёрлись в лимит страниц."""
        out = []
        for page in range(max_pages):
            prices = self.get(f"{region}/auction/{item_id}/history", {
                "limit": 100, "offset": page * 100, "additional": "true",
            }).get("prices", [])
            out.extend(prices)
            if len(prices) < 100:
                return out, "end"
            try:
                if min(parse_time(p["time"]).timestamp() for p in prices) <= stop_ts:
                    return out, "stop"
            except (KeyError, TypeError, ValueError):
                return out, "stop"
        return out, "cap"


# --------------------------- Логика поиска ---------------------------
_FRACTION_RE = re.compile(r"\.(\d+)")


def parse_time(s):
    """Время из API → datetime с часовым поясом. Терпимо к любой длине долей секунды
    (старые версии Python понимают только 3 или 6 знаков) и к времени без пояса (считаем UTC)."""
    s = str(s).strip().replace("Z", "+00:00")
    s = _FRACTION_RE.sub(lambda m: "." + (m.group(1) + "000000")[:6], s, count=1)
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def bucket_of(additional):
    """Для артефактов цена зависит от качества и заточки — сравниваем внутри «корзины»."""
    if not isinstance(additional, dict):
        return None
    qlt, ptn = additional.get("qlt"), additional.get("ptn")
    if qlt is None and ptn is None:
        return None
    ptn = int(ptn or 0)
    return (int(qlt or 0), min(ptn - ptn % 5, 15))


Q_NAMES = ["обычный", "необычный", "особый", "редкий", "исключительный", "легендарный"]


def _q_name(q):
    return Q_NAMES[q] if 0 <= q < len(Q_NAMES) else str(q)


def bucket_label(b):
    if b is None:
        return ""
    q, p = b
    return f" [{_q_name(q)}, +{p}{'' if p == 15 else '…+' + str(p + 4)}]"


def grade_of(additional):
    """Точные качество и заточка артефакта (qlt, ptn); у обычных предметов — None."""
    if bucket_of(additional) is None:
        return None
    return int(_num(additional.get("qlt"))), int(_num(additional.get("ptn")))


def grade_label(g):
    return "" if g is None else f" [{_q_name(g[0])}, +{g[1]}]"


def weighted_median(pairs):
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    acc = 0
    for v, w in pairs:
        acc += w
        if acc >= total / 2:
            return v
    return None


def _num(x):
    """Число из ответа API; мусор → 0."""
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


# ------------------- Формат цен: за весь лот или за штуку -------------------
FORMAT_MIN_GROUP = 3      # столько записей с одинаковым amount, чтобы доверять их медиане
FORMAT_MIN_RECORDS = 20   # и столько записей во всех таких группах вместе


def amount_slope(records, key):
    """Как цена зависит от количества — наклон log(цена) от log(amount):
    около 1 — цена за весь лот, около 0 — за штуку, None — данных мало, чтобы судить.
    Устойчиво к выбросам: медиана внутри каждой группы одинакового amount,
    затем медиана попарных наклонов между группами (метод Тейла — Сена)."""
    groups = {}
    for r in records:
        if bucket_of(r.get("additional")) is not None:
            continue  # у артефактов цена зависит от качества и заточки, а не от количества
        amount, price = int(_num(r.get("amount"))), _num(r.get(key))
        if amount > 0 and price > 0:
            groups.setdefault(amount, []).append(math.log(price))
    used = [v for v in groups.values() if len(v) >= FORMAT_MIN_GROUP]
    if len(used) < 2 or sum(len(v) for v in used) < FORMAT_MIN_RECORDS:
        return None
    pts = [(math.log(a), statistics.median(v)) for a, v in groups.items() if len(v) >= FORMAT_MIN_GROUP]
    xs = [x for x, _ in pts]
    if max(xs) - min(xs) < math.log(3) - 1e-9:
        return None  # количества почти одинаковые — по ним не понять
    slopes = [(y2 - y1) / (x2 - x1)
              for i, (x1, y1) in enumerate(pts) for x2, y2 in pts[i + 1:]]
    return statistics.median(slopes)


def detect_total(records, key):
    """True — цена за весь лот, False — за штуку, None — не ясно."""
    s = amount_slope(records, key)
    if s is None:
        return None
    if s >= 0.6:
        return True
    if s <= 0.35:
        return False
    return None


def _per_what(total):
    return "за весь лот" if total else "за штуку"


class PriceFormat:
    """Помнит, за что API отдаёт цены. По каждому предмету решает по его же данным;
    если по предмету не ясно — берёт вывод, сделанный по другим предметам;
    пока выводов нет — считает «за весь лот»."""

    WHERE = {"history": "в истории сделок", "lots": "в лотах"}

    def __init__(self):
        self.known = {}      # "history" / "lots" -> (за лот?, по какому предмету решили)
        self.warned = set()

    def total(self, kind, records, key, name):
        found = detect_total(records, key)
        known = self.known.get(kind)
        if found is None:
            return known[0] if known else True
        if known is None:
            self.known[kind] = (found, name)
            log.info("Формат цен %s: %s (определил по «%s»)", self.WHERE[kind], _per_what(found), name)
        elif known[0] != found and kind not in self.warned:
            self.warned.add(kind)
            log.warning("⚠ Формат цен %s по «%s» вышел «%s», а раньше по «%s» — «%s». Для каждого "
                        "предмета беру его собственный вывод. Пришли этот журнал.",
                        self.WHERE[kind], name, _per_what(found), known[1], _per_what(known[0]))
        return found


def history_window(sales, hours, now=None):
    """Сколько часов реально покрывают сделки. История берётся максимум
    HISTORY_PAGES × 100 записей: если упёрлись в лимит, окно короче history_hours —
    тогда считаем его от самой старой полученной сделки до текущего момента."""
    if len(sales) < HISTORY_PAGES * 100:
        return float(hours)
    times = []
    for s in sales:
        try:
            times.append(parse_time(s["time"]))
        except (KeyError, TypeError, ValueError):
            pass
    if not times:
        return float(hours)
    now = now or datetime.now(timezone.utc)
    span = (now - min(times)).total_seconds() / 3600
    return max(1.0, min(float(hours), span))


GRADES = "_grades"      # в рынке артефакта: сделки по точным качеству и заточке
FALLBACK = "_fallback"  # рынок за LONG_DAYS — если за обычное окно сделок мало
WINDOW = "_window_h"    # за сколько часов посчитан рынок
PAIRS = "_pairs"        # сами сделки обычного предмета (цена_за_шт, штук) — для шанса продажи
SPECIAL_KEYS = (GRADES, FALLBACK, WINDOW, PAIRS)


def market_prices(sales, min_sales, hours=48, total=True, window=None):
    """Рыночная цена за штуку: взвешенная медиана сделок.
    total — в истории цена за весь лот (True) или уже за штуку (False).
    window — сколько часов реально покрывают сделки (если известно точно, например из своей базы).
    Ключи: None — обычный предмет; (качество, диапазон заточки) — артефакт (для журнала).
    Для оценки артефактов ещё хранятся сделки по точным качеству и заточке (ключ GRADES).
    Возвращает {ключ: (цена_за_шт, число_сделок, штук_в_сутки)}."""
    window = window or history_window(sales, hours)
    groups, grades = {}, {}
    for s in sales:
        amount, price = int(_num(s.get("amount"))), _num(s.get("price"))
        if amount <= 0 or price <= 0:
            continue
        unit = price / amount if total else price
        groups.setdefault(bucket_of(s.get("additional")), []).append((unit, amount))
        grade = grade_of(s.get("additional"))
        if grade is not None:
            grades.setdefault(grade, []).append((unit, amount))
    result = {}
    for b, pairs in groups.items():
        if len(pairs) >= min_sales:
            per_day = sum(a for _, a in pairs) / max(window, 1.0) * 24
            result[b] = (weighted_median(pairs), len(pairs), per_day)
    if result:
        result[WINDOW] = window
        if None in result:
            result[PAIRS] = groups[None]
        if grades:
            result[GRADES] = {"pairs": grades, "window": window, "min_sales": min_sales}
    return result


def _market_for_one(market, additional):
    grade = grade_of(additional)
    if grade is None:
        return (market[None], None, market.get(WINDOW)) if None in market else None
    info = market.get(GRADES)
    if not info:
        return None
    q, p = grade
    pairs = [x for (gq, gp), lst in info["pairs"].items() if gq == q and p - 4 <= gp <= p for x in lst]
    if len(pairs) < info["min_sales"]:
        return None
    per_day = sum(a for _, a in pairs) / max(info["window"], 1.0) * 24
    return (weighted_median(pairs), len(pairs), per_day), bucket_of(additional), info["window"]


def market_for(market, additional):
    """Цена по сделкам для конкретного лота: ((цена, сделок, штук_в_сутки), корзина, окно_в_часах) или None.
    Артефакт оцениваем только по сделкам того же качества и заточки не выше, чем у лота
    (от −4 до той же): сделки с большей заточкой завысили бы цену. Если за обычное окно таких
    сделок мало — смотрим длинное окно из своей базы (FALLBACK). Мало и там — не оцениваем."""
    found = _market_for_one(market, additional)
    if found is None and market.get(FALLBACK):
        found = _market_for_one(market[FALLBACK], additional)
    return found


def price_trend(sales, additional, total=True, min_sales=5, now=None):
    """Как изменилась цена: медиана за последние сутки против медианы за дни до этого, в %.
    Сделки отбираются так же, как для оценки лота. None — данных мало (нужны своя база и ≥ min_sales)."""
    grade = grade_of(additional)
    now = now or time.time()
    fresh, old = [], []
    for s in sales:
        if "ts" not in s:
            continue
        g = grade_of(s.get("additional"))
        if grade is None:
            if g is not None:
                continue
        elif g is None or g[0] != grade[0] or not grade[1] - 4 <= g[1] <= grade[1]:
            continue
        amount, price = int(_num(s.get("amount"))), _num(s.get("price"))
        if amount <= 0 or price <= 0:
            continue
        (fresh if now - s["ts"] <= 86400 else old).append((price / amount if total else price, amount))
    if len(fresh) < min_sales or len(old) < min_sales:
        return None
    return (weighted_median(fresh) / weighted_median(old) - 1) * 100


def comparable_floor(lot, lots, total=True):
    """Самая низкая цена за штуку среди ДРУГИХ лотов, которые не хуже этого:
    у артефактов — качество и заточка не ниже, у остальных предметов — любой лот.
    Дороже неё перепродать не выйдет: покупатель возьмёт тот лот. None — сравнить не с чем."""
    grade = grade_of(lot.get("additional"))
    best = None
    for other in lots:
        if other is lot:
            continue
        amount, raw = int(_num(other.get("amount"))), _num(other.get("buyoutPrice"))
        if amount <= 0 or raw <= 0:
            continue
        other_grade = grade_of(other.get("additional"))
        if grade is None:
            if other_grade is not None:
                continue
        elif other_grade is None or other_grade[0] < grade[0] or other_grade[1] < grade[1]:
            continue
        unit = raw / amount if total else raw
        best = unit if best is None else min(best, unit)
    return best


def _pairs_for_one(market, additional):
    grade = grade_of(additional)
    if grade is None:
        return (market.get(PAIRS), market.get(WINDOW)) if None in market and market.get(PAIRS) else None
    info = market.get(GRADES)
    if not info:
        return None
    q, p = grade
    pairs = [x for (gq, gp), lst in info["pairs"].items() if gq == q and p - 4 <= gp <= p for x in lst]
    return (pairs, info["window"]) if len(pairs) >= info["min_sales"] else None


def deal_pairs(market, additional):
    """Сделки, по которым оценён лот: ([(цена_за_шт, штук)], окно_в_часах) — тот же отбор, что в market_for."""
    found = _pairs_for_one(market, additional)
    if found is None and market.get(FALLBACK):
        found = _pairs_for_one(market[FALLBACK], additional)
    return found


def competitors(lot, lots, price, total=True, spread=0.05):
    """Сколько других таких же или лучших лотов висит почти по той же цене (до +5%) — делят покупателей."""
    grade = grade_of(lot.get("additional"))
    n = 0
    for other in lots:
        if other is lot:
            continue
        amount, raw = int(_num(other.get("amount"))), _num(other.get("buyoutPrice"))
        if amount <= 0 or raw <= 0:
            continue
        og = grade_of(other.get("additional"))
        if grade is None:
            if og is not None:
                continue
        elif og is None or og[0] < grade[0] or og[1] < grade[1]:
            continue
        if (raw / amount if total else raw) <= price * (1 + spread):
            n += 1
    return n


CHANCE_HOURS = 24   # шанс продать за сутки
CHANCE_CAP = 0.95   # наверняка не бывает: API не знает, сколько людей хотят купить
OBSERVED_TRUST = 15  # после стольких своих наблюдений лотов формула и наблюдения весят поровну


def poisson_at_least(lam, k):
    """Вероятность, что за время придёт хотя бы k покупателей, если в среднем их lam."""
    if lam <= 0:
        return 0.0
    term = math.exp(-lam)
    below = term
    for i in range(1, k):
        term *= lam / i
        below += term
    return max(0.0, 1.0 - below)


def _rate_for(chance, need):
    """Сколько покупателей в среднем нужно, чтобы с вероятностью chance пришли хотя бы need."""
    lo, hi = 0.0, 500.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if poisson_at_least(mid, need) < chance:
            lo = mid
        else:
            hi = mid
    return hi


def liquidity_label(days):
    if days is None:
        return ""
    return "высокая" if days < 1 else "средняя" if days < 5 else "низкая"


def sale_chance(price, amount, pairs, window_h, comp=0, trend=None, age=None, hours=CHANCE_HOURS,
                supply=None, observed=None):
    """Примерный шанс продать лот за hours часов по цене price за штуку. Своя формула, не знание.
    Покупатели приходят случайно (пуассоновский поток) с частотой прошлых сделок этой корзины, и она
      × уверенность: при малом числе сделок частота ненадёжна — n/(n+2) (5 сделок — ×0,71),
      × доля сделок, где платили не меньше price (со сглаживанием: никогда не 0 и не 100%),
      ÷ (1 + 0,35 × конкурентов почти по той же цене, до +5%),
      × ликвидность: за сколько дней рынок разберёт похожие лоты, что уже висят (до +30% к цене);
        запас больше суток — продавцы перебивают цену друг друга, шанс ниже,
      × тренд (рынок за сутки упал на 10% — ×0,8) и «давно висит» (лот час никто не купил даже со скидкой).
    Чтобы продать amount штук, нужно ~amount / (обычный размер сделки) покупателей.
    observed — (продано за сутки, всего) по лотам, за которыми трекер следил сам: чем их больше,
    тем сильнее итог опирается на них, а не на формулу.
    Возвращает {chance 0…1, hours — ожидаемое время продажи, week — шанс за неделю, …} или None."""
    if not pairs or price <= 0 or amount <= 0:
        return None
    n = len(pairs)
    window_h = max(float(window_h or 0), 1.0)
    per_day = n / window_h * 24                               # сделок в сутки
    confidence = n / (n + 2)
    above = sum(1 for unit, _ in pairs if unit >= price * 0.995)
    share = (above + 1) / (n + 2)
    size = max(1.0, statistics.median(a for _, a in pairs))   # обычный размер одной сделки
    need = min(50, max(1, math.ceil(amount / size - 1e-9)))   # сколько покупателей нужно
    comp = int(comp or 0)
    comp_f = 1 / (1 + 0.35 * min(comp, 20))
    supply_days, liq_f = None, 1.0
    if supply is not None and per_day > 0:
        supply_days = int(supply) / per_day
        liq_f = 1 / (1 + 0.08 * max(0.0, supply_days - 1))
    trend_f = 1.0 if trend is None else min(1.2, max(0.5, 1 + float(trend) / 50))
    stale_f = 1.0
    if age is not None and age > STALE_MINUTES:
        stale_f = 0.55 if age > 3 * STALE_MINUTES else 0.75
    rate = per_day * confidence * share * comp_f * liq_f * trend_f * stale_f   # покупателей в сутки для лота
    model = poisson_at_least(rate * hours / 24, need)
    chance, weight, seen = model, 0.0, None
    if observed and observed[1] > 0:
        sold, total = int(observed[0]), int(observed[1])
        seen = ((sold + 0.5) / (total + 1)) ** need             # доля лотов, проданных за сутки
        weight = total / (total + OBSERVED_TRUST)
        chance = weight * seen + (1 - weight) * model
    if weight:   # частота покупателей, которая даёт итоговый шанс, — для времени продажи
        rate = _rate_for(min(chance, 0.999), need) * 24 / hours if chance > 0 else 0.0
    return {"chance": min(CHANCE_CAP, max(0.01, chance)),
            "hours": need / rate * 24 if rate > 0 else None,
            "week": min(CHANCE_CAP, max(0.01, poisson_at_least(rate * 7, need))),
            "per_day": per_day, "confidence": confidence, "share": share, "size": size, "need": need,
            "comp": comp, "supply": None if supply is None else int(supply), "supply_days": supply_days,
            "liq_f": liq_f, "trend_f": trend_f, "stale_f": stale_f, "model": model,
            "observed": [int(observed[0]), int(observed[1])] if observed else None, "weight": weight}


def chance_label(c):
    return "высокий" if c >= 0.7 else "средний" if c >= 0.4 else "низкий"


def resale_price(lot, lots, m, total=True):
    """Реальная цена перепродажи за штуку: не выше цены по сделкам и чуть ниже самого
    дешёвого такого же или лучшего лота. Возвращает (цена, дешевле_всего_такой_же)."""
    floor = comparable_floor(lot, lots, total)
    return (min(m, floor * UNDERCUT) if floor else m), floor


def lot_age_minutes(lot, now=None):
    try:
        now = now or datetime.now(timezone.utc)
        return (now - parse_time(lot.get("startTime"))).total_seconds() / 60
    except (TypeError, ValueError):
        return None


def find_deals(lots, market, cfg, total=True):
    """Лоты с выкупом заметно дешевле и прошлых сделок, и всех таких же лотов на аукционе.
    total — buyoutPrice за весь лот (True) или за штуку."""
    lots = list(lots)
    deals = []
    for lot in lots:
        amount, raw = int(_num(lot.get("amount"))), _num(lot.get("buyoutPrice"))
        if amount <= 0 or raw <= 0:
            continue  # лот только со ставками — пропускаем
        found = market_for(market, lot.get("additional"))
        if not found:
            continue
        (hist, n, per_day), b, window_h = found
        unit = raw / amount if total else raw
        if unit > hist * (1 - cfg["discount"]):
            continue  # не дешевле прошлых сделок — дальше не считаем
        resale, floor = resale_price(lot, lots, hist, total)
        if unit > resale * (1 - cfg["discount"]):
            continue  # рядом висят такие же почти по той же цене — это не скидка
        cost = unit * amount              # сколько заплатить за весь лот
        profit = resale * (1 - cfg["fee"]) * amount - cost
        if profit < cfg["min_profit"]:
            continue
        deals.append({"lot": lot, "bucket": b, "grade": grade_of(lot.get("additional")),
                      "unit": unit, "market": resale, "hist": hist, "floor": floor, "n": n,
                      "per_day": per_day, "pct": (1 - unit / resale) * 100, "profit": profit,
                      "amount": amount, "buyout": cost, "cost": cost, "age": lot_age_minutes(lot),
                      "window_h": window_h})
    deals.sort(key=lambda d: -d["profit"])
    return deals


def find_bid_deals(lots, market, cfg, now=None, total=True):
    """Лоты со ставками: скоро закончатся, а текущая цена ставки сильно ниже рынка.
    total — цены лота за весь лот (True) или за штуку. Суммы в находке — за весь лот."""
    now = now or datetime.now(timezone.utc)
    lots = list(lots)
    deals = []
    for lot in lots:
        amount = int(_num(lot.get("amount")))
        end = lot.get("endTime")
        if amount <= 0 or not end:
            continue
        minutes_left = (parse_time(end) - now).total_seconds() / 60
        if not cfg["bid_min_left_minutes"] <= minutes_left <= cfg["bid_window_minutes"]:
            continue
        found = market_for(market, lot.get("additional"))
        if not found:
            continue
        (hist, n, per_day), b, window_h = found
        k = 1 if total else amount        # множитель «цена из API → сумма за лот»
        current = _num(lot.get("currentPrice")) * k
        need = current if current > 0 else _num(lot.get("startPrice")) * k
        if need <= 0:
            continue
        buyout = _num(lot.get("buyoutPrice")) * k
        if buyout and buyout <= need:
            continue  # выгоднее просто выкупить — это поймает обычный режим
        m, floor = resale_price(lot, lots, hist, total)
        max_bid = m * (1 - cfg["fee"]) * amount - cfg["min_profit"]
        if need >= max_bid:
            continue
        deals.append({"lot": lot, "bucket": b, "grade": grade_of(lot.get("additional")),
                      "market": m, "hist": hist, "floor": floor, "n": n, "per_day": per_day,
                      "amount": amount, "window_h": window_h,
                      "need": need, "max_bid": max_bid, "has_bids": current > 0,
                      "minutes_left": minutes_left,
                      "profit_now": m * (1 - cfg["fee"]) * amount - need})
    deals.sort(key=lambda d: -d["profit_now"])
    return deals


# ------------------------- Строка рынка для журнала -------------------------
def fmt_num(x):
    if 0 < x < 10 and abs(x - round(x)) > 0.05:
        return f"{x:.1f}".replace(".", ",")
    return f"{x:,.0f}".replace(",", " ")


def fmt_window(hours):
    """48 → «2 дн.», 6 → «6 ч»."""
    if not hours:
        return ""
    return f"{hours:.0f} ч" if hours < 36 else f"{hours / 24:.0f} дн."


def _deals_word(n):
    return "сделке" if n % 10 == 1 and n % 100 != 11 else "сделкам"


def range_keys(market):
    """Ключи рынка без служебных записей — для строки в журнале и проверок."""
    return [k for k in market if k not in SPECIAL_KEYS]


def main_bucket(market):
    """Обычный предмет — корзина None; у артефактов — самая торгуемая связка качество+заточка."""
    return None if None in market else max(range_keys(market), key=lambda k: market[k][1])


def lot_units(lots, bucket, total_lots):
    """Лоты этой корзины и их цены выкупа за штуку."""
    same = [lot for lot in lots
            if int(_num(lot.get("amount"))) > 0 and bucket_of(lot.get("additional")) == bucket]
    units = []
    for lot in same:
        raw = _num(lot.get("buyoutPrice"))
        if raw > 0:
            units.append(raw / int(_num(lot.get("amount"))) if total_lots else raw)
    return same, units


def price_mismatch(market, lots, total_lots):
    """Во сколько раз (≥5) медиана цены лотов за штуку расходится с рыночной, иначе None.
    Такое расхождение почти наверняка значит, что формат цен понят неверно.
    Проверяем только когда в лотах есть стаки: при amount = 1 формат ни на что не влияет."""
    if not market:
        return None
    b = main_bucket(market)
    m = market[b][0]
    same, units = lot_units(lots, b, total_lots)
    if len(units) < 3 or m <= 0 or max(int(_num(lot.get("amount"))) for lot in same) <= 1:
        return None
    ratio = statistics.median(units) / m
    if ratio >= 5 or ratio <= 0.2:
        return ratio if ratio >= 1 else 1 / ratio
    return None


def mismatch_warning(name, factor):
    return (f"⚠ {name}: цены лотов и сделок расходятся в ~{factor:.0f} раз — похоже, формат цен "
            "понят неверно. Находки по этому предмету не показываю, чтобы не было ложных. "
            "Пришли этот журнал.")


def describe_market(name, market, lots, hours, total_lots=True):
    """Строка для журнала: какую цену трекер считает рыночной — чтобы сверить с аукционом в игре."""
    if not market:
        return f"{name}: за {fmt_window(hours)} мало сделок — цену не считаю, лоты пропускаю"
    b = main_bucket(market)
    m, n, per_day = market[b]
    period = f" за {fmt_window(market.get(WINDOW))}" if market.get(WINDOW) else ""
    text = (f"{name}{bucket_label(b)}: рынок ~{fmt_rub(m)}/шт по {n} {_deals_word(n)}{period} "
            f"(~{fmt_num(per_day)} шт/сутки)")
    same, units = lot_units(lots, b, total_lots)
    if same:
        sizes = sorted(int(_num(lot.get("amount"))) for lot in same)
        text += f" · лотов: {len(same) if len(same) < 100 else '100+'}"
        if sizes[-1] > 1:
            text += f", обычно по {sizes[len(sizes) // 2]} шт"
    if units:
        text += f" · самый дешёвый выкуп {fmt_rub(min(units))}/шт"
    if len(range_keys(market)) > 1:
        text += f" · ещё вариантов качества/заточки: {len(range_keys(market)) - 1}"
    return text


# ---------------------------- Своя база сделок ----------------------------
class MarketDB:
    """Сделки копятся у тебя на ПК (файл market.db) между запусками.
    Поэтому у редких артефактов со временем набирается достаточно сделок для оценки,
    а у API запрашиваются только новые сделки — запросов меньше.
    Для каждого предмета помним, с какого момента история непрерывна (covered_from):
    без этого «штук в сутки» считалось бы неверно после разрыва."""

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS sales (
            region TEXT NOT NULL, item_id TEXT NOT NULL, ts REAL NOT NULL,
            amount INTEGER NOT NULL, price REAL NOT NULL,
            qlt INTEGER NOT NULL, ptn INTEGER NOT NULL,  -- -1 у обычных предметов
            extra TEXT NOT NULL,                          -- остальные поля additional (JSON)
            UNIQUE (region, item_id, ts, amount, price, qlt, ptn));
        CREATE TABLE IF NOT EXISTS coverage (
            region TEXT NOT NULL, item_id TEXT NOT NULL,
            covered_from REAL NOT NULL, last_ts REAL NOT NULL,
            PRIMARY KEY (region, item_id));
        CREATE TABLE IF NOT EXISTS lots (           -- все лоты, что видел трекер: продались ли и как быстро
            region TEXT NOT NULL, item_id TEXT NOT NULL, lot_key TEXT NOT NULL,
            start_ts REAL NOT NULL, end_ts REAL, first_seen REAL NOT NULL, last_seen REAL NOT NULL,
            amount INTEGER NOT NULL, price REAL NOT NULL, qlt INTEGER NOT NULL, ptn INTEGER NOT NULL,
            ratio REAL,                                 -- цена за шт / рыночная, когда увидели
            gone_ts REAL, outcome TEXT, sold_ts REAL,   -- пропал; sold / expired / removed
            PRIMARY KEY (region, item_id, lot_key));
    """

    def __init__(self, path=None, keep_days=14):
        self.path = path or os.path.join(HERE, "market.db")
        self.keep_days = max(1, int(keep_days))
        self.con = sqlite3.connect(self.path, timeout=30)
        self.con.execute("PRAGMA journal_mode=WAL")   # чтение не мешает записи
        self.con.executescript(self.SCHEMA)
        self.cleanup()

    def close(self):
        try:
            self.con.close()
        except sqlite3.Error:
            pass

    def cleanup(self):
        """Удаляем сделки старше keep_days — база не растёт бесконечно."""
        cutoff = time.time() - self.keep_days * 86400
        with self.con:
            self.con.execute("DELETE FROM sales WHERE ts < ?", (cutoff,))
            self.con.execute("DELETE FROM lots WHERE last_seen < ?", (cutoff,))
            self.con.execute("UPDATE coverage SET covered_from = ? WHERE covered_from < ?", (cutoff, cutoff))

    def coverage(self, region, item_id):
        return self.con.execute("SELECT covered_from, last_ts FROM coverage WHERE region = ? AND item_id = ?",
                                (region, item_id)).fetchone()

    @staticmethod
    def _row(region, item_id, p):
        try:
            ts = parse_time(p["time"]).timestamp()
        except (KeyError, TypeError, ValueError):
            return None
        amount, price = int(_num(p.get("amount"))), _num(p.get("price"))
        if amount <= 0 or price <= 0:
            return None
        add = p.get("additional") if isinstance(p.get("additional"), dict) else {}
        grade = grade_of(add)
        extra = {k: v for k, v in add.items()
                 if k not in ("qlt", "ptn") and isinstance(v, (int, float, str, bool))}
        return (region, item_id, ts, amount, price, grade[0] if grade else -1, grade[1] if grade else -1,
                json.dumps(extra, ensure_ascii=False, separators=(",", ":"), sort_keys=True) if extra else "")

    def stop_point(self, region, item_id, horizon_hours):
        """До какого момента качать историю: до последней известной сделки или (в первый раз)
        на horizon_hours назад."""
        cov = self.coverage(region, item_id)
        return cov[1] if cov else time.time() - horizon_hours * 3600

    def sync(self, api, region, item_id, horizon_hours):
        """Докачать новые сделки предмета (сеть + запись). Возвращает, сколько новых добавилось."""
        records, how = api.history_since(region, item_id, self.stop_point(region, item_id, horizon_hours))
        return self.store(region, item_id, records, how)

    def store(self, region, item_id, records, how):
        """Записать скачанные сделки (results of history_since). Возвращает, сколько новых."""
        now = time.time()
        cov = self.coverage(region, item_id)
        rows = [r for r in (self._row(region, item_id, p) for p in records) if r]
        oldest = min((r[2] for r in rows), default=now)
        newest = max([r[2] for r in rows] + ([cov[1]] if cov else []), default=now)
        if cov is None:
            # история кончилась — старше сделок нет вовсе; иначе непрерывно только до самой старой из полученных
            covered_from = 0.0 if how == "end" else oldest
        elif how == "cap":
            covered_from = oldest   # новых больше, чем влезло в страницы: разрыв, непрерывно только отсюда
        else:
            covered_from = cov[0]
        with self.con:
            before = self.con.total_changes
            self.con.executemany("INSERT OR IGNORE INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
            added = self.con.total_changes - before
            self.con.execute("INSERT OR REPLACE INTO coverage VALUES (?, ?, ?, ?)",
                             (region, item_id, covered_from, newest))
        return added

    def sales(self, region, item_id, since_ts):
        """Сделки из базы в том же виде, что из API, плюс ts — время в секундах."""
        out = []
        for ts, amount, price, qlt, ptn in self.con.execute(
                "SELECT ts, amount, price, qlt, ptn FROM sales WHERE region = ? AND item_id = ? AND ts >= ? "
                "ORDER BY ts DESC", (region, item_id, since_ts)):
            out.append({"ts": ts, "amount": amount, "price": price,
                        "additional": {"qlt": qlt, "ptn": ptn} if qlt >= 0 else {}})
        return out

    def find_sale(self, region, item_id, amount, price, since_ts):
        """Была ли сделка ровно на такой лот (штук и цена за весь лот) после since_ts — значит, его купили."""
        row = self.con.execute(
            "SELECT 1 FROM sales WHERE region = ? AND item_id = ? AND amount = ? AND ABS(price - ?) < 0.5 "
            "AND ts >= ? LIMIT 1", (region, item_id, int(amount), float(price), float(since_ts))).fetchone()
        return row is not None

    def observe_lots(self, region, item_id, lots, ratio_fn=lambda lot: None, now=None):
        """Запомнить лоты этой проверки; пропавшие разобрать: в истории есть сделка ровно на лот — продан,
        вышло время — истёк, иначе через 2 часа — снят продавцом."""
        now = now or time.time()
        rows = []
        for lot in lots:
            amount, price = int(_num(lot.get("amount"))), _num(lot.get("buyoutPrice"))
            if amount <= 0 or price <= 0:
                continue   # только со ставками — по ним не сверить
            try:
                start = parse_time(lot.get("startTime")).timestamp()
            except (TypeError, ValueError):
                continue
            try:
                end = parse_time(lot.get("endTime")).timestamp()
            except (TypeError, ValueError):
                end = None
            g = grade_of(lot.get("additional"))
            rows.append((region, item_id, lot_key(item_id, lot), start, end, now, now, amount, price,
                         g[0] if g else -1, g[1] if g else -1, ratio_fn(lot)))
        with self.con:
            self.con.executemany(
                "INSERT OR IGNORE INTO lots (region, item_id, lot_key, start_ts, end_ts, first_seen, last_seen, "
                "amount, price, qlt, ptn, ratio) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
            self.con.executemany(
                "UPDATE lots SET last_seen = ?, gone_ts = NULL WHERE region = ? AND item_id = ? AND lot_key = ? "
                "AND outcome IS NULL", [(now, region, item_id, r[2]) for r in rows])
            self.con.execute("UPDATE lots SET gone_ts = ? WHERE region = ? AND item_id = ? AND outcome IS NULL "
                             "AND gone_ts IS NULL AND last_seen < ?", (now, region, item_id, now))
            pending = self.con.execute(
                "SELECT lot_key, start_ts, end_ts, amount, price, gone_ts FROM lots WHERE region = ? AND item_id = ? "
                "AND outcome IS NULL AND gone_ts IS NOT NULL", (region, item_id)).fetchall()
            for key, start, end, amount, price, gone in pending:
                sold = self.con.execute(
                    "SELECT MIN(ts) FROM sales WHERE region = ? AND item_id = ? AND amount = ? AND ABS(price - ?) < 0.5 "
                    "AND ts >= ?", (region, item_id, amount, price, start - 60)).fetchone()[0]
                if sold is not None:
                    outcome = "sold"
                elif end and end <= gone + 300:
                    outcome = "expired"
                elif now - gone > 2 * 3600:
                    outcome = "removed"
                else:
                    continue
                self.con.execute("UPDATE lots SET outcome = ?, sold_ts = ? WHERE region = ? AND item_id = ? "
                                 "AND lot_key = ?", (outcome, sold, region, item_id, key))

    def lot_outcomes(self, region, item_id, grade=None, now=None, days=7, max_ratio=1.05):
        """(продано за сутки, всего) среди лотов, выставленных не дороже рынка (до +5%), той же корзины.
        Учитываются лоты с известным исходом за первые сутки: проданные, истёкшие, снятые после суток
        и всё ещё висящие дольше суток. Лоты, купленные раньше, чем их показал API, трекер не видит —
        поэтому оценка скорее осторожная."""
        now = now or time.time()
        sold = total = 0
        for start, last, gone, outcome, sold_ts, qlt, ptn, ratio in self.con.execute(
                "SELECT start_ts, last_seen, gone_ts, outcome, sold_ts, qlt, ptn, ratio FROM lots "
                "WHERE region = ? AND item_id = ? AND start_ts >= ?", (region, item_id, now - days * 86400)):
            if grade is None:
                if qlt != -1:
                    continue
            elif qlt != grade[0] or not grade[1] - 4 <= ptn <= grade[1]:
                continue
            if ratio is None or ratio > max_ratio:
                continue
            if outcome == "sold":
                total += 1
                sold += (sold_ts - start) <= 86400
            elif outcome == "expired":
                total += 1
            elif outcome == "removed":
                total += (gone - start) >= 86400
            elif gone is None and now - start >= 86400:
                total += 1
        return sold, total

    def window_hours(self, region, item_id, hours):
        """Сколько часов из последних hours покрыто непрерывной историей."""
        now = time.time()
        cov = self.coverage(region, item_id)
        start = max(cov[0], now - hours * 3600) if cov else now - hours * 3600
        return max(1.0, (now - start) / 3600)

    def stats(self):
        return self._stats(self.con, self.path)

    @staticmethod
    def _stats(con, path):
        rows, items, oldest = con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT item_id), MIN(ts) FROM sales").fetchone()
        size = sum(os.path.getsize(p) for p in (path, path + "-wal") if os.path.exists(p))
        return {"sales": rows, "items": items,
                "days": round((time.time() - oldest) / 86400, 1) if oldest else 0,
                "mb": round(size / 1048576, 1)}

    @classmethod
    def quick_stats(cls, path=None):
        """Статистика базы без её изменения (для окна настроек). None — базы ещё нет."""
        path = path or os.path.join(HERE, "market.db")
        if not os.path.exists(path):
            return None
        try:
            con = sqlite3.connect(path, timeout=5)
            try:
                return cls._stats(con, path)
            finally:
                con.close()
        except sqlite3.Error:
            return None


# ------------------------------ Один предмет ------------------------------
class Scanner:
    """Проверка одного предмета: рынок (с кэшем), лоты, формат цен, находки.
    Общая для консольного режима и приложения."""

    def __init__(self, api, cfg, quiet=(), db=None):
        self.api, self.cfg = api, cfg
        self.db = db             # своя база сделок (MarketDB) или None — тогда только последние часы из API
        self.total_hist = {}     # item_id -> цена в истории за весь лот? (для тренда)
        self.quiet = set(quiet)  # добавлены сами («все артефакты»): без отдельной строки на каждый
        self.fmt = PriceFormat()
        self.market_cache = {}   # item_id -> (когда посчитан, рынок)
        self.described = set()   # по каким предметам уже написали строку рынка
        self.mismatched = set()  # о каких предметах уже предупредили: цены лотов и сделок не сходятся
        self.skipped = set()     # предметы, которых API не знает (ответ 400/404)
        self.priced, self.unpriced = set(), set()  # для сводки по автодобавленным
        self.quiet_label = "Все артефакты"
        self.fields_logged = set()   # какие наборы полей лотов уже описали в журнале

    def summary(self):
        """Строка-сводка по автодобавленным артефактам (или None, если их нет)."""
        if not self.quiet:
            return None
        checked = len(self.priced) + len(self.unpriced)
        period = f"{LONG_DAYS} дн. в твоей базе" if self.db is not None else f"{self.cfg['history_hours']} ч"
        text = (f"{self.quiet_label}: рыночная цена есть у {len(self.priced)} из {checked} — остальные "
                f"почти не продавались (за {period}), их лоты пропускаю")
        unknown = len(self.skipped & self.quiet)
        if unknown:
            text += f". Ещё {unknown} API не знает"
        return text

    # Проверка предмета делится на три шага, чтобы сеть шла параллельно, а база и расчёты — по очереди:
    #   plan()    — главный поток: что запросить (по кэшу и базе);
    #   fetch()   — любой поток: только запросы к API;
    #   process() — главный поток: запись в базу, рынок, находки.
    def scan(self, item_id, name):
        """Всё подряд в одном потоке. Возвращает (лоты {ключ: лот}, находки-выкупы, находки-ставки).
        Лоты — None, если их не запрашивали (рынка нет или предмет пропущен)."""
        plan = self.plan(item_id)
        if plan is None:
            return None, [], []
        return self.process(item_id, name, plan, self.fetch(item_id, plan))

    def plan(self, item_id):
        """Что скачать для предмета. None — предмет пропускаем (API его не знает)."""
        if item_id in self.skipped:
            return None
        cfg = self.cfg
        cached = self.market_cache.get(item_id)
        need_hist = not cached or time.time() - cached[0] > cfg["history_refresh_minutes"] * 60
        stop = None
        if need_hist and self.db is not None:
            stop = self.db.stop_point(cfg["region"], item_id, max(cfg["history_hours"], LONG_DAYS * 24))
        # лоты нужны, если рынок есть или станет известен после обновления истории
        return {"hist": need_hist, "stop": stop, "lots": need_hist or bool(cached and cached[1])}

    def fetch(self, item_id, plan):
        """Только сеть — можно из любого потока. Ошибку не бросает, а кладёт в результат."""
        cfg, out = self.cfg, {}
        try:
            if plan["hist"]:
                if self.db is not None:
                    out["hist"] = self.api.history_since(cfg["region"], item_id, plan["stop"])
                else:
                    since = datetime.now(timezone.utc) - timedelta(hours=cfg["history_hours"])
                    out["hist_list"] = self.api.history(cfg["region"], item_id, since)
            if plan["lots"]:
                out["lots"] = self.api.lots_all(cfg["region"], item_id)
        except Exception as e:  # разберёт главный поток
            out["error"] = e
        return out

    def process(self, item_id, name, plan, fetched):
        """Главный поток: база, рынок, находки."""
        err = fetched.get("error")
        if err is not None:
            if isinstance(err, ApiError) and err.status in (400, 404):
                self.skipped.add(item_id)  # предмета нет на аукционе — не тратим на него запросы
                log.warning("%s: %s — больше не проверяю этот предмет", name, err)
                return None, [], []
            raise err
        if plan["hist"]:
            self.market_cache[item_id] = (time.time(), self._market(item_id, name, fetched))
        return self._scan(item_id, name, fetched.get("lots"))

    def _market(self, item_id, name, fetched):
        """Рынок предмета. Со своей базой: записать новые сделки, посчитать за history_hours,
        а для качеств и заточек, где сделок мало, — ещё и за LONG_DAYS (FALLBACK)."""
        cfg, hours = self.cfg, self.cfg["history_hours"]
        if self.db is None:
            sales = fetched.get("hist_list") or []
            total = self.fmt.total("history", sales, "price", name)
            self.total_hist[item_id] = total
            return market_prices(sales, cfg["min_sales"], hours, total)
        region = cfg["region"]
        long_h = max(hours, LONG_DAYS * 24)
        records, how = fetched.get("hist") or ([], "end")
        self.db.store(region, item_id, records, how)  # в первый раз — история сразу за неделю (если влезет)
        now = time.time()
        long_sales = self.db.sales(region, item_id, now - long_h * 3600)
        recent = [s for s in long_sales if s["ts"] >= now - hours * 3600]
        total = self.fmt.total("history", recent or long_sales, "price", name)
        self.total_hist[item_id] = total
        market = market_prices(recent, cfg["min_sales"], hours, total,
                               window=self.db.window_hours(region, item_id, hours))
        if long_h > hours and len(long_sales) > len(recent):
            longer = market_prices(long_sales, cfg["min_sales"], long_h, total,
                                   window=self.db.window_hours(region, item_id, long_h))
            if not range_keys(market):
                market = longer             # за обычное окно сделок мало — берём длинное целиком
            elif longer:
                market[FALLBACK] = longer   # для качеств и заточек, где за обычное окно сделок мало
        return market

    def _scan(self, item_id, name, raw):
        cfg = self.cfg
        quiet = item_id in self.quiet
        market = self.market_cache[item_id][1]
        if not market:
            if quiet:
                self.unpriced.add(item_id)
                self.priced.discard(item_id)
            elif item_id not in self.described:
                self.described.add(item_id)
                hours = max(cfg["history_hours"], LONG_DAYS * 24) if self.db is not None else cfg["history_hours"]
                log.info("%s", describe_market(name, market, [], hours))
            return None, [], []
        if quiet:
            self.priced.add(item_id)
            self.unpriced.discard(item_id)
        if raw is None:  # рынок появился, а лоты не запрашивали — заберём их сейчас
            raw = self.api.lots_all(cfg["region"], item_id)
        lots = {lot_key(item_id, lot): lot for lot in raw}  # все лоты: по ним видна реальная цена продажи
        lot_list = list(lots.values())
        if len(self.fields_logged) < 6:  # какие поля API присылает у лотов — пригодится для точности
            keys = tuple(sorted({str(k) for lot in lot_list if isinstance(lot.get("additional"), dict)
                                 for k in lot["additional"]}))
            if keys and keys not in self.fields_logged:
                self.fields_logged.add(keys)
                log.info("%s: в данных лотов есть поля %s — сейчас учитываю качество (qlt) "
                         "и заточку (ptn)", name, ", ".join(keys))
        total_lots = self.fmt.total("lots", lot_list, "buyoutPrice", name)
        if item_id not in self.described and not quiet:
            self.described.add(item_id)
            log.info("%s", describe_market(name, market, lot_list, cfg["history_hours"], total_lots))
        if self.db is not None and len(lot_list) < LOT_PAGES * 100:   # видны все лоты — следим, какие продаются
            def ratio(lot, market=market, total=total_lots):
                found = market_for(market, lot.get("additional"))
                amount, raw = int(_num(lot.get("amount"))), _num(lot.get("buyoutPrice"))
                if not found or amount <= 0 or raw <= 0 or not found[0][0]:
                    return None
                return (raw / amount if total else raw) / found[0][0]
            self.db.observe_lots(cfg["region"], item_id, lot_list, ratio)
        factor = price_mismatch(market, lot_list, total_lots)
        if factor:  # находки по такому предмету почти наверняка ложные — молчим
            if item_id not in self.mismatched:
                self.mismatched.add(item_id)
                log.warning("%s", mismatch_warning(name, factor))
            return lots, [], []
        # find_min_profit — порог пониже для особо редких (обычные находки приложение отсеет само)
        find_cfg = dict(cfg, min_profit=cfg["find_min_profit"]) if cfg.get("find_min_profit") is not None else cfg
        deals = find_deals(lots.values(), market, find_cfg, total_lots)
        bids = find_bid_deals(lots.values(), market, cfg, total=total_lots) if cfg.get("bids") else []
        if self.db is not None and (deals or bids):  # тренд: как цена изменилась за сутки
            history = self.db.sales(cfg["region"], item_id, time.time() - LONG_DAYS * 86400)
            for d in deals + bids:
                d["trend"] = price_trend(history, d["lot"].get("additional"),
                                         self.total_hist.get(item_id, True), cfg["min_sales"])
        for d in deals + bids:   # шанс продать по цене перепродажи
            found = deal_pairs(market, d["lot"].get("additional"))
            if found:
                comp = competitors(d["lot"], lot_list, d["market"], total_lots)
                supply = competitors(d["lot"], lot_list, d["market"], total_lots, spread=0.3)
                observed = (self.db.lot_outcomes(cfg["region"], item_id, grade_of(d["lot"].get("additional")))
                            if self.db is not None else None)
                d["chance"] = sale_chance(d["market"], d["amount"], found[0], found[1], comp, d.get("trend"),
                                          d.get("age") if "unit" in d else None, supply=supply,
                                          observed=observed if observed and observed[1] else None)
        return lots, deals, bids


def scan_pass(scanner, items, on_item, should_stop=lambda: False, on_progress=None):
    """Один проход по всем предметам. Сеть — параллельно (FETCH_THREADS потоков, заранее до FETCH_AHEAD
    предметов вперёд), база и расчёты — по порядку в этом потоке. Общий темп запросов держит Api.
    on_item(item_id, name, результат) — результат: (лоты, выкупы, ставки) или исключение.
    AuthError прерывает проход."""
    pool = ThreadPoolExecutor(max_workers=FETCH_THREADS)
    plans, futures, nxt = {}, {}, 0
    try:
        for i, (item_id, name) in enumerate(items):
            while nxt < len(items) and nxt < i + FETCH_AHEAD:
                ahead_id = items[nxt][0]
                plans[nxt] = scanner.plan(ahead_id)
                if plans[nxt] is not None:
                    futures[nxt] = pool.submit(scanner.fetch, ahead_id, plans[nxt])
                nxt += 1
            if should_stop():
                break
            if on_progress:
                on_progress(i, item_id, name)
            plan = plans.pop(i)
            if plan is None:
                on_item(item_id, name, (None, [], []))
                continue
            fetched = futures.pop(i).result()
            try:
                result = scanner.process(item_id, name, plan, fetched)
            except AuthError:
                raise
            except Exception as e:  # один сбойный предмет не останавливает проход
                result = e
            on_item(item_id, name, result)
    finally:
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:  # Python 3.8 не умеет cancel_futures
            pool.shutdown(wait=False)


def sell_speed(amount, per_day):
    """Грубая оценка, за сколько рынок «съест» столько штук (если продавать ~1/5 всех продаж)."""
    if per_day <= 0:
        return "продаётся редко — может зависнуть"
    days = amount / (per_day * 0.2)
    if days < 1 / 24:
        return f"рынок берёт ~{per_day:,.0f} шт/сутки — уйдёт быстро".replace(",", " ")
    if days < 1:
        return (f"рынок берёт ~{per_day:,.0f} шт/сутки — продашь за ~{days * 24:.0f} ч"
                .replace(",", " "))
    return (f"рынок берёт ~{per_day:,.0f} шт/сутки — продавать ~{days:.0f} дн."
            .replace(",", " "))


def deal_label(d):
    """[качество, +заточка] — точная заточка лота, если она известна."""
    return grade_label(d.get("grade")) if d.get("grade") else bucket_label(d.get("bucket"))


def trend_text(d):
    """«цена за сутки −8% к прошлым дням — рынок падает» или пусто."""
    t = d.get("trend")
    if t is None:
        return ""
    word = " — рынок падает" if t <= -5 else (" — рынок растёт" if t >= 5 else "")
    return f"цена за сутки {t:+.0f}% к прошлым дням{word}".replace("-", "−")


def trend_line(d):
    """Строка «Тренд: …» с переводом строки, если тренд известен, иначе пусто."""
    text = trend_text(d)
    return f"Тренд: {text}\n" if text else ""


def resale_basis(d):
    """Откуда цена перепродажи — чтобы было видно, с чем сравнивали."""
    period = f" за {fmt_window(d.get('window_h'))}" if d.get("window_h") else ""
    text = f"по сделкам{period} ~{fmt_rub(d['hist'])}/шт"
    if d.get("floor"):
        what = "такой же или лучше" if d.get("grade") else "этот же предмет"
        return text + f"; дешевле всего {what} на аукционе — {fmt_rub(d['floor'])}/шт"
    return text + "; такого же или лучше на аукционе сейчас нет — сравнить не с чем"


def stale_note(d):
    """Лот висит давно, а его не купили — у настоящей скидки так не бывает."""
    age = d.get("age")
    if age is None or age < STALE_MINUTES:
        return ""
    when = f"{age / 60:.0f} ч" if age >= 90 else f"{age:.0f} мин"
    why = "низкий процент или слабые свойства" if d.get("grade") else "проверь лот внимательно"
    return f"⚠ Висит уже ~{when}, и его никто не купил — скорее всего, есть подвох ({why})."


def bid_message(name, d, min_profit):
    what = "текущая ставка" if d["has_bids"] else "стартовая цена (ставок ещё нет)"
    resale = d["market"] * d["amount"]
    return (f"🕒 Ставка: {name}{deal_label(d)}\n"
            f"Лот: {d['amount']} шт, {what} {fmt_rub(d['need'])} "
            f"({fmt_rub(d['need'] / d['amount'])}/шт)\n"
            f"Перепродажа: по ~{fmt_rub(d['market'])}/шт = {fmt_rub(resale)}, "
            f"после комиссии 5% {fmt_rub(resale * 0.95)}\n"
            f"Цена перепродажи: {resale_basis(d)}\n"
            f"{trend_line(d)}"
            f"Прибыль, если выиграешь по этой цене: ~{fmt_rub(d['profit_now'])}\n"
            f"Ставь не выше {fmt_rub(d['max_bid'])} за весь лот "
            f"({fmt_rub(d['max_bid'] / d['amount'])}/шт) — тогда прибыль будет "
            f"не меньше {fmt_rub(min_profit)}.\n"
            f"До конца ~{d['minutes_left']:.0f} мин · {sell_speed(d['amount'], d['per_day'])}\n"
            f"Данные API запаздывают: проверь текущую ставку в игре."
            + (f"\n{ARTIFACT_NOTE}" if d["bucket"] is not None else ""))


ARTIFACT_NOTE = ("Артефакт: цена зависит ещё от процента качества и доп. свойств — "
                 "сравни лот в игре с другими того же качества и заточки.")


def lot_key(item_id, lot):
    return f"{item_id}|{lot.get('startTime')}|{lot.get('amount')}|{lot.get('buyoutPrice')}"


def fmt_rub(x):
    return f"{x:,.0f}".replace(",", " ") + " ₽"


def deal_message(name, d):
    end = d["lot"].get("endTime")
    end_s = parse_time(end).astimezone().strftime("%d.%m %H:%M") if end else "?"
    resale = d["market"] * d["amount"]
    stale = stale_note(d)
    return (f"🔔 {name}{deal_label(d)} — дешевле рынка на {d['pct']:.0f}%\n"
            f"Купить: {d['amount']} шт за {fmt_rub(d['buyout'])} ({fmt_rub(d['unit'])}/шт)\n"
            f"Перепродать: по ~{fmt_rub(d['market'])}/шт = {fmt_rub(resale)}, "
            f"после комиссии 5% {fmt_rub(resale * 0.95)}\n"
            f"Цена перепродажи: {resale_basis(d)}\n"
            f"{trend_line(d)}"
            f"Прибыль: ~{fmt_rub(d['profit'])} (+{d['profit'] / d['buyout'] * 100:.0f}% к вложенному)\n"
            f"Сделок в расчёте цены: {d['n']} · {sell_speed(d['amount'], d['per_day'])}\n"
            f"Лот активен до {end_s}. Проверь его в игре перед покупкой."
            + (f"\n{stale}" if stale else "")
            + (f"\n{ARTIFACT_NOTE}" if d["bucket"] is not None else ""))


# ------------------------------ Вывод ------------------------------
def notify(cfg, text):
    print("\n" + text + "\n", flush=True)
    if cfg.get("telegram_token") and cfg.get("telegram_chat_id"):
        try:
            requests.post(f"https://api.telegram.org/bot{cfg['telegram_token']}/sendMessage",
                          data={"chat_id": cfg["telegram_chat_id"], "text": text}, timeout=20)
        except requests.RequestException as e:
            log.warning("Telegram не ответил: %s", e)


def load_seen():
    try:
        with open(SEEN_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, ValueError, TypeError):  # нет файла или он испорчен — начинаем с чистого листа
        return set()


def save_seen(seen):
    tmp = SEEN_FILE + ".tmp"  # сначала во временный файл: если программу закроют посреди записи,
    with open(tmp, "w", encoding="utf-8") as f:  # старый файл останется целым
        json.dump(sorted(seen)[-5000:], f)
    os.replace(tmp, SEEN_FILE)


# ------------------------------ Цикл ------------------------------
def run(cfg, once=False):
    try:
        api = Api(cfg)
    except AuthError as e:
        log.error("%s", e)
        return
    names = load_listing(cfg["region"])
    items, auto = watch_items(cfg, names)
    if not items:
        log.error("Список отслеживания пуст — заполни CONFIG['watch'] или включи all_artifacts")
        return
    log.info("%s", watching_line(items, auto))
    seen = load_seen()
    db = MarketDB(keep_days=cfg.get("history_keep_days", 14))
    log.info("%s", db_line(db.stats()))
    scanner = Scanner(api, cfg, quiet=auto, db=db)
    first_pass = True

    def on_item(item_id, name, result):
        if isinstance(result, Exception):  # один сбойный предмет не должен ронять весь цикл
            log.warning("%s: ошибка — %s", name, result)
            return
        _, deals, bids = result
        for d in deals:
            key = lot_key(item_id, d["lot"])
            if key not in seen:
                seen.add(key)
                notify(cfg, deal_message(name, d))
        for d in bids:
            key = "bid|" + lot_key(item_id, d["lot"])
            if key not in seen:
                seen.add(key)
                notify(cfg, bid_message(name, d, cfg["min_profit"]))

    while True:
        started = time.time()
        try:
            scan_pass(scanner, items, on_item)
        except AuthError as e:
            log.error("%s", e)
            save_seen(seen)
            return
        save_seen(seen)
        if first_pass and scanner.summary():
            log.info("%s", scanner.summary())
        first_pass = False
        if once:
            return
        pause = max(10, cfg["poll_minutes"] * 60 - (time.time() - started))
        log.info("Проход завершён, следующий через %.0f с", pause)
        time.sleep(pause)


# ---------------------------- Самопроверка ----------------------------
def selftest():
    now = datetime.now(timezone.utc)
    iso = lambda dt: dt.isoformat().replace("+00:00", "Z")
    sales = [{"amount": 1, "price": 3000 + 20 * i, "time": iso(now - timedelta(hours=i))}
             for i in range(20)]
    sales += [{"amount": 10, "price": 31000, "time": iso(now - timedelta(hours=2))}]
    art_sales = [{"amount": 1, "price": 900000, "time": iso(now - timedelta(hours=i)),
                  "additional": {"qlt": 3, "ptn": 10}} for i in range(8)]
    market = market_prices(sales + art_sales, 5)
    assert abs(market[None][0] - 3100) <= 120, market
    assert market[(3, 10)][0] == 900000, market
    lots = [
        {"amount": 20, "buyoutPrice": 40000, "startTime": iso(now), "endTime": iso(now + timedelta(hours=20))},
        {"amount": 1, "buyoutPrice": 2950, "startTime": iso(now), "endTime": iso(now + timedelta(hours=20))},
        # артефакты: редкий +12 за 600 000; рядом редкий +14 за 880 000 (не хуже — ограничивает
        # цену перепродажи) и особый +12 за 300 000 (хуже по качеству — не мешает)
        {"amount": 1, "buyoutPrice": 600000, "startTime": iso(now), "endTime": iso(now + timedelta(hours=20)),
         "additional": {"qlt": 3, "ptn": 12}},
        {"amount": 1, "buyoutPrice": 880000, "startTime": iso(now), "endTime": iso(now + timedelta(hours=20)),
         "additional": {"qlt": 3, "ptn": 14}},
        {"amount": 1, "buyoutPrice": 300000, "startTime": iso(now), "endTime": iso(now + timedelta(hours=20)),
         "additional": {"qlt": 2, "ptn": 12}},
        {"amount": 5, "buyoutPrice": 0, "currentPrice": 100, "startTime": iso(now),
         "endTime": iso(now + timedelta(hours=1))},
    ]
    deals = find_deals(lots, market, CONFIG)
    assert len(deals) == 2, deals
    art = deals[0]
    assert art["grade"] == (3, 12) and art["floor"] == 880000 and round(art["market"]) == 871200, art
    assert round(art["profit"]) == round(871200 * 0.95 - 600000), art
    stack = deals[1]  # 20 шт по 2 000: продать выйдет не по 3 100, а чуть дешевле лота за 2 950
    assert stack["amount"] == 20 and round(stack["unit"]) == 2000 and stack["floor"] == 2950, stack
    assert round(stack["market"]) == round(2950 * UNDERCUT), stack

    # пример со скрина: Змеиный глаз «особый» +2 за 190 000, рядом такие же по 185–246 тыс.,
    # по сделкам 230 000. Это не скидка — дороже 185 000 его не продать.
    eye = {"qlt": 2, "ptn": 2}
    eye_market = market_prices([{"amount": 1, "price": 230000, "time": iso(now - timedelta(hours=i)),
                                 "additional": eye} for i in range(8)], 5)
    eye_lots = [{"amount": 1, "buyoutPrice": p, "additional": eye}
                for p in (185000, 190000, 200000, 200000, 210000, 220000, 230000, 245999)]
    assert find_deals(eye_lots, eye_market, dict(CONFIG, discount=0.08)) == []
    # а лот за 120 000 при тех же соседях — настоящая скидка: перепродать можно за ~183 000
    cheap_eye = find_deals(eye_lots + [{"amount": 1, "buyoutPrice": 120000, "additional": eye}],
                           eye_market, CONFIG)
    assert len(cheap_eye) == 1 and round(cheap_eye[0]["market"]) == round(185000 * UNDERCUT), cheap_eye
    # артефакт с заточкой ниже, чем в сделках, по ним не оцениваем: +5 и +6 не сравниваем
    # с продажами +7…+9 (они дороже), а +9 за 2,3 млн — обычная цена
    spir_market = market_prices([{"amount": 1, "price": 2_450_000, "time": iso(now - timedelta(hours=i)),
                                  "additional": {"qlt": 3, "ptn": 7 + i % 3}} for i in range(6)], 5)
    spir_lots = [{"amount": 1, "buyoutPrice": price, "additional": {"qlt": 3, "ptn": ptn}}
                 for price, ptn in ((1_399_999, 5), (1_500_000, 6), (2_300_000, 9))]
    assert find_deals(spir_lots, spir_market, dict(CONFIG, discount=0.08)) == []
    assert "Висит уже ~2 ч" in stale_note({"age": 120, "grade": (2, 2)})
    assert stale_note({"age": 20, "grade": (2, 2)}) == ""
    for d in deals:
        print(deal_message("Тестовый предмет", d), "\n")
    bid_lots = [
        # ставка 40 000 за 20 шт, рынок ~3 100 — выгодно, кончается через 30 мин
        {"amount": 20, "startPrice": 20000, "currentPrice": 40000, "buyoutPrice": 70000,
         "startTime": iso(now), "endTime": iso(now + timedelta(minutes=30))},
        # то же, но кончается через 5 часов — рано
        {"amount": 20, "startPrice": 20000, "currentPrice": 40000, "buyoutPrice": 70000,
         "startTime": iso(now), "endTime": iso(now + timedelta(hours=5))},
        # ставка уже почти рыночная — невыгодно
        {"amount": 20, "startPrice": 20000, "currentPrice": 55000, "buyoutPrice": 0,
         "startTime": iso(now), "endTime": iso(now + timedelta(minutes=20))},
    ]
    bids = find_bid_deals(bid_lots, market, CONFIG, now)
    assert len(bids) == 1 and bids[0]["need"] == 40000, bids
    print(bid_message("Тестовый предмет", bids[0], CONFIG["min_profit"]), "\n")

    # --- формат цен: за весь лот или за штуку ---
    import random
    rnd = random.Random(7)

    def priced(per_unit):
        out = []
        for a in (1,) * 6 + (5,) * 6 + (10,) * 6 + (20,) * 4 + (50,) * 4:
            unit = 3100 * rnd.uniform(0.85, 1.15)
            out.append({"amount": a, "price": unit if per_unit else unit * a})
        return out

    junk = [{"amount": 5, "price": 99_000_000}, {"amount": 1, "price": 1}]  # выбросы
    assert detect_total(priced(False) + junk, "price") is True
    assert detect_total(priced(True) + junk, "price") is False
    assert detect_total([{"amount": 1, "price": 3000 + i} for i in range(30)], "price") is None
    was_disabled = log.disabled
    log.disabled = True
    try:
        fmt = PriceFormat()
        assert fmt.total("history", priced(False), "price", "А") is True
        assert fmt.total("history", [{"amount": 1, "price": 5}] * 10, "price", "Б") is True  # не ясно → вывод по «А»
        assert fmt.total("lots", [], "buyoutPrice", "В") is True                             # выводов ещё нет → за лот
    finally:
        log.disabled = was_disabled

    # один и тот же лот в обоих форматах даёт одну и ту же прибыль
    far, soon = iso(now + timedelta(hours=20)), iso(now + timedelta(minutes=30))
    whole = find_deals([{"amount": 20, "buyoutPrice": 40000, "endTime": far}], market, CONFIG, total=True)
    each = find_deals([{"amount": 20, "buyoutPrice": 2000, "endTime": far}], market, CONFIG, total=False)
    assert len(whole) == len(each) == 1 and abs(whole[0]["profit"] - each[0]["profit"]) < 1e-6
    bid_whole = find_bid_deals([{"amount": 20, "startPrice": 20000, "currentPrice": 40000,
                                 "buyoutPrice": 70000, "endTime": soon}], market, CONFIG, now, total=True)
    bid_each = find_bid_deals([{"amount": 20, "startPrice": 1000, "currentPrice": 2000,
                                "buyoutPrice": 3500, "endTime": soon}], market, CONFIG, now, total=False)
    assert len(bid_whole) == len(bid_each) == 1 and bid_each[0]["need"] == 40000
    assert abs(bid_whole[0]["profit_now"] - bid_each[0]["profit_now"]) < 1e-6
    unit_history = [{"amount": 10, "price": 3100, "time": iso(now - timedelta(hours=i))} for i in range(10)]
    assert market_prices(unit_history, 5, total=False)[None][0] == 3100

    # история упёрлась в лимит страниц: все сделки за 10 ч → «штук в сутки» по 10 ч, а не по 48
    cap = HISTORY_PAGES * 100
    many = [{"amount": 2, "price": 6000, "time": iso(now - timedelta(hours=10 * i / (cap - 1)))}
            for i in range(cap)]
    per_day = market_prices(many, 5, 48)[None][2]
    assert abs(per_day - 2 * cap / 10 * 24) / (2 * cap / 10 * 24) < 0.03, per_day

    # строка рынка для журнала и проверка «цены лотов и сделок сходятся»
    good_lots = [{"amount": 10, "buyoutPrice": 32000}] * 3
    text = describe_market("Морфин", market, good_lots, 48)
    assert "рынок ~3" in text and "лотов: 3, обычно по 10 шт" in text, text
    assert price_mismatch(market, good_lots, True) is None
    factor = price_mismatch(market, [{"amount": 10, "buyoutPrice": 320000}] * 3, True)
    assert factor and "расходятся в ~10 раз" in mismatch_warning("Морфин", factor), factor
    assert price_mismatch(market, [{"amount": 1, "buyoutPrice": 99000}] * 3, True) is None  # без стаков не важно
    assert "мало сделок" in describe_market("Мутаген", {}, [], 48)
    print(text, "\n")

    # --- вход в API без сети: ключи в заголовках → 401 → токен EXBO ---
    class FakeResp:
        def __init__(self, code, data=None):
            self.status_code, self.headers, self._data = code, {}, data or {}

        def json(self):
            return self._data

    class FakeSession:
        def __init__(self, codes):
            self.codes, self.sent = list(codes), []

        def get(self, url, params=None, headers=None, timeout=None):
            self.sent.append(dict(headers or {}))
            return FakeResp(self.codes.pop(0), {"lots": []})

    real_post, was_disabled = requests.post, log.disabled
    requests.post = lambda *a, **k: FakeResp(200, {"access_token": "TOK-123"})
    log.disabled = True
    try:
        keys = dict(CONFIG, client_id=" ID-1 ", client_secret=" S3CR3T ", app_token="old-demo-token")
        api = Api(keys)
        assert api.mode == "keys"  # на боевом API ключи важнее поля «Токен»
        api.min_gap, api.s = 0, FakeSession([401, 200])
        api.lots("ru", "abcd", "time_created", "desc")
        assert api.s.sent[0] == {"Client-Id": "ID-1", "Client-Secret": "S3CR3T"}, api.s.sent
        assert api.s.sent[1] == {"Authorization": "Bearer TOK-123"}, api.s.sent
        api = Api(keys)
        api.min_gap, api.s = 0, FakeSession([401, 401])
        try:
            api.lots("ru", "abcd", "time_created", "desc")
            raise AssertionError("ожидал ошибку входа")
        except AuthError as e:
            assert "Client ID" in str(e) and "S3CR3T" not in str(e) and "TOK-123" not in str(e)
        demo = Api(dict(CONFIG, base_url="https://dapi.stalzone.com",
                        client_id="", client_secret="", app_token=""))
        assert demo._headers() == {"Client-Id": DEMO_CLIENT_ID, "Client-Secret": DEMO_CLIENT_SECRET}
        try:
            Api(dict(CONFIG, client_id="", client_secret="", app_token=""))
            raise AssertionError("ожидал ошибку: ключей нет")
        except AuthError:
            pass
    finally:
        requests.post, log.disabled = real_post, was_disabled

    # --- все артефакты: тихий режим, сводка, предметы, которых API не знает ---
    class FakeMarketApi:
        def history(self, region, item_id, since):
            if item_id == "gone":
                raise ApiError(400, "API ответил 400 (Invalid item id: gone)")
            if item_id == "rare":
                return []
            return [{"amount": 1, "price": 1_000_000, "time": iso(now - timedelta(hours=i)),
                     "additional": {"qlt": 3, "ptn": 15}} for i in range(6)]

        def lots_all(self, region, item_id):
            return [{"amount": 1, "buyoutPrice": 600_000, "startTime": iso(now),
                     "endTime": iso(now + timedelta(hours=5)), "additional": {"qlt": 3, "ptn": 15}}]

    was_disabled = log.disabled
    log.disabled = True
    try:
        sc = Scanner(FakeMarketApi(), CONFIG, quiet={"good", "rare", "gone"})
        _, art_deals, _ = sc.scan("good", "Арт")
        assert len(art_deals) == 1 and ARTIFACT_NOTE in deal_message("Арт", art_deals[0])
        assert sc.scan("rare", "Редкий") == (None, [], [])
        assert sc.scan("gone", "Пропавший") == (None, [], []) and "gone" in sc.skipped
        assert "цена есть у 1 из 2" in sc.summary() and "1 API не знает" in sc.summary(), sc.summary()
        assert watching_line([("a", "Морфин"), ("b", "Вихрь")], {"b"}) == "Слежу за: Морфин + все артефакты (1 шт.)"
    finally:
        log.disabled = was_disabled

    # --- лимит API: сброс сдвигается ровно на минуту → ускоряемся до 60% лимита ---
    was_disabled = log.disabled
    log.disabled = True
    try:
        api = Api(dict(CONFIG, client_id="x", client_secret="y"))
        base = time.time() * 1000
        for reset in (base + 30_000, base + 30_000, base + 90_000):
            api._adapt_pace(FakeResp(200, {}))  # без заголовков — ничего не меняется
            r = FakeResp(200, {})
            r.headers = {"x-ratelimit-limit": "400", "x-ratelimit-reset": str(int(reset))}
            api._adapt_pace(r)
        assert api.paced and abs(api.min_gap - 60 / (400 * RATE_SHARE)) < 1e-9, api.min_gap
    finally:
        log.disabled = was_disabled

    # --- своя база сделок: докачка без дублей, разрывы, очистка, длинное окно, тренд ---
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp()
    t0 = time.time()
    server = [{"amount": 1, "price": 3000 + i, "time": iso(now - timedelta(minutes=12 * i)), "additional": {}}
              for i in range(50)]                     # 50 сделок за последние 10 ч

    class FakeHistoryApi:
        def get(self, path, params):
            off = int(params["offset"])
            return {"prices": server[off:off + 100]}
        history_since = Api.history_since

    db = MarketDB(os.path.join(tmp, "market.db"), keep_days=14)
    try:
        fake = FakeHistoryApi()
        assert db.sync(fake, "ru", "p62q6", 48) == 50
        assert abs(db.window_hours("ru", "p62q6", 48) - 48) < 0.1          # история непрерывна
        server[:0] = [{"amount": 1, "price": 3100, "time": iso(now + timedelta(seconds=k + 1)), "additional": {}}
                      for k in range(5)]
        assert db.sync(fake, "ru", "p62q6", 48) == 5                       # только новые, без дублей
        server[:0] = [{"amount": 1, "price": 3200, "time": iso(now + timedelta(seconds=10 + k * 0.01)),
                       "additional": {}} for k in range(HISTORY_PAGES * 100 + 300)][::-1]
        db.sync(fake, "ru", "p62q6", 48)                                   # новых больше, чем страниц
        assert db.window_hours("ru", "p62q6", 48) < 1.5, db.window_hours("ru", "p62q6", 48)  # разрыв учтён
        with db.con:
            db.con.execute("INSERT INTO sales VALUES ('ru', 'old', ?, 1, 1, -1, -1, '')", (t0 - 20 * 86400,))
        db.cleanup()
        assert db.con.execute("SELECT COUNT(*) FROM sales WHERE item_id = 'old'").fetchone()[0] == 0
        assert db.stats()["sales"] > 1000

        # редкий артефакт: за 48 ч всего 2 сделки по «редкий +7», за неделю — 8 → оценка по 7 дням
        art = [{"amount": 1, "price": 1_000_000, "time": iso(now - timedelta(hours=h)),
                "additional": {"qlt": 3, "ptn": 7}} for h in (5, 30, 60, 80, 100, 120, 140, 150)]
        art += [{"amount": 1, "price": 900_000, "time": iso(now - timedelta(hours=h)),
                 "additional": {"qlt": 1, "ptn": 0}} for h in range(6)]   # ходовое качество — 6 за 48 ч

        class FakeArtApi(FakeHistoryApi):
            def get(self, path, params):
                return {"prices": art if int(params["offset"]) == 0 else []}

            def lots_all(self, region, item_id):
                return [{"amount": 1, "buyoutPrice": 600_000, "startTime": iso(now - timedelta(minutes=5)),
                         "endTime": iso(now + timedelta(hours=9)), "additional": {"qlt": 3, "ptn": 7}}]

        was_disabled = log.disabled
        log.disabled = True
        try:
            sc = Scanner(FakeArtApi(), dict(CONFIG, history_keep_days=14), db=db)
            _, found, _ = sc.scan("art1", "Артефакт")
        finally:
            log.disabled = was_disabled
        assert len(found) == 1 and found[0]["window_h"] > 100, found
        assert "по сделкам за 7 дн." in resale_basis(found[0]) or "по сделкам за 6 дн." in resale_basis(found[0])

        # тренд: за сутки медиана 80, раньше 100 → −20%
        tr = [{"ts": t0 - 3600 * h, "amount": 1, "price": 80 if h < 24 else 100, "additional": {}}
              for h in list(range(1, 7)) + list(range(30, 36))]
        assert round(price_trend(tr, {}, True, 5)) == -20
        assert "рынок падает" in trend_text({"trend": -20})
    finally:
        db.close()
        shutil.rmtree(tmp, ignore_errors=True)
    # --- шанс продажи: больше сделок — выше; конкуренты, запас, падение рынка, «давно висит», большой лот — ниже ---
    pairs = [(100.0, 1)] * 40                       # 40 сделок за 48 ч по 100
    base = sale_chance(100, 1, pairs, 48)
    assert base["chance"] == CHANCE_CAP and base["need"] == 1 and base["hours"] < 3
    rare = sale_chance(100, 1, pairs[:5], 168)       # 5 сделок за неделю
    assert 0.2 < rare["chance"] < 0.6 < base["chance"] and rare["week"] > rare["chance"]
    assert sale_chance(100, 1, pairs[:5], 168, comp=4)["chance"] < rare["chance"]
    assert sale_chance(100, 1, pairs[:5], 168, trend=-20)["chance"] < rare["chance"]
    assert sale_chance(100, 1, pairs[:5], 168, age=200)["chance"] < sale_chance(100, 1, pairs[:5], 168, age=90)["chance"]
    glut = sale_chance(100, 1, pairs[:5], 168, supply=20)       # 20 таких лотов при <1 сделке в сутки
    assert glut["supply_days"] > 25 and glut["chance"] < rare["chance"] / 2 and liquidity_label(glut["supply_days"]) == "низкая"
    assert sale_chance(100, 1, pairs, 48, supply=3)["liq_f"] == 1.0     # запас меньше суток — не штрафуем
    assert sale_chance(130, 1, [(100.0, 1)] * 20 + [(140.0, 1)] * 5, 48)["share"] == 6 / 27
    assert sale_chance(1, 1, pairs[:2], 48)["confidence"] == 0.5        # 2 сделки — уверенность 50%
    big = sale_chance(100, 50, [(100.0, 5)] * 10, 48)   # 50 шт, а покупают по 5 и 5 раз в сутки
    assert big["need"] == 10 and big["chance"] < 0.2
    assert sale_chance(100, 1, [], 48) is None and chance_label(0.75) == "высокий"
    assert abs(poisson_at_least(2.0, 1) - (1 - math.exp(-2))) < 1e-12
    assert abs(poisson_at_least(_rate_for(0.6, 3), 3) - 0.6) < 1e-6
    # наблюдения: из 40 таких лотов за сутки продались 4 — итог тянется к 10%, а не к формуле
    seen = sale_chance(100, 1, pairs, 48, observed=(4, 40))
    assert seen["weight"] > 0.7 and seen["chance"] < 0.4 and seen["hours"] > base["hours"]
    assert sale_chance(100, 1, pairs, 48, observed=(1, 1))["chance"] > 0.8    # одно наблюдение почти ничего не меняет
    lot_a = {"amount": 1, "buyoutPrice": 100}
    near = [lot_a, {"amount": 1, "buyoutPrice": 103}, {"amount": 1, "buyoutPrice": 120},
            {"amount": 1, "buyoutPrice": 101, "additional": {"qlt": 3}}]
    assert competitors(lot_a, near, 100) == 1         # 120 — дорого, артефакт другой корзины — не конкурент
    m = market_prices([{"amount": 1, "price": 100, "time": iso(now - timedelta(hours=i))} for i in range(6)], 5)
    assert deal_pairs(m, None)[0] == [(100.0, 1)] * 6 and PAIRS not in range_keys(m)
    # --- наблюдение за лотами: продан (есть сделка), снят, истёк, висит дольше суток ---
    tmp_l = tempfile.mkdtemp()
    db_l = MarketDB(os.path.join(tmp_l, "m.db"))
    try:
        t0 = time.time()
        mk = lambda key, amount, price, start_h, end_h=48: {"amount": amount, "buyoutPrice": price,
            "startTime": iso(datetime.fromtimestamp(t0 - start_h * 3600, timezone.utc)),
            "endTime": iso(datetime.fromtimestamp(t0 + end_h * 3600, timezone.utc)), "_k": key}
        a, b, c, d = mk("a", 1, 90, 2), mk("b", 1, 95, 3), mk("c", 1, 99, 30), mk("e", 2, 300, 1)
        db_l.observe_lots("ru", "x", [a, b, c, d], lambda lot: lot["buyoutPrice"] / lot["amount"] / 100, now=t0)
        db_l.store("ru", "x", [{"amount": 1, "price": 90, "time": iso(datetime.fromtimestamp(t0 + 60, timezone.utc))}], "stop")
        db_l.observe_lots("ru", "x", [c, d], lambda lot: 0.99, now=t0 + 600)          # «a» и «b» пропали
        rows = dict(db_l.con.execute("SELECT lot_key, outcome FROM lots").fetchall())
        assert rows[lot_key("x", a)] == "sold" and rows[lot_key("x", b)] is None    # b ещё ждём
        db_l.observe_lots("ru", "x", [c, d], lambda lot: 0.99, now=t0 + 3 * 3600)
        rows = dict(db_l.con.execute("SELECT lot_key, outcome FROM lots").fetchall())
        assert rows[lot_key("x", b)] == "removed"
        sold, total = db_l.lot_outcomes("ru", "x", None, now=t0 + 3 * 3600)
        assert (sold, total) == (1, 2), (sold, total)   # a — продан за сутки; c — висит 33 ч; b снят до суток; e дорогой
        assert db_l.lot_outcomes("ru", "x", (3, 15), now=t0) == (0, 0)
    finally:
        db_l.close()
        shutil.rmtree(tmp_l, ignore_errors=True)
    # --- категории ---
    assert item_category({"data": "/items/other/x.json"}, "Дешевые запчасти") == "parts"
    assert item_category({"data": "/items/other/x.json"}, "Стандартные инструменты") == "tools"
    assert item_category({"data": "/items/armor/x.json"}, "Броня") == "armor"
    assert auto_categories({"all_artifacts": True, "auto_categories": ["armor", "x"]}) == ["artefact", "armor"]
    assert "вся броня" in watching_line([("a", "A"), ("b", "B")], {"b"}, ["armor"])
    print("Самопроверка пройдена: поиск, формат цен, вход в API, «все артефакты» и база сделок работают.")


def safe_console():
    """Windows пишет вывод в файл в cp1251, а там нет эмодзи (🔔) — печатаем в UTF-8 и не падаем."""
    for stream in (sys.stdout, sys.stderr):
        if stream is None:          # .exe без окна консоли
            continue
        try:
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main():
    safe_console()
    ap = argparse.ArgumentParser(description="STALZONE: лоты ниже рынка")
    ap.add_argument("--once", action="store_true", help="один проход и выход")
    ap.add_argument("--selftest", action="store_true", help="проверка без интернета")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    if args.selftest:
        selftest()
        return
    try:
        run(CONFIG, once=args.once)
    except KeyboardInterrupt:
        print("\nОстановлено.")


if __name__ == "__main__":
    main()
