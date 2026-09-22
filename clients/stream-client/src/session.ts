/**
 * One cloud phone: video socket, audio socket, HTTP input.
 *
 * Transport today is WebSocket. `StreamTransport` names the future
 * WebRTC peer, but this file only opens sockets. The decode path
 * consumes `WireHeader` values, so a later peer can feed the same
 * player without a second input or audio stack.
 */

import { parseWirePacket, type WireHeader } from "./protocol.ts";

function binaryBytes(data: unknown): Uint8Array | null {
  if (data instanceof ArrayBuffer) return new Uint8Array(data);
  if (ArrayBuffer.isView(data)) {
    const view = data as ArrayBufferView;
    const copy = new Uint8Array(view.byteLength);
    copy.set(new Uint8Array(view.buffer, view.byteOffset, view.byteLength));
    return copy;
  }
  return null;
}

/** Soft-launch stream. The phone, not the market page. */
export const SOFT_LAUNCH_STREAM = "https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net";
export const SOFT_LAUNCH_MARKET = "https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/";

export type StreamTransport = "websocket" | "webrtc";

export function assertImplementedTransport(kind: StreamTransport): void {
  if (kind === "webrtc") {
    throw new Error(
      "WebRTC is not deployed. Keep using the WebSocket transport; decoded packets stay WireHeader either way.",
    );
  }
}

export interface StreamEndpoints {
  http: string;
  health: string;
  videoSocket: string;
  audioSocket: string;
  jpegSocket: string;
  tap: string;
  swipe: string;
  key: string;
  type: string;
  size: string;
  preview: string;
}

export function streamEndpoints(base: string): StreamEndpoints {
  const trimmed = base.trim().replace(/\/+$/, "");
  const http = /^wss?:\/\//i.test(trimmed) ? trimmed.replace(/^ws/i, "http") : trimmed;
  if (!/^https?:\/\//i.test(http)) {
    throw new Error("Stream URL must start with http:// or https://");
  }
  const ws = http.replace(/^http/i, "ws");
  return {
    http,
    health: `${http}/health`,
    videoSocket: `${ws}/ws/h264`,
    audioSocket: `${ws}/ws/audio`,
    jpegSocket: `${ws}/ws/stream`,
    tap: `${http}/adb/tap`,
    swipe: `${http}/adb/swipe`,
    key: `${http}/adb/key`,
    type: `${http}/adb/type`,
    size: `${http}/adb/size`,
    preview: `${http}/adb/preview`,
  };
}

export interface StrlixSocket {
  readyState: number;
  binaryType: string;
  send(data: string): void;
  close(code?: number, reason?: string): void;
  onopen: ((ev?: unknown) => void) | null;
  onmessage: ((ev: { data: unknown }) => void) | null;
  onclose: ((ev: { code?: number; reason?: string }) => void) | null;
  onerror: ((ev?: unknown) => void) | null;
}

export type SocketFactory = (url: string) => StrlixSocket;

export function browserSocketFactory(url: string): StrlixSocket {
  const SocketCtor = (globalThis as { WebSocket?: new (url: string) => WebSocket }).WebSocket;
  if (!SocketCtor) throw new Error("WebSocket is not available");
  const ws = new SocketCtor(url);
  ws.binaryType = "arraybuffer";
  return ws as unknown as StrlixSocket;
}

export interface ControlMessage {
  type?: string;
  [key: string]: unknown;
}

export interface SocketHandlers {
  onHello?: (msg: ControlMessage) => void;
  onText?: (msg: ControlMessage) => void;
  onPacket?: (header: WireHeader) => void;
  /** Every binary message, including JPEG frames that are not 16-byte wire packets. */
  onRaw?: (bytes: Uint8Array) => void;
  onClose?: (code: number, reason: string) => void;
}

interface FetchLike {
  (input: string, init?: { method?: string; headers?: Record<string, string>; body?: string }): Promise<{
    ok: boolean;
    status: number;
    json: () => Promise<unknown>;
  }>;
}

/**
 * Owns the sockets for one player. Replies to server pings itself —
 * a viewer that forgets `pong` is dropped after ~40s and looks "stuck".
 */
export class StrlixSession {
  readonly endpoints: StreamEndpoints;
  readonly transport: StreamTransport = "websocket";
  private sockets: StrlixSocket[] = [];
  private video: StrlixSocket | null = null;
  private audio: StrlixSocket | null = null;
  private jpeg: StrlixSocket | null = null;
  private socketFactory: SocketFactory;
  private fetchImpl: FetchLike;

