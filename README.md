# STALZONE Трекер

Ищет на аукционе STALZONE (сервер RU) лоты дешевле рынка и считает прибыль перепродажи.
Сам ничего не покупает — только находит и показывает.

## Как поставить

1. Открой раздел **Releases** справа и скачай `STALZONE-Tracker.exe` из последнего выпуска.
2. Запусти. Windows может предупредить о неизвестной программе: «Подробнее» → «Выполнить в любом случае».
3. Нужны свои ключи API: напиши `/newapp` боту [@stalzone_api_bot](https://t.me/stalzone_api_bot),
   после одобрения вставь Client ID и Client Secret в «Настройки». Пока ключей нет — включи «Демо-режим».

Дальше программа обновляется сама: при запуске проверяет новые выпуски и предлагает «Обновить».

## Где данные

Ключи, настройки, находки, журнал и база сделок лежат в `%APPDATA%\STALZONE Tracker` —
отдельно от программы. Обновление их не трогает, в репозиторий и в .exe они не попадают.

## Для разработки

`pip install requests pywebview`, затем `python stalzone_app.py`.
Самопроверка: `python stalzone_tracker.py --selftest`.
Выпуск: поднять `APP_VERSION` в `stalzone_app.py`, обновить `release_notes.md`, запушить в `main`,
затем на GitHub: Releases → Draft a new release → тег `vX.Y` → Publish release.
GitHub Actions сам соберёт `STALZONE-Tracker.exe`, приложит его к выпуску и возьмёт текст из `release_notes.md`.
