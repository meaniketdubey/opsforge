---
name: incident-investigation
description: Investigate the root cause of a dev/ops incident using logs, metrics, runbooks and past incidents. Use after triage when needs_investigation is true.
---

# Incident investigation

## Method
1. **Recall first.** Call `recall_similar_incidents` with the symptom. If a past incident matches strongly, test that hypothesis before any others.
2. **Gather evidence.** Use `search_logs` with the service name and error keywords; call `get_service_metrics` for the service. Prefer 2-3 targeted queries over broad ones.
3. **Form hypotheses.** List at most three, ranked by likelihood, each tied to specific evidence.
4. **Discriminate.** Pick the cheapest check that separates the top two hypotheses and run it.
5. **Conclude** with a root cause and a confidence level (`high`, `medium`, `low`). If confidence is low, say what additional data is needed instead of guessing.

## Output format
```
root_cause: <statement>
confidence: high|medium|low
evidence:
- <log line or metric, with source>
hypotheses_rejected:
- <hypothesis>: <why>
```

## Rules
- Read-only. Never restart services, change config, or write files during investigation.
- Quote evidence verbatim from tool output; do not paraphrase log lines.
