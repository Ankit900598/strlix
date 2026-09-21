package com.zevi.agent;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.BroadcastReceiver;
import android.util.Base64;

import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/**
 * Small ADB-only continuity bridge for the desktop bezel.
 *
 * Android 10+ intentionally has no stable `adb shell` clipboard command. The
 * host talks to this explicit component over the already trusted ADB channel;
 * exported is required because the caller is the ADB shell uid. Clipboard
 * export is written to app-private storage and read once with run-as by the
 * debug host, then deleted.
 */
public final class ClipboardBridgeReceiver extends BroadcastReceiver {
    public static final String ACTION_SET = "com.zevi.agent.CLIPBOARD_SET";
    public static final String ACTION_EXPORT = "com.zevi.agent.CLIPBOARD_EXPORT";
    private static final String EXPORT_FILE = ".strlix-clipboard.b64";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) return;
        ClipboardManager clipboard =
                (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
        if (clipboard == null) return;
        try {
            if (ACTION_SET.equals(intent.getAction())) {
                String encoded = intent.getStringExtra("text_b64");
                if (encoded == null) encoded = "";
                byte[] bytes = Base64.decode(encoded, Base64.DEFAULT);
                String text = new String(bytes, StandardCharsets.UTF_8);
                clipboard.setPrimaryClip(ClipData.newPlainText("Strlix", text));
                setResultCode(Activity.RESULT_OK);
                return;
            }
            if (ACTION_EXPORT.equals(intent.getAction())) {
                String text = "";
                if (clipboard.hasPrimaryClip()) {
                    ClipData clip = clipboard.getPrimaryClip();
                    if (clip != null && clip.getItemCount() > 0 && clip.getItemAt(0).getText() != null) {
                        text = clip.getItemAt(0).getText().toString();
                    }
                }
                byte[] encoded = Base64.encode(
                        text.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP);
                try (FileOutputStream out = context.openFileOutput(EXPORT_FILE, Context.MODE_PRIVATE)) {
                    out.write(encoded);
                }
                setResultCode(Activity.RESULT_OK);
            }
        } catch (Exception ignored) {
            setResultCode(Activity.RESULT_CANCELED);
        }
    }
}
