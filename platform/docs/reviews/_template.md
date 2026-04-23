# Review Record — [document name]

**Reviewer:** [email / handle / "separate Claude session [session-id]"]
**Date:** YYYY-MM-DD
**Document reviewed:** [`../path/to/doc.md`](../path/to/doc.md) — version / commit hash
**Review scope:** [full | §N–§M | mechanical-only | rationale-only]
**Estimated time:** X min actual (Y min claimed by doc header — flag divergence)

---

## Sections read

- [ ] §0
- [ ] §1
- [ ] §2
- ...

(check = fully read, not skimmed. Leave unchecked if skipped; then add a SKIP BLOCK below.)

### SKIP BLOCK (if any)

```
Skipped: §N
Reason: [why — e.g., "out of scope for this review", "deferred to reviewer X"]
Residual risk: [what we might miss by skipping]
```

---

## Questions raised

*Minimum 3 for full review, or explicit "fewer because ..." skip block.*

1. **Q:** [question about specific claim]
   **Location:** §N paragraph P, or file:line
   **Resolution:** [author answer | "unresolved — blocks ratification"]

2. **Q:** ...

3. **Q:** ...

---

## Claims challenged

*List any claim you tested and found (a) incorrect, (b) overstated, (c) under-evidenced.*

| Claim (verbatim) | Location | Challenge | Resolution |
|---|---|---|---|
| "..." | §N | [why you challenged] | [author response + evidence] |

If no claims challenged: **explain why** (document is trivial? well-grounded? reviewer low-confidence?).

---

## Evidence re-verified by reviewer

*This is the point of peer review — YOU verified the claim, not accepted the author's citation.*

| Author's citation | Reviewer's re-verification | Match? |
|---|---|---|
| `file.py:42 — function X does Y` | `$ grep -n ...` → [actual output] | ✓ / ✗ |
| `75 status mutations` | `$ rg --count '\.status\s*=' platform/app` → [actual count] | ✓ / ✗ |
| `scenario_type enum has 4 values` | `Read task.py:86-88` → [actual constraint] | ✓ / ✗ |

Minimum 5 re-verifications for full review. Less = reviewer admits low-depth review; document stays DRAFT.

---

## Additional findings

*Things the author did not raise but reviewer discovered.*

- [ ] Finding 1: [description]
- [ ] Finding 2: [description]

These become new rows in [`../DEEP_RISK_REGISTER.md`](../DEEP_RISK_REGISTER.md) or new Findings per `contract_validator` pattern.

---

## Ratification verdict

**ACCEPT** | **ACCEPT-WITH-CHANGES** | **REJECT**

### If ACCEPT
- Document status transitions DRAFT → PEER-REVIEWED.
- One more review (or Steward sign-off) required for NORMATIVE.

### If ACCEPT-WITH-CHANGES
Required changes (author addresses before status transitions):
1. ...
2. ...

After author addresses, reviewer confirms → PEER-REVIEWED.

### If REJECT
Document stays DRAFT. Author addresses reject reasons via new version.

---

## Reviewer epistemic state

Tag your confidence in this review (per CONTRACT §B.2):

- `[CONFIRMED]` sections where you re-verified with runtime evidence or direct citation.
- `[ASSUMED]` sections where you read but did not independently test.
- `[UNKNOWN]` sections where you lack domain competence (per CONTRACT §B.7 competence boundary — name what you don't know, don't guess).

Overall review confidence: [0-100%]. If <70%, flag another reviewer needed.

---

## Record filing

- File name: `review-<doc-basename>-by-<reviewer>-<YYYY-MM-DD>.md`.
- Commit to `platform/docs/reviews/`.
- PR references the doc reviewed.
- Update [`../README.md`](../README.md) status table + [`../decisions/README.md`](../decisions/README.md) index if ADR.
