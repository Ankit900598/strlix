package com.phonecodex.app.data

import android.content.Context
import com.phonecodex.app.domain.model.AppRule
import com.phonecodex.app.domain.model.AppRuleBehavior

class AppRulesStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun getRules(): List<AppRule> {
        val defaultRules = DEFAULT_RULES.map { default ->
            default.copy(behavior = resolveBehavior(default.packageName, default.behavior))
        }
        val defaultPackages = defaultRules.map { it.packageName }.toSet()
        val customRules = loadCustomRules()
            .filter { it.packageName !in defaultPackages }
            .map { custom ->
                custom.copy(behavior = resolveBehavior(custom.packageName, custom.behavior))
            }
        return defaultRules + customRules
    }

    fun getRuleForPackage(packageName: String): AppRule? {
        return getRules().find { it.packageName == packageName }
    }

    fun getBehaviorForPackage(packageName: String): AppRuleBehavior? {
        val fallback = DEFAULT_RULES
            .find { it.packageName == packageName }
            ?.behavior
            ?: loadCustomRules()
                .find { it.packageName == packageName }
                ?.behavior
            ?: return null

        return resolveBehavior(packageName, fallback)
    }

    fun addRule(
        packageName: String,
        label: String,
        behavior: AppRuleBehavior = AppRuleBehavior.WARN
    ) {
        if (getRuleForPackage(packageName) != null) return

        val updatedCustomRules = loadCustomRules() + AppRule(
            packageName = packageName,
            label = label,
            behavior = behavior
        )
        saveCustomRules(updatedCustomRules)
        prefs.edit()
            .putString(behaviorKey(packageName), behavior.name)
            .apply()
    }

    fun setBehavior(packageName: String, behavior: AppRuleBehavior) {
        if (getRuleForPackage(packageName) == null) return
        prefs.edit()
            .putString(behaviorKey(packageName), behavior.name)
            .apply()
    }

    fun applySuggestedRule(rule: AppRule) {
        if (getRuleForPackage(rule.packageName) != null) {
            setBehavior(rule.packageName, rule.behavior)
        } else {
            addRule(
                packageName = rule.packageName,
                label = rule.label,
                behavior = rule.behavior
            )
        }
    }

    fun isDefaultRule(packageName: String): Boolean {
        return DEFAULT_RULES.any { it.packageName == packageName }
    }

    fun removeCustomRule(packageName: String) {
        if (isDefaultRule(packageName)) return

        val updatedCustomRules = loadCustomRules()
            .filter { it.packageName != packageName }
        saveCustomRules(updatedCustomRules)
        prefs.edit()
            .remove(behaviorKey(packageName))
            .apply()
    }

    private fun resolveBehavior(
        packageName: String,
        fallback: AppRuleBehavior
    ): AppRuleBehavior {
        val stored = prefs.getString(behaviorKey(packageName), null) ?: return fallback
        return runCatching { AppRuleBehavior.valueOf(stored) }.getOrNull() ?: fallback
    }

    private fun loadCustomRules(): List<AppRule> {
        return prefs.getStringSet(KEY_CUSTOM_RULES, emptySet())
            .orEmpty()
            .mapNotNull { entry ->
                val separator = entry.indexOf('|')
                if (separator <= 0) return@mapNotNull null
                val packageName = entry.substring(0, separator)
                val label = entry.substring(separator + 1)
                AppRule(
                    packageName = packageName,
                    label = label,
                    behavior = AppRuleBehavior.WARN
                )
            }
    }

    private fun saveCustomRules(rules: List<AppRule>) {
        val encoded = rules.map { rule -> "${rule.packageName}|${rule.label}" }.toSet()
        prefs.edit()
            .putStringSet(KEY_CUSTOM_RULES, encoded)
            .apply()
    }

    private fun behaviorKey(packageName: String): String {
        return "behavior_$packageName"
    }

    companion object {
        private const val PREFS_NAME = "phonecodex_app_rules"
        private const val KEY_CUSTOM_RULES = "custom_rules"

        private val DEFAULT_RULES = listOf(
            AppRule(
                packageName = "com.android.chrome",
                label = "Chrome",
                behavior = AppRuleBehavior.AI_DECIDE
            ),
            AppRule(
                packageName = "com.google.android.youtube",
                label = "YouTube",
                behavior = AppRuleBehavior.AI_DECIDE
            ),
            AppRule(
                packageName = "com.instagram.android",
                label = "Instagram",
                behavior = AppRuleBehavior.BLOCK
            )
        )
    }
}