  constructor(
    baseUrl: string,
    socketFactory: SocketFactory = browserSocketFactory,
    fetchImpl: FetchLike = fetch as unknown as FetchLike,
  ) {
    this.endpoints = streamEndpoints(baseUrl);
    this.socketFactory = socketFactory;
    this.fetchImpl = fetchImpl;
  }

  openSocket(url: string, handlers: SocketHandlers): StrlixSocket {
    const socket = this.socketFactory(url);
    socket.binaryType = "arraybuffer";
    socket.onmessage = (ev) => {
      const data = ev.data;
      if (typeof data === "string") {
        let msg: ControlMessage;
        try {
          msg = JSON.parse(data) as ControlMessage;
        } catch {
          return;
        }
        if (msg.type === "ping") {
          try {
            socket.send(JSON.stringify({ type: "pong" }));
          } catch {
            /* closing */
          }
        }
        if (msg.type === "hello") handlers.onHello?.(msg);
        handlers.onText?.(msg);
        return;
      }
      const bytes = binaryBytes(data);
      if (bytes) {
        handlers.onRaw?.(bytes);
        const header = parseWirePacket(bytes);
        if (header) handlers.onPacket?.(header);
      }
    };
    socket.onclose = (ev) => {
      handlers.onClose?.(ev?.code ?? 1006, ev?.reason ?? "");
    };
    socket.onerror = () => {
      /* close follows; the player reconnects from onClose */
    };
    this.sockets.push(socket);
    return socket;
  }

  openVideo(handlers: SocketHandlers): StrlixSocket {
    this.forget(this.video);
    this.video = this.openSocket(this.endpoints.videoSocket, handlers);
    return this.video;
  }

  openAudio(handlers: SocketHandlers): StrlixSocket {
    this.forget(this.audio);
    this.audio = this.openSocket(this.endpoints.audioSocket, handlers);
    return this.audio;
  }

  openJpeg(handlers: SocketHandlers): StrlixSocket {
    this.forget(this.jpeg);
    this.jpeg = this.openSocket(this.endpoints.jpegSocket, handlers);
    return this.jpeg;
  }

  /** Drop a socket without telling its handler. Used when reconnecting. */
  private forget(socket: StrlixSocket | null): void {
    if (!socket) return;
    socket.onclose = null;
    socket.onmessage = null;
    socket.onerror = null;
    this.sockets = this.sockets.filter((item) => item !== socket);
    try {
      socket.close(1000, "reconnect");
    } catch {
      /* already closed */
    }
  }

  stopJpeg(): void {
    this.forget(this.jpeg);
    this.jpeg = null;
  }

  requestKeyframe(): void {
    if (!this.video || this.video.readyState !== 1) return;
    try {
      this.video.send(JSON.stringify({ type: "keyframe" }));
    } catch {
      /* socket just closed */
    }
  }

  close(): void {
    for (const socket of this.sockets) {
      socket.onclose = null;
      socket.onmessage = null;
      socket.onerror = null;
      try {
        socket.close(1000, "client");
      } catch {
        /* already closed */
      }
    }
    this.sockets = [];
    this.video = null;
    this.audio = null;
    this.jpeg = null;
  }

  tap(x: number, y: number): Promise<unknown> {
    return this.post(this.endpoints.tap, { x, y });
  }

  swipe(x1: number, y1: number, x2: number, y2: number, durationMs: number): Promise<unknown> {
    return this.post(this.endpoints.swipe, { x1, y1, x2, y2, duration_ms: durationMs });
  }

  key(keycode: string): Promise<unknown> {
    return this.post(this.endpoints.key, { keycode });
  }

  typeText(text: string): Promise<unknown> {
    return this.post(this.endpoints.type, { text });
  }

  health(): Promise<unknown> {
    return this.fetchImpl(this.endpoints.health).then((res) => {
      if (!res.ok) throw new Error(`health ${res.status}`);
      return res.json();
    });
  }

  deviceSize(): Promise<{ width: number; height: number } | null> {
    return this.fetchImpl(this.endpoints.size)
      .then(async (res) => {
        if (!res.ok) return null;
        const body = (await res.json()) as { width?: number; height?: number };
        if (!body.width || !body.height) return null;
        return { width: body.width, height: body.height };
      })
      .catch(() => null);
  }

  private post(url: string, body: unknown): Promise<unknown> {
    return this.fetchImpl(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(async (res) => {
      if (!res.ok) throw new Error(`${url} ${res.status}`);
      return res.json().catch(() => ({}));
    });
  }
}
