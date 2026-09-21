package com.zevi.agent;

import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.net.Uri;
import android.provider.Settings;
import android.widget.Toast;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * On-device actions. Prefers AccessibilityService when enabled for true
 * inside-the-phone control; falls back to intents otherwise.
 */
public final class LocalActions {
    private static final Pattern OPEN_APP = Pattern.compile(
            "^(?:open|launch|start|run)\\s+(.+)$", Pattern.CASE_INSENSITIVE);
    private static final Pattern TAP = Pattern.compile(
            "^(?:tap|click)\\s+(.+)$", Pattern.CASE_INSENSITIVE);
    private static final Pattern TYPE = Pattern.compile(
            "^(?:type|enter|input)\\s+(.+)$", Pattern.CASE_INSENSITIVE);
    private static final Pattern SWIPE = Pattern.compile(
            "^swipe\\s+(up|down|left|right)$", Pattern.CASE_INSENSITIVE);

    private static final Map<String, String> ALIASES = new LinkedHashMap<>();
    static {
        ALIASES.put("chrome", "com.android.chrome");
        ALIASES.put("google chrome", "com.android.chrome");
        ALIASES.put("browser", "com.android.chrome");
        ALIASES.put("settings", "com.android.settings");
        ALIASES.put("setting", "com.android.settings");
        ALIASES.put("camera", "com.android.camera2");
        ALIASES.put("photos", "com.google.android.apps.photos");
        ALIASES.put("gmail", "com.google.android.gm");
        ALIASES.put("maps", "com.google.android.apps.maps");
        ALIASES.put("youtube", "com.google.android.youtube");
        ALIASES.put("play store", "com.android.vending");
        ALIASES.put("playstore", "com.android.vending");
        ALIASES.put("files", "com.android.documentsui");
        ALIASES.put("clock", "com.google.android.deskclock");
        ALIASES.put("phone", "com.android.dialer");
        ALIASES.put("messages", "com.google.android.apps.messaging");
        ALIASES.put("contacts", "com.android.contacts");
        ALIASES.put("calculator", "com.google.android.calculator");
    }

    private LocalActions() {}

    public static void goHome(Context ctx) {
        if (ZeviAccessibilityService.isRunning()) {
            ZeviAccessibilityService.getInstance().performHome();
            return;
        }
        Intent i = new Intent(Intent.ACTION_MAIN);
        i.addCategory(Intent.CATEGORY_HOME);
        i.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(i);
    }

    public static void goBack(Context ctx) {
        if (ZeviAccessibilityService.isRunning()) {
            ZeviAccessibilityService.getInstance().performBack();
        } else {
            Toast.makeText(ctx, "Enable Accessibility for Back", Toast.LENGTH_SHORT).show();
        }
    }

    public static void openSettings(Context ctx) {
        if (ZeviAccessibilityService.isRunning()) {
            ZeviAccessibilityService svc = ZeviAccessibilityService.getInstance();
            if (svc.launchApp("com.android.settings")) return;
        }
        Intent i = new Intent(Settings.ACTION_SETTINGS);
        i.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(i);
    }

    public static void openPackage(Context ctx, String packageName) {
        if (packageName == null || packageName.isEmpty()) return;
        if (ZeviAccessibilityService.isRunning()) {
            if (ZeviAccessibilityService.getInstance().launchApp(packageName)) return;
        }
        Intent launch = ctx.getPackageManager().getLaunchIntentForPackage(packageName);
        if (launch == null) {
            Toast.makeText(ctx, "App not found: " + packageName, Toast.LENGTH_SHORT).show();
            return;
        }
        launch.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(launch);
    }

    public static boolean openAppByName(Context ctx, String name) {
        String key = name.trim().toLowerCase(Locale.US);
        // strip trailing punctuation
        key = key.replaceAll("[.!?]+$", "").trim();
        if (ALIASES.containsKey(key)) {
            openPackage(ctx, ALIASES.get(key));
            return true;
        }
        // package name?
        if (key.contains(".") && key.matches("[a-z0-9_.]+")) {
            openPackage(ctx, key);
            return true;
        }
        String pkg = resolveLauncherApp(ctx, key);
        if (pkg != null) {
            openPackage(ctx, pkg);
            return true;
        }
        return false;
    }

    private static String resolveLauncherApp(Context ctx, String nameLower) {
        PackageManager pm = ctx.getPackageManager();
        Intent main = new Intent(Intent.ACTION_MAIN, null);
        main.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> apps = pm.queryIntentActivities(main, 0);
        String exact = null;
        String partial = null;
        for (ResolveInfo ri : apps) {
            CharSequence label = ri.loadLabel(pm);
            if (label == null) continue;
            String l = label.toString().toLowerCase(Locale.US);
            String pkg = ri.activityInfo.packageName;
            if (l.equals(nameLower)) {
                exact = pkg;
                break;
            }
            if (partial == null && (l.contains(nameLower) || nameLower.contains(l))) {
                partial = pkg;
            }
        }
        return exact != null ? exact : partial;
    }

