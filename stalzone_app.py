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
except ImportError as e:
    print("Ошибка запуска:", e)
    print("Нужен модуль requests (pip install requests) и файл stalzone_tracker.py рядом.")
    input("Нажми Enter, чтобы закрыть…")
    sys.exit(1)

APP_NAME = "STALZONE Tracker"
APP_VERSION = "1.8"
# Откуда брать обновления: открытый репозиторий GitHub «владелец/имя» только с готовыми .exe
# (код лежит в закрытом). В настройках можно указать другой. Пусто — обновления не проверяются.
UPDATE_REPO = "Enotsbeye/stalzone-tracker-releases"
OLD_UPDATE_REPOS = ("Enotsbeye/stalzone-tracker",)   # откуда обновлялись версии до 1.8
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
SETTINGS_VERSION = 2
DEFAULTS = dict(eng.CONFIG, settings_version=SETTINGS_VERSION)
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


# ------------------------------ Доступ по кодам ------------------------------
# Владелец выдаёт каждому человеку код: имя + ID его компьютера + срок, подписанные личным ключом
# владельца (Ed25519). Программа проверяет подпись встроенным открытым ключом — подделать код
# или перенести его на другой ПК нельзя. Отозвать: вписать имя или номер кода в revoked.txt
# в открытом репозитории с выпусками.
# Пока OWNER_PUBLIC_KEY пустой, программа открыта всем — так владелец может создать свой ключ.
OWNER_PUBLIC_KEY = ""
REVOKED_URL = "https://raw.githubusercontent.com/Enotsbeye/stalzone-tracker-releases/main/revoked.txt"
OWNER_KEY_FILE = os.path.join(DATA_DIR, "owner_key.pem")      # личный ключ — только у владельца
ISSUED_FILE = os.path.join(DATA_DIR, "issued_codes.json")     # кому владелец выдавал коды
ACCESS_FILE = os.path.join(DATA_DIR, "access_state.json")     # отозванные и «самая поздняя дата»
CODE_PREFIX = "SZ1-"
REVOKED_REFRESH = 3 * 3600

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
except ImportError:   # без модуля cryptography коды не проверить
    Ed25519PrivateKey = Ed25519PublicKey = serialization = None
    InvalidSignature = Exception


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
    def issue(self, name, machine, days):
        if not self.is_owner() or not OWNER_PUBLIC_KEY:
            return False, "Выдавать коды может только владелец программы", None
        name = re.sub(r"\s+", " ", str(name or "")).strip()[:40]
        machine = norm_machine(machine)
        if not name:
            return False, "Впиши имя — по нему потом можно отозвать доступ", None
        if not machine:
            return False, "ID компьютера — 10 букв и цифр, например ABCDE-23456. Его показывает программа у друга", None
        try:
            days = int(float(days or 0))
        except (TypeError, ValueError):
            return False, "Срок — число дней (0 — бессрочно)", None
        days = max(0, min(days, 3650))
        today = self.today()
        payload = {"n": name, "m": machine, "e": today + days if days else 0, "i": secrets.token_hex(3), "t": today}
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        code = CODE_PREFIX + _b64e(data) + "." + _b64e(self.owner_key.sign(data))
        issued = self.issued()
        issued.insert(0, {"name": name, "machine": machine, "id": payload["i"], "expires": payload["e"],
                          "issued": today, "code": code})
        try:
            write_json(ISSUED_FILE, issued[:300])
        except OSError:
            pass
        self.state.add_log(f"Выдан код доступа: {name} ({machine}), "
                           + (f"до {day_text(payload['e'])}" if days else "бессрочно") + f", № {payload['i']}")
        return True, "Код создан — отправь его другу", code

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
        if norm_machine(payload["m"]) != self.machine:
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
        if info["owner"] and OWNER_PUBLIC_KEY:
            info["issued"] = [dict({k: v for k, v in d.items() if k != "code"},
                                   expires_text=day_text(d["expires"]) if d.get("expires") else "бессрочно")
                              for d in self.issued()[:50]]
        return info


def minutes_since(iso):
    try:
        return (datetime.now(timezone.utc) - eng.parse_time(iso)).total_seconds() / 60
    except (TypeError, ValueError):
        return None


