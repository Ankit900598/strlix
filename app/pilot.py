"""Azure OpenAI tool-calling phone pilot."""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Optional

from openai import AzureOpenAI

from .adb_client import AdbClient, AdbError

SYSTEM_PROMPT = """You are Zevi Cloud Phone Pilot — an assistant that controls an Android cloud phone via ADB tools.
You can take screenshots, tap, type, swipe, and send keys.
When the user asks what is on screen or to open something, ALWAYS take a screenshot first, look at it, then act.
Be concise. After actions, take another screenshot if useful to confirm.
Coordinates are in pixels relative to the device screen (use wm size / screenshot orientation).
Prefer HOME key to go home, and tap visible icons.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "adb_screenshot",
            "description": "Capture the current Android screen. Returns a PNG image you can see.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adb_tap",
            "description": "Tap at pixel coordinates (x, y).",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                },
                "required": ["x", "y"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adb_type",
            "description": "Type text into the focused field.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adb_swipe",
            "description": "Swipe from (x1,y1) to (x2,y2).",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "integer"},
                    "y1": {"type": "integer"},
                    "x2": {"type": "integer"},
                    "y2": {"type": "integer"},
                    "duration_ms": {"type": "integer", "default": 300},
                },
                "required": ["x1", "y1", "x2", "y2"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adb_key",
            "description": "Send a keyevent. Use HOME, BACK, ENTER, DEL, APP_SWITCH, or a numeric keycode.",
            "parameters": {
                "type": "object",
                "properties": {"keycode": {"type": "string"}},
                "required": ["keycode"],
                "additionalProperties": False,
            },
        },
    },
]


class PhonePilot:
    def __init__(self, adb: Optional[AdbClient] = None):
        self.adb = adb or AdbClient()
        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.6-sol")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=api_version,
        )
        self.max_rounds = int(os.environ.get("PILOT_MAX_ROUNDS", "8"))

    async def _exec_tool(self, name: str, args: dict) -> tuple[str, Optional[dict]]:
        """Returns (text_result, optional screenshot dict with base64)."""
        try:
            if name == "adb_screenshot":
                shot = await self.adb.screenshot()
                return (
                    json.dumps({"ok": True, "path": shot["path"], "bytes": shot["bytes"]}),
                    shot,
                )
            if name == "adb_tap":
                return json.dumps(await self.adb.tap(args["x"], args["y"])), None
            if name == "adb_type":
                return json.dumps(await self.adb.type_text(args["text"])), None
            if name == "adb_swipe":
                return json.dumps(
                    await self.adb.swipe(
                        args["x1"], args["y1"], args["x2"], args["y2"], args.get("duration_ms", 300)
                    )
                ), None
            if name == "adb_key":
                return json.dumps(await self.adb.key(args["keycode"])), None
            return json.dumps({"ok": False, "error": f"unknown tool {name}"}), None
        except AdbError as e:
            return json.dumps({"ok": False, "error": str(e)}), None
        except Exception as e:  # noqa: BLE001
            return json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), None

    async def chat(self, user_message: str, history: Optional[list] = None) -> dict[str, Any]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        tool_trace: list[dict[str, Any]] = []
        screenshots: list[dict[str, Any]] = []
        final_text = ""

        for _ in range(self.max_rounds):
            resp = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            choice = resp.choices[0]
            msg = choice.message

            if msg.tool_calls:
                # Append assistant tool-call message
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments or "{}",
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )
                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    text_result, shot = await self._exec_tool(name, args)
                    tool_trace.append({"tool": name, "args": args, "result": text_result[:500]})
                    content_parts: Any
                    if shot and shot.get("base64"):
                        screenshots.append({"path": shot["path"], "bytes": shot["bytes"]})
                        # Vision: send image back to the model
                        content_parts = [
                            {"type": "text", "text": text_result},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{shot['base64']}",
                                },
                            },
                        ]
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": content_parts,
                            }
                        )
                    else:
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": text_result,
                            }
                        )
                continue

            final_text = msg.content or ""
            messages.append({"role": "assistant", "content": final_text})
            break
        else:
            final_text = final_text or "(stopped after max tool rounds)"

        # History for client (strip bulky images)
        slim_history = []
        for m in messages:
            if m.get("role") == "system":
                continue
            if m.get("role") == "tool" and isinstance(m.get("content"), list):
                slim_history.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.get("tool_call_id"),
                        "content": "[screenshot omitted]",
                    }
                )
            else:
                slim_history.append(m)

        return {
            "reply": final_text,
            "tools": tool_trace,
            "screenshots": [{"path": s["path"], "bytes": s["bytes"]} for s in screenshots],
            "history": slim_history[-20:],
        }
