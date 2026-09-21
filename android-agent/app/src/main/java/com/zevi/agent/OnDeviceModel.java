package com.zevi.agent;

import java.util.Collections;
import java.util.List;

/**
 * Boundary for a future on-device language/vision model.
 *
 * This is deliberately only an interface: the current APK has no model bundled
 * and must not pretend that local inference happened. Implementations must
 * keep model output separate from privileged device actions; callers remain
 * responsible for confirmation and policy checks.
 */
public interface OnDeviceModel {
    enum Availability {
        DISABLED,
        MODEL_NOT_INSTALLED,
        READY
    }

    /** A model turn with no implicit access to screen, microphone, or files. */
    final class Turn {
        public final String role;
        public final String content;

        public Turn(String role, String content) {
            this.role = role == null ? "user" : role;
            this.content = content == null ? "" : content;
        }
    }

    interface Callback {
        void onSuccess(String text);
        void onUnavailable(String reason);
        void onError(String reason);
    }

    Availability availability();

    /**
     * Run one explicitly requested foreground turn. An implementation must not
     * start background work or silently upload the prompt.
     */
    void generate(String prompt, List<Turn> history, Callback callback);

    void cancel();

    static List<Turn> noHistory() {
        return Collections.emptyList();
    }
}
