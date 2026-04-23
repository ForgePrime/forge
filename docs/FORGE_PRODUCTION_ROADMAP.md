# Forge — Production Readiness Roadmap v1.1

**Status:** active · **Target:** 10 weeks from 2026-04-23 · **Owner:** engineering lead

## v1.1 scope change — harmonization with platform/docs/ governance

v1.0 (2026-04-19) was authored against CGAID v1.1 manifest *before* platform-level normative governance was established on 2026-04-22. Since v1.0:

- **`platform/docs/FORMAL_PROPERTIES_v2.1.md`** introduced 25 atomic properties as the source of truth for delivery discipline.
- **`platform/docs/GAP_ANALYSIS_v2.md`** re-audited `platform/` per-property with file:line citations (2026-04-22, corrected three v1 hallucinations).
- **`platform/docs/CHANGE_PLAN_v2.md`** (DRAFT — pending distinct-actor peer review per ADR-003; may not execute Phase A until NORMATIVE) defined a 7-phase property-closure plan: A (deterministic gate), B (causal memory), C (impact closure + reversibility), D (failure-oriented testing), E (self-adjoint contract + diagonalization + invariants + autonomy), F (decision discipline), **G (CGAID compliance: Stage 0, Contract Violation Log, 7 metrics, Rule Lifecycle, Steward, 11 artifacts, Adaptive Rigor, Snapshot Validation)**.
- **Audit sessions v1.1 through v1.19** delivered: CSRF hardening, structured logs, PII scanner, backup/restore scripts, health+readiness split, GDPR export (art. 20), Graceful shutdown, data retention, CI starter, metrics endpoint, tracing, connection pooling, production Dockerfile, TLS docs, N+1 profiler.

**v1.1 scope becomes: enterprise-readiness items NOT covered by CHANGE_PLAN_v2**, i.e. infrastructure, compliance-closure, and ops-readiness concerns that are orthogonal to formal-property closure. CGAID compliance work migrates to CHANGE_PLAN_v2 Phase G. Items completed in audit sessions v1.1–v1.19 are marked DONE inline; remaining items are re-phased over 10 weeks.

This re-scoping respects three invariants:
1. **No duplication with CHANGE_PLAN_v2** — every item here is either property-orthogonal or explicitly out of that plan's scope.
2. **No regression of v1.0 commitments** — every Phase 1–4 deliverable either ships here, ships in Phase G, or is marked superseded with cross-reference.
3. **Reversibility** — every item below remains individually revertable (feature flag, migration downgrade, or IaC teardown).

## Baseline (2026-04-23, updated)

| Dimension | v1.0 baseline (2026-04-19) | v1.1 baseline (2026-04-23) | Source |
|---|---|---|---|
| CGAID compliance | 76% | **93%** (per `platform/docs/FRAMEWORK_MAPPING.md` §11.3) | enterprise-audit v1.7, confirmed by GAP_ANALYSIS_v2 |
| Enterprise readiness (G / A / R) | unaudited → 8G/23A/23R (Phase 0 output) | **18G / 23A / 13R — AMBER overall** | FORGE_ENTERPRISE_AUDIT.md v1.19 |
| Top-10 priority fixes | 10 open | **5 open** (CI activation, KMS secrets, load-test baseline run, durable jobs, GDPR right-to-delete) | FORGE_ENTERPRISE_AUDIT.md v1.19 |
| Formal properties closed (25) | N/A (not yet defined) | **0 fully; 8 PARTIAL; 2 WRONG-SHAPE; 14 ABSENT** | GAP_ANALYSIS_v2.md §1 |

Assumptions used for this plan (flag if wrong — plan needs rework):
- Target: production-grade for enterprise consulting clients
- Hosting: cloud (AWS/GCP/Azure) — not on-prem appliance
- Team: solo developer + product owner; plan stretches if multi-developer
- Legal scope: GDPR applies (EU clients); SOC2 optional until first SOC2 client
- **New v1.1:** CHANGE_PLAN_v2 will transition NORMATIVE within 1–2 weeks of this date; if delayed, Phase G items remain frozen, but v1.1 Phases 2–4 proceed independently (they do not depend on CHANGE_PLAN_v2 exit gates).

## Phases

