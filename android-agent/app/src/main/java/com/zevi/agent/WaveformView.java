package com.zevi.agent;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.View;

import androidx.annotation.Nullable;
import androidx.core.content.ContextCompat;

/**
 * Simple animated bars for live session (visual only — no phone TTS playback).
 */
public class WaveformView extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final float[] levels = new float[16];
    private boolean animating;
    private int mode; // 0 idle, 1 listen, 2 speak
    private long start;

    public WaveformView(Context context) {
        super(context);
        init();
    }

    public WaveformView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    private void init() {
        paint.setColor(ContextCompat.getColor(getContext(), R.color.zevi_accent));
        paint.setStrokeCap(Paint.Cap.ROUND);
        for (int i = 0; i < levels.length; i++) levels[i] = 0.15f;
        start = System.currentTimeMillis();
    }

    public void setMode(int mode) {
        this.mode = mode;
        animating = mode != 0;
        paint.setColor(ContextCompat.getColor(getContext(),
                mode == 2 ? R.color.zevi_green : R.color.zevi_accent));
        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float w = getWidth();
        float h = getHeight();
        float gap = w / (levels.length + 1f);
        float t = (System.currentTimeMillis() - start) / 1000f;
        for (int i = 0; i < levels.length; i++) {
            float target;
            if (mode == 0) {
                target = 0.12f;
            } else {
                target = 0.25f + 0.55f * Math.abs((float) Math.sin(t * (mode == 2 ? 6 : 4) + i * 0.55));
            }
            levels[i] += (target - levels[i]) * 0.25f;
            float barH = Math.max(8f, levels[i] * h * 0.85f);
            float cx = gap * (i + 1);
            canvas.drawRoundRect(cx - 4, (h - barH) / 2f, cx + 4, (h + barH) / 2f, 4, 4, paint);
        }
        if (animating || mode == 0) {
            postInvalidateOnAnimation();
        }
    }
}
