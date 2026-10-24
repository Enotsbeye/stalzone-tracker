# STALZONE Трекер

Ищет на аукционе STALZONE (сервер RU) лоты дешевле рынка и считает прибыль перепродажи.
Сам ничего не покупает — только находит и показывает.

## Как поставить

1. Скачай `STALZONE-Tracker.exe`: https://github.com/Enotsbeye/stalzone-tracker-releases/releases/latest
   (этот репозиторий с кодом закрытый, готовые .exe лежат в открытом `stalzone-tracker-releases`).
2. Запусти. Windows может предупредить о неизвестной программе: «Подробнее» → «Выполнить в любом случае».
3. Нужны свои ключи API: напиши `/newapp` боту [@stalzone_api_bot](https://t.me/stalzone_api_bot),
   после одобрения вставь Client ID и Client Secret в «Настройки». Пока ключей нет — включи «Демо-режим».

Дальше программа обновляется сама: при запуске проверяет новые выпуски и предлагает «Обновить».

## Доступ

Программа запускается только с кодом доступа. Код выдаёт владелец в разделе «Доступ»: имя, ID компьютера, срок.
Код подписан личным ключом владельца (`owner_key.pem` в папке данных, Ed25519), открытый ключ вписан в
`OWNER_PUBLIC_KEY` в `stalzone_app.py`. Отзыв — строка с именем или номером кода в `revoked.txt`
в репозитории `stalzone-tracker-releases`.

## Сервер и подписка (2.0)

Владелец включает «Доступ» → «Сервер для подписчиков»: его программа проверяет аукцион его ключом EXBO
и раздаёт находки по `GET /v1/feed` (слушает только 127.0.0.1:8790). Наружу сервер выводит Tailscale Funnel:
`tailscale funnel --bg 8790` → адрес `https://<пк>.<tailnet>.ts.net` вписывается в «Публичный адрес» и попадает
в новые коды. Подписчик вставляет код — программа берёт находки с сервера (заголовки `X-Access-Code`,
`X-Machine`), ключи EXBO ему не нужны. Сервер проверяет подпись кода, компьютер, срок и «Отключить»;
отвечает не чаще раза в 10 с на код, отдаёт ETag/304 и gzip.

## Где данные

Ключи, настройки, находки, журнал и база сделок лежат в `%APPDATA%\STALZONE Tracker` —
отдельно от программы. Обновление их не трогает, в репозиторий и в .exe они не попадают.

## Для разработки

Код: `stalzone_tracker.py` — движок (API, база сделок, поиск, шанс продажи), `stalzone_app.py` — окно, сервер,
доступ, `stalzone_ui.py` — страница окна, `stalzone_fonts.py` — шрифты Golos Text и Unbounded
(лицензия SIL OFL 1.1, `FONTS-OFL.txt`).

`pip install requests pywebview cryptography`, затем `python stalzone_app.py`.
Самопроверка: `python stalzone_tracker.py --selftest`.
Выпуск: поднять `APP_VERSION` в `stalzone_app.py`, обновить `release_notes.md`, запушить в `main`,
затем на GitHub: Releases → Draft a new release → тег `vX.Y` → Publish release.
GitHub Actions сам соберёт `STALZONE-Tracker.exe`, приложит его к выпуску и возьмёт текст из `release_notes.md`.
