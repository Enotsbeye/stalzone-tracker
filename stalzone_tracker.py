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
import bisect
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
from collections import deque
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

    "poll_minutes": 0,      # пауза между проходами в минутах; 0 — проверять без остановки (быстрее всего)

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
FETCH_THREADS = 10           # столько запросов к API могут идти одновременно (темп всё равно держит Api)
FETCH_AHEAD = 20             # на сколько предметов вперёд заранее запрашивать данные
RATE_SHARE = 0.95            # какую долю лимита API тратить: 380 из 400 в минуту (остаток проверяется в каждом ответе)
SHARE_ON, SHARE_OFF = 0.1, 0.05   # чужих запросов за минуту больше 10% лимита — делим ключ, меньше 5% — нет
SHARE_SETTLE = 5             # через столько секунд после начала новой минуты лимита считаем прошлую
SHARE_MIN_SPAN = 40          # минута в счёт, только если мы сами работали в ней столько секунд
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


def load_icons(region):
    """Справочник id → путь к картинке предмета в базе EXBO (например, /icons/artefact/…/9nd0.png)."""
    icons = {}
    for it in _listing(region):
        item_id, _ = _id_and_name(it)
        if it.get("icon"):
            icons[item_id] = str(it["icon"])
    return icons


def _grade_rows(con, region, item_id, grade, since):
    """Сделки предмета с since: для артефакта — того же качества и заточки от −4 до той же (как market_for)."""
    for ts, amount, price, qlt, ptn in con.execute(
            "SELECT ts, amount, price, qlt, ptn FROM sales WHERE region = ? AND item_id = ? AND ts >= ?",
            (region, item_id, since)):
        if amount <= 0 or price <= 0:
            continue
        if grade is None:
            if qlt != -1:
                continue
        elif qlt != grade[0] or not grade[1] - 4 <= ptn <= grade[1]:
            continue
        yield ts, amount, price


