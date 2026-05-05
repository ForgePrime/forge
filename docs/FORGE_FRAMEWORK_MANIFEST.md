# Forge — Delivery Operating Model Manifest

**Status:** v1.0 · foundational · autonomous-session draft — **needs user review before adoption**

This document is CGAID Artifact #9 (Framework Manifest) for Forge itself:
what Forge *is* as a delivery operating model, what it enforces mechanically,
what is procedural, and how its coverage maps against the CGAID reference
manifest (`.ai/framework/FRAMEWORK.md`).

It is written at the meta level — an engineer or reviewer reading only this
document should be able to answer "how does this system govern AI-assisted
delivery?" without opening any other file.

---

## 1. Thesis

**Forge is a governed software delivery system where AI acts under contract,
evidence is mechanical, and every gate is enforced in code — not in review
etiquette.**

Three invariants that the rest of the framework exists to hold:

1. **No delivery reaches DONE without evidence.** Phase A `test_runner` runs
   real pytest in the workspace after each task. Completion claims by the AI
   are not trusted — `services/contract_validator.py:158-175` checks every
   AI claim for `[EXECUTED]/[INFERRED]/[ASSUMED]` tags.
2. **No fluent wrongness.** Independent challenger LLM verifies delivery
   separately from the executor. Scope limits are surfaced on every
   deliverable card — "what was NOT checked" is displayed next to "what was
   checked".
3. **No silent assumption drift.** Every decision is captured; closed
   decisions become ADRs in `.ai/decisions/` (in-repo markdown); open
   decisions block planning.

---

## 2. What is enforced in code

This section is the differentiator from advisory frameworks. Every bullet
is a mechanical gate — a commit cannot pass if the gate fails.

### 2.1 Task structure gates (`platform/app/api/projects.py`)
- Feature/bug tasks require ≥1 AC (`create_tasks` validation, line 228).
- Feature/bug tasks require ≥1 AC with `verification='test'|'command'` and
  `test_path` (Phase A trust-gate, line 240).
- `verification='command'` requires `test_path` — the `command` field is a
  descriptive label only (Opcja A decision D-06); shell is NOT invoked.

### 2.2 AC composition gate (`services/contract_validator.py:133`)
- feature/bug delivery MUST have at least one PASS verdict on a
  `negative` or `edge_case` scenario. Positive-only passes → `FAIL`.
- Rationale: CGAID pathology 2.4 — happy-path-only coverage is how
  production incidents slip through.

### 2.3 Confabulation tag gate (`contract_validator.py:158-175`)
- feature/bug delivery reasoning MUST contain at least one of the three
  epistemic tags: `[EXECUTED]`, `[INFERRED]`, `[ASSUMED]`.
- Missing tags → `WARNING`. Evidence without tags → `WARNING`.
- These map 1:1 to CGAID 3 epistemic states (CONFIRMED/ASSUMED/UNKNOWN)
  under different naming.

### 2.4 Operational contract gate (`contract_validator.py:141-156`)
- feature/bug delivery MUST carry `assumptions` and `impact_analysis`.
- Missing either → `FAIL`. Task cannot be ACCEPTED.

### 2.5 Phase A test execution (`services/test_runner.py`)
- After every delivery, Forge runs pytest (or jest/vitest for node
  workspaces) as subprocess. Real test execution — not AI's self-
  declaration.
- `verify_ac_tests` gate rejects task if feature/bug has zero
  test-verifiable AC with test_path.

### 2.6 Challenger verification (`services/challenger.py`)
- Separate LLM call verifies the executor's delivery. Challenger's scope
  limits ("what was NOT checked") are persisted and rendered on the
  task report card — CGAID pathology 2.4 (security + architecture drift)
  enforcement.

### 2.7 Coverage of source terms (`services/coverage_analyzer.py`)
- Tokenizes linked Knowledge content + all AC texts, flags high-
  frequency source terms absent from any AC.
- Pilot-validated: in WarehouseFlow 2026-04-17 pilot, this would have
  caught "rezerwacja" and "poniżej zera" under-coverage (F2 and F3 fails).
- Mechanical gap detector, not just a lint.

### 2.8 Autonomy ladder (`services/autonomy.py`)
- L1-L5 promotion requires: clean_runs_required (numeric, per level),
  min_contract_chars (numeric, per level), and for L5 zero objective
  re-opens in last 30 days.
- Cannot skip levels. Cannot self-promote without the evidence.

### 2.9 Cost enforcement (`services/budget_guard.py` + `pipeline._enforce_budget`)
- Per-org `budget_usd_monthly` hard-stops LLM calls when month-to-date
  exceeds budget. Returns `402 Payment Required` — fail-fast.
- `veto_check` stops autonomous action when >80% budget used OR flagged
  files touched (migrations/, billing/, secrets/, .env by default).

### 2.10 Commit provenance (`services/git_verify.py:build_assisted_by_trailer`)
- Every orchestrate-generated commit carries `Assisted-by: Forge
  orchestrator (<model>)` trailer per Linux Kernel 2026 precedent.
- AI never uses legally-binding `Signed-off-by` — human
  merger/reviewer stays accountable.

### 2.11 PII detection baseline (`services/pii_scanner.py`)
- Zero-dep regex detection for EMAIL, PHONE, IBAN, PESEL,
  CREDIT_CARD (Luhn-verified), IP_ADDRESS, SSN.
- `scan_then_decide()` policy wrapper: HIGH blocks, MEDIUM warns,
  LOW passes. Standalone — wiring into `/ingest` is a user-policy decision.

---

## 3. What is procedural (not yet mechanical)

Honest list of items that are convention + documentation, not yet
gate-enforced. These are the next candidates for code enforcement:

