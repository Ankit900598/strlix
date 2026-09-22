/**
 * Strlix live wire format.
 *
 * Video (`/ws/h264`) and audio (`/ws/audio`) use the same 16-byte
 * little-endian header so one parser serves both sockets. They do NOT
 * share a meaning for flags bit 0:
 *
 *   video  bit0 = this access unit is a keyframe (IDR, SPS/PPS prepended)
 *   audio  bit0 = this packet is codec config (OpusHead), not a sound frame
 *
 * Layout, matching `struct.Struct("<BBHId")` in `app/h264_stream.py`
 * and `app/device_audio.py`:
 *
 *   offset 0   u8   version (1)
 *   offset 1   u8   flags
 *   offset 2   u16  reserved
 *   offset 4   u32  sequence
 *   offset 8   f64  PTS in microseconds
 *   offset 16… payload (Annex-B H.264, or Opus/PCM)
 *
 * Production has shipped OpusHead / OpusTags packets with flags = 0.
 * Those bytes are headers, not audio. Decoding them makes the Opus
 * decoder error and the rest of the stream goes silent. Sniff the
 * magic even when the flag is missing. The server fix is separate.
 */

export const WIRE_HEADER_BYTES = 16;
export const WIRE_VERSION = 1;
/** Video keyframe, and audio codec-config. Same bit, different sockets. */
export const FLAG_KEY_OR_CONFIG = 1;

const OPUS_HEAD = ascii("OpusHead");
const OPUS_TAGS = ascii("OpusTags");

function ascii(text: string): Uint8Array {
  const out = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) out[i] = text.charCodeAt(i);
  return out;
}

function startsWith(payload: Uint8Array, magic: Uint8Array): boolean {
  if (payload.length < magic.length) return false;
  for (let i = 0; i < magic.length; i++) {
    if (payload[i] !== magic[i]) return false;
  }
  return true;
}

export interface WireHeader {
  version: number;
  flags: number;
  sequence: number;
  /** Presentation timestamp in microseconds. Hand this to the decoder. */
  ptsUs: number;
  payload: Uint8Array;
}

export function parseWirePacket(data: ArrayBuffer | Uint8Array): WireHeader | null {
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
    payload: bytes.subarray(WIRE_HEADER_BYTES),
  };
}

/** Test helper and a readable picture of the header the server packs. */
export function packWirePacket(opts: {
  flags: number;
  sequence: number;
  ptsUs: number;
  payload: Uint8Array;
}): Uint8Array {
  const out = new Uint8Array(WIRE_HEADER_BYTES + opts.payload.length);
  const view = new DataView(out.buffer);
  view.setUint8(0, WIRE_VERSION);
  view.setUint8(1, opts.flags & 0xff);
  view.setUint16(2, 0, true);
  view.setUint32(4, opts.sequence >>> 0, true);
  view.setFloat64(8, opts.ptsUs, true);
  out.set(opts.payload, WIRE_HEADER_BYTES);
  return out;
}

export function isOpusHead(payload: Uint8Array): boolean {
  return startsWith(payload, OPUS_HEAD);
}

export function isOpusTags(payload: Uint8Array): boolean {
  return startsWith(payload, OPUS_TAGS);
}

/** True for OpusHead and OpusTags even when the server forgot flags bit0. */
export function isOpusConfigPayload(payload: Uint8Array): boolean {
  return isOpusHead(payload) || isOpusTags(payload);
}

export interface OpusHeadInfo {
  version: number;
  channels: number;
  preSkip: number;
  inputSampleRate: number;
  outputGain: number;
  channelMappingFamily: number;
}

/** RFC 7845 identification header. Returns null if the magic or length is wrong. */
export function parseOpusHead(payload: Uint8Array): OpusHeadInfo | null {
  if (!isOpusHead(payload) || payload.length < 19) return null;
  const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  return {
    version: payload[8] ?? 0,
    channels: payload[9] ?? 0,
    preSkip: view.getUint16(10, true),
    inputSampleRate: view.getUint32(12, true),
    outputGain: view.getInt16(16, true),
    channelMappingFamily: payload[18] ?? 0,
  };
}

export type AudioRouteAction =
  | "configure-opus"
  | "ignore-config"
  | "decode-opus"
  | "play-pcm"
  | "drop";

export interface RoutedAudio {
  action: AudioRouteAction;
  ptsUs: number;
  /** Codec config bytes. For OpusHead this is the WebCodecs `description`. */
  description?: Uint8Array;
  frame?: Uint8Array;
  channels?: number;
  sampleRate?: number;
}

/**
 * Decide what an `/ws/audio` packet is.
 *
 * Order matters. OpusHead / OpusTags are config even if `flags` is 0
 * (the production bug). A flagged packet that is not those magics is
 * still config. Only then do we treat the payload as Opus or PCM.
 */
