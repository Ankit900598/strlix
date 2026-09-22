import assert from "node:assert/strict";
import { test } from "node:test";
import {
  annexBStartCodeLength,
  avcCodecString,
  buildAvcDecoderConfig,
  isOpusConfigPayload,
  lengthPrefixNals,
  parseOpusHead,
  parseWirePacket,
  prepareVideoAccessUnit,
  routeAudioPacket,
  splitAnnexB,
} from "../src/protocol.ts";

function bytes(hex: string): Uint8Array {
  const clean = hex.replace(/\s+/g, "");
  const out = new Uint8Array(clean.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = Number.parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  return out;
}

test("golden header matches Python struct <BBHId", () => {
  // python: struct.Struct("<BBHId").pack(1, 1, 0, 7, 48000.0) + b"OpusHead"
  const raw = bytes("0101000007000000000000000070e7404f70757348656164");
  const header = parseWirePacket(raw);
  assert.ok(header);
  assert.equal(header.version, 1);
  assert.equal(header.flags, 1);
  assert.equal(header.sequence, 7);
  assert.equal(header.ptsUs, 48000);
  assert.equal(new TextDecoder().decode(header.payload), "OpusHead");
});

test("short and unknown-version packets are ignored", () => {
  assert.equal(parseWirePacket(new Uint8Array(15)), null);
  const bad = new Uint8Array(16);
  bad[0] = 2;
  assert.equal(parseWirePacket(bad), null);
});

test("OpusHead and OpusTags are config even when flags are 0", () => {
  // flags=0 on purpose. Payload is a real OpusHead (RFC 7845), 48 kHz stereo.
  const head = parseWirePacket(
    bytes("010000000900000000000000000000004f707573486561640102780180bb0000000000"),
  );
  assert.ok(head);
  assert.equal(head.flags, 0);
  assert.equal(isOpusConfigPayload(head.payload), true);
  const routed = routeAudioPacket(head, "opus");
  assert.equal(routed.action, "configure-opus");
  assert.equal(routed.channels, 2);
  assert.equal(routed.sampleRate, 48000);
  const info = parseOpusHead(head.payload);
  assert.ok(info);
  assert.equal(info.channels, 2);
  assert.equal(info.inputSampleRate, 48000);
  assert.equal(info.preSkip, 0x0178);

  // python pack of flags=0 seq=9 pts=123456.5 + b"OpusTags\x00"
  const tags = parseWirePacket(bytes("0100000009000000000000000824fe404f7075735461677300"));
  assert.ok(tags);
  assert.equal(tags.ptsUs, 123456.5);
  assert.equal(routeAudioPacket(tags, "opus").action, "ignore-config");
});

test("flagged config is config, and a normal opus packet is decoded", () => {
  const flagged = parseWirePacket(new Uint8Array([1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x01, 0x02]));
  assert.ok(flagged);
  assert.equal(routeAudioPacket(flagged, "opus").action, "configure-opus");

  const frame = parseWirePacket(new Uint8Array([1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xfc, 0x01]));
  assert.ok(frame);
  const routed = routeAudioPacket(frame, "opus");
  assert.equal(routed.action, "decode-opus");
  assert.deepEqual(Array.from(routed.frame ?? []), [0xfc, 0x01]);
});

test("pcm codec plays raw samples and aac is dropped", () => {
  const packet = parseWirePacket(new Uint8Array([1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x00, 0x01]));
  assert.ok(packet);
  assert.equal(routeAudioPacket(packet, "pcm").action, "play-pcm");
  assert.equal(routeAudioPacket(packet, "aac").action, "drop");
});

test("annex-B keyframe becomes avcC + length-prefixed IDR", () => {
  const annex = bytes("000000016742c0290000000168ee3c8000000001658884");
  assert.equal(annexBStartCodeLength(annex), 4);
  const nals = splitAnnexB(annex);
  assert.deepEqual(nals.map((n) => n.type), [7, 8, 5]);
  const sps = nals[0]!.payload;
  assert.equal(avcCodecString(sps), "avc1.42C029");
  const avcC = buildAvcDecoderConfig(sps, nals[1]!.payload);
  assert.ok(avcC);
  assert.equal(avcC[0], 1);
  assert.equal(avcC[1], 0x42);
  assert.equal(avcC[2], 0xc0);
  assert.equal(avcC[3], 0x29);
  assert.deepEqual(Array.from(lengthPrefixNals([nals[2]!.payload])), [0, 0, 0, 3, 0x65, 0x88, 0x84]);

  const header = parseWirePacket(
    new Uint8Array([1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...annex]),
  );
  assert.ok(header);
  const prepared = prepareVideoAccessUnit(header);
  assert.ok(prepared);
  assert.equal(prepared.kind, "key");
  assert.equal(prepared.codec, "avc1.42C029");
  assert.ok(prepared.description);
  assert.deepEqual(Array.from(prepared.avccSample), [0, 0, 0, 3, 0x65, 0x88, 0x84]);
});

test("a delta frame stays a delta and 3-byte start codes split", () => {
  const annex = bytes("00000161e00020");
  const header = parseWirePacket(new Uint8Array([1, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...annex]));
  assert.ok(header);
  const prepared = prepareVideoAccessUnit(header);
  assert.ok(prepared);
  assert.equal(prepared.kind, "delta");
  assert.equal(prepared.sps, null);
  assert.equal(splitAnnexB(annex)[0]?.type, 1);
});