- **Skill sunset criteria** — roadmap mentions "cut what doesn't work";
  no process/quorum defined.
- **Framework test harness** — CGAID claims "reproducible by outsiders"
  but there's no mechanical test for the claim. Would require two
  independent teams delivering same feature from docs only — future work.
- **Retrospective / incident-to-framework feedback loop** — if a SEV1
  incident happens, no formal channel for updating this manifest.
- **Escalation SLA for UNKNOWN tags** — documented here as convention,
  not a timer + owner enforcement.
- **Cross-project skill marketplace** — skill lift metrics exist
  (`ProjectSkill.cost_impact_usd`) but no cross-project promotion
  workflow.

---

## 4. Artifacts produced (CGAID mapping)

Every Forge project produces this artifact set. Each has its storage
location AND in-repo mirror for engineers without Forge UI access.

| CGAID # | Artifact | Forge storage | In-repo mirror |
|---------|----------|---------------|----------------|
| 1 | Evidence Pack | `Knowledge` table + `Decision.status='OPEN'` | `forge_output/{slug}/knowledge.json` + manual view |
| 2 | Master Plan | `Objective` + `KeyResult` tables | `forge_output/{slug}/objectives.json` |
| 3 | Execution Plan | `Task` table + `tracker.json` | `{workspace}/.ai/PLAN.md` + `PLAN_{O-NNN}.md` (auto-exported) |
| 4 | Handoff Document | `Task` + `Decision` + `AcceptanceCriterion` aggregate | `{workspace}/.ai/handoff/HANDOFF_T-NNN.md` (auto) |
| 5 | ADRs | `Decision` table (status=CLOSED) | `{workspace}/.ai/decisions/D-NNN-*.md` (auto) |
| 6 | Edge-Case Test Plan | `AcceptanceCriterion.scenario_type` field | in Handoff and Plan exports above |
| 7 | Business-Level DoD | `KeyResult.measurement_command` + Objective ACHIEVED state | exported per-objective in Plan |
| 8 | Skill Change Log | `ProjectLesson` + `AntiPattern` + `ProjectSkill` tables | `{workspace}/.ai/SKILL_CHANGE_LOG.md` (auto via `services/skill_log_exporter.py` + `POST /api/v1/tier1/projects/{slug}/export/skill-log`). Before/after metric delta TODO — needs `SkillRevision` snapshot model. |
| 9 | Framework Manifest | `CLAUDE.md` per-project + `.claude/forge.md` | **This document** (org-level) |

---

## 5. Metrics surface

What Forge tracks about its own operation (per org + per project):

- CGAID compliance % (measured via the 9-artifact coverage audit)
- Enterprise readiness (54-attribute audit in `docs/FORGE_ENTERPRISE_AUDIT.md`)
- Per-task: LLM cost, duration, retry count, test pass rate
- Per-project: cumulative cost, orchestrate runs success rate, autonomy level,
  clean-runs count, objective ACHIEVED count
- Per-org: monthly LLM spend vs budget, member count, project count,
  audit log entries
- Per-LLM-call: prompt hash, content snapshot, model used, input/output tokens,
  cache reads, duration, cost

---

## 6. Security + accountability posture

- Multi-tenant isolation enforced at query layer (`_assert_project_in_current_org`)
- JWT auth + bcrypt + RBAC (owner/editor/viewer)
- CSRF double-submit cookie pattern (HTMX X-CSRF-Token header)
- Secrets encrypted at rest with Fernet (roadmap: move to KMS)
- Audit log captures who/what/when for mutations
- Graceful shutdown releases task leases + marks runs INTERRUPTED
- Request-id per HTTP request, echoed as X-Request-Id for tracing
- PII detection available for ingested documents (policy-gated)

---

## 7. Known gaps vs CGAID v1.1

Honest delta from the CGAID reference manifest. Not all gaps are bugs —
some are intentional scope choices.

Where CGAID is stricter than Forge:
- CGAID requires mandatory PR review before merge (Forge commits locally
  in workspace repos; PR flow is Roadmap Phase 2 week 2).
- CGAID's 7 disclosure behaviors (assumption-in-place-of-verification,
  partial implementation, happy-path-only, narrow interpretation,
  selective context, false completeness, failure-to-propagate-change)
  map partially to Forge gates. Only some are detected mechanically.
- CGAID defines an escalation SLA for UNKNOWN; Forge leaves this to
  user discretion today.

Where Forge extends CGAID (features not in reference):
- Coverage-of-source-terms mechanical gate (§ 2.7)
- Challenger pattern with visible scope limits (§ 2.6)
- Autonomy ladder L1–L5 with mechanical criteria (§ 2.8)
- Per-LLM-call economics audit trail (§ 5)
- In-repo markdown exports for Plan + ADRs + Handoff (§ 4)
- `Assisted-by` commit trailer per Linux Kernel 2026 (§ 2.10)

---

## 8. Versioning + change process

- This manifest uses semver like the rest of the platform.
- Changes proposed via PR with `docs(manifest)` commit prefix.
- Substantive changes require: (a) problem statement, (b) at least one
  delivered feature demonstrating the need, (c) CHANGELOG entry.
- Review cadence: quarterly; or on every incident that reveals a gap.

---

## 9. Changelog

- **v1.0 (2026-04-19, autonomous session)** — Initial version. Written
  at meta-level closing CGAID Artifact #9 org-level gap. Reflects state
  after the autonomous production-readiness session (commit ea3ef9b).
  Mechanical gates enumerated (11 items in § 2), procedural items
  acknowledged honestly (§ 3), CGAID 9-artifact mapping table (§ 4),
  delta from CGAID reference (§ 7). **Needs user review** before
  adoption as the authoritative Forge framework document.
