---
name: ticket-triage
description: Classify an incoming dev/ops ticket by severity, category and owning service, and decide whether it needs investigation. Use at the start of any ticket handling.
---

# Ticket triage

## Steps
1. Read the ticket title, body, and reporter-supplied logs.
2. Assign **severity**:
   - `SEV1`: customer-facing outage or data loss.
   - `SEV2`: major degradation, workaround exists.
   - `SEV3`: minor bug or single-user impact.
   - `SEV4`: question, request, or cosmetic.
3. Assign **category**: `outage`, `performance`, `bug`, `config`, `security`, `request`.
4. Name the **service** most likely involved (use `recall_similar_incidents` if unsure).
5. Decide `needs_investigation: true|false`. Anything SEV1/SEV2 or with an unknown cause needs it.

## Output format (strict)
Return exactly this block, nothing else:

```
severity: SEV#
category: <category>
service: <service>
needs_investigation: true|false
rationale: <one or two sentences>
```

## Rules
- Security-flavoured tickets (credentials, exposed data) are at least SEV2.
- Never guess a service name you cannot justify; write `unknown` instead.
