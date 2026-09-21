package com.zevi.agent;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.android.material.button.MaterialButton;

import java.util.ArrayList;
import java.util.Locale;

/** Phone Live presence surface. Transcript stays hidden; speech is a one-line caption. */
public class LiveActivity extends AppCompatActivity {
    private static final int REQ_MIC = 7201;
    private PilotClient pilot;
    private LiveOrbView orb;
    private TextView caption;
    private MaterialButton btnMute;
    private MaterialButton btnShare;
    private ReplaySession replay;
    private SpeechRecognizer speechRecognizer;
    private String liveLanguage;
    private boolean listening, busy, speakingCue, muted;

    private void setCaption(int textRes) {
        setCaption(getString(textRes));
    }

    private void setCaption(CharSequence text) {
        if (caption == null) return;
        caption.setText(text);
        caption.setContentDescription(getString(R.string.live_caption_description) + ". " + text);
        caption.sendAccessibilityEvent(
                android.view.accessibility.AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED);
    }

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState); setContentView(R.layout.activity_live);
        pilot = new PilotClient(); replay = new ReplaySession(pilot); liveLanguage = LangPrefs.get(this);
        orb = findViewById(R.id.liveOrb); caption = findViewById(R.id.liveCaption); btnMute = findViewById(R.id.btnMute);
        btnShare = findViewById(R.id.btnShare);
        btnMute.setContentDescription(getString(R.string.live_mute_description));
        btnShare.setOnClickListener(v -> {
            v.setEnabled(false);
            Toast.makeText(this, R.string.replay_exporting, Toast.LENGTH_SHORT).show();
            replay.share(this, "Strlix Live replay", (ok, detail) -> v.setEnabled(true));
        });
        orb.setState(LiveOrbView.IDLE);
        findViewById(R.id.btnStop).setOnClickListener(v -> leave());
        findViewById(R.id.btnKeyboard).setOnClickListener(v -> { startActivity(new Intent(this, ChatActivity.class)); });
        btnMute.setOnClickListener(v -> toggleMute());
        pilot.setLiveState(true, "phone", liveLanguage, (ok, detail) -> { if (!ok) setCaption(R.string.status_offline); });
        pilot.health((ok, detail, url) -> { if (!ok) setCaption(R.string.pilot_unreachable); });
    }

    private void leave() { stopListening(); replay.cancel(); pilot.setLiveState(false, "phone", liveLanguage, (ok, detail) -> {}); finish(); }
    @Override public void onBackPressed() { leave(); }

    private void toggleMute() {
        muted = !muted;
        btnMute.setText(muted ? "🔈" : "🔇");
        btnMute.setContentDescription(getString(muted
                ? R.string.live_unmute_description : R.string.live_mute_description));
        btnMute.sendAccessibilityEvent(
                android.view.accessibility.AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED);
        if (muted) { stopListening(); orb.setState(LiveOrbView.PAUSED); setCaption(R.string.live_mic_off); }
        else { orb.setState(LiveOrbView.IDLE); setCaption(R.string.live_caption_idle); startListening(); }
    }

    private void toggleMic() {
        if (muted) return;
        if (speakingCue) { speakingCue = false; orb.setState(LiveOrbView.LISTENING); pilot.barge("phone", "talk", (ok, detail) -> {}); busy = false; }
        if (busy) return;
        if (listening) { stopListening(); return; }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) { setCaption(R.string.live_mic_fallback); return; }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC); return;
        }
        startListening();
    }
    @Override public void onRequestPermissionsResult(int code, @NonNull String[] p, @NonNull int[] grants) {
        super.onRequestPermissionsResult(code, p, grants); if (code == REQ_MIC && grants.length > 0 && grants[0] == PackageManager.PERMISSION_GRANTED) startListening();
    }

    private void startListening() {
        try {
            if (speechRecognizer == null) {
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
                speechRecognizer.setRecognitionListener(new RecognitionListener() {
                    @Override public void onReadyForSpeech(Bundle b) { listening=true; orb.setState(LiveOrbView.LISTENING); setCaption(R.string.listening); }
                    @Override public void onBeginningOfSpeech() { if (speakingCue) { speakingCue=false; pilot.barge("phone","speech",(ok,d)->{}); } }
                    @Override public void onRmsChanged(float rmsdB) { float level=Math.max(0f,Math.min(1f,(rmsdB+2f)/14f)); orb.setLevel(level); }
                    @Override public void onBufferReceived(byte[] b) {}
                    @Override public void onEndOfSpeech() { listening=false; }
                    @Override public void onError(int e) { listening=false; if(!busy)orb.setState(LiveOrbView.IDLE); setCaption(R.string.live_caption_idle); }
                    @Override public void onResults(Bundle results) { listening=false; ArrayList<String> texts=results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION); if(texts!=null&&!texts.isEmpty()) runTurn(texts.get(0)); else orb.setState(LiveOrbView.IDLE); }
                    @Override public void onPartialResults(Bundle partial) { ArrayList<String> texts=partial.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION); if(texts!=null&&!texts.isEmpty())setCaption(texts.get(0)); }
                    @Override public void onEvent(int t, Bundle b) {}
                });
            }
            Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH); i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM); i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,liveLanguage!=null?liveLanguage:Locale.getDefault().toLanguageTag()); i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,true); speechRecognizer.startListening(i);
        } catch (Exception e) { setCaption(R.string.live_mic_fallback); orb.setState(LiveOrbView.IDLE); }
    }
    private void stopListening() { listening=false; try { if(speechRecognizer!=null)speechRecognizer.stopListening(); }catch(Exception ignored){} if(!busy&&!speakingCue)orb.setState(LiveOrbView.IDLE); }

    private void runTurn(String message) {
        replay.start("Strlix Live replay");
        replay.addStep("Thinking…");
        btnShare.setVisibility(android.view.View.VISIBLE);
        busy=true; orb.setState(LiveOrbView.DOCKED); setCaption(R.string.status_thinking);
        pilot.voiceTurn(message,null,liveLanguage,new PilotClient.VoiceTurnCallback() {
            @Override public void onSuccess(String reply,String audioUrl,String provider,String rawJson) {
                busy=false; speakingCue=true; orb.setState(LiveOrbView.SPEAKING); setCaption(reply==null||reply.isEmpty()?getString(R.string.live_caption_idle):reply);
                replay.addStep(reply);
                // The host browser owns TTS. This cue stays dock-friendly and disappears when the turn settles.
                caption.postDelayed(() -> { replay.stop(); speakingCue=false; if(!listening)orb.setState(LiveOrbView.IDLE); },3500);
            }
            @Override public void onError(String error) { busy=false; replay.addStep("Couldn't complete the turn"); replay.stop(); speakingCue=false; orb.setState(LiveOrbView.IDLE); setCaption(R.string.status_offline); Toast.makeText(LiveActivity.this,error,Toast.LENGTH_SHORT).show(); }
        });
    }
    @Override protected void onStop() {
        super.onStop();
        if (replay != null) replay.stop();
    }
    @Override protected void onDestroy() { replay.cancel(); stopListening(); if(speechRecognizer!=null){try{speechRecognizer.destroy();}catch(Exception ignored){}speechRecognizer=null;} super.onDestroy(); }
}
