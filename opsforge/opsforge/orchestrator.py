"""Pipeline orchestrator.

triage -> (investigate if needed) -> plan -> review -> [revise once] -> persist

Sequencing lives in Python on purpose: control flow is deterministic and
testable, while the judgment inside each stage is the model's. Stages pass
artifacts via RunState, not raw transcripts.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from .agents import INVESTIGATOR, PLANNER, REVIEWER, TRIAGE
from .config import CONFIG, Config
from .harness.guardrails import Guardrails
from .harness.runner import StageRunner
from .harness.tracing import Tracer
from .memory import LongTermMemory, RunState, VectorMemory
from .tools import build_mcp_server


def parse_kv(text: str, key: str, default: str = "") -> str:
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else default


def ticket_block(ticket: dict) -> str:
    return f"Ticket {ticket.get('id', '?')}: {ticket.get('title', '')}\n\n{ticket.get('body', '')}"


class Orchestrator:
    def __init__(self, config: Config = CONFIG, workdir: Path | None = None):
        self.config = config
        self.workdir = Path(workdir or config.root)
        self.ltm = LongTermMemory(config.memory_dir)
        self.vm = VectorMemory(config.vector_path)
        if len(self.vm) == 0:
            self.vm.reindex(self.ltm.all_documents())

    async def run(self, ticket: dict) -> RunState:
        state = RunState(ticket=ticket)
        tracer = Tracer(self.config.trace_dir, state.run_id)
        guardrails = Guardrails(self.config, tracer, self.workdir)
        runner = StageRunner(self.config, tracer, guardrails, build_mcp_server(self.ltm, self.vm), self.workdir)
        tracer.event("run_start", ticket_id=ticket.get("id"))

        lessons = "\n".join(f"- {l}" for l in self.ltm.lessons()) or "(none yet)"
        header = f"{ticket_block(ticket)}\n\nTeam lessons from past incidents:\n{lessons}"

        # 1. triage
        t0 = time.time()
        triage = await runner.run(TRIAGE, header, state)
        state.record("triage", triage.text, t0)
        needs_investigation = parse_kv(triage.text, "needs_investigation", "true").lower().startswith("t")
        service = parse_kv(triage.text, "service", "unknown")

        # 2. investigate (conditional)
        if needs_investigation:
            t0 = time.time()
            prompt = f"{header}\n\n# Triage result\n{triage.text}\n\nInvestigate service: {service}"
            inv = await runner.run(INVESTIGATOR, prompt, state)
            state.record("investigation", inv.text, t0)
        else:
            tracer.event("stage_skipped", stage="investigation")

        # 3. plan, 4. review (with one revision pass)
        feedback = ""
        for attempt in range(2):
            t0 = time.time()
            prompt = f"{header}\n\n{state.context_for('triage', 'investigation')}"
            if feedback:
                prompt += f"\n\n# Reviewer feedback to address\n{feedback}"
            plan = await runner.run(PLANNER, prompt, state)
            state.record("plan", plan.text, t0)

            t0 = time.time()
            review_prompt = f"{ticket_block(ticket)}\n\n{state.context_for('triage', 'investigation', 'plan')}"
            review = await runner.run(REVIEWER, review_prompt, state)
            state.record("review", review.text, t0)
            verdict = parse_kv(review.text, "verdict", "REVISE").upper()
            tracer.event("review_verdict", attempt=attempt, verdict=verdict)
            if verdict.startswith("APPROVE"):
                break
            feedback = review.text
        state.scratch["approved"] = verdict.startswith("APPROVE")

        # 5. persist what was learned
        self._persist(state)
        tracer.event("run_end", approved=state.scratch["approved"], cost_usd=round(state.total_cost_usd, 4))
        state.scratch["trace_path"] = str(tracer.path)
        return state

    def _persist(self, state: RunState) -> None:
        """Deterministic memory write-back, only for approved plans."""
        if not state.scratch.get("approved"):
            return
        inv = state.get("investigation")
        root_cause = parse_kv(inv, "root_cause", "unknown") if inv else "not investigated"
        lesson = parse_kv(state.get("plan"), "lesson")
        path = self.ltm.save_incident(
            title=state.ticket.get("title", "untitled"),
            symptom=state.ticket.get("body", ""),
            root_cause=root_cause,
            fix=state.get("plan"),
            tags=[parse_kv(state.get("triage"), "service", "unknown"), parse_kv(state.get("triage"), "category", "")],
        )
        self.vm.upsert(f"incident:{path.stem}", path.read_text())
        self.vm.save()
        if lesson:
            self.ltm.add_lesson(lesson)
