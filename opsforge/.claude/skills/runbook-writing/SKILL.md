---
name: runbook-writing
description: Turn an investigation result into a remediation plan and a short incident write-up. Use after root cause is known, or when the cause is unknown and a safe interim plan is needed.
---

# Remediation planning

## Plan structure
1. **Immediate mitigation**: smallest safe action that stops the bleeding, with a rollback step.
2. **Permanent fix**: the change that removes the root cause.
3. **Verification**: concrete checks (metric, log line, health endpoint) proving the fix worked.
4. **Follow-ups**: monitoring or alert gaps worth closing.

## Output format
```
mitigation:
- <step> (rollback: <step>)
fix:
- <step>
verification:
- <check>
followups:
- <item>
lesson: <one durable sentence worth remembering for future incidents>
```

## Rules
- Every mutating step must have a rollback.
- Flag any step that needs human approval with `[NEEDS APPROVAL]`.
- The `lesson` line must be general enough to apply beyond this one ticket.
