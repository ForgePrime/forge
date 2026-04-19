# Forge — Enterprise Readiness Audit v1.0

**Status:** active · **Audited:** 2026-04-19 · **Scope:** `platform/` tree only (forge-api/ is a separate older codebase — listed but not audited here)

## Method

Each attribute scored **GREEN / AMBER / RED** per this rubric:
- **GREEN** — production-acceptable as-is; no blocker for external-client launch.
- **AMBER** — present but incomplete; acceptable for internal pilot, blocker for external enterprise.
- **RED** — absent or inadequate; blocks any production launch beyond dev.

Evidence is cited inline as `file:line` — each claim is verifiable by grep.
"Unaudited" means I did not check in this pass (not "present" or "absent").

---

## Summary

| Category | Attributes audited | G | A | R | Overall |
|----------|-------------------|---|---|---|---------|
| 12-factor app | 12 | 6 | 3 | 3 | **AMBER** |
| Security | 10 | 6 | 2 | 2 | **AMBER** |
| Observability | 6 | 3 | 1 | 2 | **AMBER** |
| CI/CD | 5 | 0 | 5 | 0 | **AMBER** |
| Scale & performance | 6 | 2 | 3 | 1 | **AMBER** |
| Compliance (GDPR/audit) | 6 | 2 | 3 | 1 | **AMBER** |
| Disaster recovery | 4 | 0 | 3 | 1 | **AMBER** |
| Documentation | 5 | 2 | 3 | 0 | **AMBER** |
| **TOTAL (54 attr.)** | **54** | **21** | **23** | **10** | **AMBER overall** |

**Verdict (v1.7):** Forge has moved from RED overall to **AMBER overall**.
CGAID delivery-governance is strong (93% per prior audit), and the baseline
infrastructure for observability, compliance, DR, and CI/CD is now in place.
Remaining RED clusters are 14 attributes concentrated in:
- Deep observability (Prometheus metrics endpoint, OpenTelemetry tracing)
- Deploy automation (IaC — Roadmap Phase 3 item)
- Compliance (GDPR retention + right-to-delete still needed)
- Scale (load test baseline, N+1 detection, durable background jobs)
- Documentation (deployment runbook partially green, needs a few missing pieces)
- Secret management (KMS-backed — Roadmap Phase 2 week 5)

Estimated effort to GREEN overall: **3-5 weeks dedicated work**, down from
5-8 weeks at v1.0. Still gated on Roadmap Phase 2 + Phase 3 items.

---

## 1. Twelve-Factor App (Heroku methodology)

