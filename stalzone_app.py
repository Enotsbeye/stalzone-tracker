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

import json
import logging
import os
import re
import secrets
import shutil
import statistics
import subprocess
import sys
import threading
import time
import webbrowser
import zipfile
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

try:
    import requests
    import stalzone_tracker as eng
except ImportError as e:
    print("Ошибка запуска:", e)
    print("Нужен модуль requests (pip install requests) и файл stalzone_tracker.py рядом.")
    input("Нажми Enter, чтобы закрыть…")
    sys.exit(1)

APP_NAME = "STALZONE Tracker"
APP_VERSION = "1.7"
# Откуда брать обновления: репозиторий GitHub «владелец/имя» с выпусками (Releases).
# В настройках можно указать другой. Пусто — обновления не проверяются.
UPDATE_REPO = "Enotsbeye/stalzone-tracker"
EXE_ASSET = "STALZONE-Tracker.exe"      # файлы в выпуске: программа для Windows
SRC_ASSET = "stalzone_source.zip"       # и исходники — для запуска через Python
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
SETTINGS_VERSION = 2
DEFAULTS = dict(eng.CONFIG, settings_version=SETTINGS_VERSION)
OPEN_LINKS = {
    "api_bot": "https://t.me/stalzone_api_bot",
    "docs": "https://eapi.stalzone.net/overview.html",
    "botfather": "https://t.me/BotFather",
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


def _spawn_detached(cmd, **kw):
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

    def check(self):
        repo = self.repo()
        if not REPO_RE.match(repo):
            self._set("off", "Обновления не настроены: укажи репозиторий GitHub в настройках")
            return
        self._set("checking", "Проверяю обновления…")
        try:
            r = requests.get(f"{GITHUB_API}/repos/{repo}/releases/latest", timeout=20,
                             headers={"Accept": "application/vnd.github+json"})
        except requests.RequestException as e:
            self._set("error", f"GitHub не ответил ({type(e).__name__})")
            return
        if r.status_code == 404:
            self._set("latest", "В репозитории пока нет выпусков")
            return
        if r.status_code != 200:
            self._set("error", f"GitHub ответил {r.status_code}")
            return
        try:
            rel = r.json()
            assets = {a["name"]: a for a in rel.get("assets", [])}
            version = str(rel.get("tag_name") or "").lstrip("vV")
        except (ValueError, KeyError, TypeError, AttributeError):
            self._set("error", "GitHub прислал непонятный ответ")
            return
        info = {"version": version, "notes": str(rel.get("body") or "")[:1500], "url": rel.get("html_url"),
                "exe": assets.get(EXE_ASSET), "src": assets.get(SRC_ASSET)}
        needed = info["exe"] if getattr(sys, "frozen", False) else info["src"]
        with self.lock:
            self.info = info
        if parse_version(version) > parse_version(APP_VERSION) and needed:
            self._set("available", f"Доступна версия {version} (у тебя {APP_VERSION})")
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
        """Из архива — stalzone_app.py и stalzone_tracker.py рядом с программой. Сначала проверяем,
        что оба файла есть и это корректный Python, потом подменяем (каждый — одним действием)."""
        wanted = {"stalzone_app.py", "stalzone_tracker.py"}
        found = {}
        with zipfile.ZipFile(zip_path) as z:
            for name in z.namelist():
                base = name.rsplit("/", 1)[-1]
                if base in wanted:
                    found[base] = z.read(name)
        if set(found) != wanted:
            raise OSError("в архиве нет файлов программы")
        for base, data in found.items():
            compile(data.decode("utf-8"), base, "exec")   # битый файл не ставим
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


def minutes_since(iso):
    try:
        return (datetime.now(timezone.utc) - eng.parse_time(iso)).total_seconds() / 60
    except (TypeError, ValueError):
        return None


# ------------------------------ Фоновая проверка ------------------------------
class Worker(threading.Thread):
    """Проверяет аукцион и передаёт находки в общее состояние через emit()."""

    def __init__(self, cfg, emit, api_factory=None, shown=()):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.emit = emit
        self.stop_event = threading.Event()
        self.api_factory = api_factory or eng.Api
        self.db = None
        self.initial_shown = set(shown)   # что уже есть в таблице (например, восстановлено после перезапуска)

    def stop(self):
        self.stop_event.set()

    def telegram(self, text):
        token, chat = self.cfg.get("telegram_token"), self.cfg.get("telegram_chat_id")
        if not (token and chat):
            return
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text}, timeout=20)
        except requests.RequestException as e:
            self.emit("log", f"Telegram не ответил: {e}")

    def run(self):
        cfg = self.cfg
        try:
            api = self.api_factory(cfg)
            names = eng.load_listing(cfg["region"])
            items, auto = eng.watch_items(cfg, names)
            if not items:
                self.emit("error", "Список предметов пуст или названия не найдены — проверь вкладку «Предметы».")
                return
            self.emit("log", eng.watching_line(items, auto))
            seen = eng.load_seen()   # о каких лотах уже сообщали (звук, Telegram) — в прошлых запусках тоже
            shown = set(self.initial_shown)  # что уже есть в таблице — второй раз не добавляем
            known = set()
            db = eng.MarketDB(keep_days=cfg.get("history_keep_days", 14))  # своя база сделок, market.db
            self.db = db
            self.emit("log", eng.db_line(db.stats()))
            # рынок, формат цен, строка рынка в журнале; автодобавленные артефакты — без строки на каждый
            scanner = eng.Scanner(api, cfg, quiet=auto, db=db)
            first_pass = True
            while not self.stop_event.is_set():
                started = time.time()
                fresh_ages, found = [], [0]

                def on_progress(i, item_id, name):
                    self.emit("progress", {"text": f"Проверяю {name}", "done": i, "total": len(items)})

                def on_item(item_id, name, result):
                    if isinstance(result, Exception):  # один сбойный предмет не останавливает проход
                        self.emit("log", f"{name}: ошибка — {result}")
                        return
                    lots, deals, bids = result
                    if lots is not None:  # лоты получили — отметим находки, которых больше нет
                        self.emit("lots_seen", {"item_id": item_id, "keys": list(lots.keys())})
                    for key, lot in (lots or {}).items():  # замер реальной задержки API
                        if key not in known:
                            known.add(key)
                            age = minutes_since(lot.get("startTime"))
                            if not first_pass and age is not None and 0 <= age <= 120:
                                fresh_ages.append(age)
                    # в таблицу — всё найденное в этом запуске; звук и Telegram — только о новом
                    for kind, items_found in (("buyout", deals), ("bid", bids)):
                        for d in items_found:
                            key = ("bid|" if kind == "bid" else "") + eng.lot_key(item_id, d["lot"])
                            if key not in shown:
                                shown.add(key)
                                found[0] += 1
                                self.deal(item_id, name, d, kind, key, notify=key not in seen)
                                seen.add(key)

                # сеть — параллельно, обработка — по порядку (см. eng.scan_pass)
                eng.scan_pass(scanner, items, on_item, self.stop_event.is_set, on_progress)
                eng.save_seen(seen)
                if first_pass and not self.stop_event.is_set() and scanner.summary():
                    self.emit("log", scanner.summary())
                self.emit("pass", {"time": time.time(), "found": found[0], "took": time.time() - started,
                                   "delay": statistics.median(fresh_ages) if fresh_ages else None,
                                   "total": len(items), "db": db.stats()})
                first_pass = False
                pause = max(5, cfg["poll_minutes"] * 60 - (time.time() - started))
                self.stop_event.wait(pause)
        except eng.AuthError as e:
            self.emit("error", str(e))
        except Exception as e:
            self.emit("error", f"Не удалось запустить: {e}")
        finally:
            if self.db is not None:
                self.db.close()
            self.emit("stopped", None)

    def deal(self, item_id, name, d, kind, key, notify=True):
        lot = d["lot"]
        b = d["bucket"]
        if kind == "bid":
            unit, profit = d["need"] / d["amount"], d["profit_now"]
            text = eng.bid_message(name, d, self.cfg["min_profit"])
        else:
            unit, profit = d["unit"], d["profit"]
            text = eng.deal_message(name, d)
        cost = unit * d["amount"]
        grade = d.get("grade")
        self.emit("deal", {
            "item_id": item_id, "name": name, "kind": kind,
            "key": key, "lot_key": eng.lot_key(item_id, lot), "gone": False,
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
            "max_bid": d.get("max_bid"), "has_bids": d.get("has_bids"),
            "text": text, "notify": notify,
        })
        if notify:
            self.telegram(text)


