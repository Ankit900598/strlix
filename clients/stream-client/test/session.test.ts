import assert from "node:assert/strict";
import { test } from "node:test";
import { StrlixSession, streamEndpoints, type StrlixSocket } from "../src/session.ts";

class FakeSocket implements StrlixSocket {
  static sockets: FakeSocket[] = [];
  readyState = 0;
  binaryType = "";
  sent: string[] = [];
  onopen: ((ev?: unknown) => void) | null = null;
  onmessage: ((ev: { data: unknown }) => void) | null = null;
  onclose: ((ev: { code?: number; reason?: string }) => void) | null = null;
  onerror: ((ev?: unknown) => void) | null = null;
  url: string;
  constructor(url: string) {
    this.url = url;
    FakeSocket.sockets.push(this);
  }
  send(data: string): void {
    this.sent.push(data);
  }
  close(): void {
    this.readyState = 3;
    this.onclose?.({ code: 1000, reason: "client" });
  }
  push(data: unknown): void {
    this.onmessage?.({ data });
  }
}

test("https stream base becomes wss sockets and http input", () => {
  const urls = streamEndpoints("https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/");
  assert.equal(urls.videoSocket, "wss://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/ws/h264");
  assert.equal(urls.audioSocket, "wss://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/ws/audio");
  assert.equal(urls.tap, "https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/adb/tap");
  assert.throws(() => streamEndpoints("not a url"));
});

test("session pongs, parses video, and posts a tap", async () => {
  FakeSocket.sockets = [];
  const posts: { url: string; body: string }[] = [];
  const session = new StrlixSession(
    "https://phone.example",
    (url) => new FakeSocket(url),
    async (url, init) => {
      posts.push({ url, body: init?.body ?? "" });
      return { ok: true, status: 200, json: async () => ({ ok: true }) };
    },
  );
  const packets: number[] = [];
  const hellos: string[] = [];
  const socket = session.openVideo({
    onHello: (msg) => hellos.push(String(msg.codec)),
    onPacket: (header) => packets.push(header.sequence),
  });
  assert.equal(socket.url, "wss://phone.example/ws/h264");
  socket.readyState = 1;
  (socket as FakeSocket).push(JSON.stringify({ type: "ping", t: 1 }));
  (socket as FakeSocket).push(JSON.stringify({ type: "hello", codec: "avc1.42C029" }));
  assert.deepEqual(JSON.parse((socket as FakeSocket).sent[0] ?? "{}"), { type: "pong" });
  assert.deepEqual(hellos, ["avc1.42C029"]);

  const au = new Uint8Array(20);
  au[0] = 1;
  au[4] = 3;
  (socket as FakeSocket).push(au.buffer);
  assert.deepEqual(packets, [3]);

  session.requestKeyframe();
  assert.equal(JSON.parse((socket as FakeSocket).sent[1] ?? "{}").type, "keyframe");

  await session.tap(12, 34);
  assert.equal(posts[0]?.url, "https://phone.example/adb/tap");
  assert.deepEqual(JSON.parse(posts[0]?.body ?? "{}"), { x: 12, y: 34 });
  session.close();
});
