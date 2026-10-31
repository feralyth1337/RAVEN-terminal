# RAVEN Terminal

[![Android build](https://github.com/feralyth1337/RAVEN-terminal/actions/workflows/android.yml/badge.svg?branch=main)](https://github.com/feralyth1337/RAVEN-terminal/actions/workflows/android.yml)
[![Latest release](https://img.shields.io/github/v/release/feralyth1337/RAVEN-terminal)](https://github.com/feralyth1337/RAVEN-terminal/releases/latest)

**RAVEN Terminal** — минималистичный терминал для Android на основе интерфейса и terminal engine проекта Termux. Интерфейс терминала и работу с PTY-сессиями RAVEN сохраняет, а вместо Termux environment использует системную оболочку Android.

> RAVEN не является полноценным Linux-дистрибутивом и не устанавливает Linux userspace. Это Android-терминал с возможностью запускать самостоятельно подготовленные пользователем окружения.

## Возможности

- Запуск системной оболочки Android: **/system/bin/sh** (обычно mksh).
- Домашний каталог и стартовая директория: **/storage/emulated/0**.
- Сессии терминала на существующем PTY engine.
- Пользовательские окружения через собственные launcher-скрипты.
- Добавление, редактирование и удаление сохранённых профилей окружений в настройках.
- Минимальная базовая установка: без Termux bootstrap, **apt**, **PREFIX** и bundled Linux userspace.

## Установка

1. Откройте [страницу Releases](https://github.com/feralyth1337/RAVEN-terminal/releases).
2. Скачайте APK из последнего стабильного релиза.
3. Установите APK. Android может запросить разрешение на установку приложений из выбранного источника.
4. При первом запуске предоставьте RAVEN доступ к общей памяти, когда Android покажет соответствующий запрос.

Идентификатор Android-пакета: **com.raven.terminal**.

## Системная оболочка Android

Кнопка **New Session** позволяет открыть **Android system shell**. RAVEN запускает **/system/bin/sh**, а **HOME** и начальная рабочая директория установлены в **/storage/emulated/0**.

Это именно оболочка Android, а не GNU/Linux shell из дистрибутива. В ней доступны системные утилиты, присутствующие в прошивке устройства. Пакетный менеджер Termux и его bootstrap в RAVEN не входят.

## Пользовательские окружения

RAVEN позволяет подключить launcher уже установленного и настроенного пользователем окружения — например, proot или chroot.

### Добавление окружения

1. Откройте **Settings → Add custom environment**.
2. Укажите отображаемое название.
3. Укажите абсолютный путь к launcher-скрипту.
4. Сохраните профиль.

Пример пути: **/data/local/start-debian.sh**.

Launcher должен существовать на устройстве и иметь право на исполнение. Например:

    chmod 755 /data/local/start-debian.sh

### Запуск

При нажатии **New Session** RAVEN показывает системную оболочку Android и список сохранённых окружений. Выберите нужный профиль, чтобы открыть отдельную PTY-сессию.

Пользовательские launcher-скрипты запускаются через **su -c**. Поэтому для них необходимы root-доступ, установленный **su** и разрешение root-менеджера для RAVEN. Системная оболочка Android сама по себе root-доступа не требует.

### Управление профилями

В **Settings → Manage custom environments** выберите сохранённое окружение. Для него доступны действия:

- **Edit** — изменить название и/или путь к launcher.
- **Delete** — удалить сохранённый профиль из RAVEN.

Удаление профиля не удаляет launcher-скрипт, файлы или само Linux-окружение с устройства.

RAVEN не скачивает, не устанавливает и не настраивает proot/chroot за пользователя. Подготовка окружения и его launcher остаются ответственностью пользователя.

## Сборка из исходников

### Требования

- Git с поддержкой submodules.
- Python 3.
- JDK 17.
- Android SDK и компоненты SDK, необходимые закреплённой версией Gradle-проекта Termux.

### Локальная сборка

Клонируйте репозиторий вместе с upstream submodule:

    git clone --recurse-submodules https://github.com/feralyth1337/RAVEN-terminal.git
    cd RAVEN-terminal

Примените патч RAVEN к закреплённым исходникам Termux и соберите universal debug APK:

    python3 scripts/patch_termux.py upstream/termux-app

    cd upstream/termux-app
    TERMUX_APP_VERSION_NAME=0.1.0-dev.1 \
    TERMUX_APK_VERSION_TAG=raven-0.1.0-dev.1 \
    TERMUX_SPLIT_APKS_FOR_DEBUG_BUILDS=0 \
    ./gradlew --no-daemon :app:assembleDebug

Собранный APK находится в **app/build/outputs/apk/debug/**. Имя файла зависит от конфигурации Gradle; ищите universal APK.

### GitHub Actions

Workflow в **.github/workflows/android.yml** собирает APK автоматически:

- Push в **main** создаёт numbered pre-release.
- Первый стабильный релиз **v0.1.0** публикуется коммитом в **main**, сообщение которого содержит **[release]**.
- Для следующих стабильных версий можно запустить workflow вручную и заполнить поле **release_version**.

Каждая сборка сохраняет APK и SHA-256 checksum как GitHub Actions artifact и прикладывает их к соответствующему GitHub Release.

## Лицензии

Оригинальные материалы и файлы, созданные для RAVEN, распространяются под MIT License в пределах, описанных в [LICENSE-MIT](LICENSE-MIT).

Это **не означает**, что весь исходный код Termux или собранное на его основе приложение переведены на MIT. RAVEN основан на закреплённой версии [termux/termux-app](https://github.com/termux/termux-app), исходное приложение которого распространяется под **GPL-3.0-only**. Terminal Emulator, Terminal View и отдельные части **termux-shared** имеют собственные лицензии и исключения. Их условия сохраняются.

Подробности, ссылки на исходный upstream commit и расположение лицензий компонентов приведены в [NOTICE.md](NOTICE.md) и в license-файлах upstream submodule **upstream/termux-app**.

## Ссылки

- [Последние релизы и APK](https://github.com/feralyth1337/RAVEN-terminal/releases)
- [Исходный код RAVEN](https://github.com/feralyth1337/RAVEN-terminal)
- [Upstream Termux App](https://github.com/termux/termux-app)
