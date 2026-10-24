# -*- coding: utf-8 -*-
"""
STALZONE Трекер — приложение для поиска лотов ниже рынка.

Файлы (в одной папке):
  stalzone_app.py      — это приложение (окно + сервер интерфейса)
  stalzone_tracker.py  — движок: API, расчёт рыночной цены и прибыли
  build_exe.bat        — собирает STALZONE Tracker.exe, чтобы поделиться с другом

Установка:  pip install requests pywebview
Запуск:     python stalzone_app.py

Данные (ключи, настройки, найденные лоты, журнал) хранятся отдельно от программы:
  Windows: %APPDATA%\\STALZONE Tracker   ·   другие системы: ~/.stalzone_tracker
Поэтому обновление или перенос программы их не стирает, а в .exe для друга они не попадают.

Если pywebview не установлен, интерфейс откроется в браузере.
Ничего не покупает сам — только находит лоты и считает прибыль перепродажи.
"""

import base64
import hashlib
import json
import math
import logging
import os
import re
import secrets
import shutil
import sqlite3
import statistics
import subprocess
import sys
import threading
import gzip
import time
import uuid
import webbrowser
import zipfile
from collections import deque
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

try:
    import requests
    import stalzone_tracker as eng
    import stalzone_fonts
    from stalzone_ui import UI_HTML
except ImportError as e:
    print("Ошибка запуска:", e)
    print("Нужен модуль requests (pip install requests) и файлы stalzone_tracker.py, stalzone_ui.py, stalzone_fonts.py рядом.")
    input("Нажми Enter, чтобы закрыть…")
    sys.exit(1)

APP_NAME = "STALZONE Tracker"
APP_VERSION = "2.5"
# Откуда брать обновления: открытый репозиторий GitHub «владелец/имя» только с готовыми .exe
# (код лежит в закрытом). В настройках можно указать другой. Пусто — обновления не проверяются.
UPDATE_REPO = "Enotsbeye/stalzone-tracker-releases"
OLD_UPDATE_REPOS = ("Enotsbeye/stalzone-tracker",)   # откуда обновлялись версии до 1.8
EXE_ASSET = "STALZONE-Tracker.exe"      # файлы в выпуске: программа для Windows
SRC_ASSET = "stalzone_source.zip"       # и исходники — для запуска через Python
SOURCE_FILES = ("stalzone_app.py", "stalzone_tracker.py", "stalzone_ui.py", "stalzone_fonts.py")   # без них не запустится
SOURCE_EXTRA = ("FONTS-OFL.txt",)       # лицензия шрифтов — кладём рядом, если есть в архиве
GITHUB_API = "https://api.github.com"
# Папка программы (рядом с .py или .exe) — только чтобы найти файлы старых версий
APP_DIR = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
           else os.path.dirname(os.path.abspath(__file__)))


def data_dir():
    """Папка с данными пользователя. STALZONE_DATA_DIR — чтобы хранить данные где-то ещё."""
    path = os.environ.get("STALZONE_DATA_DIR")
    if not path:
        if os.name == "nt":
            path = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
        else:
            path = os.path.join(os.path.expanduser("~"), ".stalzone_tracker")
    os.makedirs(path, exist_ok=True)
    return path


DATA_DIR = data_dir()
eng.HERE = DATA_DIR                                        # справочник предметов
eng.SEEN_FILE = os.path.join(DATA_DIR, "seen_lots.json")   # о каких лотах уже сообщали
eng.TOKEN_FILE = os.path.join(APP_DIR, "api_token.json")   # старый файл с токеном — удаляется
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
DEALS_FILE = os.path.join(DATA_DIR, "deals.json")
JOURNAL_FILE = os.path.join(DATA_DIR, "journal.log")
PURCHASES_FILE = os.path.join(DATA_DIR, "purchases.json")   # «Мои покупки»
KEEP_DEALS_DAYS = 3


def write_json(path, obj):
    """Запись без риска испортить файл: сначала во временный, потом подмена одним действием."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def migrate_old_files():
    """Старые версии хранили файлы рядом с программой — копируем их в папку данных.
    Если программа собрана в dist\\, смотрим и в папку выше (там лежали .py-файлы)."""
    places = [APP_DIR]
    if os.path.basename(APP_DIR).lower() == "dist":
        places.append(os.path.dirname(APP_DIR))
    copied = []
    for name in ("settings.json", "seen_lots.json"):
        new = os.path.join(DATA_DIR, name)
        if os.path.exists(new):
            continue
        for place in places:
            old = os.path.join(place, name)
            if os.path.exists(old) and os.path.abspath(old) != os.path.abspath(new):
                try:
                    shutil.copy2(old, new)
                    copied.append(name)
                except OSError:
                    pass
                break
    return copied


MIGRATED = migrate_old_files()

PROD_URL = "https://eapi.stalzone.com"
DEMO_URL = "https://dapi.stalzone.com"
SETTINGS_VERSION = 4
DEFAULTS = dict(eng.CONFIG, settings_version=SETTINGS_VERSION, watch=[],   # новый пользователь начинает с пустого списка
                calibrate=True,            # поправлять оценку перепродажи по сверке с фактическими продажами
                threshold_expected=False,  # порог прибыли — по «прибыль × шанс продажи»
                keep_awake=True,           # не давать компьютеру уснуть, пока идёт поиск
                autostart=False,           # запускать программу вместе с Windows
                autorun_search=False,      # начинать поиск сразу при запуске программы
                alerts=True,               # Telegram: трекер встал, компьютер спал, нет связи с сервером, продано, перебили
                skills={})                 # уровни навыков убежища — для калькулятора крафта
OPEN_LINKS = {
    "api_bot": "https://t.me/stalzone_api_bot",
    "docs": "https://eapi.stalzone.net/overview.html",
    "botfather": "https://t.me/BotFather",
    "revoked_new": "https://github.com/Enotsbeye/stalzone-tracker-releases/new/main?filename=revoked.txt",
    "revoked_edit": "https://github.com/Enotsbeye/stalzone-tracker-releases/edit/main/revoked.txt",
    "releases": "https://github.com/Enotsbeye/stalzone-tracker-releases/releases/latest",
}
QUALITY = ["обычный", "необычный", "особый", "редкий", "исключительный", "легендарный"]


def load_settings():
    cfg = dict(DEFAULTS)
    saved = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                saved = json.load(f)
        except (OSError, ValueError):
            saved = {}
    cfg.update(saved)
    if saved and saved.get("settings_version", 1) < 2:
        # старые версии по умолчанию проверяли раз в 3 минуты и историю раз в 30/15 — ускоряем,
        # только если пользователь сам эти числа не менял
        if saved.get("poll_minutes") == 3:
            cfg["poll_minutes"] = 1
        if saved.get("history_refresh_minutes") in (30, 15):
            cfg["history_refresh_minutes"] = 10
        cfg["settings_version"] = SETTINGS_VERSION
    if saved and saved.get("settings_version", 1) < 3:
        # 2.1: проверка без пауз между проходами — если стояло прежнее значение по умолчанию (1 мин)
        if float(cfg.get("poll_minutes") or 0) == 1:
            cfg["poll_minutes"] = 0
        cfg["settings_version"] = SETTINGS_VERSION
    if saved and saved.get("settings_version", 1) < 4:
        # 2.2: эти настройки убраны из окна — ставим значения по умолчанию, чтобы невидимое ничего не меняло
        cfg.update(poll_minutes=0, history_hours=eng.CONFIG["history_hours"], notify_min_chance=0,
                   threshold_expected=False, calibrate=True, keep_awake=True, alerts=True)
        cfg["settings_version"] = SETTINGS_VERSION
    if str(cfg.get("update_repo") or "").strip("/") in OLD_UPDATE_REPOS:
        cfg["update_repo"] = ""     # код теперь закрыт — обновления берём из открытого репозитория
    return cfg


def save_settings(cfg):
    write_json(SETTINGS_FILE, cfg)


def load_deals():
    """Находки прошлых запусков: без снятых с аукциона и старше KEEP_DEALS_DAYS дней."""
    try:
        with open(DEALS_FILE, encoding="utf-8") as f:
            deals = json.load(f)
    except (OSError, ValueError):
        return []
    now, keep = time.time(), []
    for d in deals if isinstance(deals, list) else []:
        try:
            if now - float(d.get("found", 0)) > KEEP_DEALS_DAYS * 86400:
                continue
            if d.get("ends") and eng.parse_time(d["ends"]).timestamp() < now:
                continue
            if d.get("gone"):     # лот уже купили или сняли
                continue
            d["notify"] = False   # о них уже сообщали — без звука
            keep.append(d)
        except (TypeError, ValueError, AttributeError, KeyError):
            continue
    return keep[:400]


def load_purchases():
    try:
        with open(PURCHASES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return [p for p in data if isinstance(p, dict) and p.get("id")] if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def is_rare(cfg, item_id, name, meta, quality):
    """Особо редкая находка: предмет со звёздочкой, снаряжение ранга «Легенда» или артефакт высокого качества."""
    if not cfg.get("rare_enabled", True):
        return False
    marks = {eng.norm(str(x)) for x in cfg.get("rare_items") or []}
    if item_id in marks or eng.norm(name) in marks:
        return True
    meta = meta or {}
    if meta.get("rank") == "RANK_LEGEND":
        return True
    return meta.get("cat") == "artefact" and quality is not None and quality >= int(cfg.get("rare_quality", 4))


def send_telegram(cfg, text):
    """Сообщение в Telegram. (ok, текст ошибки для журнала)."""
    token, chat = str(cfg.get("telegram_token") or "").strip(), str(cfg.get("telegram_chat_id") or "").strip()
    if not (token and chat):
        return False, ""
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text}, timeout=20)
    except requests.RequestException as e:
        return False, f"Telegram не ответил: {type(e).__name__}"
    if r.status_code == 200:
        return True, ""
    try:
        why = r.json().get("description", "")
    except ValueError:
        why = ""
    hints = {401: "неверный токен бота", 400: "неверный Chat ID или ты не нажал Start у своего бота",
             403: "бот заблокирован — открой его и нажми Start", 404: "неверный токен бота"}
    return False, f"Telegram отказал: {hints.get(r.status_code, 'ошибка ' + str(r.status_code))}" + (f" ({why})" if why else "")


WATCH_MAX = 300            # предметов в своём списке (категории целиком — сверх этого)
ICON_URL = "https://raw.githubusercontent.com/EXBO-Studio/stalzone-database/main/{region}{path}"   # картинки предметов
RESTART_DELAY = 3          # сменили ключи — перезапуск через столько секунд после последнего изменения
RESTART_KEYS = ("client_id", "client_secret", "app_token", "base_url", "region", "history_keep_days", "extra_keys")
QUIET_KEYS = ("telegram_token", "telegram_chat_id", "update_repo", "server_url", "server_port",
              "server_url_override")   # из-за них новый проход не начинаем — просто запомнить
FEED_PORT = 8790            # сервер для подписчиков слушает только этот компьютер; наружу — через Tailscale Funnel
FEED_POLL = 15              # подписчик спрашивает сервер раз в столько секунд
FEED_MIN_INTERVAL = 10      # чаще одного запроса в 10 с с одного кода — отказ
FEED_KEEP_GONE = 30 * 60    # пропавшие находки ещё полчаса видны подписчикам («уже купили»)
EXCLUSIVE_S = 120           # новая находка сначала только одному подписчику (по очереди), потом — всем
WANT_FRESH = 600            # что ищут подписчики: учитываем тех, кто приходил за последние 10 минут
SUB_ITEMS_MAX = 1500        # больше предметов для подписчиков не берём
MAX_EXTRA_KEYS = 30
NEAR_DISCOUNT = 0.08        # «почти находки»: лоты дешевле рынка хотя бы на 8%…
NEAR_MIN_PROFIT = 3000      # …с прибылью от 3 000 ₽, которые не прошли твои пороги, — видно, что и почему отсеяно
NEAR_KEEP = 30 * 60         # «почти находка» видна, пока лот на аукционе, но не дольше получаса без новых проверок
NEAR_MAX = 40
QUIET_SUMMARY = 30 * 60     # столько без находок — пишем в журнал, что было отсеяно порогами
CRAFT_PER_PASS = 15         # цены для калькулятора крафта: столько предметов за проход (≈ 20–40 запросов в минуту)
STALL_ALERT = 10 * 60       # поиск идёт, а проходов нет столько секунд — сообщить в Telegram


def deal_value(rec, cfg):
    """С чем сравнивать порог прибыли: сама прибыль или (если так в настройках) ожидаемая — прибыль × шанс
    продать за сутки. Без оценки шанса — просто прибыль."""
    profit = float(rec.get("profit") or 0)
    if cfg.get("threshold_expected") and rec.get("chance") is not None:
        return profit * float(rec["chance"])
    return profit


def meets_thresholds(rec, cfg, rare):
    """Подходит ли находка под свои пороги: «дешевле рынка на» и минимальная прибыль
    (у особо редких — свой порог прибыли)."""
    min_profit = float(cfg.get("min_profit", 0))
    if rare and cfg.get("rare_enabled", True):
        min_profit = min(min_profit, float(cfg.get("rare_min_profit", min_profit)))
    if deal_value(rec, cfg) < min_profit:
        return False
    if rec.get("kind") == "bid":
        return bool(cfg.get("bids", True))
    k = 1 - float(cfg.get("discount", 0.15))
    unit = float(rec.get("unit") or 0)
    return unit <= float(rec.get("hist") or 0) * k + 1e-6 and unit <= float(rec.get("market") or 0) * k + 1e-6


def near_pct(rec):
    """На сколько процентов лот дешевле и прошлых сделок, и цены перепродажи — меньшее из двух,
    как его проверяет meets_thresholds."""
    unit = float(rec.get("unit") or 0)
    base = min(float(rec.get("hist") or 0), float(rec.get("market") or 0))
    return (1 - unit / base) * 100 if base > 0 else 0.0


def is_near(rec):
    """Стоит ли показать находку, не прошедшую пороги, в «почти находках»."""
    return (rec.get("kind") == "buyout" and float(rec.get("profit") or 0) >= NEAR_MIN_PROFIT
            and near_pct(rec) >= NEAR_DISCOUNT * 100 - 1e-6)


def parse_keys(text, old=()):
    """Дополнительные ключи из поля настроек: по строке «Client ID  Client Secret» (через пробел, «:» или «;»).
    Вместо секрета можно оставить точки — тогда берём прежний секрет этого ID. → [{"id", "secret"}]."""
    known = {str(k.get("id")): str(k.get("secret")) for k in old or [] if isinstance(k, dict)}
    out, seen = [], set()
    lines = text if isinstance(text, list) else str(text or "").splitlines()
    for line in lines:
        if isinstance(line, dict):
            cid, secret = str(line.get("id") or "").strip(), str(line.get("secret") or "").strip()
        else:
            parts = [x for x in re.split(r"[\s:;,]+", str(line).strip()) if x]
            if not parts:
                continue
            if len(parts) != 2:
                raise ValueError("В каждой строке — Client ID и Client Secret через пробел")
            cid, secret = parts
        if not cid or cid in seen:
            continue
        if not secret or set(secret) <= {"•", "*"}:
            secret = known.get(cid, "")
            if not secret:
                raise ValueError(f"Для ключа {cid} нужен Client Secret")
        seen.add(cid)
        out.append({"id": cid, "secret": secret})
    return out[:MAX_EXTRA_KEYS]


def make_api(cfg):
    """Ключ API для проверки: один — Api, несколько (свой + дополнительные) — KeyPool, запросы делятся."""
    extra = [(k["id"], k["secret"]) for k in cfg.get("extra_keys") or []
             if isinstance(k, dict) and k.get("id") and k.get("secret") and k["id"] != cfg.get("client_id")]
    if extra and cfg.get("client_id") and cfg.get("client_secret") and not cfg.get("shared_api"):
        eng.FETCH_THREADS = min(48, 10 * (len(extra) + 1))
        eng.FETCH_AHEAD = 2 * eng.FETCH_THREADS
        return eng.KeyPool(cfg, extra)
    eng.FETCH_THREADS, eng.FETCH_AHEAD = 10, 20
    return eng.Api(cfg)


def wants(want, rec):
    """Подходит ли находка подписчику: его предметы и категории (пусто — всё) и его пороги."""
    w, c = want.get("w") or [], want.get("c") or []
    if (w or c) and rec.get("item_id") not in w and rec.get("cat") not in c:
        return False
    cfg = {"min_profit": float(want.get("mp") or 0), "discount": float(want.get("d") or 0.15),
           "rare_enabled": bool(want.get("re", True)), "rare_min_profit": float(want.get("rp") or 0),
           "rare_quality": int(want.get("rq") or 4), "bids": True}
    rare = is_rare(cfg, rec.get("item_id"), rec.get("name", ""), {"cat": rec.get("cat"), "rank": rec.get("rank")},
                   rec.get("quality"))
    return meets_thresholds(rec, cfg, rare)


def plural_ru(n, forms):
    """1 лот, 2 лота, 5 лотов."""
    n = abs(int(n)) % 100
    if 10 < n < 20:
        return forms[2]
    return forms[0] if n % 10 == 1 else forms[1] if 2 <= n % 10 <= 4 else forms[2]


def why_text(why):
    """Причина из near_reason словами: «твой порог прибыли 40 000 ₽»."""
    parts = []
    for w in why or []:
        if w.get("what") == "profit":
            parts.append(f"твой порог {'ожидаемой ' if w.get('expected') else ''}прибыли {eng.fmt_rub(w['need'])}")
        elif w.get("what") == "pct":
            parts.append(f"нужно дешевле рынка на {w['need']:.0f}%")
    return ", ".join(parts) or "не прошла пороги"


def near_reason(rec, cfg, rare):
    """Какие пороги не прошла находка: [{"what": "profit", "need": ₽}, {"what": "pct", "need": %}]."""
    min_profit = float(cfg.get("min_profit", 0))
    if rare and cfg.get("rare_enabled", True):
        min_profit = min(min_profit, float(cfg.get("rare_min_profit", min_profit)))
    why = []
    if deal_value(rec, cfg) < min_profit:
        why.append({"what": "profit", "need": min_profit, "expected": bool(cfg.get("threshold_expected"))
                    and rec.get("chance") is not None})
    need = float(cfg.get("discount", 0.15)) * 100
    if near_pct(rec) < need - 1e-6:
        why.append({"what": "pct", "need": need})
    return why


def feed_text(rec, cfg):
    """Сообщение в Telegram о находке с сервера (у подписчика — со своими порогами)."""
    rub = eng.fmt_rub
    if rec.get("kind") == "bid":
        max_bid = rec["market"] * (1 - cfg.get("fee", 0.05)) * rec["amount"] - float(cfg.get("min_profit", 0))
        lines = [f"⏳ {rec['name']} — ставка ниже рынка",
                 f"{rec['amount']} шт, {'текущая ставка' if rec.get('has_bids') else 'старт'} {rub(rec['cost'])}",
                 f"Перепродать ~{rub(rec['market'])}/шт · ставь не выше {rub(max_bid)}",
                 f"Прибыль сейчас ~{rub(rec['profit'])}"]
    else:
        lines = [f"🔔 {rec['name']} — дешевле рынка на {rec['pct']:.0f}%",
                 f"Купить: {rec['amount']} шт за {rub(rec['cost'])} ({rub(rec['unit'])}/шт)",
                 f"Перепродать ~{rub(rec['market'])}/шт · прибыль ~{rub(rec['profit'])} после комиссии"]
    if rec.get("chance_info"):
        lines.append(chance_text(rec["chance_info"]))
    if rec.get("only_you_until") and rec["only_you_until"] > time.time():
        lines.insert(0, f"🎯 Только тебе ещё ~{max(1, round((rec['only_you_until'] - time.time()) / 60))} мин — потом увидят все")
    return ("💎 ОСОБО РЕДКИЙ\n" if rec.get("rare") else "") + "\n".join(lines)


def chance_text(c):
    if not c:
        return ""
    hours = c.get("hours")
    when = "" if hours is None else (f", обычно за ~{hours:.0f} ч" if hours < 48 else f", обычно за ~{hours / 24:.0f} дн.")
    return f"Шанс продать за сутки: ~{c['chance'] * 100:.0f}% ({eng.chance_label(c['chance'])}){when}"


def load_journal(lines=200):
    """Последние строки журнала прошлых запусков. Файл больше 1 МБ укорачиваем."""
    try:
        with open(JOURNAL_FILE, encoding="utf-8") as f:
            all_lines = f.read().splitlines()
    except OSError:
        return []
    if os.path.getsize(JOURNAL_FILE) > 1_000_000:
        try:
            with open(JOURNAL_FILE + ".tmp", "w", encoding="utf-8") as f:
                f.write("\n".join(all_lines[-3000:]) + "\n")
            os.replace(JOURNAL_FILE + ".tmp", JOURNAL_FILE)
        except OSError:
            pass
    today, out = datetime.now().strftime("%Y-%m-%d"), []
    for line in all_lines[-lines:]:
        stamp, _, msg = line.partition("\t")
        day, _, clock = stamp.partition(" ")
        if not msg or not clock:
            continue
        out.append({"t": clock if day == today else f"{day[8:10]}.{day[5:7]} {clock[:5]}", "m": msg})
    return out


def open_folder(path):
    """Открыть папку в проводнике (Windows) или в файловом менеджере."""
    try:
        if os.name == "nt":
            os.startfile(path)  # есть только в Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


# ------------------------------- Обновления -------------------------------
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def parse_version(text):
    """'v1.7.2' → (1, 7, 2); без цифр — ()."""
    return tuple(int(n) for n in re.findall(r"\d+", str(text or ""))[:4])


def clean_env():
    """Окружение для запуска новой копии программы. Собранная PyInstaller программа хранит в переменных
    _PYI_* путь к своей временной папке; новая версия по тому же пути, унаследовав их, ищет свои файлы
    в папке старой (а её уже удалили) и падает: «Failed to load Python DLL». Поэтому чистим."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("_PYI_", "_MEIPASS"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def _spawn_detached(cmd, **kw):
    kw.setdefault("env", clean_env())
    """Запустить процесс, который переживёт закрытие этой программы."""
    if os.name != "nt":
        return subprocess.Popen(cmd, close_fds=True, start_new_session=True, **kw)
    flags = 0x08000000 | 0x00000200   # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP — без окна консоли
    try:  # выйти из «задания» Windows, если программа в нём, — иначе процесс закроется вместе с ней
        return subprocess.Popen(cmd, close_fds=True, creationflags=flags | 0x01000000, **kw)
    except OSError:  # задание не разрешает выход — запускаем как есть
        return subprocess.Popen(cmd, close_fds=True, creationflags=flags, **kw)


