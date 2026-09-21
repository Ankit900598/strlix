package com.zevi.agent;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.Intent;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Display;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * On-device UI control: click, swipe, type, scroll, launch apps, global actions.
 * Enable via Settings → Accessibility → Strlix Copilot (or adb secure settings on emulator).
 */
public class ZeviAccessibilityService extends AccessibilityService {
    private static final String TAG = "ZeviA11y";
    private static ZeviAccessibilityService instance;
    private final Handler main = new Handler(Looper.getMainLooper());

    public static ZeviAccessibilityService getInstance() {
        return instance;
    }

    public static boolean isRunning() {
        return instance != null;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // reserved for UI tree observation / future agent loop
    }

    @Override
    public void onInterrupt() {
        // no-op
    }

    @Override
    protected void onServiceConnected() {
        try { ZeviSearchWidget.refreshAll(this); } catch (Exception ignored) {}

        super.onServiceConnected();
        instance = this;
        Log.i(TAG, "Strlix Accessibility connected");
    }

    @Override
    public void onDestroy() {
        if (instance == this) instance = null;
        super.onDestroy();
    }

    // --- gestures ---

    public boolean tap(float x, float y) {
        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.StrokeDescription stroke =
                new GestureDescription.StrokeDescription(path, 0, 60);
        return dispatchGesture(
                new GestureDescription.Builder().addStroke(stroke).build(), null, null);
    }

    public boolean swipe(float x1, float y1, float x2, float y2, long durationMs) {
        Path path = new Path();
        path.moveTo(x1, y1);
        path.lineTo(x2, y2);
        GestureDescription.StrokeDescription stroke =
                new GestureDescription.StrokeDescription(path, 0, Math.max(120, durationMs));
        return dispatchGesture(
                new GestureDescription.Builder().addStroke(stroke).build(), null, null);
    }

    public boolean scrollDown() {
        int[] sz = screenSize();
        float midX = sz[0] / 2f;
        return swipe(midX, sz[1] * 0.72f, midX, sz[1] * 0.28f, 350);
    }

    public boolean scrollUp() {
        int[] sz = screenSize();
        float midX = sz[0] / 2f;
        return swipe(midX, sz[1] * 0.28f, midX, sz[1] * 0.72f, 350);
    }

