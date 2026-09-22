import assert from "node:assert/strict";
import { test } from "node:test";
import { clientToDevice, fitContain } from "../src/coords.ts";

test("a tap in the middle of the painted picture is the middle of the phone", () => {
  const point = clientToDevice(150, 400, { left: 50, top: 0, width: 200, height: 800 }, 1080, 2400);
  assert.deepEqual(point, { x: 540, y: 1200 });
});

test("encoder-sized canvas still maps to device pixels", () => {
  // Picture is drawn at 484×1080 css px, phone is 1080×2400.
  const point = clientToDevice(484, 1080, { left: 0, top: 0, width: 484, height: 1080 }, 1080, 2400);
  assert.deepEqual(point, { x: 1079, y: 2399 });
});

test("clicks far outside the picture are ignored, edge slack is kept", () => {
  const painted = { left: 10, top: 10, width: 100, height: 200 };
  assert.equal(clientToDevice(0, 0, painted, 100, 200, 0), null);
  const near = clientToDevice(10, 9, painted, 100, 200, 40);
  assert.deepEqual(near, { x: 0, y: 0 });
});

test("fitContain letterboxes a tall phone inside a wide window", () => {
  const box = fitContain(1000, 500, 1080, 2400);
  assert.ok(Math.abs(box.height - 500) < 0.01);
  assert.ok(box.width < 1000);
  assert.ok(box.left > 0);
  assert.equal(box.top, 0);
});
