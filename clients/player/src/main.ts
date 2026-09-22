/**
 * Full-screen cloud phone.
 *
 * Open the app and you are on the phone. There is no market, no chat,
 * and no setup wizard. The first tap unlocks the speakers (a browser
 * rule, not a product step). Fingers on Android and iOS, and the mouse
 * on desktop, both land on device pixels of the painted picture.
 */

import { clientToDevice, fitContain, type Box } from "../../stream-client/src/coords.ts";
import { ContactBook, wheelToSwipe } from "../../stream-client/src/gestures.ts";
import { keyboardToDevice } from "../../stream-client/src/keys.ts";
import { SOFT_LAUNCH_STREAM, StrlixSession, type ControlMessage } from "../../stream-client/src/session.ts";
import { Speaker } from "./speaker.ts";
import { VideoSink } from "./video-sink.ts";

interface DesktopBridge {
  platform: "desktop";
  toggleFullScreen: () => Promise<boolean>;
}

const desktop = (window as unknown as { strlixDesktop?: DesktopBridge }).strlixDesktop;

function shell(): { platform: string; input: "cursor" | "touch" } {
  const params = new URLSearchParams(location.search);
  const cap = (window as unknown as { Capacitor?: { getPlatform?: () => string } }).Capacitor;
  const platform = params.get("platform") || desktop?.platform || cap?.getPlatform?.() || "web";
  const requested = params.get("input");
  if (requested === "cursor" || requested === "touch") return { platform, input: requested };
  if (platform === "desktop") return { platform, input: "cursor" };
  if (platform === "android" || platform === "ios") return { platform, input: "touch" };
  const coarse = window.matchMedia?.("(pointer: coarse)")?.matches;
  return { platform, input: coarse ? "touch" : "cursor" };
}

function savedStream(): string {
  const fromQuery = new URLSearchParams(location.search).get("stream");
  if (fromQuery) return fromQuery;
  try {
    return localStorage.getItem("strlix.streamUrl") || SOFT_LAUNCH_STREAM;
  } catch {
    return SOFT_LAUNCH_STREAM;
  }
}

const ui = shell();
document.body.dataset.platform = ui.platform;
document.body.dataset.input = ui.input;

const statusEl = document.getElementById("status") as HTMLParagraphElement;
const hintEl = document.getElementById("hint") as HTMLParagraphElement;
const screenEl = document.getElementById("screen") as HTMLDivElement;
const canvas = document.getElementById("video") as HTMLCanvasElement;
const touch = document.getElementById("touch") as HTMLDivElement;
const soundBtn = document.getElementById("sound") as HTMLButtonElement;
const serverForm = document.getElementById("server") as HTMLFormElement;
const serverUrl = document.getElementById("serverUrl") as HTMLInputElement;
const debug = new URLSearchParams(location.search).has("debug");

let deviceW = 1080;
let deviceH = 2400;
let videoOwns = false;
let audioOn = false;
let reconnects = 0;
let lastWheel = 0;
const frameTimes: number[] = [];

const session = new StrlixSession(savedStream());
const speaker = new Speaker();
const sink = new VideoSink(canvas, () => session.requestKeyframe());
const contacts = new ContactBook();

function setStatus(text: string): void {
  statusEl.textContent = text;
}

function layout(): void {
  const rect = screenEl.getBoundingClientRect();
  const box = fitContain(rect.width, rect.height, deviceW, deviceH);
  for (const el of [canvas, touch]) {
    el.style.left = `${box.left}px`;
    el.style.top = `${box.top}px`;
    el.style.width = `${box.width}px`;
    el.style.height = `${box.height}px`;
  }
}

function setDevice(width: number, height: number): void {
  if (!(width > 0) || !(height > 0)) return;
  if (width === deviceW && height === deviceH) return;
  deviceW = width;
  deviceH = height;
  layout();
}