    public boolean scrollForward() {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return scrollDown();
        try {
            return performScrollAction(root, AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                    || scrollDown();
        } finally {
            root.recycle();
        }
    }

    public boolean scrollBackward() {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return scrollUp();
        try {
            return performScrollAction(root, AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)
                    || scrollUp();
        } finally {
            root.recycle();
        }
    }

    private boolean performScrollAction(AccessibilityNodeInfo node, int action) {
        if (node == null) return false;
        if (node.isScrollable() && node.performAction(action)) return true;
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child == null) continue;
            try {
                if (performScrollAction(child, action)) return true;
            } finally {
                child.recycle();
            }
        }
        return false;
    }

    // --- node actions ---

    public boolean clickByText(String text) {
        if (text == null || text.trim().isEmpty()) return false;
        AccessibilityNodeInfo node = findNodeByText(text.trim(), true);
        if (node == null) return false;
        try {
            return clickNode(node);
        } finally {
            node.recycle();
        }
    }

    public boolean clickByViewId(String viewId) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return false;
        try {
            List<AccessibilityNodeInfo> nodes = root.findAccessibilityNodeInfosByViewId(viewId);
            if (nodes == null || nodes.isEmpty()) return false;
            try {
                return clickNode(nodes.get(0));
            } finally {
                for (AccessibilityNodeInfo n : nodes) n.recycle();
            }
        } finally {
            root.recycle();
        }
    }

    public boolean clickNode(AccessibilityNodeInfo node) {
        if (node == null) return false;
        AccessibilityNodeInfo clickable = node;
        while (clickable != null && !clickable.isClickable()) {
            AccessibilityNodeInfo parent = clickable.getParent();
            if (clickable != node) clickable.recycle();
            clickable = parent;
        }
        if (clickable != null && clickable.isClickable()) {
            boolean ok = clickable.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            if (clickable != node) clickable.recycle();
            if (ok) return true;
        } else if (clickable != null && clickable != node) {
            clickable.recycle();
        }
        // fallback: gesture tap on bounds center
        Rect r = new Rect();
        node.getBoundsInScreen(r);
        if (r.isEmpty()) return false;
        return tap(r.centerX(), r.centerY());
    }

    public boolean typeText(String text) {
        if (text == null) return false;
        AccessibilityNodeInfo focus = findFocusedEditable();
        if (focus == null) {
            focus = findFirstEditable();
        }
        if (focus == null) {
            Log.w(TAG, "typeText: no editable field");
            return false;
        }
        try {
            Bundle args = new Bundle();
            args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text);
            if (focus.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) {
                return true;
            }
            // fallback: focus + paste-like set
            focus.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
            return focus.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
        } finally {
            focus.recycle();
        }
    }

    public boolean longClickByText(String text) {
        AccessibilityNodeInfo node = findNodeByText(text, true);
        if (node == null) return false;
        try {
            AccessibilityNodeInfo target = node;
            while (target != null && !target.isLongClickable()) {
                AccessibilityNodeInfo p = target.getParent();
                if (target != node) target.recycle();
                target = p;
            }
            if (target != null) {
                boolean ok = target.performAction(AccessibilityNodeInfo.ACTION_LONG_CLICK);
                if (target != node) target.recycle();
                return ok;
            }
            return false;
        } finally {
            node.recycle();
        }
    }

    public AccessibilityNodeInfo findNodeByText(String text, boolean clickablePreferred) {
        String needle = text.toLowerCase(Locale.US);
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return null;
        try {
            List<AccessibilityNodeInfo> byText = root.findAccessibilityNodeInfosByText(text);
            AccessibilityNodeInfo best = pickBest(byText, needle, clickablePreferred);
            if (best != null) {
                // detach from list recycling — caller owns best; recycle others
                for (AccessibilityNodeInfo n : byText) {
                    if (n != best) n.recycle();
                }
                return best;
            }
            for (AccessibilityNodeInfo n : byText) n.recycle();

            // BFS fallback (partial / content-desc)
            ArrayDeque<AccessibilityNodeInfo> q = new ArrayDeque<>();
            q.add(AccessibilityNodeInfo.obtain(root));
            AccessibilityNodeInfo found = null;
            while (!q.isEmpty()) {
                AccessibilityNodeInfo n = q.removeFirst();
                CharSequence t = n.getText();
                CharSequence d = n.getContentDescription();
                String ts = t == null ? "" : t.toString().toLowerCase(Locale.US);
                String ds = d == null ? "" : d.toString().toLowerCase(Locale.US);
                boolean match = ts.contains(needle) || ds.contains(needle) || ts.equals(needle);
                if (match) {
                    if (!clickablePreferred || n.isClickable() || hasClickableAncestor(n)) {
                        found = AccessibilityNodeInfo.obtain(n);
                        n.recycle();
                        while (!q.isEmpty()) q.removeFirst().recycle();
                        break;
                    }
                }
                for (int i = 0; i < n.getChildCount(); i++) {
                    AccessibilityNodeInfo c = n.getChild(i);
                    if (c != null) q.add(c);
                }
                n.recycle();
            }
            return found;
        } finally {
            root.recycle();
        }
    }

    private static boolean hasClickableAncestor(AccessibilityNodeInfo node) {
        AccessibilityNodeInfo p = node.getParent();
        while (p != null) {
            if (p.isClickable()) {
                p.recycle();
                return true;
            }
            AccessibilityNodeInfo next = p.getParent();
            p.recycle();
            p = next;
        }
        return false;
    }

    private static AccessibilityNodeInfo pickBest(
            List<AccessibilityNodeInfo> nodes, String needle, boolean clickablePreferred) {
        if (nodes == null || nodes.isEmpty()) return null;
        AccessibilityNodeInfo exact = null;
        AccessibilityNodeInfo clickable = null;
        AccessibilityNodeInfo any = null;
        for (AccessibilityNodeInfo n : nodes) {
            CharSequence t = n.getText();
            String ts = t == null ? "" : t.toString().toLowerCase(Locale.US);
            if (any == null) any = n;
            if (clickablePreferred && n.isClickable() && clickable == null) clickable = n;
            if (ts.equals(needle)) {
                exact = n;
                break;
            }
        }
        AccessibilityNodeInfo best = exact != null ? exact : (clickable != null ? clickable : any);
        return best == null ? null : AccessibilityNodeInfo.obtain(best);
    }

    private AccessibilityNodeInfo findFocusedEditable() {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return null;
        try {
            AccessibilityNodeInfo focus = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
            if (focus != null && focus.isEditable()) return focus;
            if (focus != null) focus.recycle();
            return null;
        } finally {
            root.recycle();
        }
    }

    private AccessibilityNodeInfo findFirstEditable() {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return null;
        try {
            ArrayDeque<AccessibilityNodeInfo> q = new ArrayDeque<>();
            q.add(AccessibilityNodeInfo.obtain(root));
            while (!q.isEmpty()) {
                AccessibilityNodeInfo n = q.removeFirst();
                if (n.isEditable()) {
                    while (!q.isEmpty()) q.removeFirst().recycle();
                    return n;
                }
                for (int i = 0; i < n.getChildCount(); i++) {
                    AccessibilityNodeInfo c = n.getChild(i);
                    if (c != null) q.add(c);
                }
                n.recycle();
            }
            return null;
        } finally {
            root.recycle();
        }
    }

    /** Dump visible clickable labels (debug / agent). */
    public List<String> listVisibleTexts(int max) {
        List<String> out = new ArrayList<>();
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return out;
        try {
            ArrayDeque<AccessibilityNodeInfo> q = new ArrayDeque<>();
            q.add(AccessibilityNodeInfo.obtain(root));
            while (!q.isEmpty() && out.size() < max) {
                AccessibilityNodeInfo n = q.removeFirst();
                CharSequence t = n.getText();
                CharSequence d = n.getContentDescription();
                if (t != null && t.length() > 0) out.add(t.toString());
                else if (d != null && d.length() > 0) out.add(d.toString());
                for (int i = 0; i < n.getChildCount(); i++) {
                    AccessibilityNodeInfo c = n.getChild(i);
                    if (c != null) q.add(c);
                }
                n.recycle();
            }
            while (!q.isEmpty()) q.removeFirst().recycle();
        } finally {
            root.recycle();
        }
        return out;
    }

    // --- global ---

    public void performHome() {
        performGlobalAction(GLOBAL_ACTION_HOME);
    }

    public void performBack() {
        performGlobalAction(GLOBAL_ACTION_BACK);
    }

    public void performRecents() {
        performGlobalAction(GLOBAL_ACTION_RECENTS);
    }

    public void performNotifications() {
        performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS);
    }

    public boolean launchApp(String packageName) {
        Intent launch = getPackageManager().getLaunchIntentForPackage(packageName);
        if (launch == null) return false;
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(launch);
        return true;
    }

    public void runOnMain(Runnable r) {
        main.post(r);
    }

    public void runOnMainDelayed(Runnable r, long delayMs) {
        main.postDelayed(r, delayMs);
    }

    /** Run an on-device command after delay (chat finishes so target app is focused). */
    public void queueForegroundCommand(String command, long delayMs) {
        final String cmd = command;
        main.postDelayed(() -> {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            String pkg = root != null && root.getPackageName() != null
                    ? root.getPackageName().toString() : "?";
            if (root != null) root.recycle();
            Log.i(TAG, "queueForegroundCommand: " + cmd + " activePkg=" + pkg);
            String result = LocalActions.tryLocalCommand(this, cmd);
            Log.i(TAG, "queueForegroundCommand result: " + result);
            Intent i = new Intent(this, ChatActivity.class);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP
                    | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            i.putExtra("agent_result", result != null ? result : "Done");
            i.putExtra(ZeviSearchWidget.EXTRA_FROM_WIDGET, true);
            startActivity(i);
        }, delayMs);
    }


    private int[] screenSize() {
        try {
            Display d = getDisplay();
            if (d != null) {
                android.graphics.Point p = new android.graphics.Point();
                d.getRealSize(p);
                return new int[]{p.x, p.y};
            }
        } catch (Exception ignored) {
        }
        android.util.DisplayMetrics m = getResources().getDisplayMetrics();
        return new int[]{m.widthPixels, m.heightPixels};
    }
}
