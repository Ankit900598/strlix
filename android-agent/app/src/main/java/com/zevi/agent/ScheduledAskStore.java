package com.zevi.agent;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import java.util.Calendar;

/** Small, local-only recurring Ask. It schedules a reminder, not a hidden background action. */
public final class ScheduledAskStore {
    private static final String PREFS = "strlix_schedule";
    private static final String KEY_ASK = "ask";
    private static final String KEY_CADENCE = "cadence";
    private static final String KEY_HOUR = "hour";
    private static final String KEY_MINUTE = "minute";
    private static final String KEY_ENABLED = "enabled";
    private static final int REQUEST_CODE = 4091;

    private ScheduledAskStore() {}

    public static final class Schedule {
        public final String ask;
        public final String cadence;
        public final int hour;
        public final int minute;
        public final boolean enabled;

        Schedule(String ask, String cadence, int hour, int minute, boolean enabled) {
            this.ask = ask;
            this.cadence = cadence;
            this.hour = hour;
            this.minute = minute;
            this.enabled = enabled;
        }

        public String label() {
            String day = "weekly".equals(cadence) ? "Every week" : "Every day";
            return day + " · " + String.format(java.util.Locale.getDefault(), "%02d:%02d", hour, minute);
        }
    }

    public static Schedule load(Context context) {
        android.content.SharedPreferences p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String ask = p.getString(KEY_ASK, "");
        if (ask == null) ask = "";
        return new Schedule(ask, p.getString(KEY_CADENCE, "daily"),
                p.getInt(KEY_HOUR, 9), p.getInt(KEY_MINUTE, 0), p.getBoolean(KEY_ENABLED, false));
    }

    public static void save(Context context, String ask, String cadence, int hour, int minute) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .putString(KEY_ASK, ask.trim())
                .putString(KEY_CADENCE, cadence)
                .putInt(KEY_HOUR, hour)
                .putInt(KEY_MINUTE, minute)
                .putBoolean(KEY_ENABLED, true)
                .apply();
        scheduleAlarm(context, load(context));
    }

    public static void cancel(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY_ENABLED, false).apply();
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms != null) alarms.cancel(pendingIntent(context));
    }

    private static PendingIntent pendingIntent(Context context) {
        Intent intent = new Intent(context, ScheduledAskReceiver.class)
                .setAction(ScheduledAskReceiver.ACTION_FIRE);
        return PendingIntent.getBroadcast(context, REQUEST_CODE, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private static void scheduleAlarm(Context context, Schedule schedule) {
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms == null || !schedule.enabled || schedule.ask.isEmpty()) return;
        Calendar first = Calendar.getInstance();
        first.set(Calendar.HOUR_OF_DAY, schedule.hour);
        first.set(Calendar.MINUTE, schedule.minute);
        first.set(Calendar.SECOND, 0);
        first.set(Calendar.MILLISECOND, 0);
        if (first.getTimeInMillis() <= System.currentTimeMillis()) {
            first.add(Calendar.DAY_OF_YEAR, "weekly".equals(schedule.cadence) ? 7 : 1);
        }
        long interval = "weekly".equals(schedule.cadence)
                ? AlarmManager.INTERVAL_DAY * 7L : AlarmManager.INTERVAL_DAY;
        alarms.setInexactRepeating(AlarmManager.RTC_WAKEUP, first.getTimeInMillis(), interval, pendingIntent(context));
    }
}