### Phase 0 — Diagnosis baseline (complete as of 2026-04-19)

Inputs to this plan already gathered:
- CGAID 9-artifacts audit with file:line evidence — `docs/FORGE_PRODUCTION_ROADMAP.md` (this file, appendix)
- Forge coverage score: 76%
- Top 3 CGAID gaps identified: PR flow (#7), in-repo markdown exports (#3, #5), formal Skill Change Log (#8)

**Not yet done — done as part of Phase 1 week 1:**
- Enterprise-readiness attribute scan: 12-factor compliance, secret management, observability stack, CI/CD maturity, scale test baseline, DR procedure

### Phase 1 — CGAID compliance closure (status: **MOSTLY DONE or MIGRATED**)

v1.0 goal: 76% → 95%. v1.1 status: **93% reached** via audit sessions v1.1–v1.19. Residual CGAID items migrate to **CHANGE_PLAN_v2 Phase G** (part of `platform/docs/` governance). This v1.1 roadmap no longer owns them; they are listed here only for cross-reference so historical commitments remain traceable.

| Week (v1.0) | Deliverable | v1.1 status | Evidence / successor |
|---|---|---|---|
| 1 | In-repo markdown exports (Artifact #3 Plan + #5 ADRs) | **DONE** | `platform/app/services/plan_exporter.py`, `adr_exporter.py` — shipped. |
| 1 | Enterprise-readiness attribute scan | **DONE** | `docs/FORGE_ENTERPRISE_AUDIT.md` v1.0 → v1.19. |
| 2 | PR flow integration (Artifact #7 Business DoD): branch/push/PR via GitHub/GitLab API | **PARTIAL** — services exist (`github_pr.py`, `git_verify.py`); merge-blocker + required-reviewers wiring pending. **Residual item kept in this roadmap** (Phase 2 week 5 below). | not in CHANGE_PLAN_v2 scope |
| 2 | Assisted-by trailer (Linux Kernel 2026 precedent) | **DONE** | per `platform/README.md:59`. |
| 3 | Formal Skill Change Log (Artifact #8) — before/after metric capture | **MIGRATED to Phase G** | CHANGE_PLAN_v2 §13 — "7 metrics service" includes CGAID Metric 5 (skill change outcomes over 30-day window). |
| 3 | Unified Handoff Document export (Artifact #4) | **DONE** | `platform/app/services/handoff_exporter.py` + `Task.risks` shipped. |

**Exit criteria Phase 1 (updated v1.1):** retained only for the one PARTIAL item (PR flow integration); see Phase 2 below. All other criteria met or re-owned by CHANGE_PLAN_v2 Phase G.

### Phase 2 — Enterprise hardening (weeks 1–5, re-numbered from v1.0 weeks 4–8)

Goal: close enterprise-readiness gaps that CGAID does not require. Scope reduced to remaining AMBER/RED items from audit v1.19 + the one PARTIAL item migrated from Phase 1 (PR flow).

| Week | Deliverable | Status vs audit v1.19 | LOC estimate | Blocker |
|------|------------|----|--------------|---------|
| 1 | **Observability stack completion**: wire `record_llm_call` / `record_orchestrate_transition` into `pipeline.py` hot paths; wire custom tracing spans into `pipeline.orchestrate` + `claude_cli`; upgrade logging RED→GREEN by switching opt-in to default-on | `metrics.py` GREEN (v1.17), `tracing.py` GREEN (v1.19), logging AMBER | ~60 | observability platform pick for dashboards (Grafana stack recommended) |
| 2 | **PR flow integration** *(migrated from Phase 1 week 2)*: merge-blocker + required-reviewers wiring on top of existing `github_pr.py`; test end-to-end against real repo | PARTIAL | ~150 | GitHub/GitLab API token configured |
| 2 | **Secret management migration to KMS**: move Fernet-key from env to AWS KMS / HashiCorp Vault | AMBER | ~200 | infra platform decision |
| 3 | **CI activation**: flip `continue-on-error: false` after initial findings triaged; add deploy stage; tag `v0.1.0` | AMBER (CI starter GREEN; needs activation) | ~50 + config | initial bandit/pip-audit findings triage |
| 3 | **Load test baseline run**: execute `platform/scripts/loadtest.js` (k6) in staging; record p95 into SLO.md; add orchestrate end-to-end scenario | AMBER (script ships, not run) | 0 LOC + test day | staging env provisioned |
| 4 | **Durable background jobs**: replace FastAPI `BackgroundTasks` with Celery or RQ for `_run_orchestrate_background`; restart-safe job resumption | AMBER (top-10 #10) | ~400 | Redis already in compose (reuse) |
| 4 | **DB hot-path indexing**: `EXPLAIN ANALYZE` on `orchestrate_runs`, `llm_calls`, `prompt_elements`; add missing indexes; wire `query_profiler.py` N+1 detection into request middleware | AMBER (indexes); AMBER (profiler ships, not wired) | ~60 | load-test data set |
| 5 | **Rate limiting enforcement**: per-org API limits + per-user quotas + graceful 429 | not audited — build new | ~150 | Redis reuse |
| 5 | **Error taxonomy + alerting rules**: wire SLO.md 7 SLOs (UI availability, API correctness, orchestrate p95, cost per task, disclosure-rate SLO, DR RPO/RTO, CI green rate) into alertmanager routing | AMBER (SLO.md ships v1.10) | ~80 | alerting target decision |

**Exit criteria Phase 2 (updated v1.1):** CI green on every PR with `continue-on-error: false`; p95 latency baseline recorded; backup restore re-tested (monthly cadence from v1.4); top-10 fix list closed to 0; enterprise readiness matrix: 0 RED.

### Phase 3 — Deploy & operate (weeks 6–8)

Goal: reproducible production deploy with documented ops procedures. Partial pre-work landed in audit v1.13 (`platform/Dockerfile` multi-stage + `docker-compose.prod.yml`); IaC remains open.

| Week | Deliverable | Status vs audit v1.19 | LOC estimate | Blocker |
|------|------------|----|--------------|---------|
| 6 | **Infrastructure-as-code** (Terraform/Pulumi): VPC, RDS postgres, ECS/Cloud Run for platform, S3 for workspace artifacts | RED | ~400 IaC | cloud platform decision |
| 7 | **CI/CD pipeline deploy stage**: build → test → security scan → deploy-to-staging → integration tests → manual-gate → deploy-to-prod (builds on existing `.github/workflows/ci.yml`) | AMBER (CI test stages GREEN) | ~200 CI config | staging env from IaC |
| 7 | **First staging deploy** — smoke test end-to-end pilot project | pending | ops | staging env provisioned |
| 8 | **Ops runbook**: incident response, rollback procedure (leveraging `platform/scripts/backup.sh` + `restore.sh` + graceful shutdown v1.1), common failure playbooks, on-call rotation template | AMBER partial (deploy runbook RED per audit) | ~15 pages MD | |
| 8 | **RTO/RPO declaration**: add targets to SLO.md (proposed RTO 4h, RPO 24h pilot tier) | RED | ~10 lines MD | |
| 8 | **Workspace artifact durability**: move `forge_output/` to object storage with versioning | AMBER (host filesystem today) | ~100 | object-store pick |

**Exit criteria Phase 3:** green E2E run on staging, documented rollback executed successfully at least once, ops runbook reviewed, DR row GREEN overall.

### Phase 4 — Compliance & scale (weeks 9–10)

Goal: first external-client readiness.

| Week | Deliverable | Status vs audit v1.19 | LOC estimate | Blocker |
|------|------------|----|--------------|---------|
| 9 | **GDPR right-to-delete (Art. 17)** — admin endpoint + verified cascading delete across LLMCall/AuditLog/OrchestrateRun/workspace | RED (data retention AMBER shipped v1.9; export GREEN v1.6; delete missing) | ~150 | legal review required |
| 9 | **Audit log tamper-evidence**: append-only constraint + per-entry hash chain | GREEN (AuditLog model exists); tamper-evidence is additive | ~80 | |
| 10 | **First production deploy** (shadow mode for 1 client, no merge to real repos until validated) | pending | ops | client commitment |
| 10 | **Reproducibility test**: two independent teams deliver same pilot feature using only `platform/docs/` + `platform/README.md`, measure divergence — validates CGAID claim "reproducible by outsiders" | pending | ops + 2 engineers time | 2 engineers available |

**Exit criteria Phase 4:** 1 external client in shadow mode for 2 weeks without P0, reproducibility test divergence < threshold (TBD; define during Phase 4 week 9 legal review), GDPR pack accepted by legal.

## Cross-phase metrics

Track weekly (dashboard TBD in Phase 2 week 1; leverage `services/metrics.py` Prometheus endpoint shipped v1.17):

1. **CGAID compliance score** (v1.1: currently 93%; target ≥95% owned by CHANGE_PLAN_v2 Phase G, not this roadmap)
2. **Enterprise readiness R count** (v1.1: 13 RED; target 0 by end of Phase 3 — this roadmap's primary KPI)
3. **Test coverage** unit + integration (target ≥80% lines on `platform/app/services/`, `platform/app/api/`)
4. **Security findings** HIGH+ open (target 0 by end of Phase 2 week 3)
5. **p95 latency** orchestrate run end-to-end (target < 120s per SLO.md SLO-3; measured Phase 2 week 3)
6. **Cost per successful task delivered** (baseline: $1 per pilot per SLO-4; target: stable or improving)
7. **Mean time to contract violation disclosure** (target per SLO-5: ≥95% disclosed within 1 turn — owned by CHANGE_PLAN_v2 Phase F property P22, surfaced here for visibility)
8. **PR review cycle time** (guards against +91% AI-team regression — CGAID metric)

## Risks & blockers (discover + track)

- **R1 PR flow scope creep** — GitHub Actions/webhooks are a rabbit hole. Mitigation: stub with "create draft PR" first, add required-reviewers in Phase 2 when auth model is hardened.
- **R2 Cost-per-call spike under load** — Claude CLI subprocess per task at scale could cost 10× estimate. Mitigation: Phase 2 week 6 load test surfaces this early.
- **R3 Polish stemming false positives** — coverage_analyzer (Tydzień 2) prefix-5 match may annoy users on real projects. Mitigation: monitor in Phase 1; if complaints > threshold, integrate simplemma in Phase 2.
- **R4 Challenger model drift** — Opus 4.7 challenger verifying Sonnet 4.6 executor; model versions will change. Mitigation: Phase 4 reproducibility test includes model-version pin + replay harness.
- **R5 Multi-tenant data leakage** — `_assert_project_in_current_org` covers URL-guessing, but cross-org LLMCall PromptElement includes context_snapshot with potentially client-identifying terms. Mitigation: Phase 4 week 11 PII scrubbing pass.
- **R6 Dependency on single Claude CLI binary** — if Anthropic changes CLI interface, all subprocess invocations break. Mitigation: Phase 2 add abstraction layer (already exists partially in `claude_cli.py`), add fallback SDK path, test matrix includes CLI version pin.
- **R7 (new v1.1) CHANGE_PLAN_v2 does not transition NORMATIVE** — if peer review rejects or substantially revises Phase G, CGAID compliance items currently ceded to Phase G (Skill Change Log metric, Rule Lifecycle, Contract Violation Log, 7 metrics service) are orphaned. Mitigation: §"Relationship to platform/docs/ governance" states explicit reversibility path — v1.2 re-absorbs CGAID items with full context; audit evidence and cross-reference table remain valid intermediate artifacts. Maximum exposure is 2 weeks of no-op before v1.2 revision begins.
- **R8 (new v1.1) Duplicate work with CHANGE_PLAN_v2** — any enterprise-item here that turns out to map to P1–P25 creates double commitment. Mitigation: every Phase 2–4 deliverable was cross-checked against GAP_ANALYSIS_v2 and CHANGE_PLAN_v2 §2–§13; items that map to properties were removed (Rule Lifecycle, side-effect registry, tool-call dedup, replay harness). Recheck before each Phase exit gate.

## Relationship to `platform/docs/` governance (new in v1.1)

This roadmap and `platform/docs/CHANGE_PLAN_v2.md` are **non-overlapping axes**:

- **This roadmap (infrastructure axis)** — owns items where the fix is deploy / ops / compliance / CI. Success = enterprise-readiness matrix goes 0 RED. Independent of formal properties.
- **CHANGE_PLAN_v2 (property-closure axis)** — owns items where the fix is delivery-discipline code in `platform/app/`. Success = 25 atomic properties reach "fully satisfied". Items here affect `forge_deliver`, `plan_gate`, `contract_validator`, `autonomy.py`, `challenger.py`, and their callers.

Cross-references:

| Concern | Owned by | Reason |
|---|---|---|
| CI green / security scans / deploy automation | this roadmap Phase 2–3 | infrastructure, not a property |
| Skill Change Log before/after metric (CGAID Metric 5) | CHANGE_PLAN_v2 Phase G | part of "7 metrics service" bundle |
| Side-effect registry + import-graph closure | CHANGE_PLAN_v2 Phase C | closes P3 Impact Closure |
| Rule Lifecycle (create / measure / retire) | CHANGE_PLAN_v2 Phase G | CGAID §4.3; listed in Phase G deliverables per INDEX.md |
| Tool-call dedup / idempotency | CHANGE_PLAN_v2 Phase A | closes P1 Idempotence via `IdempotentCall` table |
| GDPR right-to-delete | this roadmap Phase 4 week 9 | infrastructure + legal, not a property |
| IaC, KMS, durable jobs | this roadmap Phase 2–3 | infrastructure |

If a future item surfaces that does not fit cleanly into either axis, add it here by default; re-assign to CHANGE_PLAN_v2 only if it maps to a specific property P1–P25.

**Reversibility of this harmonization.** If CHANGE_PLAN_v2 does not transition NORMATIVE (fails peer review, or is substantially revised), v1.1 remains coherent: every item here stands on its own audit evidence, and the cross-reference table above survives any revision of Phase G internals. If CHANGE_PLAN_v2 is revoked entirely, v1.1 should be re-scoped to re-absorb CGAID items — but this is a larger editorial change than a roadmap bump and should trigger v1.2 (document lineage preserved).

## Out of scope for this roadmap (v2.x candidates)

- Multi-vendor AI composition (Copilot + Claude + internal model under one contract) — CGAID gap #6, requires separate design
- Inter-agent contracts (v3.x horizon per CGAID Section 8; see also FORMAL_PROPERTIES_v2 P24 Transitive Accountability — partial coverage in CHANGE_PLAN_v2 Phase F)
- Skill marketplace across organizations (cross-project promotion of anti-patterns)
- Replay regression harness for model version upgrades (partial baseline in Phase 4; full harness maps to FORMAL_PROPERTIES_v2 P6 Deterministic Evaluation replay harness in CHANGE_PLAN_v2 Phase A)
- Framework test harness for reproducibility claim (smoke test in Phase 4, full harness v2)
- Documentation generator UI (DOC task type is partially implemented; full CGAID Scenario 10 deliverable factory is v2)
- **Items owned by CHANGE_PLAN_v2 Phase A–G** — explicitly out of this roadmap's scope per §"Relationship" above.

## Changelog

- **v1.1 (2026-04-23)** — Harmonization with `platform/docs/` normative governance established 2026-04-22. Baseline updated: CGAID 76%→93%, enterprise 0G/0A/0R (unaudited)→18G/23A/13R. Phase 1 re-scored: 5 items DONE, 1 PARTIAL (PR flow migrated to Phase 2 week 2), 1 MIGRATED to CHANGE_PLAN_v2 Phase G (Skill Change Log metric). Phase 2–4 re-numbered to weeks 1–10 (from 4–12), per-item status added from audit v1.19, replay harness + side-effect registry + rule lifecycle + tool-call dedup explicitly ceded to CHANGE_PLAN_v2. New §"Relationship to platform/docs/ governance" defines non-overlapping axes with CHANGE_PLAN_v2 and reversibility statement for the harmonization itself. Out-of-scope section annotated with cross-references to FORMAL_PROPERTIES_v2 properties. Duration 12 → 10 weeks (Phase 1 collapsed to residual single item). No new commitments beyond the PARTIAL Phase 1 item and the Phase 3 RTO/RPO declaration that was implicit in v1.0. **This change is reversible**: revert to v1.0 by `git revert`; all evidence-audit annotations remain valid as historical notes.
- **v1.0 (2026-04-19)** — Initial plan. 4 phases, 12 weeks, per-week deliverables with LOC estimates and blockers. Baseline: CGAID 76% compliance, enterprise-readiness unaudited. Top 3 CGAID fixes scheduled for Phase 1.
