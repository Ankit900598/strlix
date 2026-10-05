package com.zevi.agent;

import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;

/**
 * Talks to the host Strlix pilot. Azure keys never leave the host.
 * Probes adb-reverse → emulator gateway → public HTTPS fallback.
 */
public final class PilotClient {
    private static final String TAG = "StrlixPilot";
    public static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    public interface HealthCallback {
        void onResult(boolean ok, String detail, String baseUrl);
    }

    public interface ChatCallback {
        void onSuccess(String reply, String rawJson);
        void onError(String error);
    }

    private final OkHttpClient client;
    private final List<String> candidates;
    private final AtomicReference<String> activeBase = new AtomicReference<>(null);
    private final Handler main = new Handler(Looper.getMainLooper());

    public PilotClient() {
        // Azure HTTPS first (shipped default); localhost :8788/:8787 for emulator reverse.
        this(Arrays.asList(
                ApiConfig.publicUrl(),
                BuildConfig.ANDROID_API_URL,
                BuildConfig.ANDROID_API_EMULATOR_URL,
                BuildConfig.PILOT_BASE_URL,
                BuildConfig.PILOT_EMULATOR_URL
        ));
    }

    public PilotClient(String baseUrl) {
        this(Arrays.asList(
                baseUrl,
                ApiConfig.publicUrl(),
                BuildConfig.ANDROID_API_URL,
                BuildConfig.ANDROID_API_EMULATOR_URL,
                BuildConfig.PILOT_BASE_URL,
                BuildConfig.PILOT_EMULATOR_URL
        ));
    }

