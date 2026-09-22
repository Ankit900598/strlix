/**
 * Fingers and cursors become the gestures desktop-api actually accepts.
 *
 * The public input API is `POST /adb/tap`, `/adb/swipe`, and `/adb/key`.
 * There is no touch-down / touch-move / touch-up stream, so a finger
 * cannot be held as a real Android pointer. Each contact is one tap
 * (barely moved) or one swipe (a drag), sent when that contact ends.
 *
 * Two fingers therefore become two taps or two swipes. That is the
 * honest multi-touch mapping. A pinch is not injected as two live
 * pointers; a future WebRTC or scrcpy control channel can consume the
 * same contact book because the book already tracks every pointer id.
 */

import type { DevicePoint } from "./coords.ts";

export const SWIPE_SLOP_PX = 14;

export interface ContactStart {
  id: number;
  x: number;
  y: number;
  clientX: number;
  clientY: number;
  t: number;
}

export interface TapGesture {
  kind: "tap";
  x: number;
  y: number;
}

export interface SwipeGesture {
  kind: "swipe";
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  durationMs: number;
}

export type DeviceGesture = TapGesture | SwipeGesture;

export function clampDuration(elapsedMs: number): number {
  return Math.max(80, Math.min(800, Math.round(elapsedMs)));
}

export function gestureFromContact(
  start: ContactStart,
  endClientX: number,
  endClientY: number,
  now: number,
  endDevice: DevicePoint | null,
): DeviceGesture {
  const dist = Math.hypot(endClientX - start.clientX, endClientY - start.clientY);
  if (dist < SWIPE_SLOP_PX) {
    return { kind: "tap", x: start.x, y: start.y };
  }
  const end = endDevice ?? { x: start.x, y: start.y };
  return {
    kind: "swipe",
    x1: start.x,
    y1: start.y,
    x2: end.x,
    y2: end.y,
    durationMs: clampDuration(now - start.t),
  };
}

/** One entry per pointer id. Independent contacts, including a second finger. */
export class ContactBook {
  private down = new Map<number, ContactStart>();

  get size(): number {
    return this.down.size;
  }

  begin(contact: ContactStart): void {
    this.down.set(contact.id, contact);
  }

  end(
    id: number,
    clientX: number,
    clientY: number,
    now: number,
    resolveEnd: (clientX: number, clientY: number) => DevicePoint | null,
  ): DeviceGesture | null {
    const start = this.down.get(id);
    this.down.delete(id);
    if (!start) return null;
    return gestureFromContact(start, clientX, clientY, now, resolveEnd(clientX, clientY));
  }

  cancel(id: number): void {
    this.down.delete(id);
  }

  clear(): void {
    this.down.clear();
  }
}

/**
 * Mouse wheel → a short swipe.
 * Wheel-down (deltaY > 0) means "show content below", which on a
 * touchscreen is a finger moving up, so y decreases.
 */
export function wheelToSwipe(
  origin: DevicePoint,
  deltaX: number,
  deltaY: number,
  deviceWidth: number,
  deviceHeight: number,
): SwipeGesture | null {
  if (!(deviceWidth > 0) || !(deviceHeight > 0)) return null;
  const ax = Math.abs(deltaX);
  const ay = Math.abs(deltaY);
  if (ax < 1 && ay < 1) return null;
  const dist = 180;
  let x2 = origin.x;
  let y2 = origin.y;
  if (ay >= ax) {
    y2 = Math.max(0, Math.min(deviceHeight - 1, origin.y + (deltaY > 0 ? -dist : dist)));
  } else {
    x2 = Math.max(0, Math.min(deviceWidth - 1, origin.x + (deltaX > 0 ? -dist : dist)));
  }
  if (x2 === origin.x && y2 === origin.y) return null;
  return { kind: "swipe", x1: origin.x, y1: origin.y, x2, y2, durationMs: 120 };
}
