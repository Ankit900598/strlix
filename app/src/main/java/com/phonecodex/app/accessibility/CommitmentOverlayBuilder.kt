package com.phonecodex.app.accessibility

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.phonecodex.app.domain.model.DecisionType

/**
 * View-based WindowManager overlay for WARN / BLOCK / LOCK.
 * Product voice: "You promised this. I’m helping you keep it."
 * Technical metadata stays out of this surface (Decision Inspector only).
 */
object CommitmentOverlayCopy {

    fun overlayKind(decision: String): OverlayKind {
        return when (decision.uppercase()) {
            DecisionType.WARN.name, DecisionType.ASK.name -> OverlayKind.WARN
            DecisionType.LOCK.name -> OverlayKind.LOCK
            else -> OverlayKind.BLOCK
        }
    }

    fun decisionBadge(kind: OverlayKind): String = when (kind) {
        OverlayKind.WARN -> "WARN"
        OverlayKind.BLOCK -> "BLOCK"
        OverlayKind.LOCK -> "LOCK"
    }

    fun headline(kind: OverlayKind): String = when (kind) {
        OverlayKind.WARN -> "Stay on promise"
        OverlayKind.BLOCK -> "This steps away from your promise"
        OverlayKind.LOCK -> "Your commitment is locked"
    }

    fun companionLine(kind: OverlayKind): String = when (kind) {
        OverlayKind.WARN -> "You promised this. I’m helping you keep it."
        OverlayKind.BLOCK -> "You promised this. I’m helping you keep it."
        OverlayKind.LOCK ->
            "Lock is active because of repeated attempts or a strict commitment. " +
                "There is no quick bypass here."
    }

    fun shortReason(decision: String, reason: String): String {
        val cleaned = reason.trim()
        if (cleaned.isNotEmpty()) return cleaned
        return when (overlayKind(decision)) {
            OverlayKind.LOCK, OverlayKind.BLOCK ->
                "This doesn’t match your current commitment."
            OverlayKind.WARN ->
                "This might pull you off your commitment."
        }
    }

    fun attemptLabel(attemptCount: Int?): String? {
        if (attemptCount == null || attemptCount <= 0) return null
        return if (attemptCount == 1) {
            "1 drift so far"
        } else {
            "$attemptCount drifts so far"
        }
    }

    fun remainingLabel(kind: OverlayKind, remainingMillis: Long?): String? {
        if (remainingMillis == null) return null
        val formatted = formatRemaining(remainingMillis) ?: return null
        return when (kind) {
            OverlayKind.LOCK -> "Lock holds · $formatted"
            else -> formatted
        }
    }

    fun formatRemaining(remainingMillis: Long): String? {
        if (remainingMillis <= 0L) return null
        val totalMinutes = (remainingMillis / 60_000L).toInt()
        val hours = totalMinutes / 60
        val minutes = totalMinutes % 60
        return when {
            hours > 0 -> "${hours}h ${minutes}m left"
            totalMinutes > 0 -> "${totalMinutes}m left"
            else -> "Under a minute left"
        }
    }
}

enum class OverlayKind {
    WARN,
    BLOCK,
    LOCK
}

data class CommitmentOverlayModel(
    val kind: OverlayKind,
    val reason: String,
    val promiseGoal: String? = null,
    val attemptCount: Int? = null,
    val remainingMillis: Long? = null
)

data class CommitmentOverlayActions(
    val onBackToSafe: () -> Unit,
    val onGoBack: (() -> Unit)? = null,
    val onOpenPhoneCodex: (() -> Unit)? = null,
    val onContinue: (() -> Unit)? = null
)

class CommitmentOverlayBuilder(private val context: Context) {