# ------------------------------ Фоновая проверка ------------------------------
class Worker(threading.Thread):
    """Проверяет аукцион и передаёт находки в общее состояние через emit()."""

    def __init__(self, cfg, emit, api_factory=None, shown=(), tracked=(), holdings=()):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.emit = emit
        self.stop_event = threading.Event()
        self.api_factory = api_factory or eng.Api
        self.db = None
        self.initial_shown = set(shown)   # что уже есть в таблице (например, восстановлено после перезапуска)
        # находки-выкупы, за судьбой которых следим: пропал лот — купили его или сняли
        self.tracked = {t["lot_key"]: dict(t) for t in tracked}
        self.holdings = list(holdings)     # мои покупки: следим за их текущей ценой
        self.meta = {}

    def stop(self):
        self.stop_event.set()

    def telegram(self, text):
        ok, msg = send_telegram(self.cfg, text)
        if not ok and msg:
            self.emit("log", msg)

    def run(self):
        cfg = self.cfg
        try:
            api = self.api_factory(cfg)
            names = eng.load_listing(cfg["region"])
            try:
                self.meta = {e["id"]: e for e in eng.load_catalog(cfg["region"])}
            except Exception:
                self.meta = {}
            items, auto = eng.watch_items(cfg, names)
            cats = eng.auto_categories(cfg)
            have = {i for i, _ in items}
            hold_ids = set()
            for h in self.holdings:   # купленное тоже проверяем — чтобы видеть его текущую цену
                if h.get("item_id") in names and h["item_id"] not in have:
                    have.add(h["item_id"])
                    hold_ids.add(h["item_id"])
                    items.append((h["item_id"], names[h["item_id"]]))
            if not items:
                self.emit("error", "Список предметов пуст или названия не найдены — проверь вкладку «Предметы».")
                return
            self.emit("log", eng.watching_line([x for x in items if x[0] not in hold_ids], auto, cats))
            seen = eng.load_seen()   # о каких лотах уже сообщали (звук, Telegram) — в прошлых запусках тоже
            shown = set(self.initial_shown)  # что уже есть в таблице — второй раз не добавляем
            known = set()
            db = eng.MarketDB(keep_days=cfg.get("history_keep_days", 14))  # своя база сделок, market.db
            self.db = db
            self.emit("log", eng.db_line(db.stats()))
            # рынок, формат цен, строка рынка в журнале; автодобавленные предметы — без строки на каждый
            scan_cfg = dict(cfg)
            if cfg.get("rare_enabled", True):   # редкие ищем со своим (обычно меньшим) порогом прибыли
                scan_cfg["find_min_profit"] = min(cfg["min_profit"], float(cfg.get("rare_min_profit", cfg["min_profit"])))
            scanner = eng.Scanner(api, scan_cfg, quiet=auto | hold_ids, db=db)
            scanner.quiet_label = "Все артефакты" if cats == ["artefact"] else "Категории целиком"
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
                        self.check_gone(item_id, lots)
                        if item_id in hold_ids or any(h.get("item_id") == item_id for h in self.holdings):
                            self.update_holdings(scanner, item_id, name, list(lots.values()))
                    # замер задержки API: только у предметов, где видны все лоты (иначе старые лоты
                    # «въезжают» в первые страницы и выглядят новыми)
                    complete = lots is not None and len(lots) < eng.LOT_PAGES * 100
                    for key, lot in (lots or {}).items():
                        if key not in known:
                            known.add(key)
                            age = minutes_since(lot.get("startTime"))
                            if complete and not first_pass and age is not None and 0 <= age <= 120:
                                fresh_ages.append(age)
                    # в таблицу — всё найденное в этом запуске; звук и Telegram — только о новом
                    meta = self.meta.get(item_id) or {}
                    for kind, items_found in (("buyout", deals), ("bid", bids)):
                        for d in items_found:
                            g = d.get("grade") or d.get("bucket")
                            rare = is_rare(cfg, item_id, name, meta, g[0] if g else None)
                            if kind == "buyout" and not rare and d["profit"] < cfg["min_profit"]:
                                continue   # нашлось только по «редкому» порогу, а предмет обычный
                            key = ("bid|" if kind == "bid" else "") + eng.lot_key(item_id, d["lot"])
                            if key not in shown:
                                shown.add(key)
                                found[0] += 1
                                self.deal(item_id, name, d, kind, key, notify=key not in seen, rare=rare, meta=meta)
                                seen.add(key)

                # сеть — параллельно, обработка — по порядку (см. eng.scan_pass)
                eng.scan_pass(scanner, items, on_item, self.stop_event.is_set, on_progress)
                eng.save_seen(seen)
                if first_pass and not self.stop_event.is_set() and scanner.summary():
                    self.emit("log", scanner.summary())
                self.emit("pass", {"time": time.time(), "found": found[0], "took": time.time() - started,
                                   "delay": statistics.median(fresh_ages) if fresh_ages else None,
                                   "delay_min": min(fresh_ages) if fresh_ages else None,
                                   "delay_n": len(fresh_ages),
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

    def check_gone(self, item_id, lots):
        """Находка пропала с аукциона: есть такая сделка в истории — лот купили, нет 2 часа — сняли."""
        now = time.time()
        for lot_key, t in list(self.tracked.items()):
            if t["item_id"] != item_id:
                continue
            if lot_key in lots:
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
        """Текущая цена и шанс продажи того, что ты купил."""
        cached = scanner.market_cache.get(item_id)
        market = cached[1] if cached else None
        if not market:
            return
        total = scanner.fmt.total("lots", lot_list, "buyoutPrice", name)
        for h in self.holdings:
            if h.get("item_id") != item_id or h.get("status") == "sold":
                continue
            add = h.get("additional") or {}
            found = eng.market_for(market, add)
            if not found:
                self.emit("holding", {"id": h["id"], "market": None, "updated": time.time()})
                continue
            hist = found[0][0]
            fake = {"amount": h.get("amount", 1), "buyoutPrice": 0, "additional": add}
            resale, floor = eng.resale_price(fake, lot_list, hist, total)
            pairs = eng.deal_pairs(market, add)
            chance = eng.sale_chance(resale, h.get("amount", 1), pairs[0], pairs[1],
                                     eng.competitors(fake, lot_list, resale, total)) if pairs else None
            self.emit("holding", {"id": h["id"], "market": resale, "hist": hist, "floor": floor,
                                  "chance": chance, "updated": time.time()})

    def deal(self, item_id, name, d, kind, key, notify=True, rare=False, meta=None):
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
        if rare:
            text = "💎 ОСОБО РЕДКИЙ\n" + text
        # о находках с низким шансом продажи можно не сообщать (в таблице они всё равно есть)
        min_chance = float(self.cfg.get("notify_min_chance", 0) or 0) / 100
        if notify and not rare and chance and chance["chance"] < min_chance:
            notify = False
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
        self.emit("deal", {
            "item_id": item_id, "name": name, "kind": kind,
            "key": key, "lot_key": eng.lot_key(item_id, lot), "gone": False,
            "cat": meta.get("cat"), "rank": meta.get("rank"), "rare": bool(rare),
            "additional": {k: v for k, v in (lot.get("additional") or {}).items() if k in ("qlt", "ptn")},
            "chance": chance["chance"] if chance else None, "sell_hours": chance.get("hours") if chance else None,
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
        self.catalog = []           # все предметы с категориями — для поиска и «категорий целиком»
        self.meta = {}
        self.cat_counts = {}
        self.purchases = load_purchases()
        self.worker = None
        self.api_factory = api_factory
        self.status = {"running": False, "starting": False, "progress": None, "last_pass": None,
                       "delay": None, "delay_min": None, "delay_n": 0, "found_total": 0, "took": None,
                       "error": None, "error_id": 0, "db": None, "total": None}
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
                if data.get("status") in ("holding", "listed", "sold"):
                    p["status"] = data["status"]
                    if data["status"] == "sold":
                        p["sold_price"] = float(data.get("sold_price") or 0) or p.get("sold_price")
                        if not p["sold_price"]:
                            raise ValueError
                        p["sold_at"] = time.time()
                        p["profit"] = p["sold_price"] * (1 - self.cfg["fee"]) - p["paid"]
                    else:
                        p["sold_price"] = p["sold_at"] = None
                        p.pop("profit", None)
            except (TypeError, ValueError):
                return False, "Впиши, за сколько продал (за весь лот), — только цифры"
        self.save_purchases()
        return True, "Сохранено"

    def remove_purchase(self, pid):
        with self.lock:
            self.purchases = [p for p in self.purchases if p["id"] != pid]
            for d in self.deals:
                if d.get("bought") == pid:
                    d["bought"] = None
        self.save_purchases()
        self.save_deals()
        return True, "Удалено"

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
                self.status.update(last_pass=data["time"], took=data["took"], progress=None, total=data.get("total"))
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
                for d in self.deals:
                    if d.get("item_id") == data["item_id"] and d.get("lot_key") and d["lot_key"] not in present:
                        d["gone"] = True
            elif kind == "lot_status":   # пропавший лот: купили (есть сделка в истории), сняли или истёк
                for d in self.deals:
                    if d.get("lot_key") == data["lot_key"]:
                        d["gone"] = True
                        d["fate"] = data["status"]
            elif kind == "holding":      # текущая цена купленного
                for p in self.purchases:
                    if p["id"] == data["id"]:
                        p.update({"cur_market": data.get("market"), "cur_hist": data.get("hist"),
                                  "cur_floor": data.get("floor"), "cur_chance": data.get("chance"),
                                  "cur_at": data.get("updated")})
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
            self.save_purchases()

    def load_names(self):
        try:
            names = eng.load_listing(self.cfg["region"])
            self.names = sorted(set(names.values()), key=str.lower)
            self.artifacts = len(eng.load_artifacts(self.cfg["region"]))
            catalog = eng.load_catalog(self.cfg["region"])
            counts = {}
            for e in catalog:
                if e["trade"]:
                    counts[e["cat"]] = counts.get(e["cat"], 0) + 1
            with self.lock:
                self.catalog, self.meta, self.cat_counts = catalog, {e["id"]: e for e in catalog}, counts
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
        threading.Thread(target=self.watch_access, daemon=True).start()

    def watch_access(self):
        """Раз в несколько часов — список отозванных кодов; доступ отозвали — останавливаем поиск."""
        while not self.exit_requested.is_set():
            self.access.refresh_revoked()
            info = self.access.check()
            if not info["ok"] and self.worker and self.worker.is_alive():
                self.add_log("Доступ закрыт: " + info.get("reason", ""))
                self.stop()
            self.exit_requested.wait(600)

    def start(self):
        if not self.access.check()["ok"]:
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
            self.worker = Worker(dict(self.cfg), self.emit, self.api_factory,
                                 shown={d["key"] for d in self.deals if d.get("key")},
                                 tracked=tracked, holdings=holdings)
            self.worker.start()
        self.add_log("Трекер запущен" + (" (ДЕМО-режим)" if self.cfg["base_url"] == DEMO_URL else ""))

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
                "access": self.access.snapshot(),
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
            if "notify_min_chance" in data:
                cfg["notify_min_chance"] = min(90.0, max(0.0, float(data["notify_min_chance"])))
            if "update_repo" in data:
                repo = str(data["update_repo"] or "").strip().strip("/")
                repo = re.sub(r"^https?://github\.com/", "", repo).strip("/")   # можно вставить и ссылку
                if repo and not REPO_RE.match(repo):
                    return False, "Репозиторий для обновлений пишется так: владелец/имя (например, ivan/stalzone-tracker)."
                cfg["update_repo"] = repo
            if "demo" in data:
                cfg["base_url"] = DEMO_URL if data["demo"] else PROD_URL
            if "watch" in data:
                cfg["watch"] = list(dict.fromkeys(str(w).strip() for w in data["watch"] if str(w).strip()))[:150]
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
            if url.path == "/api/catalog":
                with state.lock:
                    items = [e for e in state.catalog]
                return self.send_json({"items": items, "names": eng.CATEGORY_NAMES, "auto": list(eng.AUTO_CATEGORIES),
                                       "ranks": eng.RANK_NAMES})
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
                ok, msg, code = state.access.issue(data.get("name"), data.get("machine"), data.get("days"))
                return self.send_json({"ok": ok, "message": msg, "code": code})
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
.search{width:210px}
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
[hidden]{display:none!important}
.overlay h2{margin:14px 0 6px}
.lock{width:min(520px,92vw);text-align:left;background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:26px}
.lock h2{margin:12px 0 6px}
.idrow{display:flex;align-items:center;gap:12px;margin:12px 0;flex-wrap:wrap}
.idrow b{font-size:22px;letter-spacing:.06em;color:var(--accent)}
textarea.field.code{width:100%;min-height:74px;resize:vertical;font:12px/1.4 ui-monospace,Consolas,monospace;word-break:break-all;box-sizing:border-box}
.lock textarea.field.code{margin:10px 0 12px}
.issued{display:grid;grid-template-columns:1fr auto auto;gap:4px 14px;font-size:13px;margin-top:10px}
.issued span{padding:6px 0;border-bottom:1px solid var(--line)}
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
.row.w2{grid-template-columns:1fr 190px}
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
/* фильтры, шанс, редкие, покупки, каталог */
select.field{padding:7px 10px;cursor:pointer}
select.field option{background:var(--panel)}
.field.small{width:130px}
.toggle{all:unset;cursor:pointer;font-size:13px;font-weight:550;padding:6px 12px;border-radius:20px;border:1px solid var(--line);background:var(--panel);color:var(--muted);white-space:nowrap}
.toggle:hover{border-color:var(--line2)}
.toggle.on{border-color:var(--line2);background:var(--raise);color:var(--text)}
.toggle.rare.on{border-color:rgba(212,107,255,.6);color:#ecc8ff;background:rgba(212,107,255,.14)}
.chance{display:inline-flex;flex-direction:column;align-items:flex-end;gap:1px}
.chance b{font-size:12px;font-weight:650;padding:2px 8px;border-radius:20px}
.hi{background:var(--good-bg);color:var(--good)}
.mid{background:rgba(232,184,74,.14);color:var(--accent)}
.lo{background:var(--bad-bg);color:var(--bad)}
.chance small{font-size:11px;color:var(--dim)}
.tag.rare{background:rgba(212,107,255,.16);color:#ecc8ff}
.tag.mine{background:var(--good);color:#06210f}
.tag.fate{background:var(--raise);color:var(--muted)}
.tag.cat{background:transparent;box-shadow:inset 0 0 0 1px var(--line);color:var(--muted);font-weight:550}
.rk{font-size:11px;font-weight:650}
.rk.RANK_NEWBIE{color:#7fd17f}.rk.RANK_STALKER{color:var(--blue)}.rk.RANK_VETERAN{color:#d46bff}.rk.RANK_MASTER{color:var(--bad)}.rk.RANK_LEGEND{color:#ffb84d}
tr.lot.rare td{background:rgba(212,107,255,.05)}
tr.lot.rare td:first-child{box-shadow:inset 3px 0 0 #d46bff}
tr.lot.mine td:first-child{box-shadow:inset 3px 0 0 var(--good)}
.cblock{background:var(--panel2);border-radius:10px;padding:13px 14px;margin:14px 0}
.cblock .l{font-size:12px;color:var(--muted)}
.cblock .cv{font-size:22px;font-weight:700;margin-top:2px}
.cblock .cv span{font-size:13px;font-weight:550;margin-left:6px}
.cbar{height:6px;background:var(--line);border-radius:6px;overflow:hidden;margin:9px 0 11px}
.cbar i{display:block;height:100%;border-radius:6px}
.kv{display:grid;grid-template-columns:1fr auto;gap:5px 12px;font-size:12.5px}
.kv span:nth-child(odd){color:var(--muted)}
.kv span:nth-child(even){text-align:right;font-variant-numeric:tabular-nums}
.buybox{display:flex;gap:8px;align-items:center;margin-top:10px}
.buybox .field{width:150px}
.note.ok{background:var(--good-bg);color:var(--good)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 10px}
.tabs button{all:unset;cursor:pointer;font-size:12.5px;padding:5px 11px;border-radius:20px;background:var(--panel2);border:1px solid var(--line);color:var(--muted)}
.tabs button.on{background:var(--raise);color:var(--text);border-color:var(--line2)}
.tabs button span{color:var(--dim);margin-left:5px}
.results{max-height:460px;overflow:auto;border:1px solid var(--line);border-radius:10px}
.res{display:flex;align-items:center;gap:10px;padding:8px 10px 8px 12px;border-bottom:1px solid var(--line)}
.res:last-child{border-bottom:0}
.res:hover{background:var(--panel2)}
.res .n{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.res .muted{font-size:12px}
.star{all:unset;cursor:pointer;color:var(--dim);font-size:17px;line-height:1;padding:2px 4px}
.star:hover{color:#ecc8ff}
.star.on{color:#d46bff}
.btn.sm{padding:5px 10px;font-size:12px}
.btn.done{color:var(--good);border-color:rgba(95,214,122,.4);background:transparent}
.chip .star{font-size:15px;padding:0}
.catrow{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}
.catrow:last-of-type{border-bottom:0}
.catrow b{font-weight:600}
.catrow small{display:block;color:var(--muted);font-size:12px}
.status{font-size:11px;font-weight:650;padding:2px 8px;border-radius:20px;white-space:nowrap}
.status.holding{background:var(--blue-bg);color:var(--blue)}
.status.listed{background:rgba(232,184,74,.14);color:var(--accent)}
.status.sold{background:var(--good-bg);color:var(--good)}
.inline{display:flex;gap:6px;align-items:center;justify-content:flex-end}
.inline .field{width:120px;padding:5px 8px}
.neg{color:var(--bad);font-weight:700}
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
      <button data-view="buys"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 8h14l-1.2 11.2a2 2 0 01-2 1.8H8.2a2 2 0 01-2-1.8z"/><path d="M9 8V6a3 3 0 016 0v2"/><path d="M9.5 14l2 2 3.5-4"/></svg>Мои покупки<span class="cnt" id="cntBuys" style="background:var(--good);color:#06210f"></span></button>
      <button data-view="settings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.6 1.6 0 00-1.8-.3 1.6 1.6 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.6 1.6 0 00-1-1.5 1.6 1.6 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.6 1.6 0 00.3-1.8 1.6 1.6 0 00-1.5-1H3a2 2 0 110-4h.1a1.6 1.6 0 001.5-1 1.6 1.6 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.6 1.6 0 001.8.3H9a1.6 1.6 0 001-1.5V3a2 2 0 114 0v.1a1.6 1.6 0 001 1.5 1.6 1.6 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.6 1.6 0 00-.3 1.8V9a1.6 1.6 0 001.5 1H21a2 2 0 110 4h-.1a1.6 1.6 0 00-1.5 1z"/></svg>Настройки</button>
      <button data-view="access"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/></svg>Доступ</button>
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
        <select class="field" id="fCat" title="Категория"><option value="all">Все категории</option><option value="artefact">Артефакты</option><option value="armor">Броня</option><option value="weapon">Оружие</option><option value="parts">Запчасти</option><option value="tools">Инструменты</option><option value="other">Остальное</option></select>
        <select class="field" id="fChance" title="Шанс продажи за сутки"><option value="0">Любой шанс</option><option value="30">Шанс от 30%</option><option value="50">Шанс от 50%</option><option value="70">Шанс от 70%</option></select>
        <input class="field small num" id="fProfit" placeholder="Прибыль от, ₽" inputmode="numeric">
        <button class="toggle rare" id="fRare" title="Только особо редкие находки">💎 Редкие</button>
        <button class="toggle" id="fFresh" title="Выставлены меньше 30 минут назад">Свежие</button>
        <div class="spacer"></div>
        <label class="muted" style="font-size:13px"><input type="checkbox" id="hideOld" checked> скрывать проданные и истёкшие</label>
        <button class="btn ghost" id="fReset">Сбросить</button>
        <button class="btn ghost" id="clearBtn">Очистить</button>
      </div>
      <div class="tablewrap" id="tableWrap">
        <table>
          <thead><tr>
            <th data-s="name">Предмет</th><th data-s="amount">Кол-во</th><th data-s="unit">Цена / шт</th><th data-s="market">Рынок / шт</th>
            <th data-s="profit" class="sorted">Прибыль ↓</th><th data-s="pct">Ниже рынка</th><th data-s="chance" title="Шанс продать за сутки по цене перепродажи — оценка трекера">Шанс</th><th data-s="listed">Выставлен</th><th data-s="ends">Активен до</th>
          </tr></thead>
          <tbody id="rows"></tbody>
        </table>
        <div class="empty" id="empty"><div><div class="radar"></div><h3 id="emptyH">Пока ничего не найдено</h3><div id="emptyT">Нажми «Запустить» — трекер начнёт проверять аукцион.</div></div></div>
      </div>
    </section>

    <section class="view" id="view-items">
      <div class="grid2">
        <div class="card">
          <h3>Каталог предметов</h3>
          <div class="sub">Найди предмет и нажми «Следить». ★ — особо редкий: о нём отдельное уведомление.</div>
          <input class="field" id="catSearch" placeholder="Поиск: Морфин, Вихрь, запчасти, броня…" autocomplete="off" style="width:100%">
          <div class="tabs" id="catTabs"></div>
          <div class="results" id="catResults"><div class="res muted">Загружаю базу предметов…</div></div>
          <div class="muted" id="catMore" style="font-size:12px;margin-top:8px"></div>
        </div>
        <div class="col">
        <div class="card">
          <h3>Мой список <span class="muted" id="watchCnt" style="font-weight:500"></span></h3>
          <div class="chips" id="chips"></div>
          <div class="muted" id="chipsEmpty" style="margin-top:12px">Список пуст.</div>
        </div>
        <div class="card">
          <h3>Категории целиком</h3>
          <div class="sub">Трекер сам проверит все предметы категории, даже если их нет в твоём списке.</div>
          <div class="catrow art-head"><div><b>Артефакты</b><small id="artSub">все артефакты из базы игры</small></div><label class="switch"><input type="checkbox" id="sAllArts" data-cat="artefact"><i></i></label></div>
          <div class="catrow"><div><b>Броня</b><small data-cnt="armor"></small></div><label class="switch"><input type="checkbox" data-cat="armor"><i></i></label></div>
          <div class="catrow"><div><b>Оружие</b><small data-cnt="weapon"></small></div><label class="switch"><input type="checkbox" data-cat="weapon"><i></i></label></div>
          <div class="catrow"><div><b>Запчасти</b><small data-cnt="parts"></small></div><label class="switch"><input type="checkbox" data-cat="parts"><i></i></label></div>
          <div class="catrow"><div><b>Инструменты</b><small data-cnt="tools"></small></div><label class="switch"><input type="checkbox" data-cat="tools"><i></i></label></div>
          <div class="note" id="catNote" style="margin-bottom:0">Каждый предмет — 1–2 запроса к API за проверку (лимит EXBO — 400 в минуту). Чем больше предметов, тем реже проверка каждого. Цена брони и оружия зависит от заточки — находки по ним проверяй в игре.</div>
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

    <section class="view" id="view-buys">
      <div class="kpis">
        <div class="kpi"><div class="l">Вложено в товар</div><div class="v num" id="bInv">0 ₽</div><div class="s" id="bInvS">ещё не продано</div></div>
        <div class="kpi"><div class="l">Ожидаемая прибыль</div><div class="v num good" id="bExp">0 ₽</div><div class="s">по текущим ценам, после комиссии</div></div>
        <div class="kpi"><div class="l">Заработано</div><div class="v num" id="bEarn">0 ₽</div><div class="s" id="bEarnS">по проданным</div></div>
        <div class="kpi"><div class="l">Продано</div><div class="v num" id="bSold">0</div><div class="s" id="bSoldS">сделок</div></div>
      </div>
      <div class="toolbar">
        <div class="seg" id="bSeg"><button data-b="open" class="on">Не проданы</button><button data-b="sold">Проданы</button><button data-b="all">Все</button></div>
        <div class="spacer"></div>
        <span class="muted" style="font-size:13px">Купил лот из находок — открой его карточку и нажми «✓ Я купил».</span>
      </div>
      <div class="tablewrap">
        <table>
          <thead><tr><th>Предмет</th><th>Кол-во</th><th>Купил за</th><th>Продать по</th><th>Прибыль</th><th>Шанс</th><th>Куплено</th><th></th></tr></thead>
          <tbody id="bRows"></tbody>
        </table>
        <div class="empty" id="bEmpty"><div><div class="radar"></div><h3 id="bEmptyH">Пока нет покупок</h3><div id="bEmptyT">Купил лот из находок — открой его карточку и нажми «✓ Я купил». Трекер будет следить за его ценой и шансом продажи.</div></div></div>
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
          <h3>Особо редкие</h3>
          <div class="sub">Отдельный звук, пометка 💎 и сообщение в Telegram с заголовком «ОСОБО РЕДКИЙ».</div>
          <div class="row"><label>Отдельные уведомления</label><label class="switch"><input type="checkbox" id="sRare"><i></i></label></div>
          <div class="row w2"><label>Артефакты от качества</label><select class="field" id="sRareQ"><option value="3">редкий</option><option value="4">исключительный</option><option value="5">легендарный</option></select></div>
          <div class="row"><label>Минимальная прибыль для них<small>после комиссии, ₽ — можно ниже обычной</small></label><input class="field num" id="sRareProfit" inputmode="numeric"></div>
          <div class="note" style="margin-bottom:0">Ещё особо редкими считаются снаряжение ранга «Легенда» и всё, что отмечено звёздочкой ★ во вкладке «Предметы».</div>
        </div>
        <div class="card">
          <h3>Шанс продажи</h3>
          <div class="sub">Оценка трекера: насколько вероятно продать лот за сутки по цене перепродажи. Считается по частоте сделок, цене, конкурентам и тренду.</div>
          <div class="row"><label>Сообщать, только если шанс от<small>%, звук и Telegram; особо редкие — всегда. 0 — обо всех</small></label><input class="field num" id="sMinChance" inputmode="numeric"></div>
        </div>
        <div class="card">
          <h3>Telegram</h3>
          <div class="sub">Необязательно. Уведомления о находках придут тебе на телефон.</div>
          <div class="row wide"><label>Токен бота<small>создай бота у @BotFather</small></label><input class="field" id="sTgToken" type="password" autocomplete="off"></div>
          <div class="row wide"><label>Chat ID<small>число от @userinfobot; у своего бота нажми Start</small></label><input class="field" id="sTgChat" autocomplete="off"></div>
          <div class="linkrow"><button class="btn" id="tgTestBtn">Проверить Telegram</button><button class="btn" data-open="botfather">Открыть @BotFather</button></div>
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
          <div class="note">Поделиться с другом: дай ему ссылку на программу и код доступа (раздел «Доступ»). Твои ключи и находки в .exe не попадают. Другу нужны свои ключи API: пусть отправит /newapp боту @stalzone_api_bot.</div>
        </div>
      </div>
      <div class="savebar"><span class="muted" id="saveHint" style="align-self:center"></span><button class="btn primary" id="saveBtn">Сохранить</button></div>
    </section>

    <section class="view" id="view-access">
      <div class="form">
        <div class="col">
        <div class="card">
          <h3>Этот компьютер</h3>
          <div class="sub">По ID компьютера владелец выдаёт код доступа. Код работает только на этом ПК.</div>
          <div class="idrow"><b class="num" id="accMachine">—</b><button class="btn" id="accCopyId">Копировать ID</button></div>
          <div class="note" id="accStatus"></div>
          <div id="accCodeBox">
            <div class="row wide"><label>Новый код доступа<small>если владелец прислал новый или продлил старый</small></label><textarea class="field code" id="accCode" placeholder="SZ1-…"></textarea></div>
            <div class="linkrow"><button class="btn" id="accCodeBtn">Применить код</button></div>
          </div>
        </div>
        <div class="card" id="ownerSetup">
          <h3>Для владельца программы</h3>
          <div class="sub" id="osSub">Закрытый доступ включается один раз: владелец создаёт личный ключ, а его открытая часть вписывается в программу.</div>
          <div class="linkrow" id="osNoKey"><button class="btn primary" id="osCreate">Создать ключ владельца</button></div>
          <div id="osHasKey" hidden>
            <div class="row wide"><label>Открытый ключ<small>его не страшно показывать — по нему программа проверяет коды</small></label><textarea class="field code" id="osPub" readonly></textarea></div>
            <div class="linkrow"><button class="btn" id="osCopy">Копировать ключ</button><button class="btn" data-opendata="1">Открыть папку с ключом</button></div>
          </div>
          <div class="note warn" id="osWarn" hidden>Личный ключ — файл owner_key.pem в папке данных. Сделай копию (флешка, облако) и никому не отправляй: с ним можно выдавать коды от твоего имени.</div>
        </div>
        </div>
        <div class="col">
        <div class="card" id="ownerIssue" hidden>
          <h3>Выдать доступ</h3>
          <div class="sub">Друг запускает программу, видит ID своего компьютера и присылает тебе.</div>
          <div class="row wide"><label>Имя<small>по нему потом можно отозвать доступ</small></label><input class="field" id="isName" autocomplete="off"></div>
          <div class="row wide"><label>ID компьютера друга</label><input class="field" id="isMachine" placeholder="ABCDE-23456" autocomplete="off"></div>
          <div class="row"><label>Срок<small>дней, 0 — бессрочно</small></label><input class="field num" id="isDays" value="30" inputmode="numeric"></div>
          <div class="linkrow"><button class="btn primary" id="isBtn">Создать код</button></div>
          <div id="isResult" hidden>
            <div class="row wide"><label>Код для друга<small>отправь целиком, вместе со ссылкой на программу</small></label><textarea class="field code" id="isCode" readonly></textarea></div>
            <div class="linkrow"><button class="btn" id="isCopy">Копировать код</button><button class="btn" id="isCopyLink">Копировать ссылку на программу</button></div>
          </div>
        </div>
        <div class="card" id="ownerList" hidden>
          <h3>Выданные коды</h3>
          <div class="sub">Отозвать доступ: впиши имя или номер кода отдельной строкой в файл revoked.txt на GitHub. Программа у друга заметит это в течение трёх часов и остановится.</div>
          <div class="issued" id="issuedList"></div>
          <div class="linkrow"><button class="btn" data-open="revoked_new">Создать revoked.txt</button><button class="btn" data-open="revoked_edit">Изменить revoked.txt</button></div>
        </div>
        </div>
      </div>
    </section>

    <section class="view" id="view-log"><div class="log" id="log"></div></section>
  </main>
</div>

<aside class="drawer" id="drawer"></aside>
<div class="overlay" id="restartOverlay" hidden><div><div class="radar"></div><h2>Устанавливаю обновление</h2><div class="muted">Программа закроется и через несколько секунд откроется уже новой версией.</div></div></div>
<div class="overlay" id="lockOverlay" hidden><div class="lock">
  <div class="logo">◈</div>
  <h2>Закрытый доступ</h2>
  <div class="muted" id="lockReason"></div>
  <div class="idrow"><span class="muted">ID этого компьютера:</span><b class="num" id="lockMachine">—</b><button class="btn" id="lockCopy">Копировать</button></div>
  <div class="muted" style="font-size:13px">Отправь ID владельцу программы — он пришлёт код. Вставь его сюда:</div>
  <textarea class="field code" id="lockCode" placeholder="SZ1-…"></textarea>
  <button class="btn primary" id="lockBtn">Открыть доступ</button>
</div></div>
<div class="toast" id="toast"></div>

<script>
const TOKEN = "__TOKEN__";
const QN = ["обычный","необычный","особый","редкий","исключительный","легендарный"];
const PRESETS = {
  craft: ["Морфин","Янтарная полынь","Хлорид алюминия","Теломераза","Мутаген","Коагулянт","Чертоцвет","Полимеры","Помидор"],
  arts: ["Ледяной ежик","Вихрь","Змеиный глаз","Гелий","Спираль","Батарейка"],
  hot: ["Огромный артефактный фрагмент","Моток медной проволоки","Аммиак","Набор специй","Полимеры"],
};
const TITLES = {deals:"Выгодные лоты", items:"Предметы", buys:"Мои покупки", settings:"Настройки", access:"Доступ", log:"Журнал"};
const FILTER_CATS = ["artefact", "armor", "weapon", "parts", "tools"];
const RANK_RU = {RANK_NEWBIE: "Новичок", RANK_STALKER: "Сталкер", RANK_VETERAN: "Ветеран", RANK_MASTER: "Мастер", RANK_LEGEND: "Легенда"};
const RELEASES_URL = "https://github.com/Enotsbeye/stalzone-tracker-releases/releases/latest";
let S = null, view = "deals", kind = "all", sortKey = "profit", sortDir = -1, selected = null;
let knownIds = new Set(), firstLoad = true, lastErr = 0, formDirty = false;
const $ = (id) => document.getElementById(id);
const rub = (x) => Math.round(x).toLocaleString("ru-RU").replace(/ /g, " ") + " ₽";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const store = { get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
                set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
let CAT = null, CATMAP = {}, CATNAMES = {}, catTab = store.get("catTab", "all"), catLoading = 0;
let F = Object.assign({cat: "all", chance: 0, profit: "", rare: false, fresh: false}, store.get("filters", {}));
let bFilter = store.get("bFilter", "open"), sellOpen = null;

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
function beep(rare) {
  if (!store.get("sound", true)) return;
  try {
    const ctx = beep.ctx || (beep.ctx = new (window.AudioContext || window.webkitAudioContext)());
    const notes = rare ? [[0, 784], [0.12, 988], [0.24, 1319], [0.42, 1568]] : [[0, 880], [0.13, 1180]];
    notes.forEach(([t, f]) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = f; o.type = rare ? "triangle" : "sine";
      g.gain.setValueAtTime(0.0001, ctx.currentTime + t);
      g.gain.exponentialRampToValueAtTime(rare ? 0.22 : 0.18, ctx.currentTime + t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + (rare ? 0.2 : 0.12));
      o.connect(g).connect(ctx.destination); o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.22);
    });
  } catch (e) {}
}
function notifyDesktop(d) {
  try {
    if ("Notification" in window && Notification.permission === "granted")
      new Notification((d.rare ? "💎 Особо редкий: " : "") + d.name + " — прибыль ~" + rub(d.profit),
        { body: (d.kind === "bid" ? "Ставка · " : "Выкуп · ") + d.amount + " шт по " + rub(d.unit) + (d.chance != null ? " · шанс продажи " + Math.round(d.chance * 100) + "%" : "") });
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
function catGroup(c) { return FILTER_CATS.includes(c) ? c : "other"; }
function saveFilters() { store.set("filters", F); }
function syncFilters() {
  $("fCat").value = F.cat; $("fChance").value = String(F.chance || 0); $("fProfit").value = F.profit || "";
  $("fRare").classList.toggle("on", !!F.rare); $("fFresh").classList.toggle("on", !!F.fresh);
}
$("fCat").onchange = () => { F.cat = $("fCat").value; saveFilters(); renderDeals(); };
$("fChance").onchange = () => { F.chance = +$("fChance").value; saveFilters(); renderDeals(); };
$("fProfit").oninput = () => { F.profit = $("fProfit").value.replace(/\D/g, ""); saveFilters(); renderDeals(); };
$("fRare").onclick = () => { F.rare = !F.rare; saveFilters(); syncFilters(); renderDeals(); };
$("fFresh").onclick = () => { F.fresh = !F.fresh; saveFilters(); syncFilters(); renderDeals(); };
$("fReset").onclick = () => { F = {cat: "all", chance: 0, profit: "", rare: false, fresh: false}; $("search").value = ""; saveFilters(); syncFilters(); renderDeals(); };
syncFilters();
function fmtHours(h) { if (h === null || h === undefined) return ""; if (h < 1) return "< 1 ч"; if (h < 48) return "~" + Math.round(h) + " ч"; return "~" + Math.round(h / 24) + " дн."; }
function chanceCls(c) { return c >= 0.7 ? "hi" : c >= 0.4 ? "mid" : "lo"; }
function chanceCell(c, h) {
  if (c === null || c === undefined) return `<span class="muted">—</span>`;
  return `<span class="chance"><b class="${chanceCls(c)}">${Math.round(c * 100)}%</b><small>${fmtHours(h)}</small></span>`;
}
function fateTag(d) {
  if (d.bought) return `<span class="tag mine">✓ Куплено</span>`;
  if (d.fate === "sold") return `<span class="tag fate" title="Лот пропал, и в истории есть сделка ровно на него">уже купили</span>`;
  if (d.fate === "removed") return `<span class="tag fate" title="Лот пропал, а сделки по нему в истории нет">снят</span>`;
  if (d.fate === "expired") return `<span class="tag fate">истёк</span>`;
  if (d.gone) return `<span class="tag fate" title="Лота больше нет — сверяю с историей сделок, купили его или сняли">пропал</span>`;
  return "";
}
function gradeTag(d) {
  if (d.cat === "artefact" || (d.cat == null && d.quality !== null && d.quality !== undefined)) return qualityTag(d);
  return d.ptn ? `<span class="q">+${d.ptn}</span>` : "";
}
function rankTag(d) {
  return d.rank && RANK_RU[d.rank] && ["armor", "weapon", "attachment", "backpacks", "containers"].includes(d.cat)
    ? `<span class="rk ${d.rank}">${RANK_RU[d.rank]}</span>` : "";
}
function visibleDeals() {
  const q = $("search").value.trim().toLowerCase().replace(/ё/g, "е");
  const now = S.now, minProfit = +(F.profit || 0);
  let list = S.deals.filter((d) => (kind === "all" || d.kind === kind)
    && (!q || d.name.toLowerCase().replace(/ё/g, "е").includes(q))
    && (F.cat === "all" || catGroup(d.cat) === F.cat)
    && (!F.chance || (d.chance !== null && d.chance !== undefined && d.chance * 100 >= F.chance))
    && (!minProfit || d.profit >= minProfit)
    && (!F.rare || d.rare)
    && (!F.fresh || (d.listed && now - Date.parse(d.listed) / 1000 < 1800))
    && (!$("hideOld").checked || d.bought || (!d.gone && (!d.ends || Date.parse(d.ends) / 1000 > now))));
  const val = (d) => sortKey === "listed" || sortKey === "ends" ? Date.parse(d[sortKey] || 0)
    : sortKey === "chance" ? (d.chance === null || d.chance === undefined ? -1 : d.chance) : d[sortKey];
  list.sort((a, b) => { const x = val(a), y = val(b); return (typeof x === "string" ? x.localeCompare(y, "ru") : (x - y)) * sortDir; });
  return list;
}
function renderDeals() {
  if (!S) return;
  const list = visibleDeals(), now = S.now;
  $("rows").innerHTML = list.map((d) => {
    const old = !d.bought && (d.gone || (d.ends && Date.parse(d.ends) / 1000 <= now));
    const fresh = now - d.found < 300;
    return `<tr class="lot${selected === d.id ? " sel" : ""}${fresh ? " new" : ""}${old ? " old" : ""}${d.rare ? " rare" : ""}${d.bought ? " mine" : ""}" data-id="${d.id}">
      <td><div class="item"><span class="n">${esc(d.name)}</span><span class="tags"><span class="tag ${d.kind === "bid" ? "bid" : "buy"}">${d.kind === "bid" ? "Ставка" : "Выкуп"}</span>${d.rare ? `<span class="tag rare">💎 редкий</span>` : ""}${gradeTag(d)}${rankTag(d)}${fateTag(d)}${d.stale && !d.gone ? `<span class="tag stale" title="${esc(d.stale)}">давно висит</span>` : ""}</span></div></td>
      <td class="num">${d.amount} шт</td>
      <td class="num">${rub(d.unit)}</td>
      <td class="num muted">${rub(d.market)}</td>
      <td class="num profit">+${rub(d.profit)}</td>
      <td><span class="pct num">−${Math.round(d.pct)}%</span></td>
      <td>${chanceCell(d.chance, d.sell_hours)}</td>
      <td class="muted">${ago(d.listed, now)}</td>
      <td class="muted">${until(d.ends)}</td></tr>`;
  }).join("");
  const empty = list.length === 0;
  $("empty").style.display = empty ? "grid" : "none";
  if (empty) {
    if (S.status.running && !S.deals.length) {
      const total = (S.status.progress && S.status.progress.total) || S.status.total || watchTotal();
      $("emptyH").textContent = "Ищу выгодные лоты…";
      $("emptyT").textContent = `Проверяю ${total} предм. каждые ${S.settings.poll_minutes} мин. Как только что-то найдётся — появится здесь.`;
    }
    else if (S.deals.length) { $("emptyH").textContent = "Под фильтры ничего не подходит"; $("emptyT").textContent = "Нажми «Сбросить» или покажи проданные и истёкшие."; }
    else { $("emptyH").textContent = "Пока ничего не найдено"; $("emptyT").textContent = "Нажми «Запустить» — трекер начнёт проверять аукцион."; }
  }
  document.querySelectorAll("tr.lot").forEach((tr) => tr.onclick = () => openDrawer(+tr.dataset.id));
}
function chanceBlock(c) {
  if (!c) return `<div class="cblock"><div class="l">Шанс продать за сутки</div><div class="muted" style="margin-top:4px">Мало данных, чтобы оценить.</div></div>`;
  const p = Math.round(c.chance * 100), cls = chanceCls(c.chance);
  const col = cls === "hi" ? "var(--good)" : cls === "mid" ? "var(--accent)" : "var(--bad)";
  const lbl = cls === "hi" ? "высокий" : cls === "mid" ? "средний" : "низкий";
  const n1 = (x) => (x >= 10 ? Math.round(x) : Math.round(x * 10) / 10).toLocaleString("ru-RU");
  return `<div class="cblock">
    <div class="l">Шанс продать за сутки по цене перепродажи</div>
    <div class="cv" style="color:${col}">${p}%<span>${lbl}${c.hours !== null && c.hours !== undefined ? " · обычно за " + fmtHours(c.hours).replace("~", "") : ""}</span></div>
    <div class="cbar"><i style="width:${p}%;background:${col}"></i></div>
    <div class="kv">
      <span>Сделок в сутки по такому товару</span><span>${n1(c.per_day)}</span>
      <span>Платили не меньше этой цены</span><span>${Math.round(c.share * 100)}% сделок</span>
      <span>Нужно покупателей</span><span>${c.need}${c.need > 1 ? " (обычно берут по " + Math.round(c.size) + " шт)" : ""}</span>
      <span>Похожих лотов почти по той же цене</span><span>${c.comp}</span>
      ${c.trend_f !== 1 ? `<span>Поправка: рынок ${c.trend_f < 1 ? "падает" : "растёт"}</span><span>×${c.trend_f.toFixed(2)}</span>` : ""}
      ${c.stale_f !== 1 ? `<span>Поправка: лот давно не покупают</span><span>×${c.stale_f.toFixed(2)}</span>` : ""}
    </div>
    <div class="muted" style="font-size:12px;margin-top:9px">Оценка по формуле трекера, а не гарантия: API не показывает, сколько людей хотят купить.</div>
  </div>`;
}
function rareMarks() { return (S.settings.rare_items || []).map((x) => String(x).toLowerCase().replace(/ё/g, "е")); }
function isStarred(id, name) { const m = rareMarks(); return m.includes(String(id).toLowerCase()) || (name && m.includes(name.toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, ""))); }
async function toggleStar(id, name) {
  let list = (S.settings.rare_items || []).slice();
  const marks = rareMarks(), on = isStarred(id, name);
  if (on) list = list.filter((x, i) => marks[i] !== String(id).toLowerCase() && marks[i] !== (name || "").toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, ""));
  else list.push(id || name);
  const r = await api("/api/settings", {rare_items: list});
  toast(r.ok ? (on ? "Звёздочка снята: " : "★ Особо редкий: ") + (name || id) : r.message, !r.ok);
  await refresh();
}
function openDrawer(id) {
  const d = S.deals.find((x) => x.id === id); if (!d) return;
  selected = id; renderDeals();
  const bid = d.kind === "bid";
  const star = isStarred(d.item_id, d.name);
  $("drawer").innerHTML = `
    <button class="close" id="dClose">✕</button>
    <span class="tag ${bid ? "bid" : "buy"}">${bid ? "Ставка" : "Выкуп"}</span> ${d.rare ? `<span class="tag rare">💎 особо редкий</span>` : ""} ${gradeTag(d)} ${rankTag(d)} ${fateTag(d)}
    <h2>${esc(d.name)}</h2>
    <div class="muted">${d.amount} шт · дешевле рынка на ${Math.round(d.pct)}%${d.cat && CATNAMES[d.cat] ? " · " + esc(CATNAMES[d.cat]) : ""}</div>
    <div class="big num">+${rub(d.profit)}</div>
    <div class="muted">возможная прибыль · ${Math.round(d.roi)}% к вложенному</div>
    <div class="calc num">
      <div><span>${bid ? (d.has_bids ? "Текущая ставка" : "Стартовая цена") : "Купить"}<small>${d.amount} шт по ${rub(d.unit)}</small></span><span>${rub(d.cost)}</span></div>
      <div><span>Перепродать<small>по ~${rub(d.market)} за шт</small></span><span>${rub(d.resale)}</span></div>
      <div><span>Комиссия аукциона 5%</span><span>−${rub(d.resale * 0.05)}</span></div>
      <div><span>Прибыль</span><span>+${rub(d.profit)}</span></div>
    </div>
    ${chanceBlock(d.chance_info)}
    ${d.bought ? `<div class="note ok">✓ Отмечено как купленное — цена и шанс продажи теперь во вкладке «Мои покупки».</div>`
      : `<div class="buybox"><input class="field num" id="dPaid" value="${Math.round(d.cost)}" title="Сколько заплатил за весь лот"><button class="btn primary" id="dBuy">✓ Я купил</button></div>
         <div class="muted" style="font-size:12px;margin-top:6px">Впиши, сколько реально заплатил, — трекер будет следить за ценой и считать прибыль.</div>`}
    ${d.fate === "sold" ? `<div class="note warn">Этот лот уже купили — в истории есть сделка ровно на него.</div>`
      : d.gone && !d.bought ? `<div class="note warn">Этого лота больше нет на аукционе${d.fate === "removed" ? " — его сняли" : d.fate === "expired" ? " — время вышло" : " — сверяю с историей сделок, купили его или сняли"}.</div>` : ""}
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
      : "Такого же или лучше лота на аукционе сейчас нет — цена продажи только по прошлым сделкам, это менее надёжно."} Данные API запаздывают — проверь лот в игре перед покупкой.</div>
    ${d.cat === "artefact" || (d.cat == null && d.quality !== null && d.quality !== undefined) ? `<div class="note">Артефакт: цена зависит ещё от процента качества и доп. свойств — сравни лот в игре с другими того же качества и заточки.</div>` : ""}
    ${["armor", "weapon"].includes(d.cat) ? `<div class="note">Цена брони и оружия сильно зависит от заточки и состояния — сравни лот в игре с такими же.</div>` : ""}
    <div class="actions"><button class="btn" id="dCopy">Скопировать название</button><button class="btn" id="dStar">${star ? "★ Особо редкий" : "☆ Особо редкий"}</button><button class="btn" id="dHide">Скрыть</button></div>`;
  $("drawer").classList.add("on");
  $("dClose").onclick = closeDrawer;
  $("dCopy").onclick = () => copyText(d.name);
  $("dStar").onclick = async () => { await toggleStar(d.item_id, d.name); openDrawer(d.id); };
  $("dHide").onclick = async () => { await api("/api/deals/remove", {id: d.id}); closeDrawer(); refresh(); };
  if ($("dBuy")) $("dBuy").onclick = async () => {
    const r = await api("/api/purchases/add", {deal_id: d.id, paid: $("dPaid").value.replace(/\s/g, "").replace(",", ".")});
    toast(r.message, !r.ok); await refresh(); if (r.ok) openDrawer(d.id);
  };
}
function closeDrawer() { $("drawer").classList.remove("on"); selected = null; if (S) renderDeals(); }
function copyText(t, msg) {
  const done = () => toast(msg || "Скопировано — вставь в поиск аукциона");
  if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(t).then(done, () => fallback()); } else fallback();
  function fallback() { const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select(); try { document.execCommand("copy"); done(); } catch (e) {} a.remove(); }
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

// ---------- предметы ----------
function watch() { return S ? S.settings.watch.slice() : []; }
async function saveWatch(list, msg, warn) { const r = await api("/api/settings", {watch: list}); toast(r.ok ? (msg || "Список обновлён") : r.message, !r.ok || !!warn); await refresh(); }
const normName = (n) => String(n || "").toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, "").trim();
function entryName(w) { return CATMAP[w] ? CATMAP[w].name : w; }
function inWatch(e) { return watch().some((w) => w === e.id || normName(w) === normName(e.name)); }
function addItem(name, unknown) {
  name = (name || "").trim(); if (!name) return;
  const list = watch();
  if (list.some((x) => normName(entryName(x)) === normName(name))) { toast("Уже в списке"); return; }
  list.push(name);
  saveWatch(list, unknown ? "«" + name + "» нет в базе игры — проверь написание" : "Добавлено: " + name, unknown);
}
function addEntry(e) {
  const list = watch();
  if (inWatch(e)) { toast("Уже в списке"); return; }
  // одинаковые названия бывают у разных предметов — тогда храним id
  const dup = CAT && CAT.filter((x) => normName(x.name) === normName(e.name)).length > 1;
  list.push(dup ? e.id : e.name);
  saveWatch(list, "Добавлено: " + e.name);
}
function removeEntry(e) { saveWatch(watch().filter((w) => w !== e.id && normName(w) !== normName(e.name)), "Убрано: " + e.name); }
function plural(n, forms) {
  const a = n % 10, b = n % 100;
  return forms[a === 1 && b !== 11 ? 0 : a >= 2 && a <= 4 && (b < 12 || b > 14) ? 1 : 2];
}
function autoCount() { return (S.auto_cats || []).reduce((s, c) => s + (S.cat_counts[c] || (c === "artefact" ? S.artifacts : 0) || 0), 0); }
function watchTotal() { return watch().length + (S ? autoCount() : 0); }
async function loadCatalog() {
  if (CAT || Date.now() - catLoading < 4000) return;
  catLoading = Date.now();
  try {
    const r = await api("/api/catalog");
    if (r.items && r.items.length) {
      CAT = r.items; CATNAMES = r.names || {}; CATMAP = {};
      CAT.forEach((e) => CATMAP[e.id] = e);
      renderCatalog(true); renderChips();
    }
  } catch (e) {}
}
function renderTabs() {
  const counts = {};
  (CAT || []).forEach((e) => { if (e.trade) counts[e.cat] = (counts[e.cat] || 0) + 1; });
  const order = ["all", "artefact", "armor", "weapon", "parts", "tools", "attachment", "misc", "supply", "bullet", "containers", "backpacks", "grenade", "other"];
  $("catTabs").innerHTML = order.filter((c) => c === "all" || counts[c]).map((c) =>
    `<button data-c="${c}" class="${c === catTab ? "on" : ""}">${c === "all" ? "Все" : esc(CATNAMES[c] || c)}<span>${c === "all" ? (CAT || []).filter((e) => e.trade).length : counts[c]}</span></button>`).join("");
  $("catTabs").querySelectorAll("button").forEach((b) => b.onclick = () => { catTab = b.dataset.c; store.set("catTab", catTab); renderCatalog(); $("catResults").scrollTop = 0; });
}
let lastCatSig = "";
function renderCatalog(force) {
  if (!CAT) return;
  const sig = [catTab, $("catSearch").value, watch().join("|"), (S.settings.rare_items || []).join("|")].join("#");
  if (!force && sig === lastCatSig) return;
  lastCatSig = sig;
  renderTabs();
  const q = normName($("catSearch").value);
  const words = q.split(/\s+/).filter(Boolean);
  let list = CAT.filter((e) => e.trade && (catTab === "all" || e.cat === catTab)
    && (!words.length || words.every((w) => normName(e.name).includes(w) || normName(CATNAMES[e.cat] || "").startsWith(w))));
  if (q) list.sort((a, b) => (normName(b.name).startsWith(q) - normName(a.name).startsWith(q)) || a.name.localeCompare(b.name, "ru"));
  else list.sort((a, b) => a.name.localeCompare(b.name, "ru"));
  const shown = list.slice(0, 120);
  $("catResults").innerHTML = shown.map((e) => {
    const on = inWatch(e), star = isStarred(e.id, e.name);
    return `<div class="res"><button class="star${star ? " on" : ""}" data-star="${e.id}" title="Особо редкий — отдельное уведомление">${star ? "★" : "☆"}</button>
      <span class="n">${esc(e.name)}</span>${e.rank && RANK_RU[e.rank] ? `<span class="rk ${e.rank}">${RANK_RU[e.rank]}</span>` : ""}
      <span class="tag cat">${esc(CATNAMES[e.cat] || e.cat)}</span>
      <button class="btn sm${on ? " done" : ""}" data-add="${e.id}">${on ? "✓ В списке" : "+ Следить"}</button></div>`;
  }).join("") || `<div class="res muted">Ничего не нашёл — попробуй часть названия или другую вкладку.</div>`;
  $("catMore").textContent = list.length > shown.length ? `Показано ${shown.length} из ${list.length} — уточни поиск.` : (list.length ? `Найдено: ${list.length}` : "");
  $("catResults").querySelectorAll("[data-add]").forEach((b) => b.onclick = () => { const e = CATMAP[b.dataset.add]; inWatch(e) ? removeEntry(e) : addEntry(e); });
  $("catResults").querySelectorAll("[data-star]").forEach((b) => b.onclick = async () => { const e = CATMAP[b.dataset.star]; await toggleStar(e.id, e.name); renderCatalog(); });
}
$("catSearch").oninput = () => renderCatalog();
$("catSearch").onkeydown = (e) => {
  if (e.key !== "Enter" || !CAT) return;
  const q = normName($("catSearch").value); if (!q) return;
  const exact = CAT.find((x) => x.trade && normName(x.name) === q);
  if (exact) addEntry(exact); else addItem($("catSearch").value, true);
};
function renderChips() {
  const list = watch(), cats = S.auto_cats || [];
  $("chips").innerHTML = list.map((w, i) => {
    const e = CATMAP[w] || (CAT || []).find((x) => normName(x.name) === normName(w));
    const name = e ? e.name : w, star = isStarred(e ? e.id : w, name);
    return `<span class="chip"><button class="star${star ? " on" : ""}" data-s="${i}" title="Особо редкий">${star ? "★" : "☆"}</button>${esc(name)}${e && e.cat !== "artefact" && CATNAMES[e.cat] ? ` <span class="muted" style="font-size:11px">${esc(CATNAMES[e.cat])}</span>` : ""}<button title="Убрать" data-i="${i}">✕</button></span>`;
  }).join("");
  $("chipsEmpty").style.display = list.length ? "none" : "block";
  $("chipsEmpty").textContent = cats.length === 1 && cats[0] === "artefact" ? "Свой список пуст — проверяются только все артефакты."
    : cats.length ? "Свой список пуст — проверяются только категории целиком." : "Список пуст.";
  $("watchCnt").textContent = list.length ? "· " + list.length : "";
  $("chips").querySelectorAll("[data-i]").forEach((b) => b.onclick = () => { const l = watch(); l.splice(+b.dataset.i, 1); saveWatch(l, "Убрано"); });
  $("chips").querySelectorAll("[data-s]").forEach((b) => b.onclick = () => {
    const w = watch()[+b.dataset.s], e = CATMAP[w] || (CAT || []).find((x) => normName(x.name) === normName(w));
    toggleStar(e ? e.id : w, e ? e.name : w);
  });
  $("cntItems").textContent = watchTotal() || "";
  document.querySelectorAll("[data-cat]").forEach((el) => el.checked = cats.includes(el.dataset.cat));
  const arts = S.cat_counts.artefact || S.artifacts;
  $("artSub").textContent = arts ? `все ${arts} ${plural(arts, ["артефакт", "артефакта", "артефактов"])} из базы игры` : "все артефакты из базы игры";
  document.querySelectorAll("[data-cnt]").forEach((el) => {
    const n = S.cat_counts[el.dataset.cnt];
    el.textContent = n ? `${n} ${plural(n, ["предмет", "предмета", "предметов"])}${n > 100 ? " · проверка станет дольше на ~" + Math.max(1, Math.round(n * 1.2 / 340)) + " мин" : ""}` : "";
  });
  if (CAT && view === "items") renderCatalog();
}
document.querySelectorAll("[data-cat]").forEach((el) => el.onchange = async () => {
  const cats = [...document.querySelectorAll("[data-cat]")].filter((x) => x.checked).map((x) => x.dataset.cat);
  const r = await api("/api/settings", {auto_categories: cats});
  const name = el.closest(".catrow").querySelector("b").textContent;
  if (!r.ok) toast(r.message, true);
  else toast((el.checked ? (el.dataset.cat === "artefact" ? "Все артефакты включены" : name + ": включено целиком") : (el.dataset.cat === "artefact" ? "Все артефакты выключены" : name + ": выключено")) + (S.status.running ? " — трекер перезапускается" : ""));
  refresh();
});
document.querySelectorAll("[data-preset]").forEach((b) => b.onclick = () => {
  const list = watch(), add = PRESETS[b.dataset.preset].filter((n) => !list.some((x) => normName(entryName(x)) === normName(n)));
  if (!add.length) return toast("Всё из набора уже в списке");
  saveWatch(list.concat(add), "Добавлено: " + add.length);
});

// ---------- мои покупки ----------
$("bSeg").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; bFilter = b.dataset.b; store.set("bFilter", bFilter); renderPurchases(); };
function pUnit(p) { return p.cur_market || p.target; }
function pExpected(p) { return pUnit(p) * p.amount * (1 - S.settings.fee) - p.paid; }
const STATUS_RU = {holding: "в инвентаре", listed: "выставлен", sold: "продан"};
function renderPurchases() {
  const all = S.purchases || [];
  [...$("bSeg").children].forEach((x) => x.classList.toggle("on", x.dataset.b === bFilter));
  const open = all.filter((p) => p.status !== "sold"), sold = all.filter((p) => p.status === "sold");
  const sum = (a, f) => a.reduce((s, p) => s + f(p), 0);
  $("bInv").textContent = rub(sum(open, (p) => p.paid)); $("bInvS").textContent = open.length + " " + plural(open.length, ["покупка", "покупки", "покупок"]) + " не продано";
  const exp = sum(open, pExpected); $("bExp").textContent = (exp >= 0 ? "+" : "−") + rub(Math.abs(exp));
  $("bExp").className = "v num " + (exp >= 0 ? "good" : "neg");
  const earn = sum(sold, (p) => p.profit || 0); $("bEarn").textContent = (earn >= 0 ? "+" : "−") + rub(Math.abs(earn));
  $("bEarn").className = "v num " + (earn >= 0 ? "good" : "neg");
  $("bSold").textContent = sold.length; $("bSoldS").textContent = sold.length ? `в плюс — ${sold.filter((p) => (p.profit || 0) > 0).length}` : "сделок";
  $("cntBuys").textContent = open.length || "";
  const list = all.filter((p) => bFilter === "all" || (bFilter === "open" ? p.status !== "sold" : p.status === "sold"));
  if (document.activeElement && $("bRows").contains(document.activeElement) && document.activeElement.tagName === "INPUT") return;
  $("bRows").innerHTML = list.map((p) => {
    const unit = pUnit(p), profit = p.status === "sold" ? (p.profit || 0) : pExpected(p);
    const c = p.cur_chance;
    const fresh = p.cur_at ? `<small class="muted" style="display:block;font-size:11px">${p.cur_market ? "цена " + ago(new Date(p.cur_at * 1000).toISOString(), S.now) : "рынка сейчас нет"}</small>` : `<small class="muted" style="display:block;font-size:11px">на момент покупки</small>`;
    const grade = p.quality !== null && p.quality !== undefined && (p.cat === "artefact" || p.cat == null) ? qualityTag(p) : (p.ptn ? `<span class="q">+${p.ptn}</span>` : "");
    const actions = p.status === "sold" ? `<button class="btn sm" data-reopen="${p.id}">Вернуть</button>`
      : sellOpen === p.id ? `<span class="inline"><input class="field num" id="sellPrice" value="${Math.round(unit * p.amount)}" title="За сколько продал весь лот"><button class="btn sm primary" data-sold="${p.id}">Сохранить</button></span>`
      : `${p.status === "holding" ? `<button class="btn sm" data-listed="${p.id}">Выставил</button>` : `<button class="btn sm" data-hold="${p.id}">Снял</button>`}<button class="btn sm" data-sell="${p.id}">Продал…</button>`;
    return `<tr><td><div class="item"><span class="n">${esc(p.name)}</span><span class="tags"><span class="status ${p.status}">${STATUS_RU[p.status] || p.status}</span>${p.rare ? `<span class="tag rare">💎</span>` : ""}${grade}</span></div></td>
      <td class="num">${p.amount} шт</td>
      <td class="num">${rub(p.paid)}<small class="muted" style="display:block;font-size:11px">${rub(p.unit_paid)}/шт</small></td>
      <td class="num">${p.status === "sold" ? rub(p.sold_price) + `<small class="muted" style="display:block;font-size:11px">продал за весь лот</small>` : rub(unit) + "/шт" + fresh}</td>
      <td class="num ${profit >= 0 ? "profit" : "neg"}">${profit >= 0 ? "+" : "−"}${rub(Math.abs(profit))}</td>
      <td>${p.status === "sold" ? "" : chanceCell(c ? c.chance : null, c ? c.hours : null)}</td>
      <td class="muted">${ago(new Date(p.bought_at * 1000).toISOString(), S.now)}</td>
      <td><span class="inline">${actions}<button class="btn sm ghost" data-del="${p.id}" title="Удалить запись">✕</button></span></td></tr>`;
  }).join("");
  const empty = !list.length;
  $("bEmpty").style.display = empty ? "grid" : "none";
  if (empty && all.length) { $("bEmptyH").textContent = bFilter === "sold" ? "Пока ничего не продано" : "Всё продано"; $("bEmptyT").textContent = "Переключи фильтр сверху, чтобы увидеть остальные."; }
  else if (empty) { $("bEmptyH").textContent = "Пока нет покупок"; $("bEmptyT").textContent = "Купил лот из находок — открой его карточку и нажми «✓ Я купил». Трекер будет следить за его ценой и шансом продажи."; }
  const upd = async (body) => { const r = await api("/api/purchases/update", body); if (!r.ok) toast(r.message, true); else sellOpen = null; await refresh(); };
  $("bRows").querySelectorAll("[data-listed]").forEach((b) => b.onclick = () => upd({id: b.dataset.listed, status: "listed"}));
  $("bRows").querySelectorAll("[data-hold]").forEach((b) => b.onclick = () => upd({id: b.dataset.hold, status: "holding"}));
  $("bRows").querySelectorAll("[data-reopen]").forEach((b) => b.onclick = () => upd({id: b.dataset.reopen, status: "holding"}));
  $("bRows").querySelectorAll("[data-sell]").forEach((b) => b.onclick = () => { sellOpen = b.dataset.sell; renderPurchases(); const f = $("sellPrice"); if (f) { f.focus(); f.select(); } });
  $("bRows").querySelectorAll("[data-sold]").forEach((b) => b.onclick = () => upd({id: b.dataset.sold, status: "sold", sold_price: $("sellPrice").value.replace(/\s/g, "").replace(",", ".")}));
  $("bRows").querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => { const r = await api("/api/purchases/remove", {id: b.dataset.del}); toast(r.message, !r.ok); await refresh(); });
}

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
  $("sRare").checked = c.rare_enabled !== false; $("sRareQ").value = String(c.rare_quality ?? 4);
  $("sRareProfit").value = Math.round(c.rare_min_profit ?? 5000); $("sMinChance").value = Math.round(c.notify_min_chance || 0);
}
document.querySelectorAll("#view-settings input, #view-settings select").forEach((el) => el.addEventListener("input", () => { formDirty = true; $("saveHint").textContent = "Есть несохранённые изменения"; }));
$("tgTestBtn").onclick = async () => {
  toast("Отправляю тестовое сообщение…");
  const r = await api("/api/telegram/test", {telegram_token: $("sTgToken").value, telegram_chat_id: $("sTgChat").value});
  toast(r.message, !r.ok);
};
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
    rare_enabled: $("sRare").checked, rare_quality: $("sRareQ").value, rare_min_profit: num("sRareProfit"),
    notify_min_chance: num("sMinChance"),
  });
  toast(r.ok ? (S.status.running ? "Сохранено — трекер перезапускается" : "Настройки сохранены") : r.message, !r.ok);
  if (r.ok) { formDirty = false; $("saveHint").textContent = ""; }
  refresh();
};

// ---------- доступ ----------
document.querySelectorAll("[data-opendata]").forEach((b) => b.onclick = () => api("/api/open_data", {}));
$("accCopyId").onclick = () => copyText($("accMachine").textContent, "ID скопирован — отправь его владельцу");
$("lockCopy").onclick = () => copyText($("lockMachine").textContent, "ID скопирован — отправь его владельцу");
async function enterCode(text) {
  const r = await api("/api/access/enter", {code: text});
  toast(r.message, !r.ok);
  refresh();
  return r.ok;
}
$("lockBtn").onclick = () => enterCode($("lockCode").value);
$("accCodeBtn").onclick = async () => { if (await enterCode($("accCode").value)) $("accCode").value = ""; };
$("osCreate").onclick = async () => { const r = await api("/api/access/owner_key", {}); toast(r.message, !r.ok); refresh(); };
$("osCopy").onclick = () => copyText($("osPub").value, "Открытый ключ скопирован");
$("isBtn").onclick = async () => {
  const r = await api("/api/access/issue", {name: $("isName").value, machine: $("isMachine").value, days: $("isDays").value});
  toast(r.message, !r.ok);
  if (r.ok) { $("isCode").value = r.code; $("isResult").hidden = false; $("isName").value = ""; $("isMachine").value = ""; }
  refresh();
};
$("isCopy").onclick = () => copyText($("isCode").value, "Код скопирован — отправь его другу");
$("isCopyLink").onclick = () => copyText(RELEASES_URL, "Ссылка на программу скопирована");
function renderAccess() {
  const a = S.access || {};
  const locked = !!(a.required && !a.ok);
  $("lockOverlay").hidden = !locked;
  if (locked) { $("lockReason").textContent = a.reason || ""; $("lockMachine").textContent = a.machine || "—"; }
  $("accMachine").textContent = a.machine || "—";
  $("accStatus").textContent = !a.required ? "Закрытый доступ ещё не включён — программа открыта всем."
    : a.mode === "owner" ? "Ты владелец программы — код доступа тебе не нужен."
    : a.ok ? `Доступ открыт: ${a.name}, срок — ${a.expires_text}. Номер кода: ${a.code_id}.` : (a.reason || "");
  $("accCodeBox").hidden = !a.required || a.mode === "owner";
  const setup = !a.embedded;                     // ключ ещё не вписан в программу
  $("ownerSetup").hidden = !(setup || a.owner);
  $("osNoKey").hidden = !setup || a.has_owner_key || !a.has_crypto;
  $("osHasKey").hidden = !(setup && a.has_owner_key);
  $("osPub").value = a.owner_public || "";
  $("osSub").textContent = setup ? "Закрытый доступ включается один раз: владелец создаёт личный ключ, а его открытая часть вписывается в программу."
    : "Закрытый доступ включён. Ты владелец: коды выдаёшь в карточке «Выдать доступ».";
  $("osWarn").hidden = !a.has_owner_key || !(setup || a.owner);
  const owner = a.owner && a.embedded;
  $("ownerIssue").hidden = !owner; $("ownerList").hidden = !owner;
  if (owner) {
    const list = a.issued || [];
    $("issuedList").innerHTML = list.length ? ["<span class='muted'>Кому</span><span class='muted'>До</span><span class='muted'>№ кода</span>"]
      .concat(list.map((d) => `<span>${esc(d.name)} <span class="muted">${esc(d.machine)}</span></span><span>${esc(d.expires_text)}</span><span class="num">${esc(d.id)}</span>`)).join("")
      : "<span class='muted' style='grid-column:1/-1'>Пока никому не выдавал.</span>";
  }
}

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
  if (st.delay !== null && st.delay !== undefined) {
    $("kDelay").textContent = "~" + Math.round(st.delay) + " мин";
    $("kDelayS").textContent = `медиана по ${st.delay_n} нов. ${plural(st.delay_n, ["лоту", "лотам", "лотам"])} · самый быстрый ${Math.round(st.delay_min)} мин`;
  }
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
  if (!firstLoad && loud.length) { beep(loud.some((d) => d.rare)); loud.slice(0, 3).forEach(notifyDesktop); }
  if (firstLoad || !formDirty) fillForm();
  firstLoad = false;
  if (!CAT) loadCatalog();
  renderStatus(); renderDeals(); renderChips(); renderPurchases(); renderAccess();
}
refresh(); setInterval(refresh, 2000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
