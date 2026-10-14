"""Custom tools exposed to agents through an in-process MCP server.

Tool handlers are plain functions (`*_impl`) so tests can call them directly;
the `@tool` wrappers adapt them to the SDK.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import CONFIG
from .memory import LongTermMemory, VectorMemory

SERVER_NAME = "opsforge"


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


# --- implementations ----------------------------------------------------------
def search_logs_impl(log_path: Path, service: str, keyword: str = "", limit: int = 20) -> str:
    if not log_path.exists():
        return "No log file found."
    out = []
    for line in log_path.read_text().splitlines():
        if service.lower() in line.lower() and keyword.lower() in line.lower():
            out.append(line)
    return "\n".join(out[-limit:]) or "No matching log lines."


def service_metrics_impl(service: str) -> str:
    # Stub: replace with Prometheus/Datadog queries in a real deployment.
    fake = {
        "checkout-api": {"error_rate": 0.18, "p99_ms": 31000, "db_pool_active": 50, "db_pool_max": 50},
        "payments-worker": {"error_rate": 0.01, "p99_ms": 240},
    }
    return json.dumps(fake.get(service, {"note": "no metrics for service"}))


def recall_impl(vm: VectorMemory, query: str, k: int = 3) -> str:
    hits = vm.search(query, k=k)
    if not hits:
        return "No similar past incidents."
    return "\n\n---\n\n".join(f"[{doc_id}] score={score:.2f}\n{text[:700]}" for doc_id, score, text in hits)


def save_incident_impl(ltm: LongTermMemory, vm: VectorMemory, title: str, symptom: str, root_cause: str, fix: str, lesson: str = "") -> str:
    path = ltm.save_incident(title, symptom, root_cause, fix)
    vm.upsert(f"incident:{path.stem}", path.read_text())
    vm.save()
    if lesson:
        ltm.add_lesson(lesson)
    return f"Saved incident to {path.name}"


# --- SDK wiring ---------------------------------------------------------------
def build_mcp_server(ltm: LongTermMemory, vm: VectorMemory, log_path: Path | None = None):
    """Create the in-process MCP server. Imported lazily so the rest of the
    package (memory, harness) works without the SDK installed."""
    from claude_agent_sdk import create_sdk_mcp_server, tool

    log_path = log_path or CONFIG.root / "data" / "logs" / "sample.log"

    @tool("search_logs", "Search service logs by service name and optional keyword.", {"service": str, "keyword": str})
    async def search_logs(args):
        return _text(search_logs_impl(log_path, args["service"], args.get("keyword", "")))

    @tool("get_service_metrics", "Get current metrics for a service.", {"service": str})
    async def get_service_metrics(args):
        return _text(service_metrics_impl(args["service"]))

    @tool("recall_similar_incidents", "Semantic search over past incidents and service notes.", {"query": str})
    async def recall_similar_incidents(args):
        return _text(recall_impl(vm, args["query"]))

    @tool(
        "save_incident",
        "Persist a resolved incident and an optional durable lesson to long-term memory.",
        {"title": str, "symptom": str, "root_cause": str, "fix": str, "lesson": str},
    )
    async def save_incident(args):
        return _text(
            save_incident_impl(ltm, vm, args["title"], args["symptom"], args["root_cause"], args["fix"], args.get("lesson", ""))
        )

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="0.1.0",
        tools=[search_logs, get_service_metrics, recall_similar_incidents, save_incident],
    )


def tool_names(*names: str) -> list[str]:
    return [f"mcp__{SERVER_NAME}__{n}" for n in names]
