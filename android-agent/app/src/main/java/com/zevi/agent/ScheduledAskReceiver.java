package com.zevi.agent;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import androidx.core.app.NotificationCompat;

/** Delivers a visible, user-controlled reminder for a recurring Ask. */
public final class ScheduledAskReceiver extends BroadcastReceiver {
    public static final String ACTION_FIRE = "com.zevi.agent.SCHEDULED_ASK";
    private static final String CHANNEL = "scheduled_asks";
    private static final int NOTIFICATION_ID = 4092;

    @Override public void onReceive(Context context, Intent intent) {
        if (!ACTION_FIRE.equals(intent == null ? null : intent.getAction())) return;
        ScheduledAskStore.Schedule schedule = ScheduledAskStore.load(context);
        if (!schedule.enabled || schedule.ask.isEmpty()) return;
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(new NotificationChannel(CHANNEL, "Scheduled Asks", NotificationManager.IMPORTANCE_DEFAULT));
        }
        Intent open = new Intent(context, ChatActivity.class)
                .setAction("com.zevi.agent.OPEN_SCHEDULED_ASK")
                .putExtra("scheduled_ask", schedule.ask)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent openPending = PendingIntent.getActivity(context, NOTIFICATION_ID, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        manager.notify(NOTIFICATION_ID, new NotificationCompat.Builder(context, CHANNEL)
                .setSmallIcon(R.drawable.ic_zevi_launcher)
                .setContentTitle("Strlix is ready")
                .setContentText(schedule.ask)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(schedule.ask))
                .setContentIntent(openPending)
                .setAutoCancel(true)
                .addAction(new NotificationCompat.Action.Builder(0, "Open Ask", openPending).build())
                .build());
    }
}
