/**
 * Paint `/ws/h264` onto a canvas with as little delay as we can.
 *
 * WebCodecs is the decode path: one access unit in, one frame out, drawn
 * immediately (not on the next animation frame). Late deltas are dropped
 * once the decoder is already holding a frame — a late P-frame only adds
 * glass latency, which is the thing gaming and movies both feel.
 *
 * Preferred chunk format is avcC + length-prefixed NALs, because Safari
 * needs the description. If that decoder errors, we switch once to raw
 * Annex-B, which is what the production web viewer feeds Chromium.
 */

import { prepareVideoAccessUnit, type WireHeader } from "../../stream-client/src/protocol.ts";

export class VideoSink {
  private ctx: CanvasRenderingContext2D;
  private dec: VideoDecoder | null = null;
  private mode: "avcc" | "annexb" = "avcc";
  private helloCodec = "avc1.42E01E";
  private configKey = "";
  private needKey = true;
  private errors = 0;
  private arrivals = new Map<number, number>();
  private gaveUp = false;
  frames = 0;
  dropped = 0;
  decodeMs: number | null = null;
  onFirstFrame: (() => void) | null = null;
  onGiveUp: ((why: string) => void) | null = null;

  constructor(
    private canvas: HTMLCanvasElement,
    private requestKeyframe: () => void,
  ) {
    const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
    if (!ctx) throw new Error("2D canvas is unavailable");
    this.ctx = ctx;
  }

  get supported(): boolean {
    return typeof globalThis.VideoDecoder === "function";
  }

  setHelloCodec(codec: string): void {
    if (codec) this.helloCodec = codec;
  }

  feed(header: WireHeader): void {
    if (this.gaveUp || !this.supported) return;
    const prepared = prepareVideoAccessUnit(header);
    if (!prepared) return;
    if (this.needKey && prepared.kind !== "key") return;

    if (this.mode === "avcc" && prepared.description && prepared.codec) {
      this.configure(prepared.codec, prepared.description);
      if (prepared.avccSample.byteLength) this.decode(prepared.kind, prepared.avccSample, prepared.ptsUs);
      return;
    }
    if (this.mode === "avcc" && this.configKey.startsWith("avcc:") && prepared.avccSample.byteLength) {
      this.decode(prepared.kind, prepared.avccSample, prepared.ptsUs);
      return;
    }

    this.mode = "annexb";
    this.configure(prepared.codec || this.helloCodec, null);
    this.decode(prepared.kind, prepared.annexB, prepared.ptsUs);
  }

  /** New socket: drop the old decoder so the next IDR is not applied to a stale reference. */
  reset(): void {
    this.gaveUp = false;
    this.errors = 0;
    this.frames = 0;
    this.dropped = 0;
    this.mode = "avcc";
    this.configKey = "";
    this.closeDecoder();
  }

  paintImage(source: CanvasImageSource, width: number, height: number): void {
    if (!width || !height) return;
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.ctx.drawImage(source, 0, 0, width, height);
  }

  close(): void {
    this.gaveUp = true;
    this.closeDecoder();
  }

  private configure(codec: string, description: Uint8Array | null): void {
    const key = description ? `avcc:${codec}:${description.byteLength}:${description[1] ?? 0}` : `annex:${codec}`;
    if (this.dec && this.dec.state === "configured" && key === this.configKey) return;
    this.configKey = key;
    this.closeDecoder();
    const dec = new VideoDecoder({
      output: (frame) => {
        try {
          this.paint(frame);
        } finally {
          frame.close();
        }
      },
      error: () => this.fail("decoder"),
    });
    const config: VideoDecoderConfig = {
      codec,
      optimizeForLatency: true,
      hardwareAcceleration: "no-preference",
    };
    if (description) config.description = description;
    try {
      dec.configure(config);
    } catch {
      this.fail("configure");
      return;
    }
    this.dec = dec;
    this.needKey = true;
  }

  private decode(type: "key" | "delta", data: Uint8Array, ptsUs: number): void {
    const dec = this.dec;
    if (!dec || dec.state !== "configured" || !data.byteLength) return;
    if (this.needKey && type !== "key") return;
    if (type !== "key" && dec.decodeQueueSize > 1) {
      this.dropped += 1;
      return;
    }
    const timestamp = Math.round(ptsUs);
    try {
      dec.decode(new EncodedVideoChunk({ type, timestamp, data }));
      if (type === "key") this.needKey = false;
      if (this.arrivals.size > 240) this.arrivals.clear();
      this.arrivals.set(timestamp, performance.now());
    } catch {
      this.fail("decode");
    }
  }

  private paint(frame: VideoFrame): void {
    const width = frame.displayWidth || frame.codedWidth;
    const height = frame.displayHeight || frame.codedHeight;
    if (!width || !height) return;
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    const arrived = this.arrivals.get(frame.timestamp);
    if (arrived != null) {
      this.decodeMs = Math.round(performance.now() - arrived);
      this.arrivals.delete(frame.timestamp);
    }
    this.ctx.drawImage(frame, 0, 0, width, height);
    this.frames += 1;
    this.errors = 0;
    if (this.frames === 1) this.onFirstFrame?.();
  }

  private fail(why: string): void {
    this.needKey = true;
    this.errors += 1;
    if (this.mode === "avcc") {
      this.mode = "annexb";
      this.configKey = "";
      this.closeDecoder();
      this.requestKeyframe();
      return;
    }
    this.requestKeyframe();
    if (this.errors > 4 && !this.gaveUp) {
      this.gaveUp = true;
      this.onGiveUp?.(why);
    }
  }

  private closeDecoder(): void {
    const dec = this.dec;
    this.dec = null;
    this.needKey = true;
    if (dec && dec.state !== "closed") {
      try {
        dec.close();
      } catch {
        /* already closed */
      }
    }
  }
}
