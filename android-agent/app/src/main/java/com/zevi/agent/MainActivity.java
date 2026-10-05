package com.zevi.agent;

import android.content.Intent;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.button.MaterialButton;

public class MainActivity extends AppCompatActivity {
    private PilotClient pilot;
    private TextView pilotStatus;
    private TextView pilotUrl;
    private TextView overlayStatus;
    private MaterialButton btnOverlayPerm;
    private MaterialButton btnA11y;
    private MaterialButton btnPinWidget;
    private MaterialButton btnStartBubble;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        ApiConfig.init(this);
        ApiConfig.applyIntent(this, getIntent());
        pilot = new PilotClient();
        pilotStatus = findViewById(R.id.pilotStatus);
        pilotUrl = findViewById(R.id.pilotUrl);
        overlayStatus = findViewById(R.id.overlayStatus);

        btnOverlayPerm = findViewById(R.id.btnOverlayPerm);
        btnStartBubble = findViewById(R.id.btnStartBubble);
        MaterialButton btnOpenChat = findViewById(R.id.btnOpenChat);
        MaterialButton skipToAsk = findViewById(R.id.skipToAsk);
        skipToAsk.setOnClickListener(v -> {
            v.announceForAccessibility(getString(R.string.open_chat));
            startActivity(new Intent(this, ChatActivity.class));
        });
        btnA11y = findViewById(R.id.btnA11y);
        MaterialButton btnHome = findViewById(R.id.btnHome);
        MaterialButton btnSettings = findViewById(R.id.btnSettings);
        btnPinWidget = findViewById(R.id.btnPinWidget);

        btnOverlayPerm.setOnClickListener(v -> LocalActions.openOverlaySettings(this));
        btnStartBubble.setOnClickListener(v -> startBubble());
        btnOpenChat.setOnClickListener(v ->
                startActivity(new Intent(this, ChatActivity.class)));
        btnA11y.setOnClickListener(v -> LocalActions.openAccessibilitySettings(this));
        btnHome.setOnClickListener(v -> LocalActions.goHome(this));
        btnSettings.setOnClickListener(v -> LocalActions.openSettings(this));
        if (btnPinWidget != null) {
            btnPinWidget.setOnClickListener(v -> {
                if (ZeviSearchWidget.pinnedCount(this) > 0) {
                    Toast.makeText(this, "Strlix bar is already on Home", Toast.LENGTH_SHORT).show();
                    ZeviSearchWidget.refreshAll(this);
                    return;
                }
                boolean ok = ZeviSearchWidget.requestPin(this);
                Toast.makeText(this,
                        ok ? "Confirm pin on the launcher…" : "Add from Home → Widgets → Strlix",
                        Toast.LENGTH_SHORT).show();
            });
        }

        handleLaunchExtras(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        handleLaunchExtras(intent);
    }

    private void handleLaunchExtras(Intent intent) {
        if (intent == null) return;
        if (ApiConfig.applyIntent(this, intent)) {
            pilot = new PilotClient();
            android.util.Log.i("StrlixPilot", "api override -> " + ApiConfig.publicUrl());
        }
        if (intent.getBooleanExtra("set_demo_wallpaper", false)) {
            String path = intent.getStringExtra("wallpaper_path");
            if (path == null || path.isEmpty()) {
                path = "/sdcard/Download/strlix_wallpaper.png";
            }
            DemoWallpaper.setFromPath(this, path);
        }
        if (intent.getBooleanExtra("start_qsb_mask", false)
                || "start_qsb_mask".equals(intent.getStringExtra("action"))) {
            if (Settings.canDrawOverlays(this)) {
                OverlayService.startQsbMask(this);
            }
        }
        if (intent.getBooleanExtra("start_bubble", false)
                || "start_bubble".equals(intent.getStringExtra("action"))) {
            startBubble();
        }
        if (intent.getBooleanExtra("open_chat", false)) {
            startActivity(new Intent(this, ChatActivity.class));
        }
        if (intent.getBooleanExtra("pin_widget", false)) {
            if (ZeviSearchWidget.pinnedCount(this) == 0) {
                ZeviSearchWidget.requestPin(this);
            }
        }
        if (intent.getBooleanExtra("widget_pinned", false)) {
            Toast.makeText(this, "Strlix bar added to Home", Toast.LENGTH_SHORT).show();
            ZeviSearchWidget.refreshAll(this);
        }
        if (intent.getBooleanExtra("refresh_widget", false)) {
            ZeviSearchWidget.refreshAll(this);
        }
    }

