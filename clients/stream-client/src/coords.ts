/**
 * Map a finger or cursor onto Android pixels.
 *
 * The canvas bitmap is the *encoder* size (often ~480×1080). The phone
 * is the *device* size (1080×2400 on the soft-launch emulator). Taps
 * must use device pixels, because `input tap` is in that coordinate
 * space. Mapping through the encoder size lands every tap in the
 * top-left quarter of the screen.
 *
 * The painted element is the source of truth — the rectangle the user
 * is actually looking at — not a letterbox we recompute from CSS.
 */

export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface DevicePoint {
  x: number;
  y: number;
}

/** How far outside the picture a finger can be and still count, in device px. */
export const EDGE_TOLERANCE_PX = 40;

export function clientToDevice(
  clientX: number,
  clientY: number,
  painted: Box,
  deviceWidth: number,
  deviceHeight: number,
  edgeTol = EDGE_TOLERANCE_PX,
): DevicePoint | null {
  if (!(painted.width > 1) || !(painted.height > 1)) return null;
  if (!(deviceWidth > 0) || !(deviceHeight > 0)) return null;
  const scaleX = painted.width / deviceWidth;
  const scaleY = painted.height / deviceHeight;
  if (!scaleX || !scaleY) return null;
  const ix = (clientX - painted.left) / scaleX;
  const iy = (clientY - painted.top) / scaleY;
  if (ix < -edgeTol || iy < -edgeTol || ix > deviceWidth + edgeTol || iy > deviceHeight + edgeTol) {
    return null;
  }
  return {
    x: Math.max(0, Math.min(deviceWidth - 1, Math.round(ix))),
    y: Math.max(0, Math.min(deviceHeight - 1, Math.round(iy))),
  };
}

/**
 * Largest rectangle of `deviceW × deviceH` that fits in the viewport,
 * centered. The canvas CSS box should be this rectangle so the hit
 * target and the picture are the same element.
 */
export function fitContain(
  viewportW: number,
  viewportH: number,
  deviceW: number,
  deviceH: number,
): Box {
  if (viewportW <= 0 || viewportH <= 0 || deviceW <= 0 || deviceH <= 0) {
    return { left: 0, top: 0, width: 0, height: 0 };
  }
  const scale = Math.min(viewportW / deviceW, viewportH / deviceH);
  const width = deviceW * scale;
  const height = deviceH * scale;
  return {
    width,
    height,
    left: (viewportW - width) / 2,
    top: (viewportH - height) / 2,
  };
}