    public PilotClient(List<String> urls) {
        this.candidates = new ArrayList<>();
        for (String u : urls) {
            if (u == null || u.isEmpty()) continue;
            String n = u.endsWith("/") ? u.substring(0, u.length() - 1) : u;
            if (!candidates.contains(n)) candidates.add(n);
        }
        this.client = new OkHttpClient.Builder()
                .connectTimeout(8, TimeUnit.SECONDS)
                .readTimeout(180, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build();
    }

    public String getBaseUrl() {
        String a = activeBase.get();
        return a != null ? a : candidates.get(0);
    }

    public void health(HealthCallback cb) {
        probe(0, cb);
    }

    private void probe(int index, HealthCallback cb) {
        if (index >= candidates.size()) {
            main.post(() -> cb.onResult(false, "all endpoints unreachable", candidates.get(0)));
            return;
        }
        String base = candidates.get(index);
        Log.i(TAG, "health probe " + base);
        Request req = new Request.Builder().url(base + "/health").get().build();
        client.newCall(req).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                Log.w(TAG, "health fail " + base + ": " + e.getMessage());
                probe(index + 1, cb);
            }

            @Override
            public void onResponse(Call call, Response response) {
                try (ResponseBody body = response.body()) {
                    String text = body != null ? body.string() : "";
                    if (!response.isSuccessful()) {
                        Log.w(TAG, "health HTTP " + response.code() + " " + base);
                        probe(index + 1, cb);
                        return;
                    }
                    JSONObject j = new JSONObject(text);
                    boolean ok = j.optBoolean("ok", false);
                    String svc = j.optString("service", "");
                    String dep = j.optString("deployment", j.optString("model", "?"));
                    String adb = j.optString("adb_state", j.optString("note", ""));
                    if (ok) {
                        activeBase.set(base);
                        String detail = (svc.isEmpty() ? "" : svc + " · ") + dep
                                + (adb.isEmpty() ? "" : " · " + truncate(adb, 48));
                        Log.i(TAG, "health OK via " + base + " (" + detail + ")");
                        main.post(() -> cb.onResult(true, detail, base));
                    } else {
                        probe(index + 1, cb);
                    }
                } catch (Exception e) {
                    Log.w(TAG, "health parse " + base + ": " + e.getMessage());
                    probe(index + 1, cb);
                }
            }
        });
    }

    public void chat(String message, List<JSONObject> history, ChatCallback cb) {
        ensureBaseThen(() -> doChat(getBaseUrl(), message, history, cb), cb);
    }

    private void ensureBaseThen(Runnable okAction, ChatCallback cb) {
        if (activeBase.get() != null) {
            okAction.run();
            return;
        }
        health((ok, detail, url) -> {
            if (!ok) {
                cb.onError("unreachable: " + detail);
            } else {
                okAction.run();
            }
        });
    }

    private void doChat(String base, String message, List<JSONObject> history, ChatCallback cb) {
        try {
            JSONObject payload = new JSONObject();
            payload.put("message", message);
            if (history != null && !history.isEmpty()) {
                JSONArray arr = new JSONArray();
                for (JSONObject h : history) {
                    arr.put(h);
                }
                payload.put("history", arr);
            }
            RequestBody body = RequestBody.create(payload.toString(), JSON);
            String chatPath = chatPathFor(base);
            Request req = new Request.Builder()
                    .url(base + chatPath)
                    .post(body)
                    .build();
            Log.i(TAG, "chat → " + base + chatPath);
            client.newCall(req).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    Log.e(TAG, "chat fail: " + e.getMessage());
                    // retry once via next candidate
                    activeBase.set(null);
                    main.post(() -> cb.onError(e.getMessage() == null ? "network error" : e.getMessage()));
                }

                @Override
                public void onResponse(Call call, Response response) {
                    try (ResponseBody rb = response.body()) {
                        String text = rb != null ? rb.string() : "";
                        if (!response.isSuccessful()) {
                            main.post(() -> cb.onError("HTTP " + response.code() + ": " + truncate(text, 200)));
                            return;
                        }
                        JSONObject j = new JSONObject(text);
                        String reply = extractReply(j);
                        main.post(() -> cb.onSuccess(reply, text));
                    } catch (Exception e) {
                        main.post(() -> cb.onError(e.getMessage()));
                    }
                }
            });
        } catch (Exception e) {
            cb.onError(e.getMessage());
        }
    }

    /** android-api exposes /v1/chat (and /chat alias); pilot monolith uses /chat. */
    private static String chatPathFor(String base) {
        if (base == null) return "/chat";
        // android-api (local or Azure Container Apps) — /chat is an alias of /v1/chat
        if (base.contains(":8788") || base.contains("ca-android-api") || base.contains("azurecontainerapps.io")) {
            return "/v1/chat";
        }
        return "/chat";
    }

    private static String extractReply(JSONObject j) {
        if (j.has("reply")) return j.optString("reply");
        if (j.has("message")) return j.optString("message");
        if (j.has("content")) return j.optString("content");
        if (j.has("assistant")) return j.optString("assistant");
        if (j.has("final_answer")) return j.optString("final_answer");
        return j.toString();
    }

    private static String truncate(String s, int n) {
        if (s == null) return "";
        return s.length() <= n ? s : s.substring(0, n) + "…";
    }

    public interface VoiceTurnCallback {
        void onSuccess(String reply, String audioUrl, String provider, String rawJson);
        void onError(String error);
    }

    public interface SimpleCallback {
        void onDone(boolean ok, String detail);
    }

    public interface FrameCallback {
        void onSuccess(String base64);
        void onError(String error);
    }

    public interface ReplayGifCallback {
        void onSuccess(String gifUrl, int frameCount);
        void onError(String error);
    }

    public interface GifDownloadCallback {
        void onSuccess(byte[] bytes, String fileName);
        void onError(String error);
    }

    private final AtomicReference<Call> replayCall = new AtomicReference<>(null);

    /** Notify host live session state (browser clients sync via /ws/live). */
    public void setLiveState(boolean active, String source, SimpleCallback cb) {
        setLiveState(active, source, null, cb);
    }

    public void setLiveState(boolean active, String source, String language, SimpleCallback cb) {
        ensureBaseThen(() -> {
            try {
                JSONObject payload = new JSONObject();
                payload.put("active", active);
                if (source != null) payload.put("source", source);
                if (language != null) payload.put("language", language);
                RequestBody body = RequestBody.create(payload.toString(), JSON);
                Request req = new Request.Builder()
                        .url(getBaseUrl() + "/voice/live")
                        .post(body)
                        .build();
                client.newCall(req).enqueue(new Callback() {
                    @Override public void onFailure(Call call, IOException e) {
                        main.post(() -> cb.onDone(false, e.getMessage()));
                    }
                    @Override public void onResponse(Call call, Response response) {
                        try (ResponseBody rb = response.body()) {
                            String text = rb != null ? rb.string() : "";
                            main.post(() -> cb.onDone(response.isSuccessful(), text));
                        } catch (Exception e) {
                            main.post(() -> cb.onDone(false, e.getMessage()));
                        }
                    }
                });
            } catch (Exception e) {
                cb.onDone(false, e.getMessage());
            }
        }, new ChatCallback() {
            @Override public void onSuccess(String reply, String rawJson) {}
            @Override public void onError(String error) { cb.onDone(false, error); }
        });
    }

    /**
     * Live turn: host LLM + host TTS. Audio URL is for laptop browser playback —
     * do not play on the phone.
     */
    public void voiceTurn(String message, List<JSONObject> history, VoiceTurnCallback cb) {
        voiceTurn(message, history, null, cb);
    }

    public void voiceTurn(String message, List<JSONObject> history, String language, VoiceTurnCallback cb) {
        ensureBaseThen(() -> doVoiceTurn(getBaseUrl(), message, history, language, cb), new ChatCallback() {
            @Override public void onSuccess(String reply, String rawJson) {}
            @Override public void onError(String error) { cb.onError(error); }
        });
    }

    private void doVoiceTurn(String base, String message, List<JSONObject> history, String language,
                             VoiceTurnCallback cb) {
        try {
            JSONObject payload = new JSONObject();
            payload.put("message", message);
            payload.put("speak", true);
            payload.put("source", "phone");
            if (language != null) payload.put("language", language);
            if (history != null && !history.isEmpty()) {
                JSONArray arr = new JSONArray();
                for (JSONObject h : history) arr.put(h);
                payload.put("history", arr);
            }
            RequestBody body = RequestBody.create(payload.toString(), JSON);
            Request req = new Request.Builder()
                    .url(base + "/voice/turn")
                    .post(body)
                    .build();
            Log.i(TAG, "voiceTurn → " + base + " lang=" + language);
            client.newCall(req).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    main.post(() -> cb.onError(e.getMessage() == null ? "network error" : e.getMessage()));
                }
                @Override
                public void onResponse(Call call, Response response) {
                    try (ResponseBody rb = response.body()) {
                        String text = rb != null ? rb.string() : "";
                        if (!response.isSuccessful()) {
                            // Live voice is host/pilot-only; if android-api 404s, try next base.
                            if (response.code() == 404 || response.code() == 405) {
                                Log.w(TAG, "voiceTurn unsupported on " + base + " — falling back");
                                activeBase.set(null);
                                List<String> rest = new ArrayList<>();
                                for (String c : candidates) {
                                    if (!c.equals(base)) rest.add(c);
                                }
                                if (!rest.isEmpty()) {
                                    PilotClient fallback = new PilotClient(rest);
                                    fallback.voiceTurn(message, history, language, cb);
                                    return;
                                }
                            }
                            main.post(() -> cb.onError("HTTP " + response.code() + ": " + truncate(text, 200)));
                            return;
                        }
                        JSONObject j = new JSONObject(text);
                        String reply = extractReply(j);
                        String audioUrl = null;
                        String provider = null;
                        JSONObject audio = j.optJSONObject("audio");
                        if (audio != null) {
                            audioUrl = audio.optString("url", null);
                            if (audioUrl != null && audioUrl.isEmpty()) audioUrl = null;
                            provider = audio.optString("provider", null);
                        }
                        final String aUrl = audioUrl;
                        final String prov = provider;
                        main.post(() -> cb.onSuccess(reply, aUrl, prov, text));
                    } catch (Exception e) {
                        main.post(() -> cb.onError(e.getMessage()));
                    }
                }
            });
        } catch (Exception e) {
            cb.onError(e.getMessage());
        }
    }


    /** Tell laptop browsers to hard-stop TTS (barge-in). */
    public void barge(String source, String reason, SimpleCallback cb) {
        ensureBaseThen(() -> {
            try {
                JSONObject payload = new JSONObject();
                if (source != null) payload.put("source", source);
                if (reason != null) payload.put("reason", reason);
                RequestBody body = RequestBody.create(payload.toString(), JSON);
                // Prefer pilot :8787 for live barge; android-api may 404
                String base = getBaseUrl();
                Request req = new Request.Builder()
                        .url(base + "/voice/barge")
                        .post(body)
                        .build();
                client.newCall(req).enqueue(new Callback() {
                    @Override public void onFailure(Call call, IOException e) {
                        // Try pilot fallbacks
                        activeBase.set(null);
                        main.post(() -> cb.onDone(false, e.getMessage()));
                    }
                    @Override public void onResponse(Call call, Response response) {
                        try (ResponseBody rb = response.body()) {
                            String text = rb != null ? rb.string() : "";
                            if (response.code() == 404) {
                                activeBase.set(null);
                                // retry via next candidate once
                                List<String> rest = new ArrayList<>();
                                for (String c : candidates) if (!c.equals(base)) rest.add(c);
                                if (!rest.isEmpty()) {
                                    new PilotClient(rest).barge(source, reason, cb);
                                    return;
                                }
                            }
                            main.post(() -> cb.onDone(response.isSuccessful(), text));
                        } catch (Exception e) {
                            main.post(() -> cb.onDone(false, e.getMessage()));
                        }
                    }
                });
            } catch (Exception e) {
                cb.onDone(false, e.getMessage());
            }
        }, new ChatCallback() {
            @Override public void onSuccess(String reply, String rawJson) {}
            @Override public void onError(String error) { cb.onDone(false, error); }
        });
    }


    /** Capture a compact JPEG of the host phone for Replay GIF export. */
    public void captureFrame(FrameCallback cb) {
        ensureBaseThen(() -> captureFrameAt(getBaseUrl(), candidateIndex(getBaseUrl()), cb),
                new ChatCallback() {
                    @Override public void onSuccess(String reply, String rawJson) {}
                    @Override public void onError(String error) { cb.onError(error); }
                });
    }

    private void captureFrameAt(String base, int index, FrameCallback cb) {
        Request req = new Request.Builder()
                .url(base + "/adb/preview.json?quality=50&max_width=360")
                .get().build();
        client.newCall(req).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {
                if (nextCandidate(index) != null) {
                    captureFrameAt(nextCandidate(index), index + 1, cb);
                    return;
                }
                main.post(() -> cb.onError(e.getMessage() == null ? "network error" : e.getMessage()));
            }

            @Override public void onResponse(Call call, Response response) {
                try (ResponseBody body = response.body()) {
                    String text = body == null ? "" : body.string();
                    if ((response.code() == 404 || response.code() == 405)
                            && nextCandidate(index) != null) {
                        captureFrameAt(nextCandidate(index), index + 1, cb);
                        return;
                    }
                    if (!response.isSuccessful()) {
                        main.post(() -> cb.onError(errorFrom(text, "HTTP " + response.code())));
                        return;
                    }
                    JSONObject json = new JSONObject(text);
                    String base64 = json.optString("base64", "");
                    if (!json.optBoolean("ok", false) || base64.isEmpty()) {
                        main.post(() -> cb.onError("host returned no replay frame"));
                        return;
                    }
                    main.post(() -> cb.onSuccess(base64));
                } catch (Exception e) {
                    main.post(() -> cb.onError(e.getMessage() == null ? "bad replay frame" : e.getMessage()));
                }
            }
        });
    }

    /** Export frames through the pilot GIF endpoint without changing the active chat base. */
    public void replayGif(String title, List<String> steps, List<String> frames,
                          int durationMs, ReplayGifCallback cb) {
        ensureBaseThen(() -> replayGifAt(getBaseUrl(), candidateIndex(getBaseUrl()),
                        title, steps, frames, durationMs, cb),
                new ChatCallback() {
                    @Override public void onSuccess(String reply, String rawJson) {}
                    @Override public void onError(String error) { cb.onError(error); }
                });
    }

    private void replayGifAt(String base, int index, String title, List<String> steps,
                             List<String> frames, int durationMs, ReplayGifCallback cb) {
        try {
            JSONObject payload = new JSONObject();
            payload.put("title", title == null ? "Strlix replay" : title);
            payload.put("duration_ms", durationMs);
            JSONArray frameArray = new JSONArray();
            if (frames != null) for (String frame : frames) frameArray.put(frame);
            payload.put("frames", frameArray);
            JSONArray stepArray = new JSONArray();
            if (steps != null) for (String step : steps) stepArray.put(step);
            payload.put("steps", stepArray);
            RequestBody requestBody = RequestBody.create(payload.toString(), JSON);
            Request req = new Request.Builder().url(base + "/replay/gif").post(requestBody).build();
            Call call = client.newCall(req);
            replayCall.set(call);
            call.enqueue(new Callback() {
                @Override public void onFailure(Call call, IOException e) {
                    replayCall.compareAndSet(call, null);
                    if (nextCandidate(index) != null) {
                        replayGifAt(nextCandidate(index), index + 1, title, steps, frames,
                                durationMs, cb);
                        return;
                    }
                    main.post(() -> cb.onError(e.getMessage() == null ? "network error" : e.getMessage()));
                }

                @Override public void onResponse(Call call, Response response) {
                    try (ResponseBody body = response.body()) {
                        String text = body == null ? "" : body.string();
                        replayCall.compareAndSet(call, null);
                        if ((response.code() == 404 || response.code() == 405)
                                && nextCandidate(index) != null) {
                            replayGifAt(nextCandidate(index), index + 1, title, steps, frames,
                                    durationMs, cb);
                            return;
                        }
                        if (!response.isSuccessful()) {
                            main.post(() -> cb.onError(errorFrom(text, "HTTP " + response.code())));
                            return;
                        }
                        JSONObject json = new JSONObject(text);
                        String gif = json.optString("gif", "");
                        if (!json.optBoolean("ok", false) || gif.isEmpty()) {
                            main.post(() -> cb.onError("replay export returned no GIF"));
                            return;
                        }
                        int count = json.optInt("frame_count", frames == null ? 0 : frames.size());
                        String resolved = resolveUrl(base, gif);
                        main.post(() -> cb.onSuccess(resolved, count));
                    } catch (Exception e) {
                        main.post(() -> cb.onError(e.getMessage() == null ? "bad replay export" : e.getMessage()));
                    }
                }
            });
        } catch (Exception e) {
            cb.onError(e.getMessage() == null ? "replay export failed" : e.getMessage());
        }
    }

    /** Download the exported GIF into the app cache before granting a content URI. */
    public void downloadGif(String url, GifDownloadCallback cb) {
        try {
            Request req = new Request.Builder().url(url).get().build();
            Call call = client.newCall(req);
            replayCall.set(call);
            call.enqueue(new Callback() {
                @Override public void onFailure(Call call, IOException e) {
                    replayCall.compareAndSet(call, null);
                    main.post(() -> cb.onError(e.getMessage() == null ? "network error" : e.getMessage()));
                }

                @Override public void onResponse(Call call, Response response) {
                    try (ResponseBody body = response.body()) {
                        byte[] bytes = body == null ? new byte[0] : body.bytes();
                        replayCall.compareAndSet(call, null);
                        if (!response.isSuccessful() || bytes.length == 0) {
                            main.post(() -> cb.onError("GIF download failed: HTTP " + response.code()));
                            return;
                        }
                        String path = response.request().url().encodedPath();
                        String name = path.substring(path.lastIndexOf('/') + 1);
                        main.post(() -> cb.onSuccess(bytes, name));
                    } catch (Exception e) {
                        main.post(() -> cb.onError(e.getMessage() == null ? "GIF download failed" : e.getMessage()));
                    }
                }
            });
        } catch (Exception e) {
            cb.onError(e.getMessage() == null ? "GIF download failed" : e.getMessage());
        }
    }

    public void cancelReplay() {
        Call call = replayCall.getAndSet(null);
        if (call != null) call.cancel();
    }

    private int candidateIndex(String base) {
        int i = candidates.indexOf(base);
        return i < 0 ? 0 : i;
    }

    private String nextCandidate(int index) {
        int next = index + 1;
        return next < candidates.size() ? candidates.get(next) : null;
    }

    private static String resolveUrl(String base, String path) {
        if (path.startsWith("http://") || path.startsWith("https://")) return path;
        return base + (path.startsWith("/") ? path : "/" + path);
    }

    private static String errorFrom(String body, String fallback) {
        try {
            JSONObject json = new JSONObject(body == null ? "{}" : body);
            String detail = json.optString("detail", "");
            if (!detail.isEmpty()) return detail;
        } catch (Exception ignored) {
        }
        return fallback;
    }

}
