package com.zevi.agent;

import android.content.Context;
import android.content.Intent;

/**
 * Runtime override of the public android-api base URL.
 * Order: runtime override (prefs, set via intent extra "strlix_api_url") → BuildConfig.ANDROID_API_PUBLIC_URL
 * (set at build time with -Pstrlix.androidApiUrl=... or env STRLIX_ANDROID_API_URL).
 * Clear with extra "strlix_api_url" = "" (empty).
 */
public final class ApiConfig {
    private static final String PREFS = "strlix_api";
    private static final String KEY = "android_api_url";
    public static final String EXTRA = "strlix_api_url";
    private static volatile String override = null;

    private ApiConfig() {}

    public static void init(Context ctx) {
        override = ctx.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null);
    }

    /** Returns true if the intent carried an override (stored, or cleared when empty). */
    public static boolean applyIntent(Context ctx, Intent intent) {
        if (intent == null || !intent.hasExtra(EXTRA)) return false;
        String v = intent.getStringExtra(EXTRA);
        if (v != null) v = v.trim();
        boolean valid = v != null && (v.startsWith("https://") || v.startsWith("http://"));
        ctx.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .putString(KEY, valid ? v : null).apply();
        override = valid ? v : null;
        return true;
    }

    /** Effective public base URL. */
    public static String publicUrl() {
        String o = override;
        return (o != null && !o.isEmpty()) ? o : BuildConfig.ANDROID_API_PUBLIC_URL;
    }
}
