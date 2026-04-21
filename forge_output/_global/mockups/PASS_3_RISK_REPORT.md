# Pass 3 deep-risk report

**Date:** 2026-04-19 · **Auditor:** deep-risk (Explore agent)
**Scope:** 5 Pass 3 mockups (3 task-deliverable variants + 2 auditor surfaces)

## Summary

- **High risks: 3** (must address before production)
- **Medium risks: 5** (should address in Pass 4)
- **Low risks: 2** (note for future)

**Categorical hotspots:**
1. **Pass 2 HIGH#4 partially mitigated** — 4-verdict structure + forensic capture added, but evidence enforcement is UI-side; no API-level authenticity validation.
2. **Asymmetric AC scope** — analysis/planning/documentation tasks can surface unsourced ("INVENTED") AC without a hard block before they propagate downstream.
3. **Evidence authenticity not validated** — file hashes captured but never verified on read; PASSED_ATTESTATION verdict has no re-check trigger.
4. **External-auditor surface area** — file-preview links labeled "read-only" but enforcement is client-side; assign-auditor (Pass 2) promised scope is not visibly enforced in auditor-review.
5. **Verdict permanence overstated** — typed-name "signature" is ceremonial, not cryptographic; no override audit trail described.

**Single most dangerous risk + mitigation:**

**Risk:** `05v2-auditor-review.html` lines 393–397 explicitly state "Forge does NOT validate evidence authenticity." For HIPAA / SOC2 acceptance criteria, an auditor uploading a screenshot or log file with no post-submission verification is treated as prima facie evidence. If the auditor account is compromised — or the auditor simply pastes plausible-looking 200-character text + uploads a stale screenshot — Forge has no detection mechanism, and 6 months later during a real compliance audit the chain breaks.

**Mitigation:** (A) S3 object-lock (write-once-read-many) on uploaded files; (B) link evidence to a specific git commit hash captured at submit time so a future verifier can replay the artifact; (C) optional GPG-signed attestation for HIGH-severity AC; (D) introduce a `REQUIRES_REVALIDATION` lifecycle for `PASSED_ATTESTATION` verdicts that auto-reopens after N days for HIPAA/SOC2-tagged AC.

---

## High risks (must address)

### HIGH#1. Evidence Authenticity Unverified in PASSED_WITH_EVIDENCE
**Mockup:** `05v2-auditor-review.html` lines 320–397
**Dimensions:** Hidden state, contract violation, audit failure, privacy/auth

The verdict form requires ≥1 file OR ≥200 chars of text and stores SHA256 hashes + IP + UA + Forge-service-key signature on the audit log. But: (a) hashes are stored, never re-checked on display; (b) uploaded files are not made immutable; (c) text-only evidence has only a length floor — an auditor can paste 200 chars of plausible filler ("Verified per logs in production environment on 2026-04-19, output matched expected pattern from spec section 4.2…") with no semantic gate; (d) no link to the git commit hash of the code under audit, so 6 months later the file the verdict referenced may not match the file the regulator inspects.

**Mitigation:** Object-lock storage; capture `code_commit_hash` at submit time; semantic check on text evidence (require references to file paths or AC fragments); make the hash visible + re-verifiable in `auditor-review` history view; flag mismatched hashes loudly.

### HIGH#2. Invented AC / Unsourced Claims Accepted Without Hard Block
**Mockups:** `05v2-analysis-deliverable.html` (AC list with "INVENTED" badge) + `05v2-documentation-deliverable.html` (unsourced paragraphs flagged)
**Dimensions:** Skeptical-UX violation, hidden state, downstream contract violation

Analysis tasks can output AC marked "INVENTED" (no source citation), and the deliverable lets the user "Approve all AC" with the INVENTED ones included — they then propagate into the planning task and become contracts the develop tasks must satisfy. Same pattern: documentation deliverable flags 2 unsourced paragraphs but allows freeze-and-publish without resolution. The skeptical-UX counterweight surfaces the gap, but doesn't block it.

**Mitigation:** Hard block on "Approve all" while any AC carries `source_status = INVENTED`; require either a citation or an explicit downgrade-to-decision (forces a Q-NNN to capture the assumption); same pattern for unsourced doc paragraphs — block freeze, require citation or `(Pending: O-NNN)` placeholder.

### HIGH#3. PASSED_ATTESTATION Verdict Has No Re-Check Mechanism
**Mockup:** `05v2-auditor-review.html` lines 254–286 (PASSED_ATTESTATION variant)
**Dimensions:** Hidden state, audit failure, time-decay risk

The PASSED_ATTESTATION variant is correctly tagged "auditor sign-off, no artifact" with a skeptical-UX warning, but once submitted the verdict is permanent and equivalent (in objective KR roll-up) to PASSED_WITH_EVIDENCE. For HIPAA/SOC2 AC this is wrong: attestation should carry a TTL and auto-reopen for re-verification on a schedule, otherwise the compliance posture silently rots.

