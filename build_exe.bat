@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
title Сборка STALZONE Tracker.exe
set "OWNPY=%LOCALAPPDATA%\STALZONE Build\python"

rem === 1. Ищем рабочий Python прямо в папках установки ===
rem Команды py и python не используем: у некоторых они ведут на сломанную версию.
set "PYEXE="
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*" "%ProgramFiles%\Python3*" "%OWNPY%") do call :try "%%~d\python.exe"
if defined PYEXE goto found

rem === 2. Не нашли - скачиваем Python 3.12 и ставим в отдельную папку ===
echo Рабочий Python не найден. Скачиваю Python 3.12, это около 25 МБ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile ($env:TEMP + '\stalzone-python.exe')"
if errorlevel 1 goto fail
echo Устанавливаю Python, это около минуты...
"%TEMP%\stalzone-python.exe" /quiet InstallAllUsers=0 PrependPath=0 Include_launcher=0 Include_test=0 Include_doc=0 Shortcuts=0 AssociateFiles=0 TargetDir="%OWNPY%"
call :try "%OWNPY%\python.exe"
if not defined PYEXE goto fail

:found
echo Использую Python: %PYEXE%
echo.
echo [1/3] Проверяю модули...
"%PYEXE%" -m pip install --disable-pip-version-check -q requests pywebview cryptography pyinstaller
if errorlevel 1 goto fail
echo [2/3] Проверяю логику трекера...
"%PYEXE%" stalzone_tracker.py --selftest >"%TEMP%\stalzone-selftest.txt" 2>&1
if errorlevel 1 goto selftest_failed
echo [3/3] Собираю программу, это 1-2 минуты...
"%PYEXE%" make_version_info.py >nul
"%PYEXE%" -m PyInstaller --noconfirm --onefile --windowed --noupx --log-level WARN --name "STALZONE Tracker" --icon stalzone.ico --version-file version_info.txt stalzone_app.py
if errorlevel 1 goto fail
echo.
echo Готово: папка dist, файл "STALZONE Tracker.exe". Его можно отправить другу.
explorer dist
pause
exit /b 0

:selftest_failed
type "%TEMP%\stalzone-selftest.txt"
goto fail

:fail
echo.
echo Сборка не удалась. Пришли скрин этого окна.
pause
exit /b 1

:try
rem Подходит первый Python, который реально запускается и не старее 3.8
if defined PYEXE exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>nul
if not errorlevel 1 set "PYEXE=%~1"
exit /b 0
