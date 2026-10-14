# OpsForge

A multi-agent dev/ops triage system on the Claude Agent SDK (Python). It takes a ticket, triages it, investigates root cause, writes a remediation plan, has an independent reviewer critique it, and writes what it learned back to memory.

## Architecture

```
ticket -> triage -> (investigate?) -> plan -> review --APPROVE--> persist to memory
                                        ^        |
                                        +-REVISE-+  (one revision pass)
```

| Layer | Where | What it does |
|---|---|---|
| Agents | `opsforge/agents.py` | Four roles: prompt + skill + least-privilege tool list |
| Skills | `.claude/skills/*/SKILL.md` | Procedures and strict output formats, loaded via `setting_sources=["project"]` |
| Tools | `opsforge/tools.py` | In-process MCP server: logs, metrics, recall, save |
| Orchestrator | `opsforge/orchestrator.py` | Deterministic Python control flow; stages hand off artifacts, not transcripts |
| Harness | `opsforge/harness/` | Guardrail hooks, JSONL tracing, retry/backoff, cost budget |
| Short-term memory | `memory/run_state.py` | Per-run shared state |
| Long-term memory | `memory/long_term.py` | Markdown incidents, lessons, service notes (source of truth) |
| Vector memory | `memory/vector.py` | Similarity recall; dependency-free hashing embedder, swappable via `Embedder` |

## Run

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python -m opsforge.cli run data/tickets/sample.json
python -m opsforge.cli recall "database connection timeout"
python -m opsforge.cli trace <run_id>
pytest
```

## Design notes
- Guardrails are SDK hooks, so they hold even if the model ignores instructions.
- The reviewer sees conclusions only, not the investigation process, to avoid self-grading.
- Memory is written only for approved plans, by deterministic code rather than the model.
- Investigator and reviewer have no write tools.
