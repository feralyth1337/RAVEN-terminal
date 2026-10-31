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


def remove_gradle_blocks(path: Path, block_name: str) -> None:
    """Remove complete Gradle brace blocks without depending on whitespace."""
    source = path.read_text(encoding="utf-8")
    while block_name in source:
        start = source.index(block_name)
        line_start = source.rfind("\n", 0, start) + 1
        opening = source.find("{", start)
        if opening < 0:
            raise RuntimeError(f"{path}: opening brace not found for {block_name}")
        depth = 0
        end = None
        for index in range(opening, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise RuntimeError(f"{path}: unmatched Gradle block {block_name}")
        source = source[:line_start] + source[end:]
    if "src/main/cpp/Android.mk" in source:
        raise RuntimeError(f"{path}: stale Termux bootstrap NDK path remains")
    path.write_text(source, encoding="utf-8")


if len(sys.argv) != 2:
    raise SystemExit("usage: patch_termux.py PATH_TO_TERMUX_APP")

root = Path(sys.argv[1]).resolve()
if not (root / "app/build.gradle").is_file():
    raise SystemExit(f"not a Termux app source tree: {root}")

# Persist user-defined root launcher profiles.
environment_manager = root / "app/src/main/java/com/termux/app/RavenEnvironmentManager.java"
environment_manager.write_text("""package com.termux.app;

import android.content.Context;
import android.content.SharedPreferences;
import androidx.annotation.NonNull;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;

public final class RavenEnvironmentManager {
    private static final String PREFS_NAME = "raven_terminal";
    private static final String KEY_ENVIRONMENTS = "custom_environments";

    private RavenEnvironmentManager() {
    }

    public static final class Environment {
        public final String name;
        public final String path;
        Environment(String name, String path) { this.name = name; this.path = path; }
    }

    @NonNull
    public static List<Environment> getEnvironments(@NonNull Context context) {
        String serialized = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_ENVIRONMENTS, "[]");
        List<Environment> environments = new ArrayList<>();
        try {
            JSONArray array = new JSONArray(serialized);
            for (int i = 0; i < array.length(); i++) {
                JSONObject item = array.optJSONObject(i);
                if (item == null) continue;
                String name = item.optString("name", "").trim();
                String path = item.optString("path", "").trim();
                if (!name.isEmpty() && !path.isEmpty()) environments.add(new Environment(name, path));
            }
        } catch (Exception ignored) {
            // Ignore malformed preferences and keep the built-in shell available.
        }
        return environments;
    }

    public static boolean addEnvironment(@NonNull Context context, String name, String path) {
        return saveEnvironment(context, null, name, path);
    }

    public static boolean updateEnvironment(@NonNull Context context, String oldName, String name, String path) {
        if (oldName == null || oldName.trim().isEmpty()) return false;
        return saveEnvironment(context, oldName, name, path);
    }

    private static boolean saveEnvironment(@NonNull Context context, String replacedName, String name, String path) {
        String cleanName = name == null ? "" : name.trim();
        String cleanPath = path == null ? "" : path.trim();
        if (cleanName.isEmpty() || cleanPath.isEmpty() || cleanPath.charAt(0) != '/'
            || cleanName.indexOf((char) 10) >= 0 || cleanName.indexOf((char) 13) >= 0
            || cleanPath.indexOf((char) 10) >= 0 || cleanPath.indexOf((char) 13) >= 0) return false;

        JSONArray updated = new JSONArray();
        try {
            for (Environment environment : getEnvironments(context)) {
                boolean replacing = replacedName != null && environment.name.equalsIgnoreCase(replacedName);
                boolean collision = environment.name.equalsIgnoreCase(cleanName);
                if (replacing || collision) continue;
                JSONObject item = new JSONObject();
                item.put("name", environment.name);
                item.put("path", environment.path);
                updated.put(item);
            }
            JSONObject item = new JSONObject();
            item.put("name", cleanName);
            item.put("path", cleanPath);
            updated.put(item);
        } catch (Exception e) {
            return false;
        }

        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit().putString(KEY_ENVIRONMENTS, updated.toString()).apply();
        return true;
    }

    public static boolean removeEnvironment(@NonNull Context context, String name) {
        if (name == null || name.trim().isEmpty()) return false;
        JSONArray updated = new JSONArray();
        boolean removed = false;
        try {
            for (Environment environment : getEnvironments(context)) {
                if (environment.name.equalsIgnoreCase(name.trim())) {
                    removed = true;
                    continue;
                }
                JSONObject item = new JSONObject();
                item.put("name", environment.name);
                item.put("path", environment.path);
                updated.put(item);
            }
        } catch (Exception e) {
            return false;
        }
        if (!removed) return false;
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit().putString(KEY_ENVIRONMENTS, updated.toString()).apply();
        return true;
    }
}""", encoding="utf-8")

# Start the terminal only after Android grants access to shared storage.
activity = root / "app/src/main/java/com/termux/app/TermuxActivity.java"
# Add the custom environment chooser to the existing new-session button.
replace_once(
    activity,
    "import java.util.Arrays;\n",
    "import java.util.Arrays;\nimport java.util.List;\n",
)
replace_once(
    activity,
    "        newSessionButton.setOnClickListener(v -> mTermuxTerminalSessionActivityClient.addNewSession(false, null));",
    "        newSessionButton.setOnClickListener(v -> showNewSessionDialog());",
)
replace_once(
    activity,
    "    private void setToggleKeyboardView() {\n",
    """    private void showNewSessionDialog() {
        List<RavenEnvironmentManager.Environment> environments = RavenEnvironmentManager.getEnvironments(this);
        CharSequence[] choices = new CharSequence[environments.size() + 1];
        choices[0] = getString(R.string.raven_android_shell);
        for (int i = 0; i < environments.size(); i++)
            choices[i + 1] = environments.get(i).name;

        new AlertDialog.Builder(this)
            .setTitle(R.string.raven_select_environment)
            .setItems(choices, (dialog, which) -> {
                if (which == 0) {
                    mTermuxTerminalSessionActivityClient.addNewSession(false, null);
                } else {
                    RavenEnvironmentManager.Environment environment = environments.get(which - 1);
                    mTermuxTerminalSessionActivityClient.addNewEnvironmentSession(environment.name, environment.path);
                }
            })
            .show();
    }

    private void setToggleKeyboardView() {
""",
)

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

# Create selected custom environments as su-backed PTY sessions.
replace_once(
    session_client,
    "            mActivity.getDrawer().closeDrawers();\n        }\n    }\n\n    public void setCurrentStoredSession()",
    """            mActivity.getDrawer().closeDrawers();
        }
    }

    /** Launch a user-configured proot/chroot launcher through the device's su binary. */
    public void addNewEnvironmentSession(String environmentName, String launcherPath) {
        TermuxService service = mActivity.getTermuxService();
        if (service == null) return;

        if (service.getTermuxSessionsSize() >= MAX_SESSIONS) {
            new AlertDialog.Builder(mActivity).setTitle(R.string.title_max_terminals_reached)
                .setMessage(R.string.msg_max_terminals_reached)
                .setPositiveButton(android.R.string.ok, null).show();
            return;
        }

        // The launcher itself changes into the guest root. Keep the host-side PTY cwd valid.
        String command = "exec " + quoteForShell(launcherPath);
        TermuxSession newTermuxSession = service.createTermuxSession(
            "su", new String[]{"-c", command}, null, "/storage/emulated/0", false, environmentName);
        if (newTermuxSession == null) return;

        setCurrentSession(newTermuxSession.getTerminalSession());
        mActivity.getDrawer().closeDrawers();
    }

    private static String quoteForShell(String value) {
        String singleQuote = String.valueOf((char) 39);
        String escapedQuote = singleQuote + (char) 92 + singleQuote + singleQuote;
        return singleQuote + value.replace(singleQuote, escapedQuote) + singleQuote;
    }

    public void setCurrentStoredSession()""",
)

# Add a settings entry and dialog for registering launcher name/path pairs.
settings_activity = root / "app/src/main/java/com/termux/app/activities/SettingsActivity.java"
replace_once(
    settings_activity,
    "import android.content.Context;\n",
    """import android.app.AlertDialog;
import android.content.Context;
import android.text.InputType;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Toast;
import androidx.preference.ListPreference;
""",
)
replace_once(
    settings_activity,
    "import com.termux.R;\n",
    "import com.termux.R;\nimport com.termux.app.RavenEnvironmentManager;\n",
)
replace_once(
    settings_activity,
    "            setPreferencesFromResource(R.xml.root_preferences, rootKey);\n",
    """            setPreferencesFromResource(R.xml.root_preferences, rootKey);
            configureRavenEnvironmentPreference(context);
""",
)
replace_once(
    settings_activity,
    "        private void configureTermuxAPIPreference(@NonNull Context context) {",
    """        private void configureRavenEnvironmentPreference(@NonNull Context context) {
            Preference addPreference = findPreference("raven_add_environment");
            if (addPreference != null) {
                addPreference.setOnPreferenceClickListener(clicked -> {
                    showAddRavenEnvironmentDialog(context);
                    return true;
                });
            }

            ListPreference managePreference = findPreference("raven_manage_environments");
            if (managePreference != null) {
                managePreference.setPersistent(false);
                managePreference.setDialogTitle(R.string.raven_manage_environments_title);
                managePreference.setOnPreferenceChangeListener((preference, newValue) -> {
                    showManageRavenEnvironmentDialog(context, String.valueOf(newValue));
                    return false;
                });
                refreshRavenEnvironmentPreference(context);
            }
        }

        private void refreshRavenEnvironmentPreference(@NonNull Context context) {
            ListPreference preference = findPreference("raven_manage_environments");
            if (preference == null) return;
            java.util.List<RavenEnvironmentManager.Environment> environments =
                RavenEnvironmentManager.getEnvironments(context);
            CharSequence[] entries = new CharSequence[environments.size()];
            CharSequence[] values = new CharSequence[environments.size()];
            for (int i = 0; i < environments.size(); i++) {
                entries[i] = environments.get(i).name;
                values[i] = environments.get(i).name;
            }
            preference.setEntries(entries);
            preference.setEntryValues(values);
            preference.setEnabled(!environments.isEmpty());
            preference.setSummary(environments.isEmpty()
                ? R.string.raven_no_environments_summary : R.string.raven_manage_environments_summary);
        }

        private void showManageRavenEnvironmentDialog(@NonNull Context context, String environmentName) {
            RavenEnvironmentManager.Environment selected = null;
            for (RavenEnvironmentManager.Environment item : RavenEnvironmentManager.getEnvironments(context)) {
                if (item.name.equalsIgnoreCase(environmentName)) { selected = item; break; }
            }
            if (selected == null) {
                refreshRavenEnvironmentPreference(context);
                return;
            }
            RavenEnvironmentManager.Environment environment = selected;
            CharSequence[] actions = new CharSequence[] {
                context.getString(R.string.raven_edit_environment),
                context.getString(R.string.raven_delete_environment)
            };
            new AlertDialog.Builder(context).setTitle(environment.name)
                .setItems(actions, (dialog, which) -> {
                    if (which == 0) {
                        showRavenEnvironmentEditorDialog(context, environment);
                    } else {
                        new AlertDialog.Builder(context)
                            .setTitle(R.string.raven_delete_environment)
                            .setMessage(context.getString(R.string.raven_delete_environment_confirmation, environment.name))
                            .setNegativeButton(android.R.string.cancel, null)
                            .setPositiveButton(R.string.raven_delete_environment, (confirm, result) -> {
                                if (RavenEnvironmentManager.removeEnvironment(context, environment.name)) {
                                    Toast.makeText(context, R.string.raven_environment_deleted, Toast.LENGTH_SHORT).show();
                                }
                                refreshRavenEnvironmentPreference(context);
                            }).show();
                    }
                }).show();
        }

        private void showAddRavenEnvironmentDialog(@NonNull Context context) {
            showRavenEnvironmentEditorDialog(context, null);
        }

        private void showRavenEnvironmentEditorDialog(
            @NonNull Context context, RavenEnvironmentManager.Environment existing) {
            LinearLayout fields = new LinearLayout(context);
            fields.setOrientation(LinearLayout.VERTICAL);
            int padding = (int) (20 * context.getResources().getDisplayMetrics().density + 0.5f);
            fields.setPadding(padding, padding / 2, padding, 0);

            EditText nameInput = new EditText(context);
            nameInput.setSingleLine(true);
            nameInput.setHint(R.string.raven_environment_name_hint);
            fields.addView(nameInput, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

            EditText pathInput = new EditText(context);
            pathInput.setSingleLine(true);
            pathInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
            pathInput.setHint(R.string.raven_environment_launcher_hint);
            fields.addView(pathInput, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

            boolean editing = existing != null;
            if (editing) {
                nameInput.setText(existing.name);
                pathInput.setText(existing.path);
            }

            AlertDialog dialog = new AlertDialog.Builder(context)
                .setTitle(editing ? R.string.raven_edit_environment_title : R.string.raven_add_environment_title)
                .setView(fields)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.raven_save_environment, null)
                .create();
            dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
                String name = nameInput.getText().toString().trim();
                String path = pathInput.getText().toString().trim();
                if (name.isEmpty()) {
                    nameInput.setError(context.getString(R.string.raven_environment_name_required));
                    return;
                }
                boolean saved = editing
                    ? RavenEnvironmentManager.updateEnvironment(context, existing.name, name, path)
                    : RavenEnvironmentManager.addEnvironment(context, name, path);
                if (!saved) {
                    pathInput.setError(context.getString(R.string.raven_environment_path_required));
                    return;
                }
                Toast.makeText(context,
                    editing ? R.string.raven_environment_updated : R.string.raven_environment_saved,
                    Toast.LENGTH_SHORT).show();
                refreshRavenEnvironmentPreference(context);
                dialog.dismiss();
            }));
            dialog.show();
        }

        private void configureTermuxAPIPreference(@NonNull Context context) {""",
)

# Expose the "Add custom environment" action in the existing Settings screen.
root_preferences = root / "app/src/main/res/xml/root_preferences.xml"
replace_once(
    root_preferences,
    '    <Preference\n        app:key="about"\n',
    """    <Preference
        app:key="raven_add_environment"
        app:title="@string/raven_add_environment_title"
        app:summary="@string/raven_add_environment_summary"
        app:persistent="false"/>

    <ListPreference
        app:key="raven_manage_environments"
        app:title="@string/raven_manage_environments_title"
        app:summary="@string/raven_no_environments_summary"
        app:persistent="false"/>

    <Preference
        app:key="about"
""",
)

# Remove the upstream Termux-only About and Donate settings entries.
replace_block(
    root_preferences,
    '    <Preference\n        app:key="about"\n',
    '        app:isPreferenceVisible="false"/>',
    "",
)

# Add labels for the settings form and the new-session environment picker.
app_strings = root / "app/src/main/res/values/strings.xml"
replace_once(
    app_strings,
    '    <string name="action_create_named_session_confirm">Create</string>\n',
    """    <string name="action_create_named_session_confirm">Create</string>
    <string name="raven_select_environment">Select environment</string>
    <string name="raven_android_shell">Android system shell</string>
    <string name="raven_add_environment_title">Add custom environment</string>
    <string name="raven_add_environment_summary">Register a launcher for your proot or chroot environment</string>
    <string name="raven_manage_environments_title">Manage custom environments</string>
    <string name="raven_manage_environments_summary">Select an environment to edit or remove it</string>
    <string name="raven_no_environments_summary">No custom environments added</string>
    <string name="raven_edit_environment_title">Edit custom environment</string>
    <string name="raven_edit_environment">Edit</string>
    <string name="raven_delete_environment">Delete</string>
    <string name="raven_delete_environment_confirmation">Remove the saved launcher for %1$s? The launcher script and environment files will not be deleted.</string>
    <string name="raven_environment_name_hint">Environment name</string>
    <string name="raven_environment_launcher_hint">Absolute launcher path</string>
    <string name="raven_environment_name_required">Enter an environment name</string>
    <string name="raven_environment_path_required">Enter an absolute launcher path</string>
    <string name="raven_save_environment">Save</string>
    <string name="raven_environment_saved">Environment saved</string>
    <string name="raven_environment_updated">Environment updated</string>
    <string name="raven_environment_deleted">Environment removed</string>
""",
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
remove_gradle_blocks(app_gradle, "externalNativeBuild")
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
