package com.zevi.agent;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.provider.Settings;
import android.util.AttributeSet;
import android.view.View;
import android.view.animation.LinearInterpolator;

/** In-bezel Live presence orb. It uses transform-like scale/alpha drawing only. */
public class LiveOrbView extends View {
    public static final int IDLE = 0, LISTENING = 1, THINKING = 2, SPEAKING = 3, DOCKED = 4, PAUSED = 5;
    private final Paint core = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
    private int state = IDLE;
    private float level;
    private float breathe = 1f;
    private ValueAnimator animator;

    public LiveOrbView(Context c, AttributeSet a) { super(c, a); init(); }
    public LiveOrbView(Context c) { super(c); init(); }
    private void init() {
        ring.setStyle(Paint.Style.STROKE); ring.setStrokeWidth(dp(2));
        setLayerType(View.LAYER_TYPE_SOFTWARE, null);
        boolean reduced = Settings.Global.getFloat(getContext().getContentResolver(), Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f;
        if (!reduced) {
            animator = ValueAnimator.ofFloat(1f, 1.04f, 1f);
            animator.setDuration(2400); animator.setRepeatCount(ValueAnimator.INFINITE); animator.setInterpolator(new LinearInterpolator());
            animator.addUpdateListener(v -> { breathe = (Float) v.getAnimatedValue(); invalidate(); }); animator.start();
        }
    }
    public void setState(int value) { state = value; invalidate(); }
    public void setLevel(float value) { level = Math.max(0f, Math.min(1f, value)); invalidate(); }
    @Override protected void onDraw(Canvas c) {
        super.onDraw(c); float cx=getWidth()/2f, cy=getHeight()/2f, base=Math.min(getWidth(),getHeight())*.38f;
        float scale = state == DOCKED ? .30f : (state == THINKING ? .75f : 1f) * breathe;
        c.save(); c.scale(scale, scale, cx, cy);
        core.setShader(new RadialGradient(cx-base*.3f, cy-base*.35f, base*1.8f, new int[]{0xff7fa3ff,0xff5b8cff,0xff7c6bff}, null, Shader.TileMode.CLAMP));
        core.setShadowLayer(dp(20), 0, 0, 0x665b8cff); c.drawCircle(cx,cy,base,core); core.clearShadowLayer();
        ring.setColor(state == LISTENING ? 0xfff5f1e8 : 0xff5b8cff); ring.setAlpha(state == PAUSED ? 120 : 235);
        float ringScale = 1f + level*.18f + (state == SPEAKING ? .08f : 0f); c.save(); c.scale(ringScale,ringScale,cx,cy); c.drawCircle(cx,cy,base+dp(5),ring); c.restore();
        c.restore();
    }
    private float dp(float v) { return v * getResources().getDisplayMetrics().density; }
    @Override protected void onDetachedFromWindow() { if (animator != null) animator.cancel(); super.onDetachedFromWindow(); }
}
