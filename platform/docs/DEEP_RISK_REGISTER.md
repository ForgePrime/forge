# Forge Platform — Deep Risk Register

> **Status:** LIVING document. Audit findings 2026-04-23. Update when risks change, close, or new ones surface. Own risks need ADRs when mitigation is non-trivial.

**Scoring:** Composite = P + I + R + D (range 4–20).
- **P** Probability (1-5)
- **I** Impact (1-5)
- **R** Reversibility cost (1-5, 5 = IRREVERSIBLE)
- **D** Detectability (1-5, 5 = silent / undetected)

**Thresholds:** ≥18 CRITICAL · 15–17 HIGH · 11–14 MEDIUM · <11 LOW.

**Status legend:** OPEN · MITIGATING · ACCEPTED · CLOSED · WATCHING.

---

## Summary

| Level | Count | IDs |
|---|---|---|
| CRITICAL | 2 | R-FW-02, R-GOV-01 |
| HIGH | 6 | R-SPEC-03, R-GOV-02, R-GAP-02, R-SPEC-05, R-PLAN-05, R-FW-04 |
| MEDIUM | 17 | R-SPEC-01, R-PLAN-03, R-IRR-03, R-GOV-03, R-PLAN-01, R-FW-03, R-IRR-02, R-OP-02, R-FW-01, R-GAP-01, R-OP-01, R-IRR-01, R-PLAN-04, R-SPEC-02, R-SPEC-04, R-PLAN-02 |
| LOW | 4 | R-HAL-01, R-GAP-03, R-HAL-02, R-OP-03 |

Total: **29 risks** identified in deep-risk audit 2026-04-23.

**Phase-agnostic risks** (apply to all phases): R-GOV-01, R-GOV-02, R-SPEC-05, R-SPEC-03.

---

## CRITICAL

### R-FW-02 — Stage 0 Data Classification policy-only + IRREVERSIBLE leak path

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 5 | 5 | 5 | 4 | **19** | MITIGATING |

**Description.** OPERATING_MODEL §2 honesty statement is explicit: *"any engineer with direct access to an AI tool can bypass the gate (copy-paste, screenshot, ad-hoc upload)"*. Forge Phase G1 `DataClassification` entity is a policy marker — not technical enforcement. A Confidential leak via ad-hoc channel is IRREVERSIBLE: client data in vendor training corpus cannot be unleaked.

**Blast radius.** Legal exposure (Client IP, GDPR breach notifications), contractual breach, insurance claim impact, reputational damage persistent.

**Applicable phase.** G (G.1 Stage 0 Data Classification Gate).

**Mitigation (in progress).**
- CHANGE_PLAN_v2 §13.3 G1 escalated with mandatory adoption preconditions: DLP or signed acceptance that Forge is Public/Internal-only until DLP deployed.
- FRAMEWORK_MAPPING §12 flagged as R-FW-02 non-waivable.
- UI banner required on Confidential+ ingest without DLP.
- Steward quarterly audit + kill-criteria trigger on ≥ 1 leak.

**Owner.** Platform + Security + Framework Steward.

**Residual risk after mitigation.** Cannot eliminate — policy gates are fundamentally bypassable. Must document "Forge not certified for Confidential+ without DLP" in every adoption agreement.

---

### R-GOV-01 — Solo-Claude authorship of entire v2.1 spec

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 5 | 5 | 4 | 5 | **19** | MITIGATING |

**Description.** The entire v2.1 work package — FORMAL_PROPERTIES_v2, GAP_ANALYSIS_v2, CHANGE_PLAN_v2, FRAMEWORK_MAPPING, ADR-001, ADR-002, ADR-003 — was authored by a single actor (Claude, one session 2026-04-22) and self-labeled `Status: normative`. CONTRACT §B.8 Solo-verifier + OM §9.2 explicit prohibition. User approval of headline decisions ≠ review of rationale / alternatives / consequences / evidence sections.

**Blast radius.** Quaternary amplification: v2.1 → ADRs → Phase A impl → production → customer. Error at top compounds 4 levels.

