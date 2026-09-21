package com.zevi.agent;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.IBinder;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;

import androidx.core.app.NotificationCompat;

/**
 * Floating overlay: optional Strlix bubble, or a wallpaper-matched mask that
 * covers Pixel launcher's built-in Google Quick Search Box so only the Strlix
 * home widget remains as the search UI.
 */
public class OverlayService extends Service {
    public static final String ACTION_STOP = "com.zevi.agent.STOP_OVERLAY";
    public static final String EXTRA_MODE = "mode";
    public static final String MODE_BUBBLE = "bubble";
    public static final String MODE_QSB_MASK = "qsb_mask";

    private static final String CHANNEL = "strlix_overlay";
    private static final int NOTIF_ID = 4201;

    private WindowManager windowManager;
    private View overlayView;
    private WindowManager.LayoutParams params;
    private String mode = MODE_BUBBLE;
    private int startX, startY;
    private float touchX, touchY;
    private boolean moved;

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }
        if (intent != null && intent.getStringExtra(EXTRA_MODE) != null) {
            mode = intent.getStringExtra(EXTRA_MODE);
        }
        startForeground(NOTIF_ID, buildNotification());
        showOverlay();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        removeOverlay();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void removeOverlay() {
        if (overlayView != null && windowManager != null) {
            try {
                windowManager.removeView(overlayView);
            } catch (Exception ignored) {
            }
            overlayView = null;
        }
    }

    private void showOverlay() {
        removeOverlay();
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        if (MODE_QSB_MASK.equals(mode)) {
            showQsbMask();
        } else {
            showBubble();
        }
    }

    /** Opaque bar matching demo wallpaper — covers Google hotseat QSB. */
    private void showQsbMask() {
        DisplayMetrics dm = getResources().getDisplayMetrics();
        int screenW = dm.widthPixels;
        int screenH = dm.heightPixels;

        // Cover Google hotseat QSB fully (typical bounds ~y 2120–2290 on 2400h).
        // Keep above gesture pill; do not cover dock icons (~y 1870–2070).
        int maskH = Math.max(dp(72), (int) (screenH * 0.085f));
        int bottomPad = Math.max(dp(8), (int) (screenH * 0.008f));

        FrameLayout frame = new FrameLayout(this);
        GradientDrawable bg = new GradientDrawable();
        // Pure black blends with demo wallpaper / default dark home
        bg.setColor(Color.parseColor("#0C0E16")); // match demo wallpaper bottom
        bg.setCornerRadius(0f);
        frame.setBackground(bg);
        frame.setClickable(true);
        frame.setFocusable(false);

        int type = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY;
        params = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                maskH,
                type,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                        | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.OPAQUE
        );
        params.gravity = Gravity.BOTTOM | Gravity.FILL_HORIZONTAL;
        params.x = 0;
        params.y = bottomPad;
        params.width = screenW;
        overlayView = frame;
        windowManager.addView(overlayView, params);
    }

    private void showBubble() {
        overlayView = LayoutInflater.from(this).inflate(R.layout.overlay_bubble, null);

        int type = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY;
        params = new WindowManager.LayoutParams(
                dp(56),
                dp(56),
                type,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.TRANSLUCENT
        );
        params.gravity = Gravity.TOP | Gravity.START;
        params.x = dp(16);
        params.y = dp(160);

        overlayView.setOnTouchListener((v, event) -> {
            switch (event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                    startX = params.x;
                    startY = params.y;
                    touchX = event.getRawX();
                    touchY = event.getRawY();
                    moved = false;
                    return true;
                case MotionEvent.ACTION_MOVE:
                    int dx = (int) (event.getRawX() - touchX);
                    int dy = (int) (event.getRawY() - touchY);
                    if (Math.abs(dx) > 8 || Math.abs(dy) > 8) {
                        moved = true;
                    }
                    params.x = startX + dx;
                    params.y = startY + dy;
                    windowManager.updateViewLayout(overlayView, params);
                    return true;
                case MotionEvent.ACTION_UP:
                    if (!moved) {
                        openChat();
                    }
                    return true;
                default:
                    return false;
            }
        });

        windowManager.addView(overlayView, params);
    }

    private void openChat() {
        Intent i = new Intent(this, ChatActivity.class);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(i);
    }

    private void createChannel() {
        NotificationChannel ch = new NotificationChannel(
                CHANNEL,
                getString(R.string.overlay_channel),
                NotificationManager.IMPORTANCE_LOW
        );
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm != null) {
            nm.createNotificationChannel(ch);
        }
    }

    private Notification buildNotification() {
        Intent open = new Intent(this, ChatActivity.class);
        open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent pi = PendingIntent.getActivity(
                this, 0, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        Intent stop = new Intent(this, OverlayService.class);
        stop.setAction(ACTION_STOP);
        PendingIntent stopPi = PendingIntent.getService(
                this, 1, stop,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        String text = MODE_QSB_MASK.equals(mode)
                ? "Keeping Home focused on Strlix"
                : getString(R.string.overlay_notif);
        return new NotificationCompat.Builder(this, CHANNEL)
                .setContentTitle("Strlix Copilot")
                .setContentText(text)
                .setSmallIcon(R.drawable.ic_zevi_launcher)
                .setContentIntent(pi)
                .addAction(0, "Stop", stopPi)
                .setOngoing(true)
                .build();
    }

    private int dp(int v) {
        float d = getResources().getDisplayMetrics().density;
        return Math.round(v * d);
    }

    public static void start(Context ctx) {
        start(ctx, MODE_BUBBLE);
    }

    public static void start(Context ctx, String mode) {
        Intent i = new Intent(ctx, OverlayService.class);
        i.putExtra(EXTRA_MODE, mode);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ctx.startForegroundService(i);
        } else {
            ctx.startService(i);
        }
    }

    public static void startQsbMask(Context ctx) {
        start(ctx, MODE_QSB_MASK);
    }

    public static void stop(Context ctx) {
        Intent i = new Intent(ctx, OverlayService.class);
        i.setAction(ACTION_STOP);
        ctx.startService(i);
    }
}