    private void startBubble() {
        if (!Settings.canDrawOverlays(this)) {
            Toast.makeText(this, "Allow display over other apps first", Toast.LENGTH_SHORT).show();
            LocalActions.openOverlaySettings(this);
            return;
        }
        OverlayService.start(this);
        Toast.makeText(this, "Bubble on — tap it to chat", Toast.LENGTH_SHORT).show();
        refreshOverlayStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        // Critical: DB-placed widgets have no PendingIntents until refresh —
        // without this, tapping the home bar opens MainActivity (MAIN/LAUNCHER).
        ZeviSearchWidget.refreshAll(this);
        refreshOverlayStatus();
        refreshPilot();
    }

    private void refreshOverlayStatus() {
        boolean overlay = Settings.canDrawOverlays(this);
        boolean a11y = ZeviAccessibilityService.isRunning();
        int widgets = ZeviSearchWidget.pinnedCount(this);
        String setupSummary =
                (overlay ? getString(R.string.overlay_granted) : getString(R.string.overlay_needed))
                        + " · "
                        + (a11y ? getString(R.string.a11y_on) : getString(R.string.a11y_off))
                        + " · Home bar: " + (widgets > 0 ? "ready" : "not added");
        overlayStatus.setText(setupSummary);
        overlayStatus.setContentDescription(
                getString(R.string.setup_status_label) + ". " + setupSummary);
        overlayStatus.sendAccessibilityEvent(
                android.view.accessibility.AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED);

        // Hide setup actions that are already done — less confusing chrome
        if (btnOverlayPerm != null) {
            btnOverlayPerm.setVisibility(overlay ? View.GONE : View.VISIBLE);
        }
        if (btnA11y != null) {
            btnA11y.setVisibility(a11y ? View.GONE : View.VISIBLE);
        }
        if (btnPinWidget != null) {
            btnPinWidget.setVisibility(widgets > 0 ? View.GONE : View.VISIBLE);
        }
        if (btnStartBubble != null) {
            // Bubble is optional for demo; keep as low-emphasis escape hatch
            btnStartBubble.setVisibility(View.VISIBLE);
        }
    }

    private void refreshPilot() {
        pilotStatus.setText("Cloud: checking…");
        pilotStatus.setContentDescription(getString(R.string.cloud_status_label) + ". Cloud: checking");
        if (pilotUrl != null) {
            pilotUrl.setVisibility(View.GONE);
        }
        pilot.health((ok, detail, url) -> {
            if (ok) {
                pilotStatus.setText("Cloud: connected");
                pilotStatus.setContentDescription(getString(R.string.cloud_status_label) + ". Cloud: connected");
                pilotStatus.setTextColor(getColor(R.color.zevi_green));
                if (pilotUrl != null) {
                    // Keep URL out of consumer UI; available in logcat / eng builds only
                    pilotUrl.setVisibility(View.GONE);
                }
            } else {
                pilotStatus.setText(getString(R.string.pilot_unreachable));
                pilotStatus.setContentDescription(getString(R.string.cloud_status_label) + ". " + getString(R.string.pilot_unreachable));
                pilotStatus.setTextColor(getColor(R.color.zevi_orange));
                if (pilotUrl != null) {
                    pilotUrl.setText(url);
                    pilotUrl.setVisibility(View.VISIBLE);
                }
            }
        });
    }
}
