package com.zevi.agent;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.widget.RemoteViews;
import android.widget.Toast;

/**
 * Home-screen Google-style search pill. Tap opens Strlix voice+text assistant.
 * Branding: S logo + colored dots instead of G / Assistant.
 */
public class ZeviSearchWidget extends AppWidgetProvider {
    public static final String ACTION_OPEN_ASSISTANT = "com.zevi.agent.OPEN_ASSISTANT";
    public static final String EXTRA_FROM_WIDGET = "from_widget";
    public static final String EXTRA_VOICE = "start_voice";

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] appWidgetIds) {
        for (int id : appWidgetIds) {
            updateAppWidget(context, manager, id);
        }
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (intent == null || intent.getAction() == null) return;
        if (ACTION_OPEN_ASSISTANT.equals(intent.getAction())
                || Intent.ACTION_VIEW.equals(intent.getAction())) {
            boolean voice = intent.getBooleanExtra(EXTRA_VOICE, false)
                    || "voice".equals(intent.getStringExtra("mode"));
            openAssistant(context, voice);
        }
    }

    static void updateAppWidget(Context context, AppWidgetManager manager, int appWidgetId) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_search_pill);

        Intent open = new Intent(context, ChatActivity.class);
        open.setAction(ACTION_OPEN_ASSISTANT);
        open.putExtra(EXTRA_FROM_WIDGET, true);
        open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP
                | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent openPi = PendingIntent.getActivity(
                context, appWidgetId, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widgetRoot, openPi);
        views.setOnClickPendingIntent(R.id.widgetHint, openPi);
        views.setOnClickPendingIntent(R.id.widgetLogo, openPi);

        Intent voice = new Intent(context, ChatActivity.class);
        voice.setAction(ACTION_OPEN_ASSISTANT);
        voice.putExtra(EXTRA_FROM_WIDGET, true);
        voice.putExtra(EXTRA_VOICE, true);
        voice.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP
                | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent voicePi = PendingIntent.getActivity(
                context, appWidgetId + 10000, voice,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widgetMic, voicePi);
        views.setOnClickPendingIntent(R.id.widgetDots, voicePi);

        manager.updateAppWidget(appWidgetId, views);
    }

    public static void openAssistant(Context context, boolean startVoice) {
        Intent i = new Intent(context, ChatActivity.class);
        i.putExtra(EXTRA_FROM_WIDGET, true);
        i.putExtra(EXTRA_VOICE, startVoice);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP
                | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        context.startActivity(i);
    }

    /** How many Strlix search pills are already on the home screen. */
    public static int pinnedCount(Context context) {
        AppWidgetManager mgr = AppWidgetManager.getInstance(context);
        int[] ids = mgr.getAppWidgetIds(new ComponentName(context, ZeviSearchWidget.class));
        return ids == null ? 0 : ids.length;
    }

    /**
     * Request launcher to pin the Strlix search pill (API 26+).
     * No-ops if one is already pinned — never create duplicates.
     */
    public static boolean requestPin(Context context) {
        if (pinnedCount(context) > 0) {
            Toast.makeText(context, "Strlix search bar already on Home", Toast.LENGTH_SHORT).show();
            return false;
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            Toast.makeText(context, "Pin widget from Home → Widgets → Strlix", Toast.LENGTH_LONG).show();
            return false;
        }
        AppWidgetManager mgr = AppWidgetManager.getInstance(context);
        ComponentName provider = new ComponentName(context, ZeviSearchWidget.class);
        if (!mgr.isRequestPinAppWidgetSupported()) {
            Toast.makeText(context, "Add from Home → Widgets → Strlix Copilot", Toast.LENGTH_LONG).show();
            return false;
        }
        Intent success = new Intent(context, MainActivity.class);
        success.putExtra("widget_pinned", true);
        PendingIntent successPi = PendingIntent.getActivity(
                context, 42, success,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        Bundle extras = new Bundle();
        return mgr.requestPinAppWidget(provider, extras, successPi);
    }

    public static void refreshAll(Context context) {
        AppWidgetManager mgr = AppWidgetManager.getInstance(context);
        int[] ids = mgr.getAppWidgetIds(new ComponentName(context, ZeviSearchWidget.class));
        if (ids != null && ids.length > 0) {
            for (int id : ids) {
                updateAppWidget(context, mgr, id);
            }
        }
    }
}
