"""Stage runner: executes one agent role as a single SDK query with the
harness wrapped around it (hooks, tracing, retry, cost accounting)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..agents import AgentSpec
from ..config import Config
from ..memory import RunState
from .guardrails import Guardrails
from .retry import retry_async
from .tracing import Tracer


@dataclass
class StageOutcome:
    text: str
    cost_usd: float
    turns: int
    is_error: bool


class StageRunner:
    def __init__(self, config: Config, tracer: Tracer, guardrails: Guardrails, mcp_server: Any, workdir: Path):
        self.config = config
        self.tracer = tracer
        self.guardrails = guardrails
        self.mcp_server = mcp_server
        self.workdir = workdir

    def _options(self, spec: AgentSpec):
        from claude_agent_sdk import ClaudeAgentOptions, HookMatcher
        from ..tools import SERVER_NAME

        return ClaudeAgentOptions(
            system_prompt=spec.system_prompt,
            model=spec.model or self.config.model,
            cwd=str(self.workdir),
            setting_sources=["project"],  # loads .claude/skills from cwd
            allowed_tools=list(spec.tools),
            mcp_servers={SERVER_NAME: self.mcp_server},
            max_turns=self.config.max_turns,
            hooks={
                "PreToolUse": [HookMatcher(hooks=[self.guardrails.pre_tool_use])],
                "PostToolUse": [HookMatcher(hooks=[self.guardrails.post_tool_use])],
            },
        )

    async def run(self, spec: AgentSpec, prompt: str, state: RunState) -> StageOutcome:
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, query

        async def attempt() -> StageOutcome:
            started = time.time()
            self.tracer.event("stage_start", stage=spec.name)
            chunks: list[str] = []
            cost, turns, is_error = 0.0, 0, False
            async for msg in query(prompt=prompt, options=self._options(spec)):
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            chunks.append(block.text)
                elif isinstance(msg, ResultMessage):
                    cost = msg.total_cost_usd or 0.0
                    turns = msg.num_turns
                    is_error = msg.is_error
            text = "".join(chunks).strip()
            if is_error or not text:
                raise RuntimeError(f"stage {spec.name} produced no usable output")
            self.tracer.event("stage_end", stage=spec.name, cost_usd=cost, turns=turns, secs=round(time.time() - started, 2))
            return StageOutcome(text, cost, turns, is_error)

        outcome = await retry_async(
            attempt,
            attempts=3,
            on_retry=lambda n, e: self.tracer.event("retry", stage=spec.name, attempt=n, error=str(e)),
        )
        state.total_cost_usd += outcome.cost_usd
        if state.total_cost_usd > self.config.max_budget_usd:
            self.tracer.event("budget_exceeded", spent=state.total_cost_usd)
            raise RuntimeError(f"Run budget exceeded: ${state.total_cost_usd:.2f} > ${self.config.max_budget_usd:.2f}")
        return outcome
