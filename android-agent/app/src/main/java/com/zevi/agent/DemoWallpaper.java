package com.zevi.agent;

import android.app.WallpaperManager;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.Log;

import java.io.File;
import java.io.FileInputStream;

/** Sets a clean demo wallpaper from a file path (emulator polish). */
public final class DemoWallpaper {
    private static final String TAG = "DemoWallpaper";

    private DemoWallpaper() {}

    public static boolean setFromPath(Context ctx, String path) {
        try {
            File f = new File(path);
            if (!f.isFile()) {
                Log.w(TAG, "missing " + path);
                return false;
            }
            Bitmap bmp;
            try (FileInputStream in = new FileInputStream(f)) {
                bmp = BitmapFactory.decodeStream(in);
            }
            if (bmp == null) return false;
            WallpaperManager wm = WallpaperManager.getInstance(ctx);
            wm.setBitmap(bmp);
            try {
                wm.setBitmap(bmp, null, true, WallpaperManager.FLAG_SYSTEM);
                wm.setBitmap(bmp, null, true, WallpaperManager.FLAG_LOCK);
            } catch (Throwable ignored) {
            }
            Log.i(TAG, "wallpaper set from " + path);
            return true;
        } catch (Exception e) {
            Log.e(TAG, "set wallpaper failed", e);
            return false;
        }
    }
}
