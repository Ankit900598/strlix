package com.zevi.agent;

import android.app.Activity;
import android.app.role.RoleManager;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * Feature-gated inspection seam for Android ROLE_ASSISTANT.
 *
 * The hook never requests a role by itself. In this build it is disabled, and
 * no manifest component qualifies as a VoiceInteractionService or ACTION_ASSIST
 * handler. A future UI must obtain explicit user consent and verify the result
 * plus RoleManager.isRoleHeld() before describing the role as granted.
 */
public final class AssistantRoleHook {
    public enum Status {
        DISABLED,
        UNSUPPORTED,
        UNAVAILABLE,
        AVAILABLE_NOT_HELD,
        HELD
    }

    private AssistantRoleHook() {}

    public static Status status(Context context) {
        if (!BuildConfig.ASSISTANT_ROLE_HOOKS_ENABLED) return Status.DISABLED;
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return Status.UNSUPPORTED;
        if (context == null) return Status.UNAVAILABLE;

        RoleManager roles = context.getSystemService(RoleManager.class);
        if (roles == null || !roles.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) {
            return Status.UNAVAILABLE;
        }
        return roles.isRoleHeld(RoleManager.ROLE_ASSISTANT)
                ? Status.HELD
                : Status.AVAILABLE_NOT_HELD;
    }

    /**
     * Builds, but does not launch, Android's user-consent activity. Returns
     * null while the hook is disabled or the role is unavailable.
     */
    public static Intent createUserConsentIntent(Context context) {
        if (!BuildConfig.ASSISTANT_ROLE_HOOKS_ENABLED
                || Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
                || context == null) {
            return null;
        }
        RoleManager roles = context.getSystemService(RoleManager.class);
        if (roles == null || !roles.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) {
            return null;
        }
        return roles.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT);
    }

    /**
     * Defensive result check for a future Activity Result callback. RESULT_OK
     * alone is not treated as proof; the caller should also call status().
     */
    public static boolean isConfirmed(Context context, int resultCode) {
        return resultCode == Activity.RESULT_OK && status(context) == Status.HELD;
    }
}
