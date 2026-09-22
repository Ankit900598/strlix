import assert from "node:assert/strict";
import { test } from "node:test";
import { keyboardToDevice } from "../src/keys.ts";

test("cursor keys become android keys and letters become text", () => {
  assert.deepEqual(keyboardToDevice({ key: "Escape" }), { type: "key", keycode: "BACK" });
  assert.deepEqual(keyboardToDevice({ key: "Enter" }), { type: "key", keycode: "ENTER" });
  assert.deepEqual(keyboardToDevice({ key: "Backspace" }), { type: "key", keycode: "DEL" });
  assert.deepEqual(keyboardToDevice({ key: "ArrowLeft" }), { type: "key", keycode: "KEYCODE_DPAD_LEFT" });
  assert.deepEqual(keyboardToDevice({ key: "a" }), { type: "text", text: "a" });
  assert.deepEqual(keyboardToDevice({ key: "A" }), { type: "text", text: "A" });
});

test("shortcuts are not typed into the phone", () => {
  assert.deepEqual(keyboardToDevice({ key: "c", ctrl: true }), { type: "ignore" });
  assert.deepEqual(keyboardToDevice({ key: "v", meta: true }), { type: "ignore" });
  assert.deepEqual(keyboardToDevice({ key: "F5" }), { type: "ignore" });
});
