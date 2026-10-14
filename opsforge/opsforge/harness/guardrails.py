"""Guardrails implemented as SDK PreToolUse / PostToolUse hooks.

Hooks run in the harness process, outside the model's control, so they hold
even if a prompt is ignored or injected. Three policies:

1. Block dangerous shell commands.
2. Cap total tool calls per run.
3. Keep file writes inside the project's output directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import Config
from .tracing import Tracer


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


class Guardrails:
    def __init__(self, config: Config, tracer: Tracer, workdir: Path):
        self.config = config
        self.tracer = tracer
        self.workdir = Path(workdir).resolve()
        self.tool_calls = 0

    # --- pure decision logic (unit-testable without the SDK) -------------
    def check_command(self, command: str) -> str | None:
        low = command.lower()
        for pat in self.config.blocked_command_patterns:
            if pat in low:
                return f"Command blocked by guardrail (matched '{pat}')."
        return None

    def check_path(self, path: str) -> str | None:
        p = (self.workdir / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        try:
            p.relative_to(self.workdir)
        except ValueError:
            return f"Write outside project directory is not allowed: {p}"
        return None

    def check_budget(self) -> str | None:
        if self.tool_calls > self.config.max_tool_calls:
            return f"Tool-call budget exhausted ({self.config.max_tool_calls})."
        return None

    # --- SDK hook callbacks ----------------------------------------------
    async def pre_tool_use(self, input_data: dict, tool_use_id: str | None, context: Any) -> dict[str, Any]:
        self.tool_calls += 1
        name = input_data.get("tool_name", "")
        args = input_data.get("tool_input", {}) or {}
        self.tracer.event("tool_call", tool=name, args=args, n=self.tool_calls)

        reason = self.check_budget()
        if not reason and name == "Bash":
            reason = self.check_command(str(args.get("command", "")))
        if not reason and name in {"Write", "Edit"}:
            reason = self.check_path(str(args.get("file_path", "")))

        if reason:
            self.tracer.event("guardrail_denied", tool=name, reason=reason)
            return _deny(reason)
        return {}

    async def post_tool_use(self, input_data: dict, tool_use_id: str | None, context: Any) -> dict[str, Any]:
        resp = str(input_data.get("tool_response", ""))
        self.tracer.event("tool_result", tool=input_data.get("tool_name"), preview=resp[:300])
        return {}
