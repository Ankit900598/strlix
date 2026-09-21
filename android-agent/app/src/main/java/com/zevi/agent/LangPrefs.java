package com.zevi.agent;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.Configuration;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Live-voice language catalog + SharedPreferences persistence. */
public final class LangPrefs {
    public static final String PREFS = "strlix_live";
    public static final String KEY_LANG = "language";

    public static final class Lang {
        public final String id;
        public final String name;
        public final String nativeName;

        public Lang(String id, String name, String nativeName) {
            this.id = id;
            this.name = name;
            this.nativeName = nativeName;
        }

        @Override public String toString() {
            return name + " · " + nativeName;
        }
    }

    private static final Map<String, Lang> ALL = new LinkedHashMap<>();
    static {
        add("en-US", "English", "English");
        add("hi-IN", "Hindi", "हिन्दी");
        add("es-ES", "Spanish", "Español");
        add("fr-FR", "French", "Français");
        add("zh-CN", "Mandarin", "中文");
        add("ar-SA", "Arabic", "العربية");
        add("pt-BR", "Portuguese", "Português");
        add("ja-JP", "Japanese", "日本語");
    }

    private static void add(String id, String name, String nativeName) {
        ALL.put(id, new Lang(id, name, nativeName));
    }

    public static List<Lang> all() {
        return new ArrayList<>(ALL.values());
    }

    public static String deviceDefault() {
        Locale loc = Locale.getDefault();
        String tag = loc.toLanguageTag();
        if (ALL.containsKey(tag)) return tag;
        String primary = loc.getLanguage().toLowerCase(Locale.ROOT);
        switch (primary) {
            case "en": return "en-US";
            case "hi": return "hi-IN";
            case "es": return "es-ES";
            case "fr": return "fr-FR";
            case "zh": return "zh-CN";
            case "ar": return "ar-SA";
            case "pt": return "pt-BR";
            case "ja": return "ja-JP";
            default: return "en-US";
        }
    }

    public static String get(Context ctx) {
        SharedPreferences sp = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String v = sp.getString(KEY_LANG, null);
        if (v == null || !ALL.containsKey(v)) {
            v = deviceDefault();
            sp.edit().putString(KEY_LANG, v).apply();
        }
        return v;
    }

    public static void set(Context ctx, String id) {
        if (!ALL.containsKey(id)) id = "en-US";
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_LANG, id).apply();
    }

    public static Lang getLang(Context ctx) {
        return ALL.get(get(ctx));
    }

    private LangPrefs() {}
}
