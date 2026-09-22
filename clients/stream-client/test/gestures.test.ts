import assert from "node:assert/strict";
import { test } from "node:test";
import { ContactBook, gestureFromContact, wheelToSwipe } from "../src/gestures.ts";

const start = { id: 1, x: 100, y: 200, clientX: 10, clientY: 20, t: 1000 };

test("a short press is a tap at the finger-down point", () => {
  const gesture = gestureFromContact(start, 12, 22, 1100, { x: 140, y: 260 });
  assert.deepEqual(gesture, { kind: "tap", x: 100, y: 200 });
});

test("a drag is a swipe whose duration is the hold time", () => {
  const gesture = gestureFromContact(start, 80, 20, 1250, { x: 400, y: 200 });
  assert.equal(gesture.kind, "swipe");
  if (gesture.kind !== "swipe") return;
  assert.equal(gesture.x1, 100);
  assert.equal(gesture.x2, 400);
  assert.equal(gesture.durationMs, 250);
});

test("two fingers produce two independent gestures", () => {
  const book = new ContactBook();
  book.begin({ id: 1, x: 10, y: 10, clientX: 1, clientY: 1, t: 0 });
  book.begin({ id: 2, x: 90, y: 90, clientX: 50, clientY: 50, t: 5 });
  assert.equal(book.size, 2);
  const first = book.end(1, 2, 2, 40, () => ({ x: 11, y: 11 }));
  const second = book.end(2, 90, 50, 80, () => ({ x: 200, y: 90 }));
  assert.equal(first?.kind, "tap");
  assert.equal(second?.kind, "swipe");
  assert.equal(book.size, 0);
  assert.equal(book.end(3, 0, 0, 0, () => null), null);
});

test("wheel down swipes the finger up the screen", () => {
  const swipe = wheelToSwipe({ x: 500, y: 1000 }, 0, 40, 1080, 2400);
  assert.ok(swipe);
  assert.equal(swipe?.y2, 820);
  assert.equal(swipe?.x2, 500);
});