function painted(): Box {
  const rect = canvas.getBoundingClientRect();
  return { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
}

function toDevice(clientX: number, clientY: number) {
  return clientToDevice(clientX, clientY, painted(), deviceW, deviceH);
}

function unlockAudio(): void {
  speaker.unlock();
  hintEl.hidden = true;
  if (audioOn || speaker.muted) return;
  audioOn = true;
  session.openAudio({
    onHello: (msg) => applyAudioStatus(msg),
    onText: (msg) => {
      if (msg.type === "audio" || msg.type === "hello") applyAudioStatus(msg);
    },
    onPacket: (header) => {
      speaker.feed(header);
      paintSound();
    },
    onClose: () => {
      audioOn = false;
      if (!speaker.muted) {
        speaker.note = "Sound disconnected. Tap the speaker to retry.";
        paintSound();
      }
    },
  });
}

function applyAudioStatus(msg: ControlMessage): void {
  speaker.status(msg);
  paintSound();
  // A missing emulator audio HAL is the thing the user needs to read.
  // "Opening…" stays on the speaker button so it does not cover "Live".
  if (String(msg.source || "") === "error" && speaker.note) setStatus(speaker.note);
}

function paintSound(): void {
  soundBtn.textContent = speaker.muted ? "🔇" : "🔊";
  soundBtn.dataset.on = speaker.live && !speaker.muted ? "1" : "0";
  soundBtn.title = speaker.note || (speaker.muted ? "Sound muted" : "Phone sound");
}

function connectVideo(): void {
  sink.reset();
  videoOwns = false;
  session.openVideo({
    onHello: (msg) => {
      reconnects = 0;
      const w = Number(msg.device_width);
      const h = Number(msg.device_height);
      if (w && h) setDevice(w, h);
      sink.setHelloCodec(String(msg.codec || ""));
      if (!speaker.note) setStatus("Live");
    },
    onText: (msg) => {
      if (msg.type === "bye") setStatus(String(msg.reason || "Stream declined"));
    },
    onPacket: (header) => sink.feed(header),
    onClose: (code) => {
      videoOwns = false;
      const wait = Math.min(5000, Math.round(400 * 1.6 ** reconnects));
      reconnects += 1;
      setStatus(code === 1013 ? "Phone is full — retrying" : "Reconnecting…");
      window.setTimeout(connectVideo, wait);
    },
  });
}

sink.onFirstFrame = () => {
  if (videoOwns) return;
  videoOwns = true;
  session.stopJpeg();
  if (!speaker.note) setStatus(debug ? "Live · H.264" : "Live");
};

sink.onGiveUp = () => {
  setStatus("Video decoder failed — using photos");
  startJpeg();
};

function startJpeg(): void {
  if (videoOwns) return;
  session.openJpeg({
    onRaw: (bytes) => {
      if (videoOwns || bytes.length < 2 || bytes[0] !== 0xff || bytes[1] !== 0xd8) return;
      const blob = new Blob([bytes], { type: "image/jpeg" });
      createImageBitmap(blob)
        .then((bitmap) => {
          if (!videoOwns) {
            sink.paintImage(bitmap, bitmap.width, bitmap.height);
            setStatus("Live · photo fallback");
          }
          bitmap.close();
        })
        .catch(() => undefined);
    },
    onClose: () => {
      if (!videoOwns) window.setTimeout(startJpeg, 900);
    },
  });
}

function sendGesture(gesture: { kind: string; x?: number; y?: number; x1?: number; y1?: number; x2?: number; y2?: number; durationMs?: number }): void {
  if (gesture.kind === "tap") {
    void session.tap(gesture.x ?? 0, gesture.y ?? 0).catch(() => setStatus("Tap did not reach the phone"));
    return;
  }
  void session
    .swipe(gesture.x1 ?? 0, gesture.y1 ?? 0, gesture.x2 ?? 0, gesture.y2 ?? 0, gesture.durationMs ?? 120)
    .catch(() => setStatus("Swipe did not reach the phone"));
}

touch.addEventListener("pointerdown", (ev) => {
  if (ev.pointerType === "mouse" && ev.button === 2) {
    ev.preventDefault();
    unlockAudio();
    void session.key("BACK");
    return;
  }
  if (ev.pointerType === "mouse" && ev.button !== 0) return;
  const point = toDevice(ev.clientX, ev.clientY);
  if (!point) return;
  ev.preventDefault();
  unlockAudio();
  touch.focus({ preventScroll: true });
  try {
    touch.setPointerCapture(ev.pointerId);
  } catch {
    /* the gesture still ends on pointerup */
  }
  contacts.begin({
    id: ev.pointerId,
    x: point.x,
    y: point.y,
    clientX: ev.clientX,
    clientY: ev.clientY,
    t: performance.now(),
  });
});

touch.addEventListener("pointerup", (ev) => {
  const gesture = contacts.end(ev.pointerId, ev.clientX, ev.clientY, performance.now(), toDevice);
  if (!gesture) return;
  ev.preventDefault();
  sendGesture(gesture);
});

touch.addEventListener("pointercancel", (ev) => contacts.cancel(ev.pointerId));
touch.addEventListener("contextmenu", (ev) => ev.preventDefault());

if (ui.input === "cursor") {
  touch.addEventListener(
    "wheel",
    (ev) => {
      ev.preventDefault();
      const now = performance.now();
      if (now - lastWheel < 90) return;
      const origin = toDevice(ev.clientX, ev.clientY);
      if (!origin) return;
      const swipe = wheelToSwipe(origin, ev.deltaX, ev.deltaY, deviceW, deviceH);
      if (!swipe) return;
      lastWheel = now;
      sendGesture(swipe);
    },
    { passive: false },
  );
}

document.addEventListener("keydown", (ev) => {
  const target = ev.target as HTMLElement | null;
  if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;
  if (ev.key === "F11") {
    ev.preventDefault();
    void toggleFull();
    return;
  }
  const action = keyboardToDevice({
    key: ev.key,
    ctrl: ev.ctrlKey,
    meta: ev.metaKey,
    alt: ev.altKey,
  });
  if (action.type === "ignore") return;
  ev.preventDefault();
  unlockAudio();
  if (action.type === "key") void session.key(action.keycode).catch(() => setStatus("Key did not reach the phone"));
  else void session.typeText(action.text).catch(() => setStatus("Text did not reach the phone"));
});

document.getElementById("nav")?.addEventListener("click", (ev) => {
  const button = (ev.target as HTMLElement).closest("button[data-key]") as HTMLButtonElement | null;
  if (!button?.dataset.key) return;
  unlockAudio();
  void session.key(button.dataset.key).catch(() => setStatus("Button did not reach the phone"));
});

soundBtn.addEventListener("click", () => {
  const failed = Boolean(speaker.note) && !speaker.live;
  if (!speaker.unlocked || !audioOn || failed) {
    audioOn = false;
    speaker.setMuted(false);
    unlockAudio();
    return;
  }
  speaker.setMuted(!speaker.muted);
  paintSound();
});

document.getElementById("full")?.addEventListener("click", () => void toggleFull());

async function toggleFull(): Promise<void> {
  if (desktop?.toggleFullScreen) {
    await desktop.toggleFullScreen();
    return;
  }
  if (!document.fullscreenElement) await document.documentElement.requestFullscreen().catch(() => undefined);
  else await document.exitFullscreen().catch(() => undefined);
}

document.getElementById("serverBtn")?.addEventListener("click", () => {
  serverUrl.value = savedStream();
  serverForm.hidden = false;
  serverUrl.focus();
});
document.getElementById("serverCancel")?.addEventListener("click", () => {
  serverForm.hidden = true;
});
serverForm.addEventListener("submit", (ev) => {
  ev.preventDefault();
  const next = serverUrl.value.trim();
  if (!next) return;
  try {
    localStorage.setItem("strlix.streamUrl", next);
  } catch {
    /* private mode */
  }
  const url = new URL(location.href);
  url.searchParams.set("stream", next);
  location.href = url.toString();
});

window.addEventListener("resize", layout);
if (debug) {
  window.setInterval(() => {
    frameTimes.push(sink.frames);
    if (frameTimes.length > 2) frameTimes.shift();
    const fps = frameTimes.length === 2 ? (frameTimes[1] ?? 0) - (frameTimes[0] ?? 0) : 0;
    if (videoOwns) {
      setStatus(`Live · H.264 · ${fps} fps · decode ${sink.decodeMs ?? "—"} ms · drop ${sink.dropped}`);
    }
  }, 1000);
}

layout();
connectVideo();
if (!sink.supported) {
  setStatus("No video decoder — using photos");
  startJpeg();
} else {
  window.setTimeout(() => {
    if (!videoOwns) startJpeg();
  }, 9000);
}

void session.deviceSize().then((size) => {
  if (size) setDevice(size.width, size.height);
});
void session.health().catch(() => {
  if (!videoOwns && sink.frames === 0) setStatus("Phone host is not answering");
});

window.addEventListener("pagehide", () => {
  speaker.close();
  sink.close();
  session.close();
});