**Applicable.** All phases. Blocks Phase A entry (no PR against DRAFT spec).

**Mitigation (in progress).**
- ADR-003 created 2026-04-22, ratifies peer-review requirement.
- All v2.1 docs demoted to DRAFT 2026-04-23.
- ROADMAP.md Stage 0.1 = ratify ADR-003.
- Reviews folder + template created.

**Owner.** User / Framework Steward (not yet staffed).

**Residual risk after mitigation.** Low if ADR-003 ratified + docs peer-reviewed. UNMITIGATED until that happens — current state.

---

## HIGH

### R-SPEC-03 — Hidden property contradictions among 25

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 5 | 3 | 5 | **16** | OPEN |

**Description.** `FORMAL_PROPERTIES_v2 §5` "Consistency claims" are informal. Specific candidates:
- **P20 × P4**: uncertainty blocks execution vs autonomy may rise. If every task has some uncertainty, autonomy never promotes → asymptote doesn't reach `A_max`.
- **P8 × P23**: Evidence Completeness biconditional vs Verification Independence. Path where challenge passes but `Req ⊄ Prov` → conflict.
- **P1 × P13**: Idempotence vs Invariant Preservation. If invariant evaluates `now()` → repeated call violates idempotence.

**Applicable.** Phases A (P6, P8), D (property tests), E (P13 invariant), F (P19, P20, P23).

**Mitigation.** Phase D Stage D.2 `tests/property/test_cross_property_consistency.py` with per-pair test. Pre-Phase-A spike: explicit proofs for 6 consistency claims in §5.

**Owner.** Platform + spec author.

---

### R-GOV-02 — ADR-001 and ADR-002 CLOSED in same session as content authoring

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 5 | 4 | 3 | 4 | **16** | MITIGATING |

**Description.** User approved decisions; I authored rationale + alternatives + consequences. Per CONTRACT §B.8, content is solo-verified. Headline decision has distinct-actor ratification; content does not.

**Mitigation.** Per ADR-003, ADR-001 and ADR-002 have `decision CLOSED · content DRAFT` status. Peer-review of content required before implementation binds on rationale.

**Owner.** User / Framework Steward.

---

### R-GAP-02 — IMPLEMENTATION_TRACKER as self-reported evidence

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 4 | 3 | 4 | **15** | OPEN |

**Description.** 57 `[EXECUTED]` claims dated 2026-04-15/16 in `platform/IMPLEMENTATION_TRACKER.md`, authored by previous Claude session. v2 gap analysis partially relies on them. Per CONTRACT §B.8 transitivity: subagent `CONFIRMED` → parent `ASSUMED` at my level.

**Applicable.** All phases that reference current platform state.

**Mitigation.** ROADMAP Stage 0.3 "Smoke-test IMPLEMENTATION_TRACKER claims" — HTTP calls against every `[EXECUTED]` endpoint; divergence → Finding + GAP_ANALYSIS patch. Tracker claims labeled `[ASSUMED]` in v2.1 + memory until verified.

**Owner.** Platform.

---

### R-SPEC-05 — MANIFEST Principle 9 "we control our tools" masks vendor dependency

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 4 | 4 | 4 | **15** | OPEN |

**Description.** Principle 9 labeled "meta-reflexive" in FRAMEWORK_MAPPING.md §1 row 9. But "control" requires: own source + own release cycle + modify without vendor permission + audit. Claude Code CLI (Anthropic) + Anthropic API + model versions are in critical path. Silent model regression (compass: "Gaslightus 4.7" r/ClaudeCode 2026) = v2.1 enforcement degrades without detection.

**Mitigation.**
- ADR-006 "Model version pinning policy" (ROADMAP §12).
- Weekly eval canary (5 canonical tasks) — compass §143 recommendation.
- ADR-004 calibration: include "vendor dependency audit cadence".
- Amend FRAMEWORK_MAPPING §1 row 9: "PARTIAL — vendor boundary acknowledged per ADR-006".

**Owner.** Governance.

---

### R-PLAN-05 — Metric 4 gaming / self-referential

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 4 | 3 | 5 | **15** | OPEN |

