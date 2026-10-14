"""Short-term memory: shared scratchpad for one pipeline run.

Subagents in the SDK do not share context windows, so the orchestrator hands
off *artifacts* between stages through RunState rather than raw transcripts.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StageResult:
    stage: str
    output: str
    started_at: float
    finished_at: float
    cost_usd: float = 0.0

    @property
    def duration_s(self) -> float:
        return round(self.finished_at - self.started_at, 3)


@dataclass
class RunState:
    ticket: dict[str, Any]
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stages: dict[str, StageResult] = field(default_factory=dict)
    scratch: dict[str, Any] = field(default_factory=dict)
    tool_calls: int = 0
    total_cost_usd: float = 0.0

    def record(self, stage: str, output: str, started_at: float, cost_usd: float = 0.0) -> None:
        self.stages[stage] = StageResult(stage, output, started_at, time.time(), cost_usd)
        self.total_cost_usd += cost_usd

    def get(self, stage: str, default: str = "") -> str:
        r = self.stages.get(stage)
        return r.output if r else default

    def context_for(self, *stages: str) -> str:
        """Render prior stage outputs as a compact hand-off block."""
        parts = [f"## {s}\n{self.get(s)}" for s in stages if s in self.stages]
        return "\n\n".join(parts)

    def to_json(self) -> str:
        return json.dumps(
            {
                "run_id": self.run_id,
                "ticket": self.ticket,
                "stages": {k: asdict(v) for k, v in self.stages.items()},
                "tool_calls": self.tool_calls,
                "total_cost_usd": round(self.total_cost_usd, 6),
            },
            indent=2,
        )
