"""Central configuration. Everything tunable lives here."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    root: Path = ROOT
    # Where Claude Code-style skills live (cwd/.claude/skills/<name>/SKILL.md).
    skills_dir: Path = ROOT / ".claude" / "skills"
    # Long-term, file-based memory (human-readable markdown).
    memory_dir: Path = ROOT / "memory_store"
    # Vector index persisted as JSON.
    vector_path: Path = ROOT / "memory_store" / "vector_index.json"
    # Traces (one JSONL file per run).
    trace_dir: Path = ROOT / "traces"

    model: str = os.getenv("OPSFORGE_MODEL", "claude-sonnet-5-5")
    max_turns: int = int(os.getenv("OPSFORGE_MAX_TURNS", "25"))
    # Per-run budget guardrail (USD). The harness aborts when exceeded.
    max_budget_usd: float = float(os.getenv("OPSFORGE_MAX_BUDGET_USD", "1.00"))
    # Max tool calls per run, enforced by a PreToolUse hook.
    max_tool_calls: int = int(os.getenv("OPSFORGE_MAX_TOOL_CALLS", "40"))
    # Shell commands containing any of these are denied.
    blocked_command_patterns: tuple[str, ...] = field(
        default=(
            "rm -rf",
            "mkfs",
            "dd if=",
            ":(){",
            "shutdown",
            "reboot",
            "curl | sh",
            "curl | bash",
            "chmod -R 777",
            "> /dev/sd",
        )
    )


CONFIG = Config()