def price_series(con, region, item_id, grade=None, days=7, step_h=12, now=None):
    """Цена за штуку по отрезкам (для графика в карточке находки): [(начало, медиана, сделок)]."""
    now = now or time.time()
    since = now - days * 86400
    buckets = {}
    for ts, amount, price in _grade_rows(con, region, item_id, grade, since):
        buckets.setdefault(int((ts - since) // (step_h * 3600)), []).append((price / amount, amount))
    return [(since + k * step_h * 3600, weighted_median(v), len(v)) for k, v in sorted(buckets.items())]


def hour_profile(con, region, item_id, grade=None, days=14, now=None):
    """Сколько сделок было в каждый час суток (по часам этого компьютера) — когда предмет покупают."""
    now = now or time.time()
    counts = [0] * 24
    for ts, _, _ in _grade_rows(con, region, item_id, grade, now - days * 86400):
        counts[time.localtime(ts).tm_hour] += 1
    return counts


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


HIDEOUT_URL = ("https://raw.githubusercontent.com/EXBO-Studio/"
               "stalzone-database/main/{region}/hideout_recipes.json")   # рецепты крафта в убежище
_hideout_cache = {}
_hideout_failed = {"at": 0.0}


def _tr(x):
    """Русская строка из перевода базы EXBO ({"lines": {"ru": …}})."""
    return ((x or {}).get("lines") or {}).get("ru") or "" if isinstance(x, dict) else str(x or "")


def load_hideout(region):
    """Рецепты убежища из базы EXBO (скачиваются раз в неделю): (навыки {id: название}, рецепты).
    Рецепт: {id, bench, cat, sub, result [(item, шт)], ingredients [(item, шт)], energy, perks {навык: уровень},
    features [улучшения убежища]}. (None, []) — рецепты не удалось получить."""
    path = os.path.join(HERE, f"hideout_{region}.json")
    stale = not os.path.exists(path) or time.time() - os.path.getmtime(path) > 7 * 86400
    if stale and not os.environ.get("STALZONE_OFFLINE") and time.time() - _hideout_failed["at"] > 600:
        try:
            r = requests.get(HIDEOUT_URL.format(region=region), timeout=30)
            r.raise_for_status()
            json.loads(r.text)
            with open(path + ".tmp", "w", encoding="utf-8") as f:
                f.write(r.text)
            os.replace(path + ".tmp", path)
        except (requests.RequestException, ValueError, OSError) as e:
            _hideout_failed["at"] = time.time()
            log.info("Рецепты убежища не скачались (%s)", type(e).__name__)
    if not os.path.exists(path):
        return None, []
    mtime = os.path.getmtime(path)
    cached = _hideout_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        perks = {str(p["id"]): _tr(p.get("name")) or str(p["id"]) for p in data.get("perks") or []}
        recipes = []
        for i, r in enumerate(data.get("recipes") or []):
            req = r.get("requirements") or {}
            res = [(str(x["item"]), int(_num(x.get("amount")) or 1)) for x in r.get("result") or [] if x.get("item")]
            if not res:
                continue
            recipes.append({
                "id": i, "bench": str(r.get("bench") or ""), "cat": _tr(r.get("category")), "sub": _tr(r.get("subcategory")),
                "result": res,
                "ingredients": [(str(x["item"]), int(_num(x.get("amount")) or 1)) for x in r.get("ingredients") or []
                                if x.get("item")],
                "energy": _num(r.get("energy")),
                "perks": {str(k): int(_num(v)) for k, v in (req.get("perks") or {}).items()},
                "features": [str(f) for f in req.get("features") or []]})
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        return None, []
    _hideout_cache[path] = (mtime, (perks, recipes))
    return perks, recipes


def craft_rows(recipes, prices, skills, fee=0.05):
    """Прибыль рецептов по ценам аукциона. prices — {item_id: цена за шт}; нет цены — предмета нет в словаре.
    Выручка — после комиссии аукциона. Для каждого рецепта: cost, value, profit (None, если каких-то цен нет),
    на 1000 энергии, доступен ли по навыкам и чего не хватает."""
    out = []
    for r in recipes:
        missing, cost, value = [], 0.0, 0.0
        for item, n in r["ingredients"]:
            if item in prices:
                cost += prices[item] * n
            else:
                missing.append(item)
        for item, n in r["result"]:
            if item in prices:
                value += prices[item] * n * (1 - fee)
            else:
                missing.append(item)
        need = {k: v for k, v in r["perks"].items() if int(skills.get(k, 0) or 0) < v}
        profit = None if missing else value - cost
        out.append(dict(r, cost=None if missing else cost, value=None if missing else value, profit=profit,
                        per_energy=(profit / r["energy"] * 1000) if profit is not None and r["energy"] > 0 else None,
                        available=not need, need=need, missing=missing))
    return out


def skill_advice(rows, skills, perks):
    """Какой навык поднять: для каждого навыка — самый прибыльный рецепт, который откроется на следующем
    уровне (остальные требования уже выполнены), и сколько прибыльных рецептов откроется."""
    out = []
    for perk, name in (perks or {}).items():
        level = int(skills.get(perk, 0) or 0)
        if level >= 5:
            continue
        opens = [r for r in rows if r["profit"] is not None and r["profit"] > 0 and r["perks"].get(perk) == level + 1
                 and all(int(skills.get(k, 0) or 0) >= v for k, v in r["perks"].items() if k != perk)]
        best = max(opens, key=lambda r: r["profit"], default=None)
        out.append({"perk": perk, "name": name, "level": level, "count": len(opens),
                    "best": {"id": best["id"], "result": best["result"], "profit": best["profit"],
                             "per_energy": best["per_energy"]} if best else None})
    out.sort(key=lambda a: -(a["best"]["profit"] if a["best"] else 0))
    return out


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


class RateLimited(Exception):
    """Ответ 429 у ключа из KeyPool: решает пул — подождать этот ключ или всем сбавить скорость."""

    def __init__(self, remaining, limit, reset_at):
        super().__init__("429")
        self.remaining, self.limit, self.reset_at = remaining, limit, reset_at


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

    AUTH_RETRY_S = 60    # «нет доступа» у работавшего ключа — столько секунд ждём перед повтором

    def __init__(self, cfg):
        self.cfg = cfg
        self.base = str(cfg["base_url"]).rstrip("/")
        self.demo = "://dapi." in self.base
        self.client_id = str(cfg.get("client_id") or "").strip()
        self.client_secret = str(cfg.get("client_secret") or "").strip()
        self.app_token = str(cfg.get("app_token") or "").strip()
        self.share_hint = str(cfg.get("share_hint") or "")   # кто ещё, скорее всего, пользуется ключом
        # делить лимит, только если ключ дали другим программам сами (коды доступа с ключом). Иначе чужие
        # запросы — повод сменить секрет, а не замедляться: от лишнего лимит и так бережёт _respect_ratelimit
        self.share_expected = bool(cfg.get("share_expected"))
        self.s = requests.Session()
        # запросы идут из нескольких потоков — пул соединений побольше
        self.s.mount("https://", requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=FETCH_THREADS + 4))
        self.min_gap = 0.3          # до 200 запросов в минуту, пока окно лимита не подтвердилось
        self._lock = threading.Lock()       # темп общий для всех потоков
        self._auth_lock = threading.Lock()
        self._next_slot = 0.0               # когда можно отправить следующий запрос
        self._resets = []           # моменты сброса лимита из ответов API — по ним узнаём его окно
        self.paced = False
        self.base_gap = None        # темп, когда ключ API использует только эта программа
        self._init_share()
        self.bearer = None          # токен от EXBO — только в памяти
        self.oauth_tried = False
        self.pool = None            # KeyPool, если ключ — один из нескольких
        self._ok_at = 0.0           # когда ключ последний раз ответил нормально
        self._auth_retries = 0      # сколько раз подряд ждали после «нет доступа» у работавшего ключа
        self._said = {}             # что и когда писали в журнал (чтобы не сыпать одинаковыми строками)
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
        return (f"API не пустил ключ с Client ID {self.client_id} (ответ {code}). Проверь в настройках: Client ID и Client Secret "
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
            sent_at = time.time()
            try:
                r = self.s.get(url, params=params, headers=headers, timeout=30)
            except requests.RequestException as e:
                log.warning("Сеть: %s — повтор через %s с", type(e).__name__, delay)
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            self._share_pace(r)          # каждый ответ, и с ошибкой: сервер его тоже посчитал
            if self.pool is None:
                self._respect_ratelimit(r)
            else:
                self._hold_if_spent(r)   # в пуле не спим: запрос возьмёт другой ключ
            if r.status_code in (401, 403):
                if self._try_oauth(headers, r.status_code):
                    continue
                if self._auth_flaky():   # ключ только что работал — EXBO иногда отвечает так зря
                    continue
                raise AuthError(self._auth_hint(r.status_code))
            if r.status_code == 429:
                if self.pool is not None:
                    raise RateLimited(*self._limits(r))
                # один ключ: ждут все потоки разом — иначе каждый сам по себе снова упирается в лимит
                with self._lock:
                    self._next_slot = max(self._next_slot, time.time() + delay)
                self._say("429", 30, "API ответил 429 (слишком много запросов) — пауза %s с", delay)
                delay = min(delay * 2, 120)
                continue
            if r.status_code >= 500:
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
            self._ok_at, self._auth_retries = time.time(), 0
            if r.headers.get("Date"):
                note_server_time(r.headers.get("Date"), sent_at, self._ok_at)
            try:
                return r.json()
            except ValueError:
                raise RuntimeError(f"API прислал непонятный ответ на запрос {path}") from None
        raise RuntimeError(f"API не отвечает: {path}")

    def _say(self, key, every, msg, *args):
        """В журнал — не чаще раза в every секунд на одну и ту же тему."""
        now = time.time()
        with self._lock:
            if now - self._said.get(key, 0) < every:
                return
            self._said[key] = now
        log.warning(msg, *args)

    @staticmethod
    def _limits(r):
        """(остаток, лимит, момент сброса) из заголовков ответа; чего нет — None."""
        def num(name):
            try:
                return float(r.headers.get(name))
            except (TypeError, ValueError):
                return None
        remaining, limit, reset = num("x-ratelimit-remaining"), num("x-ratelimit-limit"), num("x-ratelimit-reset")
        if reset is not None:
            reset = reset / 1000 if reset > 1e12 else reset
            reset = reset if reset > 1e9 else time.time() + reset
        return (None if remaining is None else int(remaining), None if limit is None else int(limit), reset)

    def _hold_if_spent(self, r):
        """Лимит ключа почти кончился — этот ключ не трогаем до сброса (пул берёт другие)."""
        remaining, _, reset = self._limits(r)
        if remaining is not None and remaining <= 2:
            with self._lock:
                self._next_slot = max(self._next_slot, min(reset or time.time() + 15, time.time() + 90))

    def _auth_flaky(self):
        """«Нет доступа» у ключа, который только что работал: подождать минуту и повторить (до 3 раз подряд).
        Так один сбой EXBO не останавливает поиск. Ключ правда сменили — через 3 минуты будет ошибка."""
        now = time.time()
        with self._lock:
            if self.mode != "keys" or not self._ok_at or now - self._ok_at > 1800 or self._auth_retries >= 3:
                return False
            if self._next_slot > now + self.AUTH_RETRY_S * 0.8:
                return True          # паузу уже объявил другой поток
            self._auth_retries += 1
            self._next_slot = now + self.AUTH_RETRY_S
            n = self._auth_retries
        log.warning("EXBO не пустила ключ с Client ID %s, хотя он только что работал — жду минуту и пробую снова "
                    "(%d из 3)", self.client_id, n)
        return True

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
                self.base_gap = self.min_gap
                self.paced = True
            else:
                return
        log.info("Лимит API: %s запросов в минуту — проверяю быстрее (запрос раз в %.2f с)",
                 limit, self.min_gap)

    def _init_share(self):
        self.sharing = False        # ключ сейчас использует ещё кто-то (друг с кодом доступа)
        self._win = {}              # окна лимита: момент сброса → счётчик сервера и наши ответы в этом окне
        self._win_closed = 0.0      # минуты с моментом сброса не позже этого уже посчитаны
        self._others = deque(maxlen=4)   # чужих запросов в последних посчитанных окнах

    def _share_pace(self, r, now=None):
        """Один ключ API — несколько программ (ты и друзья с кодом доступа). Лимит у ключа общий.

        Сервер сам пишет в каждом ответе, к какой минуте лимита он отнёс запрос (момент сброса),
        и сколько запросов в этой минуте уже было (лимит − остаток). Наших ответов с тем же моментом
        сброса — столько наших запросов в этой минуте. Разница — чужие. Считаем только по
        закончившимся минутам, где мы сами работали почти всю минуту: тогда ни часы компьютера,
        ни задержка сети на подсчёт не влияют (раньше из-за них программа «делила ключ» сама с собой).
        Делим лимит, когда чужих больше 10% лимита две минуты подряд; перестаём — когда меньше 5%
        две минуты подряд. Пока делим, берём не больше половины того, что остаётся от 85% лимита,
        и меняем темп плавно — так несколько программ сходятся к поровну, а не раскачивают друг друга."""
        if not self.paced:
            return
        try:
            limit = int(float(r.headers.get("x-ratelimit-limit")))
            remaining = int(float(r.headers.get("x-ratelimit-remaining")))
            reset = float(r.headers.get("x-ratelimit-reset"))
        except (TypeError, ValueError, AttributeError):
            return
        if reset > 1e12:
            reset /= 1000
        now = time.monotonic() if now is None else now
        with self._lock:
            if reset < self._win_closed + 2:
                return                          # запоздалый ответ из уже посчитанной минуты
            # одна минута — один момент сброса (± пару секунд, если сервер его округляет по-разному)
            key = next((k for k in self._win if abs(k - reset) < 2), reset)
            w = self._win.setdefault(key, {"used": 0, "mine": 0, "first": now, "last": now})
            w["used"] = max(w["used"], limit - remaining)
            w["mine"] += 1
            w["last"] = now
            newest = max(self._win)
            if now - self._win[newest]["first"] < SHARE_SETTLE:
                return                          # ответы прошлой минуты могут ещё идти
            closed = sorted(k for k in self._win if k < newest)
            if not closed:
                return
            for k in closed:
                st = self._win.pop(k)
                if st["mine"] >= 20 and st["last"] - st["first"] >= SHARE_MIN_SPAN:
                    self._others.append(max(0, st["used"] - st["mine"]))
            self._win_closed = closed[-1]
            was = self.sharing
            last = list(self._others)[-2:]
            if len(last) == 2:
                if all(o > limit * SHARE_ON for o in last):
                    self.sharing = True
                elif all(o < limit * SHARE_OFF for o in last):
                    self.sharing = False
            others = last[-1] if last else 0
            self.others_last, self.key_limit = others, limit   # для окна: сколько ключа уходит не нам
            budget = limit * RATE_SHARE
            expected = getattr(self, "share_expected", True)
            if self.sharing and expected:
                want = max(limit * 0.1, min(budget - others, budget / 2))
                target = (60 / self.min_gap + want) / 2
            else:
                target = budget
            self.min_gap = max(self.base_gap or 0.15, 60 / target)
            say_unknown = self.sharing and not was and not expected and not getattr(self, "_share_said", False)
            if say_unknown:
                self._share_said = True
        if self.sharing != was and expected:
            if self.sharing:
                log.info("Ключ API сейчас использует ещё кто-то (~%.0f запр./мин)%s — делю лимит, "
                         "проверки станут медленнее", others, getattr(self, "share_hint", ""))
            else:
                log.info("Ключ API снова только у этой программы — проверяю в полную скорость")
        elif say_unknown:
            log.info("Сервер EXBO насчитал на твоём ключе ~%.0f запр./мин сверх запросов этой программы. "
                     "Скорость не снижаю. Если ключ знает кто-то ещё — вторая копия трекера или сайт, где ты "
                     "вводил Client ID и Secret, — смени Client Secret в @stalzone_api_bot", others)

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

    def lots_top(self, region, item_id, min_buyouts=20, max_pages=LOT_PAGES):
        """Самые дешёвые лоты предмета — для поиска выгодных этого достаточно: первая страница (100 шт.),
        следующая — только если на ней почти нет лотов с выкупом. Раньше на каждый популярный предмет
        качалось до 5 страниц, и это была половина всех запросов прохода. Список полный для всех лотов
        дешевле последнего на странице (lots_cap)."""
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
            if sum(1 for lot in out if _num(lot.get("buyoutPrice")) > 0) >= min_buyouts:
                break
        return out

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


class KeyPool(Api):
    """Несколько ключей API в одной программе: запросы расходятся по ключам, у каждого свой темп и свой
    лимит (400 в минуту). Главный ключ — сам этот объект, дополнительные — отдельные Api. Ключ, который
    EXBO не пустила, выбывает — проверка идёт дальше на остальных."""

    def __init__(self, cfg, extra):
        super().__init__(cfg)
        self.members = [self]
        for cid, secret in extra:
            try:
                self.members.append(Api(dict(cfg, client_id=cid, client_secret=secret, app_token="",
                                             share_expected=False, share_hint="")))
            except AuthError:
                continue
        for m in self.members:
            m.pool = self
        self.dead = {}                       # ключ → до какого момента его не трогаем (не пустил)
        self._pick_lock = threading.Lock()
        # Общий темп пула. EXBO, кроме лимита на ключ, может ограничивать и всё вместе (ответ 429, хотя у ключа
        # лимит не кончился). Тогда снижаем темп на 20%, а минуту без 429 — понемногу поднимаем обратно.
        self.max_rate = len(self.members) * 400 * RATE_SHARE
        self.rate = self.max_rate
        self._gate_next = 0.0
        self._last_429 = self._cut_at = self._raise_at = 0.0
        self._spent = {}                     # ключ → сколько раз подряд его лимит кончался раньше времени
        log.info("Ключей API: %d — запросы делятся между ними (до %d в минуту)", len(self.members), self.max_rate)

    def alive(self):
        now = time.time()
        return [m for m in self.members if self.dead.get(id(m), 0) <= now]

    def _pick(self):
        with self._pick_lock:
            alive = self.alive()
            if not alive:
                raise AuthError("Ни один ключ API не подошёл — проверь Client ID и Client Secret в «Настройках».")
            m = min(alive, key=lambda x: x._next_slot)
            if self._spent.get(id(m)):          # ключ, чей лимит тратит кто-то ещё, — пробуем по одному запросу
                with m._lock:
                    m._next_slot = max(m._next_slot, time.time()) + 1.0
            return m

    def _gate(self):
        """Очередь всего пула: не чаще self.rate запросов в минуту на все ключи вместе."""
        with self._pick_lock:
            now = time.time()
            if self.rate < self.max_rate and now - self._last_429 > 30 and now - self._raise_at > 15:
                self.rate = min(self.max_rate, self.rate * 1.05 + 10)
                self._raise_at = now
            slot = max(now, self._gate_next)
            self._gate_next = slot + 60.0 / self.rate
        if slot > now:
            time.sleep(slot - now)

    def _limited(self, api, e):
        """429: лимит ключа кончился (им пользуется ещё кто-то) — ждём только его;
        лимит не кончился — это общий предел EXBO, сбавляем скорость всем."""
        now = time.time()
        n = self.members.index(api) + 1
        spent = e.remaining is not None and e.remaining <= 2
        cut = None
        with self._pick_lock:
            self._last_429 = now
            if not spent and now - self._cut_at > 15:     # одна волна 429 — одно снижение
                self._cut_at = now
                self.rate = max(60.0, self.rate * 0.85)
                cut = round(self.rate)
            if not spent:
                self._gate_next = max(self._gate_next, now + 1.0)
            # лимит ключа снова кончается сразу после сброса — его постоянно тратит кто-то ещё: ждём дольше
            streak = self._spent[id(api)] = self._spent.get(id(api), 0) + 1 if spent else 0
        if spent:
            until = min(e.reset_at or now + 15, now + 90) + (min(600, 60 * 2 ** (streak - 2)) if streak >= 2 else 0)
        else:
            until = now + 3
        with api._lock:
            api._next_slot = max(api._next_slot, until)
        if spent:
            self._say(f"spent{n}", 300, "Ключ API №%d (Client ID %s) исчерпал лимит раньше конца минуты — им, похоже, "
                                        "пользуется кто-то ещё (вторая копия трекера, друг, сайт). Беру запросы "
                                        "другими ключами", n, api.client_id)
        elif cut is not None:
            self._say("cut", 60, "EXBO просит сбавить скорость (ответ 429), хотя лимит у ключей не кончился — "
                                 "общий предел. Снижаю до %d запросов в минуту, потом подниму обратно", cut)

    def get(self, path, params):
        limited = 0
        while True:
            self._gate()
            api = self._pick()
            try:
                out = Api.get(api, path, params)
                if self._spent:
                    self._spent.pop(id(api), None)
                return out
            except RateLimited as e:
                self._limited(api, e)
                limited += 1
                if limited >= 25:
                    raise RuntimeError(f"API не отвечает (слишком много запросов): {path}") from None
            except AuthError:
                if len(self.members) == 1:
                    raise
                with self._pick_lock:
                    self.dead[id(api)] = time.time() + 900      # через 15 минут попробуем снова
                    left = len(self.alive())
                n = self.members.index(api) + 1
                log.warning("Ключ API №%d (Client ID %s) не пустил — работаю без него, осталось %d. "
                            "Через 15 минут попробую его снова", n, api.client_id, left)
                if not left:
                    raise

# --------------------------- Логика поиска ---------------------------
_FRACTION_RE = re.compile(r"\.(\d+)")


# Часы компьютера могут спешить или отставать — тогда «лот выставлен N мин назад», задержка API и время
# до конца торгов врут. Сверяемся со временем сервера EXBO (заголовок Date в каждом ответе API).
_SKEW = {"samples": deque(maxlen=21), "value": 0.0}


def note_server_time(date_header, sent_at, got_at):
    """Запомнить, насколько часы сервера впереди наших (секунды). Точность заголовка — 1 с."""
    try:
        from email.utils import parsedate_to_datetime
        server = parsedate_to_datetime(date_header).timestamp()
    except (TypeError, ValueError, IndexError, AttributeError):
        return
    sample = server + 0.5 - (sent_at + got_at) / 2      # Date округлён вниз до секунды
    with _SKEW_LOCK:
        _SKEW["samples"].append(sample)
        med = statistics.median(_SKEW["samples"])
        _SKEW["value"] = med if abs(med) >= 5 else 0.0     # меньше 5 с — шум, не трогаем


_SKEW_LOCK = threading.Lock()


def clock_skew():
    """Секунды: время сервера EXBO минус часы этого компьютера (0 — часы верные или ещё не сверяли)."""
    return _SKEW["value"]


def server_now():
    return datetime.now(timezone.utc) + timedelta(seconds=_SKEW["value"])


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


_FORMAT_SAID = set()   # что про формат цен уже писали в журнал (раз за запуск программы)


class PriceFormat:
    """За что API отдаёт цены. По документации EXBO — за весь лот, и в истории сделок, и в лотах;
    так и считаем для всех предметов сразу (API не меняет формат от предмета к предмету).

    По данным каждого предмета формат проверяется (наклон цены от количества), но один предмет его
    не меняет: у оптовых товаров одиночные лоты стоят за штуку в разы дороже больших (полимеры:
    ~11 500 ₽ за 1 шт и ~1 300 ₽/шт в пачке по 50), и наклон выходит как «за штуку», хотя цены — за лот.
    Раньше из-за этого у таких предметов цены считались неверно. Теперь формат переключается, только
    если «за штуку» вышло у большинства предметов (не меньше 3 и 80% ясных выводов)."""

    WHERE = {"history": "в истории сделок", "lots": "в лотах"}
    SWITCH_MIN, SWITCH_SHARE = 3, 0.8

    def __init__(self):
        self.votes = {k: {} for k in self.WHERE}      # вид → {предмет: за лот?}
        self.current = {k: True for k in self.WHERE}

    def total(self, kind, records, key, name):
        found = detect_total(records, key)
        if found is None:
            return self.current[kind]
        votes = self.votes[kind]
        votes[name] = found
        per_unit = sum(1 for v in votes.values() if not v)
        verdict = not (per_unit >= self.SWITCH_MIN and per_unit >= self.SWITCH_SHARE * len(votes))
        if verdict != self.current[kind]:
            self.current[kind] = verdict
            log.warning("⚠ Формат цен %s: %s — так вышло у %d из %d предметов. Пришли этот журнал.",
                        self.WHERE[kind], _per_what(verdict),
                        len(votes) - per_unit if verdict else per_unit, len(votes))
        elif verdict and found and (kind, verdict) not in _FORMAT_SAID:
            _FORMAT_SAID.add((kind, verdict))
            log.info("Формат цен %s: %s (как в документации EXBO, сходится с «%s»)",
                     self.WHERE[kind], _per_what(verdict), name)
        return self.current[kind]


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
    now = now or server_now()
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
CHANCE_CAP = 0.9    # наверняка не бывает: API не знает, сколько людей хотят купить
OBSERVED_TRUST = 10  # после стольких своих наблюдений лотов формула и наблюдения весят поровну
VISIBILITY = 0.6     # не каждый покупатель берёт самый дешёвый лот: ставки, другое количество, перебивают цену
# Шанс по наблюдениям: лоты, за которыми трекер следил сам, по корзинам «цена к рынку × ходовость предмета»
RATIO_BINS = (0.0, 0.9, 0.97, 1.03, 1.1, 1.25, 1.6)   # цена лота за штуку / рыночная
LIQ_BINS = (0.0, 3.0, 15.0, 60.0)                       # сделок предмета в сутки
RATES_TRUST_H = 48   # столько часов наблюдений в корзине весят столько же, сколько формула


def rate_bin(x, edges):
    """Номер корзины: последняя граница, не больше x."""
    return max(0, bisect.bisect_right(edges, x) - 1)


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
                supply=None, observed=None, rates=None):
    """Примерный шанс продать лот за hours часов по цене price за штуку. Своя формула, не знание.
    Строгая («сердитая») оценка. Покупатели приходят случайно (пуассоновский поток) с частотой прошлых
    сделок этой корзины, и она
      × 0,6 — не каждый покупатель берёт именно твой лот (ставки, другое количество, тебя перебивают),
      × уверенность: при малом числе сделок частота ненадёжна — n/(n+5) (5 сделок — ×0,5),
      × доля сделок, где платили не меньше price (со сглаживанием: никогда не 0 и не 100%),
      ÷ (1 + 0,5 × конкурентов почти по той же цене, до +5%),
      × ликвидность: за сколько дней рынок разберёт похожие лоты, что уже висят (до +30% к цене);
        запас больше полусуток — продавцы перебивают цену друг друга, шанс ниже,
      × тренд (рынок за сутки упал на 10% — ×0,75) и «давно висит» (лот час никто не купил даже со скидкой).
    Чтобы продать amount штук, нужно ~amount / (обычный размер сделки) покупателей.
    observed — (продано за сутки, всего) по лотам этого предмета, за которыми трекер следил сам.
    rates — (продано, часов наблюдения) у похожих лотов всех предметов: та же цена относительно рынка,
    такая же ходовость предмета. Это главное: шанс = 1 − e^(−продаж_в_час × 24) с поправкой на размер лота,
    тренд, «давно висит» и лишних конкурентов. Чем больше часов наблюдения, тем меньше вес формулы.
    Возвращает {chance 0…1, hours — ожидаемое время продажи, week — шанс за неделю, …} или None."""
    if not pairs or price <= 0 or amount <= 0:
        return None
    n = len(pairs)
    window_h = max(float(window_h or 0), 1.0)
    per_day = n / window_h * 24                               # сделок в сутки
    confidence = n / (n + 5)
    above = sum(1 for unit, _ in pairs if unit >= price * 0.995)
    share = (above + 1) / (n + 2)
    size = max(1.0, statistics.median(a for _, a in pairs))   # обычный размер одной сделки
    need = min(50, max(1, math.ceil(amount / size - 1e-9)))   # сколько покупателей нужно
    comp = int(comp or 0)
    comp_f = 1 / (1 + 0.5 * min(comp, 20))
    supply_days, liq_f = None, 1.0
    if supply is not None and per_day > 0:
        supply_days = int(supply) / per_day
        liq_f = 1 / (1 + 0.15 * max(0.0, supply_days - 0.5))
    trend_f = 1.0 if trend is None else min(1.1, max(0.4, 1 + float(trend) / 40))
    stale_f = 1.0
    if age is not None and age > STALE_MINUTES:
        stale_f = 0.4 if age > 3 * STALE_MINUTES else 0.6
    rate = per_day * VISIBILITY * confidence * share * comp_f * liq_f * trend_f * stale_f   # покупателей в сутки
    model = poisson_at_least(rate * hours / 24, need)
    chance, weight, seen = model, 0.0, None
    if observed and observed[1] > 0:
        sold, total = int(observed[0]), int(observed[1])
        seen = ((sold + 0.5) / (total + 1)) ** need             # доля лотов, проданных за сутки
        weight = total / (total + OBSERVED_TRUST)
        chance = weight * seen + (1 - weight) * model
    data = None
    if rates and float(rates[1]) > 0:
        sold_n, seen_h = float(rates[0]), float(rates[1])
        per_hour = (sold_n + 0.5) / (seen_h + 1.0)                 # продаж на час, что лот был на виду
        per_hour *= trend_f * stale_f / (1 + 0.25 * max(0, min(comp, 20) - 1))
        data_p = poisson_at_least(per_hour * hours, need)          # хватит ли покупателей на весь лот
        data_w = seen_h / (seen_h + RATES_TRUST_H)
        chance = data_w * data_p + (1 - data_w) * chance
        weight = max(weight, data_w)
        data = {"sold": int(sold_n), "hours": seen_h, "per_hour": per_hour, "p": data_p, "weight": data_w}
    if weight:   # частота покупателей, которая даёт итоговый шанс, — для времени продажи
        rate = _rate_for(min(chance, 0.999), need) * 24 / hours if chance > 0 else 0.0
    return {"chance": min(CHANCE_CAP, max(0.01, chance)),
            "hours": need / rate * 24 if rate > 0 else None,
            "week": min(CHANCE_CAP, max(0.01, poisson_at_least(rate * 7, need))),
            "per_day": per_day, "confidence": confidence, "share": share, "size": size, "need": need,
            "comp": comp, "supply": None if supply is None else int(supply), "supply_days": supply_days,
            "liq_f": liq_f, "trend_f": trend_f, "stale_f": stale_f, "model": model,
            "observed": [int(observed[0]), int(observed[1])] if observed else None, "weight": weight,
            "data": data}


def chance_label(c):
    return "высокий" if c >= 0.7 else "средний" if c >= 0.4 else "низкий"


def resale_price(lot, lots, m, total=True):
    """Реальная цена перепродажи за штуку: не выше цены по сделкам и чуть ниже самого
    дешёвого такого же или лучшего лота. Возвращает (цена, дешевле_всего_такой_же)."""
    floor = comparable_floor(lot, lots, total)
    return (min(m, floor * UNDERCUT) if floor else m), floor


CALIBRATE_MIN = 15            # столько сверенных находок — и можно поправлять оценку перепродажи
CALIBRATE_FLOOR = 0.88        # сильнее, чем на 12%, не занижаем: дальше это скорее падение рынка, чем ошибка


def calibration_factor(acc):
    """Поправка оценки перепродажи по сверке с фактом (только вниз): 0,94 — продавали на 6% дешевле оценки."""
    if not acc or acc.get("n", 0) < CALIBRATE_MIN:
        return 1.0
    return min(1.0, max(CALIBRATE_FLOOR, float(acc["ratio"])))


def _nice_price(x):
    """Цена, которую удобно вписать в игре: до рубля, у дорогих — до десятков."""
    return float(round(x)) if x < 100000 else float(round(x / 10) * 10)


def price_options(hist, amount, pairs, window_h, lots, additional, total=True, paid=0.0, fee=0.05,
                  rates_fn=None, trend=None):
    """За сколько выставить купленное: варианты цены за штуку с шансом продать за сутки и примерным сроком.
    hist — рынок по сделкам; lots — лоты на аукционе сейчас (свой выставленный лот — уже без него).
    Возвращает до трёх вариантов: «быстро» (самый высокий шанс), «выгодно» (больше всего прибыли с учётом
    шанса) и «дороже» (больше прибыли, если готов подождать). Пусто — оценить не по чему."""
    if not pairs or hist <= 0 or amount <= 0:
        return []
    fake = {"amount": amount, "buyoutPrice": 0, "additional": additional or {}}
    floor = comparable_floor(fake, lots, total)
    cands = {_nice_price(hist * k) for k in (0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2)}
    if floor:
        cands |= {_nice_price(floor * UNDERCUT), float(max(1, math.floor(floor) - 1))}
    rows = []
    for unit in sorted(c for c in cands if c > 0):
        comp = competitors(fake, lots, unit, total)
        supply = competitors(fake, lots, unit, total, spread=0.3)
        c = sale_chance(unit, amount, pairs, window_h, comp, trend, supply=supply,
                        rates=rates_fn(unit) if rates_fn else None)
        if not c:
            continue
        profit = unit * amount * (1 - fee) - paid
        rows.append({"unit": unit, "total": unit * amount, "chance": c["chance"], "hours": c["hours"],
                     "profit": profit, "cheapest": floor is None or unit < floor})
    if not rows:
        return []
    wait = lambda r: r["hours"] if r["hours"] else 24 * 30
    # шанс за сутки упирается в потолок 90%, поэтому «быстро» — по ожидаемому времени продажи,
    # а «выгодно» — прибыль с учётом шанса, поделённая на (1 + дней ожидания): деньги в товаре тоже стоят
    score = lambda r: r["profit"] * r["chance"] / (1 + wait(r) / 24)
    quickest = min(wait(r) for r in rows)
    fast = max((r for r in rows if wait(r) <= quickest * 1.3 + 0.5), key=lambda r: r["unit"])   # почти так же быстро — дороже
    best = max(rows, key=lambda r: (score(r), r["unit"]))
    slow = [r for r in rows if r["unit"] > best["unit"] and r["chance"] >= 0.2 and r["profit"] > best["profit"]]
    out = [dict(fast, key="fast")]
    if best["unit"] != fast["unit"]:
        out.append(dict(best, key="best"))
    else:
        out[0]["key"] = "best"   # самый быстрый и есть самый выгодный
    if slow:
        out.append(dict(max(slow, key=score), key="slow"))
    return out


def listing_state(lots, amount, list_total, additional, total=True):
    """Твой выставленный лот среди лотов предмета: виден ли он (то же количество, та же цена, та же
    корзина), сколько таких же или лучших лотов дешевле и самый дешёвый из них (за штуку)."""
    if amount <= 0 or list_total <= 0:
        return None
    list_unit = list_total / amount
    grade = grade_of(additional or {})
    own, cheaper = False, []
    for lot in lots:
        a, raw = int(_num(lot.get("amount"))), _num(lot.get("buyoutPrice"))
        if a <= 0 or raw <= 0:
            continue
        og = grade_of(lot.get("additional"))
        lot_total = raw if total else raw * a
        if not own and a == amount and abs(lot_total - list_total) < 1 and og == grade:
            own = True
            continue
        if grade is None:
            if og is not None:
                continue
        elif og is None or og[0] < grade[0] or og[1] < grade[1]:
            continue
        unit = raw / a if total else raw
        if unit < list_unit - 0.5:
            cheaper.append(unit)
    return {"own": own, "cheaper": len(cheaper), "best": min(cheaper) if cheaper else None,
            "suggest": _nice_price(min(cheaper) * UNDERCUT) if cheaper else None}


def lot_age_minutes(lot, now=None):
    try:
        now = now or server_now()
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
        raw_resale = resale
        resale *= min(1.0, float(cfg.get("resale_factor") or 1.0))   # поправка по сверке прогнозов с фактом
        if unit > resale * (1 - cfg["discount"]):
            continue  # рядом висят такие же почти по той же цене — это не скидка
        cost = unit * amount              # сколько заплатить за весь лот
        profit = resale * (1 - cfg["fee"]) * amount - cost
        if profit < cfg["min_profit"]:
            continue
        deals.append({"lot": lot, "bucket": b, "grade": grade_of(lot.get("additional")),
                      "unit": unit, "market": resale, "market_raw": raw_resale, "hist": hist, "floor": floor, "n": n,
                      "per_day": per_day, "pct": (1 - unit / resale) * 100, "profit": profit,
                      "amount": amount, "buyout": cost, "cost": cost, "age": lot_age_minutes(lot),
                      "window_h": window_h})
    deals.sort(key=lambda d: -d["profit"])
    return deals


def find_bid_deals(lots, market, cfg, now=None, total=True):
    """Лоты со ставками: скоро закончатся, а текущая цена ставки сильно ниже рынка.
    total — цены лота за весь лот (True) или за штуку. Суммы в находке — за весь лот."""
    now = now or server_now()
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
        m *= min(1.0, float(cfg.get("resale_factor") or 1.0))
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


def lots_cap(lots, page=100):
    """Ниже какой цены выкупа список лотов полный. Лоты приходят от дешёвых к дорогим страницами по 100:
    последняя страница неполная — видны все лоты; полная — видны все, что дешевле последнего на ней."""
    if not lots or len(lots) % page:
        return math.inf
    prices = [_num(lot.get("buyoutPrice")) for lot in lots if _num(lot.get("buyoutPrice")) > 0]
    return max(prices) if prices else 0.0


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
    """Во сколько раз (≥5) цена лотов за штуку расходится с рыночной, иначе None.
    Такое расхождение почти наверняка значит, что формат цен понят неверно.
    Медиана — по штукам, как и рыночная цена: иначе у оптовых товаров (много одиночных лотов,
    каждый за штуку в разы дороже пачки) медиана по числу лотов ложно кричала бы «формат не тот».
    Проверяем только когда в лотах есть стаки: при amount = 1 формат ни на что не влияет."""
    if not market:
        return None
    b = main_bucket(market)
    m = market[b][0]
    same, _ = lot_units(lots, b, total_lots)
    pairs = []
    for lot in same:
        amount, raw = int(_num(lot.get("amount"))), _num(lot.get("buyoutPrice"))
        if raw > 0:
            pairs.append((raw / amount if total_lots else raw, amount))
    if len(pairs) < 3 or m <= 0 or max(a for _, a in pairs) <= 1:
        return None
    ratio = weighted_median(pairs) / m
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
        CREATE TABLE IF NOT EXISTS predictions (    -- оценки находок: потом сверяем с тем, за сколько продавали
            region TEXT NOT NULL, item_id TEXT NOT NULL, lot_key TEXT NOT NULL, ts REAL NOT NULL,
            qlt INTEGER NOT NULL, ptn INTEGER NOT NULL, amount INTEGER NOT NULL,
            unit REAL NOT NULL, resale REAL NOT NULL, hist REAL NOT NULL, chance REAL,
            kind TEXT NOT NULL,                         -- deal — показана, near — «почти находка»
            PRIMARY KEY (region, lot_key));
    """

    def __init__(self, path=None, keep_days=14):
        self.path = path or os.path.join(HERE, "market.db")
        self.keep_days = max(1, int(keep_days))
        self.con = sqlite3.connect(self.path, timeout=30)
        self.con.execute("PRAGMA journal_mode=WAL")   # чтение не мешает записи
        self.con.executescript(self.SCHEMA)
        self.cleanup()

    @classmethod
    def reader(cls, path=None):
        """База только для чтения — для окна программы, пока проверка пишет в неё. None — базы ещё нет."""
        path = path or os.path.join(HERE, "market.db")
        if not os.path.exists(path):
            return None
        self = cls.__new__(cls)
        self.path, self.keep_days = path, 14
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
        return self

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
            self.con.execute("DELETE FROM predictions WHERE ts < ?", (cutoff,))
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

    def observe_lots(self, region, item_id, lots, ratio_fn=lambda lot: None, now=None, cap=math.inf):
        """Запомнить лоты этой проверки; пропавшие разобрать: в истории есть сделка ровно на лот — продан,
        вышло время — истёк, иначе через 2 часа — снят продавцом.
        cap — ниже какой цены список полный (lots_cap): лот дороже мог просто не попасть на страницу,
        его пропавшим не считаем."""
        now = now or time.time()
        cap = math.inf if cap is None else cap
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
                             "AND gone_ts IS NULL AND last_seen < ? AND price < ?",
                             (now, region, item_id, now, cap if cap < math.inf else 1e300))
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

    def sale_rates(self, region, now=None, days=7):
        """Как быстро продаются лоты на твоём рынке — по лотам, за которыми трекер следил сам.
        Корзины: (цена лота к рынку, ходовость предмета) → (продано, часов, что лоты были на виду).
        Возвращает (корзины, {item_id: сделок в сутки})."""
        now = now or time.time()
        since = now - days * 86400
        cov = dict(self.con.execute("SELECT item_id, covered_from FROM coverage WHERE region = ?", (region,)))
        liq = {}
        for item, n in self.con.execute(
                "SELECT item_id, COUNT(*) FROM sales WHERE region = ? AND ts >= ? GROUP BY item_id", (region, since)):
            start = max(since, cov.get(item, since))
            liq[item] = n / max(0.5, (now - start) / 86400)
        table = {}
        for item, ratio, first, last, gone, outcome in self.con.execute(
                "SELECT item_id, ratio, first_seen, last_seen, gone_ts, outcome FROM lots "
                "WHERE region = ? AND last_seen >= ? AND ratio BETWEEN 0.3 AND 3", (region, since)):
            seen_h = max(0.0, ((gone or last) - first) / 3600)
            if seen_h <= 0 and outcome != "sold":
                continue
            key = (rate_bin(ratio, RATIO_BINS), rate_bin(liq.get(item, 0.0), LIQ_BINS))
            sold, hours = table.get(key, (0, 0.0))
            table[key] = (sold + (outcome == "sold"), hours + seen_h)
        return table, liq

    def new_lot_rates(self, region, hours=6, now=None):
        """Сколько новых лотов в час появлялось у каждого предмета за последние hours часов — где
        выгодные лоты появляются чаще, туда и смотреть чаще."""
        now = now or time.time()
        return {item: n / hours for item, n in self.con.execute(
            "SELECT item_id, COUNT(*) + 4 * SUM(CASE WHEN ratio < 0.9 THEN 1 ELSE 0 END) FROM lots "
            "WHERE region = ? AND first_seen >= ? GROUP BY item_id",
            (region, now - hours * 3600))}

    def radar_rows(self, region, since, max_ratio):
        """Для «Радара»: лоты дешевле рынка (ratio ≤ max_ratio), выставленные, пока трекер работал,
        и сколько часов он работал. ([(item, qlt, ptn, start, first_seen, gone, outcome, ratio, amount)],
        часов работы, {item: с какого момента его видели})."""
        hours = {int(ts // 3600) for (ts,) in self.con.execute(
            "SELECT first_seen FROM lots WHERE region = ? AND first_seen >= ?", (region, since))}
        starts = dict(self.con.execute(
            "SELECT item_id, MIN(first_seen) FROM lots WHERE region = ? AND first_seen >= ? GROUP BY item_id",
            (region, since)))
        rows = [r for r in self.con.execute(
            "SELECT item_id, qlt, ptn, start_ts, first_seen, gone_ts, outcome, ratio, amount FROM lots "
            "WHERE region = ? AND start_ts >= ? AND ratio IS NOT NULL AND ratio <= ?", (region, since, max_ratio))
            if r[3] >= starts.get(r[0], math.inf) - 60]      # выставлен, когда за предметом уже следили
        return rows, len(hours), starts

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
            elif gone is None and last - start >= 86400:   # сами видели, что висит дольше суток
                total += 1
        return sold, total

    # --- прогноз против факта ---
    def record_predictions(self, rows):
        """Запомнить оценки находок. rows — (region, item_id, lot_key, ts, qlt, ptn, amount, unit, resale, hist,
        chance, kind). Важна первая оценка лота — повторные не перезаписываем."""
        if not rows:
            return
        with self.con:
            self.con.executemany(
                "INSERT OR IGNORE INTO predictions (region, item_id, lot_key, ts, qlt, ptn, amount, unit, resale, "
                "hist, chance, kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

    def accuracy(self, region, now=None, days=7, min_age_h=3, horizon_h=24, limit=400):
        """Сбылась ли оценка перепродажи: для каждой находки — медиана цен за штуку таких же лотов (предмет,
        качество, заточка той же корзины), проданных за horizon_h часов после находки, кроме самой находки.
        Возвращает {"n", "ratio" — медиана «факт / прогноз», "hit" — доля, где факт ≥ 97% прогноза,
        "by_kind": {deal|near: (n, ratio)}, "rows": [(item_id, kind, прогноз, факт, ts)]} или None."""
        now = now or time.time()
        preds = self.con.execute(
            "SELECT item_id, lot_key, ts, qlt, ptn, amount, unit, resale, kind FROM predictions "
            "WHERE region = ? AND ts >= ? AND ts <= ? ORDER BY ts DESC LIMIT ?",
            (region, now - days * 86400, now - min_age_h * 3600, limit)).fetchall()
        rows = []
        for item_id, key, ts, qlt, ptn, amount, unit, resale, kind in preds:
            if resale <= 0:
                continue
            if qlt < 0:
                cond, args = "qlt = -1", ()
            else:
                lo = min(ptn - ptn % 5, 15)
                cond, args = "qlt = ? AND ptn BETWEEN ? AND ?", (qlt, lo, lo + 4 if lo < 15 else 99)
            prices, own = [], False
            for a, p in self.con.execute(
                    f"SELECT amount, price FROM sales WHERE region = ? AND item_id = ? AND ts > ? AND ts <= ? AND {cond}",
                    (region, item_id, ts, ts + horizon_h * 3600) + args):
                if a <= 0:
                    continue
                u = p / a
                if not own and a == amount and abs(u - unit) <= unit * 0.005:
                    own = True          # сама находка — её купили по её цене, это не перепродажа
                    continue
                prices.append(u)
            if prices:
                rows.append((item_id, kind, resale, statistics.median(prices), ts))
        if not rows:
            return None
        ratios = [fact / pred for _, _, pred, fact, _ in rows]
        by_kind = {}
        for kind in ("deal", "near"):
            r = [fact / pred for _, k, pred, fact, _ in rows if k == kind]
            if r:
                by_kind[kind] = (len(r), statistics.median(r))
        return {"n": len(rows), "ratio": statistics.median(ratios),
                "hit": sum(1 for x in ratios if x >= 0.97) / len(ratios), "by_kind": by_kind, "rows": rows}

    def item_yield(self, region, now=None, days=7, cheap=0.9, live_s=180):
        """Что приносят предметы: {item_id: {lots — лотов видели, cheap — дешевле рынка (цена/рынок < cheap),
        catch — из них висели хотя бы live_s секунд (на такие успеваешь), first/last — когда видели}}."""
        now = now or time.time()
        out = {}
        for item, n, c, k, first, last in self.con.execute(
                "SELECT item_id, COUNT(*), SUM(ratio < ?), "
                "SUM(ratio < ? AND COALESCE(sold_ts, gone_ts, last_seen) - first_seen >= ?), "
                "MIN(first_seen), MAX(last_seen) FROM lots WHERE region = ? AND first_seen >= ? GROUP BY item_id",
                (cheap, cheap, live_s, region, now - days * 86400)):
            out[item] = {"lots": n, "cheap": int(c or 0), "catch": int(k or 0), "first": first, "last": last}
        for item, kind, n in self.con.execute(
                "SELECT item_id, kind, COUNT(*) FROM predictions WHERE region = ? AND ts >= ? GROUP BY item_id, kind",
                (region, now - days * 86400)):
            out.setdefault(item, {"lots": 0, "cheap": 0, "catch": 0, "first": None, "last": None})[kind] = n
        return out

    def unit_prices(self, region, item_ids, now=None, days=7, max_sales=60):
        """Цена за штуку по последним сделкам — медиана, обычное качество и без заточки:
        {item_id: (цена, сделок, время последней)}. Предметов без сделок в ответе нет."""
        now = now or time.time()
        out = {}
        for item in item_ids:
            rows = self.con.execute(
                "SELECT amount, price, ts FROM sales WHERE region = ? AND item_id = ? AND ts >= ? AND qlt <= 0 "
                "AND ptn <= 0 ORDER BY ts DESC LIMIT ?", (region, item, now - days * 86400, max_sales)).fetchall()
            units = [p / a for a, p, _ in rows if a > 0 and p > 0]
            if units:
                out[item] = (statistics.median(units), len(units), rows[0][2])
        return out

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
        self.last_cap = {}           # item_id -> ниже какой цены последний список лотов полный
        self._rates, self._rates_at = ({}, {}), 0.0   # как быстро продаются похожие лоты (раз в 20 мин)

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

    def rates_for(self, item_id, price, hist):
        """(продано, часов на виду) у похожих лотов: та же цена к рынку, такой же ходовости предмет."""
        if self.db is None or not hist or price <= 0:
            return None
        now = time.time()
        if now - self._rates_at > 1200:
            try:
                self._rates = self.db.sale_rates(self.cfg["region"], now=now)
            except sqlite3.Error:
                self._rates = ({}, {})
            self._rates_at = now
        table, liq = self._rates
        return table.get((rate_bin(price / hist, RATIO_BINS), rate_bin(liq.get(item_id, 0.0), LIQ_BINS)))

    def _lots(self, region, item_id):
        """Самые дешёвые лоты (lots_top); у подставных API в проверках — все (lots_all)."""
        top = getattr(self.api, "lots_top", None)
        return top(region, item_id) if top else self.api.lots_all(region, item_id)

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
                out["lots"] = self._lots(cfg["region"], item_id)
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
            raw = self._lots(cfg["region"], item_id)
        cap = lots_cap(raw)    # ниже этой цены видны все лоты
        lots = {lot_key(item_id, lot): lot for lot in raw}  # по лотам видна реальная цена продажи
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
        if self.db is not None:   # следим, какие лоты продаются (там, где список полный — ниже cap)
            def ratio(lot, market=market, total=total_lots):
                found = market_for(market, lot.get("additional"))
                amount, raw = int(_num(lot.get("amount"))), _num(lot.get("buyoutPrice"))
                if not found or amount <= 0 or raw <= 0 or not found[0][0]:
                    return None
                return (raw / amount if total else raw) / found[0][0]
            self.db.observe_lots(cfg["region"], item_id, lot_list, ratio, cap=cap)
        factor = price_mismatch(market, lot_list, total_lots)
        if factor:  # находки по такому предмету почти наверняка ложные — молчим
            if item_id not in self.mismatched:
                self.mismatched.add(item_id)
                log.warning("%s", mismatch_warning(name, factor))
            return lots, [], []
        # find_min_profit — порог пониже для особо редких (обычные находки приложение отсеет само)
        find_cfg = dict(cfg, min_profit=cfg["find_min_profit"]) if cfg.get("find_min_profit") is not None else cfg
        deals = find_deals(lots.values(), market, find_cfg, total_lots)
        if deals and cap < math.inf and any(d["floor"] is None for d in deals) and hasattr(self.api, "lots_all"):
            # редкий случай: у находки (обычно артефакт высокого качества) на первой странице нет лотов
            # не хуже неё — цену перепродажи не с чем сравнить. Докачиваем остальные страницы.
            raw = self.api.lots_all(cfg["region"], item_id)
            cap = lots_cap(raw)
            lots = {lot_key(item_id, lot): lot for lot in raw}
            lot_list = list(lots.values())
            deals = find_deals(lots.values(), market, find_cfg, total_lots)
        self.last_cap[item_id] = cap
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
                d["chance"] = sale_chance(d["market"], d["amount"], found[0], found[1], comp, d.get("trend"),
                                          d.get("age") if "unit" in d else None, supply=supply,
                                          rates=self.rates_for(item_id, d["market"], d.get("hist") or d["market"]))
        return lots, deals, bids


def _best_hours(hours, width=3):
    """Самое «урожайное» окно в width часов: (с какого часа, по какой) — или None, если данных мало."""
    if len(hours) < 6:
        return None
    count = [0] * 24
    for h in hours:
        count[h % 24] += 1
    best = max(range(24), key=lambda a: (sum(count[(a + k) % 24] for k in range(width)), count[a]))
    if sum(count[(best + k) % 24] for k in range(width)) < len(hours) * 0.4:
        return None                 # дешёвые лоты бывают в любое время — окно ни о чём не говорит
    return best, (best + width) % 24


def radar(rows, active_hours, market_fn, discount, fee, min_profit, local_hour=None, top=15):
    """«Радар»: где дешёвые лоты появляются чаще и выгоднее всего — туда стоит заглядывать на аукцион
    самому (в игре лоты видны сразу, а в API — минут через 10). rows — из MarketDB.radar_rows;
    market_fn(item_id, additional) → рынок за штуку сейчас или None. Для каждого предмета (у артефактов —
    качества и заточки): «бери, если дешевле X за шт» (и от скольки штук это даёт минимальную прибыль),
    сколько таких лотов в сутки, через сколько их обычно покупают и в какие часы их больше."""
    groups = {}
    for item, qlt, ptn, start, first, gone, outcome, ratio, amount in rows:
        add = {"qlt": qlt, "ptn": ptn} if qlt is not None and qlt >= 0 else {}
        groups.setdefault((item, bucket_of(add)), []).append((start, gone, ratio, int(amount or 1), add))
    hours = max(1.0, float(active_hours or 0))
    out = []
    for (item, bucket), lots in groups.items():
        add = lots[0][4]
        unit = market_fn(item, add)
        if not unit or unit <= 0:
            continue
        net = unit * (1 - fee)
        profits = [(net - ratio * unit) * amount for _, _, ratio, amount, _ in lots]
        good = [p for p in profits if p >= max(min_profit, 1)]
        if not good:
            continue
        buy_below = _nice_price(unit * (1 - discount))
        margin = net - buy_below
        if margin <= 0:
            continue
        lives = [(g - st) / 60 for st, g, _, _, _ in lots if g and g > st]
        local = [datetime.fromtimestamp(st).hour for st, _, _, _, _ in lots]
        window = _best_hours(local)
        per_day = len(good) / hours * 24
        out.append({
            "item_id": item, "additional": add, "bucket": bucket, "market": unit, "buy_below": buy_below,
            "need": max(1, math.ceil(min_profit / margin)) if min_profit > 0 else 1,
            "per_day": per_day, "n": len(good), "profit": statistics.median(good),
            "life_min": statistics.median(lives) if len(lives) >= 3 else None,
            "hours": window,
            "peak": bool(window and local_hour is not None and (local_hour - window[0]) % 24 < 3),
            "score": per_day * statistics.median(good),
        })
    out.sort(key=lambda r: (-(r["score"] * (1.5 if r["peak"] else 1.0)), -r["n"]))
    return out[:top]


def pass_order(items, heat, share=0.25, pass_no=0, keep=()):
    """Порядок проверки на один проход. Самые «горячие» предметы (heat — новых лотов в час, дешёвые
    считаются за несколько) идут первыми и проверяются ещё раз в середине прохода, а в длинном списке
    (от 30 предметов) — ещё дважды, на трети и двух третях: новый лот у них виден в 2–3 раза быстрее.
    В длинном списке (от 40) «холодные» — где за 6 часов не было ни одного нового лота — проверяются
    через проход (не больше половины списка; keep — всегда). Без данных о лотах — как в списке."""
    items = list(items)
    if len(items) < 8 or not heat:
        return items
    base = sorted(items, key=lambda it: -heat.get(it[0], 0))
    hot = [it for it in base[:max(1, int(len(base) * share))] if heat.get(it[0], 0) > 0]
    if len(base) >= 40 and pass_no % 2 == 1:
        keep = set(keep)
        cold = [it for it in base if heat.get(it[0], 0) <= 0 and it[0] not in keep][:len(base) // 2]
        if cold:
            drop = set(cold)
            base = [it for it in base if it not in drop]
    if len(items) >= 30 and hot:
        a, b = len(base) // 3, 2 * len(base) // 3
        return base[:a] + hot + base[a:b] + hot + base[b:]
    mid = len(base) // 2
    return base[:mid] + hot + base[mid:]


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
        as_lots = lambda per_unit: [{"amount": r["amount"], "buyoutPrice": r["price"]} for r in priced(per_unit)]
        # как у полимеров в настоящей базе: одиночные лоты за штуку в разы дороже пачек — формат не меняется
        assert fmt.total("lots", as_lots(True), "buyoutPrice", "Полимеры") is True
        assert fmt.total("lots", as_lots(True), "buyoutPrice", "Фрагмент") is True
        assert fmt.total("lots", as_lots(False), "buyoutPrice", "Морфин") is True
        fmt2 = PriceFormat()   # а если «за штуку» выходит почти у всех — значит, API и правда так считает
        assert [fmt2.total("lots", as_lots(True), "buyoutPrice", n) for n in "ХЦЧ"] == [True, True, False]
    finally:
        log.disabled = was_disabled
    # оптовый товар (настоящие цифры полимеров): сделки в основном пачками по 50 по ~1 300 ₽/шт,
    # лотов-одиночек по 11 500 ₽ больше всего — это не «формат не тот»
    poly_sales = ([{"amount": 50, "price": 65000}] * 112 + [{"amount": 10, "price": 20000}] * 42
                  + [{"amount": 1, "price": 9500}] * 15)
    poly_lots = ([{"amount": 1, "buyoutPrice": 11500}] * 123 + [{"amount": 10, "buyoutPrice": 19998}] * 53
                 + [{"amount": 5, "buyoutPrice": 14942}] * 20)
    assert price_mismatch(market_prices(poly_sales, 5), poly_lots, True) is None

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
    assert 0.1 < rare["chance"] < 0.4 < base["chance"] and rare["week"] > rare["chance"]
    assert sale_chance(100, 1, pairs[:5], 168, comp=4)["chance"] < rare["chance"]
    assert sale_chance(100, 1, pairs[:5], 168, trend=-20)["chance"] < rare["chance"]
    assert sale_chance(100, 1, pairs[:5], 168, age=200)["chance"] < sale_chance(100, 1, pairs[:5], 168, age=90)["chance"]
    glut = sale_chance(100, 1, pairs[:5], 168, supply=20)       # 20 таких лотов при <1 сделке в сутки
    assert glut["supply_days"] > 25 and glut["chance"] < rare["chance"] / 2 and liquidity_label(glut["supply_days"]) == "низкая"
    assert sale_chance(100, 1, pairs, 48, supply=3)["liq_f"] == 1.0     # запас меньше суток — не штрафуем
    assert sale_chance(130, 1, [(100.0, 1)] * 20 + [(140.0, 1)] * 5, 48)["share"] == 6 / 27
    assert abs(sale_chance(1, 1, pairs[:2], 48)["confidence"] - 2 / 7) < 1e-12   # 2 сделки — уверенность 29%
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
        table, liq = db_l.sale_rates("ru", now=t0 + 3 * 3600)    # a и b — в корзине «цена 0,90–0,97»
        sold_b, hours_b = table[(rate_bin(0.9, RATIO_BINS), rate_bin(liq["x"], LIQ_BINS))]
        assert sold_b == 1 and hours_b > 0, table
        assert db_l.new_lot_rates("ru", now=t0 + 60)["x"] > 0
        # --- что приносят предметы: «a» (0,9) и «b» (0,95) — дешевле 0,97; на «a» успевали: висел до сделки ---
        y = db_l.item_yield("ru", now=t0 + 3 * 3600, cheap=0.97, live_s=30)
        assert y["x"]["lots"] == 4 and y["x"]["cheap"] == 2 and y["x"]["catch"] >= 1, y
        # --- прогноз против факта: оценили перепродажу в 100, а такие лоты потом продавали по 90 ---
        preds = [("ru", "y", f"y|{i}", t0 - 10 * 3600 - i, -1, -1, 1, 70.0, 100.0, 100.0, 0.5, "deal") for i in range(16)]
        db_l.record_predictions(preds)
        db_l.record_predictions(preds[:1])                            # повтор — не дублируется
        db_l.store("ru", "y", [{"amount": 1, "price": 90 + k % 3, "time": iso(datetime.fromtimestamp(
            t0 - 9 * 3600 + k * 60, timezone.utc))} for k in range(5)]
            + [{"amount": 1, "price": 70, "time": iso(datetime.fromtimestamp(t0 - 9 * 3600 + 400, timezone.utc))}], "stop")
        acc = db_l.accuracy("ru", now=t0)
        assert acc["n"] == 16 and 0.89 < acc["ratio"] < 0.92 and acc["hit"] == 0, acc
        assert abs(calibration_factor(acc) - acc["ratio"]) < 1e-9 and calibration_factor({"n": 3, "ratio": 0.5}) == 1.0
        assert calibration_factor({"n": 40, "ratio": 0.5}) == CALIBRATE_FLOOR
        assert db_l.item_yield("ru", now=t0)["y"]["deal"] == 16
        assert abs(db_l.unit_prices("ru", ["y", "nope"], now=t0)["y"][0] - 90) < 1.01
    finally:
        db_l.close()
        shutil.rmtree(tmp_l, ignore_errors=True)
    # --- поправка оценки: та же находка с оценкой ниже на 10% — прибыль меньше, слабая отсеивается ---
    mk_lot = lambda price, start_h=0.1: {"amount": 1, "buyoutPrice": price, "startTime": iso(now - timedelta(hours=start_h)),
                                         "endTime": iso(now + timedelta(hours=20))}
    mkt = market_prices([{"amount": 1, "price": 100000, "time": iso(now - timedelta(hours=i))} for i in range(10)], 5)
    d1 = find_deals([mk_lot(80000)], mkt, dict(CONFIG, min_profit=10000))
    d2 = find_deals([mk_lot(80000)], mkt, dict(CONFIG, min_profit=10000, resale_factor=0.9))
    assert d1 and d1[0]["market"] == 100000 and not d2, (d1, d2)
    d3 = find_deals([mk_lot(70000)], mkt, dict(CONFIG, min_profit=10000, resale_factor=0.9))
    assert d3 and d3[0]["market"] == 90000 and d3[0]["market_raw"] == 100000
    # --- помощник продажи: варианты цены и «твой лот перебили» ---
    pairs = [(100000.0, 1)] * 30
    others = [mk_lot(98000), mk_lot(105000), mk_lot(120000)]
    opts = price_options(100000, 1, pairs, 48, others, {}, paid=80000)
    assert opts and opts[0]["key"] in ("fast", "best") and all(o["chance"] > 0 for o in opts), opts
    fast = opts[0]
    assert fast["unit"] < 98000 and fast["cheapest"], opts   # быстрее всего — дешевле самого дешёвого конкурента
    assert len({o["unit"] for o in opts}) == len(opts)
    assert price_options(100000, 1, [], 48, others, {}) == []
    st = listing_state(others + [mk_lot(97000)], 1, 97000, {})
    assert st["own"] and st["cheaper"] == 0
    st = listing_state(others + [mk_lot(99000)], 1, 99000, {})
    assert st["own"] and st["cheaper"] == 1 and st["best"] == 98000 and st["suggest"] < 98000, st
    assert not listing_state(others, 1, 99500, {})["own"]
    # --- калькулятор крафта: прибыль рецепта, недостающие цены, совет по навыку ---
    recs = [{"id": 1, "bench": "w", "cat": "", "sub": "", "result": [("r1", 2)], "ingredients": [("i1", 3), ("i2", 1)],
             "energy": 500.0, "perks": {"medicine": 2}, "features": []},
            {"id": 2, "bench": "w", "cat": "", "sub": "", "result": [("r2", 1)], "ingredients": [("i9", 1)],
             "energy": 100.0, "perks": {"medicine": 1}, "features": []}]
    rows = craft_rows(recs, {"r1": 1000.0, "i1": 100.0, "i2": 200.0, "r2": 50.0}, {"medicine": 1}, fee=0.05)
    assert rows[0]["cost"] == 500 and rows[0]["value"] == 1900 and rows[0]["profit"] == 1400 and not rows[0]["available"]
    assert rows[0]["per_energy"] == 2800 and rows[0]["need"] == {"medicine": 2}
    assert rows[1]["profit"] is None and rows[1]["missing"] == ["i9"] and rows[1]["available"]
    adv = skill_advice(rows, {"medicine": 1}, {"medicine": "Медицина", "cooking": "Кулинария"})
    assert adv[0]["perk"] == "medicine" and adv[0]["count"] == 1 and adv[0]["best"]["profit"] == 1400, adv
    # --- один ключ на несколько программ: делим лимит по остатку из ответов API ---
    class _R:
        def __init__(self, remaining, reset):
            self.headers = {"x-ratelimit-limit": "400", "x-ratelimit-remaining": str(remaining),
                            "x-ratelimit-reset": str(int(reset * 1000))}
    sh = Api.__new__(Api)
    sh._lock, sh.paced = threading.Lock(), True
    sh._init_share()
    sh.base_gap = sh.min_gap = 60 / (400 * RATE_SHARE)
    clock = [1000.0]      # своё время программы: важны только промежутки, часы компьютера не нужны

    def minute(ours, others, api=None):
        """Минута лимита: наши ответы идут всю минуту, чужие запросы сервер считает вперемешку."""
        api = api or sh
        reset = 1_790_000_000 + 60 * int(clock[0] / 60 + 1)
        for i in range(ours):
            used = min(400, round((i + 1) * (ours + others) / ours))
            api._share_pace(_R(400 - used, reset), now=clock[0] + i * 58 / ours)
        clock[0] += 60
    for _ in range(3):
        minute(300, 0)                                                  # одни — чужих нет
    assert not sh.sharing and abs(sh.min_gap - sh.base_gap) < 1e-9
    minute(250, 150); minute(300, 0); minute(300, 0)                    # одна шумная минута — не повод
    assert not sh.sharing
    minute(200, 150); minute(200, 150); minute(200, 150)                # друг работает две минуты подряд
    assert sh.sharing and sh.min_gap > sh.base_gap
    minute(170, 5); minute(170, 5); minute(170, 5)                      # друг закрыл программу
    assert not sh.sharing and abs(sh.min_gap - sh.base_gap) < 1e-9
    sh._share_pace(_R(10, 1_790_000_000), now=clock[0])                 # запоздалый ответ давней минуты
    assert not sh.sharing
    # ключ никому не давали, а сервер насчитывает лишнее — не замедляемся, один раз советуем сменить секрет
    un = Api.__new__(Api)
    un._lock, un.paced, un.share_expected = threading.Lock(), True, False
    un._init_share()
    un.base_gap = un.min_gap = 60 / (400 * RATE_SHARE)
    said = []
    catch = logging.Handler()
    catch.emit = lambda rec: said.append(rec.getMessage())
    log.addHandler(catch)
    try:
        for _ in range(3):
            minute(250, 45, un)
        minute(250, 0, un); minute(250, 0, un); minute(250, 50, un); minute(250, 50, un); minute(250, 50, un)
    finally:
        log.removeHandler(catch)
    assert abs(un.min_gap - un.base_gap) < 1e-9, un.min_gap
    assert sum("Скорость не снижаю" in s for s in said) == 1 and not any("делю лимит" in s for s in said), said
    # --- шанс по наблюдениям за похожими лотами ---
    pairs10 = [(100.0, 1)] * 10
    base = sale_chance(100, 1, pairs10, 24 * 7)["chance"]
    hot = sale_chance(100, 1, pairs10, 24 * 7, rates=(300, 400))
    cold = sale_chance(100, 1, pairs10, 24 * 7, rates=(0, 600))
    assert hot["chance"] > base > cold["chance"] and cold["chance"] < 0.2 and hot["data"]["weight"] > 0.85, (base, hot, cold)
    assert rate_bin(0.5, RATIO_BINS) == 0 and rate_bin(1.0, RATIO_BINS) == 2 and rate_bin(100, LIQ_BINS) == 3
    # --- порядок прохода: горячие — дважды ---
    its = [(f"i{k}", f"П{k}") for k in range(10)]
    order = pass_order(its, {"i5": 9.0, "i2": 1.0})
    assert order.count(("i5", "П5")) == 2 and order[0] == ("i5", "П5") and len(order) == 12
    assert pass_order(its, {}) == its
    # --- радар: где дешёвые лоты бывают чаще и выгоднее ---
    t_r = datetime(2026, 10, 20, 20, 0).timestamp()
    r_rows = ([("a", -1, -1, t_r + i * 600, t_r + i * 600 + 610, t_r + i * 600 + 900, "sold", 0.7, 10) for i in range(8)]
              + [("b", -1, -1, t_r + 3600 * i, t_r + 3600 * i + 610, None, None, 0.85, 1) for i in range(2)]
              + [("c", 4, 15, t_r, t_r + 610, None, None, 0.6, 1)])
    rad = radar(r_rows, 10, lambda item, add: {"a": 1000, "b": 50000, "c": 200000}[item], 0.15, 0.05, 1000,
                local_hour=21)
    by_r = {r["item_id"]: r for r in rad}
    assert rad[0]["item_id"] in ("a", "c") and by_r["a"]["buy_below"] == 850 and by_r["a"]["need"] == 10
    assert abs(by_r["a"]["per_day"] - 8 / 10 * 24) < 1e-9 and abs(by_r["a"]["life_min"] - 15) < 1e-9
    assert by_r["a"]["hours"] == (20, 23) and by_r["a"]["peak"] and by_r["c"]["bucket"] == (4, 15)
    assert by_r["b"]["profit"] == 50000 * 0.95 - 42500 and by_r["b"]["life_min"] is None
    its40 = [(f"j{k}", f"Р{k}") for k in range(40)]
    heat40 = {f"j{k}": (9.0 if k < 5 else 1.0 if k < 20 else 0) for k in range(40)}
    o0, o1 = pass_order(its40, heat40, pass_no=0), pass_order(its40, heat40, pass_no=1, keep={"j39"})
    assert o0.count(("j0", "Р0")) == 3 and set(o0) == set(its40)
    assert ("j30", "Р30") not in o1 and ("j39", "Р39") in o1 and o1.count(("j0", "Р0")) == 3
    assert lots_cap([{"buyoutPrice": p} for p in range(1, 101)]) == 100 and lots_cap([{"buyoutPrice": 5}]) == math.inf
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
