package com.zevi.agent;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Intent;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/** Captures a bounded host-phone replay and hands the resulting GIF to Android's share sheet. */
public final class ReplaySession {
    private static final long CAPTURE_INTERVAL_MS = 700L;
    private static final int MAX_FRAMES = 24;
    private static final int MAX_STEPS = 36;

    public interface ShareCallback {
        void onFinished(boolean ok, String detail);
    }

    private final PilotClient pilot;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final List<String> frames = new ArrayList<>();
    private final List<String> steps = new ArrayList<>();
    private final Runnable captureLoop = this::captureNext;
    private boolean capturing;
    private boolean captureInFlight;
    private boolean exporting;
    private boolean cancelled;
    private String title = "Strlix replay";
    private PendingShare pendingShare;

    private static final class PendingShare {
        final Activity activity;
        final String title;
        final ShareCallback callback;

        PendingShare(Activity activity, String title, ShareCallback callback) {
            this.activity = activity;
            this.title = title;
            this.callback = callback;
        }
    }

    public ReplaySession(PilotClient pilot) {
        this.pilot = pilot;
    }

    public void start(String title) {
        cancelled = false;
        exporting = false;
        pendingShare = null;
        this.title = title == null || title.trim().isEmpty() ? "Strlix replay" : title;
        main.removeCallbacks(captureLoop);
        frames.clear();
        steps.clear();
        capturing = true;
        addStep("Started");
        captureNow("Started");
        main.postDelayed(captureLoop, CAPTURE_INTERVAL_MS);
    }

    public void addStep(String line) {
        if (line == null) return;
        String clean = line.trim();
        if (clean.isEmpty()) return;
        if (clean.length() > 120) clean = clean.substring(0, 120) + "…";
        if (!steps.isEmpty() && steps.get(steps.size() - 1).equals(clean)) return;
        if (steps.size() >= MAX_STEPS) return;
        steps.add(clean);
    }

    public void stop() {
        capturing = false;
        main.removeCallbacks(captureLoop);
        if (!cancelled) captureNow("Done");
    }

    public boolean hasFrames() {
        return !frames.isEmpty();
    }

    public int frameCount() {
        return frames.size();
    }

    private void captureNext() {
        if (!capturing || cancelled) return;
        captureNow(null);
        main.postDelayed(captureLoop, CAPTURE_INTERVAL_MS);
    }

    private void captureNow(String caption) {
        if (cancelled || captureInFlight) return;
        captureInFlight = true;
        pilot.captureFrame(new PilotClient.FrameCallback() {
            @Override public void onSuccess(String base64) {
                captureInFlight = false;
                if (cancelled || base64 == null || base64.isEmpty()) return;
                if (frames.size() >= MAX_FRAMES) frames.remove(0);
                frames.add(base64);
                if (caption != null) addStep(caption);
                PendingShare pending = pendingShare;
                if (pending != null && !frames.isEmpty()) {
                    pendingShare = null;
                    export(pending.activity, pending.title, pending.callback);
                }
            }

            @Override public void onError(String error) {
                captureInFlight = false;
                PendingShare pending = pendingShare;
                if (pending != null && frames.isEmpty()) {
                    pendingShare = null;
                    exporting = false;
                    toast(pending.activity, friendlyError(error));
                    pending.callback.onFinished(false, error);
                }
            }
        });
    }

    public void share(Activity activity, String shareTitle, ShareCallback callback) {
        if (activity == null || cancelled || exporting) return;
        if (!hasFrames()) {
            exporting = true;
            pendingShare = new PendingShare(activity, shareTitle, callback);
            captureNow("Replay");
            main.postDelayed(() -> {
                if (pendingShare != null && frames.isEmpty() && !cancelled) {
                    PendingShare pending = pendingShare;
                    pendingShare = null;
                    exporting = false;
                    toast(pending.activity, friendlyError("no replay frames"));
                    pending.callback.onFinished(false, "no replay frames");
                }
            }, 2500L);
            return;
        }
        exporting = true;
        export(activity, shareTitle, callback);
    }

