package com.rk.terminal.ui.screens.terminal

import com.rk.libcommons.localBinDir
import com.rk.libcommons.localLibDir
import com.rk.libcommons.pendingCommand
import com.rk.terminal.ui.activities.terminal.MainActivity
import com.termux.terminal.TerminalEmulator
import com.termux.terminal.TerminalSession
import com.termux.terminal.TerminalSessionClient

object MkSession {
    fun createSession(
        activity: MainActivity,
        sessionClient: TerminalSessionClient,
        session_id: String,
        workingMode: Int
    ): TerminalSession {
        with(activity) {
            val envVariables = mapOf(
                "ANDROID_ART_ROOT" to System.getenv("ANDROID_ART_ROOT"),
                "ANDROID_DATA" to System.getenv("ANDROID_DATA"),
                "ANDROID_I18N_ROOT" to System.getenv("ANDROID_I18N_ROOT"),
                "ANDROID_ROOT" to System.getenv("ANDROID_ROOT"),
                "ANDROID_RUNTIME_ROOT" to System.getenv("ANDROID_RUNTIME_ROOT"),
                "ANDROID_TZDATA_ROOT" to System.getenv("ANDROID_TZDATA_ROOT"),
                "BOOTCLASSPATH" to System.getenv("BOOTCLASSPATH"),
                "DEX2OATBOOTCLASSPATH" to System.getenv("DEX2OATBOOTCLASSPATH"),
                "EXTERNAL_STORAGE" to System.getenv("EXTERNAL_STORAGE")
            )

            val workingDir = pendingCommand?.workingDir ?: "/sdcard"
            val env = mutableListOf(
                "PATH=${System.getenv("PATH")}:/sbin:${localBinDir().absolutePath}",
                "HOME=/sdcard",
                "PUBLIC_HOME=${getExternalFilesDir(null)?.absolutePath}",
                "COLORTERM=truecolor",
                "TERM=xterm-256color",
                "LANG=C.UTF-8",
                "BIN=${localBinDir()}",
                "PREFIX=${filesDir.parentFile!!.path}",
                "LD_LIBRARY_PATH=${localLibDir().absolutePath}",
                "PKG=${packageName}",
                "RISH_APPLICATION_ID=${packageName}",
                "PKG_PATH=${applicationInfo.sourceDir}"
            )
            env.addAll(envVariables.map { "${it.key}=${it.value}" })
            pendingCommand?.env?.let { env.addAll(it) }

            val shell: String
            val args: Array<String>
            if (pendingCommand == null) {
                shell = "/system/bin/sh"
                args = arrayOf()
            } else {
                shell = pendingCommand!!.shell
                args = pendingCommand!!.args
            }

            pendingCommand = null
            return TerminalSession(
                shell,
                workingDir,
                args,
                env.toTypedArray(),
                TerminalEmulator.DEFAULT_TERMINAL_TRANSCRIPT_ROWS,
                sessionClient
            )
        }
    }
}