**Description.** Metric 4 (contract violations disclosed vs detected) becomes THE signal. If detection is weak (only validator), agents learn to structure output to pass without disclosure. Ratio looks healthy by default — silent failure of the metric itself.

**Applicable.** Phase G.3.

**Mitigation.** Detection must be independent of validator. Rotating cross-validator check + random manual review. Log append-only (prevent retroactive tampering).

**Owner.** Platform + Steward.

---

### R-FW-04 — Framework Steward may reject acknowledged gaps during quarterly audit

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 4 | 4 | 4 | **15** | OPEN |

**Description.** `FRAMEWORK_MAPPING.md §12` acknowledges gaps (culture, Steward people, regulatory, kill criteria) as "not Forge's responsibility". Framework Steward during quarterly audit (OM §4.5) may reject this classification → Forge marked non-compliant → cannot claim CGAID alignment.

**Applicable.** Phase G.

**Mitigation.** Send FRAMEWORK_MAPPING.md to Framework Steward for sign-off before ratification. Steward objection → Finding → new ADR.

**Owner.** Governance.

---

## MEDIUM

### R-SPEC-01 — Calibration constants undefined

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 4 | 3 | 3 | **14** | MITIGATING |

**Description.** FORMAL §7 lists 8 calibration constants (W, q_min, τ, α, ImpactClosure thresholds, impact-estimate tolerance, idempotency TTL, acyclicity clock-skew). Without values, Phase A cannot exit. Ad-hoc value = P19 violation.

**Mitigation.** ROADMAP Stage 0.2: ADR-004 `Calibration constants` before Phase A PR.

**Owner.** Governance.

---

### R-PLAN-03 — Phase G depends on Phase E refactor (largest blast radius)

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 4 | 3 | 3 | **14** | WATCHING |

**Description.** Phase E moves 47 files into 6 subdirs. If it drags, G never ships.

**Mitigation.** Sequence E first (ROADMAP §2). Allow G to start incrementally per-mode as E lands. Don't bundle all G into one milestone.

---

### R-IRR-03 — Retroactive Stage 0 classification of existing Knowledge

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 4 | 3 | 3 | **14** | OPEN |

**Description.** Phase G1 introduces `DataClassification`. Existing Knowledge rows have no classification. Retroactive: (a) default (unsafe) or (b) block (halt downstream).

**Mitigation.** ADR-008 `Retroactive Stage 0 classification strategy` — defaults to Internal tier + time-boxed Steward reclassification session.

**Owner.** Governance + security.

---

### R-GOV-03 — No v2.1 deprecation mechanism

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 2 | 5 | 4 | 3 | **14** | OPEN |

**Description.** If P13 Invariant Preservation turns out unimplementable (e.g., invariants conflict at every transition), no formal way to retire a property. Docs are in git, propagated, memorized.

**Mitigation.** Explicit deprecation procedure in a future ADR: property flagged deprecated with date, new ADR explains why, rollout plan to remove binding.

---

### R-PLAN-01 — Shadow mode 1-week may not exercise all 75 sites

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 4 | 2 | 3 | **13** | OPEN |

**Description.** Phase A Stage A.3 shadow mode exposes 75 call-sites; some may not fire in 1 week depending on traffic.

**Mitigation.** Path-hit counter per call-site. Block enforcement until coverage ≥ 95%. Extend shadow window as needed.

---

### R-FW-03 — Cross-source hallucinations beyond MINIMAL

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 4 | 2 | 4 | **13** | OPEN |

**Description.** ADR-002 corrected one cross-source error (`MINIMAL` from outer CLAUDE.md). Others may lurk.

**Mitigation.** Systematic grep: terms appearing in `forge/.claude/CLAUDE.md` but NOT in `platform/` code → audit each.

---

### R-IRR-02 — CausalEdge backfill misclassification

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 2 | 3 | 4 | 4 | **13** | OPEN |

**Description.** Phase B.2 backfill from 10 FK relations. Misclassification (e.g., `Finding.source_llm_call_id` as `evidences` instead of `generated_by`) spreads bad semantics across graph.

