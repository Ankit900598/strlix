/**
 * Desktop keyboard → the key names `POST /adb/key` already understands.
 *
 * `app/adb_client.py` maps HOME, BACK, ENTER, DEL, RECENTS, and a few
 * others to Android keycodes, and forwards anything else to
 * `input keyevent`. `KEYCODE_DPAD_*` works on that path. Printable
 * ASCII goes to `POST /adb/type`, which is how a cursor-driven desktop
 * session types into the focused Android field.
 */

export type KeyAction =
  | { type: "key"; keycode: string }
  | { type: "text"; text: string }
  | { type: "ignore" };

export interface KeyInput {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  alt?: boolean;
}

export function keyboardToDevice(input: KeyInput): KeyAction {
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
