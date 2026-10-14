"""Agent role definitions. Each role = prompt + skill(s) + allowed tools."""

from __future__ import annotations

from dataclasses import dataclass

from .tools import tool_names


@dataclass(frozen=True)
class AgentSpec:
    name: str
    description: str
    system_prompt: str
    skills: tuple[str, ...]
    tools: tuple[str, ...]  # fully qualified tool names (plus built-ins)
    model: str | None = None  # None -> config default


TRIAGE = AgentSpec(
    name="triage",
    description="Classifies tickets by severity, category and service.",
    system_prompt=(
        "You are the triage agent in an ops team. Use the `ticket-triage` skill and follow its output "
        "format exactly. Be decisive and brief."
    ),
    skills=("ticket-triage",),
    tools=("Skill", *tool_names("recall_similar_incidents")),
)

INVESTIGATOR = AgentSpec(
    name="investigator",
    description="Finds root cause using logs, metrics and past incidents (read-only).",
    system_prompt=(
        "You are the investigation agent. Use the `incident-investigation` skill. You are strictly "
        "read-only: gather evidence, test hypotheses, and report a root cause with confidence."
    ),
    skills=("incident-investigation",),
    tools=("Skill", *tool_names("search_logs", "get_service_metrics", "recall_similar_incidents")),
)

PLANNER = AgentSpec(
    name="planner",
    description="Writes mitigation, fix, verification and follow-ups.",
    system_prompt=(
        "You are the remediation planner. Use the `runbook-writing` skill. Plans must be safe, "
        "reversible, and verifiable. Flag anything needing human approval."
    ),
    skills=("runbook-writing",),
    tools=("Skill", *tool_names("recall_similar_incidents")),
)

REVIEWER = AgentSpec(
    name="reviewer",
    description="Independently critiques the plan against the evidence.",
    system_prompt=(
        "You are a skeptical senior SRE reviewing a colleague's remediation plan. You have not seen the "
        "investigation process, only its conclusions. Check that every claim is supported by evidence, "
        "every mutating step has a rollback, and nothing risky is unflagged.\n\n"
        "Respond in exactly this format:\n"
        "verdict: APPROVE|REVISE\n"
        "issues:\n- <issue> (or 'none')"
    ),
    skills=(),
    tools=(),
)

ALL_AGENTS = {a.name: a for a in (TRIAGE, INVESTIGATOR, PLANNER, REVIEWER)}


def to_sdk_definitions():
    """Optional: expose roles as native SDK subagents for a lead-agent delegation mode."""
    from claude_agent_sdk import AgentDefinition

    return {
        a.name: AgentDefinition(description=a.description, prompt=a.system_prompt, tools=list(a.tools), model=a.model)
        for a in ALL_AGENTS.values()
    }