class Updater:
    """Обновление из выпусков (Releases) на GitHub: проверить → скачать → заменить себя → перезапуститься.
    .exe нельзя заменить, пока он запущен, поэтому замену делает маленький bat после выхода программы."""

    def __init__(self, state):
        self.state = state
        self.lock = threading.Lock()
        self.status, self.message, self.info = "idle", "", None

    def _set(self, status, message):
        with self.lock:
            self.status, self.message = status, message
        if status in ("available", "error", "restarting"):
            self.state.add_log("Обновление: " + message)

    def repo(self):
        if os.environ.get("STALZONE_NO_UPDATE"):   # для тестов и тех, кто не хочет обновлений
            return ""
        return str(self.state.cfg.get("update_repo") or UPDATE_REPO or "").strip().strip("/")

    def snapshot(self):
        with self.lock:
            info = self.info or {}
            return {"status": self.status, "message": self.message, "repo": self.repo(),
                    "version": info.get("version"), "notes": info.get("notes", ""), "url": info.get("url")}

    def _latest(self, repo):
        """Последний выпуск репозитория: (info | None, ошибка | None). 404 — выпусков нет (не ошибка)."""
        try:
            r = requests.get(f"{GITHUB_API}/repos/{repo}/releases/latest", timeout=20,
                             headers={"Accept": "application/vnd.github+json"})
        except requests.RequestException as e:
            return None, f"GitHub не ответил ({type(e).__name__})"
        if r.status_code == 404:
            return None, None
        if r.status_code != 200:
            return None, f"GitHub ответил {r.status_code}"
        try:
            rel = r.json()
            assets = {a["name"]: a for a in rel.get("assets", [])}
            version = str(rel.get("tag_name") or "").lstrip("vV")
        except (ValueError, KeyError, TypeError, AttributeError):
            return None, "GitHub прислал непонятный ответ"
        return {"version": version, "notes": str(rel.get("body") or "")[:1500], "url": rel.get("html_url"),
                "exe": assets.get(EXE_ASSET), "src": assets.get(SRC_ASSET), "repo": repo}, None

    def check(self):
        repo = self.repo()
        if not REPO_RE.match(repo):
            self._set("off", "Обновления не настроены: укажи репозиторий GitHub в настройках")
            return
        self._set("checking", "Проверяю обновления…")
        # пока идёт переезд в открытый репозиторий с выпусками, смотрим и в старый
        repos = [repo] + ([r for r in OLD_UPDATE_REPOS if r != repo] if repo == UPDATE_REPO else [])
        frozen = getattr(sys, "frozen", False)
        found, errors = [], []
        for name in repos:
            info, err = self._latest(name)
            if err:
                errors.append(err)
            elif info:
                found.append(info)
        if not found:
            if errors and len(errors) == len(repos):
                self._set("error", errors[0])
            else:
                self._set("latest", "В репозитории пока нет выпусков")
            return
        usable = [i for i in found if (i["exe"] if frozen else i["src"])] or found
        info = max(usable, key=lambda i: parse_version(i["version"]))
        needed = info["exe"] if frozen else info["src"]
        with self.lock:
            self.info = info
        if parse_version(info["version"]) > parse_version(APP_VERSION) and needed:
            self._set("available", f"Доступна версия {info['version']} (у тебя {APP_VERSION})")
        else:
            self._set("latest", f"У тебя последняя версия ({APP_VERSION})")

    def _download(self, asset, folder):
        path = os.path.join(folder, asset["name"] + ".part")
        with requests.get(asset["browser_download_url"], stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(256 * 1024):
                    f.write(chunk)
        if asset.get("size") and os.path.getsize(path) != asset["size"]:
            raise OSError("файл скачался не целиком")
        return path

    def apply(self):
        """Скачать и поставить новую версию, потом перезапуститься. Работает в отдельном потоке."""
        with self.lock:
            if self.status != "available" or not self.info:
                return
            self.status = "downloading"
            self.message = f"Скачиваю версию {self.info['version']}…"
        info = self.info
        folder = os.path.join(DATA_DIR, "update")
        try:
            os.makedirs(folder, exist_ok=True)
            if getattr(sys, "frozen", False):
                new_exe = self._download(info["exe"], folder)
                with open(new_exe, "rb") as f:
                    if f.read(2) != b"MZ":
                        raise OSError("скачался не файл программы")
                self._swap_exe_after_exit(new_exe, folder)
            else:
                self._replace_sources(self._download(info["src"], folder))
                self._restart_sources()
        except (requests.RequestException, OSError, zipfile.BadZipFile, SyntaxError) as e:
            self._set("error", f"Не получилось обновиться: {e}")
            return
        self._set("restarting", f"Версия {info['version']} установлена — перезапускаюсь")
        self.state.request_exit()

    def _swap_exe_after_exit(self, new_exe, folder):
        """bat ждёт, пока программа закроется (файл освободится), подменяет .exe и запускает новую."""
        bat = os.path.join(folder, "apply_update.bat")
        script = "\r\n".join([
            "@echo off",
            "chcp 65001 >nul",
            # новая версия должна запуститься как отдельная программа, а не как часть старой
            'set "PYINSTALLER_RESET_ENVIRONMENT=1"',
            'set "_PYI_APPLICATION_HOME_DIR="',
            'set "_PYI_ARCHIVE_FILE="',
            'set "_PYI_PARENT_PROCESS_LEVEL="',
            'set "_PYI_SPLASH_IPC="',
            'set "_MEIPASS2="',
            f'set "OLD={sys.executable}"',
            f'set "NEW={new_exe}"',
            "for /l %%i in (1,1,90) do (",
            '  move /y "%NEW%" "%OLD%" >nul 2>nul && goto started',
            "  ping -n 2 127.0.0.1 >nul",
            ")",
            "exit /b 1",
            ":started",
            'start "" "%OLD%"',
            'del "%~f0"',
            ""])
        with open(bat, "w", encoding="utf-8") as f:
            f.write(script)
        self.state.save_deals()
        _spawn_detached(["cmd", "/c", bat])

    def _replace_sources(self, zip_path):
        """Из архива — файлы программы рядом с ней. Сначала проверяем, что все есть и это корректный
        Python, потом подменяем (каждый — одним действием)."""
        wanted = set(SOURCE_FILES)
        found = {}
        with zipfile.ZipFile(zip_path) as z:
            for name in z.namelist():
                base = name.rsplit("/", 1)[-1]
                if base in wanted or base in SOURCE_EXTRA:
                    found[base] = z.read(name)
        if not wanted <= set(found):
            raise OSError("в архиве нет файлов программы")
        for base in wanted:
            compile(found[base].decode("utf-8"), base, "exec")   # битый файл не ставим
        for base, data in found.items():
            target = os.path.join(APP_DIR, base)
            with open(target + ".new", "wb") as f:
                f.write(data)
            os.replace(target + ".new", target)

    def _restart_sources(self):
        self.state.save_deals()
        exe = sys.executable
        pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.name == "nt" and os.path.exists(pythonw):
            exe = pythonw   # без чёрного окна консоли
        _spawn_detached([exe, os.path.join(APP_DIR, "stalzone_app.py")], cwd=APP_DIR)


# ------------------------------ Доступ по кодам ------------------------------
# Владелец выдаёт каждому человеку код: имя + ID его компьютера + срок, подписанные личным ключом
# владельца (Ed25519). Программа проверяет подпись встроенным открытым ключом — подделать код
# или перенести его на другой ПК нельзя. Отозвать: вписать имя или номер кода в revoked.txt
# в открытом репозитории с выпусками.
# Пустой OWNER_PUBLIC_KEY — программа открыта всем (так владелец создаёт свой ключ).
OWNER_PUBLIC_KEY = "8jFXVw8KRA87j0EZ51KzGtDkzun5eXuanTy2Q05b_5Y"
REVOKED_URL = "https://raw.githubusercontent.com/Enotsbeye/stalzone-tracker-releases/main/revoked.txt"
OWNER_KEY_FILE = os.path.join(DATA_DIR, "owner_key.pem")      # личный ключ — только у владельца
ISSUED_FILE = os.path.join(DATA_DIR, "issued_codes.json")     # кому владелец выдавал коды
SEATS_FILE = os.path.join(DATA_DIR, "code_seats.json")        # какие компьютеры заняли места по кодам без привязки
ANY_MACHINE = "*"           # код без привязки: компьютер привязывается сам при первом подключении к серверу
MAX_SEATS = 1000
ACCESS_FILE = os.path.join(DATA_DIR, "access_state.json")     # отозванные и «самая поздняя дата»
DEVICE_KEY_FILE = os.path.join(DATA_DIR, "device_key.pem")     # ключ этого компьютера — для ключа API владельца
CODE_PREFIX = "SZ1-"
REQUEST_PREFIX = "SZR1-"   # код запроса: ID компьютера + его открытый ключ
REVOKED_REFRESH = 3 * 3600

try:
    from cryptography.exceptions import InvalidSignature, InvalidTag
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
except ImportError:   # без модуля cryptography коды не проверить
    Ed25519PrivateKey = Ed25519PublicKey = serialization = X25519PrivateKey = None
    InvalidSignature = InvalidTag = Exception


def _b64e(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def machine_id():
    """Короткий ID компьютера: из MachineGuid Windows (меняется только при переустановке системы)."""
    raw = ""
    if os.name == "nt":
        try:
            import winreg
            flags = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, flags) as k:
                raw = str(winreg.QueryValueEx(k, "MachineGuid")[0])
        except OSError:
            raw = ""
    if not raw:
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                with open(path, encoding="utf-8") as f:
                    raw = f.read().strip()
                if raw:
                    break
            except OSError:
                pass
    raw = raw or str(uuid.getnode())
    code = base64.b32encode(hashlib.sha256(("stalzone|" + raw).encode("utf-8")).digest()).decode("ascii")[:10]
    return code[:5] + "-" + code[5:]


def _raw_pub(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _share_key(shared, eph_pub, dev_pub):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=b"stalzone-share-v1" + eph_pub + dev_pub).derive(shared)


def seal_for(dev_pub, plaintext, aad):
    """Зашифровать для одного компьютера (его открытый ключ X25519): расшифрует только он."""
    eph = X25519PrivateKey.generate()
    eph_pub = _raw_pub(eph)
    key = _share_key(eph.exchange(X25519PublicKey.from_public_bytes(dev_pub)), eph_pub, dev_pub)
    nonce = secrets.token_bytes(12)
    return _b64e(eph_pub + nonce + AESGCM(key).encrypt(nonce, plaintext, aad))


def unseal(dev_key, blob, aad):
    raw = _b64d(blob)
    eph_pub, nonce, ct = raw[:32], raw[32:44], raw[44:]
    key = _share_key(dev_key.exchange(X25519PublicKey.from_public_bytes(eph_pub)), eph_pub, _raw_pub(dev_key))
    return AESGCM(key).decrypt(nonce, ct, aad)


def norm_machine(text):
    s = re.sub(r"[^A-Z0-9]", "", str(text or "").upper())
    return s[:5] + "-" + s[5:] if len(s) == 10 else ""


def today_day():
    return int(time.time() // 86400)


def day_text(day):
    return datetime.fromtimestamp(day * 86400, timezone.utc).strftime("%d.%m.%Y")


class Access:
    """Проверка кода доступа. Владелец (у кого есть личный ключ) проходит всегда."""

    def __init__(self, state):
        self.state = state
        self.lock = threading.Lock()
        self.machine = machine_id()
        self.owner_key = self._load_owner_key()
        saved = self._load_state()
        self.revoked = set(saved.get("revoked", []))
        self.max_day = int(saved.get("max_day", 0))
        self.revoked_at = 0.0
        self._device = None
        self._shared = (None, None)   # (код, расшифрованный ключ API владельца) — только в памяти

    # --- ключ этого компьютера и код запроса ---
    def device_key(self):
        """Ключ X25519 этого компьютера: им расшифровывается ключ API владельца из кода доступа."""
        if self._device is None and X25519PrivateKey is not None:
            try:
                with open(DEVICE_KEY_FILE, "rb") as f:
                    self._device = serialization.load_pem_private_key(f.read(), password=None)
            except (OSError, ValueError, TypeError):
                key = X25519PrivateKey.generate()
                try:
                    with open(DEVICE_KEY_FILE + ".tmp", "wb") as f:
                        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                  serialization.NoEncryption()))
                    os.replace(DEVICE_KEY_FILE + ".tmp", DEVICE_KEY_FILE)
                    self._device = key
                except OSError:
                    return None
        return self._device

    def request_code(self):
        """Что друг отправляет владельцу: ID компьютера + открытый ключ компьютера."""
        key = self.device_key()
        raw = self.machine.replace("-", "").encode("ascii") + (_raw_pub(key) if key else b"")
        return REQUEST_PREFIX + _b64e(raw)

    @staticmethod
    def parse_request(text):
        """(ID компьютера, открытый ключ или None) из кода запроса или просто из ID."""
        t = re.sub(r"\s+", "", str(text or ""))
        if t.upper().startswith(REQUEST_PREFIX):
            try:
                raw = _b64d(t[len(REQUEST_PREFIX):])
                machine = norm_machine(raw[:10].decode("ascii"))
                return machine, (raw[10:42] if len(raw) >= 42 else None)
            except (ValueError, UnicodeDecodeError):
                return "", None
        return norm_machine(t), None

    def shared_api(self):
        """Ключ API владельца из кода доступа (если владелец его вложил) — расшифрован ключом этого
        компьютера. Только в памяти: в настройки и журнал не попадает. None — ключа в коде нет."""
        code = re.sub(r"\s+", "", str(self.state.cfg.get("access_code") or ""))
        if not code or not OWNER_PUBLIC_KEY or self.is_owner():
            return None
        if self._shared[0] == code:
            return self._shared[1]
        creds = None
        payload, err = self.parse(code)
        if not err and payload.get("k") and self.device_key() is not None:
            try:
                data = json.loads(unseal(self.device_key(), payload["k"], str(payload["i"]).encode()).decode("utf-8"))
                if isinstance(data, dict) and ((data.get("id") and data.get("secret")) or data.get("token")):
                    creds = {"client_id": str(data.get("id") or ""), "client_secret": str(data.get("secret") or ""),
                             "app_token": str(data.get("token") or "")}
            except (InvalidTag, ValueError, TypeError, UnicodeDecodeError):
                creds = None
        self._shared = (code, creds)
        return creds

    # --- ключ владельца ---
    @staticmethod
    def _load_owner_key():
        if serialization is None or not os.path.exists(OWNER_KEY_FILE):
            return None
        try:
            with open(OWNER_KEY_FILE, "rb") as f:
                return serialization.load_pem_private_key(f.read(), password=None)
        except (OSError, ValueError, TypeError):
            return None

    def owner_public(self):
        if not self.owner_key:
            return ""
        raw = self.owner_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return _b64e(raw)

    def is_owner(self):
        return bool(self.owner_key) and (not OWNER_PUBLIC_KEY or self.owner_public() == OWNER_PUBLIC_KEY)

    def create_owner_key(self):
        if Ed25519PrivateKey is None:
            return False, "Нет модуля cryptography — ключ не создать (pip install cryptography)"
        if self.owner_key:
            return True, "Ключ владельца уже есть"
        key = Ed25519PrivateKey.generate()
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
        with open(OWNER_KEY_FILE + ".tmp", "wb") as f:
            f.write(pem)
        os.replace(OWNER_KEY_FILE + ".tmp", OWNER_KEY_FILE)
        self.owner_key = key
        self.state.add_log("Создан ключ владельца — храни файл owner_key.pem, без него новые коды не выдать")
        return True, "Ключ владельца создан"

    # --- даты и отозванные ---
    def _load_state(self):
        try:
            with open(ACCESS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_state(self):
        try:
            write_json(ACCESS_FILE, {"revoked": sorted(self.revoked), "max_day": self.max_day})
        except OSError:
            pass

    def today(self):
        """Сегодня по UTC, но не раньше уже виденной даты — перевод часов назад не продлит код."""
        day = today_day()
        if day > self.max_day:
            self.max_day = day
            self._save_state()
        return max(day, self.max_day)

    def refresh_revoked(self, force=False):
        if not OWNER_PUBLIC_KEY or (not force and time.time() - self.revoked_at < REVOKED_REFRESH):
            return
        self.revoked_at = time.time()
        try:
            r = requests.get(REVOKED_URL, timeout=15, headers={"Cache-Control": "no-cache"})
        except requests.RequestException:
            return                         # нет сети — помним прошлый список
        if r.status_code == 404:
            lines = []
        elif r.status_code == 200:
            lines = r.text.splitlines()
        else:
            return
        try:   # дата с сервера GitHub — на случай, если часы на ПК отстают
            server_day = int(parsedate_to_datetime(r.headers.get("Date", "")).timestamp() // 86400)
        except (TypeError, ValueError, IndexError):
            server_day = 0
        revoked = {ln.split("#", 1)[0].strip().lower() for ln in lines}
        revoked.discard("")
        with self.lock:
            changed = revoked != self.revoked or server_day > self.max_day
            self.revoked = revoked
            self.max_day = max(self.max_day, server_day)
        if changed:
            self._save_state()

    # --- коды ---
    def issue(self, name, request, days, share=False, creds=None, server=None, base_day=None, seats=1):
        """Код доступа. Без кода запроса — код не привязан: компьютер (или до seats компьютеров) привязывается
        сам при первом подключении к серверу. Так код можно просто отправить — или выложить для группы."""
        if not self.is_owner() or not OWNER_PUBLIC_KEY:
            return False, "Выдавать коды может только владелец программы", None
        name = re.sub(r"\s+", " ", str(name or "")).strip()[:40]
        if not name:
            return False, "Впиши имя — по нему потом можно отключить доступ", None
        if str(request or "").strip():
            machine, dev_pub = self.parse_request(request)
            if not machine:
                return False, "Это не код запроса и не ID компьютера — оставь поле пустым, код привяжется сам", None
        else:
            machine, dev_pub = ANY_MACHINE, None
        try:
            seats = max(1, min(MAX_SEATS, int(float(seats or 1))))
        except (TypeError, ValueError):
            return False, "Мест — число", None
        if machine != ANY_MACHINE:
            seats = 1
        creds = {k: v for k, v in (creds or {}).items() if v}
        if share:
            if not dev_pub:
                return False, ("Чтобы вложить твой ключ API, нужен код запроса целиком (SZR1-…) — "
                               "друг копирует его в программе кнопкой «Копировать»"), None
            if not ((creds.get("id") and creds.get("secret")) or creds.get("token")):
                return False, "Сначала впиши свои Client ID и Client Secret в «Настройках»", None
        try:
            days = int(float(days or 0))
        except (TypeError, ValueError):
            return False, "Срок — число дней (0 — бессрочно)", None
        days = max(0, min(days, 3650))
        today = self.today()
        start = max(today, int(base_day or 0))     # продление: считаем от конца прошлого срока
        payload = {"n": name, "m": machine, "e": start + days if days else 0, "i": secrets.token_hex(3), "t": today}
        if seats > 1:
            payload["c"] = seats
        server = str(server or "").strip().rstrip("/")
        if server:   # куда подписчику ходить за находками
            payload["s"] = server
        if share:   # ключ API владельца — зашифрован для компьютера друга, в коде его не прочитать
            payload["k"] = seal_for(dev_pub, json.dumps(creds).encode("utf-8"), payload["i"].encode())
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        code = CODE_PREFIX + _b64e(data) + "." + _b64e(self.owner_key.sign(data))
        issued = self.issued()
        issued.insert(0, {"name": name, "machine": machine, "id": payload["i"], "expires": payload["e"],
                          "issued": today, "code": code, "shared": bool(share), "server": bool(server), "seats": seats})
        try:
            write_json(ISSUED_FILE, issued[:300])
        except OSError:
            pass
        self.state.add_log(f"Выдан код доступа: {name} ("
                           + (machine if machine != ANY_MACHINE else "без привязки" + (f", мест: {seats}" if seats > 1 else ""))
                           + "), "
                           + (f"до {day_text(payload['e'])}" if days else "бессрочно") + f", № {payload['i']}"
                           + (", с твоим ключом API" if share else ""))
        return True, "Код создан — отправь его подписчику", code

    def _save_issued(self, issued):
        try:
            write_json(ISSUED_FILE, issued[:300])
        except OSError:
            pass

    def set_blocked(self, code_id, blocked):
        """Отключить (или включить обратно) подписчика: сервер сразу перестаёт отдавать ему находки."""
        if not self.is_owner():
            return False, "Только владелец"
        issued, found = self.issued(), None
        for d in issued:
            if d.get("id") == code_id:
                d["blocked"] = bool(blocked)
                found = d
        if not found:
            return False, "Код не найден"
        self._save_issued(issued)
        self.state.add_log(f"{'Отключил' if blocked else 'Включил'} подписчика: {found['name']} (№ {code_id})")
        return True, ("Отключён — сервер больше не отдаёт ему находки" if blocked else "Снова включён")

    def renew(self, code_id, days, server=None):
        """Продлить подписку: новый код на тот же компьютер, срок — от конца прошлого."""
        old = next((d for d in self.issued() if d.get("id") == code_id), None)
        if not old:
            return False, "Код не найден", None
        anyone = old.get("machine") == ANY_MACHINE
        ok, msg, code = self.issue(old["name"], "" if anyone else old["machine"], days, server=server,
                                   base_day=old.get("expires") or 0, seats=old.get("seats") or 1)
        if ok and anyone:   # занятые места переходят на новый код
            new_id = self.parse(code)[0]["i"]
            with self.lock:
                seats = self._seats()
                if seats.get(code_id):
                    seats[new_id] = dict(seats[code_id])
                    self._save_seats(seats)
        if ok:
            issued = self.issued()
            for d in issued:
                if d.get("id") == code_id:
                    d["renewed"] = True
            self._save_issued(issued)
            msg = "Новый код скопирован — отправь его подписчику"
        return ok, msg, code

    def blocked_ids(self):
        return {str(d.get("id")) for d in self.issued() if d.get("blocked")}

    @staticmethod
    def _seats():
        try:
            with open(SEATS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _save_seats(seats):
        try:
            write_json(SEATS_FILE, seats)
        except OSError:
            pass

    def take_seat(self, payload, machine):
        """Код без привязки: компьютер занимает место при первом подключении. Ошибка — все места заняты."""
        machine = norm_machine(machine)
        if not machine:
            return "Нет ID компьютера — обнови программу"
        cid, limit = str(payload["i"]), max(1, int(payload.get("c") or 1))
        with self.lock:
            seats = self._seats()
            taken = seats.setdefault(cid, {})
            if machine in taken:
                return None
            if len(taken) >= limit:
                return (f"По этому коду уже подключены все компьютеры ({limit}) — попроси владельца освободить "
                        "место или выдать новый код")
            taken[machine] = time.time()
            self._save_seats(seats)
        self.state.add_log(f"Новый компьютер по коду «{payload['n']}» (№ {cid}): {machine}, мест занято "
                           f"{len(taken)} из {limit}")
        return None

    def free_seats(self, code_id):
        """Освободить места кода: компьютеры привяжутся заново при следующем подключении."""
        if not self.is_owner():
            return False, "Только владелец"
        with self.lock:
            seats = self._seats()
            n = len(seats.pop(str(code_id), {}) or {})
            self._save_seats(seats)
        return True, f"Освобождено мест: {n}"

    def shared_names(self):
        """Кому выданы действующие коды с ключом API владельца — они и делят с ним лимит."""
        today = self.today()
        names = [d.get("name") for d in self.issued()
                 if d.get("shared") and not d.get("renewed") and (not d.get("expires") or d["expires"] >= today)]
        return list(dict.fromkeys(n for n in names if n))

    def verify_subscriber(self, code, machine):
        """Для сервера: можно ли отдать находки по этому коду с этого компьютера. (данные кода, ошибка)."""
        payload, err = self.parse(code)
        if err:
            return None, err
        anyone = payload["m"] == ANY_MACHINE
        if not anyone and norm_machine(payload["m"]) != norm_machine(machine):
            return None, "Код выдан для другого компьютера"
        expires = int(payload.get("e") or 0)
        if expires and self.today() > expires:
            return None, f"Подписка закончилась {day_text(expires)} — продли у владельца"
        cid = str(payload["i"])
        with self.lock:
            revoked = str(payload["n"]).lower() in self.revoked or cid.lower() in self.revoked
        if revoked or cid in self.blocked_ids():
            return None, "Владелец отключил этот доступ"
        if anyone:
            err = self.take_seat(payload, machine)
            if err:
                return None, err
        return payload, None

    def server_url(self):
        """Адрес сервера владельца из своего кода доступа (подписчик) или None."""
        if self.is_owner():
            return None
        payload, err = self.parse(self.state.cfg.get("access_code", ""))
        if err or not payload.get("s"):
            return None
        url = str(payload["s"]).strip().rstrip("/")
        return url if re.match(r"^https?://[^\s/]+", url) else None

    @staticmethod
    def issued():
        try:
            with open(ISSUED_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    @staticmethod
    def parse(code):
        """(данные кода, ошибка). Проверяет только подпись владельца."""
        code = re.sub(r"\s+", "", str(code or ""))
        if not code:
            return None, "Нужен код доступа — его выдаёт владелец программы"
        if not code.startswith(CODE_PREFIX) or code.count(".") != 1:
            return None, "Это не код доступа — скопируй его целиком, он начинается с SZ1-"
        if Ed25519PublicKey is None:
            return None, "В программе нет модуля cryptography — код не проверить"
        body, sig = code[len(CODE_PREFIX):].split(".")
        try:
            data, sig = _b64d(body), _b64d(sig)
            Ed25519PublicKey.from_public_bytes(_b64d(OWNER_PUBLIC_KEY)).verify(sig, data)
            payload = json.loads(data.decode("utf-8"))
            if not isinstance(payload, dict) or not all(k in payload for k in ("n", "m", "e", "i")):
                raise ValueError
        except InvalidSignature:
            return None, "Код не подходит: его выдал не владелец программы или он повреждён"
        except (ValueError, TypeError, UnicodeDecodeError):
            return None, "Код повреждён — скопируй его ещё раз целиком"
        return payload, None

    def check(self, code=None):
        """Можно ли пользоваться программой. Возвращает словарь для интерфейса."""
        base = {"required": bool(OWNER_PUBLIC_KEY), "machine": self.machine, "owner": self.is_owner()}
        if not OWNER_PUBLIC_KEY:
            return dict(base, ok=True, mode="open")
        if base["owner"]:
            return dict(base, ok=True, mode="owner")
        code = self.state.cfg.get("access_code", "") if code is None else code
        payload, err = self.parse(code)
        if err:
            return dict(base, ok=False, mode="locked", reason=err)
        name, expires = str(payload["n"]), int(payload["e"] or 0)
        info = dict(base, name=name, expires=expires, expires_text=day_text(expires) if expires else "бессрочно",
                    code_id=str(payload["i"]))
        info["server"] = str(payload.get("s") or "")
        if payload["m"] != ANY_MACHINE and norm_machine(payload["m"]) != self.machine:
            return dict(info, ok=False, mode="locked",
                        reason="Этот код выдан для другого компьютера. Отправь владельцу свой ID — он выдаст новый")
        if expires and self.today() > expires:
            return dict(info, ok=False, mode="locked",
                        reason=f"Срок кода закончился {day_text(expires)} — попроси владельца продлить")
        with self.lock:
            revoked = name.lower() in self.revoked or str(payload["i"]).lower() in self.revoked
        if revoked:
            return dict(info, ok=False, mode="locked", reason="Владелец отозвал этот доступ")
        return dict(info, ok=True, mode="code")

    def snapshot(self):
        info = self.check()
        info["has_crypto"] = Ed25519PrivateKey is not None
        info["has_owner_key"] = bool(self.owner_key)
        info["owner_public"] = self.owner_public()
        info["embedded"] = bool(OWNER_PUBLIC_KEY)
        info["request"] = self.request_code() if X25519PrivateKey is not None else info["machine"]
        info["shared_api"] = bool(info["ok"] and info.get("mode") == "code" and self.shared_api())
        if info["owner"] and OWNER_PUBLIC_KEY:
            today, seen = self.today(), self.state.subscribers_seen()
            with self.lock:
                seats = self._seats()
            info["issued"] = [dict({k: v for k, v in d.items() if k != "code"},
                                   expires_text=day_text(d["expires"]) if d.get("expires") else "бессрочно",
                                   expired=bool(d.get("expires") and today > d["expires"]),
                                   last_seen=seen.get(d.get("id")), taken=len(seats.get(d.get("id"), {})))
                              for d in self.issued()[:100]]
        return info


def minutes_since(iso):
    try:
        return (datetime.now(timezone.utc) - eng.parse_time(iso)).total_seconds() / 60
    except (TypeError, ValueError):
        return None


# ------------------------------ Фоновая проверка ------------------------------
def api_delay(ages):
    """Через сколько минут новый лот виден в API: нижняя четверть возрастов лотов при первой встрече.
    Медиана врала: в неё попадали старые лоты, которые просто раньше не попадали в выдачу
    (по настоящей базе: новые лоты видны через ~10–12 мин, а медиана выходила под час)."""
    if not ages:
        return None
    ages = sorted(ages)
    return ages[(len(ages) - 1) // 4]


class Worker(threading.Thread):
    """Проверяет аукцион и передаёт находки в общее состояние через emit().
    Настройки меняются на ходу (reconfigure): пороги — сразу, список предметов — со следующего прохода.
    Перезапуск нужен только при смене ключей API (раньше любая галочка перезапускала проверку с нуля)."""

    def __init__(self, cfg, emit, api_factory=None, shown=(), tracked=(), holdings=(), serving=False, shared=None,
                 wants_fn=None):
        super().__init__(daemon=True)
        self.wants_fn = wants_fn or (lambda: (set(), set()))   # что ищут подписчики: (предметы, категории)
        self.cfg = cfg
        self.serving = serving             # владелец раздаёт находки подписчикам
        self.emit = emit
        self.stop_event = threading.Event()
        self.wake = threading.Event()      # новые настройки — не ждать конца паузы между проходами
        self._pending = None               # (настройки, serving) — применить со следующего прохода
        self._pending_lock = threading.Lock()
        self.api_factory = api_factory or make_api
        self.db = None
        self.initial_shown = set(shown)   # что уже есть в таблице (например, восстановлено после перезапуска)
        # находки-выкупы, за судьбой которых следим: пропал лот — купили его или сняли
        self.tracked = {t["lot_key"]: dict(t) for t in tracked}
        self.holdings = list(holdings)     # мои покупки: следим за их текущей ценой
        self.meta = {}
        # что уже писали в журнал за этот запуск программы (строки рынка и т. п.) — после перезапуска не повторяем
        self.shared = shared if shared is not None else {}
        self.price_queue = deque()         # предметы, чьи цены нужны калькулятору крафта (история без лотов)
        self.resale_factor = 1.0           # поправка оценки перепродажи по сверке прогнозов с фактом
        self._predicted = set()            # какие лоты уже записаны в сверку прогнозов
        self._undercut = {}                # покупка → самый дешёвый конкурент, о котором уже сообщили
        self._own_seen = set()             # покупки, чей выставленный лот трекер видел на аукционе

    def stop(self):
        self.stop_event.set()
        self.wake.set()

    def reconfigure(self, cfg, serving=None, wake=True):
        """Новые настройки без перезапуска: пороги и уведомления — сразу, что проверять — со следующего прохода
        (он начнётся сразу, если проверка ждала паузу между проходами)."""
        with self._pending_lock:
            self._pending = (dict(cfg), self.serving if serving is None else bool(serving))
            self.cfg = self._pending[0]
        if wake:
            self.wake.set()

    def _take_pending(self):
        with self._pending_lock:
            pending, self._pending = self._pending, None
        if pending:
            self.serving = pending[1]
        return pending is not None

    def _plan(self, names, wanted=None):
        """Что проверять и с какими порогами — по текущим настройкам: (предметы, авто, купленное, категории, пороги).
        Сервер для подписчиков ищет ещё и то, что выбрали они сами (их предметы и категории)."""
        cfg = self.cfg
        sub_items, sub_cats = wanted or (set(), set())
        own_cats = eng.auto_categories(cfg)
        cats_all = own_cats + [c for c in sorted(sub_cats) if c in eng.AUTO_CATEGORIES and c not in own_cats]
        items, auto = eng.watch_items(dict(cfg, auto_categories=cats_all, all_artifacts="artefact" in cats_all), names)
        have = {i for i, _ in items}
        for item_id in sorted(sub_items):
            if len(auto) >= SUB_ITEMS_MAX:
                break
            if item_id in names and item_id not in have:
                have.add(item_id)
                auto.add(item_id)
                items.append((item_id, names[item_id]))
        cats = cats_all
        have = {i for i, _ in items}
        hold_ids = set()
        for h in list(self.holdings):   # купленное тоже проверяем — чтобы видеть его текущую цену
            if h.get("item_id") in names and h["item_id"] not in have:
                have.add(h["item_id"])
                hold_ids.add(h["item_id"])
                items.append((h["item_id"], names[h["item_id"]]))
        scan_cfg = dict(cfg)
        if cfg.get("rare_enabled", True):   # редкие ищем со своим (обычно меньшим) порогом прибыли
            scan_cfg["find_min_profit"] = min(cfg["min_profit"], float(cfg.get("rare_min_profit", cfg["min_profit"])))
        # ищем чуть шире своих порогов: что не прошло, видно в «почти находках» — с причиной.
        # Запросов к API это не добавляет: те же лоты, просто другой порог при подсчёте.
        scan_cfg["discount"] = min(float(cfg["discount"]), NEAR_DISCOUNT)
        scan_cfg["find_min_profit"] = min(float(scan_cfg.get("find_min_profit", cfg["min_profit"])), NEAR_MIN_PROFIT)
        if self.serving:   # для подписчиков ищем ещё шире — у каждого свои пороги, отсеют у себя
            scan_cfg["min_profit"] = min(float(cfg["min_profit"]), 1000.0)
            scan_cfg["find_min_profit"] = min(scan_cfg["find_min_profit"], 1000.0)
        scan_cfg["resale_factor"] = self.resale_factor if cfg.get("calibrate", True) else 1.0
        return items, auto, hold_ids, cats, scan_cfg

    def telegram(self, text):
        ok, msg = send_telegram(self.cfg, text)
        if not ok and msg:
            self.emit("log", msg)

    def predict(self, rec, kind):
        """Запомнить оценку находки — через сутки сверим её с тем, за сколько такие лоты продавали."""
        if self.db is None or rec.get("lot_key") in self._predicted:
            return
        self._predicted.add(rec["lot_key"])
        try:
            self.db.record_predictions([(self.cfg["region"], rec["item_id"], rec["lot_key"], time.time(),
                                         rec["quality"] if rec.get("exact") and rec.get("quality") is not None else -1,
                                         rec["ptn"] if rec.get("exact") and rec.get("ptn") is not None else -1,
                                         int(rec["amount"]), float(rec["unit"]), float(rec.get("market_raw") or rec["market"]),
                                         float(rec.get("hist") or 0), rec.get("chance"), kind)])
        except Exception:
            pass

    def check_accuracy(self, db):
        """Сверка прогнозов: показать в окне и вернуть поправку оценки перепродажи (или None — не по чему)."""
        try:
            acc = db.accuracy(self.cfg["region"])
        except Exception:
            return None
        factor = eng.calibration_factor(acc)
        old, self.resale_factor = self.resale_factor, factor
        info = None
        if acc:
            names = {i: e.get("name", i) for i, e in self.meta.items()}
            rows = sorted(acc["rows"], key=lambda r: r[4], reverse=True)[:8]
            info = {"n": acc["n"], "ratio": acc["ratio"], "hit": acc["hit"], "factor": factor,
                    "by_kind": {k: list(v) for k, v in acc["by_kind"].items()},
                    "rows": [{"item_id": i, "name": names.get(i, i), "kind": k, "pred": p, "fact": f, "ts": t}
                             for i, k, p, f, t in rows], "at": time.time()}
        self.emit("accuracy", info)
        if acc and abs(factor - old) >= 0.01 and self.cfg.get("calibrate", True):
            if factor < 1:
                self.emit("log", f"Сверка прогнозов: по {acc['n']} находкам такие лоты продавали в среднем за "
                                 f"{acc['ratio'] * 100:.0f}% от оценки — снижаю оценку перепродажи на "
                                 f"{(1 - factor) * 100:.0f}%")
            else:
                self.emit("log", f"Сверка прогнозов: оценки сбываются (по {acc['n']} находкам) — поправка не нужна")
        return factor

    def fetch_prices(self, api, db, limit):
        """История сделок для калькулятора крафта — по нескольку предметов за проход."""
        region = self.cfg["region"]
        for _ in range(min(limit, len(self.price_queue))):
            item_id = self.price_queue.popleft()
            try:
                stop = db.stop_point(region, item_id, eng.LONG_DAYS * 24)
                records, how = api.history_since(region, item_id, stop, max_pages=2)
                db.store(region, item_id, records, how)
            except eng.AuthError:
                raise
            except Exception as e:
                if not (isinstance(e, eng.ApiError) and e.status in (400, 404)):
                    self.price_queue.append(item_id)   # сеть подвела — попробуем позже
            self.emit("craft_progress", {"left": len(self.price_queue)})

    def run(self):
        cfg = self.cfg
        try:
            api = self.api_factory(cfg)
            names = eng.load_listing(cfg["region"])
            try:
                self.meta = {e["id"]: e for e in eng.load_catalog(cfg["region"])}
            except Exception:
                self.meta = {}
            self._take_pending()   # что поменяли, пока запускались, уже в self.cfg
            items, auto, hold_ids, cats, scan_cfg = self._plan(names, self.wants_fn() if self.serving else None)
            if not items:
                self.emit("error", "Список предметов пуст или названия не найдены — проверь вкладку «Предметы».")
                return
            seen = eng.load_seen()   # о каких лотах уже сообщали (звук, Telegram) — в прошлых запусках тоже
            shown = set(self.initial_shown)  # что уже есть в таблице — второй раз не добавляем
            known = set()
            db = eng.MarketDB(keep_days=cfg.get("history_keep_days", 14))  # своя база сделок, market.db
            self.db = db
            self.emit("log", eng.db_line(db.stats()))
            # рынок, формат цен, строка рынка в журнале; автодобавленные предметы — без строки на каждый
            scanner = eng.Scanner(api, scan_cfg, quiet=auto | hold_ids, db=db)
            for attr in ("described", "mismatched", "fields_logged"):   # раз за запуск программы, а не проверки
                setattr(scanner, attr, self.shared.setdefault(attr, set()))
            first_pass, announce, last_line = True, True, None
            heat, heat_at, acc_at = {}, 0.0, 0.0
            wanted_sig = None
            while not self.stop_event.is_set():
                wanted = self.wants_fn() if self.serving else (set(), set())
                sig = (frozenset(wanted[0]), frozenset(wanted[1]))
                if self._take_pending() or (sig != wanted_sig and wanted_sig is not None):
                    items, auto, hold_ids, cats, scan_cfg = self._plan(names, wanted)
                    scanner.cfg, scanner.quiet = scan_cfg, auto | hold_ids
                    announce = True
                wanted_sig = sig
                if announce:
                    announce = False
                    scanner.quiet_label = "Все артефакты" if cats == ["artefact"] else "Категории целиком"
                    line = (eng.watching_line([x for x in items if x[0] not in hold_ids], auto, cats) if items else
                            "Список предметов пуст — добавь предметы во вкладке «Предметы», проверка продолжится сама")
                    if self.serving:
                        line += ". Сервер для подписчиков: ищу шире (от 8% и 1 000 ₽), у себя показываю по своим порогам"
                    if line != last_line:
                        self.emit("log", line)
                        last_line = line
                if not items:
                    self.wake.wait()
                    self.wake.clear()
                    continue
                started = time.time()
                fresh_ages, found = [], [0]
                if started - acc_at > 1800:   # сверка прогнозов с фактом — раз в полчаса
                    acc_at = started
                    factor = self.check_accuracy(db)
                    if (factor is not None and self.cfg.get("calibrate", True)
                            and abs(factor - scanner.cfg.get("resale_factor", 1.0)) > 1e-9):
                        scanner.cfg = dict(scanner.cfg, resale_factor=factor)
                if self.price_queue:          # цены для калькулятора крафта — понемногу, не мешая поиску
                    self.fetch_prices(api, db, CRAFT_PER_PASS)
                if started - heat_at > 600:   # где чаще появляются новые лоты — раз в 10 минут
                    try:
                        heat, heat_at = db.new_lot_rates(cfg["region"]), started
                    except Exception:
                        heat, heat_at = {}, started
                order = eng.pass_order(items, heat)

                def on_progress(i, item_id, name):
                    self.emit("progress", {"text": f"Проверяю {name}", "done": i, "total": len(order)})

                def on_item(item_id, name, result):
                    if isinstance(result, Exception):  # один сбойный предмет не останавливает проход
                        self.emit("log", f"{name}: ошибка — {result}")
                        return
                    lots, deals, bids = result
                    cfg = self.cfg                      # настройки могли поменять на ходу
                    cap = scanner.last_cap.get(item_id, math.inf)   # ниже этой цены видны все лоты
                    if lots is not None:  # лоты получили — отметим находки, которых больше нет
                        self.emit("lots_seen", {"item_id": item_id, "keys": list(lots.keys()),
                                                "cap": None if cap == math.inf else cap})
                        self.check_gone(item_id, lots, cap)
                        if item_id in hold_ids or any(h.get("item_id") == item_id for h in list(self.holdings)):
                            self.update_holdings(scanner, item_id, name, list(lots.values()))
                    # замер задержки API: только лоты дешевле cap — среди них видны все (дороже старые лоты
                    # «въезжают» на страницу, когда дешёвые раскупают, и выглядят новыми)
                    for key, lot in (lots or {}).items():
                        if key not in known:
                            known.add(key)
                            age = minutes_since(lot.get("startTime"))
                            if (not first_pass and age is not None and 0 <= age <= 120
                                    and 0 < eng._num(lot.get("buyoutPrice")) < cap):
                                fresh_ages.append(age)
                    # в таблицу — всё найденное в этом запуске; звук и Telegram — только о новом
                    meta = self.meta.get(item_id) or {}
                    for kind, items_found in (("buyout", deals), ("bid", bids)):
                        for d in items_found:
                            g = d.get("grade") or d.get("bucket")
                            rare = is_rare(cfg, item_id, name, meta, g[0] if g else None)
                            key = ("bid|" if kind == "bid" else "") + eng.lot_key(item_id, d["lot"])
                            rec, text = self.record(item_id, name, d, kind, key, meta)
                            if self.serving:
                                self.emit("feed", rec)
                            if not meets_thresholds(rec, cfg, rare):
                                # нашлось по более низкому порогу — в находки не берём, но показываем,
                                # что отсеяно и почему: «0 находок» не должно быть загадкой
                                if is_near(rec):
                                    self.emit("near", dict(rec, rare=bool(rare), why=near_reason(rec, cfg, rare)))
                                    self.predict(rec, "near")
                                continue
                            if kind == "buyout":
                                self.predict(rec, "deal")
                            if key not in shown:
                                shown.add(key)
                                found[0] += 1
                                self.publish(rec, text, notify=key not in seen, rare=rare)
                                seen.add(key)

                # сеть — параллельно, обработка — по порядку (см. eng.scan_pass)
                eng.scan_pass(scanner, order, on_item, self.stop_event.is_set, on_progress)
                eng.save_seen(seen)
                if first_pass and not self.stop_event.is_set() and scanner.summary():
                    self.emit("log", scanner.summary())
                self.emit("pass", {"time": time.time(), "found": found[0], "took": time.time() - started,
                                   "key_others": getattr(api, "others_last", None), "key_limit": getattr(api, "key_limit", None),
                                   "keys": len(api.alive()) if hasattr(api, "alive") else 1,
                                   "keys_total": len(getattr(api, "members", [api])),
                                   "delay": api_delay(fresh_ages),
                                   "delay_min": min(fresh_ages) if fresh_ages else None,
                                   "delay_n": len(fresh_ages),
                                   "total": len(items), "db": db.stats()})
                first_pass = False
                pause = max(0.5, float(self.cfg["poll_minutes"]) * 60 - (time.time() - started))
                self.wake.wait(pause)
                self.wake.clear()
        except eng.AuthError as e:
            if cfg.get("shared_api"):
                self.emit("error", "Ключ API владельца не подошёл — возможно, он сменил ключ. "
                                   "Попроси у владельца новый код доступа (или впиши свои ключи в «Настройках»).")
            else:
                self.emit("error", str(e))
        except Exception as e:
            self.emit("error", f"Не удалось запустить: {e}")
        finally:
            if self.db is not None:
                self.db.close()
            self.emit("stopped", None)

    def check_gone(self, item_id, lots, cap=math.inf):
        """Находка пропала с аукциона: есть такая сделка в истории — лот купили, нет 2 часа — сняли.
        cap — ниже какой цены видны все лоты: дороже лот мог просто не попасть на страницу."""
        now = time.time()
        for lot_key, t in list(self.tracked.items()):
            if t["item_id"] != item_id:
                continue
            if lot_key in lots or float(t.get("price") or 0) >= cap:
                t.pop("gone_at", None)
                continue
            t.setdefault("gone_at", now)
            status = None
            if self.db is not None and self.db.find_sale(self.cfg["region"], item_id, t["amount"], t["price"],
                                                         t.get("since", 0) - 60):
                status = "sold"
            elif t.get("ends") and t["ends"] <= now:
                status = "expired"
            elif now - t["gone_at"] > 2 * 3600:
                status = "removed"
            if status:
                self.emit("lot_status", {"lot_key": lot_key, "status": status})
                del self.tracked[lot_key]

    def update_holdings(self, scanner, item_id, name, lot_list):
        """Купленное: текущая цена и шанс продажи, за сколько выставить, перебили ли твой лот, продан ли он."""
        cached = scanner.market_cache.get(item_id)
        market = cached[1] if cached else None
        if not market:
            return
        total = scanner.fmt.total("lots", lot_list, "buyoutPrice", name)
        cap = scanner.last_cap.get(item_id, math.inf)
        for h in list(self.holdings):
            if h.get("item_id") != item_id or h.get("status") == "sold":
                continue
            add = h.get("additional") or {}
            amount = int(h.get("amount", 1) or 1)
            listed = h.get("status") == "listed" and float(h.get("list_price") or 0) > 0
            state = eng.listing_state(lot_list, amount, float(h["list_price"]), add, total) if listed else None
            others = lot_list
            if state and state["own"]:   # свой лот — не конкурент самому себе
                self._own_seen.add(h["id"])
                own_total = float(h["list_price"])
                skip = [True]
                def not_own(lot, skip=skip):
                    a, raw = int(eng._num(lot.get("amount"))), eng._num(lot.get("buyoutPrice"))
                    if skip[0] and a == amount and abs((raw if total else raw * a) - own_total) < 1 \
                            and eng.grade_of(lot.get("additional")) == eng.grade_of(add):
                        skip[0] = False
                        return False
                    return True
                others = [lot for lot in lot_list if not_own(lot)]
            if listed and state and not state["own"] and h["id"] in self._own_seen \
                    and float(h["list_price"]) / amount < cap and self.db is not None \
                    and self.db.find_sale(self.cfg["region"], item_id, amount, float(h["list_price"]),
                                          float(h.get("listed_at") or 0) - 60):
                self._own_seen.discard(h["id"])     # лот пропал, и в истории есть сделка ровно на него — продан
                h["status"] = "sold"
                self.emit("holding_sold", {"id": h["id"], "price": float(h["list_price"])})
                continue
            found = eng.market_for(market, add)
            if not found:
                self.emit("holding", {"id": h["id"], "market": None, "updated": time.time(), "list_state": state})
                continue
            hist = found[0][0]
            fake = {"amount": amount, "buyoutPrice": 0, "additional": add}
            resale, floor = eng.resale_price(fake, others, hist, total)
            pairs = eng.deal_pairs(market, add)
            chance = eng.sale_chance(resale, amount, pairs[0], pairs[1],
                                     eng.competitors(fake, others, resale, total),
                                     supply=eng.competitors(fake, others, resale, total, spread=0.3),
                                     rates=scanner.rates_for(item_id, resale, hist)) if pairs else None
            options = eng.price_options(hist, amount, pairs[0], pairs[1], others, add, total,
                                        paid=float(h.get("paid") or 0), fee=self.cfg["fee"],
                                        rates_fn=lambda p, hist=hist: scanner.rates_for(item_id, p, hist)) if pairs else []
            self.emit("holding", {"id": h["id"], "market": resale, "hist": hist, "floor": floor,
                                  "chance": chance, "options": options, "list_state": state, "updated": time.time()})
            if state and state["cheaper"]:
                self.undercut_alert(h, name, state)
            else:
                self._undercut.pop(h["id"], None)

    def undercut_alert(self, h, name, state):
        """Твой лот перебили — сообщить, если появился лот дешевле прежнего (не чаще, чем цена падает)."""
        best = state["best"]
        said = self._undercut.get(h["id"])
        if said is not None and best >= said - 0.5:
            return
        self._undercut[h["id"]] = best
        amount = int(h.get("amount", 1) or 1)
        mine = float(h["list_price"]) / amount
        text = (f"⚠ Твой лот перебили: {name}\nУ тебя {eng.fmt_rub(mine)}/шт, появился лот за "
                f"{eng.fmt_rub(best)}/шт" + (f" (дешевле тебя — {state['cheaper']})" if state["cheaper"] > 1 else "")
                + (f"\nЧтобы продать первым, выставь за {eng.fmt_rub(state['suggest'])}/шт" if state.get("suggest") else ""))
        self.emit("log", text.replace("\n", ". ").replace("⚠ ", ""))
        self.emit("undercut", {"id": h["id"], "best": best, "suggest": state.get("suggest")})
        if self.cfg.get("alerts", True):
            self.telegram(text)

    def record(self, item_id, name, d, kind, key, meta=None):
        """Находка в том виде, в каком она уходит в таблицу и подписчикам. (запись, текст для Telegram)."""
        lot = d["lot"]
        b = d["bucket"]
        meta = meta or {}
        if kind == "bid":
            unit, profit = d["need"] / d["amount"], d["profit_now"]
            text = eng.bid_message(name, d, self.cfg["min_profit"])
        else:
            unit, profit = d["unit"], d["profit"]
            text = eng.deal_message(name, d)
        chance = d.get("chance")
        if chance:
            text = text.rstrip() + "\n" + chance_text(chance)
        cost = unit * d["amount"]
        grade = d.get("grade")
        if kind == "buyout":
            try:
                since = eng.parse_time(lot.get("startTime")).timestamp()
            except (TypeError, ValueError):
                since = time.time() - 86400
            try:
                ends = eng.parse_time(lot.get("endTime")).timestamp()
            except (TypeError, ValueError):
                ends = None
            self.tracked[eng.lot_key(item_id, lot)] = {
                "lot_key": eng.lot_key(item_id, lot), "item_id": item_id, "amount": d["amount"],
                "price": eng._num(lot.get("buyoutPrice")), "since": since, "ends": ends}
        max_bid = d.get("max_bid")
        if kind == "bid":   # «ставь не выше» — по своей минимальной прибыли
            max_bid = d["market"] * (1 - self.cfg["fee"]) * d["amount"] - self.cfg["min_profit"]
        rec = {
            "item_id": item_id, "name": name, "kind": kind,
            "key": key, "lot_key": eng.lot_key(item_id, lot), "gone": False,
            "cat": meta.get("cat"), "rank": meta.get("rank"),
            "additional": {k: v for k, v in (lot.get("additional") or {}).items() if k in ("qlt", "ptn")},
            "chance": chance["chance"] if chance else None, "sell_hours": chance.get("hours") if chance else None,
            "exp_profit": profit * chance["chance"] if chance else None,     # прибыль × шанс продать за сутки
            "market_raw": d.get("market_raw", d["market"]),                  # оценка до поправки по сверке
            "chance_info": chance,
            "quality": (grade or b or (None, None))[0], "ptn": (grade or b or (None, None))[1],
            "exact": bool(grade),
            "hist": d.get("hist", d["market"]), "floor": d.get("floor"),
            "window_h": d.get("window_h"), "trend": d.get("trend"),
            "stale": eng.stale_note(d) if kind == "buyout" else "",
            "amount": d["amount"], "unit": unit, "cost": cost, "market": d["market"],
            "resale": d["market"] * d["amount"], "profit": profit,
            "roi": profit / cost * 100 if cost else 0,
            "pct": (1 - unit / d["market"]) * 100 if d["market"] else 0,
            "n_sales": d["n"], "per_day": d["per_day"],
            "speed": eng.sell_speed(d["amount"], d["per_day"]),
            "listed": lot.get("startTime"), "ends": lot.get("endTime"),
            "max_bid": max_bid, "has_bids": d.get("has_bids"),
        }
        return rec, text

    def publish(self, rec, text, notify=True, rare=False):
        """В свою таблицу; звук и Telegram — только о новом (и с подходящим шансом продажи)."""
        if rare:
            text = "💎 ОСОБО РЕДКИЙ\n" + text
        chance = rec.get("chance_info")
        min_chance = float(self.cfg.get("notify_min_chance", 0) or 0) / 100
        if notify and not rare and chance and chance["chance"] < min_chance:
            notify = False
        self.emit("deal", dict(rec, rare=bool(rare), text=text, notify=notify))
        if notify:
            self.telegram(text)

    def deal(self, item_id, name, d, kind, key, notify=True, rare=False, meta=None):
        """Совместимость: собрать запись и показать."""
        rec, text = self.record(item_id, name, d, kind, key, meta)
        self.publish(rec, text, notify=notify, rare=rare)


class FeedWorker(threading.Thread):
    """Подписчик: находки не ищет сам, а берёт у сервера владельца и отбирает по своим настройкам."""

    def __init__(self, cfg, emit, url, code, machine, shown=(), holdings=()):
        super().__init__(daemon=True)
        self.cfg, self.emit, self.url = cfg, emit, url.rstrip("/")
        self.code, self.machine = code, machine
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self._pending_lock = threading.Lock()
        self._changed = False
        self.initial_shown = set(shown)
        self.holdings = list(holdings)
        self.db = None

    def stop(self):
        self.stop_event.set()
        self.wake.set()

    def reconfigure(self, cfg, serving=None, wake=True):
        """Новые пороги и список — со следующего запроса к серверу (он будет сразу), без перезапуска."""
        with self._pending_lock:
            self.cfg = dict(cfg)
            self._changed = True
        if wake:
            self.wake.set()

    def _sleep(self, seconds):
        self.wake.wait(seconds)
        self.wake.clear()

    def run(self):
        cfg = self.cfg
        try:
            names = eng.load_listing(cfg["region"])
            try:
                meta = {e["id"]: e for e in eng.load_catalog(cfg["region"])}
            except Exception:
                meta = {}
            watch_ids = {i for i, _ in eng.resolve_watch(cfg.get("watch") or [], names)}
            cats = set(eng.auto_categories(cfg))
            seen, shown = eng.load_seen(), set(self.initial_shown)
            etag, fails, first, quiet_next = None, 0, True, False
            self.emit("log", f"Подписка: находки беру с сервера владельца ({self.url}). "
                             + ("Отбираю по твоему списку и категориям" if watch_ids or cats else "Показываю все находки")
                             + " и по твоим порогам.")
            while not self.stop_event.is_set():
                with self._pending_lock:
                    changed, self._changed = self._changed, False
                if changed:   # настройки поменяли — перечитать всю ленту по новым, старое — без звука
                    cfg = self.cfg
                    watch_ids = {i for i, _ in eng.resolve_watch(cfg.get("watch") or [], names)}
                    cats = set(eng.auto_categories(cfg))
                    etag, quiet_next = None, True
                started = time.time()
                headers = {"X-Access-Code": self.code, "X-Machine": self.machine, "X-App-Version": APP_VERSION,
                           "Accept-Encoding": "gzip", "X-Want": self.want_header(cfg, watch_ids, cats)}
                if etag:
                    headers["If-None-Match"] = etag
                wait = FEED_POLL
                try:
                    r = requests.get(self.url + "/v1/feed", headers=headers, timeout=25)
                except requests.RequestException as e:
                    fails += 1
                    self.emit("server", {"ok": False, "error": f"сервер владельца не отвечает ({type(e).__name__})"})
                    if fails == 1:
                        self.emit("log", "Сервер владельца не отвечает — возможно, его компьютер выключен. Повторяю…")
                    self._sleep(min(300, FEED_POLL * 2 ** min(fails, 3)))
                    continue
                if r.status_code in (401, 403):
                    try:
                        why = r.json().get("error") or ""
                    except ValueError:
                        why = ""
                    self.emit("server", {"ok": False, "error": why or f"сервер отказал ({r.status_code})"})
                    self.emit("error", "Сервер владельца не пускает: " + (why or str(r.status_code)))
                    self._sleep(300)
                    continue
                if r.status_code == 429:
                    try:
                        wait = max(5, int(r.headers.get("Retry-After", "15")))
                    except ValueError:
                        wait = 15
                elif r.status_code == 304:
                    fails = 0
                    self.emit("server", {"ok": True, "checked": time.time()})
                    self.emit("pass", {"time": time.time(), "found": 0, "took": time.time() - started,
                                       "delay": None, "total": None})
                elif r.status_code == 200:
                    fails = 0
                    try:
                        data = r.json()
                    except ValueError:
                        data = None
                    if isinstance(data, dict):
                        etag = r.headers.get("ETag")
                        found = self.process(data, cfg, meta, watch_ids, cats, seen, shown, quiet=first or quiet_next)
                        first = quiet_next = False
                        eng.save_seen(seen)
                        self.emit("server", {"ok": True, "checked": time.time(), "server_pass": data.get("last_pass"),
                                             "items": data.get("items"), "version": data.get("server_version")})
                        self.emit("pass", {"time": time.time(), "found": found, "took": time.time() - started,
                                           "delay": None, "total": data.get("items")})
                else:
                    self.emit("server", {"ok": False, "error": f"сервер ответил {r.status_code}"})
                self._sleep(max(1, wait - (time.time() - started)))
        except Exception as e:
            self.emit("error", f"Не удалось подключиться к серверу: {e}")
        finally:
            self.emit("stopped", None)

    @staticmethod
    def want_header(cfg, watch_ids, cats):
        """Что я ищу — серверу: он проверит и мои предметы и будет отдавать мне находки по очереди с другими."""
        want = {"w": sorted(watch_ids)[:400], "c": sorted(cats)[:20], "mp": float(cfg.get("min_profit") or 0),
                "d": float(cfg.get("discount") or 0.15), "re": bool(cfg.get("rare_enabled", True)),
                "rq": int(cfg.get("rare_quality", 4)), "rp": float(cfg.get("rare_min_profit", 5000))}
        return _b64e(json.dumps(want, separators=(",", ":")).encode("utf-8"))

    def process(self, data, cfg, meta, watch_ids, cats, seen, shown, quiet=False):
        present, fates, found = set(), {}, 0
        for rec in data.get("deals") or []:
            if not isinstance(rec, dict) or not rec.get("key") or not rec.get("lot_key"):
                continue
            present.add(rec["lot_key"])
            if rec.get("gone") or rec.get("fate"):
                fates[rec["lot_key"]] = rec.get("fate") or ""
                continue
            item = rec.get("item_id")
            if (watch_ids or cats) and item not in watch_ids and rec.get("cat") not in cats:
                continue   # не из моего списка и не из моих категорий
            rare = is_rare(cfg, item, rec.get("name", ""), meta.get(item), rec.get("quality"))
            if not meets_thresholds(rec, cfg, rare):
                if is_near(rec):
                    near = {k: v for k, v in rec.items() if k not in ("found", "id", "notify", "text")}
                    self.emit("near", dict(near, rare=bool(rare), why=near_reason(rec, cfg, rare), source="server"))
                continue
            key = rec["key"]
            self.update_holding_price(rec)
            if key in shown:
                continue
            shown.add(key)
            found += 1
            out = {k: v for k, v in rec.items() if k not in ("found", "id", "notify", "text")}
            out["rare"], out["source"] = bool(rare), "server"
            if out.get("kind") == "bid":
                out["max_bid"] = out["market"] * (1 - cfg["fee"]) * out["amount"] - cfg["min_profit"]
            notify = key not in seen and not quiet
            chance = out.get("chance_info")
            if notify and not rare and chance and chance["chance"] < float(cfg.get("notify_min_chance", 0) or 0) / 100:
                notify = False
            seen.add(key)
            text = feed_text(out, cfg)
            self.emit("deal", dict(out, text=text, notify=notify))
            if notify:
                ok, msg = send_telegram(cfg, text)
                if not ok and msg:
                    self.emit("log", msg)
        self.emit("feed_sync", {"present": sorted(present), "fates": fates})
        return found

    def update_holding_price(self, rec):
        """Текущая цена купленного — по находкам того же предмета с сервера."""
        for h in self.holdings:
            if h.get("item_id") != rec.get("item_id") or h.get("status") == "sold":
                continue
            if h.get("quality") != rec.get("quality"):
                continue
            self.emit("holding", {"id": h["id"], "market": rec.get("market"), "hist": rec.get("hist"),
                                  "floor": rec.get("floor"), "chance": rec.get("chance_info"), "updated": time.time()})


def make_feed_handler(state):
    """Сервер для подписчиков: только /v1/ping и /v1/feed. Слушает 127.0.0.1 — наружу его выводит Tailscale Funnel."""

    class FeedHandler(BaseHTTPRequestHandler):
        server_version = "STALZONE-Feed"
        sys_version = ""

        def log_message(self, *args):
            pass

        def _send(self, code, body=b"", headers=None):
            self.send_response(code)
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if body and self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, code, obj, headers=None):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                       dict({"Content-Type": "application/json; charset=utf-8"}, **(headers or {})))

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/v1/ping":
                return self._json(200, {"ok": True, "app": "stalzone-tracker", "version": APP_VERSION,
                                        "time": time.time()})
            if path != "/v1/feed":
                return self._json(404, {"error": "not found"})
            code = str(self.headers.get("X-Access-Code") or "")[:4000]
            machine = str(self.headers.get("X-Machine") or "")[:40]
            payload, err = state.access.verify_subscriber(code, machine)
            if err:
                return self._json(403, {"error": err})
            cid, now = str(payload["i"]), time.time()
            skey = cid if payload["m"] != ANY_MACHINE else f"{cid}:{norm_machine(machine)}"   # у кода на группу — по компьютерам
            want = None
            raw = str(self.headers.get("X-Want") or "")[:16000]
            if raw:     # что подписчик ищет сам: предметы, категории, пороги
                try:
                    want = json.loads(_b64d(raw).decode("utf-8"))
                    want = want if isinstance(want, dict) else None
                except (ValueError, UnicodeDecodeError):
                    want = None
            first = False
            with state.lock:
                sub = state.subscribers.get(skey)
                if sub and now - sub["last"] < FEED_MIN_INTERVAL:
                    too_fast = True
                else:
                    too_fast = False
                    first = sub is None
                    state.subscribers[skey] = {
                        "want": want if want is not None else (sub or {}).get("want"),
                        "given": (sub or {}).get("given") or [],
                        "cid": cid, "name": payload["n"], "machine": norm_machine(machine) or payload["m"], "last": now,
                        "requests": (sub or {}).get("requests", 0) + 1,
                        "version": str(self.headers.get("X-App-Version") or "")[:20],
                        "ip": str(self.headers.get("X-Forwarded-For") or self.client_address[0])[:60]}
            if too_fast:
                return self._json(429, {"error": "слишком часто"}, {"Retry-After": str(FEED_MIN_INTERVAL)})
            if first:
                state.add_log(f"Подписчик подключился: {payload['n']} (№ {cid})")
            rev, body, gz = state.feed_bytes(skey)
            etag = f'"{rev}"'
            if self.headers.get("If-None-Match") == etag:
                return self._send(304, b"", {"ETag": etag})
            headers = {"Content-Type": "application/json; charset=utf-8", "ETag": etag}
            if "gzip" in str(self.headers.get("Accept-Encoding") or ""):
                headers["Content-Encoding"] = "gzip"
                return self._send(200, gz, headers)
            return self._send(200, body, headers)

        def do_HEAD(self):
            return self._send(405)

        do_POST = do_PUT = do_DELETE = do_HEAD

    return FeedHandler


# --------------------------------- Состояние ---------------------------------
AUTOSTART_NAME = "STALZONE Tracker"
TAILSCALE_PATHS = (r"C:\Program Files\Tailscale\tailscale.exe", r"C:\Program Files (x86)\Tailscale\tailscale.exe",
                   "/usr/bin/tailscale", "/usr/local/bin/tailscale", "/Applications/Tailscale.app/Contents/MacOS/Tailscale")
TAILSCALE_DOWNLOAD = "https://tailscale.com/download"


def tailscale_exe():
    """Где программа tailscale (её ставит обычный установщик Tailscale). None — не установлена."""
    found = shutil.which("tailscale")
    if found:
        return found
    return next((p for p in TAILSCALE_PATHS if os.path.exists(p)), None)


def _run_quiet(args, timeout):
    """Запустить команду без чёрного окна: (код, вывод). Код None — не дождались (вывод — что успела написать)."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, creationflags=flags,
                           encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        out = e.stdout or b""
        err = e.stderr or b""
        dec = lambda x: x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")
        return None, dec(out) + dec(err)
    except OSError as e:
        return 1, str(e)


def funnel_open(port, exe=None, run=None):
    """Открыть сервер для подписчиков в интернет через Tailscale Funnel — одной кнопкой.
    (ok, адрес или что сделать, ссылка, которую надо открыть, или None)."""
    run = run or _run_quiet
    exe = exe or tailscale_exe()
    if not exe:
        return False, "Tailscale не установлен. Скачай его (бесплатно), установи и войди через Google или Microsoft — потом нажми ещё раз.", TAILSCALE_DOWNLOAD
    code, out = run([exe, "status", "--json"], 15)
    try:
        info = json.loads(out[out.index("{"):]) if "{" in out else {}
    except ValueError:
        info = {}
    state = str(info.get("BackendState") or "")
    if state in ("NeedsLogin", "NoState", "Stopped") or (code not in (0, None) and not info):
        return False, "Tailscale установлен, но не вошёл в аккаунт: открой Tailscale (значок у часов) и войди — потом нажми ещё раз.", None
    dns = str((info.get("Self") or {}).get("DNSName") or "").rstrip(".")
    code, out = run([exe, "funnel", "--bg", str(int(port))], 40)
    link = re.search(r"https://login\.tailscale\.com/\S+", out)
    if link and (code != 0 or "not enabled" in out.lower()):
        return False, "Tailscale просит разрешить Funnel: открой ссылку, нажми «Enable» — и нажми эту кнопку ещё раз.", link.group(0)
    found = re.search(r"https://[A-Za-z0-9.-]+\.ts\.net", out)
    url = found.group(0) if found else (f"https://{dns}" if dns.endswith(".ts.net") else "")
    if code == 0 and url:
        return True, url, None
    tail = " ".join(out.split())[:300]
    return False, f"Tailscale не открыл доступ{': ' + tail if tail else ''}", None


def keep_awake():
    """Windows: сбросить таймер сна — пока поиск идёт, компьютер не уснёт (экран гаснуть может).
    Действует до следующего ухода в сон по таймеру, поэтому вызываем каждые 30 секунд."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x00000001)   # ES_SYSTEM_REQUIRED
    except Exception:
        pass


def set_autostart(on):
    """Запуск вместе с Windows — строка в HKCU\\...\\Run. Только у программы-.exe. (ok, текст ошибки)."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False, "Автозапуск работает только у программы .exe (при запуске из исходников — нет)"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                            winreg.KEY_SET_VALUE) as key:
            if on:
                winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, f'"{sys.executable}" --autostart')
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_NAME)
                except FileNotFoundError:
                    pass
        return True, ""
    except OSError as e:
        return False, f"Не получилось настроить автозапуск ({e})"


class State:
    def __init__(self, api_factory=None):
        self.lock = threading.Lock()
        self.file_lock = threading.Lock()   # запись файлов из разных потоков — по очереди
        self.cfg = load_settings()
        self.deals = load_deals()           # находки прошлых запусков (ещё не снятые лоты)
        self.next_id = max((d["id"] for d in self.deals), default=0) + 1
        self.log = deque(load_journal(), maxlen=400)
        self.names = []
        self.artifacts = 0          # сколько артефактов в базе игры (для переключателя)
        self.catalog = []           # все предметы с категориями — для поиска и «категорий целиком»
        self.meta = {}
        self.cat_counts = {}
        self.purchases = load_purchases()
        self.worker = None
        self.api_factory = api_factory
        self.journal_once = {}      # что проверка уже писала в журнал за этот запуск программы (строки рынка и т. п.)
        self.icon_paths, self._icon_fail = {}, {}   # картинки предметов: путь в базе EXBO; когда не скачалась
        self._restart_due, self._restarting = 0.0, False
        # сервер для подписчиков (у владельца) и связь с сервером (у подписчика)
        self.feed, self.feed_rev, self._feed_cache = {}, 0, (None, b"", b"")
        self.subscribers = {}               # № кода → когда и откуда приходил
        self.feed_server, self.feed_error = None, ""
        self.near = {}                      # «почти находки»: ключ лота → запись с причиной, почему не прошла пороги
        self.quiet_since = None             # с какого момента нет находок — для сводки в журнале
        self._alerted = {}                  # текст оповещения → когда отправили (одно и то же — не чаще раза в 30 мин)
        self.status = {"running": False, "starting": False, "progress": None, "last_pass": None,
                       "delay": None, "delay_min": None, "delay_n": 0, "found_total": 0, "took": None,
                       "error": None, "error_id": 0, "db": None, "total": None, "server": None}
        self.last_poll = time.time()
        self.updater = Updater(self)
        self.access = Access(self)
        self.exit_requested = threading.Event()
        self.exit_hook = None               # как закрыть окно программы (задаёт main)
        logging.getLogger("tracker").addHandler(_LogHandler(self))
        logging.getLogger("tracker").setLevel(logging.INFO)
        self.add_log(f"— Запуск {APP_NAME} {APP_VERSION} · данные: {DATA_DIR} —")
        if MIGRATED:
            self.add_log("Перенёс из папки программы в папку данных: " + ", ".join(MIGRATED))
        if self.deals:
            self.add_log(f"Восстановил находки прошлого запуска: {len(self.deals)}")

    def add_log(self, msg):
        now = datetime.now()
        with self.lock:
            self.log.append({"t": now.strftime("%H:%M:%S"), "m": str(msg)})
        line = now.strftime("%Y-%m-%d %H:%M:%S") + "\t" + str(msg).replace("\n", " ") + "\n"
        with self.file_lock:
            try:
                with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
                    f.write(line)
            except OSError:
                pass

    def request_exit(self):
        """Закрыть программу — например, после установки обновления (новая версия запустится сама)."""
        self.exit_requested.set()
        hook = self.exit_hook
        if hook:
            try:
                hook()
            except Exception:
                pass

    def save_purchases(self):
        with self.lock:
            data = [dict(p) for p in self.purchases]
        with self.file_lock:
            try:
                write_json(PURCHASES_FILE, data)
            except OSError:
                pass

    # --- мои покупки ---
    def buy(self, deal_id, price=None):
        with self.lock:
            d = next((x for x in self.deals if x["id"] == deal_id), None)
            if d is None:
                return False, "Находка не найдена — обнови список"
            if d.get("bought"):
                return False, "Уже отмечено как купленное"
            try:
                paid = float(price) if price not in (None, "") else float(d["cost"])
            except (TypeError, ValueError):
                return False, "Цена покупки — число"
            pid = secrets.token_hex(4)
            self.purchases.insert(0, {
                "id": pid, "deal_id": d["id"], "item_id": d["item_id"], "name": d["name"], "cat": d.get("cat"),
                "kind": d["kind"], "amount": d["amount"], "paid": paid, "unit_paid": paid / max(d["amount"], 1),
                "additional": d.get("additional") or {}, "quality": d.get("quality"), "ptn": d.get("ptn"),
                "exact": d.get("exact"), "rare": d.get("rare"),
                "target": d["market"], "expected": d["market"] * d["amount"] * (1 - self.cfg["fee"]) - paid,
                "bought_at": time.time(), "status": "holding", "sold_price": None, "sold_at": None})
            d["bought"] = pid
            w = self.worker
            if w and w.is_alive():      # трекер уже работает — пусть сразу следит и за этой покупкой
                w.holdings.append(dict(self.purchases[0]))
        self.reconfigure_worker(wake=False)   # предмет покупки — в проверку со следующего прохода
        self.add_log(f"Отметил покупку: {d['name']} за {eng.fmt_rub(paid)}")
        self.save_purchases()
        self.save_deals()
        return True, "Отмечено: куплено ✓"

    def update_purchase(self, data):
        with self.lock:
            p = next((x for x in self.purchases if x["id"] == data.get("id")), None)
            if p is None:
                return False, "Покупка не найдена"
            try:
                if "paid" in data:
                    p["paid"] = max(0.0, float(data["paid"]))
                    p["unit_paid"] = p["paid"] / max(p["amount"], 1)
                if data.get("list_price") not in (None, ""):
                    price = float(str(data["list_price"]).replace(" ", "").replace(",", "."))
                    if price <= 0:
                        raise ValueError
                    p.update(list_price=price, listed_at=time.time(), status="listed")
                    p.pop("undercut", None)
                if data.get("status") in ("holding", "listed", "sold"):
                    p["status"] = data["status"]
                    if data["status"] == "holding":
                        p.pop("list_state", None)
                        p.pop("undercut", None)
                    if data["status"] == "listed" and not p.get("listed_at"):
                        p["listed_at"] = time.time()
                    if data["status"] == "sold":
                        p["sold_price"] = float(data.get("sold_price") or 0) or p.get("sold_price")
                        if not p["sold_price"]:
                            raise ValueError
                        p["sold_at"] = time.time()
                        p["profit"] = p["sold_price"] * (1 - self.cfg["fee"]) - p["paid"]
                    else:
                        p["sold_price"] = p["sold_at"] = None
                        p.pop("profit", None)
                    if data["status"] != "sold":
                        p.pop("auto_sold", None)
            except (TypeError, ValueError):
                return False, ("Впиши цену за весь лот — только цифры" if "list_price" in data
                               else "Впиши, за сколько продал (за весь лот), — только цифры")
        self.save_purchases()
        self._sync_holdings()
        return True, "Сохранено"

    def _sync_holdings(self):
        """Работающей проверке — свежий список того, что куплено и не продано (выставил, снял, продал)."""
        with self.lock:
            w, holdings = self.worker, [dict(p) for p in self.purchases if p.get("status") != "sold"]
        if w is not None and hasattr(w, "holdings"):
            w.holdings = holdings

    def alert(self, text, dedupe=False):
        """Сообщение о важном (продано, перебили, поиск встал) — в Telegram, если он настроен и не выключен.
        Сеть сразу после сна может ещё не подняться — три попытки с паузой. dedupe — одно и то же не чаще
        раза в 30 минут."""
        if not self.cfg.get("alerts", True):
            return
        cfg = dict(self.cfg)
        if not (str(cfg.get("telegram_token") or "").strip() and str(cfg.get("telegram_chat_id") or "").strip()):
            return
        now = time.time()
        if dedupe:
            if now - self._alerted.get(text, 0) < 1800:
                return
            self._alerted[text] = now

        def send():
            for attempt in range(3):
                ok, msg = send_telegram(cfg, text)
                if ok:
                    return
                if attempt == 2 or (msg and "не ответил" not in msg):
                    if msg:
                        self.add_log(msg)
                    return
                time.sleep(30)
        threading.Thread(target=send, daemon=True).start()

    def watchdog(self):
        """Раз в 30 секунд: не давать компьютеру уснуть во время поиска; заметить, что он всё-таки спал,
        что проверка встала или подписчик потерял связь с сервером, — и сообщить в Telegram."""
        last, stall_said, server_bad = time.time(), False, None
        while not self.exit_requested.wait(30):
            now = time.time()
            gap, last = now - last, now
            st = self.status
            running = st.get("running")
            if running and self.cfg.get("keep_awake", True):
                keep_awake()
            if gap > 150:      # часы прыгнули вперёд — компьютер спал
                fmt = lambda t: datetime.fromtimestamp(t).strftime("%H:%M")
                line = f"Компьютер спал с {fmt(now - gap)} до {fmt(now)} — поиск в это время не шёл"
                if running and self.feed_server:
                    line += ", подписчики не получали находок"
                self.add_log(line)
                if running:
                    self.alert("😴 " + line)
                continue
            lp = st.get("last_pass")
            subscriber = isinstance(self.worker, FeedWorker)
            if running and not subscriber and not st.get("starting") and lp and now - lp > STALL_ALERT:
                if not stall_said:
                    stall_said = True
                    err = st.get("error")
                    line = ("Поиск включён, но проверка аукциона не проходит уже больше 10 минут"
                            + (f": {err}" if err else " — проверь интернет"))
                    self.add_log(line)
                    self.alert("⚠ " + line)
            elif stall_said and lp and now - lp < 300:
                stall_said = False
                self.add_log("Проверка аукциона снова идёт")
                self.alert("✅ Проверка аукциона снова идёт")
            sv = st.get("server") or {}
            if running and subscriber and sv and not sv.get("ok"):
                server_bad = server_bad or now
                if now - server_bad > 300 and server_bad > 0:
                    line = "Нет связи с сервером владельца больше 5 минут" + (f": {sv.get('error')}" if sv.get("error") else "")
                    self.add_log(line)
                    self.alert("⚠ " + line)
                    server_bad = -1          # сообщили — ждём, пока связь вернётся
            elif sv.get("ok") and server_bad:
                if server_bad == -1:
                    self.add_log("Связь с сервером владельца восстановилась")
                    self.alert("✅ Связь с сервером владельца восстановилась")
                server_bad = None

    def remove_purchase(self, pid):
        with self.lock:
            self.purchases = [p for p in self.purchases if p["id"] != pid]
            for d in self.deals:
                if d.get("bought") == pid:
                    d["bought"] = None
        self.save_purchases()
        self.save_deals()
        self._sync_holdings()
        return True, "Удалено"

    # --- сервер для подписчиков (владелец) ---
    def feed_bytes(self, who=None):
        """(метка, JSON, JSON в gzip) для подписчика who: находки, отданные по очереди другому, он пока не видит."""
        now = time.time()
        with self.lock:
            for key in [k for k, r in self.feed.items()
                        if (r.get("gone") and now - (r.get("gone_at") or now) > FEED_KEEP_GONE)
                        or (r.get("ends") and State._ts(r["ends"], now + 1) < now - 300)]:
                del self.feed[key]
                self.feed_rev += 1
            deals = []
            for r in self.feed.values():
                mine = r.get("excl") and now < r.get("excl_until", 0)
                if mine and r["excl"] != who:
                    continue        # пока — только тому, кому досталась по очереди
                d = {k: v for k, v in r.items() if k not in ("text", "notify", "id", "excl", "excl_until")}
                if mine:
                    d["only_you_until"] = r["excl_until"]
                deals.append(d)
            payload = {"v": 1, "server_version": APP_VERSION, "time": now,
                       "last_pass": self.status.get("last_pass"), "items": self.status.get("total"), "deals": deals}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        tag = hashlib.md5(json.dumps(deals, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return tag, body, gzip.compress(body, 6)

    def _assign_exclusive(self, rec):
        """Новая находка — сначала одному подписчику (под lock): из тех, кто онлайн и кому она подходит по его
        предметам и порогам, тому, кто за последний час получил меньше всех. Через EXCLUSIVE_S её видят все."""
        now = time.time()
        cands = [(key, sub) for key, sub in self.subscribers.items()
                 if now - sub["last"] < 90 and isinstance(sub.get("want"), dict) and wants(sub["want"], rec)]
        if not cands or rec.get("gone"):
            return
        key, sub = min(cands, key=lambda ks: (sum(1 for t in ks[1].get("given", []) if now - t < 3600),
                                              ks[1].get("given", [0])[-1] if ks[1].get("given") else 0))
        sub["given"] = (sub.get("given") or [])[-199:] + [now]
        rec["excl"], rec["excl_until"] = key, now + EXCLUSIVE_S

    def subscriber_wants(self):
        """Что выбрали подписчики, которые заходили за последние 10 минут: (предметы, категории)."""
        now, items, cats = time.time(), set(), set()
        with self.lock:
            for sub in self.subscribers.values():
                want = sub.get("want")
                if now - sub["last"] < WANT_FRESH and isinstance(want, dict):
                    items.update(str(x) for x in (want.get("w") or [])[:400])
                    cats.update(str(x) for x in (want.get("c") or [])[:20])
        return items, cats

    def subscribers_seen(self):
        """№ кода → когда последний раз приходил кто-то из его компьютеров."""
        with self.lock:
            out = {}
            for key, s in self.subscribers.items():
                cid = s.get("cid") or key
                out[cid] = max(out.get(cid, 0), s["last"])
            return out

    def serving(self):
        return bool(self.cfg.get("server_enabled") and self.access.is_owner() and OWNER_PUBLIC_KEY)

    def sync_feed_server(self):
        """Включить или выключить сервер для подписчиков по настройкам."""
        want = self.serving()
        port = int(self.cfg.get("server_port") or FEED_PORT)
        srv = self.feed_server
        if srv and (not want or srv.server_address[1] != port):
            srv.shutdown()
            srv.server_close()
            self.feed_server = None
            self.add_log("Сервер для подписчиков выключен")
        if want and not self.feed_server:
            try:
                srv = ThreadingHTTPServer(("127.0.0.1", port), make_feed_handler(self))
            except OSError as e:
                self.feed_error = f"порт {port} занят ({e.strerror or e})"
                self.add_log("Сервер для подписчиков не запустился: " + self.feed_error)
                return
            srv.daemon_threads = True
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            self.feed_server, self.feed_error = srv, ""
            self.add_log(f"Сервер для подписчиков работает: 127.0.0.1:{port}. Наружу его выводит Tailscale Funnel "
                         f"(команда: tailscale funnel {port})")

    def open_funnel(self):
        """Кнопка «Открыть доступ из интернета»: Tailscale Funnel, адрес — сразу в настройки, сервер — включить."""
        if not self.access.is_owner():
            return False, "Только владелец", None
        port = int(self.cfg.get("server_port") or FEED_PORT)
        ok, msg, link = funnel_open(port)
        if not ok:
            return False, msg, link
        ok2, why = self.update_settings({"server_enabled": True, "server_url": msg})
        if not ok2:
            return False, why, None
        self.add_log(f"Сервер для подписчиков открыт в интернет: {msg}")
        return True, f"Готово: {msg} — новые коды будут вести сюда", None

    def test_public_url(self):
        """Владелец проверяет, видно ли его сервер из интернета по публичному адресу."""
        url = str(self.cfg.get("server_url") or "").strip().rstrip("/")
        if not re.match(r"^https?://[^\s/]+", url):
            return False, "Впиши публичный адрес, например https://мой-пк.xxxx.ts.net"
        try:
            r = requests.get(url + "/v1/ping", timeout=15)
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            return False, f"По адресу {url} сервер не отвечает ({type(e).__name__}). Включён ли Tailscale Funnel?"
        if r.status_code == 200 and data.get("app") == "stalzone-tracker":
            return True, f"Работает: по адресу {url} отвечает твой трекер {data.get('version', '')}"
        return False, f"По адресу {url} отвечает что-то другое (код {r.status_code})"

    def save_deals(self):
        with self.lock:
            deals = list(self.deals)
        with self.file_lock:
            try:
                write_json(DEALS_FILE, deals)
            except OSError:
                pass

    def _prune_near(self, now):
        """«Почти находки»: купленные видно 10 минут, остальные — пока их видят проверки (до получаса)."""
        for key, rec in list(self.near.items()):
            if (rec.get("gone") and now - (rec.get("gone_at") or now) > 600) or now - rec.get("seen", now) > NEAR_KEEP:
                del self.near[key]
        if len(self.near) > NEAR_MAX:
            for key, _ in sorted(self.near.items(), key=lambda kv: kv[1].get("seen", 0))[:len(self.near) - NEAR_MAX]:
                del self.near[key]

    def _quiet_summary(self, now):
        """Полчаса без находок — строка для журнала: что было отсеяно порогами (или что рынок тихий).
        Вызывать под self.lock."""
        if self.quiet_since is None:
            self.quiet_since = now
            return None
        if now - self.quiet_since < QUIET_SUMMARY:
            return None
        since, self.quiet_since = self.quiet_since, now
        self._prune_near(now)
        recent = [r for r in self.near.values() if r.get("seen", 0) >= since]   # были на аукционе за это время
        minutes = round((now - since) / 60)
        if not recent:
            return (f"За {minutes} мин находок нет. Лотов дешевле рынка хотя бы на {NEAR_DISCOUNT * 100:.0f}% "
                    f"с прибылью от {eng.fmt_rub(NEAR_MIN_PROFIT)} тоже не было — рынок сейчас тихий")
        best = max(recent, key=lambda r: r.get("profit") or 0)
        return (f"За {minutes} мин находок по твоим порогам нет, но было {len(recent)} "
                f"{plural_ru(len(recent), ('лот', 'лота', 'лотов'))} дешевле рынка с меньшей выгодой. "
                f"Лучший: {best['name']} — прибыль ~{eng.fmt_rub(best['profit'])} ({why_text(best.get('why'))}). "
                "Пороги — в «Настройках», такие лоты видно в «Почти находках»")

    def emit(self, kind, data):
        quiet_line = sold_line = None
        with self.lock:
            if kind == "deal":
                data["id"] = self.next_id
                data["found"] = time.time()
                self.next_id += 1
                self.deals.insert(0, data)
                del self.deals[400:]
                self.status["found_total"] += 1
                self.near.pop(data.get("key"), None)   # порог снизили — «почти находка» стала находкой
                self.quiet_since = data["found"]
            elif kind == "near":
                now = time.time()
                old = self.near.get(data["key"])
                rec = dict(data, found=(old or {}).get("found", now), seen=now)
                if old and old.get("gone"):
                    rec.update(gone=True, fate=old.get("fate"), gone_at=old.get("gone_at"))
                self.near[data["key"]] = rec
                self._prune_near(now)
            elif kind == "progress":
                self.status["progress"] = data
                self.status["starting"] = False
            elif kind == "pass":
                self.status.update(last_pass=data["time"], took=data["took"], progress=None, total=data.get("total"),
                                   key_others=data.get("key_others"), key_limit=data.get("key_limit"),
                                   keys=data.get("keys"), keys_total=data.get("keys_total"))
                quiet_line = self._quiet_summary(data["time"])
                if data["delay"] is not None:
                    self.status.update(delay=data["delay"], delay_min=data.get("delay_min"),
                                       delay_n=data.get("delay_n", 0))
                if data.get("db"):
                    self.status["db"] = data["db"]
            elif kind == "error":
                self.status["error"] = data
                self.status["error_id"] += 1
            elif kind == "lots_seen":  # лота больше нет на аукционе — его купили или сняли
                present = set(data["keys"])
                cap = data.get("cap")      # дороже — лот мог просто не попасть на первую страницу
                cap = math.inf if cap is None else cap
                for d in self.deals:
                    if (d.get("item_id") == data["item_id"] and d.get("lot_key") and d["lot_key"] not in present
                            and self._lot_price(d) < cap):
                        d["gone"] = True
                now = time.time()
                for rec in self.near.values():
                    if (rec.get("item_id") == data["item_id"] and rec.get("lot_key") not in present
                            and not rec.get("gone") and self._lot_price(rec) < cap):
                        rec["gone"], rec["gone_at"] = True, now
                for rec in self.feed.values():
                    if (rec["item_id"] == data["item_id"] and rec["lot_key"] not in present and not rec.get("gone")
                            and self._lot_price(rec) < cap):
                        rec["gone"], rec["gone_at"] = True, now
                        self.feed_rev += 1
            elif kind == "feed":         # находка для подписчиков (широкие пороги)
                old = self.feed.get(data["key"])
                rec = dict(data, found=(old or {}).get("found", time.time()))
                if old and old.get("gone"):
                    rec.update(gone=old["gone"], gone_at=old.get("gone_at"), fate=old.get("fate"))
                if old:
                    rec.update({k: old[k] for k in ("excl", "excl_until") if k in old})
                else:
                    self._assign_exclusive(rec)
                self.feed[data["key"]] = rec
                self.feed_rev += 1
            elif kind == "feed_sync":    # подписчик: что сейчас есть на сервере
                present, fates = set(data["present"]), data["fates"]
                for d in self.deals:
                    if d.get("source") != "server":
                        continue
                    if d.get("lot_key") in fates:
                        d["gone"] = True
                        if fates[d["lot_key"]]:
                            d["fate"] = fates[d["lot_key"]]
                    elif d.get("lot_key") not in present:
                        d["gone"] = True
            elif kind == "server":
                self.status["server"] = dict(data, at=time.time())
            elif kind == "lot_status":   # пропавший лот: купили (есть сделка в истории), сняли или истёк
                for d in self.deals:
                    if d.get("lot_key") == data["lot_key"]:
                        d["gone"] = True
                        d["fate"] = data["status"]
                for rec in self.feed.values():
                    if rec.get("lot_key") == data["lot_key"]:
                        rec.update(gone=True, fate=data["status"], gone_at=rec.get("gone_at") or time.time())
                        self.feed_rev += 1
                for rec in self.near.values():
                    if rec.get("lot_key") == data["lot_key"]:
                        rec.update(gone=True, fate=data["status"], gone_at=rec.get("gone_at") or time.time())
            elif kind == "holding":      # текущая цена купленного
                for p in self.purchases:
                    if p["id"] == data["id"]:
                        p.update({"cur_market": data.get("market"), "cur_hist": data.get("hist"),
                                  "cur_floor": data.get("floor"), "cur_chance": data.get("chance"),
                                  "cur_at": data.get("updated")})
                        if "options" in data:
                            p["options"] = data["options"]
                        p["list_state"] = data.get("list_state")
                        if not (data.get("list_state") or {}).get("cheaper"):
                            p.pop("undercut", None)
            elif kind == "undercut":     # твой выставленный лот перебили
                for p in self.purchases:
                    if p["id"] == data["id"]:
                        p["undercut"] = dict(data, at=time.time())
            elif kind == "holding_sold":   # выставленный лот пропал, а в истории есть сделка ровно на него
                for p in self.purchases:
                    if p["id"] == data["id"] and p.get("status") != "sold":
                        p.update(status="sold", sold_price=data["price"], sold_at=time.time(), auto_sold=True,
                                 profit=data["price"] * (1 - self.cfg["fee"]) - p["paid"])
                        p.pop("undercut", None)
                        sold_line = (f"Продано: {p['name']} за {eng.fmt_rub(data['price'])} — прибыль "
                                     f"{'+' if p['profit'] >= 0 else '−'}{eng.fmt_rub(abs(p['profit']))} (по истории сделок; "
                                     "если это не ты — нажми «Вернуть» в «Моих покупках»)")
            elif kind == "accuracy":
                self.status["accuracy"] = data
            elif kind == "craft_progress":
                self.status["craft_left"] = data["left"]
            elif kind == "stopped":
                self.status.update(running=False, starting=False, progress=None)
                self.quiet_since = None
        if sold_line:
            self.add_log(sold_line)
            self.save_purchases()
            self.alert("💰 " + sold_line.split(" (по истории")[0])
        if kind == "log":
            self.add_log(data)
        elif kind == "deal":
            self.add_log(f"Найдено: {data['name']} — прибыль ~{eng.fmt_rub(data['profit'])}")
        elif kind == "error":
            self.add_log("ОШИБКА: " + data)
            self.alert("⚠ Трекер: " + data, dedupe=True)
        elif kind in ("pass", "stopped"):
            if quiet_line:
                self.add_log(quiet_line)
            self.save_deals()   # находки на диск после каждой проверки — закрытие окна их не сотрёт
            self.save_purchases()

    def load_names(self):
        try:
            names = eng.load_listing(self.cfg["region"])
            self.names = sorted(set(names.values()), key=str.lower)
            self.artifacts = len(eng.load_artifacts(self.cfg["region"]))
            catalog = eng.load_catalog(self.cfg["region"])
            counts = {}
            for e in catalog:   # в «категориях целиком» — только то, что продаётся и не бартерное
                if e["trade"] and not e["barter"]:
                    counts[e["cat"]] = counts.get(e["cat"], 0) + 1
            with self.lock:
                self.catalog, self.meta, self.cat_counts = catalog, {e["id"]: e for e in catalog}, counts
            try:
                self.icon_paths = eng.load_icons(self.cfg["region"])
            except Exception:
                self.icon_paths = {}
            self.add_log(f"Справочник предметов загружен: {len(self.names)} шт., из них артефактов: "
                         f"{self.artifacts}")
        except Exception as e:
            self.add_log(f"Справочник не загрузился ({e}) — названия вводи точно как в игре")
        stats = eng.MarketDB.quick_stats()
        if stats:
            with self.lock:
                self.status["db"] = stats
        self.sync_feed_server()
        if self.updater.repo():
            self.updater.check()    # при запуске сами смотрим, нет ли новой версии
        threading.Thread(target=self.watch_access, daemon=True).start()

    def icon(self, item_id):
        """Картинка предмета (PNG): из папки данных, а в первый раз — из базы EXBO на GitHub. None — нет."""
        if not re.fullmatch(r"[a-z0-9]{2,16}", item_id or ""):
            return None
        folder = os.path.join(DATA_DIR, "icons")
        path = os.path.join(folder, item_id + ".png")
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            pass
        rel = self.icon_paths.get(item_id)
        if not rel or os.environ.get("STALZONE_OFFLINE") or time.time() - self._icon_fail.get(item_id, 0) < 900:
            return None
        try:
            r = requests.get(ICON_URL.format(region=self.cfg.get("region", "ru"), path=rel), timeout=15)
            data = r.content if r.status_code == 200 else b""
        except requests.RequestException:
            data = b""
        if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > 2_000_000:
            self._icon_fail[item_id] = time.time()
            return None
        try:
            os.makedirs(folder, exist_ok=True)
            with open(path + ".part", "wb") as f:
                f.write(data)
            os.replace(path + ".part", path)
        except OSError:
            pass
        return data

    # --- калькулятор крафта ---
    def craft(self):
        """Рецепты убежища с ценами аукциона: прибыль за крафт и на 1000 энергии, что откроет следующий
        уровень навыка. Цены — медиана последних сделок из своей базы (за 7 дней)."""
        region = self.cfg.get("region", "ru")
        perks, recipes = eng.load_hideout(region)
        if perks is None:
            return {"ok": False, "message": "Рецепты убежища не скачались — проверь интернет и открой вкладку ещё раз."}
        skills = {k: int(v) for k, v in (self.cfg.get("skills") or {}).items()}
        items = {i for r in recipes for i, _ in r["result"] + r["ingredients"]}
        db = eng.MarketDB.reader()
        try:
            raw = db.unit_prices(region, items) if db else {}
        finally:
            if db:
                db.close()
        prices = {i: v[0] for i, v in raw.items()}
        rows = eng.craft_rows(recipes, prices, skills, fee=self.cfg.get("fee", 0.05))
        advice = eng.skill_advice(rows, skills, perks)
        with self.lock:
            meta = dict(self.meta)
            w = self.worker
        queued = len(w.price_queue) if isinstance(w, Worker) else 0
        trade = {i: bool((meta.get(i) or {}).get("trade", True)) for i in items}
        return {"ok": True, "perks": [{"id": k, "name": v, "level": skills.get(k, 0)} for k, v in perks.items()],
                "rows": [{k: r[k] for k in ("id", "bench", "cat", "sub", "result", "ingredients", "energy", "perks",
                                            "features", "cost", "value", "profit", "per_energy", "available", "need",
                                            "missing")} for r in rows],
                "advice": advice, "prices": {i: [round(v[0], 2), v[1], v[2]] for i, v in raw.items()},
                "names": {i: (meta.get(i) or {}).get("name", i) for i in items}, "trade": trade,
                "queued": queued, "running": isinstance(w, Worker) and w.is_alive()}

    def craft_fetch(self, only_available=True):
        """Поставить в очередь цены, которых не хватает калькулятору: предметы, что продаются на аукционе,
        без сделок в базе или с последней сделкой старше суток. Качает работающая проверка, понемногу."""
        with self.lock:
            w, meta = self.worker, dict(self.meta)
        if isinstance(w, FeedWorker) or self.subscriber_server():
            return False, "По подписке своей базы цен нет — калькулятору крафта нужны свои ключи API"
        if not (isinstance(w, Worker) and w.is_alive()):
            return False, "Цены качаются вместе с поиском — нажми «Начать поиск»"
        region = self.cfg.get("region", "ru")
        perks, recipes = eng.load_hideout(region)
        if perks is None:
            return False, "Рецепты убежища не скачались"
        skills = {k: int(v) for k, v in (self.cfg.get("skills") or {}).items()}
        if only_available:
            recipes = [r for r in recipes if all(skills.get(k, 0) >= v for k, v in r["perks"].items())]
        items = {i for r in recipes for i, _ in r["result"] + r["ingredients"] if (meta.get(i) or {}).get("trade", True)}
        db = eng.MarketDB.reader()
        try:
            have = db.unit_prices(region, items) if db else {}
        finally:
            if db:
                db.close()
        fresh = {i for i, v in have.items() if time.time() - v[2] < 86400}
        todo = [i for i in sorted(items) if i not in fresh and i not in w.price_queue]
        w.price_queue.extend(todo)
        with self.lock:
            self.status["craft_left"] = len(w.price_queue)
        if not todo:
            return True, "Все нужные цены уже есть"
        minutes = max(1, round(len(w.price_queue) / CRAFT_PER_PASS * 0.6))
        return True, f"Узнаю цены {len(todo)} предм. — примерно {minutes} мин, поиск при этом не останавливается"

    # --- что приносят предметы списка ---
    def item_yield(self):
        """По каждому предмету своего списка: сколько лотов дешевле рынка видели за неделю, на сколько из них
        можно было успеть (висели 3+ минуты), сколько было находок. Пустые — кандидаты на удаление."""
        names = self.names_map()
        items, auto = eng.watch_items(self.cfg, names)
        db = eng.MarketDB.reader()
        try:
            y = db.item_yield(self.cfg.get("region", "ru"), cheap=1 - float(self.cfg.get("discount", 0.15))) if db else {}
        finally:
            if db:
                db.close()
        now, rows = time.time(), []
        if not y:      # своей базы лотов нет (подписка или поиск ещё не запускали) — нечего показать
            return {"ok": True, "rows": [], "total": len(items), "auto": len(auto)}
        for item_id, name in items:
            if item_id in auto:
                continue
            v = y.get(item_id) or {}
            span = (now - v["first"]) / 3600 if v.get("first") else 0
            good = v.get("catch", 0) or v.get("deal", 0)
            status = "good" if good else "empty" if span >= 24 and v.get("lots", 0) and not v.get("cheap") else "new"
            rows.append({"id": item_id, "name": name, "lots": v.get("lots", 0), "cheap": v.get("cheap", 0),
                         "catch": v.get("catch", 0), "deal": v.get("deal", 0), "near": v.get("near", 0),
                         "hours": round(span, 1), "status": status})
        rows.sort(key=lambda r: (-r["catch"] - r["deal"], -r["cheap"], r["name"].lower()))
        return {"ok": True, "rows": rows, "total": len(items), "auto": len(auto)}

    def names_map(self):
        try:
            return eng.load_listing(self.cfg.get("region", "ru"))
        except Exception:
            return {}

    def remove_watch_ids(self, ids):
        """Убрать предметы из своего списка по id (записи в списке — названия или id)."""
        ids = set(ids or [])
        names = self.names_map()
        keep = [w for w in self.cfg.get("watch") or [] if not any(i in ids for i, _ in eng.resolve_watch([w], names))]
        removed = len(self.cfg.get("watch") or []) - len(keep)
        ok, msg = self.update_settings({"watch": keep})
        return ok, (f"Убрал {removed} {plural_ru(removed, ('предмет', 'предмета', 'предметов'))}" if ok else msg)

    def item_stats(self, item_id, quality=None, ptn=None):
        """Для карточки находки: цена по дням за неделю и в какие часы предмет покупают."""
        try:
            grade = (int(quality), int(ptn)) if quality not in (None, "") and ptn not in (None, "") else None
        except (TypeError, ValueError):
            grade = None
        path = os.path.join(eng.HERE, "market.db")
        if not os.path.exists(path):
            return {"series": [], "hours": [0] * 24}
        con = sqlite3.connect(path, timeout=5)
        try:
            region = self.cfg.get("region", "ru")
            series = eng.price_series(con, region, item_id, grade)
            hours = eng.hour_profile(con, region, item_id, grade)
        except sqlite3.Error:
            series, hours = [], [0] * 24
        finally:
            con.close()
        return {"series": [{"t": t, "p": p, "n": n} for t, p, n in series], "hours": hours}

    def watch_access(self):
        """Раз в несколько часов — список отозванных кодов; доступ отозвали — останавливаем поиск."""
        while not self.exit_requested.is_set():
            self.access.refresh_revoked()
            info = self.access.check()
            if not info["ok"] and self.worker and self.worker.is_alive():
                self.add_log("Доступ закрыт: " + info.get("reason", ""))
                self.stop()
            self.exit_requested.wait(600)

    def api_cfg(self):
        """Настройки для проверки: свои ключи API, а если их нет — ключ владельца из кода доступа
        (только в памяти, в settings.json не пишется)."""
        cfg = dict(self.cfg)
        try:   # в журнале при делёже лимита — кто, скорее всего, пользуется ключом
            names = self.access.shared_names() if self.access.is_owner() else []
        except Exception:
            names = []
        if names:
            cfg["share_hint"] = (" — скорее всего, это " + ", ".join(names[:5])
                                 + " (код доступа с твоим ключом API)")
            cfg["share_expected"] = True    # ты сам дал ключ друзьям — лимит делим поровну
        own = (cfg.get("client_id") and cfg.get("client_secret")) or cfg.get("app_token")
        if not own and cfg.get("base_url", "").rstrip("/") != DEMO_URL:
            shared = self.access.shared_api()
            if shared:
                cfg.update({k: v for k, v in shared.items() if v})
                cfg["shared_api"] = True
                cfg["share_expected"] = True   # ключ владельца — с ним и другими его друзьями
        return cfg

    def subscriber_server(self):
        """Адрес сервера владельца, если эта программа — подписчик (находки берёт с сервера)."""
        if not OWNER_PUBLIC_KEY or self.access.is_owner():
            return None
        info = self.access.check()
        if not info["ok"] or info.get("mode") != "code":
            return None
        return str(self.cfg.get("server_url_override") or "").strip().rstrip("/") or self.access.server_url()

    def start(self):
        if not self.access.check()["ok"]:
            return
        feed_url = self.subscriber_server()
        if feed_url:
            with self.lock:
                if self.worker and self.worker.is_alive():
                    return
                self.status.update(running=True, starting=True, error=None)
                self.worker = FeedWorker(dict(self.cfg), self.emit, feed_url, self.cfg.get("access_code", ""),
                                         self.access.machine, shown={d["key"] for d in self.deals if d.get("key")},
                                         holdings=[dict(p) for p in self.purchases if p.get("status") != "sold"])
                self.worker.start()
            self.add_log("Трекер запущен — находки с сервера владельца")
            return
        with self.lock:
            if self.worker and self.worker.is_alive():
                return
            self.status.update(running=True, starting=True, error=None)
            tracked = [{"lot_key": d["lot_key"], "item_id": d["item_id"], "amount": d["amount"],
                        "price": self._lot_price(d), "since": self._ts(d.get("listed"), 0),
                        "ends": self._ts(d.get("ends"), None)}
                       for d in self.deals if d.get("kind") == "buyout" and d.get("lot_key") and not d.get("fate")]
            holdings = [dict(p) for p in self.purchases if p.get("status") != "sold"]
            self.worker = Worker(self.api_cfg(), self.emit, self.api_factory,
                                 shown={d["key"] for d in self.deals if d.get("key")},
                                 tracked=tracked, holdings=holdings, serving=self.serving(),
                                 shared=self.journal_once, wants_fn=self.subscriber_wants)
            self.worker.start()
        self.add_log("Трекер запущен" + (" (ДЕМО-режим)" if self.cfg["base_url"] == DEMO_URL else "")
                     + (" — по ключу API владельца из кода доступа" if self.worker.cfg.get("shared_api") else ""))

    @staticmethod
    def _lot_price(d):
        """Цена выкупа лота как её отдаёт API (она же в ключе лота) — с ней сверяем историю сделок."""
        try:
            return float(str(d["lot_key"]).rsplit("|", 1)[1])
        except (KeyError, IndexError, ValueError):
            return float(d.get("cost") or 0)

    @staticmethod
    def _ts(iso, default):
        try:
            return eng.parse_time(iso).timestamp()
        except (TypeError, ValueError):
            return default

    def stop(self):
        w = self.worker
        if w and w.is_alive():
            w.stop()
            self.add_log("Останавливаю…")

    def restart_if_running(self):
        """Перезапуск проверки (сменили ключи API). Несколько изменений подряд — один перезапуск,
        через RESTART_DELAY секунд после последнего. Если проверку за это время остановили — не запускаем."""
        w = self.worker
        if not (w and w.is_alive()):
            return
        with self.lock:
            self._restart_due = time.time() + RESTART_DELAY
            if self._restarting:
                return
            self._restarting = True

        def go():
            try:
                while True:
                    with self.lock:
                        left = self._restart_due - time.time()
                    if left <= 0:
                        break
                    time.sleep(min(left, 0.5))
                w = self.worker
                if not (w and w.is_alive()) or w.stop_event.is_set():
                    return              # остановили вручную или проверка завершилась сама
                w.stop()
                w.join(timeout=180)
                if w.is_alive():
                    self.add_log("Проверка не остановилась за 3 минуты — запусти её заново кнопкой")
                    return
                self.start()
            finally:
                with self.lock:
                    self._restarting = False
        threading.Thread(target=go, daemon=True).start()

    def reconfigure_worker(self, wake=True):
        """Новые настройки работающей проверке — без перезапуска."""
        w = self.worker
        if not (w and w.is_alive()) or w.stop_event.is_set():
            return
        if isinstance(w, FeedWorker):
            w.reconfigure(dict(self.cfg), wake=wake)
        else:
            w.reconfigure(self.api_cfg(), serving=self.serving(), wake=wake)

    def snapshot(self):
        with self.lock:
            cfg = dict(self.cfg)
            demo = cfg.get("base_url", "").rstrip("/") == DEMO_URL
            has_keys = bool(cfg.get("client_id") and cfg.get("client_secret"))
        shared = bool(not demo and not has_keys and not cfg.get("app_token") and self.access.shared_api())
        feed_url = self.subscriber_server()
        server = None
        if self.access.is_owner() and OWNER_PUBLIC_KEY:
            now = time.time()
            with self.lock:
                online = sum(1 for x in self.subscribers.values() if now - x["last"] < 120)
                feed_n = sum(1 for r in self.feed.values() if not r.get("gone"))
            sub_items, sub_cats = self.subscriber_wants()
            server = {"role": "owner", "enabled": bool(cfg.get("server_enabled")), "running": bool(self.feed_server),
                      "sub_items": len(sub_items), "sub_cats": sorted(sub_cats),
                      "port": int(cfg.get("server_port") or FEED_PORT), "url": cfg.get("server_url") or "",
                      "error": self.feed_error, "online": online, "feed": feed_n}
        elif feed_url:
            server = {"role": "subscriber", "url": feed_url}
        access, update = self.access.snapshot(), self.updater.snapshot()   # до self.lock: им самим нужен этот замок
        with self.lock:
            self._prune_near(time.time())
            near = sorted(self.near.values(), key=lambda r: (bool(r.get("gone")), -(r.get("profit") or 0)))[:12]
            return {
                "status": dict(self.status),
                "deals": list(self.deals),
                "near": [{k: v for k, v in r.items() if k != "text"} for r in near],
                "log": list(self.log)[-200:],
                "settings": cfg,
                # для демо ключи встроены, поэтому демо-режим тоже считается «настроенным»
                "configured": bool(demo or has_keys or cfg.get("app_token") or shared or feed_url),
                "server": server,
                "shared_api": shared,
                "has_keys": has_keys,
                "demo": demo,
                "artifacts": self.artifacts,
                "version": APP_VERSION,
                "data_dir": DATA_DIR,
                "update": update,
                "access": access,
                "purchases": [dict(p) for p in self.purchases],
                "cat_counts": dict(self.cat_counts),
                "auto_cats": eng.auto_categories(cfg),
                "frozen": bool(getattr(sys, "frozen", False)),
                "now": time.time(),
            }

    def update_settings(self, data):
        cfg = dict(self.cfg)
        try:
            for key in ("client_id", "client_secret", "app_token", "telegram_token", "telegram_chat_id"):
                if key in data:
                    cfg[key] = str(data[key]).strip()
            if "discount_pct" in data:
                cfg["discount"] = min(0.9, max(0.01, float(data["discount_pct"]) / 100))
            if "min_profit" in data:
                cfg["min_profit"] = max(0.0, float(data["min_profit"]))
            if "poll_minutes" in data:
                cfg["poll_minutes"] = min(60.0, max(0.0, float(data["poll_minutes"])))
            if "history_hours" in data:
                cfg["history_hours"] = min(168, max(6, int(float(data["history_hours"]))))
            if "history_keep_days" in data:
                cfg["history_keep_days"] = min(90, max(3, int(float(data["history_keep_days"]))))
            if "bid_window_minutes" in data:
                cfg["bid_window_minutes"] = min(720, max(5, int(float(data["bid_window_minutes"]))))
            if "bids" in data:
                cfg["bids"] = bool(data["bids"])
            if "all_artifacts" in data:
                cfg["all_artifacts"] = bool(data["all_artifacts"])
                cats = [c for c in cfg.get("auto_categories") or [] if c != "artefact"]
                cfg["auto_categories"] = (["artefact"] if cfg["all_artifacts"] else []) + cats
            if "auto_categories" in data:
                cats = [c for c in data["auto_categories"] or [] if c in eng.AUTO_CATEGORIES]
                cfg["auto_categories"] = list(dict.fromkeys(cats))
                cfg["all_artifacts"] = "artefact" in cats
            if "rare_enabled" in data:
                cfg["rare_enabled"] = bool(data["rare_enabled"])
            if "rare_quality" in data:
                cfg["rare_quality"] = min(5, max(0, int(float(data["rare_quality"]))))
            if "rare_min_profit" in data:
                cfg["rare_min_profit"] = max(0.0, float(data["rare_min_profit"]))
            if "rare_items" in data:
                cfg["rare_items"] = list(dict.fromkeys(str(x).strip() for x in data["rare_items"] if str(x).strip()))[:200]
            if "server_enabled" in data:
                cfg["server_enabled"] = bool(data["server_enabled"])
            if "server_url" in data:
                url = str(data["server_url"] or "").strip().rstrip("/")
                if url and not re.match(r"^https?://[^\s/]+$", url):
                    return False, "Публичный адрес пишется так: https://имя-пк.xxxx.ts.net"
                cfg["server_url"] = url
            if "server_port" in data:
                cfg["server_port"] = min(65000, max(1024, int(float(data["server_port"]))))
            if "server_url_override" in data:
                cfg["server_url_override"] = str(data["server_url_override"] or "").strip().rstrip("/")
            if "notify_min_chance" in data:
                cfg["notify_min_chance"] = min(90.0, max(0.0, float(data["notify_min_chance"])))
            if "extra_keys" in data:
                try:
                    cfg["extra_keys"] = parse_keys(data["extra_keys"], self.cfg.get("extra_keys"))
                except ValueError as e:
                    return False, f"Ещё ключи: {e}"
            for key in ("calibrate", "threshold_expected", "keep_awake", "autostart", "autorun_search", "alerts"):
                if key in data:
                    cfg[key] = bool(data[key])
            if "skills" in data and isinstance(data["skills"], dict):
                cfg["skills"] = {str(k)[:40]: min(5, max(0, int(float(v or 0)))) for k, v in data["skills"].items()}
            if "update_repo" in data:
                repo = str(data["update_repo"] or "").strip().strip("/")
                repo = re.sub(r"^https?://github\.com/", "", repo).strip("/")   # можно вставить и ссылку
                if repo and not REPO_RE.match(repo):
                    return False, "Репозиторий для обновлений пишется так: владелец/имя (например, ivan/stalzone-tracker)."
                cfg["update_repo"] = repo
            if "demo" in data:
                cfg["base_url"] = DEMO_URL if data["demo"] else PROD_URL
            if "watch" in data:
                watch = list(dict.fromkeys(str(w).strip() for w in data["watch"] if str(w).strip()))
                if len(watch) > WATCH_MAX:   # раньше лишнее молча отрезалось — и «Добавлено» врало
                    return False, (f"В списке не больше {WATCH_MAX} предметов. Для целых групп включи "
                                   "«Категории целиком» — они в этот предел не входят.")
                cfg["watch"] = watch
        except (TypeError, ValueError):
            return False, "Проверь числа в настройках — там должны быть только цифры."
        with self.lock:
            old, self.cfg = self.cfg, cfg
        save_settings(cfg)
        self.sync_feed_server()
        changed = {k for k in set(old) | set(cfg) if old.get(k) != cfg.get(k)}
        note = ""
        if "autostart" in changed:
            ok, why = set_autostart(cfg["autostart"])
            if not ok:
                note = " · " + why
        if changed & {"min_profit", "discount", "rare_enabled", "rare_min_profit", "rare_quality", "rare_items",
                      "threshold_expected"}:
            with self.lock:
                self.near = {}              # пороги другие — «почти находки» пересчитает следующий проход
        if changed & set(RESTART_KEYS):
            self.restart_if_running()       # другие ключи API — нужен новый вход
        elif changed:                       # остальное — на ходу, без перезапуска
            self.reconfigure_worker(wake=bool(changed - set(QUIET_KEYS)))
        return True, "Сохранено" + note

    def suggest(self, q):
        q = eng.norm(q or "")
        if len(q) < 2:
            return []
        starts = [n for n in self.names if eng.norm(n).startswith(q)]
        contains = [n for n in self.names if q in eng.norm(n) and n not in starts]
        return (starts + contains)[:25]


class _LogHandler(logging.Handler):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def emit(self, record):
        self.state.add_log(record.getMessage())


# ---------------------------------- Сервер ----------------------------------
FONT_FILES = {name: base64.b64decode(data) for name, data in stalzone_fonts.FONTS.items()}
BLANK_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def make_handler(state, token):
    page = UI_HTML.replace("__TOKEN__", token)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            return secrets.compare_digest(self.headers.get("X-Token", ""), token)

        def send_file(self, data, ctype, max_age=604800):
            """Картинка или шрифт с кэшем; нет такого файла — 404."""
            self.send_response(200 if data else 404)
            self.send_header("Content-Type", ctype if data else "text/plain")
            self.send_header("Cache-Control", f"max-age={max_age}" if data else "no-store")
            self.send_header("Content-Length", str(len(data or b"")))
            self.end_headers()
            if data:
                self.wfile.write(data)

        def body_json(self):
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode("utf-8"))
            except ValueError:
                return {}

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                body = page.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if url.path.startswith("/icon/") and url.path.endswith(".png"):
                data = state.icon(url.path[6:-4])
                # нет картинки — прозрачный пиксель (страница покажет букву); попробуем снова через 10 минут
                return self.send_file(data or BLANK_PNG, "image/png", 604800 if data else 600)
            if url.path.startswith("/font/") and url.path.endswith(".woff2"):
                return self.send_file(FONT_FILES.get(url.path[6:-6]), "font/woff2")
            if not self.authorized():
                return self.send_json({"error": "forbidden"}, 403)
            if url.path == "/api/state":
                state.last_poll = time.time()
                return self.send_json(state.snapshot())
            if url.path == "/api/catalog":
                with state.lock:
                    items = [e for e in state.catalog]
                return self.send_json({"items": items, "names": eng.CATEGORY_NAMES, "auto": list(eng.AUTO_CATEGORIES),
                                       "ranks": eng.RANK_NAMES})
            if url.path == "/api/craft":
                return self.send_json(state.craft())
            if url.path == "/api/yield":
                return self.send_json(state.item_yield())
            if url.path == "/api/item_stats":
                q = parse_qs(url.query)
                one = lambda k: (q.get(k) or [None])[0]
                return self.send_json(state.item_stats(one("id") or "", one("q"), one("p")))
            if url.path == "/api/suggest":
                q = parse_qs(url.query).get("q", [""])[0]
                return self.send_json({"items": state.suggest(q)})
            self.send_json({"error": "not found"}, 404)

        def do_POST(self):
            if not self.authorized():
                return self.send_json({"error": "forbidden"}, 403)
            path = urlparse(self.path).path
            data = self.body_json()
            if path == "/api/purchases/add":
                ok, msg = state.buy(data.get("deal_id"), data.get("paid"))
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/purchases/update":
                ok, msg = state.update_purchase(data)
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/purchases/remove":
                ok, msg = state.remove_purchase(data.get("id"))
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/telegram/test":
                cfg = dict(state.cfg)
                for k in ("telegram_token", "telegram_chat_id"):
                    if data.get(k):
                        cfg[k] = str(data[k]).strip()
                if not (cfg.get("telegram_token") and cfg.get("telegram_chat_id")):
                    return self.send_json({"ok": False, "message": "Сначала впиши токен бота и Chat ID"})
                ok, msg = send_telegram(cfg, "✅ STALZONE Трекер: уведомления работают. Сюда будут приходить находки.")
                return self.send_json({"ok": ok, "message": "Сообщение отправлено — проверь Telegram" if ok else msg})
            if path == "/api/access/enter":
                info = state.access.check(data.get("code", ""))
                if info["ok"] and info.get("mode") == "code":
                    cfg = dict(state.cfg, access_code=re.sub(r"\s+", "", str(data.get("code", ""))))
                    with state.lock:
                        state.cfg = cfg
                    save_settings(cfg)
                    state.add_log(f"Доступ открыт: {info['name']}, срок — {info['expires_text']}")
                    return self.send_json({"ok": True, "message": f"Доступ открыт, {info['name']}"})
                return self.send_json({"ok": False, "message": info.get("reason") or "Код не нужен"})
            if path == "/api/access/owner_key":
                ok, msg = state.access.create_owner_key()
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/access/issue":
                own = {"id": state.cfg.get("client_id"), "secret": state.cfg.get("client_secret"),
                       "token": state.cfg.get("app_token")}
                ok, msg, code = state.access.issue(data.get("name"), data.get("machine"), data.get("days"),
                                                   share=bool(data.get("share")), creds=own, seats=data.get("seats") or 1,
                                                   server=state.cfg.get("server_url") or None)
                return self.send_json({"ok": ok, "message": msg, "code": code})
            if path == "/api/access/free_seats":
                ok, msg = state.access.free_seats(data.get("id"))
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/server/funnel":
                ok, msg, link = state.open_funnel()
                return self.send_json({"ok": ok, "message": msg, "link": link})
            if path == "/api/access/renew":
                ok, msg, code = state.access.renew(data.get("id"), data.get("days") or 30,
                                                   server=state.cfg.get("server_url") or None)
                return self.send_json({"ok": ok, "message": msg, "code": code})
            if path == "/api/access/block":
                ok, msg = state.access.set_blocked(data.get("id"), bool(data.get("blocked")))
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/server/test":
                ok, msg = state.test_public_url()
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/access/refresh":
                threading.Thread(target=state.access.refresh_revoked, kwargs={"force": True}, daemon=True).start()
                return self.send_json({"ok": True})
            if path == "/api/start":
                access = state.access.check()
                if not access["ok"]:
                    return self.send_json({"ok": False, "message": access.get("reason", "Нет доступа")})
                if not state.snapshot()["configured"]:
                    return self.send_json({"ok": False, "message": "Сначала вставь Client ID и Client Secret "
                                                                   "в настройках — или включи демо-режим."})
                if (not state.cfg.get("watch") and not eng.auto_categories(state.cfg)
                        and not state.subscriber_server()):
                    return self.send_json({"ok": False, "message": "Добавь предметы во вкладке «Предметы» "
                                                                   "или включи «Все артефакты»."})
                state.start()
                return self.send_json({"ok": True})
            if path == "/api/stop":
                state.stop()
                return self.send_json({"ok": True})
            if path == "/api/settings":
                ok, msg = state.update_settings(data)
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/deals/remove":
                with state.lock:
                    state.deals = [d for d in state.deals if d["id"] != data.get("id")]
                state.save_deals()
                return self.send_json({"ok": True})
            if path == "/api/craft/fetch":
                ok, msg = state.craft_fetch(bool(data.get("only_available", True)))
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/watch/remove":
                ok, msg = state.remove_watch_ids(data.get("ids") or [])
                return self.send_json({"ok": ok, "message": msg})
            if path == "/api/deals/clear":
                with state.lock:
                    state.deals = []
                    state.near = {}
                state.save_deals()
                return self.send_json({"ok": True})
            if path == "/api/open_data":
                return self.send_json({"ok": open_folder(DATA_DIR)})
            if path == "/api/update/check":
                threading.Thread(target=state.updater.check, daemon=True).start()
                return self.send_json({"ok": True})
            if path == "/api/update/apply":
                threading.Thread(target=state.updater.apply, daemon=True).start()
                return self.send_json({"ok": True})
            if path == "/api/open":
                url = OPEN_LINKS.get(data.get("link"))
                extra = str(data.get("url") or "")
                if not url and extra.startswith(("https://login.tailscale.com/", TAILSCALE_DOWNLOAD)):
                    url = extra   # ссылка, которую попросил открыть Tailscale (разрешить Funnel, скачать)
                if url:
                    webbrowser.open(url)
                return self.send_json({"ok": bool(url)})
            self.send_json({"error": "not found"}, 404)

    return Handler


def start_server(state):
    token = secrets.token_urlsafe(24)
    handler = make_handler(state, token)
    for port in range(8765, 8800):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    else:
        raise RuntimeError("Не нашёл свободный порт 8765–8799")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def main():
    state = State()
    server, port = start_server(state)
    url = f"http://127.0.0.1:{port}/"
    autostarted = "--autostart" in sys.argv

    def boot():
        state.load_names()
        if state.cfg.get("autorun_search"):   # «начинать поиск сразу» — и при обычном запуске, и при автозапуске
            state.start()
    threading.Thread(target=boot, daemon=True).start()
    threading.Thread(target=state.watchdog, daemon=True).start()
    if state.cfg.get("autostart"):
        set_autostart(True)   # программу могли перенести в другую папку — обновим путь
    windowed = False
    try:
        import webview  # окно приложения (pip install pywebview)
        window = webview.create_window("STALZONE Трекер", url, width=1320, height=840,
                                       min_size=(1080, 680), background_color="#0d1012",
                                       minimized=autostarted)
        state.exit_hook = window.destroy   # чтобы обновление могло закрыть окно
        webview.start()
        windowed = True
    except Exception as e:  # нет pywebview или окно не открылось (например, нет WebView2) — откроем браузер
        state.add_log(f"Отдельное окно не открылось ({type(e).__name__}) — открываю в браузере")
    if not windowed and not state.exit_requested.is_set():
        print(f"Интерфейс открыт в браузере: {url}", flush=True)
        print("Для отдельного окна установи: pip install pywebview", flush=True)
        webbrowser.open(url)
        try:
            while not state.exit_requested.is_set():  # вкладку закрыли больше чем на 2 минуты — выходим
                time.sleep(2)
                if time.time() - state.last_poll > 120:
                    break
        except KeyboardInterrupt:
            pass
    state.stop()
    state.save_deals()
    server.shutdown()
    if state.exit_requested.is_set():
        os._exit(0)   # обновление ждёт, пока файл программы освободится — выходим сразу, не дожидаясь сети


# ------------------------------------ Интерфейс ------------------------------------


if __name__ == "__main__":
    main()
