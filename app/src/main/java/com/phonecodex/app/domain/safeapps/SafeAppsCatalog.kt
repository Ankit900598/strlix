package com.phonecodex.app.domain.safeapps

object SafeAppsCatalog {

    val DEFAULT_PACKAGES: Set<String> = setOf(
        "com.phonecodex.app",
        "com.android.dialer",
        "com.google.android.dialer",
        "com.android.mms",
        "com.google.android.apps.messaging",
        "com.android.settings",
        "com.miui.home",
        "com.android.systemui",
        "com.whatsapp"
    )

    private val DEFAULT_LABELS: Map<String, String> = mapOf(
        "com.phonecodex.app" to "PhoneCodex",
        "com.android.dialer" to "Phone",
        "com.google.android.dialer" to "Phone",
        "com.android.mms" to "Messages",
        "com.google.android.apps.messaging" to "Messages",
        "com.android.settings" to "Settings",
        "com.miui.home" to "Home",
        "com.android.systemui" to "System UI",
        "com.whatsapp" to "WhatsApp"
    )

    fun isDefaultPackage(packageName: String): Boolean {
        return packageName in DEFAULT_PACKAGES
    }

    fun defaultLabel(packageName: String): String {
        return DEFAULT_LABELS[packageName] ?: packageName
    }
}
