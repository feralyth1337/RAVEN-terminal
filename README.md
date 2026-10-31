# RAVEN Terminal

Минимальная Android-сборка на основе терминального интерфейса Termux. UI и terminal emulator оставлены без редизайна.

## Первая версия

- Запуск системной оболочки Android: `/system/bin/sh` (mksh).
- `HOME` и начальный каталог: `/storage/emulated/0`.
- Нет Termux bootstrap, `PREFIX`, `apt`, пакетного окружения и bundled Linux userspace.
- Используется системный `PATH` Android.
- Android package id: `com.raven.terminal`.
- Перед стартом первой сессии приложение запрашивает разрешение на доступ к общей памяти.

Важно: это именно системная оболочка Android, а не полноценный GNU/Linux shell. Команды доступны только из Android userspace (в том числе системные утилиты Toybox).

## Исходники

Оригинальный `termux/termux-app` подключён как git submodule в `upstream/termux-app` и закреплён на конкретном upstream commit. Скрипт `scripts/patch_termux.py` применяет RAVEN-изменения во время CI-сборки. Так сохраняется точная база для форка, а изменения остаются отдельными и воспроизводимыми.

## Сборка

GitHub Actions собирает APK при push в `main`, сохраняет его как workflow artifact и публикует GitHub pre-release.

Локальная сборка:

```bash
git clone --recurse-submodules https://github.com/feralyth1337/RAVEN-terminal.git
python3 scripts/patch_termux.py upstream/termux-app
cd upstream/termux-app
TERMUX_APP_VERSION_NAME=0.1.0-pre.1 TERMUX_APK_VERSION_TAG=raven-0.1.0-pre.1 TERMUX_SPLIT_APKS_FOR_DEBUG_BUILDS=0 ./gradlew :app:assembleDebug
```

## Лицензии

Базовый код приложения Termux распространяется под GPL-3.0-only. Компоненты terminal emulator/view содержат отдельные лицензионные исключения; см. файлы лицензий в `upstream/termux-app`.
