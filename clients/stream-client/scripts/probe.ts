/**
 * Connect to a live Strlix stream and print how the shared client
 * classifies the first packets. Does not send taps.
 *
 *   npm run probe
 *   npm run probe -- https://your-host
 */
import {
  SOFT_LAUNCH_STREAM,
  StrlixSession,
  prepareVideoAccessUnit,
  routeAudioPacket,
} from "../src/index.ts";

const base = process.argv[2] || SOFT_LAUNCH_STREAM;
const session = new StrlixSession(base);
let video = 0;
let audio = 0;
let finished = false;

function finish(): void {
  if (finished) return;
  finished = true;
  console.log(`counts video=${video} audio=${audio}`);
  session.close();
  process.exit(0);
}

console.log(`probing ${base}`);
session.openVideo({
  onHello: (msg) => {
    console.log(
      `video hello codec=${String(msg.codec)} device=${String(msg.device_width)}x${String(msg.device_height)} source=${String(msg.source ?? "")}`,
    );
  },
  onPacket: (header) => {
    video += 1;
    if (video <= 4) {
      const prepared = prepareVideoAccessUnit(header);
      console.log(
        `video seq=${header.sequence} flags=${header.flags} kind=${prepared?.kind ?? "unparsed"} codec=${prepared?.codec ?? "-"} bytes=${header.payload.byteLength} avcc=${prepared?.avccSample.byteLength ?? 0}`,
      );
    }
    if (video >= 12) finish();
  },
  onClose: (code, reason) => console.log(`video close ${code} ${reason}`),
});

session.openAudio({
  onHello: (msg) => console.log(`audio hello source=${String(msg.source)} codec=${String(msg.codec)} reason=${String(msg.reason ?? "")}`),
  onText: (msg) => {
    if (msg.type === "ping" || msg.type === "hello") return;
    console.log(`audio ${String(msg.type)} source=${String(msg.source ?? "")} reason=${String(msg.reason ?? "")}`);
  },
  onPacket: (header) => {
    audio += 1;
    if (audio <= 6) {
      const routed = routeAudioPacket(header, "opus");
      const magic = new TextDecoder().decode(header.payload.subarray(0, 8));
      console.log(`audio seq=${header.sequence} flags=${header.flags} action=${routed.action} magic=${JSON.stringify(magic)} bytes=${header.payload.byteLength}`);
    }
  },
  onClose: (code, reason) => console.log(`audio close ${code} ${reason}`),
});

setTimeout(() => {
  console.log("probe window elapsed");
  finish();
}, 12000);
