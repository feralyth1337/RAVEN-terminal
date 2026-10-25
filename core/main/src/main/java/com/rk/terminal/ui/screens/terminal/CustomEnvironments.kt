package com.rk.terminal.ui.screens.terminal

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class CustomEnvironment(
    val name: String,
    val launcherPath: String
)

object CustomEnvironmentStore {
    private const val PREFERENCES_NAME = "raven_custom_environments"
    private const val ENVIRONMENTS_KEY = "environments"

    fun load(context: Context): List<CustomEnvironment> {
        val raw = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
            .getString(ENVIRONMENTS_KEY, "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(raw)
            List(array.length()) { index ->
                val item = array.getJSONObject(index)
                CustomEnvironment(
                    name = item.getString("name"),
                    launcherPath = item.getString("launcherPath")
                )
            }
        }.getOrDefault(emptyList())
    }

    fun save(context: Context, environments: List<CustomEnvironment>) {
        val array = JSONArray()
        environments.forEach { environment ->
            array.put(
                JSONObject()
                    .put("name", environment.name)
                    .put("launcherPath", environment.launcherPath)
            )
        }
        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(ENVIRONMENTS_KEY, array.toString())
            .apply()
    }
}