**Mitigation.** Relation type explicit per backfill rule. Dry-run + distinct-actor review of sample 20 edges before commit. Allow relation edit post-backfill.

---

### R-OP-02 — Team capacity for 25-property Steward quarterly audit

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 3 | 3 | 3 | **13** | WATCHING |

**Description.** OM §4.5 demands quarterly Steward audit. Forge's 25 properties amplify audit time. Plus OM §4.4 clauses 1–8, plus 11 artifact mapping.

**Mitigation.** Automate what's automatable (property tests ARE the audit for those properties). Narrow human audit to §4.4 clauses only. Properties checked by CI.

---

### R-FW-01 — §12 acknowledged gaps may expand beyond Phase G scope

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 3 | 2 | 3 | **12** | WATCHING |

**Description.** During Steward review of §12, gaps may expand (e.g., Steward demands culture training, not just acknowledgment).

**Mitigation.** Early Steward engagement on FRAMEWORK_MAPPING.md § content.

---

### R-GAP-01 — Grep-only detection misses semantic boundaries

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 3 | 2 | 4 | **12** | OPEN |

**Description.** "No boundary coverage" claim via grep may miss function accepting `[min, max]` without "boundary" keyword in code.

**Mitigation.** Manual read of `scenario_generator.py` + sampling. Ask author before closing enum decision.

---

### R-OP-01 — Plan calendar 6-9 months exceeds typical org priority window

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 5 | 3 | 2 | 2 | **12** | WATCHING |

**Description.** 17–22 sprints estimated total. Organizational priority vs feature work uncertain.

**Mitigation.** Phase A + B + F = critical path for CGAID compliance minimum; others can defer. Explicit MVP subset in ROADMAP.

---

### R-DOC-02 — New docs are DRAFT per ADR-003

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 3 | 2 | 3 | **12** | MITIGATED |

**Description.** ROADMAP, DEEP_RISK_REGISTER, ARCHITECTURE, ONBOARDING, DATA_MODEL, WORKFLOW — all created in same session, DRAFT.

**Mitigation.** DRAFT banner on each; docs/README.md status table; status state machine in place.

---

### R-DOC-04 — ONBOARDING.md "<1h" claim unvalidated

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 3 | 2 | 4 | **12** | OPEN |

**Description.** Claim onboarding takes <1h not verified with a real new contributor.

**Mitigation.** Timing promise flagged `[ASSUMED]`. First real onboarding produces actual-time Finding.

---

### R-DOC-06 — ROADMAP diverges from CHANGE_PLAN_v2 over time

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 3 | 2 | 4 | **12** | OPEN |

**Description.** Two documents describing same phases — classic duplication risk.

**Mitigation.** ROADMAP.md header explicitly "derives from" CHANGE_PLAN_v2. When phase closes, update both in same PR. Consider CI check diffing phase names/count.

---

### R-IRR-01 — BLOCKED state down-migration handling

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 3 | 4 | 2 | **12** | OPEN |

**Description.** Phase F adds `BLOCKED` to `Execution.status`. Down-migration must specify: what happens to BLOCKED production rows?

**Mitigation.** ADR-011 `BLOCKED state down-migration handling` — default behavior: set to FAILED with `reason=ROLLBACK`.

---

### R-PLAN-04 — Non-trivial classifier overblocks → BLOCKED avalanche

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 3 | 2 | 2 | **11** | OPEN |

**Description.** P20 halts on UNKNOWN. Heuristic classifier — overclassify = every task stuck in BLOCKED.

**Mitigation.** Classifier opt-out. Shadow mode first. Human approves scope classification. Rate-of-BLOCKED metric monitored.

---

### R-SPEC-02 — Invariant.check_fn format undefined

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 4 | 3 | 2 | 2 | **11** | MITIGATING |

**Description.** P25 test synthesis needs `Invariant.check_fn` format. Python callable reference vs DSL — both have implications.

**Mitigation.** ADR-005 before Phase E.2.

---