    private void export(Activity activity, String shareTitle, ShareCallback callback) {
        final String finalTitle = shareTitle == null || shareTitle.trim().isEmpty()
                ? title : shareTitle;
        final List<String> frameCopy = new ArrayList<>(frames);
        final List<String> stepCopy = new ArrayList<>(steps);
        pilot.replayGif(finalTitle, stepCopy, frameCopy, 450,
                new PilotClient.ReplayGifCallback() {
                    @Override public void onSuccess(String gifUrl, int frameCount) {
                        pilot.downloadGif(gifUrl, new PilotClient.GifDownloadCallback() {
                            @Override public void onSuccess(byte[] bytes, String fileName) {
                                writeAndShare(activity, finalTitle, bytes, fileName, frameCount, callback);
                            }

                            @Override public void onError(String error) {
                                finishFailure(activity, callback, error);
                            }
                        });
                    }

                    @Override public void onError(String error) {
                        finishFailure(activity, callback, error);
                    }
                });
    }

    private void writeAndShare(Activity activity, String shareTitle, byte[] bytes, String fileName,
                               int frameCount, ShareCallback callback) {
        if (cancelled || !isAlive(activity)) {
            exporting = false;
            callback.onFinished(false, "share cancelled");
            return;
        }
        new Thread(() -> {
            File out = null;
            String error = null;
            try {
                File dir = new File(activity.getCacheDir(), "replay");
                if (!dir.exists() && !dir.mkdirs()) throw new IOException("could not create replay cache");
                prune(dir);
                String safe = safeName(fileName);
                if (!safe.toLowerCase(Locale.ROOT).endsWith(".gif")) safe = "strlix-replay.gif";
                out = new File(dir, safe);
                try (FileOutputStream stream = new FileOutputStream(out)) {
                    stream.write(bytes);
                }
            } catch (Exception e) {
                error = e.getMessage() == null ? "could not save replay" : e.getMessage();
            }
            File result = out;
            String failure = error;
            main.post(() -> {
                if (failure != null || result == null || cancelled || !isAlive(activity)) {
                    finishFailure(activity, callback, failure == null ? "share cancelled" : failure);
                    return;
                }
                try {
                    Uri uri = FileProvider.getUriForFile(activity,
                            activity.getPackageName() + ".fileprovider", result);
                    Intent send = new Intent(Intent.ACTION_SEND)
                            .setType("image/gif")
                            .putExtra(Intent.EXTRA_STREAM, uri)
                            .putExtra(Intent.EXTRA_TITLE, shareTitle)
                            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    send.setClipData(ClipData.newRawUri("", uri));
                    Intent chooser = Intent.createChooser(send,
                            activity.getString(R.string.share_replay));
                    chooser.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    activity.startActivity(chooser);
                    exporting = false;
                    toast(activity, activity.getString(R.string.replay_ready, frameCount));
                    callback.onFinished(true, result.getName());
                } catch (ActivityNotFoundException e) {
                    finishFailure(activity, callback, "no share app available");
                } catch (IllegalArgumentException e) {
                    finishFailure(activity, callback, e.getMessage());
                }
            });
        }, "strlix-replay-share").start();
    }

    private void finishFailure(Activity activity, ShareCallback callback, String error) {
        exporting = false;
        if (!cancelled && isAlive(activity)) toast(activity, friendlyError(error));
        callback.onFinished(false, error);
    }

    public void cancel() {
        cancelled = true;
        capturing = false;
        pendingShare = null;
        main.removeCallbacks(captureLoop);
        pilot.cancelReplay();
    }

    private static boolean isAlive(Activity activity) {
        return activity != null && !activity.isFinishing() && !activity.isDestroyed();
    }

    private static String safeName(String name) {
        if (name == null || name.isEmpty()) return "strlix-replay.gif";
        String base = name.substring(name.lastIndexOf('/') + 1);
        return base.replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private static void prune(File dir) {
        File[] files = dir.listFiles();
        if (files == null || files.length <= 5) return;
        Arrays.sort(files, Comparator.comparingLong(File::lastModified).reversed());
        for (int i = 5; i < files.length; i++) files[i].delete();
    }

    private static String friendlyError(String error) {
        if (error == null || error.isEmpty()) return "Replay sharing isn't available right now.";
        String lower = error.toLowerCase(Locale.ROOT);
        if (lower.contains("unreachable") || lower.contains("connect") || lower.contains("network")) {
            return "Replay needs the host pilot. Check the connection and try again.";
        }
        if (lower.contains("pillow") || lower.contains("replay export")) {
            return "Replay export isn't ready on the host yet.";
        }
        return "Couldn't share this replay. Try again in a moment.";
    }

    private static void toast(Activity activity, String message) {
        if (isAlive(activity)) Toast.makeText(activity, message, Toast.LENGTH_SHORT).show();
    }
}