**Mitigation:** Distinguish three persistence classes: PASSED_WITH_EVIDENCE (permanent), PASSED_ATTESTATION (REQUIRES_REVALIDATION, auto-reopen at 90/180 days for HIPAA/SOC2-tagged AC), PASSED_PROVISIONAL (short TTL). Surface on objective dashboard "AC verified by attestation only — N days to revalidation."

---

## Medium risks (should address)

### MED#1. File-Preview Scope Not Enforced at API Level
**Mockup:** `05v2-auditor-review.html` (file preview links to source-preview / code files)
**Dimensions:** Privacy/auth, scope creep, contract violation

Auditor (jpatel@acme.com — external email) gets read-only links to code files via `02v2-source-preview.html`. The UI labels these "read-only" and assign-auditor (Pass 2) promised scope was limited to specific AC. But there's no annotation showing the API enforces `auditor.scope = AC.ids` at request time — it's described as a UI affordance only. An external auditor who probes URLs could traverse to other files. **Fix:** annotate the preview links with `?assignment_id=...&scope_check=enforced`; document the server-side authz check in the data-source panel; reject preview requests outside the assigned AC scope with 403 + audit log entry.

### MED#2. Artifact Regeneration Has No Lock / Versioning
**Mockup:** `05v2-documentation-deliverable.html` (Regenerate buttons on artifacts; ADR-001 included)
**Dimensions:** Concurrency, recoverability, hidden state

The deliverable shows "Regenerate" actions on individual artifacts, but ADR-001 should be append-only (decision records are immutable by convention) and there's no version pin or lock indication if two users regenerate at once. **Fix:** disable regenerate on `kind=ADR`; show `version_n` + `last_regenerated_at` per artifact; optimistic lock via `artifact_version` + 409 on stale write; offer "view diff vs previous" before commit.

### MED#3. NEEDS_CLARIFICATION Has No Timeout
**Mockups:** `05v2-auditor-review.html` (NEEDS_CLARIFICATION verdict spawns Q-NNN) + `05v2-auditor-inbox.html`
**Dimensions:** Round-trip risk, blocked work

NEEDS_CLARIFICATION creates a decision Q-NNN waiting on the original assigner. If the assigner is unavailable, the AC stays unverified indefinitely and the parent objective cannot ACHIEVE. The inbox shows OOO for the auditor but no equivalent escalation when the question recipient is OOO. **Fix:** 7-day SLA on NEEDS_CLARIFICATION questions with auto-escalation to project owner; surface "questions waiting on you N days" in the assigner's home dashboard.

### MED#4. Analysis Ambiguity Escalation Blocks But Doesn't Prioritize
**Mockup:** `05v2-analysis-deliverable.html` (6 ambiguities, 2 escalated)
**Dimensions:** Confusion, hidden cost

When 2 ambiguities are escalated to user, all are presented equally — but one may block 8 downstream tasks while another blocks 1. No priority signal. User answers in arrival order, not impact order. **Fix:** show downstream-blocked-task-count per ambiguity; sort by impact descending; show est-cost-of-delay per ambiguity.

### MED#5. Planning Task Fanout Risk Not Hard-Blocked
**Mockup:** `05v2-planning-deliverable.html` (12 develop tasks + 1 doc task drafted; cost estimate visible)
**Dimensions:** Cost runaway, late-discovery

Planning deliverable shows estimated_llm_cost per task and aggregate, but only as informational — there is no project-level cap that blocks "Approve plan" if aggregate exceeds budget envelope. Big-bang plans pass through. **Fix:** project-level `plan_cost_cap_usd`; block approve-plan above cap; require `--force` with reason; show diff vs prior plan if re-planning.

---

## Low risks (note)

### LOW#1. Deliverable Status Ambiguity (DONE vs DONE_WITH_CONCERNS)
**Mockups:** All 3 deliverable variants
The challenger-review section flags concerns but the task header status remains "DONE" — no visual signal that the task was closed despite challenger findings. **Fix:** introduce `DONE_WITH_CONCERNS` status; render distinctly in objective dashboard.

### LOW#2. Auditor Inbox History Has No Recency Bias
**Mockup:** `05v2-auditor-inbox.html` (history filter)
The history list shows past assignments but the filter doesn't default to "last 30 days" — auditors with hundreds of past assignments will scroll forever. **Fix:** default filter `completed_at >= now() - interval '30 days'`; add quick filters (this week / this month / all).

---

## Cross-cutting patterns

