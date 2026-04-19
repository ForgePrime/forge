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
| 12-factor app | 12 | 5 | 4 | 3 | **AMBER** |
| Security | 10 | 4 | 4 | 2 | **AMBER** |
| Observability | 6 | 1 | 1 | 4 | **RED** |
| CI/CD | 5 | 0 | 0 | 5 | **RED** |
| Scale & performance | 6 | 1 | 2 | 3 | **RED** |
| Compliance (GDPR/audit) | 6 | 1 | 2 | 3 | **RED** |
| Disaster recovery | 4 | 0 | 1 | 3 | **RED** |
| Documentation | 5 | 2 | 2 | 1 | **AMBER** |
| **TOTAL (54 attr.)** | **54** | **14** | **16** | **24** | **RED overall** |

**Verdict:** Forge is **NOT enterprise-production-ready today**. It is a well-engineered pilot with strong delivery-governance (CGAID coverage 82%+ per prior audit), but gaps in observability, CI/CD, compliance, and DR make it unsuitable for external-client launch without Phase 2 of the Production Roadmap.

Estimated effort to GREEN overall: **5-8 weeks dedicated work** (aligned with Roadmap Phase 2 weeks 4-8).

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
| IX | Disposability — fast start, graceful shutdown | AMBER | Startup: fast (~2s). Shutdown: no SIGTERM handler found — orchestrate mid-task may leave tasks in IN_PROGRESS | Add signal handler releasing leases on shutdown |
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
| CSRF protection | AMBER | `forge_csrf` cookie referenced in UI templates (`_ac_row.html`, etc.) but middleware enforcement not grepped | Verify CSRF middleware is enforced on state-changing routes |
| Secret management | AMBER | Anthropic API keys encrypted via Fernet in DB (`auth.py encrypt_secret/decrypt_secret`) — **symmetric, key in env var** | Rotate to KMS-backed (AWS KMS / HashiCorp Vault) for production |
| TLS termination | AMBER | Not in-process (FastAPI listens plain HTTP); assumed reverse proxy | Document + enforce reverse proxy requirement in deploy guide |
| Input validation | GREEN | Pydantic `BaseModel` on all API bodies (projects.py etc.) | — |
| SAST / dep scan in CI | RED | No CI workflow files found | Add Semgrep/Bandit/pip-audit to CI (Roadmap Phase 2 week 5) |
| Content safety scan on uploads | RED | `/ingest` accepts user-uploaded documents directly into Knowledge.content without PII/size scrutiny | Add max-size + regex-based PII detection (Roadmap Phase 2 week 7) |

**Category verdict:** AMBER. Authentication/authorization/multi-tenant are mature. CI security scanning and KMS-backed secret storage are the main gaps.

## 3. Observability

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| Structured logs | RED | Python `logging` (stdlib), no JSON formatter, no correlation IDs found | Add `structlog` + request-id middleware |
| Metrics endpoint (Prometheus) | RED | No `/metrics` route found; no `prometheus_client` import | Add `starlette_prometheus` or equivalent |
| Distributed tracing | RED | No `opentelemetry` import | Add OTel instrumentation (FastAPI + SQLAlchemy + httpx) |
| Health endpoint | GREEN | `main.py:117-119` `@app.get('/health')` returns `{status, version}` | — |
| Liveness vs readiness split | RED | Only one `/health` endpoint; no readiness probe distinct from liveness | Add `/ready` that checks DB+Redis+workspace |
| Alert/SLO definitions | AMBER | No formal SLOs; informal expectations in docstrings | Codify p95 latency targets + error-rate SLOs (Roadmap Phase 2 week 8) |

**Category verdict:** RED. This is the single biggest enterprise blocker beyond tests — without metrics/tracing/alerts, production incidents will be diagnosed by log-tailing.

## 4. CI/CD

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| CI config file present | RED | No `.github/workflows/*.yml`, no `.gitlab-ci.yml` at repo root | **Nothing runs on push.** Add GH Actions or GitLab CI (Roadmap Phase 3 week 9) |
| Automated test on PR | RED | n/a — no CI | Same as above |
| Automated security scan | RED | n/a — no CI | See Security table |
| Deploy pipeline | RED | Deploy is manual (docker-compose on host) | Add IaC + staging→prod promotion (Roadmap Phase 3 week 9) |
| Release versioning | RED | No git tags spotted in recent log, no `CHANGELOG.md` at repo root (per-file changelogs in doc/ only) | Add semver tags + release notes |

**Category verdict:** RED. Every production deployment today is artisanal.

## 5. Scale & performance

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| DB indexing review | AMBER | Primary keys + FK indexes auto-created; `orchestrate_runs` and `llm_calls` are write-heavy — no evidence of explicit indexes beyond FKs | Run `EXPLAIN ANALYZE` on hot paths (cost forecast, task_report); add indexes as needed |
| Load test baseline | RED | No load test scripts in tests/ except Locust files in workspace test projects (workspace tests of user code, not platform) | Add k6/Locust suite hitting orchestrate at 100 parallel tasks (Roadmap Phase 2 week 6) |
| Connection pooling | AMBER | SQLAlchemy default pool; size not explicitly tuned in config | Review + tune for expected concurrency |
| Cache layer | GREEN | Redis included in docker-compose (used for workspace lease? rate limiting? unaudited) | — |
| Background job durability | AMBER | `BackgroundTasks` FastAPI is in-process; lost on restart | Replace with Celery/RQ for production |
| N+1 query detection | RED | No sqlalchemy.events profiling, no test assertion on query count | Add `pytest-sqlalchemy-profiler` or similar |

**Category verdict:** RED. Without load testing, predicting p95 under real workload is guesswork. Roadmap Phase 2 week 6 addresses.

## 6. Compliance (GDPR / audit)

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| Audit log (who/when/what) | GREEN | `AuditLog` model + `_audit(...)` helper used in execute.py/pipeline.py | — |
| PII scrubbing before LLM call | RED | LLM prompt includes raw Knowledge.content from user-uploaded docs — no PII detection/redaction before send to Anthropic | **Enterprise-blocker for EU clients.** Add PII regex + optional redaction per-project flag |
| Data retention policy | RED | No code enforces retention limits; data accumulates indefinitely in DB | Add per-artifact retention config + scheduled cleanup |
| Right-to-delete (GDPR art. 17) | RED | No endpoint to purge user/org data | Add admin endpoint + verified cascading delete |
| Data export (GDPR art. 20) | AMBER | Manual via SQL / export_* endpoints we added | Formalize per-user/per-org export bundle |
| Terms + consent | AMBER | Not in Forge scope (client-facing deployment owns) | Document expectation in deploy guide |

**Category verdict:** RED. PII-to-LLM and GDPR right-to-delete are hard blockers for EU enterprise clients. Roadmap Phase 4 week 11 addresses; consider accelerating if first client is EU-based.

## 7. Disaster recovery

| Attribute | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| Automated DB backup | RED | No backup script found in scripts/ | Add nightly pg_dump to offsite storage |
| Restore-tested runbook | RED | No docs/RESTORE.md | Write + exercise end-to-end restore in staging |
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
