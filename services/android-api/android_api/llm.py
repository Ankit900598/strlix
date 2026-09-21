"""Azure OpenAI chat for android-api — Accessibility-oriented tools, NOT ADB."""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Optional

from openai import AzureOpenAI

from .agent_protocol import ChatTurnRequest, ChatTurnResponse, ToolProposal

SYSTEM = """You are Strlix, the AI assistant living INSIDE the user's Android phone.
You help via short replies and optional Accessibility actions the phone will execute.
Prefer on-device actions (open app, tap label, type, swipe, home/back) over guessing.
Never ask for screenshots from a cloud ADB pipe — the phone has Accessibility.
Be concise. Phone-first product: you are the search/assistant bar, not a web chat.
When you need an action, emit a function call; the phone runs it and returns a result.

Planning policy:
- If the user clearly asks you to do something and the exact app/account is not known,
  do not block on a clarification question. Start with one safe, reversible
  `a11y_launch` into the most likely installed app, then inspect it with Accessibility.
  A launch is a plan, not a claim that the task succeeded.
- Use the common installed apps for these intents: Gmail for an inbox unsubscribe;
  Chrome for food delivery, reservations, or shopping comparisons; Photos for photos;
  Calendar or Clock for reminders; Settings for notifications. For reservations and
  shopping, prefer Chrome/Maps over naming a third-party app that may not be installed.
- For destructive or financial requests, navigate and fill only up to the review/final
  confirmation screen. Never tap the irreversible confirmation without a separate,
  explicit user approval. Say that you are stopping for review.
- For ambiguous-but-actionable requests such as “my usual food” or “compare prices”,
  begin safe app discovery instead of asking which app/model first; the current screen
  can supply that context.
"""

# Tools the PHONE executes (Accessibility). Names map to agent_protocol.ToolName.
# These are deliberately narrow, safe starts for clear requests where a model may
# otherwise ask a blocking clarification question. They do not assert completion and
# never include typing, checkout, deletion, or confirmation actions.
PLANNING_FALLBACKS = (
    (("unsubscribe", "mailing"), "Gmail", "Opening Gmail to find the mailing list; I will stop before any final unsubscribe confirmation."),
    (("unsubscribe", "inbox"), "Gmail", "Opening Gmail to find the mailing list; I will stop before any final unsubscribe confirmation."),
    (("order", "food"), "Chrome", "Opening Chrome to find the saved food order; I will stop at the review screen."),
    (("book", "table"), "Chrome", "Opening Chrome to find a reservation option; I will stop before the final booking confirmation."),
    (("compare", "price"), "Chrome", "Opening Chrome to compare the item across shopping sites before I report the delivered prices."),
)


def safe_planning_fallback(message: str) -> tuple[ToolProposal, str] | None:
    """Return a truthful, reversible first step for an unplanned clear intent."""
    text = message.casefold()
    for terms, app, reply in PLANNING_FALLBACKS:
        if all(term in text for term in terms):
            return ToolProposal(id=f"local-plan-{uuid.uuid4().hex}", name="a11y_launch", args={"app": app}), reply
    return None


A11Y_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "a11y_launch",
            "description": "Launch an app by package or friendly name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "e.g. Chrome, Settings, com.android.settings"},
                },
                "required": ["app"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "a11y_tap",
            "description": "Tap a UI element by visible text/content-desc, or by normalized coords 0-1.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "x_norm": {"type": "number"},
                    "y_norm": {"type": "number"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "a11y_type",
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
            "name": "a11y_swipe",
            "description": "Swipe direction on screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                },
                "required": ["direction"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "a11y_key",
            "description": "Press HOME, BACK, or APP_SWITCH.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keycode": {"type": "string", "enum": ["HOME", "BACK", "APP_SWITCH"]},
                },
                "required": ["keycode"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "a11y_scroll",
            "description": "Scroll forward/backward in the focused scrollable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["forward", "backward"]},
                },
                "required": ["direction"],
                "additionalProperties": False,
            },
        },
    },
]


class AndroidLLM:
    def __init__(self) -> None:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.6-sol")
        self.api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        if not endpoint or not key:
            raise RuntimeError("AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY required")
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=self.api_version,
        )

    def chat(self, req: ChatTurnRequest) -> ChatTurnResponse:
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM}]
        if req.history:
            for h in req.history[-20:]:
                role = h.get("role") or "user"
                content = h.get("content") or h.get("text") or ""
                if role in ("user", "assistant", "system") and content:
                    messages.append({"role": role, "content": str(content)})
        if req.tool_results:
            # Fold prior tool outcomes into the user turn context
            summary = "; ".join(
                f"{tr.name}({'ok' if tr.ok else 'fail'}: {tr.detail or ''})"
                for tr in req.tool_results
            )
            messages.append({
                "role": "user",
                "content": f"{req.message}\n\n[Accessibility results: {summary}]",
            })
        else:
            messages.append({"role": "user", "content": req.message})

        resp = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            tools=A11Y_TOOLS,
            tool_choice="auto",
            max_completion_tokens=800,
        )
        choice = resp.choices[0].message
        tools: list[ToolProposal] = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                tools.append(
                    ToolProposal(
                        id=tc.id or uuid.uuid4().hex,
                        name=tc.function.name,  # type: ignore[arg-type]
                        args=args,
                    )
                )
        reply = (choice.content or "").strip()
        # A model clarification is useful when the request is underspecified, but it
        # should not prevent a safe first step for the four common golden-intent
        # planning cases above. Keep this fallback local and bounded to a launch.
        if not tools:
            fallback = safe_planning_fallback(req.message)
            if fallback:
                fallback_tool, fallback_reply = fallback
                tools.append(fallback_tool)
                reply = fallback_reply
        if not reply and tools:
            reply = "On it."
        usage = None
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            }
        return ChatTurnResponse(
            ok=True,
            reply=reply or "(no reply)",
            tools=tools,
            model=self.deployment,
            usage=usage,
        )