### Evidence-handling pattern (auditor-review + analysis + documentation)
All three surfaces capture "evidence" of varying form (file uploads, source citations, paragraph footnotes), but none verify that evidence persists in usable form across time. **Unified fix:** Evidence-Persistence template — every artifact-bearing surface stores `(content_hash, code_commit_hash, captured_at, immutable_storage_url)` and re-verifies on read.

### Skeptical-UX counterweight pattern (all 5 mockups)
Counterweight is present and well-formed (6 gaps each), but is treated as informational. Some gaps (INVENTED AC, unsourced doc, attestation-only verdict) should be **blocking**, not just visible. **Unified fix:** classify each counterweight item as `informational | warning | blocking`; render blocking items as red and require explicit override with reason.

### Approval finality pattern (planning approve, doc freeze, verdict submit)
All three "final" actions can be reversed in code (re-plan, unfreeze, override-verdict) but the UI presents them as terminal. Users may be surprised when finance audit later finds a verdict was overridden silently. **Unified fix:** every final action writes to an immutable `final_actions_log` with reason + actor + before-state hash.

---

## Skeptical-UX contract scoring

Scale 0–3 per: **(a)** counterweight visible · **(b)** primary action conservatively named · **(c)** reversibility/impact previewed.

| Mockup | (a) | (b) | (c) | Total | Status |
|---|---|---|---|---|---|
| 05v2-analysis-deliverable | 3 | 2 | 2 | **7/9** | OK — but INVENTED AC needs hard block |
| 05v2-planning-deliverable | 3 | 2 | 2 | **7/9** | OK — needs cost-cap hard block |
| 05v2-documentation-deliverable | 3 | 2 | 1 | **6/9** | Borderline — unsourced paragraphs flagged but not blocked |
| **05v2-auditor-inbox** | 3 | 3 | 2 | **8/9** | **Best** — clear, conservative, reversible |
| 05v2-auditor-review | 3 | 2 | 1 | **6/9** | Borderline — verdict permanence overstated; evidence not verified |

**Average: 6.8/9.** Mockups <6/9 (require redesign): 0. Mockups at 6/9 (borderline, fix in Pass 4): 2.

---

## Status check on Pass 2 HIGH risks

| Pass 2 risk | Status after Pass 3 |
|---|---|
| H#1 KB folder PII (sensitive-file ingest) | **UNCHANGED** — Pass 3 didn't touch KB ingest surface |
| H#2 Scenario-gen no gas gauge (cost runaway) | **UNCHANGED** — Pass 3 didn't touch scenario-gen |
| H#3 Close-task deferred-findings circuit-breaker | **UNCHANGED** — Pass 3 didn't touch close-task |
| **H#4 Manual AC stores verdict without evidence** | **PARTIAL (≈60% mitigated)** — verdict types + forensic capture are real wins, but evidence not authenticity-validated, attestation has no TTL, signatures are ceremonial |

Pass 3 explicitly targeted H#4 and made meaningful structural progress, but introduced **3 new HIGH risks** (HIGH#1–#3 above) that are downstream of the same root cause: evidence is *captured* but not *verified*. Net HIGH-risk count: Pass 2 left 4 HIGHs open; Pass 3 closed 0, partially mitigated 1, opened 3 → **6 HIGHs open** going into Pass 4.

---

## Recommendations by priority

**Before shipping Pass 3:**
1. Add hard block on "Approve all AC" while INVENTED AC present (HIGH#2).
2. Introduce `PASSED_ATTESTATION` TTL + auto-revalidation for HIPAA/SOC2 AC (HIGH#3).
3. Add `code_commit_hash` capture on every verdict submit (HIGH#1 partial).

**In Pass 4 (highest leverage):**
1. S3 object-lock + immutable-storage URLs on all uploaded evidence (HIGH#1).
2. Auditor scope enforcement annotation + server-side check on file-preview links (MED#1).
3. Artifact versioning + lock on documentation regenerate (MED#2).
4. Project-level plan-cost cap (MED#5).
5. NEEDS_CLARIFICATION 7-day SLA with escalation (MED#3).
6. Carry forward Pass 2 unaddressed HIGHs (KB PII, scenario-gen cost, close-task circuit-breaker).

**Total assessment:** Pass 3 is **safe to prototype with caveats**. The auditor loop is now end-to-end (assign → inbox → review), the 4-verdict structure is a real evidence-chain improvement over Pass 2, and the deliverable shell extends cleanly to all 4 task types (DEVELOP, ANALYSIS, PLANNING, DOC). But the same skeptical-UX contract that calls out gaps does not always *block* on them — three new HIGH risks (HIGH#1–#3) are all variants of "Forge surfaces the gap, then lets the user proceed anyway." Pass 4 should focus on converting the strongest counterweight items from informational to blocking, and on making evidence cryptographically verifiable end-to-end.