    public static void openOverlaySettings(Context ctx) {
        Intent i = new Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + ctx.getPackageName())
        );
        i.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(i);
    }

    public static void openAccessibilitySettings(Context ctx) {
        Intent i = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
        i.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(i);
    }

    /**
     * Handle simple commands on-device before (or instead of) host pilot.
     * @return human-readable result if handled, null if not a local command
     */
    public static String tryLocalCommand(Context ctx, String message) {
        if (message == null) return null;
        String m = message.trim();
        if (m.isEmpty()) return null;
        String lower = m.toLowerCase(Locale.US);

        if (lower.equals("home") || lower.equals("go home") || lower.equals("/home")
                || lower.equals("go to home") || lower.equals("press home")) {
            goHome(ctx);
            return "Went Home.";
        }
        if (lower.equals("back") || lower.equals("go back") || lower.equals("/back")) {
            goBack(ctx);
            return "Went back.";
        }
        if (lower.equals("recents") || lower.equals("recent apps") || lower.equals("/recents")) {
            if (ZeviAccessibilityService.isRunning()) {
                ZeviAccessibilityService.getInstance().performRecents();
                return "Opened Recents.";
            }
            return "Turn on screen control to open Recents.";
        }
        if (lower.equals("settings") || lower.equals("open settings") || lower.equals("/settings")) {
            openSettings(ctx);
            return "Opened Settings.";
        }
        if (lower.equals("scroll down") || lower.equals("scroll")) {
            if (ZeviAccessibilityService.isRunning()) {
                ZeviAccessibilityService.getInstance().scrollForward();
                return "Scrolled down.";
            }
            return "Turn on screen control to scroll.";
        }
        if (lower.equals("scroll up")) {
            if (ZeviAccessibilityService.isRunning()) {
                ZeviAccessibilityService.getInstance().scrollBackward();
                return "Scrolled up.";
            }
            return "Turn on screen control to scroll.";
        }

        Matcher swipe = SWIPE.matcher(m);
        if (swipe.matches()) {
            if (!ZeviAccessibilityService.isRunning()) return "Turn on screen control to swipe.";
            ZeviAccessibilityService svc = ZeviAccessibilityService.getInstance();
            int[] sz = new int[]{1080, 2280};
            try {
                android.util.DisplayMetrics dm = ctx.getResources().getDisplayMetrics();
                sz[0] = dm.widthPixels;
                sz[1] = dm.heightPixels;
            } catch (Exception ignored) {
            }
            float cx = sz[0] / 2f, cy = sz[1] / 2f;
            String dir = swipe.group(1).toLowerCase(Locale.US);
            switch (dir) {
                case "up":
                    svc.swipe(cx, cy + 400, cx, cy - 400, 300);
                    break;
                case "down":
                    svc.swipe(cx, cy - 400, cx, cy + 400, 300);
                    break;
                case "left":
                    svc.swipe(cx + 300, cy, cx - 300, cy, 300);
                    break;
                case "right":
                    svc.swipe(cx - 300, cy, cx + 300, cy, 300);
                    break;
            }
            return "Swiped " + dir + ".";
        }

        Matcher tap = TAP.matcher(m);
        if (tap.matches()) {
            if (!ZeviAccessibilityService.isRunning()) return "Turn on screen control to tap.";
            String label = tap.group(1).trim().replaceAll("^[\"']|[\"']$", "");
            boolean ok = ZeviAccessibilityService.getInstance().clickByText(label);
            return ok ? "Tapped \"" + label + "\"." : "Couldn't find \"" + label + "\" on screen.";
        }

        Matcher type = TYPE.matcher(m);
        if (type.matches()) {
            if (!ZeviAccessibilityService.isRunning()) return "Turn on screen control to type.";
            String text = type.group(1).trim().replaceAll("^[\"']|[\"']$", "");
            boolean ok = ZeviAccessibilityService.getInstance().typeText(text);
            return ok ? "Typed." : "No text field focused — tap a field first.";
        }

        if (lower.startsWith("/open ")) {
            openPackage(ctx, m.substring(6).trim());
            return "Launched.";
        }

        Matcher open = OPEN_APP.matcher(m);
        if (open.matches()) {
            String app = open.group(1).trim().replaceAll("^[\"']|[\"']$", "");
            if (openAppByName(ctx, app)) {
                return "Opened " + app + ".";
            }
            return "App not found: " + app;
        }

        return null;
    }

    private static String a11yNote() {
        return ZeviAccessibilityService.isRunning() ? " (a11y)" : " (intent)";
    }
}
