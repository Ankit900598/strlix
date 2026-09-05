package com.phonecodex.app.data

import android.content.Context
import com.phonecodex.app.domain.model.SafeApp
import com.phonecodex.app.domain.safeapps.SafeAppsCatalog

class SafeAppsStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun getSafeApps(): List<SafeApp> {
        val defaults = SafeAppsCatalog.DEFAULT_PACKAGES.map { packageName ->
            SafeApp(
                packageName = packageName,
                label = SafeAppsCatalog.defaultLabel(packageName),
                isDefault = true
            )
        }
        val custom = loadCustomSafeApps()
            .filter { app -> !SafeAppsCatalog.isDefaultPackage(app.packageName) }
        return (defaults + custom).sortedBy { app -> app.label.lowercase() }
    }

    fun getSafePackageNames(): Set<String> {
        return SafeAppsCatalog.DEFAULT_PACKAGES + loadCustomSafeApps().map { it.packageName }
    }

    fun isSafePackage(packageName: String): Boolean {
        return packageName in getSafePackageNames()
    }

    fun isDefaultSafePackage(packageName: String): Boolean {
        return SafeAppsCatalog.isDefaultPackage(packageName)
    }

    fun addSafeApp(packageName: String, label: String) {
        if (isSafePackage(packageName)) return

        val updated = loadCustomSafeApps() + SafeApp(
            packageName = packageName,
            label = label,
            isDefault = false
        )
        saveCustomSafeApps(updated)
    }

    fun removeSafeApp(packageName: String) {
        if (SafeAppsCatalog.isDefaultPackage(packageName)) return

        val updated = loadCustomSafeApps()
            .filter { app -> app.packageName != packageName }
        saveCustomSafeApps(updated)
    }

    private fun loadCustomSafeApps(): List<SafeApp> {
        return prefs.getStringSet(KEY_CUSTOM_SAFE_APPS, emptySet())
            .orEmpty()
            .mapNotNull { entry ->
                val separator = entry.indexOf('|')
                if (separator <= 0) return@mapNotNull null
                val packageName = entry.substring(0, separator)
                val label = entry.substring(separator + 1)
                SafeApp(
                    packageName = packageName,
                    label = label,
                    isDefault = false
                )
            }
    }

    private fun saveCustomSafeApps(apps: List<SafeApp>) {
        val encoded = apps.map { app -> "${app.packageName}|${app.label}" }.toSet()
        prefs.edit()
            .putStringSet(KEY_CUSTOM_SAFE_APPS, encoded)
            .apply()
    }

    companion object {
        private const val PREFS_NAME = "phonecodex_safe_apps"
        private const val KEY_CUSTOM_SAFE_APPS = "custom_safe_apps"
    }
}