# --------------------------------- Состояние ---------------------------------
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
        self.worker = None
        self.api_factory = api_factory
        self.status = {"running": False, "starting": False, "progress": None, "last_pass": None,
                       "delay": None, "found_total": 0, "took": None, "error": None, "error_id": 0,
                       "db": None}
        self.last_poll = time.time()
        self.updater = Updater(self)
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

    def save_deals(self):
        with self.lock:
            deals = list(self.deals)
        with self.file_lock:
            try:
                write_json(DEALS_FILE, deals)
            except OSError:
                pass

    def emit(self, kind, data):
        with self.lock:
            if kind == "deal":
                data["id"] = self.next_id
                data["found"] = time.time()
                self.next_id += 1
                self.deals.insert(0, data)
                del self.deals[400:]
                self.status["found_total"] += 1
            elif kind == "progress":
                self.status["progress"] = data
                self.status["starting"] = False
            elif kind == "pass":
                self.status.update(last_pass=data["time"], took=data["took"], progress=None)
                if data["delay"] is not None:
                    self.status["delay"] = data["delay"]
                if data.get("db"):
                    self.status["db"] = data["db"]
            elif kind == "error":
                self.status["error"] = data
                self.status["error_id"] += 1
            elif kind == "lots_seen":  # лота больше нет на аукционе — его купили или сняли
                present = set(data["keys"])
                for d in self.deals:
                    if d.get("item_id") == data["item_id"] and d.get("lot_key") and d["lot_key"] not in present:
                        d["gone"] = True
            elif kind == "stopped":
                self.status.update(running=False, starting=False, progress=None)
        if kind == "log":
            self.add_log(data)
        elif kind == "deal":
            self.add_log(f"Найдено: {data['name']} — прибыль ~{eng.fmt_rub(data['profit'])}")
        elif kind == "error":
            self.add_log("ОШИБКА: " + data)
        elif kind in ("pass", "stopped"):
            self.save_deals()   # находки на диск после каждой проверки — закрытие окна их не сотрёт

    def load_names(self):
        try:
            names = eng.load_listing(self.cfg["region"])
            self.names = sorted(set(names.values()), key=str.lower)
            self.artifacts = len(eng.load_artifacts(self.cfg["region"]))
            self.add_log(f"Справочник предметов загружен: {len(self.names)} шт., из них артефактов: "
                         f"{self.artifacts}")
        except Exception as e:
            self.add_log(f"Справочник не загрузился ({e}) — названия вводи точно как в игре")
        stats = eng.MarketDB.quick_stats()
        if stats:
            with self.lock:
                self.status["db"] = stats
        if self.updater.repo():
            self.updater.check()    # при запуске сами смотрим, нет ли новой версии

    def start(self):
        with self.lock:
            if self.worker and self.worker.is_alive():
                return
            self.status.update(running=True, starting=True, error=None)
            self.worker = Worker(dict(self.cfg), self.emit, self.api_factory,
                                 shown={d["key"] for d in self.deals if d.get("key")})
            self.worker.start()
        self.add_log("Трекер запущен" + (" (ДЕМО-режим)" if self.cfg["base_url"] == DEMO_URL else ""))

    def stop(self):
        w = self.worker
        if w and w.is_alive():
            w.stop()
            self.add_log("Останавливаю…")

    def restart_if_running(self):
        w = self.worker
        if not (w and w.is_alive()):
            return

        def go():
            w.stop()
            w.join(timeout=90)
            self.start()
        threading.Thread(target=go, daemon=True).start()

    def snapshot(self):
        with self.lock:
            cfg = dict(self.cfg)
            demo = cfg.get("base_url", "").rstrip("/") == DEMO_URL
            has_keys = bool(cfg.get("client_id") and cfg.get("client_secret"))
            return {
                "status": dict(self.status),
                "deals": list(self.deals),
                "log": list(self.log)[-200:],
                "settings": cfg,
                # для демо ключи встроены, поэтому демо-режим тоже считается «настроенным»
                "configured": bool(demo or has_keys or cfg.get("app_token")),
                "has_keys": has_keys,
                "demo": demo,
                "artifacts": self.artifacts,
                "version": APP_VERSION,
                "data_dir": DATA_DIR,
                "update": self.updater.snapshot(),
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
                cfg["poll_minutes"] = min(60.0, max(0.5, float(data["poll_minutes"])))
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
            if "update_repo" in data:
                repo = str(data["update_repo"] or "").strip().strip("/")
                repo = re.sub(r"^https?://github\.com/", "", repo).strip("/")   # можно вставить и ссылку
                if repo and not REPO_RE.match(repo):
                    return False, "Репозиторий для обновлений пишется так: владелец/имя (например, ivan/stalzone-tracker)."
                cfg["update_repo"] = repo
            if "demo" in data:
                cfg["base_url"] = DEMO_URL if data["demo"] else PROD_URL
            if "watch" in data:
                cfg["watch"] = [str(w).strip() for w in data["watch"] if str(w).strip()][:60]
        except (TypeError, ValueError):
            return False, "Проверь числа в настройках — там должны быть только цифры."
        with self.lock:
            self.cfg = cfg
        save_settings(cfg)
        self.restart_if_running()
        return True, "Сохранено"

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
            if not self.authorized():
                return self.send_json({"error": "forbidden"}, 403)
            if url.path == "/api/state":
                state.last_poll = time.time()
                return self.send_json(state.snapshot())
            if url.path == "/api/suggest":
                q = parse_qs(url.query).get("q", [""])[0]
                return self.send_json({"items": state.suggest(q)})
            self.send_json({"error": "not found"}, 404)

        def do_POST(self):
            if not self.authorized():
                return self.send_json({"error": "forbidden"}, 403)
            path = urlparse(self.path).path
            data = self.body_json()
            if path == "/api/start":
                if not state.snapshot()["configured"]:
                    return self.send_json({"ok": False, "message": "Сначала вставь Client ID и Client Secret "
                                                                   "в настройках — или включи демо-режим."})
                if not state.cfg.get("watch") and not state.cfg.get("all_artifacts"):
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
            if path == "/api/deals/clear":
                with state.lock:
                    state.deals = []
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
    threading.Thread(target=state.load_names, daemon=True).start()
    windowed = False
    try:
        import webview  # окно приложения (pip install pywebview)
        window = webview.create_window("STALZONE Трекер", url, width=1320, height=840,
                                       min_size=(1080, 680), background_color="#0d1012")
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
UI_HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>STALZONE Трекер</title>
<style>
:root{
  --bg:#0d1012; --panel:#14191c; --panel2:#1a2024; --raise:#20272c; --line:#273036; --line2:#323c43;
  --text:#e7ece9; --muted:#8c9893; --dim:#5e6a65;
  --accent:#e8b84a; --accent-ink:#1b1505; --good:#5fd67a; --good-bg:rgba(95,214,122,.12);
  --bad:#ff6b5e; --bad-bg:rgba(255,107,94,.12); --blue:#5fa8ff; --blue-bg:rgba(95,168,255,.13);
  --q0:#b9c9b9; --q1:#5fd67a; --q2:#5fa8ff; --q3:#d46bff; --q4:#ff6b5e; --q5:#ffb84d;
  --r:12px; --font:"Segoe UI Variable Text","Segoe UI",Inter,system-ui,-apple-system,sans-serif;
}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);font:14px/1.45 var(--font);-webkit-font-smoothing:antialiased;overflow:hidden}
button,input,select{font:inherit;color:inherit}
.num{font-variant-numeric:tabular-nums}
.app{display:grid;grid-template-columns:232px 1fr;height:100vh}