    fun build(model: CommitmentOverlayModel, actions: CommitmentOverlayActions): View {
        val density = context.resources.displayMetrics.density
        val dp: (Int) -> Int = { value -> (value * density).toInt() }

        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Palette.SCRIM)
            setPadding(dp(24), dp(48), dp(24), dp(48))
            gravity = Gravity.CENTER
            isClickable = true
            isFocusable = true
        }

        val card = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = roundedRect(Palette.CARD, dp(20).toFloat())
            setPadding(dp(28), dp(28), dp(28), dp(28))
            elevation = 8f * density
        }

        val badge = TextView(context).apply {
            text = CommitmentOverlayCopy.decisionBadge(model.kind)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 12f)
            setTextColor(badgeTextColor(model.kind))
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            letterSpacing = 0.08f
            background = roundedRect(badgeFill(model.kind), dp(999).toFloat())
            setPadding(dp(12), dp(6), dp(12), dp(6))
            gravity = Gravity.CENTER
        }
        val badgeWrap = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.START
            addView(badge)
        }

        val headline = TextView(context).apply {
            text = CommitmentOverlayCopy.headline(model.kind)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 24f)
            setTextColor(Palette.TEXT_PRIMARY)
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            setPadding(0, dp(18), 0, 0)
        }

        val companion = TextView(context).apply {
            text = CommitmentOverlayCopy.companionLine(model.kind)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
            setTextColor(Palette.TEXT_MUTED)
            setPadding(0, dp(10), 0, 0)
            setLineSpacing(0f, 1.25f)
        }

        val reason = TextView(context).apply {
            text = model.reason
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
            setTextColor(Palette.TEXT_PRIMARY)
            setPadding(0, dp(18), 0, 0)
            setLineSpacing(0f, 1.3f)
        }

        card.addView(badgeWrap)
        card.addView(headline)
        card.addView(companion)
        card.addView(reason)

        val goal = model.promiseGoal?.trim().orEmpty()
        if (goal.isNotEmpty()) {
            card.addView(metaLabel("Your promise", dp))
            card.addView(
                TextView(context).apply {
                    text = goal
                    setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
                    setTextColor(Palette.CLAY)
                    setPadding(0, dp(4), 0, 0)
                    setLineSpacing(0f, 1.25f)
                }
            )
        }

        val attempt = CommitmentOverlayCopy.attemptLabel(model.attemptCount)
        if (attempt != null) {
            card.addView(metaLabel(attempt, dp, top = 14))
        }

        val remaining = CommitmentOverlayCopy.remainingLabel(model.kind, model.remainingMillis)
        if (remaining != null) {
            card.addView(metaLabel(remaining, dp, top = if (attempt != null) 6 else 14))
        }

        card.addView(spacer(dp(22)))

        when (model.kind) {
            OverlayKind.WARN -> {
                card.addView(
                    primaryButton("Stay on promise", actions.onBackToSafe, dp)
                )
                actions.onGoBack?.let { goBack ->
                    card.addView(spacer(dp(10)))
                    card.addView(secondaryButton("Go Back", goBack, dp))
                }
                actions.onContinue?.let { continueAction ->
                    card.addView(spacer(dp(10)))
                    card.addView(quietButton("Continue", continueAction, dp))
                }
            }
            OverlayKind.BLOCK -> {
                card.addView(
                    primaryButton("Back to safe screen", actions.onBackToSafe, dp)
                )
                actions.onOpenPhoneCodex?.let { openApp ->
                    card.addView(spacer(dp(10)))
                    card.addView(secondaryButton("Open PhoneCodex", openApp, dp))
                }
            }
            OverlayKind.LOCK -> {
                card.addView(
                    primaryButton("Back to safe screen", actions.onBackToSafe, dp)
                )
                actions.onOpenPhoneCodex?.let { openApp ->
                    card.addView(spacer(dp(10)))
                    card.addView(secondaryButton("Open PhoneCodex", openApp, dp))
                }
            }
        }

        val scroll = ScrollView(context).apply {
            isFillViewport = true
            addView(
                LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    gravity = Gravity.CENTER
                    addView(
                        card,
                        LinearLayout.LayoutParams(
                            LinearLayout.LayoutParams.MATCH_PARENT,
                            LinearLayout.LayoutParams.WRAP_CONTENT
                        )
                    )
                }
            )
        }

        root.addView(
            scroll,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        )
        return root
    }

    private fun metaLabel(
        text: String,
        dp: (Int) -> Int,
        top: Int = 16
    ): TextView {
        return TextView(context).apply {
            this.text = text
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f)
            setTextColor(Palette.TEXT_MUTED)
            setPadding(0, dp(top), 0, 0)
        }
    }

    private fun spacer(heightPx: Int): View {
        return View(context).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                heightPx
            )
        }
    }

    private fun primaryButton(label: String, onClick: () -> Unit, dp: (Int) -> Int): Button {
        return Button(context).apply {
            text = label
            isAllCaps = false
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
            setTextColor(Palette.ON_CLAY)
            background = roundedRect(Palette.CLAY, dp(14).toFloat())
            setPadding(dp(16), dp(14), dp(16), dp(14))
            setOnClickListener { onClick() }
        }
    }

    private fun secondaryButton(label: String, onClick: () -> Unit, dp: (Int) -> Int): Button {
        return Button(context).apply {
            text = label
            isAllCaps = false
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
            setTextColor(Palette.TEXT_PRIMARY)
            background = roundedRect(Palette.SURFACE_RAISED, dp(14).toFloat(), Palette.OUTLINE)
            setPadding(dp(16), dp(12), dp(16), dp(12))
            setOnClickListener { onClick() }
        }
    }

    private fun quietButton(label: String, onClick: () -> Unit, dp: (Int) -> Int): Button {
        return Button(context).apply {
            text = label
            isAllCaps = false
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
            setTextColor(Palette.TEXT_MUTED)
            background = roundedRect(Color.TRANSPARENT, dp(14).toFloat())
            setPadding(dp(16), dp(10), dp(16), dp(10))
            setOnClickListener { onClick() }
        }
    }

    private fun badgeFill(kind: OverlayKind): Int = when (kind) {
        OverlayKind.WARN -> Palette.CLAY_SOFT
        OverlayKind.BLOCK -> Palette.SURFACE_RAISED
        OverlayKind.LOCK -> Palette.EMBER_SOFT
    }

    private fun badgeTextColor(kind: OverlayKind): Int = when (kind) {
        OverlayKind.WARN -> Palette.CLAY
        OverlayKind.BLOCK -> Palette.TEXT_PRIMARY
        OverlayKind.LOCK -> Palette.EMBER
    }

    private fun roundedRect(
        fill: Int,
        radiusPx: Float,
        stroke: Int? = null
    ): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = radiusPx
            setColor(fill)
            if (stroke != null) {
                setStroke((1.5f * context.resources.displayMetrics.density).toInt(), stroke)
            }
        }
    }

    /** Soft dark / warm clay tokens mirrored from Compose theme (View overlay). */
    private object Palette {
        val SCRIM = Color.parseColor("#F20C0C10")
        val CARD = Color.parseColor("#FF15151B")
        val SURFACE_RAISED = Color.parseColor("#FF1D1D25")
        val OUTLINE = Color.parseColor("#FF2B2B35")
        val TEXT_PRIMARY = Color.parseColor("#FFEDEAE3")
        val TEXT_MUTED = Color.parseColor("#FF9A968D")
        val CLAY = Color.parseColor("#FFD9825C")
        val CLAY_SOFT = Color.parseColor("#FF3A2016")
        val ON_CLAY = Color.parseColor("#FF2A140A")
        val EMBER = Color.parseColor("#FFE0685C")
        val EMBER_SOFT = Color.parseColor("#FF331614")
    }
}
