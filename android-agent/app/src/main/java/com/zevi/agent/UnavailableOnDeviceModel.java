package com.zevi.agent;

import java.util.List;

/**
 * Honest Pass P placeholder. There is no local model in this build.
 */
public final class UnavailableOnDeviceModel implements OnDeviceModel {
    private static final String DISABLED_REASON =
            "On-device model is disabled; using the configured Strlix chat path.";
    private static final String MISSING_REASON =
            "On-device model is enabled for development, but no model is installed.";

    @Override
    public Availability availability() {
        return BuildConfig.ON_DEVICE_MODEL_ENABLED
                ? Availability.MODEL_NOT_INSTALLED
                : Availability.DISABLED;
    }

    @Override
    public void generate(String prompt, List<Turn> history, Callback callback) {
        if (callback == null) return;
        callback.onUnavailable(BuildConfig.ON_DEVICE_MODEL_ENABLED
                ? MISSING_REASON
                : DISABLED_REASON);
    }

    @Override
    public void cancel() {
        // No work is started by this stub.
    }
}
