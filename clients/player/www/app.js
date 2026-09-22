(() => {
  // ../stream-client/src/coords.ts
  var EDGE_TOLERANCE_PX = 40;
  function clientToDevice(clientX, clientY, painted2, deviceWidth, deviceHeight, edgeTol = EDGE_TOLERANCE_PX) {
    if (!(painted2.width > 1) || !(painted2.height > 1)) return null;
    if (!(deviceWidth > 0) || !(deviceHeight > 0)) return null;
    const scaleX = painted2.width / deviceWidth;
    const scaleY = painted2.height / deviceHeight;
    if (!scaleX || !scaleY) return null;
    const ix = (clientX - painted2.left) / scaleX;
    const iy = (clientY - painted2.top) / scaleY;
    if (ix < -edgeTol || iy < -edgeTol || ix > deviceWidth + edgeTol || iy > deviceHeight + edgeTol) {
      return null;
    }
    return {
      x: Math.max(0, Math.min(deviceWidth - 1, Math.round(ix))),
      y: Math.max(0, Math.min(deviceHeight - 1, Math.round(iy)))
    };
  }
  function fitContain(viewportW, viewportH, deviceW2, deviceH2) {
    if (viewportW <= 0 || viewportH <= 0 || deviceW2 <= 0 || deviceH2 <= 0) {
      return { left: 0, top: 0, width: 0, height: 0 };
    }
    const scale = Math.min(viewportW / deviceW2, viewportH / deviceH2);
    const width = deviceW2 * scale;
    const height = deviceH2 * scale;
    return {
      width,
      height,
      left: (viewportW - width) / 2,
      top: (viewportH - height) / 2
    };
  }

  // ../stream-client/src/gestures.ts
  var SWIPE_SLOP_PX = 14;
  function clampDuration(elapsedMs) {
    return Math.max(80, Math.min(800, Math.round(elapsedMs)));
  }
  function gestureFromContact(start, endClientX, endClientY, now, endDevice) {
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
      durationMs: clampDuration(now - start.t)
    };
  }
  var ContactBook = class {
    down = /* @__PURE__ */ new Map();
    get size() {
      return this.down.size;
    }
    begin(contact) {
      this.down.set(contact.id, contact);
    }
    end(id, clientX, clientY, now, resolveEnd) {
      const start = this.down.get(id);
      this.down.delete(id);
      if (!start) return null;
      return gestureFromContact(start, clientX, clientY, now, resolveEnd(clientX, clientY));
    }
    cancel(id) {
      this.down.delete(id);
    }
    clear() {
      this.down.clear();
    }
  };
  function wheelToSwipe(origin, deltaX, deltaY, deviceWidth, deviceHeight) {
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

  // ../stream-client/src/keys.ts
  function keyboardToDevice(input) {
    if (input.ctrl || input.meta || input.alt) return { type: "ignore" };
    switch (input.key) {
      case "Escape":
        return { type: "key", keycode: "BACK" };
      case "Enter":
        return { type: "key", keycode: "ENTER" };
      case "Backspace":
        return { type: "key", keycode: "DEL" };
      case "Tab":
        return { type: "key", keycode: "TAB" };
      case "ArrowUp":
        return { type: "key", keycode: "KEYCODE_DPAD_UP" };
      case "ArrowDown":
        return { type: "key", keycode: "KEYCODE_DPAD_DOWN" };
      case "ArrowLeft":
        return { type: "key", keycode: "KEYCODE_DPAD_LEFT" };
      case "ArrowRight":
        return { type: "key", keycode: "KEYCODE_DPAD_RIGHT" };
      case "Home":
        return { type: "key", keycode: "HOME" };
      case "PageUp":
        return { type: "key", keycode: "VOLUME_UP" };
      case "PageDown":
        return { type: "key", keycode: "VOLUME_DOWN" };
      default:
        break;
    }
    if (input.key.length === 1 && input.key >= " " && input.key <= "~") {
      return { type: "text", text: input.key };
    }
    return { type: "ignore" };
  }

  // ../stream-client/src/protocol.ts
  var WIRE_HEADER_BYTES = 16;
  var WIRE_VERSION = 1;
  var FLAG_KEY_OR_CONFIG = 1;
  var OPUS_HEAD = ascii("OpusHead");
  var OPUS_TAGS = ascii("OpusTags");
  function ascii(text) {
    const out = new Uint8Array(text.length);
    for (let i = 0; i < text.length; i++) out[i] = text.charCodeAt(i);
    return out;
  }
  function startsWith(payload, magic) {
    if (payload.length < magic.length) return false;
    for (let i = 0; i < magic.length; i++) {
      if (payload[i] !== magic[i]) return false;
    }
    return true;
  }
  function parseWirePacket(data) {
    const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    if (bytes.byteLength < WIRE_HEADER_BYTES) return null;
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const version = view.getUint8(0);
    if (version !== WIRE_VERSION) return null;
    return {
      version,
      flags: view.getUint8(1),
      sequence: view.getUint32(4, true),
      ptsUs: view.getFloat64(8, true),
      payload: bytes.subarray(WIRE_HEADER_BYTES)
    };
  }
  function isOpusHead(payload) {
    return startsWith(payload, OPUS_HEAD);
  }
  function isOpusTags(payload) {
    return startsWith(payload, OPUS_TAGS);
  }
  function parseOpusHead(payload) {
    if (!isOpusHead(payload) || payload.length < 19) return null;
    const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
    return {
      version: payload[8] ?? 0,
      channels: payload[9] ?? 0,
      preSkip: view.getUint16(10, true),
      inputSampleRate: view.getUint32(12, true),
      outputGain: view.getInt16(16, true),
      channelMappingFamily: payload[18] ?? 0
    };
  }
  function routeAudioPacket(header, codec) {
    const payload = header.payload;
    const ptsUs = header.ptsUs;
    const flagged = (header.flags & FLAG_KEY_OR_CONFIG) === FLAG_KEY_OR_CONFIG;
    if (isOpusHead(payload)) {
      const info = parseOpusHead(payload);
      return {
        action: "configure-opus",
        ptsUs,
        description: payload,
        channels: info?.channels || 2,
        sampleRate: 48e3
      };
    }
    if (isOpusTags(payload)) {
      return { action: "ignore-config", ptsUs, description: payload };
    }
    if (flagged) {
      return {
        action: "configure-opus",
        ptsUs,
        description: payload.byteLength ? payload : void 0,
        channels: 2,
        sampleRate: 48e3
      };
    }
    if (!payload.byteLength) return { action: "drop", ptsUs };
    if (codec === "pcm") return { action: "play-pcm", ptsUs, frame: payload, channels: 2, sampleRate: 48e3 };
    if (codec === "aac") return { action: "drop", ptsUs };
    return { action: "decode-opus", ptsUs, frame: payload };
  }
  function splitAnnexB(data) {
    const nalStarts = [];
    for (let i = 0; i + 3 < data.length; i++) {
      if (data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 1) {
        nalStarts.push(i + 3);
        i += 2;
        continue;
      }
      if (i + 4 < data.length && data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 0 && data[i + 3] === 1) {
        nalStarts.push(i + 4);
        i += 3;
      }
    }
    const out = [];
    for (let n = 0; n < nalStarts.length; n++) {
      const begin = nalStarts[n] ?? 0;
      const next = nalStarts[n + 1];
      let end = data.length;
      if (next != null) {
        end = next >= 4 && data[next - 4] === 0 && data[next - 3] === 0 && data[next - 2] === 0 && data[next - 1] === 1 ? next - 4 : next - 3;
      }
      if (end <= begin) continue;
      const payload = data.subarray(begin, end);
      out.push({ type: payload[0] & 31, payload });
    }
    return out;
  }
  function annexBStartCodeLength(payload) {
    if (payload.length >= 4 && payload[0] === 0 && payload[1] === 0 && payload[2] === 0 && payload[3] === 1) {
      return 4;
    }
    if (payload.length >= 3 && payload[0] === 0 && payload[1] === 0 && payload[2] === 1) return 3;
    return 0;
  }
  function avcCodecString(sps) {
    if (sps.length < 4) return null;
    const hex = (b) => b.toString(16).toUpperCase().padStart(2, "0");
    return `avc1.${hex(sps[1] ?? 0)}${hex(sps[2] ?? 0)}${hex(sps[3] ?? 0)}`;
  }
  function buildAvcDecoderConfig(sps, pps) {
    if (sps.length < 4 || pps.length < 1) return null;
    const out = new Uint8Array(11 + sps.length + pps.length);
    out[0] = 1;
    out[1] = sps[1] ?? 0;
    out[2] = sps[2] ?? 0;
    out[3] = sps[3] ?? 0;
    out[4] = 255;
    out[5] = 225;
    out[6] = sps.length >> 8 & 255;
    out[7] = sps.length & 255;
    out.set(sps, 8);
    let offset = 8 + sps.length;
    out[offset++] = 1;
    out[offset++] = pps.length >> 8 & 255;
    out[offset++] = pps.length & 255;
    out.set(pps, offset);
    return out;
  }
  function lengthPrefixNals(nals) {
    let size = 0;
    for (const nal of nals) size += 4 + nal.length;
    const out = new Uint8Array(size);
    const view = new DataView(out.buffer);
    let offset = 0;
    for (const nal of nals) {
      view.setUint32(offset, nal.length, false);
      out.set(nal, offset + 4);
      offset += 4 + nal.length;
    }
    return out;
  }
  var VCL_TYPES = /* @__PURE__ */ new Set([1, 2, 3, 4, 5]);
  function prepareVideoAccessUnit(header) {
    if (!header.payload.byteLength) return null;
    if (annexBStartCodeLength(header.payload) === 0) return null;
    const nals = splitAnnexB(header.payload);
    const sps = nals.find((n) => n.type === 7)?.payload ?? null;
    const pps = nals.find((n) => n.type === 8)?.payload ?? null;
    const vcl = nals.filter((n) => VCL_TYPES.has(n.type)).map((n) => n.payload);
    const key = (header.flags & FLAG_KEY_OR_CONFIG) === FLAG_KEY_OR_CONFIG || nals.some((n) => n.type === 5 || n.type === 7);
    return {
      kind: key ? "key" : "delta",
      ptsUs: header.ptsUs,
      annexB: header.payload,
      avccSample: lengthPrefixNals(vcl),
      sps,
      pps,
      codec: sps ? avcCodecString(sps) : null,
      description: sps && pps ? buildAvcDecoderConfig(sps, pps) : null
    };
  }

  // ../stream-client/src/session.ts
  function binaryBytes(data) {
    if (data instanceof ArrayBuffer) return new Uint8Array(data);
    if (ArrayBuffer.isView(data)) {
      const view = data;
      const copy = new Uint8Array(view.byteLength);
      copy.set(new Uint8Array(view.buffer, view.byteOffset, view.byteLength));
      return copy;
    }
    return null;
  }
  var SOFT_LAUNCH_STREAM = "https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net";
  function streamEndpoints(base) {
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
      preview: `${http}/adb/preview`
    };
  }
  function browserSocketFactory(url) {
    const SocketCtor = globalThis.WebSocket;
    if (!SocketCtor) throw new Error("WebSocket is not available");
    const ws = new SocketCtor(url);
    ws.binaryType = "arraybuffer";
    return ws;
  }
  var StrlixSession = class {
    endpoints;
    transport = "websocket";
    sockets = [];
    video = null;
    audio = null;
    jpeg = null;
    socketFactory;
    fetchImpl;
    constructor(baseUrl, socketFactory = browserSocketFactory, fetchImpl = fetch) {
      this.endpoints = streamEndpoints(baseUrl);
      this.socketFactory = socketFactory;
      this.fetchImpl = fetchImpl;
    }
    openSocket(url, handlers) {
      const socket = this.socketFactory(url);
      socket.binaryType = "arraybuffer";
      socket.onmessage = (ev) => {
        const data = ev.data;
        if (typeof data === "string") {
          let msg;
          try {
            msg = JSON.parse(data);
          } catch {
            return;
          }
          if (msg.type === "ping") {
            try {
              socket.send(JSON.stringify({ type: "pong" }));
            } catch {
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
      };
      this.sockets.push(socket);
      return socket;
    }
    openVideo(handlers) {
      this.forget(this.video);
      this.video = this.openSocket(this.endpoints.videoSocket, handlers);
      return this.video;
    }
    openAudio(handlers) {
      this.forget(this.audio);
      this.audio = this.openSocket(this.endpoints.audioSocket, handlers);
      return this.audio;
    }
    openJpeg(handlers) {
      this.forget(this.jpeg);
      this.jpeg = this.openSocket(this.endpoints.jpegSocket, handlers);
      return this.jpeg;
    }
    /** Drop a socket without telling its handler. Used when reconnecting. */
    forget(socket) {
      if (!socket) return;
      socket.onclose = null;
      socket.onmessage = null;
      socket.onerror = null;
      this.sockets = this.sockets.filter((item) => item !== socket);
      try {
        socket.close(1e3, "reconnect");
      } catch {
      }
    }
    stopJpeg() {
      this.forget(this.jpeg);
      this.jpeg = null;
    }
    requestKeyframe() {
      if (!this.video || this.video.readyState !== 1) return;
      try {
        this.video.send(JSON.stringify({ type: "keyframe" }));
      } catch {
      }
    }
    close() {
      for (const socket of this.sockets) {
        socket.onclose = null;
        socket.onmessage = null;
        socket.onerror = null;
        try {
          socket.close(1e3, "client");
        } catch {
        }
      }
      this.sockets = [];
      this.video = null;
      this.audio = null;
      this.jpeg = null;
    }
    tap(x, y) {
      return this.post(this.endpoints.tap, { x, y });
    }
    swipe(x1, y1, x2, y2, durationMs) {
      return this.post(this.endpoints.swipe, { x1, y1, x2, y2, duration_ms: durationMs });
    }
    key(keycode) {
      return this.post(this.endpoints.key, { keycode });
    }
    typeText(text) {
      return this.post(this.endpoints.type, { text });
    }
    health() {
      return this.fetchImpl(this.endpoints.health).then((res) => {
        if (!res.ok) throw new Error(`health ${res.status}`);
        return res.json();
      });
    }
    deviceSize() {
      return this.fetchImpl(this.endpoints.size).then(async (res) => {
        if (!res.ok) return null;
        const body = await res.json();
        if (!body.width || !body.height) return null;
        return { width: body.width, height: body.height };
      }).catch(() => null);
    }
    post(url, body) {
      return this.fetchImpl(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      }).then(async (res) => {
        if (!res.ok) throw new Error(`${url} ${res.status}`);
        return res.json().catch(() => ({}));
      });
    }
  };

  // src/speaker.ts
  var Speaker = class {
    ctx = null;
    gain = null;
    dec = null;
    configured = false;
    playAt = 0;
    muted = false;
    unlocked = false;
    codec = "unknown";
    note = "";
    live = false;
    unlock() {
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
    setMuted(muted) {
      this.muted = muted;
      if (this.gain) this.gain.gain.value = muted ? 0 : 1;
    }
    status(msg) {
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
      if (source === "starting") this.note = "Opening phone audio\u2026";
    }
    feed(header) {
      if (!this.unlocked || !this.ctx) return;
      const codec = this.codec === "unknown" ? "opus" : this.codec;
      const routed = routeAudioPacket(header, codec);
      if (routed.action === "configure-opus") {
        this.configure(routed.description);
        return;
      }
      if (routed.action === "ignore-config" || routed.action === "drop") return;
      if (routed.action === "play-pcm" && routed.frame) {
        this.playPcm(routed.frame, routed.sampleRate || 48e3, routed.channels || 2);
        this.live = true;
        return;
      }
      if (routed.action === "decode-opus" && routed.frame) {
        if (!this.configured) this.configure(void 0);
        this.decode(routed.frame, routed.ptsUs);
      }
    }
    close() {
      try {
        this.dec?.close();
      } catch {
      }
      this.dec = null;
      this.configured = false;
      void this.ctx?.close();
      this.ctx = null;
      this.gain = null;
    }
    configure(description) {
      if (typeof AudioDecoder !== "function") {
        this.note = "This WebView cannot decode Opus. Sound works in the Android and desktop apps. On iOS, use a WebKit that ships AudioDecoder \u2014 steps are in clients/README.md.";
        return;
      }
      if (!this.ctx) return;
      try {
        this.dec?.close();
      } catch {
      }
      const dec = new AudioDecoder({
        output: (data) => this.playAudioData(data),
        error: () => {
          this.note = "Opus decoder stopped. Tap the speaker to retry.";
          this.live = false;
          this.configured = false;
        }
      });
      const config = {
        codec: "opus",
        sampleRate: 48e3,
        numberOfChannels: 2
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
    decode(frame, ptsUs) {
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
    playAudioData(data) {
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
    playPcm(bytes, sampleRate, channels) {
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
    schedule(buffer) {
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
  };

  // src/video-sink.ts
  var VideoSink = class {
    constructor(canvas2, requestKeyframe) {
      this.canvas = canvas2;
      this.requestKeyframe = requestKeyframe;
      const ctx = canvas2.getContext("2d", { alpha: false, desynchronized: true });
      if (!ctx) throw new Error("2D canvas is unavailable");
      this.ctx = ctx;
    }
    ctx;
    dec = null;
    mode = "avcc";
    helloCodec = "avc1.42E01E";
    configKey = "";
    needKey = true;
    errors = 0;
    arrivals = /* @__PURE__ */ new Map();
    gaveUp = false;
    frames = 0;
    dropped = 0;
    decodeMs = null;
    onFirstFrame = null;
    onGiveUp = null;
    get supported() {
      return typeof globalThis.VideoDecoder === "function";
    }
    setHelloCodec(codec) {
      if (codec) this.helloCodec = codec;
    }
    feed(header) {
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
    reset() {
      this.gaveUp = false;
      this.errors = 0;
      this.frames = 0;
      this.dropped = 0;
      this.mode = "avcc";
      this.configKey = "";
      this.closeDecoder();
    }
    paintImage(source, width, height) {
      if (!width || !height) return;
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width;
        this.canvas.height = height;
      }
      this.ctx.drawImage(source, 0, 0, width, height);
    }
    close() {
      this.gaveUp = true;
      this.closeDecoder();
    }
    configure(codec, description) {
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
        error: () => this.fail("decoder")
      });
      const config = {
        codec,
        optimizeForLatency: true,
        hardwareAcceleration: "no-preference"
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
    decode(type, data, ptsUs) {
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
    paint(frame) {
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
    fail(why) {
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
    closeDecoder() {
      const dec = this.dec;
      this.dec = null;
      this.needKey = true;
      if (dec && dec.state !== "closed") {
        try {
          dec.close();
        } catch {
        }
      }
    }
  };

  // src/main.ts
  var desktop = window.strlixDesktop;
  function shell() {
    const params = new URLSearchParams(location.search);
    const cap = window.Capacitor;
    const platform = params.get("platform") || desktop?.platform || cap?.getPlatform?.() || "web";
    const requested = params.get("input");
    if (requested === "cursor" || requested === "touch") return { platform, input: requested };
    if (platform === "desktop") return { platform, input: "cursor" };
    if (platform === "android" || platform === "ios") return { platform, input: "touch" };
    const coarse = window.matchMedia?.("(pointer: coarse)")?.matches;
    return { platform, input: coarse ? "touch" : "cursor" };
  }
  function savedStream() {
    const fromQuery = new URLSearchParams(location.search).get("stream");
    if (fromQuery) return fromQuery;
    try {
      return localStorage.getItem("strlix.streamUrl") || SOFT_LAUNCH_STREAM;
    } catch {
      return SOFT_LAUNCH_STREAM;
    }
  }
  var ui = shell();
  document.body.dataset.platform = ui.platform;
  document.body.dataset.input = ui.input;
  var statusEl = document.getElementById("status");
  var hintEl = document.getElementById("hint");
  var screenEl = document.getElementById("screen");
  var canvas = document.getElementById("video");
  var touch = document.getElementById("touch");
  var soundBtn = document.getElementById("sound");
  var serverForm = document.getElementById("server");
  var serverUrl = document.getElementById("serverUrl");
  var debug = new URLSearchParams(location.search).has("debug");
  var deviceW = 1080;
  var deviceH = 2400;
  var videoOwns = false;
  var audioOn = false;
  var reconnects = 0;
  var lastWheel = 0;
  var frameTimes = [];
  var session = new StrlixSession(savedStream());
  var speaker = new Speaker();
  var sink = new VideoSink(canvas, () => session.requestKeyframe());
  var contacts = new ContactBook();
  function setStatus(text) {
    statusEl.textContent = text;
  }
  function layout() {
    const rect = screenEl.getBoundingClientRect();
    const box = fitContain(rect.width, rect.height, deviceW, deviceH);
    for (const el of [canvas, touch]) {
      el.style.left = `${box.left}px`;
      el.style.top = `${box.top}px`;
      el.style.width = `${box.width}px`;
      el.style.height = `${box.height}px`;
    }
  }
  function setDevice(width, height) {
    if (!(width > 0) || !(height > 0)) return;
    if (width === deviceW && height === deviceH) return;
    deviceW = width;
    deviceH = height;
    layout();
  }
  function painted() {
    const rect = canvas.getBoundingClientRect();
    return { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
  }
  function toDevice(clientX, clientY) {
    return clientToDevice(clientX, clientY, painted(), deviceW, deviceH);
  }
  function unlockAudio() {
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
      }
    });
  }
  function applyAudioStatus(msg) {
    speaker.status(msg);
    paintSound();
    if (String(msg.source || "") === "error" && speaker.note) setStatus(speaker.note);
  }
  function paintSound() {
    soundBtn.textContent = speaker.muted ? "\u{1F507}" : "\u{1F50A}";
    soundBtn.dataset.on = speaker.live && !speaker.muted ? "1" : "0";
    soundBtn.title = speaker.note || (speaker.muted ? "Sound muted" : "Phone sound");
  }
  function connectVideo() {
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
        const wait = Math.min(5e3, Math.round(400 * 1.6 ** reconnects));
        reconnects += 1;
        setStatus(code === 1013 ? "Phone is full \u2014 retrying" : "Reconnecting\u2026");
        window.setTimeout(connectVideo, wait);
      }
    });
  }
  sink.onFirstFrame = () => {
    if (videoOwns) return;
    videoOwns = true;
    session.stopJpeg();
    if (!speaker.note) setStatus(debug ? "Live \xB7 H.264" : "Live");
  };
  sink.onGiveUp = () => {
    setStatus("Video decoder failed \u2014 using photos");
    startJpeg();
  };
  function startJpeg() {
    if (videoOwns) return;
    session.openJpeg({
      onRaw: (bytes) => {
        if (videoOwns || bytes.length < 2 || bytes[0] !== 255 || bytes[1] !== 216) return;
        const blob = new Blob([bytes], { type: "image/jpeg" });
        createImageBitmap(blob).then((bitmap) => {
          if (!videoOwns) {
            sink.paintImage(bitmap, bitmap.width, bitmap.height);
            setStatus("Live \xB7 photo fallback");
          }
          bitmap.close();
        }).catch(() => void 0);
      },
      onClose: () => {
        if (!videoOwns) window.setTimeout(startJpeg, 900);
      }
    });
  }
  function sendGesture(gesture) {
    if (gesture.kind === "tap") {
      void session.tap(gesture.x ?? 0, gesture.y ?? 0).catch(() => setStatus("Tap did not reach the phone"));
      return;
    }
    void session.swipe(gesture.x1 ?? 0, gesture.y1 ?? 0, gesture.x2 ?? 0, gesture.y2 ?? 0, gesture.durationMs ?? 120).catch(() => setStatus("Swipe did not reach the phone"));
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
    }
    contacts.begin({
      id: ev.pointerId,
      x: point.x,
      y: point.y,
      clientX: ev.clientX,
      clientY: ev.clientY,
      t: performance.now()
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
      { passive: false }
    );
  }
  document.addEventListener("keydown", (ev) => {
    const target = ev.target;
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
      alt: ev.altKey
    });
    if (action.type === "ignore") return;
    ev.preventDefault();
    unlockAudio();
    if (action.type === "key") void session.key(action.keycode).catch(() => setStatus("Key did not reach the phone"));
    else void session.typeText(action.text).catch(() => setStatus("Text did not reach the phone"));
  });
  document.getElementById("nav")?.addEventListener("click", (ev) => {
    const button = ev.target.closest("button[data-key]");
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
  async function toggleFull() {
    if (desktop?.toggleFullScreen) {
      await desktop.toggleFullScreen();
      return;
    }
    if (!document.fullscreenElement) await document.documentElement.requestFullscreen().catch(() => void 0);
    else await document.exitFullscreen().catch(() => void 0);
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
        setStatus(`Live \xB7 H.264 \xB7 ${fps} fps \xB7 decode ${sink.decodeMs ?? "\u2014"} ms \xB7 drop ${sink.dropped}`);
      }
    }, 1e3);
  }
  layout();
  connectVideo();
  if (!sink.supported) {
    setStatus("No video decoder \u2014 using photos");
    startJpeg();
  } else {
    window.setTimeout(() => {
      if (!videoOwns) startJpeg();
    }, 9e3);
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
})();
//# sourceMappingURL=app.js.map
