"""Agent tool protocol for on-device Accessibility (no ADB screencap).

The Android app runs gestures locally via ZeviAccessibilityService and reports
results here. The LLM on the host proposes high-level tools; the phone executes.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


ToolName = Literal[
    "a11y_tap",
    "a11y_swipe",
    "a11y_type",
    "a11y_key",
    "a11y_launch",
    "a11y_scroll",
    "local_done",
]


class ToolProposal(BaseModel):
    """Host → phone: proposed Accessibility action (phone executes)."""
    id: str
    name: ToolName
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Phone → host: outcome of an Accessibility action."""
    id: str
    name: ToolName
    ok: bool
    detail: Optional[str] = None
    elapsed_ms: Optional[int] = None


class ChatTurnRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: Optional[list[dict[str, Any]]] = None
    language: Optional[str] = None
    # Results from tools the phone already ran (multi-turn agent loop)
    tool_results: Optional[list[ToolResult]] = None
    device_id: Optional[str] = None


class ChatTurnResponse(BaseModel):
    ok: bool = True
    reply: str
    # If non-empty, phone should run these via Accessibility then POST results
    tools: list[ToolProposal] = Field(default_factory=list)
    model: Optional[str] = None
    usage: Optional[dict[str, Any]] = None