export function routeAudioPacket(
  header: WireHeader,
  codec: "opus" | "pcm" | "aac" | "unknown",
): RoutedAudio {
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
      sampleRate: 48000,
    };
  }
  if (isOpusTags(payload)) {
    return { action: "ignore-config", ptsUs, description: payload };
  }
  if (flagged) {
    return {
      action: "configure-opus",
      ptsUs,
      description: payload.byteLength ? payload : undefined,
      channels: 2,
      sampleRate: 48000,
    };
  }
  if (!payload.byteLength) return { action: "drop", ptsUs };
  if (codec === "pcm") return { action: "play-pcm", ptsUs, frame: payload, channels: 2, sampleRate: 48000 };
  if (codec === "aac") return { action: "drop", ptsUs };
  return { action: "decode-opus", ptsUs, frame: payload };
}

export interface AnnexBNal {
  /** H.264 nal_unit_type (low 5 bits of the first payload byte). */
  type: number;
  payload: Uint8Array;
}

/** Split an Annex-B access unit into NAL payloads, start codes removed. */
export function splitAnnexB(data: Uint8Array): AnnexBNal[] {
  const nalStarts: number[] = [];
  for (let i = 0; i + 3 < data.length; i++) {
    if (data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 1) {
      nalStarts.push(i + 3);
      i += 2;
      continue;
    }
    if (
      i + 4 < data.length &&
      data[i] === 0 &&
      data[i + 1] === 0 &&
      data[i + 2] === 0 &&
      data[i + 3] === 1
    ) {
      nalStarts.push(i + 4);
      i += 3;
    }
  }
  const out: AnnexBNal[] = [];
  for (let n = 0; n < nalStarts.length; n++) {
    const begin = nalStarts[n] ?? 0;
    const next = nalStarts[n + 1];
    let end = data.length;
    if (next != null) {
      end = next >= 4 && data[next - 4] === 0 && data[next - 3] === 0 && data[next - 2] === 0 && data[next - 1] === 1
        ? next - 4
        : next - 3;
    }
    if (end <= begin) continue;
    const payload = data.subarray(begin, end);
    out.push({ type: payload[0]! & 0x1f, payload });
  }
  return out;
}

export function annexBStartCodeLength(payload: Uint8Array): 0 | 3 | 4 {
  if (
    payload.length >= 4 &&
    payload[0] === 0 &&
    payload[1] === 0 &&
    payload[2] === 0 &&
    payload[3] === 1
  ) {
    return 4;
  }
  if (payload.length >= 3 && payload[0] === 0 && payload[1] === 0 && payload[2] === 1) return 3;
  return 0;
}

/** `avc1.42C029` from the SPS bytes the encoder actually sent. */
export function avcCodecString(sps: Uint8Array): string | null {
  if (sps.length < 4) return null;
  const hex = (b: number) => b.toString(16).toUpperCase().padStart(2, "0");
  return `avc1.${hex(sps[1] ?? 0)}${hex(sps[2] ?? 0)}${hex(sps[3] ?? 0)}`;
}

/**
 * ISO/IEC 14496-15 AVCDecoderConfigurationRecord.
 * WebCodecs on Safari wants this as `description`. Chrome accepts it too,
 * as long as the chunks are length-prefixed rather than Annex-B.
 */
export function buildAvcDecoderConfig(sps: Uint8Array, pps: Uint8Array): Uint8Array | null {
  if (sps.length < 4 || pps.length < 1) return null;
  const out = new Uint8Array(11 + sps.length + pps.length);
  out[0] = 1;
  out[1] = sps[1] ?? 0;
  out[2] = sps[2] ?? 0;
  out[3] = sps[3] ?? 0;
  out[4] = 0xff; // 4-byte NAL lengths
  out[5] = 0xe1; // one SPS
  out[6] = (sps.length >> 8) & 0xff;
  out[7] = sps.length & 0xff;
  out.set(sps, 8);
  let offset = 8 + sps.length;
  out[offset++] = 1; // one PPS
  out[offset++] = (pps.length >> 8) & 0xff;
  out[offset++] = pps.length & 0xff;
  out.set(pps, offset);
  return out;
}

/** Big-endian 4-byte lengths. This is the chunk format that pairs with avcC. */
export function lengthPrefixNals(nals: Uint8Array[]): Uint8Array {
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

const VCL_TYPES = new Set([1, 2, 3, 4, 5]);

export interface PreparedVideo {
  kind: "key" | "delta";
  ptsUs: number;
  /** Annex-B bytes, unchanged. Chromium can decode these with no description. */
  annexB: Uint8Array;
  /** Length-prefixed VCL NALs for the avcC path. Empty if this AU has none. */
  avccSample: Uint8Array;
  sps: Uint8Array | null;
  pps: Uint8Array | null;
  codec: string | null;
  description: Uint8Array | null;
}

/**
 * Turn one video access unit into both decode shapes.
 * The player prefers avcC (works on Safari and Chrome) and can fall
 * back to raw Annex-B if that decoder errors.
 */
export function prepareVideoAccessUnit(header: WireHeader): PreparedVideo | null {
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
    description: sps && pps ? buildAvcDecoderConfig(sps, pps) : null,
  };
}
