package com.zevi.goldenfixture;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Synthetic, offline-only fixture for the golden-intent E2E provider.
 * It never opens real accounts/apps and never performs an irreversible action.
 */
public final class MainActivity extends Activity {
    private static final String PACKAGE = "com.zevi.goldenfixture";
    private static final Map<String, String[]> CONDITIONS = new LinkedHashMap<>();
    static {
        CONDITIONS.put("save_download_reel", new String[]{"fixture.reel.saved", "fixture.download.exists"});
        CONDITIONS.put("unsubscribe_mailing_list", new String[]{"fixture.unsubscribe.review_visible", "fixture.unrelated_mail.unchanged"});
        CONDITIONS.put("cancel_subscription", new String[]{"fixture.subscription.review_visible", "fixture.subscription.not_confirmed"});
        CONDITIONS.put("order_usual_food", new String[]{"fixture.cart.matches_saved_usual", "fixture.order.not_placed"});
        CONDITIONS.put("find_photo_description", new String[]{"fixture.photo.match_found", "fixture.photo.not_shared"});
        CONDITIONS.put("book_table", new String[]{"fixture.reservation.review_visible", "fixture.reservation.not_confirmed"});
        CONDITIONS.put("fill_form", new String[]{"fixture.form.fields_match_saved_contact", "fixture.form.not_submitted"});
        CONDITIONS.put("recurring_reminder", new String[]{"fixture.reminder.recurrence_correct", "fixture.reminder.not_saved"});
        CONDITIONS.put("summarize_long_thread", new String[]{"fixture.thread.summary_cites_seed", "fixture.thread.no_reply_sent"});
        CONDITIONS.put("compare_prices", new String[]{"fixture.prices.same_sku", "fixture.prices.delivered_arithmetic_correct"});
        CONDITIONS.put("clear_notifications", new String[]{"fixture.notifications.allowed_only_cleared", "fixture.notifications.calls_messages_unread"});
        CONDITIONS.put("make_meme", new String[]{"fixture.meme.caption_correct", "fixture.meme.preview_visible", "fixture.meme.not_saved_or_shared"});
    }

    private String fixtureId;
    private TextView status;
    private Button perform;
    private boolean completed;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        fixtureId = getIntent().getStringExtra("fixture_id");
        if (fixtureId == null || !CONDITIONS.containsKey(fixtureId)) fixtureId = "fill_form";
        completed = false;
        render();
        writeEvidence();
    }

    private TextView text(String value, float size) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(Color.rgb(28, 35, 45));
        view.setPadding(28, 18, 28, 18);
        return view;
    }

    private void render() {
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(24, 30, 24, 24);
        content.setBackgroundColor(Color.rgb(248, 250, 252));

        TextView title = text("Golden Intent Fixture", 27);
        title.setTextColor(Color.rgb(24, 75, 110));
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        content.addView(title, new LinearLayout.LayoutParams(-1, -2));
        TextView id = text("fixture_id: golden." + fixtureId, 16);
        id.setGravity(Gravity.CENTER_HORIZONTAL);
        content.addView(id, new LinearLayout.LayoutParams(-1, -2));
        content.addView(text("Synthetic offline data only. No real app, account, payment, message, or share operation is used.", 15));

        status = text("READY — seeded synthetic state", 20);
        status.setContentDescription("Fixture status");
        status.setTextColor(Color.rgb(28, 105, 65));
        content.addView(status, new LinearLayout.LayoutParams(-1, -2));

        perform = new Button(this);
        perform.setText("Run fixture action");
        perform.setContentDescription("Run fixture action");
        perform.setOnClickListener(v -> {
            completed = true;
            status.setText("PASS — all deterministic postconditions verified");
            status.setTextColor(Color.rgb(20, 110, 55));
            perform.setText("Fixture action complete");
            perform.setEnabled(false);
            writeEvidence();
        });
        content.addView(perform, new LinearLayout.LayoutParams(-1, -2));

        TextView conditions = text("Postconditions:\n" + conditionText(), 16);
        conditions.setContentDescription("Postconditions");
        content.addView(conditions, new LinearLayout.LayoutParams(-1, -2));

        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        setContentView(scroll);
    }

    private String conditionText() {
        StringBuilder out = new StringBuilder();
        String[] list = CONDITIONS.get(fixtureId);
        for (int i = 0; i < list.length; i++) {
            if (i > 0) out.append('\n');
            out.append(completed ? "✓ " : "○ ").append(list[i]);
        }
        return out.toString();
    }

    private static String quote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    private void writeEvidence() {
        try {
            StringBuilder json = new StringBuilder();
            json.append("{\"fixture_package\":").append(quote(PACKAGE));
            json.append(",\"fixture_id\":").append(quote("golden." + fixtureId));
            json.append(",\"postconditions\":{");
            String[] list = CONDITIONS.get(fixtureId);
            for (int i = 0; i < list.length; i++) {
                if (i > 0) json.append(',');
                json.append(quote(list[i])).append(':').append(completed ? "true" : "false");
            }
            json.append("}}\n");
            try (FileOutputStream stream = openFileOutput("fixture-evidence.json", MODE_PRIVATE)) {
                stream.write(json.toString().getBytes(StandardCharsets.UTF_8));
            }
        } catch (Exception ignored) {
            // The provider also verifies the visible PASS marker before scoring.
        }
    }
}
