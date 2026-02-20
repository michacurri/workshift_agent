# Product Context

## Why This Project Exists

Operations and scheduling teams receive shift-change requests in natural language (chat, email, forms). Manually interpreting and validating them is slow and error-prone. This project provides a single system that:

1. **Understands** free-form requests (LLM extraction when user pastes text).
2. **Validates** them against business rules (deterministic engine).
3. **Routes** by type: swaps need partner consent first, then admin approval; coverage requests stay with the employee until admin fills the shift; moves go to admin.
4. **Gates** changes behind human approval (partner and/or admin) and keeps a clear audit trail.

## Problems It Solves

- **Ambiguity:** "Swap John Tuesday to Wednesday" or "I need coverage for my night shift" → system extracts employee, dates, shift types, and action; returns a human-readable summary.
- **Consistency:** Same rules for everyone (skills, certs, conflicts); no ad-hoc decisions.
- **Accountability:** Coverage = employee remains responsible until admin assigns someone; no automatic release.
- **Partner clarity:** Swap partner sees what they would give and take, plus workload (e.g. shifts this week) before accepting or rejecting.
- **Admin focus:** Urgent items (<48h to shift start) surface at top with visual highlight; coverage fill via eligible candidate list and one-click assign.
- **Vendor lock-in:** LLM can be local (Ollama) or hosted via config; structured-only flow works without LLM.

## How It Should Work

1. **Employee:** Opens Shiftboard (default). Types or pastes in single input, clicks Preview; if something is missing (e.g. date), UI asks for that one thing and shows prefilled draft; user completes and submits. Can also open "Review details" to edit structured fields. Clicks owned shift to "Request coverage" (pre-fills cover). Submits → request created with correct status (pending_partner for swap, pending_fill for coverage, pending_admin for move).
2. **Partner (swap):** Sees request in Consents tab; reads summary and workload; Accept (sends to admin) or Reject (closes as partner_rejected).
3. **Admin:** Approvals tab shows pending and pending_admin with urgent first; approve/reject. My Requests shows all requests; for pending_fill with coverage_shift_id, "Fill coverage" → list of eligible candidates → Assign to close the request and assign the shift.
4. **Everyone:** My Requests shows own and (for partner) consent-needed items, with status and summary; urgent highlighted.

## User Experience Goals

- **Shiftboard:** Primary entry; **single input** "Describe your request (or paste a message)" + Preview; summary shown first; when info is missing, UI shows targeted prompts (e.g. "What date?") and prefilled draft instead of a dead-end error; "Review details" (structured form) optional; request coverage by clicking owned shift.
- **Consents:** Clear summary and workload; one-click Accept/Reject.
- **My Requests:** List with status and summary; admin sees Fill coverage flow for pending_fill.
- **Approvals:** Pending list with summary; urgent (<48h) at top and highlighted; approve/reject.
- **Errors:** API returns errorCode, userMessage, developerMessage, correlationId. Preview does not 400 for missing fields; returns needsInput for guided completion.

## Edge Cases the Product Handles

- Employee not in DB → RULE_EMPLOYEE_NOT_FOUND. Expired cert → RULE_CERT_EXPIRED. Skill mismatch → RULE_SKILL_MISMATCH. Shift conflict → RULE_CONFLICT with suggestions.
- Duplicate submit → Idempotent; return existing request.
- Approve/reject twice → 409 APPROVAL_NOT_PENDING. Partner consent on wrong request → 403/409.
- Coverage fill: only eligible candidates (skills, certs, no conflict) listed; assign updates shift and marks request approved.
