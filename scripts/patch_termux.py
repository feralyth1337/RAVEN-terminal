#!/usr/bin/env python3
"""Apply the small RAVEN-specific patch set to the pinned Termux app source."""

from pathlib import Path
import shutil
import sys


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    if new in source:
        return
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one occurrence of patch anchor, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def replace_block(path: Path, start_marker: str, end_marker: str, replacement: str) -> None:
    source = path.read_text(encoding="utf-8")
    start = source.find(start_marker)
    if start < 0:
        if replacement in source:
            return
        raise RuntimeError(f"{path}: start marker not found: {start_marker!r}")
    end = source.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{path}: end marker not found: {end_marker!r}")
    end += len(end_marker)
    source = source[:start] + replacement + source[end:]
    path.write_text(source, encoding="utf-8")


if len(sys.argv) != 2:
    raise SystemExit("usage: patch_termux.py PATH_TO_TERMUX_APP")

root = Path(sys.argv[1]).resolve()
if not (root / "app/build.gradle").is_file():
    raise SystemExit(f"not a Termux app source tree: {root}")

# Start the terminal only after Android grants access to shared storage.
activity = root / "app/src/main/java/com/termux/app/TermuxActivity.java"
replace_block(
    activity,
    "                TermuxInstaller.setupBootstrapIfNeeded(TermuxActivity.this, () -> {",
    "                });",
    "                requestStoragePermission(false);",
)
replace_once(
    activity,
    "                    TermuxInstaller.setupStorageSymlinks(TermuxActivity.this);\n",
    """                    TermuxActivity.this.runOnUiThread(() -> {
                        if (mTermuxService != null && mTermuxService.isTermuxSessionsEmpty()) {
                            mTermuxTerminalSessionActivityClient.addNewSession(false, null);
                        }
                    });
""",
)

# Do not create Termux's private files tree or start its helper socket services.
application = root / "app/src/main/java/com/termux/app/TermuxApplication.java"
replace_block(
    application,
    "        // Check and create termux files directory.",
    "            TermuxShellEnvironment.writeEnvironmentToFile(this);\n        }",
    "",
)

# A new session uses Android's built-in shell and starts in shared internal storage.
session_client = root / "app/src/main/java/com/termux/app/terminal/TermuxTerminalSessionActivityClient.java"
replace_once(
    session_client,
    "                workingDirectory = mActivity.getProperties().getDefaultWorkingDirectory();",
    '                workingDirectory = "/storage/emulated/0";',
)
replace_once(
    session_client,
    "            TermuxSession newTermuxSession = service.createTermuxSession(null, null, null, workingDirectory, isFailSafe, sessionName);",
    '            TermuxSession newTermuxSession = service.createTermuxSession("/system/bin/sh", null, null, workingDirectory, isFailSafe, sessionName);',
)

# The Termux session adapter now exposes only Android's shell environment.
shell_environment = root / "termux-shared/src/main/java/com/termux/shared/termux/shell/command/environment/TermuxShellEnvironment.java"
shell_environment.write_text("""package com.termux.shared.termux.shell.command.environment;

import android.content.Context;

import androidx.annotation.NonNull;

import com.termux.shared.shell.command.environment.AndroidShellEnvironment;

import java.util.HashMap;

/**
 * RAVEN shell environment: Android's built-in shell, with shared storage as HOME.
 * No Termux PREFIX, package paths, bootstrap environment or Termux libraries are exposed.
 */
public class TermuxShellEnvironment extends AndroidShellEnvironment {

    public static final String RAVEN_HOME = "/storage/emulated/0";

    public TermuxShellEnvironment() {
        super();
    }

    /** Legacy callback retained for upstream SystemEventReceiver; RAVEN has no termux.env file. */
    public static void writeEnvironmentToFile(@NonNull Context context) {
        // The Android system shell consumes the process environment directly.
    }

    @NonNull
    @Override
    public HashMap<String, String> getEnvironment(@NonNull Context context, boolean isFailSafe) {
        HashMap<String, String> environment = super.getEnvironment(context, isFailSafe);
        environment.put("HOME", RAVEN_HOME);
        environment.put("PATH", "/system/bin:/system/xbin:/vendor/bin");
        environment.put("SHELL", "/system/bin/sh");
        environment.put("TMPDIR", context.getCacheDir().getAbsolutePath());
        environment.remove("PREFIX");
        environment.remove("LD_LIBRARY_PATH");
        return environment;
    }

    @NonNull
    @Override
    public String getDefaultWorkingDirectoryPath() {
        return RAVEN_HOME;
    }

    @NonNull
    @Override
    public String getDefaultBinPath() {
        return "/system/bin";
    }
}
""", encoding="utf-8")

