package com.zevi.agent;

import android.Manifest;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.view.View;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.inputmethod.EditorInfo;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.TimePicker;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.google.android.material.button.MaterialButton;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Voice + text assistant sheet. Local a11y actions first; else host POST /chat.
 */
public class ChatActivity extends AppCompatActivity {
    private static final int REQ_MIC = 7101;

    private PilotClient pilot;
    private MessageAdapter adapter;
    private EditText input;
    private TextView chatStatus;
    private MaterialButton btnSend;
    private ImageButton btnMic;
    private RecyclerView messageList;
    private View chipScroll;
    private View skipToMessage;
    private View doStrip;
    private TextView doNarration;
    private TextView scheduleSummary;
    private TextView triageState;
    private TextView doShare;
    private ReplaySession replay;
    private final List<JSONObject> history = new ArrayList<>();
    private boolean busy;
    private SpeechRecognizer speechRecognizer;
    private boolean listening;
    private boolean pendingVoiceStart;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_chat);

        ApiConfig.init(this); pilot = new PilotClient();
        replay = new ReplaySession(pilot);
        chatStatus = findViewById(R.id.chatStatus);
        input = findViewById(R.id.input);
        btnSend = findViewById(R.id.btnSend);
        btnMic = findViewById(R.id.btnMic);

        messageList = findViewById(R.id.messageList);
        adapter = new MessageAdapter();
        messageList.setLayoutManager(new LinearLayoutManager(this));
        messageList.setAdapter(adapter);

        boolean fromWidget = getIntent() != null
                && getIntent().getBooleanExtra(ZeviSearchWidget.EXTRA_FROM_WIDGET, false);
        // Keep home-bar PendingIntents alive whenever chat opens
        ZeviSearchWidget.refreshAll(this);
        String welcome = fromWidget
                ? getString(R.string.chat_welcome_widget)
                : getString(R.string.chat_welcome);
        if (!ZeviAccessibilityService.isRunning()) {
            welcome += "\n\nTip: turn on screen control in Strlix setup so I can tap and type for you.";
        }
        adapter.add(MessageAdapter.Message.agent(welcome));

        chipScroll = findViewById(R.id.chipScroll);
        scheduleSummary = findViewById(R.id.scheduleSummary);
        triageState = findViewById(R.id.triageState);
        skipToMessage = findViewById(R.id.skipToMessage);
        if (skipToMessage != null) {
            skipToMessage.setOnClickListener(v -> {
                input.requestFocus();
                input.sendAccessibilityEvent(android.view.accessibility.AccessibilityEvent.TYPE_VIEW_FOCUSED);
            });
            // The skip link is the first deliberate keyboard/TalkBack stop; it avoids
            // forcing a user through optional suggestions before the Ask field.
            skipToMessage.post(() -> skipToMessage.requestFocus());
        }
        doStrip = findViewById(R.id.doStrip);
        doNarration = findViewById(R.id.doNarration);
        doShare = findViewById(R.id.doShare);
        if (doShare != null) {
            doShare.setOnClickListener(v -> {
                v.setEnabled(false);
                Toast.makeText(this, R.string.replay_exporting, Toast.LENGTH_SHORT).show();
                replay.share(this, "Strlix Ask replay", (ok, detail) -> v.setEnabled(true));
            });
        }
        View doStop = findViewById(R.id.doStop);
        if (doStop != null) {
            doStop.setOnClickListener(v -> exitDoMode(null));
        }

        findViewById(R.id.chipChrome).setOnClickListener(v -> send("Open Chrome"));
        findViewById(R.id.chipHome).setOnClickListener(v -> send("Go home"));
        findViewById(R.id.chipScreen).setOnClickListener(v ->
                send("What's on my screen?"));
        findViewById(R.id.chipLive).setOnClickListener(v ->
                startActivity(new Intent(this, LiveActivity.class)));
        findViewById(R.id.chipSchedule).setOnClickListener(v -> showScheduleDialog());
        if (scheduleSummary != null) scheduleSummary.setOnClickListener(v -> showScheduleDialog());

        View triageOpen = findViewById(R.id.triageOpen);
        if (triageOpen != null) triageOpen.setOnClickListener(v -> openNotificationShade());
        View triageAsk = findViewById(R.id.triageAsk);
        if (triageAsk != null) triageAsk.setOnClickListener(v ->
                send("Review the notifications I choose and handle the actionable ones."));
        refreshScheduleSurface();

        // Long-press status opens setup (engineer console) — product entry is Ask.
        chatStatus.setOnLongClickListener(v -> {
            startActivity(new Intent(this, MainActivity.class));
            return true;
        });

        btnSend.setOnClickListener(v -> send(input.getText().toString()));
        btnMic.setOnClickListener(v -> toggleVoice());
        input.setOnEditorActionListener((tv, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEND) {
                send(input.getText().toString());
                return true;
            }
            return false;
        });

        pilot.health((ok, detail, url) ->
                announceStatus(ok ? statusOnline() : getString(R.string.status_offline), false));

        handleVoiceExtra(getIntent());
        handleAgentResult(getIntent());
        handleScheduledAsk(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleVoiceExtra(intent);
        handleAgentResult(intent);
        handleScheduledAsk(intent);
    }

    private void handleScheduledAsk(Intent intent) {
        if (intent == null || input == null) return;
        String ask = intent.getStringExtra("scheduled_ask");
        if (ask == null || ask.trim().isEmpty()) return;
        intent.removeExtra("scheduled_ask");
        input.setText(ask);
        input.setSelection(input.length());
        announceStatus(getString(R.string.schedule_ready), true);
        adapter.add(MessageAdapter.Message.agent(getString(R.string.schedule_ready)));
        scrollToEnd();
    }

    private void handleAgentResult(Intent intent) {
        if (intent == null || adapter == null) return;
        String r = intent.getStringExtra("agent_result");
        if (r != null && !r.isEmpty()) {
            intent.removeExtra("agent_result");
            adapter.add(MessageAdapter.Message.agent(r));
            scrollToEnd();
            Toast.makeText(this, r, Toast.LENGTH_SHORT).show();
        }
    }

    private void handleVoiceExtra(Intent intent) {
        if (intent != null && intent.getBooleanExtra(ZeviSearchWidget.EXTRA_VOICE, false)) {
            pendingVoiceStart = true;
            input.post(this::toggleVoice);
        }
    }

    private void openNotificationShade() {
        ZeviAccessibilityService service = ZeviAccessibilityService.getInstance();
        if (service == null) {
            Toast.makeText(this, "Turn on screen control to open notifications", Toast.LENGTH_LONG).show();
            announceStatus("Screen control is needed to open notifications", true);
            return;
        }
        if (triageState != null) triageState.setText("Choose what to handle");
        service.performNotifications();
        moveTaskToBack(true);
    }

    private void refreshScheduleSurface() {
        if (scheduleSummary == null) return;
        ScheduledAskStore.Schedule schedule = ScheduledAskStore.load(this);
        if (schedule.enabled && !schedule.ask.isEmpty()) {
            scheduleSummary.setVisibility(View.VISIBLE);
            scheduleSummary.setText(getString(R.string.schedule_saved, schedule.label()) + " · Edit");
            scheduleSummary.setContentDescription(scheduleSummary.getText());
        } else {
            scheduleSummary.setVisibility(View.GONE);
        }
    }

    private void showScheduleDialog() {
        ScheduledAskStore.Schedule current = ScheduledAskStore.load(this);
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (20 * getResources().getDisplayMetrics().density);
        box.setPadding(pad, 0, pad, 0);

        EditText askField = new EditText(this);
        askField.setHint(R.string.schedule_hint);
        askField.setSingleLine(false);
        askField.setMinLines(2);
        askField.setText(current.ask);
        askField.setContentDescription(getString(R.string.schedule_hint));
        box.addView(askField, new LinearLayout.LayoutParams(-1, -2));

        Spinner cadence = new Spinner(this);
        ArrayAdapter<String> cadenceAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item,
                new String[]{getString(R.string.schedule_daily), getString(R.string.schedule_weekly)});
        cadence.setAdapter(cadenceAdapter);
        cadence.setSelection("weekly".equals(current.cadence) ? 1 : 0);
        cadence.setContentDescription(getString(R.string.schedule_cadence));
        box.addView(cadence, new LinearLayout.LayoutParams(-1, -2));

        TimePicker picker = new TimePicker(this);
        picker.setIs24HourView(android.text.format.DateFormat.is24HourFormat(this));
        picker.setHour(current.hour);
        picker.setMinute(current.minute);
        picker.setContentDescription(getString(R.string.schedule_time));
        box.addView(picker, new LinearLayout.LayoutParams(-1, -2));

        AlertDialog.Builder builder = new AlertDialog.Builder(this)
                .setTitle(R.string.schedule_title)
                .setView(box)
                .setNegativeButton(R.string.schedule_cancel, null)
                .setPositiveButton(R.string.schedule_save, null);
        if (current.enabled) builder.setNeutralButton(R.string.schedule_pause, null);
        AlertDialog dialog = builder.create();
        dialog.setOnShowListener(ignored -> {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                String ask = askField.getText().toString().trim();
                if (ask.isEmpty()) {
                    askField.setError(getString(R.string.schedule_hint));
                    return;
                }
                String cadenceValue = cadence.getSelectedItemPosition() == 1 ? "weekly" : "daily";
                ScheduledAskStore.save(this, ask, cadenceValue, picker.getHour(), picker.getMinute());
                refreshScheduleSurface();
                announceStatus(getString(R.string.schedule_saved, ScheduledAskStore.load(this).label()), true);
                dialog.dismiss();
            });
            if (current.enabled) dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                ScheduledAskStore.cancel(this);
                refreshScheduleSurface();
                announceStatus(getString(R.string.schedule_paused), true);
                dialog.dismiss();
            });
        });
        dialog.show();
    }

    private String a11yShort() {
        return ZeviAccessibilityService.isRunning() ? "control on" : "control off";
    }

    private String statusOnline() {
        return getString(R.string.status_online) + " · " + a11yShort();
    }

    private void announceStatus(CharSequence text, boolean announce) {
        if (chatStatus == null) return;
        chatStatus.setText(text);
        chatStatus.setContentDescription(getString(R.string.cloud_status_label) + ". " + text);
        if (announce) {
            chatStatus.sendAccessibilityEvent(
                    android.view.accessibility.AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED);
        }
    }

    private void enterDoMode(String narration) {
        replay.start("Strlix Ask replay");
        if (chipScroll != null) chipScroll.setVisibility(View.GONE);
        if (scheduleSummary != null) scheduleSummary.setVisibility(View.GONE);
        if (doStrip != null) {
            doStrip.setVisibility(View.VISIBLE);
            if (doNarration != null) {
                String text = narration == null ? getString(R.string.status_working) : narration;
                doNarration.setText(text);
                doNarration.setContentDescription(getString(R.string.working_status_description) + ". " + text);
                doNarration.sendAccessibilityEvent(
                        android.view.accessibility.AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED);
            }
        }
        if (messageList != null) messageList.setAlpha(0.35f);
    }

    private void exitDoMode(String finalLine) {
        if (finalLine != null && !finalLine.isEmpty()) replay.addStep(finalLine);
        replay.stop();
        if (doStrip != null) doStrip.setVisibility(View.GONE);
        if (chipScroll != null) chipScroll.setVisibility(View.VISIBLE);
        refreshScheduleSurface();
        if (messageList != null) messageList.setAlpha(1f);
        if (finalLine != null && !finalLine.isEmpty() && doNarration != null) {
            // keep last line only as a toast-ish status
            announceStatus(finalLine.length() > 40 ? finalLine.substring(0, 40) + "…" : finalLine, true);
        }
    }

    private void setNarration(String line) {
        replay.addStep(line);
        if (doNarration != null && line != null) {
            doNarration.setText(line);
            doNarration.setContentDescription(getString(R.string.working_status_description) + ". " + line);
            doNarration.sendAccessibilityEvent(
                    android.view.accessibility.AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED);
        }
        announceStatus(line == null ? getString(R.string.status_working) : line, true);
    }

    private void send(String raw) {
        String message = raw == null ? "" : raw.trim();
        if (message.isEmpty() || busy) {
            return;
        }
        input.setText("");
        adapter.add(MessageAdapter.Message.user(message));
        scrollToEnd();
        enterDoMode("On it…");

        // Gesture commands need another app in front — finish chat, act, then reopen with result
        String lower = message.toLowerCase(Locale.US);
        boolean needsForeground = lower.startsWith("tap ") || lower.startsWith("click ")
                || lower.startsWith("type ") || lower.startsWith("enter ")
                || lower.startsWith("swipe ") || lower.equals("scroll down")
                || lower.equals("scroll") || lower.equals("scroll up");
        if (needsForeground && ZeviAccessibilityService.isRunning()) {
            setNarration("Running on-screen…");
            adapter.add(MessageAdapter.Message.agent("OK — running on-screen…"));
            scrollToEnd();
            // Move whole Zevi task back so Settings/other apps stay focused (finish() would reveal MainActivity)
            ZeviAccessibilityService.getInstance().queueForegroundCommand(message, 700);
            moveTaskToBack(true);
            return;
        }

        String local = LocalActions.tryLocalCommand(this, message);
        if (local != null) {
            setNarration(local);
            adapter.add(MessageAdapter.Message.agent(local));
            scrollToEnd();
            messageList.postDelayed(() -> exitDoMode(local), 900);
            return;
        }

        busy = true;
        setNarration(getString(R.string.status_thinking));
        btnSend.setEnabled(false);

        pilot.chat(message, history, new PilotClient.ChatCallback() {
            @Override
            public void onSuccess(String reply, String rawJson) {
                busy = false;
                btnSend.setEnabled(true);
                String shown = reply == null || reply.isEmpty() ? "Done" : reply;
                // Prefer tool narration if android-api returned tools[]
                String narrate = shown;
                try {
                    JSONObject j = new JSONObject(rawJson == null ? "{}" : rawJson);
                    org.json.JSONArray tools = j.optJSONArray("tools");
                    if (tools != null && tools.length() > 0) {
                        JSONObject t0 = tools.optJSONObject(0);
                        if (t0 != null) {
                            String name = t0.optString("name", "");
                            JSONObject args = t0.optJSONObject("args");
                            if ("a11y_launch".equals(name) && args != null) {
                                narrate = "Opening " + args.optString("app", args.optString("package", "app")) + "…";
                            } else if ("a11y_tap".equals(name)) {
                                narrate = "Tapping…";
                            } else if ("a11y_type".equals(name)) {
                                narrate = "Typing…";
                            } else {
                                narrate = shown;
                            }
                        }
                    }
                } catch (Exception ignored) {
                }
                setNarration(narrate);
                adapter.add(MessageAdapter.Message.agent(shown));
                scrollToEnd();
                messageList.postDelayed(() -> {
                    exitDoMode(shown);
                    announceStatus(statusOnline(), true);
                }, 1200);
                try {
                    JSONObject u = new JSONObject();
                    u.put("role", "user");
                    u.put("content", message);
                    history.add(u);
                    JSONObject a = new JSONObject();
                    a.put("role", "assistant");
                    a.put("content", reply);
                    history.add(a);
                } catch (Exception ignored) {
                }
            }

            @Override
            public void onError(String error) {
                busy = false;
                btnSend.setEnabled(true);
                String friendly = friendlyError(error);
                setNarration(friendly);
                adapter.add(MessageAdapter.Message.agent(friendly));
                scrollToEnd();
                messageList.postDelayed(() -> {
                    exitDoMode(null);
                    announceStatus(getString(R.string.status_offline), true);
                }, 1000);
                Toast.makeText(ChatActivity.this, R.string.error_generic, Toast.LENGTH_SHORT).show();
            }
        });
    }

    private String friendlyError(String error) {
        if (error == null || error.isEmpty()) {
            return getString(R.string.error_generic);
        }
        String e = error.toLowerCase(Locale.US);
        if (e.contains("unreachable") || e.contains("failed to connect") || e.contains("network")) {
            return getString(R.string.pilot_unreachable);
        }
        if (e.startsWith("http ")) {
            return getString(R.string.error_generic) + " (" + error + ")";
        }
        return getString(R.string.error_generic) + "\n" + error;
    }

    private void scrollToEnd() {
        messageList.post(() -> {
            if (adapter.getItemCount() > 0) {
                messageList.smoothScrollToPosition(adapter.getItemCount() - 1);
            }
        });
    }

    private void toggleVoice() {
        if (listening) {
            stopListening();
            return;
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            Toast.makeText(this, R.string.mic_unavailable, Toast.LENGTH_LONG).show();
            adapter.add(MessageAdapter.Message.agent(getString(R.string.mic_unavailable)));
            scrollToEnd();
            return;
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                    this, new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC);
            return;
        }
        startListening();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_MIC) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startListening();
            } else {
                Toast.makeText(this, R.string.mic_unavailable, Toast.LENGTH_LONG).show();
            }
        }
    }

    private void startListening() {
        try {
            if (speechRecognizer == null) {
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
                speechRecognizer.setRecognitionListener(new RecognitionListener() {
                    @Override public void onReadyForSpeech(Bundle params) {
                        listening = true;
                        announceStatus(getString(R.string.listening), true);
                        btnMic.setContentDescription(getString(R.string.stop_listening));
                        btnMic.setAlpha(0.5f);
                    }
                    @Override public void onBeginningOfSpeech() {}
                    @Override public void onRmsChanged(float rmsdB) {}
                    @Override public void onBufferReceived(byte[] buffer) {}
                    @Override public void onEndOfSpeech() {
                        listening = false;
                        btnMic.setAlpha(1f);
                        btnMic.setContentDescription(getString(R.string.voice));
                    }
                    @Override public void onError(int error) {
                        listening = false;
                        btnMic.setAlpha(1f);
                        announceStatus(statusOnline(), true);
                        String msg = getString(R.string.mic_unavailable);
                        Toast.makeText(ChatActivity.this, msg, Toast.LENGTH_SHORT).show();
                        if (pendingVoiceStart) {
                            pendingVoiceStart = false;
                            adapter.add(MessageAdapter.Message.agent(getString(R.string.mic_unavailable)));
                            scrollToEnd();
                        }
                    }
                    @Override
                    public void onResults(Bundle results) {
                        listening = false;
                        btnMic.setAlpha(1f);
                        announceStatus(statusOnline(), true);
                        ArrayList<String> texts =
                                results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                        if (texts != null && !texts.isEmpty()) {
                            String heard = texts.get(0);
                            input.setText(heard);
                            send(heard);
                        }
                    }
                    @Override public void onPartialResults(Bundle partialResults) {}
                    @Override public void onEvent(int eventType, Bundle params) {}
                });
            }
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
            speechRecognizer.startListening(intent);
        } catch (Exception e) {
            Toast.makeText(this, R.string.mic_unavailable, Toast.LENGTH_LONG).show();
            adapter.add(MessageAdapter.Message.agent(getString(R.string.mic_unavailable)));
            scrollToEnd();
        }
    }

    private void stopListening() {
        listening = false;
        btnMic.setAlpha(1f);
        btnMic.setContentDescription(getString(R.string.voice));
        try {
            if (speechRecognizer != null) speechRecognizer.stopListening();
        } catch (Exception ignored) {
        }
        announceStatus(statusOnline(), true);
    }

    @Override
    protected void onStop() {
        super.onStop();
        if (replay != null) replay.stop();
    }

    @Override
    protected void onDestroy() {
        if (replay != null) replay.cancel();
        if (speechRecognizer != null) {
            try {
                speechRecognizer.destroy();
            } catch (Exception ignored) {
            }
            speechRecognizer = null;
        }
        super.onDestroy();
    }
}
