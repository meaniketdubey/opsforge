"""CLI: python -m opsforge.cli run data/tickets/sample.json"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .config import CONFIG
from .harness.tracing import Tracer
from .memory import LongTermMemory, VectorMemory


def main() -> None:
    ap = argparse.ArgumentParser(prog="opsforge")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Run the pipeline on a ticket JSON file")
    r.add_argument("ticket", type=Path)

    s = sub.add_parser("recall", help="Search long-term memory")
    s.add_argument("query")

    sub.add_parser("reindex", help="Rebuild the vector index from memory files")

    t = sub.add_parser("trace", help="Summarise a run trace")
    t.add_argument("run_id")

    args = ap.parse_args()

    if args.cmd == "run":
        from .orchestrator import Orchestrator

        ticket = json.loads(args.ticket.read_text())
        state = asyncio.run(Orchestrator().run(ticket))
        print(state.get("plan"))
        print(f"\napproved={state.scratch['approved']} cost=${state.total_cost_usd:.4f} trace={state.scratch['trace_path']}")
    elif args.cmd == "recall":
        vm = VectorMemory(CONFIG.vector_path)
        for doc_id, score, text in vm.search(args.query):
            print(f"[{score:.2f}] {doc_id}\n{text[:300]}\n")
    elif args.cmd == "reindex":
        ltm = LongTermMemory(CONFIG.memory_dir)
        vm = VectorMemory(CONFIG.vector_path)
        vm.reindex(ltm.all_documents())
        print(f"Indexed {len(vm)} documents")
    elif args.cmd == "trace":
        print(json.dumps(Tracer(CONFIG.trace_dir, args.run_id).summary(), indent=2))


if __name__ == "__main__":
    main()
