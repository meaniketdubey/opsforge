"""Structured tracing: one JSONL file per run, one event per line."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class Tracer:
    def __init__(self, trace_dir: Path, run_id: str):
        self.path = Path(trace_dir) / f"{run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id

    def event(self, kind: str, **data: Any) -> None:
        rec = {"ts": round(time.time(), 3), "run_id": self.run_id, "kind": kind, **data}
        with self.path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]

    def summary(self) -> dict:
        events = self.read()
        kinds: dict[str, int] = {}
        for e in events:
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        return {"run_id": self.run_id, "events": len(events), "by_kind": kinds}
