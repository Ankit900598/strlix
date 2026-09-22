/**
 * Phone sound → this device's speakers.
 *
 * Browsers will not start an AudioContext from app launch alone. The
 * player calls `unlock()` on the first finger or click. Until then we
 * do not open `/ws/audio`, so the OpusHead config arrives after the
 * context exists.
 *
 * OpusHead / OpusTags are routed by the shared library. A flags=0
 * OpusHead configures the decoder and is never passed to `decode`.
 */

import { routeAudioPacket, type WireHeader } from "../../stream-client/src/protocol.ts";
import type { ControlMessage } from "../../stream-client/src/session.ts";

export class Speaker {
  private ctx: AudioContext | null = null;
  private gain: GainNode | null = null;
  private dec: AudioDecoder | null = null;
  private configured = false;
  private playAt = 0;
  muted = false;
  unlocked = false;
  codec: "opus" | "pcm" | "aac" | "unknown" = "unknown";
  note = "";
  live = false;

  unlock(): void {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) {
      this.note = "This device has no Web Audio output.";
      return;
    }
    if (!this.ctx) {
      const ctx = new AC({ latencyHint: "interactive" });
      const gain = ctx.createGain();
      gain.gain.value = this.muted ? 0 : 1;
      gain.connect(ctx.destination);
      this.ctx = ctx;
      this.gain = gain;
    }
    if (this.ctx.state === "suspended") void this.ctx.resume();
    this.unlocked = true;
  }

  setMuted(muted: boolean): void {
    this.muted = muted;
    if (this.gain) this.gain.gain.value = muted ? 0 : 1;
  }

  status(msg: ControlMessage): void {
    const codec = msg.codec;
    if (codec === "opus" || codec === "pcm" || codec === "aac") this.codec = codec;
    const source = String(msg.source || "");
    if (source === "error") {
      this.live = false;
      this.note = String(msg.reason || "Phone audio is not available.");
      return;
    }
    if (source === "scrcpy" || source === "pulse") {
      this.note = "";
      this.live = true;
      return;
    }
    if (source === "starting") this.note = "Opening phone audio…";
  }

  feed(header: WireHeader): void {
    if (!this.unlocked || !this.ctx) return;
    const codec = this.codec === "unknown" ? "opus" : this.codec;
    const routed = routeAudioPacket(header, codec);
    if (routed.action === "configure-opus") {
      this.configure(routed.description);
      return;
    }
    if (routed.action === "ignore-config" || routed.action === "drop") return;
    if (routed.action === "play-pcm" && routed.frame) {
      this.playPcm(routed.frame, routed.sampleRate || 48000, routed.channels || 2);
      this.live = true;
      return;
    }
    if (routed.action === "decode-opus" && routed.frame) {
      if (!this.configured) this.configure(undefined);
      this.decode(routed.frame, routed.ptsUs);
    }
  }

  close(): void {
    try {
      this.dec?.close();
    } catch {
      /* already closed */
    }
    this.dec = null;
    this.configured = false;
    void this.ctx?.close();
    this.ctx = null;
    this.gain = null;
  }

  private configure(description: Uint8Array | undefined): void {
    if (typeof AudioDecoder !== "function") {
      this.note =
        "This WebView cannot decode Opus. Sound works in the Android and desktop apps. On iOS, use a WebKit that ships AudioDecoder — steps are in clients/README.md.";
      return;
    }
    if (!this.ctx) return;
    try {
      this.dec?.close();
    } catch {
      /* replacing */
    }
    const dec = new AudioDecoder({
      output: (data) => this.playAudioData(data),
      error: () => {
        this.note = "Opus decoder stopped. Tap the speaker to retry.";
        this.live = false;
        this.configured = false;
      },
    });
    const config: AudioDecoderConfig = {
      codec: "opus",
      sampleRate: 48000,
      numberOfChannels: 2,
    };
    if (description?.byteLength) config.description = description.slice();
    try {
      dec.configure(config);
    } catch {
      if (!config.description) {
        this.note = "Opus is not supported by this decoder.";
        return;
      }
      delete config.description;
      try {
        dec.configure(config);
      } catch {
        this.note = "Opus is not supported by this decoder.";
        return;
      }
    }
    this.dec = dec;
    this.configured = true;
    this.codec = "opus";
  }

  private decode(frame: Uint8Array, ptsUs: number): void {
    const dec = this.dec;
    if (!dec || dec.state !== "configured") return;
    try {
      dec.decode(new EncodedAudioChunk({ type: "key", timestamp: Math.round(ptsUs), data: frame }));
      this.live = true;
      if (!this.note.startsWith("This WebView")) this.note = "";
    } catch {
      this.note = "Could not play a sound frame.";
    }
  }

  private playAudioData(data: AudioData): void {
    const ctx = this.ctx;
    if (!ctx) {
      data.close();
      return;
    }
    try {
      const buffer = ctx.createBuffer(data.numberOfChannels, data.numberOfFrames, data.sampleRate);
      for (let channel = 0; channel < data.numberOfChannels; channel++) {
        data.copyTo(buffer.getChannelData(channel), { planeIndex: channel, format: "f32" });
      }
      this.schedule(buffer);
    } catch {
      this.note = "Speaker output failed.";
    } finally {
      data.close();
    }
  }

  private playPcm(bytes: Uint8Array, sampleRate: number, channels: number): void {
    const ctx = this.ctx;
    if (!ctx) return;
    const view = new Int16Array(bytes.buffer, bytes.byteOffset, Math.floor(bytes.byteLength / 2));
    const frames = Math.floor(view.length / channels);
    if (!frames) return;
    const buffer = ctx.createBuffer(channels, frames, sampleRate);
    for (let channel = 0; channel < channels; channel++) {
      const out = buffer.getChannelData(channel);
      for (let i = 0; i < frames; i++) out[i] = (view[i * channels + channel] ?? 0) / 32768;
    }
    this.schedule(buffer);
  }

  /**
   * Keep a short lead (~50ms) so a single late packet does not click,
   * and snap back if we drift past 350ms. Movies want no clicks.
   * Games want the lead to stay this small.
   */
  private schedule(buffer: AudioBuffer): void {
    const ctx = this.ctx;
    const gain = this.gain;
    if (!ctx || !gain) return;
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(gain);
    const now = ctx.currentTime;
    if (this.playAt < now + 0.02) this.playAt = now + 0.05;
    if (this.playAt > now + 0.35) this.playAt = now + 0.05;
    src.start(this.playAt);
    this.playAt += buffer.duration;
  }
}