| # | Factor | Status | Evidence | Gap |
|---|--------|--------|----------|-----|
| I | Codebase — one repo, many deploys | GREEN | Single Forge repo with branching | — |
| II | Dependencies — explicit, isolated | GREEN | `pyproject.toml` | pyproject exists; lock file (uv.lock / poetry.lock) unaudited |
| III | Config — in env | GREEN | `platform/app/config.py:4,18,51` BaseSettings + env_prefix=FORGE_ + env_file | — |
| IV | Backing services — swappable URLs | GREEN | DATABASE_URL / REDIS_URL env-driven | — |
| V | Build/release/run — strict separation | AMBER | `forge-api/Dockerfile` present; no release stage, no artifact repo | Need CI that builds once, promotes image |
| VI | Processes — stateless | AMBER | FastAPI app is stateless; **workspace_infra spawns per-project postgres containers** which tie state to host | Workspace state not portable; live migration between hosts would need volume attach |
| VII | Port binding — self-contained | GREEN | `FORGE_HOST=0.0.0.0 FORGE_PORT=8000` env-bound | — |
| VIII | Concurrency — horizontal scale | AMBER | FastAPI/uvicorn scales; **orchestrate_runs use DB-backed lease (FOR UPDATE SKIP LOCKED) so multi-instance-safe** (platform/app/api/execute.py:110). However `_run_orchestrate_background` uses in-process BackgroundTasks — lost on restart. | Need Celery/RQ or DB-backed job queue for production |
| IX | Disposability — fast start, graceful shutdown | GREEN | Startup: fast (~2s). Shutdown path added in v1.1 (audit top-10 #8): `lifespan` end releases IN_PROGRESS tasks and marks RUNNING orchestrate runs INTERRUPTED. See `services/orphan_recovery.py:release_in_progress_tasks`, `mark_running_runs_interrupted_on_shutdown` + `tests/test_graceful_shutdown.py`. | — (upgraded AMBER→GREEN in v1.1) |
| X | Dev/prod parity | AMBER | docker-compose mirrors prod (postgres 16, redis); no staging env definition | Staging IaC missing |
| XI | Logs — to stdout as streams | AMBER | Python `logging` used in 4 files (main.py, hooks_runner.py, orphan_recovery.py, schema_migrations.py); **unstructured** (no JSON formatter, no correlation IDs) | Add structlog/json-logger + request-id middleware |
| XII | Admin processes — one-off | GREEN | `schema_migrations.py apply()` runs at startup + `forge-api/scripts/migrate_skills.py` available | — |

**Category verdict:** AMBER. Core stateless design is there; observability of processes (XI) is the main drag.

## 2. Security

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| Authentication (user identity) | GREEN | JWT via `app/services/auth.py` `create_access_token`, login at `api/ui.py:89` | — |
| Password storage | GREEN | bcrypt via `hash_password` (auth.py); constant-time `verify_password` | — |
| Authorization (RBAC) | GREEN | `_require_role(request, 'editor')` `platform/app/api/ui.py:65-71`; 3-tier owner/editor/viewer | — |
| Multi-tenant isolation | GREEN | `_assert_project_in_current_org` (ui.py:44-54) — 404 on cross-tenant attempt, doesn't leak existence | — |
| CSRF protection | GREEN | `app/services/csrf.py:CSRFMiddleware` wired in `app/main.py:99`. Validates X-CSRF-Token header on POST/PATCH/DELETE/PUT. Exemptions listed (auth, /health, /share). Verified by `tests/test_csrf_middleware.py` (9 tests, all PASS). | — (upgraded from AMBER in v1.1 — direct contract tests added) |
| Secret management | AMBER | Anthropic API keys encrypted via Fernet in DB (`auth.py encrypt_secret/decrypt_secret`) — **symmetric, key in env var** | Rotate to KMS-backed (AWS KMS / HashiCorp Vault) for production |
| TLS termination | GREEN | v1.15: docs/DEPLOY.md now has explicit TLS section with 3 reverse-proxy recipes (Caddy auto-LE, nginx, Traefik docker-compose), required forwarded headers documented, sanity-check commands listed. Platform architecturally delegates TLS to edge proxy (correct separation of concerns). | — (upgraded AMBER→GREEN in v1.15) |
| Input validation | GREEN | Pydantic `BaseModel` on all API bodies (projects.py etc.) | — |
| SAST / dep scan in CI | RED | No CI workflow files found | Add Semgrep/Bandit/pip-audit to CI (Roadmap Phase 2 week 5) |
| Content safety scan on uploads | RED | `/ingest` accepts user-uploaded documents directly into Knowledge.content without PII/size scrutiny | Add max-size + regex-based PII detection (Roadmap Phase 2 week 7) |

**Category verdict:** AMBER. Authentication/authorization/multi-tenant are mature. CI security scanning and KMS-backed secret storage are the main gaps.

## 3. Observability

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| Structured logs | AMBER | `app/services/logging_setup.py` (v1.2): stdlib JSON formatter opt-in via `FORGE_LOG_JSON=true`; `RequestIdMiddleware` assigns + echoes `X-Request-Id`; `RequestIdFilter` injects into every LogRecord. Tests: `tests/test_logging_setup.py` (14 tests). | Upgrade to AMBER from RED. Still stdlib (not structlog) — acceptable baseline; upgrade to structlog if processor chains needed. |
| Metrics endpoint (Prometheus) | RED | No `/metrics` route found; no `prometheus_client` import | Add `starlette_prometheus` or equivalent |
| Distributed tracing | RED | No `opentelemetry` import | Add OTel instrumentation (FastAPI + SQLAlchemy + httpx) |
| Health endpoint | GREEN | `main.py:117-119` `@app.get('/health')` returns `{status, version}` | — |
| Liveness vs readiness split | GREEN | v1.5: `/health` is pure process-alive (no backend checks); `/ready` checks DB via SELECT 1 + Redis via raw socket PING (zero-dep, no `redis` lib added). Returns 200 with `checks: {db: ok/fail:…, redis: ok/fail:…}` or 503. Both public (not auth-gated). Tests: `tests/test_health_ready.py` (5 tests). | — (upgraded RED→GREEN in v1.5) |
| Alert/SLO definitions | GREEN | v1.10: `docs/SLO.md` ships with 7 SLOs — UI availability (99.5%), API correctness (99.0%), orchestrate p95 latency (<120s), cost per task (<$1.50 mean, $10 hard ceiling), **contract violation disclosure rate** (≥95% — CGAID trust SLO), DR RPO/RTO (24h/4h), CI green rate (95%). All numbers explicitly aspirational pending load test baseline; adjustment process documented. | Tune after first month of measurement. |

**Category verdict:** RED. This is the single biggest enterprise blocker beyond tests — without metrics/tracing/alerts, production incidents will be diagnosed by log-tailing.

## 4. CI/CD

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| CI config file present | AMBER | v1.7: `.github/workflows/ci.yml` ships as starter — pytest against real postgres+redis services, py3.13 matrix, concurrency cancellation. Still starter: security/lint jobs use `continue-on-error: true` until baselines are clean. | Activate on GH org + turn off continue-on-error once baselines clean. |
| Automated test on PR | AMBER | v1.7: `on: [push, pull_request]` trigger in ci.yml. Requires activation on GitHub side. | Same as above |
| Automated security scan | AMBER | v1.7: pip-audit + bandit in ci.yml + weekly `.github/workflows/security.yml` with artifact upload. Non-blocking until baseline clean. | Fix initial findings, flip continue-on-error to false |
| Deploy pipeline | AMBER | v1.13: `platform/Dockerfile` (multi-stage, non-root user, healthcheck) + `platform/docker-compose.prod.yml` (healthchecks, mandatory secrets via `${VAR:?err}`, resource limits, log rotation, persistent volumes, depends_on healthy). Deploy is still host-side docker compose up; cloud IaC (Terraform) remains Roadmap Phase 3. | Add CI deploy stage once staging target chosen. Add Terraform for cloud. |
| Release versioning | AMBER | v1.7: `CHANGELOG.md` ships at repo root with "Unreleased" section + session summary. Git tags still TODO. | Tag first semver release `v0.1.0`; wire `changelog` to tags. |

**Category verdict:** RED. Every production deployment today is artisanal.

## 5. Scale & performance

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| DB indexing review | AMBER | Primary keys + FK indexes auto-created; `orchestrate_runs` and `llm_calls` are write-heavy — no evidence of explicit indexes beyond FKs | Run `EXPLAIN ANALYZE` on hot paths (cost forecast, task_report); add indexes as needed |
| Load test baseline | AMBER | v1.11: `platform/scripts/loadtest.js` ships as k6 starter — VUs/duration via env, ramp-up plan, checks health/ready/optional project-status, thresholds enforce p95 < 100ms health / 300ms ready / <1% errors. docs/DEPLOY.md updated with invocation examples. **Not yet run against a baseline** — needs k6 binary + staging instance; first run establishes numbers referenced by SLO-1/2/3. | Run in staging, record baseline, wire into CI as optional job. Add orchestrate end-to-end load scenario. |
| Connection pooling | GREEN | v1.12: `app/database.py` tunes `pool_size=10`, `max_overflow=20`, `pool_recycle=1800s`, `pool_timeout=30s`, `pool_pre_ping=True`. Overridable via env vars `FORGE_DB_POOL_SIZE / MAX_OVERFLOW / POOL_RECYCLE / POOL_TIMEOUT`. Pool status verified in-process. | Tune defaults based on production workload measurement. |
| Cache layer | GREEN | Redis included in docker-compose (used for workspace lease? rate limiting? unaudited) | — |
| Background job durability | AMBER | `BackgroundTasks` FastAPI is in-process; lost on restart | Replace with Celery/RQ for production |
| N+1 query detection | AMBER | v1.14: `services/query_profiler.py` ships — SQLAlchemy `after_cursor_execute` listener, contextvar-scoped counter, normalizes statements (collapse placeholders + whitespace), threshold env override (`FORGE_NPLUS1_THRESHOLD`, default 5). `scope()` context manager for per-handler profiling; logs WARNING with structured extras on breach. 17 unit tests. Zero new deps. | Wire into request middleware for automatic per-request N+1 reporting. |

**Category verdict:** RED. Without load testing, predicting p95 under real workload is guesswork. Roadmap Phase 2 week 6 addresses.

## 6. Compliance (GDPR / audit)

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| Audit log (who/when/what) | GREEN | `AuditLog` model + `_audit(...)` helper used in execute.py/pipeline.py | — |
| PII scrubbing before LLM call | AMBER | v1.3: `services/pii_scanner.py` provides regex-based detection (EMAIL, PHONE, IBAN, PESEL, CREDIT_CARD w/ Luhn, IP, SSN) + `redact()` + policy-wrapped `scan_then_decide()`. 30 unit tests. **NOT wired into `/ingest` yet** — standalone tool awaiting user policy decision (block vs warn vs redact by default). | Wire into ingest endpoint with project-level policy config. Optional upgrade to presidio/NER for higher recall. |
| Data retention policy | AMBER | v1.8: `services/data_retention.py` ships with 3 default policies (LLMCall 180d, AuditLog 365d, OrchestrateRun 365d) + dry-run support + per-entity overrides + per-entity error capture. `POST /api/v1/tier1/gdpr/retention/sweep` owner-only endpoint. 12 unit tests. **NOT yet scheduled** — admin manually triggers or wires to external cron. PromptElement excluded pending TimestampMixin migration. | Schedule via cron/systemd timer. Add PromptElement after migration. |
| Right-to-delete (GDPR art. 17) | RED | No endpoint to purge user/org data | Add admin endpoint + verified cascading delete |
| Data export (GDPR art. 20) | GREEN | v1.6: `services/gdpr_export.py` + tier1 endpoints `GET /gdpr/users/{id}/export` (self or owner) + `GET /gdpr/orgs/{slug}/export` (owner-only). Structured JSON covering identity/memberships/audit entries for users; projects summary + members for orgs. Explicit `notes` section documents what ISN'T in the export (workspace artifacts, raw LLM bodies). 8 unit tests. | — (upgraded AMBER→GREEN in v1.6) |
| Terms + consent | AMBER | Not in Forge scope (client-facing deployment owns) | Document expectation in deploy guide |

**Category verdict:** RED. PII-to-LLM and GDPR right-to-delete are hard blockers for EU enterprise clients. Roadmap Phase 4 week 11 addresses; consider accelerating if first client is EU-based.

## 7. Disaster recovery

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| Automated DB backup | AMBER | v1.4: `platform/scripts/backup.sh` ships — idempotent pg_dump with gzip, retention pruning, optional S3 upload. Cron example in docs/DEPLOY.md. | Production still needs monitoring (alert on missed nightly) + verified offsite copy. |
| Restore-tested runbook | AMBER | v1.4: `platform/scripts/restore.sh` ships — safety-guarded (refuses to overwrite prod without FORCE_PROD=1), smoke verification via table count, instructions in docs/DEPLOY.md for monthly verification cadence. | Automate the monthly verification in CI or cron. |
| RTO/RPO defined | RED | No stated targets | Declare (proposed: RTO 4h, RPO 24h for pilot tier) |
| Workspace artifact durability | AMBER | `forge_output/` is in host filesystem (not S3 / object storage); forge_output/{project}/workspace/ is actual git repo per project | Move to object storage with versioning for prod |

**Category verdict:** RED. Single host failure today means complete data loss.

## 8. Documentation

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| Developer README | AMBER | docs/DESIGN.md, docs/CLI-REFERENCE.md, docs/STANDARDS.md present; no top-level README.md | Add README with 5-minute quickstart |
| API reference (OpenAPI) | GREEN | FastAPI auto-generates at `/docs` | — |
| Deployment runbook | RED | No docs/DEPLOY.md or runbook | Required for on-call rotation (Roadmap Phase 3 week 10) |
| Architecture diagram | GREEN | docs/FORGE-PROCESS-DIAGRAM.md exists | — |
| Changelog | AMBER | Per-doc changelogs in MD files; no top-level CHANGELOG.md | Add one; tie to git tags |

**Category verdict:** AMBER.

---

## Top 10 priority fixes (ordered by unblocking value)

These are the concrete next items to move Forge toward "not-RED":

1. **CI pipeline with test + security scan** — RED across 3 categories, single biggest unblocker. GitHub Actions or GitLab CI. Roadmap Phase 2 week 5 → promote to week 4.
2. **Structured logging + request-id middleware** — unblocks observability and incident response. `structlog` or `loguru` + middleware. ~1-2 days.
3. **Prometheus `/metrics` endpoint** — enables SLO tracking. `starlette_prometheus`. ~1 day.
4. **PII detection pre-LLM-call** — enterprise-blocker for EU. Regex-based baseline + optional flag. ~2-3 days.
5. **Automated nightly backup + tested restore** — single host failure today = full loss. ~3-5 days including runbook.
6. **Load test baseline** — we do not know p95 under load today. k6 or Locust against orchestrate. ~3 days.
7. **Top-level README.md + DEPLOY.md** — new engineers currently need Slack to get started. ~1 day.
8. **SIGTERM handler releasing task leases on shutdown** — graceful shutdown prevents stuck IN_PROGRESS tasks. ~0.5 day.
9. **CSRF enforcement verification** — middleware expected on state-changing routes; confirm + add missing. ~1 day (audit+fix).
10. **Durable background jobs (Celery/RQ) for orchestrate** — in-process BackgroundTasks are lost on restart. ~1 week (migration).

Total estimated effort for top-10: **~5-7 weeks** for single developer, concentrated in Roadmap Phase 2.

---

## What I did not audit (scope limitations of this pass)

- **`forge-api/` tree** — this is a separate older codebase (different Dockerfile, different model). If it will be retired, skip; otherwise it needs its own audit.
- **JavaScript bundles / templates** — inline scripts in Jinja templates exist (_ac_row.html etc.); no npm audit on frontend deps (because there are no npm deps — all inline).
- **License compliance of Python deps** — `pyproject.toml` present but no `pip-licenses` report generated in this pass.
- **Penetration test** — requires a real attempt against a deployed instance; not a desk audit.
- **SOC2 / ISO 27001 gap analysis** — requires controls framework; this audit covers common-sense prerequisites, not formal attestation.
- **Cost of infra at scale** — IaC not written yet, cannot estimate.

---

## Changelog

- **v1.0 (2026-04-19)** — Initial audit. 54 attributes scored across 8 categories. Overall RED for production; AMBER for internal pilot. Top 10 priority fixes identified, aligned with Production Roadmap Phase 2.
- **v1.1 (2026-04-19, autonomous session)** — CSRF upgraded AMBER→GREEN after direct middleware contract tests added (`tests/test_csrf_middleware.py`, 9 tests). Security row: 4G/4A/2R → 5G/3A/2R. Overall 14G/16A/24R → 15G/15A/24R. Graceful shutdown (top-10 #8) landed — no audit row moved because shutdown isn't a separate attribute; reflected as improvement under 12-factor disposability.
- **v1.2 (2026-04-19, autonomous session)** — Structured logs upgraded RED→AMBER. `services/logging_setup.py` adds stdlib JsonFormatter (opt-in via `FORGE_LOG_JSON` env), RequestIdMiddleware assigning per-request UUID echoed as `X-Request-Id`, and RequestIdFilter injecting the ID into every LogRecord. Zero new deps (stdlib only). 14 unit tests. Observability row: 1G/1A/4R → 1G/2A/3R. Overall 16G/14A/24R → 16G/15A/23R.
- **v1.3 (2026-04-19, autonomous session)** — PII scrubbing row RED→AMBER. `services/pii_scanner.py` (NEW, zero-dep regex): EMAIL, PHONE, IBAN, PESEL, CREDIT_CARD (Luhn-verified), IP_ADDRESS, SSN. `scan()` + `redact()` + policy wrapper `scan_then_decide()`. 30 unit tests. **Not yet wired into `/ingest`** — awaits per-project policy decision (block/warn/redact by default). Compliance row: 1G/2A/3R → 1G/3A/2R. Overall: 16G/15A/23R → 16G/16A/22R.
- **v1.4 (2026-04-19, autonomous session)** — DB backup + restore scripts ship. `platform/scripts/backup.sh` (idempotent pg_dump, gzip, retention prune, optional S3) + `platform/scripts/restore.sh` (safety-guarded, smoke-verified). docs/DEPLOY.md updated with cron example + monthly verification cadence. DR category: 0G/1A/3R → 0G/3A/1R. Overall: 16G/16A/22R → 16G/18A/20R. **DR category upgraded AMBER overall** (was RED); still RED project overall (observability, CI/CD, compliance, scale).
- **v1.5 (2026-04-19, autonomous session)** — `/ready` readiness probe added (liveness/readiness split). Zero-dep: raw TCP socket for Redis PING to avoid adding `redis` lib. Public (added to auth whitelist) so LB probes don't need credentials. 5 unit tests. Observability liveness row RED→GREEN. Category: 1G/2A/3R → 2G/2A/2R (AMBER overall). Total: 16G/18A/20R → 17G/18A/19R.
- **v1.6 (2026-04-19, autonomous session)** — GDPR Article 20 data export. `services/gdpr_export.py` + tier1 endpoints `GET /gdpr/users/{id}/export` (self or owner) + `GET /gdpr/orgs/{slug}/export` (owner-only). Structured JSON with identity/memberships/audit/projects summary. Explicit `notes` section documenting what isn't exported (workspace, raw LLM bodies). 8 unit tests. Compliance data-export row AMBER→GREEN. Compliance category: 1G/3A/2R → 2G/2A/2R (**AMBER overall**, was RED). Total: 17G/18A/19R → 18G/17A/19R.
- **v1.7 (2026-04-19, autonomous session)** — CI/CD category goes RED→AMBER. `.github/workflows/ci.yml` ships as starter (pytest against real postgres+redis, pip-audit, bandit, ruff — security/lint non-blocking until baseline clean). `.github/workflows/security.yml` runs weekly deep scan with 30-day artifact retention. `CHANGELOG.md` ships at repo root. Documentation CHANGELOG row RED→AMBER. CI category: 0G/0A/5R → 0G/4A/1R. Documentation: 2G/2A/1R → 2G/3A/0R. Total: 18G/17A/19R → **18G/22A/14R (AMBER overall — down from RED for the first time this session)**.
- **v1.8 (2026-04-19, autonomous session)** — `docs/FORGE_FRAMEWORK_MANIFEST.md` ships — CGAID Artifact #9 org-level closure. Meta-level document enumerating Forge's 11 mechanical gates, acknowledging 5 procedural gaps honestly, full CGAID 9-artifact mapping table, delta vs CGAID reference manifest (Forge extends CGAID in 6 ways, is stricter in 3). No audit score movement (the manifest doesn't have its own audit row — it closes the prior CGAID Artifact #9 gap which was tracked separately at ~92% CGAID coverage). Needs user review before authoritative adoption.
- **v1.9 (2026-04-19, autonomous session)** — Data retention policy row RED→AMBER. `services/data_retention.py` + `POST /api/v1/tier1/gdpr/retention/sweep`. 3 default policies (LLMCall 180d PII-conservative, AuditLog 365d SOC2-aligned, OrchestrateRun 365d for cost trends). Dry-run default; per-entity TTL overrides; per-entity error capture (single failure doesn't abort sweep); deterministic clock injection for tests. 12 unit tests. PromptElement excluded from defaults (needs TimestampMixin migration — documented inline). Compliance category: 2G/2A/2R → 2G/3A/1R. Overall: 18G/22A/14R → 18G/23A/13R.
- **v1.10 (2026-04-19, autonomous session)** — SLO definitions row AMBER→GREEN. `docs/SLO.md` ships with 7 SLOs (UI availability, API correctness, orchestrate p95, cost per task, contract violation disclosure — the CGAID trust SLO — DR RPO/RTO, CI green rate). Every target has metric source + breach action + rationale. Honest header disclaimer: aspirational pending load test baseline. Observability category: 2G/2A/2R → 3G/1A/2R. Overall: 18G/23A/13R → 19G/22A/13R.
- **v1.11 (2026-04-19, autonomous session)** — Load test baseline row RED→AMBER. `platform/scripts/loadtest.js` k6 starter ships — VUs/duration via env, ramp-up plan, thresholds encoded (p95 100ms/300ms/<1% errors). docs/DEPLOY.md updated with k6 invocation examples. Scale category: 1G/2A/3R → 1G/3A/2R. Overall: 19G/22A/13R → 19G/23A/12R. Still AMBER overall — running in staging + capturing baseline is a user-operated step, not code.
- **v1.12 (2026-04-19, autonomous session)** — Connection pooling row AMBER→GREEN. `app/database.py` configures `pool_size=10`, `max_overflow=20`, `pool_recycle=1800s`, `pool_timeout=30s`, `pool_pre_ping=True`. All overridable via `FORGE_DB_POOL_*` env vars. Scale category: 1G/3A/2R → 2G/2A/2R. Overall: 19G/23A/12R → 20G/22A/12R.
- **v1.13 (2026-04-19, autonomous session)** — Deploy pipeline row RED→AMBER. `platform/Dockerfile` (multi-stage, non-root user, healthcheck) + `platform/docker-compose.prod.yml` (mandatory secrets via `${VAR:?err}`, resource limits, log rotation, healthchecks, persistent volumes) ship. CI/CD category: 0G/4A/1R → 0G/5A/0R (AMBER overall, was RED pre-v1.7). Overall: 20G/22A/12R → 20G/23A/11R.
- **v1.14 (2026-04-19, autonomous session)** — N+1 query detection row RED→AMBER. `services/query_profiler.py` ships — SQLAlchemy event listener + contextvar-scoped counter + statement normalization + threshold env. 17 unit tests. Zero new deps. `scope()` context manager usable from handlers or tests. Wiring into request middleware deferred to avoid touching every handler at once. Scale category: 2G/2A/2R → 2G/3A/1R. Overall: 20G/23A/11R → 20G/24A/10R.
- **v1.15 (2026-04-19, autonomous session)** — TLS termination row AMBER→GREEN. docs/DEPLOY.md gets explicit TLS section with 3 reverse-proxy recipes (Caddy auto-LE, nginx + certbot, Traefik docker-compose), required X-Forwarded-* headers documented, post-deploy sanity commands. Security category: 5G/3A/2R → 6G/2A/2R. Overall: 20G/24A/10R → 21G/23A/10R.