# Make the property default agree with the fixed first-session directory.
property_constants = root / "termux-shared/src/main/java/com/termux/shared/termux/settings/properties/TermuxPropertyConstants.java"
replace_once(
    property_constants,
    "    public static final String DEFAULT_IVALUE_DEFAULT_WORKING_DIRECTORY = TermuxConstants.TERMUX_HOME_DIR_PATH;",
    '    public static final String DEFAULT_IVALUE_DEFAULT_WORKING_DIRECTORY = "/storage/emulated/0";',
)

# Give the fork its own Android package id and visible app name.
termux_constants = root / "termux-shared/src/main/java/com/termux/shared/termux/TermuxConstants.java"
replace_once(termux_constants, 'public static final String TERMUX_APP_NAME = "Termux";', 'public static final String TERMUX_APP_NAME = "RAVEN Terminal";')
replace_once(termux_constants, 'public static final String TERMUX_PACKAGE_NAME = "com.termux";', 'public static final String TERMUX_PACKAGE_NAME = "com.raven.terminal";')

app_gradle = root / "app/build.gradle"
replace_once(
    app_gradle,
    "    defaultConfig {\n",
    '    defaultConfig {\n        applicationId "com.raven.terminal"\n',
)
replace_once(app_gradle, 'manifestPlaceholders.TERMUX_PACKAGE_NAME = "com.termux"', 'manifestPlaceholders.TERMUX_PACKAGE_NAME = "com.raven.terminal"')
replace_once(app_gradle, 'manifestPlaceholders.TERMUX_APP_NAME = "Termux"', 'manifestPlaceholders.TERMUX_APP_NAME = "RAVEN Terminal"')

# Remove the task and dependency that download/embed Termux bootstrap archives.
gradle_source = app_gradle.read_text(encoding="utf-8")
bootstrap_task_start = gradle_source.find("def downloadBootstrap(")
if bootstrap_task_start >= 0:
    gradle_source = gradle_source[:bootstrap_task_start] + "// RAVEN does not build or package Termux bootstrap archives.\n"
    app_gradle.write_text(gradle_source, encoding="utf-8")
elif "downloadBootstrap(" in gradle_source:
    raise RuntimeError("app/build.gradle: unexpected bootstrap task layout")

# Remove the obsolete native bootstrap library from the Android build.
replace_once(
    app_gradle,
    """        externalNativeBuild {
            ndkBuild {
                cFlags "-std=c11", "-Wall", "-Wextra", "-Werror", "-Os", "-fno-stack-protector", "-Wl,--gc-sections"
            }
        }

""",
    "        // RAVEN does not build the Termux bootstrap native library.\n",
)
replace_once(
    app_gradle,
    """    externalNativeBuild {
        ndkBuild {
            path "src/main/cpp/Android.mk"
        }
    }

""",
    "    // RAVEN does not build the Termux bootstrap native library.\n",
)
cpp_directory = root / "app/src/main/cpp"
if cpp_directory.exists():
    shutil.rmtree(cpp_directory)

# Keep XML package/app labels in sync with the Android manifest and constants.
app_strings = root / "app/src/main/res/values/strings.xml"
replace_once(app_strings, '<!ENTITY TERMUX_PACKAGE_NAME "com.termux">', '<!ENTITY TERMUX_PACKAGE_NAME "com.raven.terminal">')
replace_once(app_strings, '<!ENTITY TERMUX_APP_NAME "Termux">', '<!ENTITY TERMUX_APP_NAME "RAVEN Terminal">')

shared_strings = root / "termux-shared/src/main/res/values/strings.xml"
replace_once(shared_strings, '<!ENTITY TERMUX_PACKAGE_NAME "com.termux">', '<!ENTITY TERMUX_PACKAGE_NAME "com.raven.terminal">')
replace_once(shared_strings, '<!ENTITY TERMUX_APP_NAME "Termux">', '<!ENTITY TERMUX_APP_NAME "RAVEN Terminal">')
replace_once(shared_strings, '<!ENTITY TERMUX_PREFIX_DIR_PATH "/data/data/com.termux/files/usr">', '<!ENTITY TERMUX_PREFIX_DIR_PATH "/data/data/com.raven.terminal/files/usr">')

# The installer is not part of a system-shell-only build.
installer = root / "app/src/main/java/com/termux/app/TermuxInstaller.java"
if installer.exists():
    installer.unlink()

print("RAVEN patch applied: Android /system/bin/sh, HOME=/storage/emulated/0, no Termux bootstrap.")