/* --- боковая панель --- */
.side{background:var(--panel);border-right:1px solid var(--line);display:flex;flex-direction:column;padding:18px 14px}
.brand{display:flex;gap:11px;align-items:center;padding:4px 6px 20px}
.logo{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(140deg,#f2c25a,#b9851d);color:var(--accent-ink);font-weight:800;font-size:18px;box-shadow:0 6px 18px rgba(232,184,74,.25)}
.brand b{display:block;letter-spacing:.14em;font-size:13px}
.brand span{color:var(--muted);font-size:12px}
.nav{display:flex;flex-direction:column;gap:3px}
.nav button{all:unset;cursor:pointer;display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:9px;color:var(--muted);font-weight:500}
.nav button:hover{background:var(--panel2);color:var(--text)}
.nav button.on{background:var(--raise);color:var(--text);box-shadow:inset 3px 0 0 var(--accent)}
.nav svg{width:18px;height:18px;flex:none}
.nav .cnt{margin-left:auto;background:var(--accent);color:var(--accent-ink);font-size:11px;font-weight:700;border-radius:20px;padding:1px 7px;min-width:20px;text-align:center}
.nav .cnt:empty{display:none}
.side-foot{margin-top:auto;display:flex;flex-direction:column;gap:10px}
.run{all:unset;cursor:pointer;text-align:center;padding:12px;border-radius:10px;font-weight:700;background:var(--accent);color:var(--accent-ink);transition:filter .15s}
.run:hover{filter:brightness(1.08)}
.run.stop{background:var(--raise);color:var(--text);box-shadow:inset 0 0 0 1px var(--line2)}
.run[disabled]{opacity:.6;cursor:default}
.mode{font-size:12px;color:var(--muted);text-align:center}
.mode b{color:var(--accent)}

/* --- основная часть --- */
main{display:flex;flex-direction:column;min-width:0;height:100vh}
.top{display:flex;align-items:center;gap:14px;padding:18px 26px 6px}
.top h1{font-size:21px;margin:0;font-weight:650;letter-spacing:-.01em}
.state{margin-left:auto;display:flex;align-items:center;gap:9px;font-size:13px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:30px;padding:7px 14px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--dim)}
.dot.live{background:var(--good);box-shadow:0 0 0 0 rgba(95,214,122,.6);animation:pulse 1.8s infinite}
@keyframes pulse{70%{box-shadow:0 0 0 9px rgba(95,214,122,0)}100%{box-shadow:0 0 0 0 rgba(95,214,122,0)}}
.view{display:none;flex:1;min-height:0;padding:12px 26px 22px;overflow:auto}
.view.on{display:flex;flex-direction:column}

.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:14px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:13px 16px}
.kpi .l{font-size:12px;color:var(--muted)}
.kpi .v{font-size:22px;font-weight:650;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kpi .s{font-size:12px;color:var(--dim);margin-top:1px}
.kpi .v.good{color:var(--good)}
.bar{height:4px;background:var(--line);border-radius:4px;margin-top:9px;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:var(--accent);transition:width .4s}

.toolbar{display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.seg{display:flex;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:3px}
.seg button{all:unset;cursor:pointer;padding:6px 13px;border-radius:7px;color:var(--muted);font-weight:500;font-size:13px}
.seg button.on{background:var(--raise);color:var(--text)}
.field{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 12px;outline:none;min-width:0}
.field:focus{border-color:var(--accent)}
.search{width:240px}
.spacer{flex:1}
.btn{all:unset;cursor:pointer;padding:8px 14px;border-radius:9px;background:var(--panel);border:1px solid var(--line);font-size:13px;font-weight:550;color:var(--text);white-space:nowrap}
.btn:hover{border-color:var(--line2);background:var(--panel2)}
.btn.primary{background:var(--accent);color:var(--accent-ink);border-color:transparent}
.btn.ghost{background:transparent}

/* таблица */
.tablewrap{flex:1;min-height:220px;background:var(--panel);border:1px solid var(--line);border-radius:var(--r);overflow:auto}
table{width:100%;border-collapse:collapse}
th{position:sticky;top:0;background:var(--panel);z-index:1;text-align:right;font-size:12px;font-weight:600;color:var(--muted);padding:11px 14px;border-bottom:1px solid var(--line);white-space:nowrap;cursor:pointer;user-select:none}
th:first-child,td:first-child{text-align:left}
th.sorted{color:var(--text)}
td{padding:11px 14px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
tr.lot{cursor:pointer}
tr.lot:hover td{background:var(--panel2)}
tr.lot.sel td{background:var(--raise)}
tr.lot.new td:first-child{box-shadow:inset 3px 0 0 var(--accent)}
tr.lot.old td{opacity:.45}
.item{display:flex;flex-direction:column;gap:3px}
.item .n{font-weight:600;color:var(--text)}
.tags{display:flex;gap:6px;align-items:center}
.tag{font-size:11px;font-weight:650;padding:2px 7px;border-radius:5px;background:var(--raise);color:var(--muted)}
.tag.buy{background:var(--good-bg);color:var(--good)}
.tag.bid{background:var(--blue-bg);color:var(--blue)}
.tag.stale{background:rgba(232,184,74,.14);color:var(--accent)}
.note.warn{background:rgba(232,184,74,.1);color:#f1d08a;border:1px solid rgba(232,184,74,.3)}
.q{font-size:11px;font-weight:650}
.profit{color:var(--good);font-weight:700}
.pct{display:inline-block;font-size:12px;font-weight:650;padding:2px 8px;border-radius:20px;background:var(--good-bg);color:var(--good)}
.muted{color:var(--muted)}
.empty{flex:1;display:grid;place-items:center;text-align:center;color:var(--muted);padding:40px}
.empty h3{color:var(--text);margin:14px 0 6px;font-size:17px}
.radar{width:86px;height:86px;border-radius:50%;margin:auto;border:1px solid var(--line2);position:relative;overflow:hidden;background:radial-gradient(circle,var(--panel2) 0 30%,transparent 31%),repeating-radial-gradient(circle,transparent 0 13px,var(--line) 14px 15px)}
.radar:after{content:"";position:absolute;inset:0;background:conic-gradient(from 0deg,rgba(232,184,74,.35),transparent 70deg);animation:spin 3s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* карточка подключения */
.onboard{background:linear-gradient(180deg,rgba(232,184,74,.08),transparent),var(--panel);border:1px solid rgba(232,184,74,.35);border-radius:var(--r);padding:18px 20px;margin-bottom:14px}
.onboard h3{margin:0 0 4px;font-size:16px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}
.step{background:var(--panel2);border-radius:10px;padding:12px 14px}
.step b{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--accent);color:var(--accent-ink);font-size:12px;margin-right:6px}
.step p{margin:6px 0 10px;color:var(--muted);font-size:13px}

/* плашка демо-режима */
.demo-note{display:flex;align-items:center;gap:14px;background:linear-gradient(90deg,rgba(232,184,74,.13),rgba(232,184,74,.03)),var(--panel);border:1px solid rgba(232,184,74,.45);border-radius:var(--r);padding:12px 16px;margin-bottom:14px}
.demo-note[hidden]{display:none}
.demo-note .ic{flex:none;width:30px;height:30px;border-radius:8px;display:grid;place-items:center;background:var(--accent);color:var(--accent-ink);font-weight:800}
.demo-note .tx{flex:1;min-width:0}
.demo-note .tx div{color:var(--muted);font-size:13px;margin-top:1px}
.demo-note .tx div b{color:var(--accent);font-weight:600}
.upd-note{background:linear-gradient(90deg,rgba(95,214,122,.14),rgba(95,214,122,.03)),var(--panel);border-color:rgba(95,214,122,.45)}
.upd-note .ic{background:var(--good);color:#06210f}
.overlay{position:fixed;inset:0;z-index:50;display:grid;place-items:center;background:rgba(13,16,18,.92);text-align:center}
.overlay[hidden]{display:none}
.overlay h2{margin:14px 0 6px}
.row.flash{animation:flash 1.8s ease}
@keyframes flash{0%,55%{background:rgba(232,184,74,.16)}100%{background:transparent}}

/* боковая карточка сделки */
.drawer{position:fixed;top:0;right:0;height:100vh;width:380px;background:var(--panel);border-left:1px solid var(--line);transform:translateX(100%);transition:transform .22s ease;padding:22px;overflow:auto;z-index:20;box-shadow:-20px 0 50px rgba(0,0,0,.35)}
.drawer.on{transform:none}
.drawer h2{margin:6px 0 2px;font-size:19px}
.big{font-size:32px;font-weight:750;color:var(--good);margin:16px 0 2px}
.calc{margin:16px 0;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.calc div{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 14px;border-bottom:1px solid var(--line)}
.calc small{display:block;color:var(--dim);font-size:12px}
.calc div:last-child{border-bottom:0;background:var(--good-bg);font-weight:700;color:var(--good)}
.calc span:first-child{color:var(--muted)}
.facts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0}
.fact{background:var(--panel2);border-radius:10px;padding:10px 12px}
.fact .l{font-size:11px;color:var(--muted)}
.fact .v{font-weight:600;margin-top:2px}
.note{font-size:13px;color:var(--muted);background:var(--panel2);border-radius:10px;padding:11px 13px;margin:12px 0}
.close{all:unset;cursor:pointer;float:right;color:var(--muted);font-size:20px;line-height:1}
.actions{display:flex;gap:8px;margin-top:8px}

/* предметы */
.grid2{display:grid;grid-template-columns:1.1fr 1fr;gap:16px;align-items:start}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:18px}
.card h3{margin:0 0 4px;font-size:15px}
.card .sub{color:var(--muted);font-size:13px;margin-bottom:14px}
.combo{position:relative}
.combo .field{width:100%}
.dropdown{position:absolute;left:0;right:0;top:calc(100% + 4px);background:var(--raise);border:1px solid var(--line2);border-radius:10px;max-height:260px;overflow:auto;z-index:5;display:none;box-shadow:0 12px 30px rgba(0,0,0,.4)}
.dropdown.on{display:block}
.dropdown div{padding:9px 12px;cursor:pointer}
.dropdown div:hover,.dropdown div.act{background:var(--line)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.chip{display:flex;align-items:center;gap:8px;background:var(--panel2);border:1px solid var(--line);border-radius:30px;padding:6px 8px 6px 13px}
.chip button{all:unset;cursor:pointer;width:20px;height:20px;border-radius:50%;display:grid;place-items:center;color:var(--muted)}
.chip button:hover{background:var(--bad-bg);color:var(--bad)}
.presets{display:flex;flex-direction:column;gap:10px}
.preset{all:unset;cursor:pointer;background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.preset:hover{border-color:var(--line2)}
.preset b{display:block}
.preset span{color:var(--muted);font-size:12.5px}
.col{display:flex;flex-direction:column;gap:16px;min-width:0}
.art-head{display:flex;gap:16px;align-items:flex-start;justify-content:space-between}
.art-head .switch{flex:none;margin-top:2px}

/* настройки */
.form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start}
.row{display:grid;grid-template-columns:1fr 150px;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}
.row.wide{grid-template-columns:1fr}
.row label{font-weight:550}
.row small{display:block;color:var(--muted);font-size:12px;font-weight:400}
.row .field{width:100%}
.switch{position:relative;width:42px;height:24px;justify-self:end}
.switch input{opacity:0;width:0;height:0}
.switch i{position:absolute;inset:0;background:var(--line2);border-radius:20px;cursor:pointer;transition:.2s}
.switch i:before{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.2s}
.switch input:checked+i{background:var(--accent)}
.switch input:checked+i:before{transform:translateX(18px)}
.linkrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.savebar{position:sticky;bottom:-22px;display:flex;justify-content:flex-end;gap:10px;margin-top:16px;padding:14px 0 6px;background:linear-gradient(rgba(13,16,18,0),var(--bg) 35%)}

/* журнал */
.log{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;font:12.5px/1.6 Consolas,"Cascadia Mono",monospace;overflow:auto;white-space:pre-wrap}
.log .t{color:var(--dim)}
.log .e{color:var(--bad)}
.log .f{color:var(--good)}
.log .w{color:var(--accent)}

.toast{position:fixed;bottom:22px;left:50%;transform:translate(-50%,20px);background:var(--raise);border:1px solid var(--line2);padding:11px 18px;border-radius:10px;opacity:0;transition:.25s;pointer-events:none;z-index:30}
.toast.on{opacity:1;transform:translate(-50%,0)}
.toast.err{border-color:rgba(255,107,94,.5);color:#ffb3ab}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:var(--line2);border-radius:10px;border:2px solid var(--panel)}
@media (max-width:1180px){.kpis{grid-template-columns:repeat(2,1fr)}.steps{grid-template-columns:1fr}.form,.grid2{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="app">
  <aside class="side">
    <div class="brand"><div class="logo">◈</div><div><b>STALZONE</b><span>трекер аукциона</span></div></div>
    <nav class="nav">
      <button data-view="deals" class="on"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>Выгодные лоты<span class="cnt" id="cntDeals"></span></button>
      <button data-view="items"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9h10M7 13h10M7 17h6"/></svg>Предметы<span class="cnt" id="cntItems" style="background:var(--raise);color:var(--muted)"></span></button>
      <button data-view="settings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.6 1.6 0 00-1.8-.3 1.6 1.6 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.6 1.6 0 00-1-1.5 1.6 1.6 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.6 1.6 0 00.3-1.8 1.6 1.6 0 00-1.5-1H3a2 2 0 110-4h.1a1.6 1.6 0 001.5-1 1.6 1.6 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.6 1.6 0 001.8.3H9a1.6 1.6 0 001-1.5V3a2 2 0 114 0v.1a1.6 1.6 0 001 1.5 1.6 1.6 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.6 1.6 0 00-.3 1.8V9a1.6 1.6 0 001.5 1H21a2 2 0 110 4h-.1a1.6 1.6 0 00-1.5 1z"/></svg>Настройки</button>
      <button data-view="log"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h16M4 12h16M4 18h10"/></svg>Журнал</button>
    </nav>
    <div class="side-foot">
      <button class="run" id="runBtn">▶ Запустить</button>
      <div class="mode" id="modeLbl">Регион RU</div>
    </div>
  </aside>

  <main>
    <header class="top">
      <h1 id="viewTitle">Выгодные лоты</h1>
      <div class="state"><span class="dot" id="dot"></span><span id="stateTxt">Остановлен</span></div>
    </header>

    <section class="view on" id="view-deals">
      <div class="demo-note upd-note" id="updNote" hidden>
        <div class="ic">↑</div>
        <div class="tx"><b id="updTitle">Доступна новая версия</b><div id="updSub"></div></div>
        <button class="btn primary" id="updBtn">Обновить</button>
      </div>
      <div class="demo-note" id="demoNote" hidden>
        <div class="ic">!</div>
        <div class="tx"><b>Демо-режим: тестовые данные EXBO, а не настоящий аукцион</b><div id="demoNoteSub"></div></div>
        <button class="btn" id="demoOffBtn">Выключить в настройках</button>
      </div>
      <div class="onboard" id="onboard" hidden>
        <h3>Подключи доступ к API — это займёт пару минут</h3>
        <div class="muted">Без ключей трекер не видит аукцион. Ключи выдаёт сама EXBO, бесплатно.</div>
        <div class="steps">
          <div class="step"><b>1</b>Подай заявку<p>Отправь /newapp боту EXBO и войди через свой аккаунт.</p><button class="btn" data-open="api_bot">Открыть @stalzone_api_bot</button></div>
          <div class="step"><b>2</b>Вставь ключи<p>После одобрения бот пришлёт Client ID и Client Secret.</p><button class="btn" data-goto="settings">Перейти в настройки</button></div>
          <div class="step"><b>3</b>Проверь на демо<p>Пока ждёшь одобрения — включи демо, ключи для него уже встроены.</p><button class="btn" id="demoOnBtn">Включить демо</button></div>
        </div>
      </div>
      <div class="kpis">
        <div class="kpi"><div class="l">Найдено за сессию</div><div class="v num" id="kFound">0</div><div class="s" id="kFoundS">выгодных лотов</div></div>
        <div class="kpi"><div class="l">Возможная прибыль</div><div class="v num good" id="kProfit">0 ₽</div><div class="s">по активным лотам</div></div>
        <div class="kpi"><div class="l">Задержка API</div><div class="v num" id="kDelay">—</div><div class="s" id="kDelayS">измерится со второй проверки</div></div>
        <div class="kpi"><div class="l">Проверка</div><div class="v num" id="kPass">—</div><div class="s" id="kPassS">ещё не было</div><div class="bar"><i id="kBar"></i></div></div>
      </div>
      <div class="toolbar">
        <div class="seg" id="kindSeg"><button data-k="all" class="on">Все</button><button data-k="buyout">Выкуп</button><button data-k="bid">Ставки</button></div>
        <input class="field search" id="search" placeholder="Поиск по названию">
        <div class="spacer"></div>
        <label class="muted" style="font-size:13px"><input type="checkbox" id="hideOld" checked> скрывать проданные и истёкшие</label>
        <button class="btn ghost" id="clearBtn">Очистить</button>
      </div>
      <div class="tablewrap" id="tableWrap">
        <table>
          <thead><tr>
            <th data-s="name">Предмет</th><th data-s="amount">Кол-во</th><th data-s="unit">Цена / шт</th><th data-s="market">Рынок / шт</th>
            <th data-s="profit" class="sorted">Прибыль ↓</th><th data-s="pct">Ниже рынка</th><th data-s="listed">Выставлен</th><th data-s="ends">Активен до</th>
          </tr></thead>
          <tbody id="rows"></tbody>
        </table>
        <div class="empty" id="empty"><div><div class="radar"></div><h3 id="emptyH">Пока ничего не найдено</h3><div id="emptyT">Нажми «Запустить» — трекер начнёт проверять аукцион.</div></div></div>
      </div>
    </section>

    <section class="view" id="view-items">
      <div class="grid2">
        <div class="card">
          <h3>Что отслеживать</h3>
          <div class="sub">Начни вводить название — появятся подсказки из базы игры. Enter добавляет предмет.</div>
          <div class="combo">
            <input class="field" id="itemInput" placeholder="Например: Морфин, Ледяной ежик…" autocomplete="off">
            <div class="dropdown" id="dropdown"></div>
          </div>
          <div class="chips" id="chips"></div>
          <div class="muted" id="chipsEmpty" style="margin-top:14px">Список пуст.</div>
        </div>
        <div class="col">
        <div class="card">
          <div class="art-head">
            <div><h3>Все артефакты</h3><div class="sub" id="artSub">Трекер сам проверит все артефакты из базы игры — не только твой список.</div></div>
            <label class="switch"><input type="checkbox" id="sAllArts"><i></i></label>
          </div>
          <div class="note" style="margin:0">Полный проход занимает несколько минут. Цена артефакта зависит ещё от процента качества и доп. свойств — их трекер не видит, поэтому каждую находку проверяй в игре.</div>
        </div>
        <div class="card">
          <h3>Готовые наборы</h3>
          <div class="sub">Добавляет предметы к списку, уже добавленные не дублируются.</div>
          <div class="presets">
            <button class="preset" data-preset="craft"><b>Ингредиенты твоих крафтов</b><span>Морфин, Янтарная полынь, Хлорид алюминия, Теломераза, Мутаген, Коагулянт, Чертоцвет, Полимеры, Помидор</span></button>
            <button class="preset" data-preset="arts"><b>Ходовые артефакты</b><span>Ледяной ежик, Вихрь, Змеиный глаз, Гелий, Спираль, Батарейка</span></button>
            <button class="preset" data-preset="hot"><b>Ходовые материалы</b><span>Огромный артефактный фрагмент, Моток медной проволоки, Аммиак, Набор специй, Полимеры</span></button>
          </div>
        </div>
        </div>
      </div>
    </section>

    <section class="view" id="view-settings">
      <div class="form">
        <div class="card">
          <h3>Доступ к API</h3>
          <div class="sub">Ключи выдаёт @stalzone_api_bot после одобрения заявки.</div>
          <div class="row" id="demoRow"><label>Демо-режим<small>Тестовые данные EXBO, ключи не нужны</small></label><label class="switch"><input type="checkbox" id="sDemo"><i></i></label></div>
          <div class="row wide"><label>Client ID</label><input class="field" id="sClientId" autocomplete="off"></div>
          <div class="row wide"><label>Client Secret</label><input class="field" id="sClientSecret" type="password" autocomplete="off"></div>
          <div class="row wide"><label>Токен (необязательно)<small>Только если EXBO выдала готовый токен</small></label><input class="field" id="sToken" type="password" autocomplete="off"></div>
          <div class="linkrow"><button class="btn" data-open="api_bot">Получить доступ</button><button class="btn" data-open="docs">Документация</button></div>
        </div>
        <div class="card">
          <h3>Когда сообщать</h3>
          <div class="sub">Лот попадёт в список, только если выполнены оба условия.</div>
          <div class="row"><label>Дешевле рынка минимум на<small>в процентах</small></label><input class="field num" id="sDiscount" inputmode="numeric"></div>
          <div class="row"><label>Минимальная прибыль<small>после комиссии 5%, ₽</small></label><input class="field num" id="sMinProfit" inputmode="numeric"></div>
          <div class="row"><label>Проверять каждые<small>минут, от 0,5 до 60 (новые лоты API отдаёт с задержкой ~10–20 мин)</small></label><input class="field num" id="sPoll" inputmode="numeric"></div>
          <div class="row"><label>Рыночная цена по сделкам за<small>часов</small></label><input class="field num" id="sHist" inputmode="numeric"></div>
        </div>
        <div class="card">
          <h3>Ставки</h3>
          <div class="sub">Лоты со ставками, которые скоро закончатся, а ставка сильно ниже рынка.</div>
          <div class="row"><label>Искать выгодные ставки</label><label class="switch"><input type="checkbox" id="sBids"><i></i></label></div>
          <div class="row"><label>Лоты, что закончатся в ближайшие<small>минут</small></label><input class="field num" id="sBidWin" inputmode="numeric"></div>
          <div class="row"><label>Звук при находке<small>сохраняется в этом окне</small></label><label class="switch"><input type="checkbox" id="sSound"><i></i></label></div>
        </div>
        <div class="card">
          <h3>Telegram</h3>
          <div class="sub">Необязательно. Уведомления о находках придут тебе на телефон.</div>
          <div class="row wide"><label>Токен бота<small>создай бота у @BotFather</small></label><input class="field" id="sTgToken" type="password" autocomplete="off"></div>
          <div class="row wide"><label>Chat ID<small>напиши боту, затем открой api.telegram.org/bot&lt;токен&gt;/getUpdates</small></label><input class="field" id="sTgChat" autocomplete="off"></div>
          <div class="linkrow"><button class="btn" data-open="botfather">Открыть @BotFather</button></div>
        </div>
        <div class="card">
          <h3>Программа и данные</h3>
          <div class="sub">Версия <span id="appVer"></span>. Ключи, настройки, находки и журнал хранятся отдельно от программы — обновление или перенос .exe их не сотрёт.</div>
          <div class="row wide"><label>Папка с данными<small id="dataDir" style="word-break:break-all"></small></label></div>
          <div class="row"><label>Хранить историю сделок<small>дней, от 3 до 90: больше — точнее оценка редких артефактов, но файл больше</small></label><input class="field num" id="sKeep" inputmode="numeric"></div>
          <div class="muted" id="dbInfo" style="font-size:13px;margin-top:10px">База сделок пока пустая — начнёт копиться после запуска.</div>
          <div class="row wide" style="margin-top:6px"><label>Обновления с GitHub<small>репозиторий «владелец/имя» — программа сама проверит, скачает и поставит новую версию</small></label><input class="field" id="sUpdRepo" placeholder="например, ivan/stalzone-tracker" autocomplete="off"></div>
          <div class="muted" id="updInfo" style="font-size:13px;margin-top:8px"></div>
          <div class="linkrow"><button class="btn" id="updCheckBtn">Проверить обновления</button><button class="btn" id="openDataBtn">Открыть папку</button></div>
          <div class="note">Поделиться с другом: собери STALZONE Tracker.exe файлом build_exe.bat и отправь ему. Твои ключи и находки в .exe не попадают. Другу нужны свои ключи: пусть отправит /newapp боту @stalzone_api_bot.</div>
        </div>
      </div>
      <div class="savebar"><span class="muted" id="saveHint" style="align-self:center"></span><button class="btn primary" id="saveBtn">Сохранить</button></div>
    </section>

    <section class="view" id="view-log"><div class="log" id="log"></div></section>
  </main>
</div>

<aside class="drawer" id="drawer"></aside>
<div class="overlay" id="restartOverlay" hidden><div><div class="radar"></div><h2>Устанавливаю обновление</h2><div class="muted">Программа закроется и через несколько секунд откроется уже новой версией.</div></div></div>
<div class="toast" id="toast"></div>

<script>
const TOKEN = "__TOKEN__";
const QN = ["обычный","необычный","особый","редкий","исключительный","легендарный"];
const PRESETS = {
  craft: ["Морфин","Янтарная полынь","Хлорид алюминия","Теломераза","Мутаген","Коагулянт","Чертоцвет","Полимеры","Помидор"],
  arts: ["Ледяной ежик","Вихрь","Змеиный глаз","Гелий","Спираль","Батарейка"],
  hot: ["Огромный артефактный фрагмент","Моток медной проволоки","Аммиак","Набор специй","Полимеры"],
};
const TITLES = {deals:"Выгодные лоты", items:"Предметы", settings:"Настройки", log:"Журнал"};
let S = null, view = "deals", kind = "all", sortKey = "profit", sortDir = -1, selected = null;
let knownIds = new Set(), firstLoad = true, lastErr = 0, formDirty = false;
const $ = (id) => document.getElementById(id);
const rub = (x) => Math.round(x).toLocaleString("ru-RU").replace(/ /g, " ") + " ₽";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const store = { get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
                set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };

async function api(path, body) {
  const opt = { headers: { "X-Token": TOKEN } };
  if (body !== undefined) { opt.method = "POST"; opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const r = await fetch(path, opt);
  return r.json();
}
function toast(msg, err) {
  const t = $("toast"); t.textContent = msg; t.className = "toast on" + (err ? " err" : "");
  clearTimeout(toast.h); toast.h = setTimeout(() => t.className = "toast", 2600);
}
function ago(iso, now) {
  if (!iso) return "—";
  const m = (now - Date.parse(iso) / 1000) / 60;
  if (m < 1) return "только что";
  if (m < 60) return Math.round(m) + " мин назад";
  if (m < 48 * 60) return Math.round(m / 60) + " ч назад";
  return Math.round(m / 1440) + " дн назад";
}
function fmtWindow(h) { return h < 36 ? Math.round(h) + " ч" : Math.round(h / 24) + " дн."; }
function until(iso) {
  if (!iso) return "—";
  const d = new Date(iso), now = new Date();
  const hm = d.toLocaleTimeString("ru-RU", {hour: "2-digit", minute: "2-digit"});
  return d.toDateString() === now.toDateString() ? "сегодня " + hm : d.toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit"}) + " " + hm;
}
function qualityTag(d) {
  if (d.quality === null || d.quality === undefined) return "";
  const p = d.exact ? "+" + d.ptn : d.ptn >= 15 ? "+15" : "+" + d.ptn + "…" + (d.ptn + 4);
  return `<span class="q" style="color:var(--q${d.quality})">${QN[d.quality] || d.quality} ${p}</span>`;
}
function beep() {
  if (!store.get("sound", true)) return;
  try {
    const ctx = beep.ctx || (beep.ctx = new (window.AudioContext || window.webkitAudioContext)());
    [0, 0.13].forEach((t, i) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = i ? 1180 : 880; o.type = "sine";
      g.gain.setValueAtTime(0.0001, ctx.currentTime + t);
      g.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + 0.12);
      o.connect(g).connect(ctx.destination); o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.14);
    });
  } catch (e) {}
}
function notifyDesktop(d) {
  try {
    if ("Notification" in window && Notification.permission === "granted")
      new Notification(d.name + " — прибыль ~" + rub(d.profit), { body: (d.kind === "bid" ? "Ставка · " : "Выкуп · ") + d.amount + " шт по " + rub(d.unit) });
  } catch (e) {}
}

// ---------- навигация ----------
function go(v) {
  view = v;
  document.querySelectorAll(".nav button").forEach((b) => b.classList.toggle("on", b.dataset.view === v));
  document.querySelectorAll(".view").forEach((s) => s.classList.toggle("on", s.id === "view-" + v));
  $("viewTitle").textContent = TITLES[v];
  if (v !== "deals") closeDrawer();
}
document.querySelectorAll(".nav button").forEach((b) => b.onclick = () => go(b.dataset.view));
document.querySelectorAll("[data-goto]").forEach((b) => b.onclick = () => go(b.dataset.goto));
document.querySelectorAll("[data-open]").forEach((b) => b.onclick = () => api("/api/open", {link: b.dataset.open}));
$("demoOnBtn").onclick = async () => {
  const r = await api("/api/settings", {demo: true});
  toast(r.ok ? "Демо-режим включён — нажми «Запустить»" : r.message, !r.ok);
  refresh();
};
$("demoOffBtn").onclick = () => {
  go("settings");
  const row = $("demoRow");
  row.classList.remove("flash"); void row.offsetWidth; row.classList.add("flash");
  row.scrollIntoView({block: "center", behavior: "smooth"});
  toast("Выключи «Демо-режим» и нажми «Сохранить»");
};

// ---------- запуск ----------
$("runBtn").onclick = async () => {
  if (S && S.status.running) { await api("/api/stop", {}); toast("Останавливаю…"); return; }
  try { if ("Notification" in window && Notification.permission === "default") Notification.requestPermission(); } catch (e) {}
  beep.ctx = beep.ctx || null;
  const r = await api("/api/start", {});
  if (!r.ok) { toast(r.message, true); if (!S.configured) go("settings"); else go("items"); }
  else toast("Трекер запущен");
  refresh();
};

// ---------- сделки ----------
$("kindSeg").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; kind = b.dataset.k; [...$("kindSeg").children].forEach((x) => x.classList.toggle("on", x === b)); renderDeals(); };
$("search").oninput = renderDeals;
$("hideOld").onchange = renderDeals;
$("clearBtn").onclick = async () => { await api("/api/deals/clear", {}); closeDrawer(); refresh(); };
document.querySelectorAll("th[data-s]").forEach((th) => th.onclick = () => {
  const k = th.dataset.s; sortDir = sortKey === k ? -sortDir : (k === "name" ? 1 : -1); sortKey = k;
  document.querySelectorAll("th[data-s]").forEach((x) => { x.classList.toggle("sorted", x === th); x.textContent = x.textContent.replace(/ [↑↓]$/, ""); });
  th.textContent += sortDir > 0 ? " ↑" : " ↓"; renderDeals();
});
function visibleDeals() {
  const q = $("search").value.trim().toLowerCase().replace(/ё/g, "е");
  const now = S.now;
  let list = S.deals.filter((d) => (kind === "all" || d.kind === kind)
    && (!q || d.name.toLowerCase().replace(/ё/g, "е").includes(q))
    && (!$("hideOld").checked || (!d.gone && (!d.ends || Date.parse(d.ends) / 1000 > now))));
  const val = (d) => sortKey === "listed" || sortKey === "ends" ? Date.parse(d[sortKey] || 0) : d[sortKey];
  list.sort((a, b) => { const x = val(a), y = val(b); return (typeof x === "string" ? x.localeCompare(y, "ru") : (x - y)) * sortDir; });
  return list;
}
function renderDeals() {
  if (!S) return;
  const list = visibleDeals(), now = S.now;
  $("rows").innerHTML = list.map((d) => {
    const old = d.gone || (d.ends && Date.parse(d.ends) / 1000 <= now);
    const fresh = now - d.found < 300;
    return `<tr class="lot${selected === d.id ? " sel" : ""}${fresh ? " new" : ""}${old ? " old" : ""}" data-id="${d.id}">
      <td><div class="item"><span class="n">${esc(d.name)}</span><span class="tags"><span class="tag ${d.kind === "bid" ? "bid" : "buy"}">${d.kind === "bid" ? "Ставка" : "Выкуп"}</span>${qualityTag(d)}${d.gone ? `<span class="tag">куплен или снят</span>` : ""}${d.stale ? `<span class="tag stale" title="${esc(d.stale)}">давно висит</span>` : ""}</span></div></td>
      <td class="num">${d.amount} шт</td>
      <td class="num">${rub(d.unit)}</td>
      <td class="num muted">${rub(d.market)}</td>
      <td class="num profit">+${rub(d.profit)}</td>
      <td><span class="pct num">−${Math.round(d.pct)}%</span></td>
      <td class="muted">${ago(d.listed, now)}</td>
      <td class="muted">${until(d.ends)}</td></tr>`;
  }).join("");
  const empty = list.length === 0;
  $("empty").style.display = empty ? "grid" : "none";
  if (empty) {
    if (S.status.running) {
      const total = (S.status.progress && S.status.progress.total) || watchTotal();
      $("emptyH").textContent = "Ищу выгодные лоты…";
      $("emptyT").textContent = `Проверяю ${total} предм. каждые ${S.settings.poll_minutes} мин. Как только что-то найдётся — появится здесь.`;
    }
    else if (S.deals.length) { $("emptyH").textContent = "Под фильтр ничего не подходит"; $("emptyT").textContent = "Сбрось поиск или покажи истёкшие лоты."; }
    else { $("emptyH").textContent = "Пока ничего не найдено"; $("emptyT").textContent = "Нажми «Запустить» — трекер начнёт проверять аукцион."; }
  }
  document.querySelectorAll("tr.lot").forEach((tr) => tr.onclick = () => openDrawer(+tr.dataset.id));
}
function openDrawer(id) {
  const d = S.deals.find((x) => x.id === id); if (!d) return;
  selected = id; renderDeals();
  const bid = d.kind === "bid";
  $("drawer").innerHTML = `
    <button class="close" id="dClose">✕</button>
    <span class="tag ${bid ? "bid" : "buy"}">${bid ? "Ставка" : "Выкуп"}</span> ${qualityTag(d)}
    <h2>${esc(d.name)}</h2>
    <div class="muted">${d.amount} шт · дешевле рынка на ${Math.round(d.pct)}%</div>
    <div class="big num">+${rub(d.profit)}</div>
    <div class="muted">возможная прибыль · ${Math.round(d.roi)}% к вложенному</div>
    <div class="calc num">
      <div><span>${bid ? (d.has_bids ? "Текущая ставка" : "Стартовая цена") : "Купить"}<small>${d.amount} шт по ${rub(d.unit)}</small></span><span>${rub(d.cost)}</span></div>
      <div><span>Перепродать<small>по ~${rub(d.market)} за шт</small></span><span>${rub(d.resale)}</span></div>
      <div><span>Комиссия аукциона 5%</span><span>−${rub(d.resale * 0.05)}</span></div>
      <div><span>Прибыль</span><span>+${rub(d.profit)}</span></div>
    </div>
    ${d.gone ? `<div class="note warn">Этого лота больше нет на аукционе — его уже купили или сняли.</div>` : ""}
    ${d.stale && !d.gone ? `<div class="note warn">${esc(d.stale)}</div>` : ""}
    ${bid ? `<div class="note">Ставь не выше <b>${rub(d.max_bid)}</b> за весь лот — тогда прибыль будет не меньше минимальной из настроек.</div>` : ""}
    <div class="facts">
      <div class="fact"><div class="l">Цена по сделкам${d.window_h ? " за " + fmtWindow(d.window_h) : ""}</div><div class="v num">${rub(d.hist)}/шт</div></div>
      <div class="fact"><div class="l">${d.exact ? "Такой же или лучше" : "Дешевле всего"} на аукционе</div><div class="v num">${d.floor ? rub(d.floor) + "/шт" : "нет"}</div></div>
      <div class="fact"><div class="l">Выставлен</div><div class="v">${ago(d.listed, S.now)}</div></div>
      <div class="fact"><div class="l">Активен до</div><div class="v">${until(d.ends)}</div></div>
      <div class="fact"><div class="l">Сделок в расчёте</div><div class="v num">${d.n_sales}</div></div>
      <div class="fact"><div class="l">Рынок покупает</div><div class="v num">~${Math.round(d.per_day).toLocaleString("ru-RU")} шт/сут</div></div>
      <div class="fact"><div class="l">Цена за сутки</div><div class="v num" style="color:${d.trend == null ? "inherit" : d.trend <= -5 ? "var(--bad)" : d.trend >= 5 ? "var(--good)" : "inherit"}">${d.trend == null ? "мало данных" : (d.trend > 0 ? "+" : d.trend < 0 ? "−" : "") + Math.abs(Math.round(d.trend)) + "% к прошлым дням"}</div></div>
    </div>
    <div class="note">${d.floor && d.floor * 0.99 < d.hist
      ? "Перепродать дороже самого дешёвого такого же лота не выйдет, поэтому цена продажи — чуть ниже него, а не по прошлым сделкам."
      : d.floor ? "Цена продажи — по прошлым сделкам: такие же лоты на аукционе сейчас дороже."
      : "Такого же или лучше лота на аукционе сейчас нет — цена продажи только по прошлым сделкам, это менее надёжно."}</div>
    <div class="note">${esc((d.speed.charAt(0).toUpperCase() + d.speed.slice(1)).replace(/\.$/, ""))}. Данные API запаздывают — проверь лот в игре перед покупкой.</div>
    ${d.quality !== null && d.quality !== undefined ? `<div class="note">Артефакт: цена зависит ещё от процента качества и доп. свойств — сравни лот в игре с другими того же качества и заточки.</div>` : ""}
    <div class="actions"><button class="btn primary" id="dCopy">Скопировать название</button><button class="btn" id="dHide">Скрыть</button></div>`;
  $("drawer").classList.add("on");
  $("dClose").onclick = closeDrawer;
  $("dCopy").onclick = () => copyText(d.name);
  $("dHide").onclick = async () => { await api("/api/deals/remove", {id: d.id}); closeDrawer(); refresh(); };
}
function closeDrawer() { $("drawer").classList.remove("on"); selected = null; if (S) renderDeals(); }
function copyText(t) {
  const done = () => toast("Скопировано — вставь в поиск аукциона");
  if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(t).then(done, () => fallback()); } else fallback();
  function fallback() { const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select(); try { document.execCommand("copy"); done(); } catch (e) {} a.remove(); }
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

// ---------- предметы ----------
function watch() { return S ? S.settings.watch.slice() : []; }
async function saveWatch(list, msg, warn) { const r = await api("/api/settings", {watch: list}); toast(r.ok ? (msg || "Список обновлён") : r.message, !r.ok || !!warn); refresh(); }
function addItem(name, unknown) {
  name = (name || "").trim(); if (!name) return;
  const list = watch();
  if (list.some((x) => x.toLowerCase() === name.toLowerCase())) { toast("Уже в списке"); return; }
  list.push(name); $("itemInput").value = ""; hideDrop();
  saveWatch(list, unknown ? "«" + name + "» нет в базе игры — проверь написание" : "Добавлено: " + name, unknown);
}
function plural(n, forms) {
  const a = n % 10, b = n % 100;
  return forms[a === 1 && b !== 11 ? 0 : a >= 2 && a <= 4 && (b < 12 || b > 14) ? 1 : 2];
}
function watchTotal() {
  return watch().length + (S && S.settings.all_artifacts ? (S.artifacts || 0) : 0);
}
function renderChips() {
  const list = watch(), allArts = !!S.settings.all_artifacts;
  $("chips").innerHTML = list.map((n, i) => `<span class="chip">${esc(n)}<button title="Убрать" data-i="${i}">✕</button></span>`).join("");
  $("chipsEmpty").style.display = list.length ? "none" : "block";
  $("chipsEmpty").textContent = allArts ? "Свой список пуст — проверяются только все артефакты." : "Список пуст.";
  $("chips").querySelectorAll("button").forEach((b) => b.onclick = () => { const l = watch(); l.splice(+b.dataset.i, 1); saveWatch(l, "Убрано"); });
  $("cntItems").textContent = watchTotal() || "";
  $("sAllArts").checked = allArts;
  $("artSub").textContent = S.artifacts
    ? `Трекер сам проверит все ${S.artifacts} ${plural(S.artifacts, ["артефакт", "артефакта", "артефактов"])} из базы игры — не только твой список.`
    : "Трекер сам проверит все артефакты из базы игры — не только твой список.";
}
$("sAllArts").onchange = async () => {
  const on = $("sAllArts").checked;
  const r = await api("/api/settings", {all_artifacts: on});
  if (!r.ok) toast(r.message, true);
  else toast(on ? "Все артефакты включены" + (S.status.running ? " — трекер перезапускается" : "") : "Все артефакты выключены");
  refresh();
};
let dropIdx = -1, dropItems = [];
function hideDrop() { $("dropdown").classList.remove("on"); dropIdx = -1; }
$("itemInput").oninput = async () => {
  const q = $("itemInput").value.trim();
  if (q.length < 2) return hideDrop();
  const r = await api("/api/suggest?q=" + encodeURIComponent(q));
  dropItems = r.items || []; dropIdx = dropItems.length ? 0 : -1;
  $("dropdown").innerHTML = dropItems.map((n, i) => `<div data-i="${i}">${esc(n)}</div>`).join("") || `<div class="muted">Не нашёл — Enter добавит как есть</div>`;
  $("dropdown").classList.add("on");
  $("dropdown").querySelectorAll("[data-i]").forEach((el, i) => el.classList.toggle("act", i === dropIdx));
  $("dropdown").querySelectorAll("[data-i]").forEach((el) => el.onmousedown = (e) => { e.preventDefault(); addItem(dropItems[+el.dataset.i]); });
};
$("itemInput").onkeydown = (e) => {
  const els = $("dropdown").querySelectorAll("[data-i]");
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault(); if (!els.length) return;
    dropIdx = (dropIdx + (e.key === "ArrowDown" ? 1 : -1) + els.length) % els.length;
    els.forEach((el, i) => el.classList.toggle("act", i === dropIdx));
  } else if (e.key === "Enter") {
    const typed = $("itemInput").value.trim();
    const exact = dropItems.find((n) => n.toLowerCase().replace(/ё/g, "е") === typed.toLowerCase().replace(/ё/g, "е"));
    if (exact) addItem(exact);
    else if (dropIdx >= 0 && dropItems[dropIdx]) addItem(dropItems[dropIdx]);
    else if (typed) addItem(typed, true);
  }
  else if (e.key === "Escape") hideDrop();
};
$("itemInput").onblur = () => setTimeout(hideDrop, 150);
document.querySelectorAll("[data-preset]").forEach((b) => b.onclick = () => {
  const list = watch(), add = PRESETS[b.dataset.preset].filter((n) => !list.some((x) => x.toLowerCase() === n.toLowerCase()));
  if (!add.length) return toast("Всё из набора уже в списке");
  saveWatch(list.concat(add), "Добавлено: " + add.length);
});

// ---------- настройки ----------
function fillForm() {
  const c = S.settings;
  $("sDemo").checked = S.demo; $("sClientId").value = c.client_id || ""; $("sClientSecret").value = c.client_secret || ""; $("sToken").value = c.app_token || "";
  $("sDiscount").value = Math.round(c.discount * 100); $("sMinProfit").value = Math.round(c.min_profit); $("sPoll").value = c.poll_minutes;
  $("sHist").value = c.history_hours; $("sBids").checked = !!c.bids; $("sBidWin").value = c.bid_window_minutes;
  $("sTgToken").value = c.telegram_token || ""; $("sTgChat").value = c.telegram_chat_id || ""; $("sSound").checked = store.get("sound", true);
  $("appVer").textContent = S.version || ""; $("dataDir").textContent = S.data_dir || "";
  $("sKeep").value = c.history_keep_days || 14;
  $("sUpdRepo").value = c.update_repo || "";
}
document.querySelectorAll("#view-settings input").forEach((el) => el.addEventListener("input", () => { formDirty = true; $("saveHint").textContent = "Есть несохранённые изменения"; }));
$("sSound").onchange = () => store.set("sound", $("sSound").checked);
$("openDataBtn").onclick = async () => { const r = await api("/api/open_data", {}); if (!r.ok) toast("Не получилось открыть — путь указан выше", true); };
$("updCheckBtn").onclick = async () => {
  if (formDirty) { toast("Сначала нажми «Сохранить»", true); return; }
  await api("/api/update/check", {}); toast("Проверяю обновления…"); setTimeout(refresh, 1500);
};
$("updBtn").onclick = async () => { await api("/api/update/apply", {}); toast("Скачиваю обновление…"); refresh(); };
$("saveBtn").onclick = async () => {
  const num = (id) => $(id).value.replace(/\s/g, "").replace(",", ".");
  const r = await api("/api/settings", {
    demo: $("sDemo").checked, client_id: $("sClientId").value, client_secret: $("sClientSecret").value, app_token: $("sToken").value,
    discount_pct: num("sDiscount"), min_profit: num("sMinProfit"), poll_minutes: num("sPoll"), history_hours: num("sHist"),
    bids: $("sBids").checked, bid_window_minutes: num("sBidWin"), telegram_token: $("sTgToken").value, telegram_chat_id: $("sTgChat").value,
    history_keep_days: num("sKeep"), update_repo: $("sUpdRepo").value,
  });
  toast(r.ok ? (S.status.running ? "Сохранено — трекер перезапускается" : "Настройки сохранены") : r.message, !r.ok);
  if (r.ok) { formDirty = false; $("saveHint").textContent = ""; }
  refresh();
};

// ---------- состояние ----------
function renderStatus() {
  const st = S.status, run = st.running;
  $("dot").classList.toggle("live", run);
  let txt = "Остановлен";
  if (run) txt = st.starting ? "Запускаю…" : (st.progress ? st.progress.text : "Жду следующей проверки");
  $("stateTxt").textContent = txt;
  const btn = $("runBtn"); btn.textContent = run ? "■ Остановить" : "▶ Запустить"; btn.classList.toggle("stop", run);
  $("modeLbl").innerHTML = "Регион RU · " + (S.demo ? "<b>ДЕМО-режим</b>" : "боевой API");
  $("onboard").hidden = S.configured;
  $("demoNote").hidden = !S.demo;
  $("demoNoteSub").innerHTML = S.has_keys
    ? "<b>Ключи у тебя уже есть — выключи демо-режим.</b> Находки здесь ненастоящие."
    : "Находки здесь ненастоящие — режим нужен, только чтобы проверить, что приложение работает.";
  const active = S.deals.filter((d) => !d.gone && (!d.ends || Date.parse(d.ends) / 1000 > S.now));
  $("kFound").textContent = st.found_total; $("kFoundS").textContent = active.length + " " + plural(active.length, ["активный", "активных", "активных"]) + " сейчас";
  $("kProfit").textContent = rub(active.reduce((s, d) => s + d.profit, 0));
  if (st.delay !== null && st.delay !== undefined) { $("kDelay").textContent = "~" + Math.round(st.delay) + " мин"; $("kDelayS").textContent = "столько идут новые лоты до трекера"; }
  if (st.progress) {
    $("kPass").textContent = st.progress.done + " / " + st.progress.total; $("kPassS").textContent = "идёт проверка";
    $("kBar").style.width = (st.progress.total ? st.progress.done / st.progress.total * 100 : 0) + "%";
  } else if (st.last_pass) {
    const t = new Date(st.last_pass * 1000).toLocaleTimeString("ru-RU", {hour: "2-digit", minute: "2-digit"});
    $("kPass").textContent = t; $("kPassS").textContent = "за " + Math.round(st.took) + " с · каждые " + S.settings.poll_minutes + " мин"; $("kBar").style.width = "100%";
  }
  $("cntDeals").textContent = active.length || "";
  const up = S.update || {}, busy = up.status === "downloading";
  $("updNote").hidden = !(up.status === "available" || busy);
  $("updTitle").textContent = busy ? up.message : `Доступна версия ${up.version || ""}`;
  $("updSub").textContent = busy ? "Не закрывай программу — она перезапустится сама."
    : ((up.notes || "").split("\n").find((l) => l.trim()) || "Скачается и установится само, программа перезапустится.");
  $("updBtn").hidden = up.status !== "available";
  $("updInfo").textContent = up.message || (up.repo ? "" : "Обновления не настроены — укажи репозиторий и сохрани.");
  $("restartOverlay").hidden = up.status !== "restarting";
  const db = st.db;
  if (db && db.sales) {
    const n = (x) => String(x).replace(".", ",");
    $("dbInfo").textContent = `База сделок: ${db.sales.toLocaleString("ru-RU")} сделок по ${db.items} предм. за ${n(db.days)} дн. · ${n(db.mb)} МБ`;
  }
  if (st.error && st.error_id !== lastErr) { lastErr = st.error_id; toast(st.error, true); }
  const logCls = (m) => /ОШИБКА|ошибка/.test(m) ? "e" : /^⚠/.test(m) ? "w" : /^Найдено/.test(m) ? "f" : "";
  $("log").innerHTML = S.log.map((l) => `<div><span class="t">${l.t}</span>  <span class="${logCls(l.m)}">${esc(l.m)}</span></div>`).join("");
}
async function refresh() {
  try { S = await api("/api/state"); } catch (e) { $("stateTxt").textContent = "Нет связи с приложением"; return; }
  const fresh = S.deals.filter((d) => !knownIds.has(d.id));
  fresh.forEach((d) => knownIds.add(d.id));
  const loud = fresh.filter((d) => d.notify !== false);  // о старых находках из прошлых запусков — тихо
  if (!firstLoad && loud.length) { beep(); loud.slice(0, 3).forEach(notifyDesktop); }
  if (firstLoad || !formDirty) fillForm();
  firstLoad = false;
  renderStatus(); renderDeals(); renderChips();
}
refresh(); setInterval(refresh, 2000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