### R-SPEC-04 — scenario_type 9 values taxonomic overlap

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 3 | 2 | 3 | **11** | OPEN |

**Description.** `boundary` ⊂? `edge_case`; `malformed` ⊂? `negative`. Ambiguous categorization.

**Mitigation.** Canonical examples in ADR-001 companion + classifier heuristic rules + manual override.

---

### R-DOC-05 — DEEP_RISK_REGISTER authored by risk-producer

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 3 | 2 | 3 | **11** | MITIGATING |

**Description.** This register written by same actor who created the risks. Double-dip R-GOV-01.

**Mitigation.** DRAFT status; peer review per ADR-003 same rigor.

---

### R-PLAN-02 — RuleAdapter assumes existing validators are pure

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 3 | 2 | 2 | **10** | OPEN |

**Description.** Adapter pattern works only if `plan_gate` + `contract_validator` are pure. If any has side effects (e.g., `audit_log.add`), wrapper insufficient.

**Mitigation.** Pre-Phase-A spike: full read of both files. Confirm no mutations. Plan rewrite if violated.

---

## LOW

### R-HAL-01 — file:line citations in docs rot

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 2 | 1 | 3 | **9** | WATCHING |

**Description.** v2.1 docs cite `execute.py:125` etc. Code edits shift lines.

**Mitigation.** Use symbolic refs (function names) where possible. CI citation-freshness check post-Phase-A.

---

### R-GAP-03 — "75 status mutations" may be overcounted

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 2 | 1 | 2 | **8** | OPEN |

**Description.** `Grep status\s*=\s*['\"]|\.state\s*=\s*['\"]` returns 75, includes `.state` (not just `.status`), render-time conditionals. True mutation count may be lower.

**Mitigation.** Precise grep `\.status\s*=` only (no `==`, no `.state`). Manual spot-check on 10 random matches.

---

### R-HAL-02 — ADR-002 Premise Correction requires session context

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 2 | 2 | 1 | 3 | **8** | WATCHING |

**Description.** Premise Correction section references prior-session Claude turn. Read in isolation — unclear.

**Mitigation.** Each ADR self-contained; inline context. No "see prior conversation" references.

---

### R-OP-03 — Onboarding time grows with doc set

| P | I | R | D | Composite | Status |
|---|---|---|---|---|---|
| 3 | 2 | 1 | 2 | **8** | MITIGATED |

**Description.** Original INDEX claimed 30 min onboarding; with ROADMAP + DEEP_RISK + platform docs = 2–3h realistic.

**Mitigation.** README.md §Fast path (15 min) provided for decision-makers. §Reading paths segmented by role.

---

## Risk evolution log

| Date | Event |
|---|---|
| 2026-04-23 | Initial audit: 29 risks enumerated. 2 CRITICAL, 6 HIGH, 17 MEDIUM, 4 LOW. P0 mitigations applied 2026-04-23: all v2.1 → DRAFT, ADR-003 created, R-FW-02 escalation in CHANGE_PLAN §13.3 G1 + FRAMEWORK_MAPPING §12. |

## Quarterly review cadence

This register is reviewed quarterly by Framework Steward (OM §4.5):
- Open risks: review mitigation progress.
- Closed risks: archive with closure evidence.
- New risks: added as discovered.
- Status updates: OPEN / MITIGATING / ACCEPTED / CLOSED / WATCHING.

## Relation to other docs

- **FORMAL_PROPERTIES_v2** — risks that violate a property reference property ID (e.g., R-SPEC-03 mentions P20 × P4).
- **GAP_ANALYSIS_v2** — risks that are gaps reference gap ID.
- **CHANGE_PLAN_v2 / ROADMAP** — mitigations map to phase/stage.
- **ADRs** — risks requiring decisions spawn ADRs (e.g., R-SPEC-01 → ADR-004).

## Escalation

- New **CRITICAL** (composite ≥ 18) → IMMEDIATELY notify Framework Steward + spawn ADR + pause affected phase.
- New **HIGH** (15-17) → flag in next standup + ADR within one sprint.
- New **MEDIUM / LOW** → log, review in quarterly.
