# RAVEN Terminal

[Русская версия](README.md)

[![Android build](https://github.com/feralyth1337/RAVEN-terminal/actions/workflows/android.yml/badge.svg?branch=main)](https://github.com/feralyth1337/RAVEN-terminal/actions/workflows/android.yml)
[![Latest release](https://img.shields.io/github/v/release/feralyth1337/RAVEN-terminal)](https://github.com/feralyth1337/RAVEN-terminal/releases/latest)

**RAVEN Terminal** is a minimal Android terminal based on the interface and terminal engine of the Termux project. RAVEN retains the terminal interface and PTY session handling, but uses the Android system shell instead of the Termux environment.

> RAVEN is not a full Linux distribution and does not install a Linux userspace. It is an Android terminal that can launch user-prepared environments.

## Features

- Launches the Android system shell: **/system/bin/sh** (usually mksh).
- Home directory and initial working directory: **/storage/emulated/0**.
- Terminal sessions using the existing PTY engine.
- Custom environments launched through user-provided launcher scripts.
- Add, edit, and delete saved environment profiles in Settings.
- Minimal base installation: no Termux bootstrap, **apt**, **PREFIX**, or bundled Linux userspace.

## Installation

1. Open the [Releases page](https://github.com/feralyth1337/RAVEN-terminal/releases).
2. Download the APK from the latest stable release.
3. Install the APK. Android may ask you to allow installation from the selected source.
4. On first launch, grant RAVEN access to shared storage when Android displays the permission request.

Android application ID: **com.raven.terminal**.

## Android system shell

Tap **New Session** and select **Android system shell**. RAVEN launches **/system/bin/sh**, with **HOME** and the initial working directory set to **/storage/emulated/0**.

This is the Android system shell, not a GNU/Linux shell from a distribution. It provides the system utilities included in your device's firmware. The Termux package manager and bootstrap are not included in RAVEN.

## Custom environments

RAVEN can connect to a launcher for an environment that you have already installed and configured yourself — for example, proot or chroot.

### Adding an environment

1. Open **Settings → Add custom environment**.
2. Enter a display name.
3. Enter the absolute path to the launcher script.
4. Save the profile.

Example path: **/data/local/start-debian.sh**.

The launcher must exist on the device and be executable. For example:

    chmod 755 /data/local/start-debian.sh

### Launching

When you tap **New Session**, RAVEN displays the Android system shell and your saved environments. Select an environment to open it in a separate PTY session.

Custom launcher scripts are started through **su -c**. This requires root access, an installed **su** binary, and permission granted to RAVEN by your root manager. The Android system shell does not require root access.

### Managing profiles

Open **Settings → Manage custom environments** and select a saved environment. The available actions are:

- **Edit** — change the environment name and/or launcher path.
- **Delete** — remove the saved profile from RAVEN.

Deleting a profile does not remove the launcher script, its files, or the Linux environment from your device.

RAVEN does not download, install, or configure proot/chroot environments for you. Preparing the environment and its launcher is the user's responsibility.

## Building from source

### Requirements

- Git with submodule support.
- Python 3.
- JDK 17.
- Android SDK and the SDK components required by the pinned Termux Gradle project.

### Local build

Clone the repository, including its upstream submodule:

    git clone --recurse-submodules https://github.com/feralyth1337/RAVEN-terminal.git
    cd RAVEN-terminal

Apply the RAVEN patch to the pinned Termux source and build a universal debug APK:

    python3 scripts/patch_termux.py upstream/termux-app

    cd upstream/termux-app
    TERMUX_APP_VERSION_NAME=0.1.0-dev.1 \
    TERMUX_APK_VERSION_TAG=raven-0.1.0-dev.1 \
    TERMUX_SPLIT_APKS_FOR_DEBUG_BUILDS=0 \
    ./gradlew --no-daemon :app:assembleDebug

The APK is placed in **app/build/outputs/apk/debug/**. The exact filename depends on the Gradle configuration; look for the universal APK.

### GitHub Actions

The workflow in **.github/workflows/android.yml** builds the APK automatically:

- Pushes to **main** create numbered pre-releases.
- The first stable release, **v0.1.0**, is published by a commit to **main** whose message contains **[release]**.
- For subsequent stable releases, you can run the workflow manually and fill in the **release_version** field.

Each build saves the APK and its SHA-256 checksum as a GitHub Actions artifact and attaches them to the corresponding GitHub Release.

## Licensing

Original materials and files created for RAVEN are distributed under the MIT License, within the scope described in [LICENSE-MIT](LICENSE-MIT).

This **does not mean** that all Termux source code or the resulting application have been relicensed under MIT. RAVEN is based on a pinned version of [termux/termux-app](https://github.com/termux/termux-app), whose upstream application is distributed under **GPL-3.0-only**. Terminal Emulator, Terminal View, and parts of **termux-shared** have their own licenses and exceptions. Those terms remain in effect.

Further details, including the pinned upstream commit and the locations of component license files, are provided in [NOTICE.md](NOTICE.md) and the license files in the upstream submodule at **upstream/termux-app**.

## Links

- [Latest releases and APK downloads](https://github.com/feralyth1337/RAVEN-terminal/releases)
- [RAVEN source code](https://github.com/feralyth1337/RAVEN-terminal)
- [Upstream Termux App](https://github.com/termux/termux-app)
