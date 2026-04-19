# Forge — Production Readiness Roadmap v1.0

**Status:** active · **Target:** 12 weeks from 2026-04-19 · **Owner:** engineering lead

## Baseline (2026-04-19)

Audited against CGAID v1.1 manifest (Contract-Governed AI Delivery). Coverage 76% across 9 standardized artifacts. Enterprise-readiness attributes (security hardening, observability, CI/CD, compliance, scale) unaudited as of this date — **Phase 0 closes that gap before Phase 2 commits to fixes**.

Assumptions used for this plan (flag if wrong — plan needs rework):
- Target: production-grade for enterprise consulting clients (ITRP, Randstad Ninja Code context)
- Hosting: cloud (AWS/GCP/Azure) — not on-prem appliance
- Team: solo developer + product owner; plan stretches if multi-developer
- Legal scope: GDPR applies (EU clients); SOC2 optional until first SOC2 client

## Phases

### Phase 0 — Diagnosis baseline (complete as of 2026-04-19)

Inputs to this plan already gathered:
- CGAID 9-artifacts audit with file:line evidence — `docs/FORGE_PRODUCTION_ROADMAP.md` (this file, appendix)
- Forge coverage score: 76%
- Top 3 CGAID gaps identified: PR flow (#7), in-repo markdown exports (#3, #5), formal Skill Change Log (#8)

**Not yet done — done as part of Phase 1 week 1:**
- Enterprise-readiness attribute scan: 12-factor compliance, secret management, observability stack, CI/CD maturity, scale test baseline, DR procedure

### Phase 1 — CGAID compliance closure (weeks 1–3)

Goal: lift CGAID compliance from 76% to ≥95%.

| Week | Deliverable | LOC estimate | Blocker |
|------|------------|--------------|---------|
| 1 | **In-repo markdown exports** (Artifact #3 Plan + #5 ADRs): `plan_exporter.py`, `adr_exporter.py`, hooks in approve-plan + Decision.status=CLOSED transition, tests | ~150 | none — starts immediately |
| 1 | **Enterprise-readiness attribute scan** → `docs/FORGE_ENTERPRISE_AUDIT.md` with per-attribute score | ~300 MD | none |
| 2 | **PR flow integration** (Artifact #7 Business DoD): branch creation per DONE task, push to remote, PR creation via GitHub/GitLab API, required-reviewers config, merge blocker until review | ~250 | GitHub/GitLab API token must be configured in org settings before coding starts |
| 2 | **Assisted-by trailer** in commit messages (Linux Kernel 2026 precedent) | ~20 | none |
| 3 | **Formal Skill Change Log** (Artifact #8): `SkillRevision` model, before/after metric capture, `/skill-change-log` endpoint + template | ~180 | DB migration window |
| 3 | **Unified Handoff Document export** (Artifact #4): template rendering all 8 CGAID fields per task + `Task.risks` field addition | ~100 | migration for risks column |

**Exit criteria Phase 1:** CGAID re-audit ≥95% coverage, 4 artifacts newly testable (export round-trip: MD ↔ DB), PR flow tested against real GitHub repo.

### Phase 2 — Enterprise hardening (weeks 4–8)

Goal: close gaps that CGAID does not require but enterprises mandate.

| Week | Deliverable | LOC estimate | Blocker |
|------|------------|--------------|---------|
| 4 | **Observability stack**: structured JSON logs, Prometheus metrics endpoint, health checks, tracing (OpenTelemetry) | ~400 | need observability platform decision (Grafana vs Datadog vs self-hosted) |
| 5 | **Secret management migration**: move Anthropic keys + JWT secret from env vars to vault-backed store (AWS Secrets Manager / HashiCorp Vault) | ~200 | infra decision |
| 5 | **SAST + dependency scan** in CI: bandit for Python, safety/pip-audit for deps, semgrep for business logic anti-patterns; fail build on HIGH+ | ~100 + config | CI platform decision (GH Actions / GitLab CI) |
| 6 | **Performance baseline + DB indexing**: load test 100 concurrent tasks, profile slow queries, add missing indexes (LLMCall, TestRun, PromptElement likely hot) | ~50 LOC + test scripts | test data set creation (~1 day) |
| 6 | **Backup + restore runbook**: automated pg_dump, offsite storage, tested restore procedure | ~80 | storage target decision |
| 7 | **Rate limiting + quota enforcement**: per-org API rate limits, per-user quotas, graceful 429 responses | ~150 | Redis instance (already in docker-compose) |
| 7 | **Content safety scan** on uploaded source docs: PII detection, size limits, malicious content heuristics | ~100 | decide depth: regex-only or ML-based |
| 8 | **Error taxonomy + alerting rules**: classify known failure modes, route to Slack/PagerDuty, define SLOs | ~60 | alerting target decision |

**Exit criteria Phase 2:** security scan clean, p95 latency < 500ms for UI routes under load, backup restore tested, 1 week of metrics collected, no P0 open findings.

### Phase 3 — Deploy & operate (weeks 9–10)

Goal: reproducible production deploy with documented ops procedures.

| Week | Deliverable | LOC estimate | Blocker |
|------|------------|--------------|---------|
| 9 | **Infrastructure-as-code** (Terraform/Pulumi): VPC, RDS postgres, ECS/Cloud Run for platform, S3 for workspace artifacts | ~400 IaC | cloud platform decision |
| 9 | **CI/CD pipeline**: build → test → security scan → deploy-to-staging → integration tests → manual-gate → deploy-to-prod | ~200 CI config | |
| 10 | **First staging deploy** — smoke test end-to-end pilot project (repeat WarehouseFlow 2026-04-17) | ops | staging env provisioned |
| 10 | **Ops runbook**: incident response, rollback procedure, common failure playbooks, on-call rotation template | ~15 pages MD | |

**Exit criteria Phase 3:** green E2E run on staging, documented rollback executed successfully at least once, ops runbook reviewed.

### Phase 4 — Compliance & scale (weeks 11–12)

Goal: first external-client readiness.

| Week | Deliverable | LOC estimate | Blocker |
|------|------------|--------------|---------|
| 11 | **GDPR data-retention policy**: per-artifact retention periods, right-to-delete endpoint, PII scrubbing pre-LLM-call | ~150 | legal review required |
| 11 | **Audit log export** (per-org, structured, tamper-evident) | ~80 | |
| 12 | **First production deploy** (shadow mode for 1 client, no merge to real repos until validated) | ops | client commitment |
| 12 | **Reproducibility test**: two independent teams deliver same pilot feature using only `docs/` documentation, measure divergence — validates CGAID claim "reproducible by outsiders" | ops + 2 engineers time | 2 engineers available |

**Exit criteria Phase 4:** 1 external client in shadow mode for 2 weeks without P0, reproducibility test divergence < threshold (TBD), GDPR pack accepted by legal.

## Cross-phase metrics

Track weekly (dashboard TBD in Phase 2 week 4):

1. **CGAID compliance score** (target ≥95% by end of Phase 1)
2. **Test coverage** unit + integration (target ≥80% lines on services/, api/)
3. **Security findings** HIGH+ open (target 0 by end of Phase 2)
4. **p95 latency** orchestrate run end-to-end (target < 120s for simple feature task)
5. **Cost per successful task delivered** (baseline: $1 per pilot, target: stable or improving as skills mature)
6. **Mean time to contract violation disclosure** (target: < 1 turn of model interaction)
7. **PR review cycle time** (guards against +91% AI-team regression — CGAID metric)

## Risks & blockers (discover + track)

- **R1 PR flow scope creep** — GitHub Actions/webhooks are a rabbit hole. Mitigation: stub with "create draft PR" first, add required-reviewers in Phase 2 when auth model is hardened.
- **R2 Cost-per-call spike under load** — Claude CLI subprocess per task at scale could cost 10× estimate. Mitigation: Phase 2 week 6 load test surfaces this early.
- **R3 Polish stemming false positives** — coverage_analyzer (Tydzień 2) prefix-5 match may annoy users on real projects. Mitigation: monitor in Phase 1; if complaints > threshold, integrate simplemma in Phase 2.
- **R4 Challenger model drift** — Opus 4.7 challenger verifying Sonnet 4.6 executor; model versions will change. Mitigation: Phase 4 reproducibility test includes model-version pin + replay harness.
- **R5 Multi-tenant data leakage** — `_assert_project_in_current_org` covers URL-guessing, but cross-org LLMCall PromptElement includes context_snapshot with potentially client-identifying terms. Mitigation: Phase 4 week 11 PII scrubbing pass.
- **R6 Dependency on single Claude CLI binary** — if Anthropic changes CLI interface, all subprocess invocations break. Mitigation: Phase 2 add abstraction layer (already exists partially in `claude_cli.py`), add fallback SDK path, test matrix includes CLI version pin.

## Out of scope for this roadmap (v2.x candidates)

- Multi-vendor AI composition (Copilot + Claude + internal model under one contract) — CGAID gap #6, requires separate design
- Inter-agent contracts (v3.x horizon per CGAID Section 8)
- Skill marketplace across organizations (cross-project promotion of anti-patterns)
- Replay regression harness for model version upgrades (partial baseline in Phase 4)
- Framework test harness for reproducibility claim (smoke test in Phase 4, full harness v2)
- Documentation generator UI (DOC task type is partially implemented; full CGAID Scenario 10 deliverable factory is v2)

## Changelog

- **v1.0 (2026-04-19)** — Initial plan. 4 phases, 12 weeks, per-week deliverables with LOC estimates and blockers. Baseline: CGAID 76% compliance, enterprise-readiness unaudited. Top 3 CGAID fixes scheduled for Phase 1.
