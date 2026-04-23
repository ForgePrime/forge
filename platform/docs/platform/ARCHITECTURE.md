# Forge Platform — Architecture

> **Status:** DRAFT per [`../decisions/ADR-003`](../decisions/ADR-003-human-reviewer-normative-transition.md). Point-in-time snapshot 2026-04-23; file:line citations will rot — verify against current code before binding. Reference only, not normative.

## 1. What Forge is

**Forge Platform** is a web + API service that governs AI-driven software delivery. It orchestrates multi-step work with typed contracts, evidence-based gates, and audited LLM interactions. Where root-level Forge (`forge/.claude/CLAUDE.md`) is a CLI discipline for single-developer Claude Code sessions, **Platform** is the orchestrator + UI + audit plane for multi-tenant use.

**Not-goals.** Not a LangGraph clone. Not a multi-agent chat framework. Not a CI replacement. Not a full IDE. Stays focused on governance + orchestration + audit.

## 2. Tech stack

Confirmed from [`pyproject.toml`](../../pyproject.toml):

| Layer | Technology | Version |
|---|---|---|
| Language | Python | ≥ 3.11 |
| Web framework | FastAPI | ≥ 0.115.0 |
| ASGI server | uvicorn[standard] | ≥ 0.32.0 |
| ORM | SQLAlchemy | ≥ 2.0.35 (D-13 fix — < 2.0.35 crashes on Python 3.13) |
| Migration | Alembic | ≥ 1.14 |
| DB driver | psycopg2-binary | ≥ 2.9 |
| Data validation | Pydantic + pydantic-settings | ≥ 2.0 |
| Form parsing | python-multipart | ≥ 0.0.9 |
| Metrics | prometheus-client | ≥ 0.20 |
| Tracing | OpenTelemetry (API + SDK + FastAPI + SQLAlchemy + OTLP exporter) | ≥ 1.28 |
| Test | pytest + pytest-asyncio + httpx | dev extra |
| Lint | Ruff (line-length 120, target-version py311) | ≥ 0.8 |

**Database:** PostgreSQL (required — psycopg2 is the driver; no SQLite fallback in production).
**Cache / queue:** Redis (optional — opt-in via `settings.redis_url`; `/ready` probes it if configured).
**Templates:** Jinja2 + HTMX (server-side rendered UI under `app/templates/`).

## 3. Entry point + lifespan

From [`app/main.py`](../../app/main.py):

### Startup (lines 41-72)

```
1. Register all models (import app.models)
2. Base.metadata.create_all(bind=engine) — MVP: creates tables
3. Apply idempotent ALTERs (app.services.schema_migrations.apply)
4. Bootstrap default Organization + migrate orphan projects
5. Seed self anti-patterns (app.api.lessons.seed_self_anti_patterns)
6. P5.7 orphan recovery: flip RUNNING runs left by prior shutdown → INTERRUPTED
```

### Shutdown (lines 74-98)

```
1. Release IN_PROGRESS tasks back to TODO (lease returned)
2. Mark RUNNING orchestrate runs → INTERRUPTED
3. Best-effort — failures logged, never raised
```

Consequence: crashes do NOT leak "stuck RUNNING" state into the UI. Orphan recovery is symmetric at startup + shutdown.

### Liveness vs readiness split (lines 184-275)

- `GET /health` — liveness only. Returns 200 as long as the process can answer HTTP. Does NOT check DB/Redis (would create liveness-restart loops on transient blips).
- `GET /ready` — readiness. Checks DB (`SELECT 1`) + Redis (raw socket PING if configured). Returns 503 if any downstream unavailable, so load balancers skip this pod without triggering liveness restart.
- `GET /metrics` — Prometheus scrape endpoint, public (no auth — Prometheus servers don't carry session cookies; protect via network policy).

## 4. Middleware stack

From [`app/main.py:120-144`](../../app/main.py):

Order of **addition** (lines 120-144) — middleware added later runs FIRST on request:

```
RequestIdMiddleware       ← runs FIRST on request (added last)
MetricsMiddleware         ← always on, captures final status code
QueryProfilerMiddleware   ← OPT-IN via FORGE_PROFILE_NPLUS1=true
AuthMiddleware
CSRFMiddleware
RoleMiddleware
PageContextMiddleware     ← runs LAST on request (added first, after CORS)
CORSMiddleware            ← outermost
```

**Order of execution on a request** (reverse of add order + CORS is outermost because registered first):

```
CORS → RequestId → Metrics → [QueryProfiler if on] → Auth → CSRF → Role → PageContext → handler
```

**Key guarantees:**
- `RequestIdMiddleware` first → every log line carries `request_id` for correlation.
- `MetricsMiddleware` wraps the entire downstream → Prometheus captures the final status code.
- `AuthMiddleware` before Role → role check has an authenticated user.
- `PageContextMiddleware` last before handler → sidebar context ready for UI routes.

## 5. Routers (12)

Registered in `app/main.py:169-181`:

| Router | File | Purpose |
|---|---|---|
| auth | `api/auth.py` | sign-up, login, session |
| execute | `api/execute.py` | `GET /execute` (claim + assemble), `POST /execute/{id}/deliver`, `/heartbeat`, `/fail`, `/challenge` |
| projects | `api/projects.py` | project CRUD, AC CRUD, findings triage, decisions |
| pipeline | `api/pipeline.py` | orchestrate runs, plan, analyze, decisions |
| webhooks | `api/webhooks_api.py` | incoming webhook events |
| ai | `api/ai.py` | AI sidebar chat |
| tier1 | `api/tier1.py` | UX helpers: objective CRUD, AC CRUD, finding CRUD, backlog views |
| skills | `api/skills.py` | micro-skill registry |
| lessons | `api/lessons.py` | anti-pattern lessons learned |
| search | `api/search.py` | full-text search across entities |
| ui | `api/ui.py` | Jinja-rendered HTMX pages |
| share_router | `api/ui.py` | public share links |

MCP server is a **separate process** (`mcp_server/server.py`) that wraps the HTTP API with tool definitions for Claude Code. Tools: `forge_execute`, `forge_deliver`, `forge_decision`, `forge_finding`, `forge_challenge`, `forge_fail`.

## 6. Services layer (47 files)

Flat `app/services/` directory. Phase E of [`../ROADMAP.md`](../ROADMAP.md) refactors this into 6 diagonal modes (planning, evidence, execution, validation, governance, autonomy). Until then, services are categorized by function:

### Core orchestration
- `claude_cli.py` — external LLM call wrapper
- `crafter.py` — prompt crafter for "crafted" execution mode
- `test_runner.py` — Phase A executable tests (Forge runs pytest itself after delivery, doesn't trust completion_claims)
- `challenger.py` — independent LLM verification (P23 Verification Independence)
- `scenario_generator.py` — heuristic test-stub generation (basis for P25 deterministic synthesis)

### Validation / gates
- `contract_validator.py` — validates delivery against output contract (14+ checks)
- `plan_gate.py` — validates plan requirement_refs (P5.3 traceability)
- `coverage_analyzer.py` — source-term coverage (Knowledge SRC-NNN terms in AC)

### Evidence / export
- `delivery_extractor.py` — pulls structured evidence from reasoning
- `adr_exporter.py` — exports Decision → `.ai/decisions/NNN-*.md` in project repo
- `handoff_exporter.py` — CGAID Handoff Document artifact
- `plan_exporter.py` — Plan artifact
- `skill_log_exporter.py` — Skill Change Log artifact
- `snippet_extractor.py` — quoted evidence extraction
- `diff_renderer.py` — git-diff rendering for UI

### State machine / lifecycle
- `pipeline_state.py` — orchestrate run state transitions
- `orphan_recovery.py` — startup/shutdown stuck-state cleanup
- `schema_migrations.py` — idempotent ALTERs on startup
- `hooks_runner.py` — execute `ProjectHook` triggers

### Policy / governance
- `autonomy.py` — L1–L5 autonomy levels + promotion criteria
- `budget_guard.py` — per-task / per-run USD budget veto
- `kr_measurer.py` — Key Result measurement runner

### Context / memory
- `page_context.py` — UI sidebar context per route (orthogonal to causal context projection in `../FORMAL_PROPERTIES_v2.md` P15)
- `kb_scope.py` — Knowledge scope filtering
- `prompt_parser.py` — prompt assembly (7 sections P0–P7)

### Infrastructure
- `auth.py` — API key + session auth
- `csrf.py` — CSRF protection
- `rate_limit.py` — per-endpoint rate limiting
- `tenant.py` — multi-tenant isolation
- `metrics.py` — Prometheus metrics middleware + render
- `tracing.py` — OpenTelemetry setup (opt-in)
- `logging_setup.py` — structured logging + RequestIdMiddleware
- `query_profiler.py` — N+1 query detector (opt-in)

### Data handling
- `pii_scanner.py` — PII detection
- `data_retention.py` — retention policy enforcement
- `gdpr_export.py` — GDPR export
- `git_verify.py` — git state verification
- `github_pr.py` — GitHub PR integration

### UI helpers
- `ai_chat.py` — sidebar chat handler
- `docs_toc.py` — documentation TOC
- `slash_commands.py` — slash command registry
- `time_format.py` — relative time formatting
- `webhooks.py` — outbound webhook delivery
- `workspace_browser.py` — file-tree browser
- `workspace_infra.py` — workspace initialization
- `skill_attach.py`, `skill_lift.py` — skill runtime attachment
- `kb_crawl.py` — knowledge base crawl

## 7. Models layer (30 entities)

Full list in [`DATA_MODEL.md`](DATA_MODEL.md). Grouped by CGAID Layer per [`../FRAMEWORK_MAPPING.md §4`](../FRAMEWORK_MAPPING.md):

**Layer 1 (Principles)** — reference only, no models.

**Layer 2 (Tooling):**
- `MicroSkill` — project-tailored skills
- `Guideline` — shared instructions
- `Knowledge` — source docs (SRC-NNN)
- `AIInteraction`, `LLMCall` — LLM call audit

**Layer 3 (Delivery):**
- `Project`, `Objective`, `KeyResult`, `ObjectiveReopen` — business goals
- `Task`, `AcceptanceCriterion`, `task_dependencies` — work decomposition
- `Execution`, `ExecutionAttempt` — run state machine
- `OrchestrateRun` — multi-task pipeline runs
- `PromptSection`, `PromptElement` — prompt assembly audit
- `Change` — file-level modifications
- `Finding` — detected issues / opportunities
- `TestRun` — Phase A test execution records

**Layer 4 (Control):**
- `Decision` — ADR-equivalent decisions
- `OutputContract` — per-task_type × ceremony contract definitions
- `ContractRevision` — contract versioning
- `ProjectHook`, `HookRun` — automation hooks
- `AuditLog` — cross-cutting audit

**Meta:**
- `Organization`, `User`, `Membership` — tenant + access
- `Lessons` — anti-pattern learnings
- `Comment` — threaded comments
- `Webhook` — outbound webhook config

## 8. Observability

### Metrics (`/metrics`)

Always on (`prometheus-client` dep). Middleware captures per-request:
- `forge_http_requests_total{method, path, status}` — counter
- `forge_http_request_duration_seconds{method, path}` — histogram
- Custom business metrics via `MetricsMiddleware` + `render_metrics()`

Phase G3 [`../ROADMAP.md §10`](../ROADMAP.md) adds 7 CGAID metrics (M1–M7) as separate service.

### Tracing (`FORGE_OTEL_ENABLED=true`)

Opt-in. When enabled:
- `FastAPIInstrumentor` wraps every request span.
- `SQLAlchemyInstrumentor` adds DB query spans.
- OTLP exporter ships to configured collector.

Deps installed always (one-flag-flip vs dep-add-op).

### Logging

Structured. `RequestIdMiddleware` injects `request_id` into every log record. If `FORGE_LOG_JSON=true`, JSON format for log aggregators.

### N+1 query profiler (`FORGE_PROFILE_NPLUS1=true`)

Opt-in diagnostic. When off = no-op pass-through (zero overhead).

## 9. Security posture

### Auth

- API key authentication ([ASSUMED per IMPLEMENTATION_TRACKER.md:134] status NOT DONE / PARTIAL — verify Pre-flight Stage 0.3).
- Session cookies for UI.
- CSRF middleware on state-mutating POSTs.

### Multi-tenant

- `Organization` → `Project` → `Task` hierarchy.
- `tenant.py` enforces org isolation.
- `Membership` defines user roles per org.

### Data handling

- `pii_scanner.py` — detects PII in user content.
- `data_retention.py` — retention sweeps (configurable per org).
- `gdpr_export.py` — per-user data export.
- CGAID Stage 0 classification: **NOT IMPLEMENTED** — see Phase G1 in [`../ROADMAP.md §10`](../ROADMAP.md). Until implemented, Forge is **not certified for Confidential+ processing without deployed DLP** (deep-risk R-FW-02 CRITICAL).

## 10. Deployment model

### Local dev (from [`../../README.md`](../../README.md))

```bash
cd platform
cp .env.example .env
docker compose up -d postgres redis
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/ui/signup`.

### Production

`docs/DEPLOY.md` — **does not yet exist** (tracked doc gap; see `platform/README.md` note).

Suggested shape (not prescriptive yet):
- Container runtime: Docker Compose for single-node; Kubernetes for multi-node.
- Reverse proxy: nginx / Traefik / CloudFront with TLS termination.
- DB: managed Postgres (Azure Flexible, AWS RDS, GCP Cloud SQL).
- Redis: optional; enables rate limiting + background queue.
- Secrets: env vars via Vault / secret manager; never in git.
- Backups: DB snapshots (daily) + WAL shipping.
- Observability: Prometheus scrape + OTEL collector endpoint.

This deploy doc will be written as part of Phase G or when first production deployment lands.

## 11. Configuration

From `app/config.py` (via Pydantic Settings):

- `default_org_slug`, `default_org_name` — bootstrap org for pilots
- `api_host`, `api_port` — bind
- `redis_url` (optional) — enables Redis-dependent features
- `FORGE_PROFILE_NPLUS1` (env, boolean) — opt-in N+1 profiler
- `FORGE_OTEL_ENABLED` (env, boolean) — opt-in OpenTelemetry
- `FORGE_LOG_JSON` (env, boolean) — JSON logging
- `VERDICT_ENGINE_MODE` (env, `off|shadow|enforce`) — Phase A toggle (not yet implemented; see [`../ROADMAP.md §4`](../ROADMAP.md))
- `CAUSAL_PROJECTION` (env, boolean) — Phase B toggle
- `STAGE0_ENFORCEMENT` (env, `off|log_only|enforce`) — Phase G toggle

## 12. Key invariants (CheckConstraints)

Database-level enforced:

- `Execution.status ∈ {PROMPT_ASSEMBLED, IN_PROGRESS, DELIVERED, VALIDATING, ACCEPTED, REJECTED, EXPIRED, FAILED}` (execution.py:14-19). Phase F adds `BLOCKED`.
- `Task.status ∈ {TODO, CLAIMING, IN_PROGRESS, DONE, FAILED, SKIPPED}` (task.py:33-36).
- `Task.type ∈ {feature, bug, chore, investigation, analysis, planning, develop, documentation}` (task.py:29-30).
- `AcceptanceCriterion.scenario_type ∈ {positive, negative, edge_case, regression}` (task.py:86-88). ADR-001 extends to 9 values in Phase F.
- `AcceptanceCriterion.verification ∈ {test, command, manual}` (task.py:89-92).
- `Decision.status ∈ {OPEN, CLOSED, DEFERRED, ANALYZING, MITIGATED, ACCEPTED}` (decision.py:12).
- `Finding.status ∈ {OPEN, APPROVED, DEFERRED, REJECTED, DISMISSED, ACCEPTED}` (finding.py:15).
- `Finding.type`, `Finding.severity` — enumerated (finding.py:13-14).
- `task_dependencies.no_self_dep` — task cannot depend on itself (task.py:15).
- `Task.task_has_content` — instruction OR description required (task.py:22-25).
- `KeyResult.kr_type ∈ {numeric, descriptive}` (objective.py:62).

Phase E [`../ROADMAP.md §8`](../ROADMAP.md) makes these first-class `Invariant` entities registered per transition, evaluated by `VerdictEngine.commit()`.

## 13. Scaling assumptions

- **Single-node sufficient for initial deployment.** Postgres + FastAPI on one host serves pilot.
- **Horizontal scale by org.** Multi-tenant in one DB; scale by sharding on `organization_id` if needed.
- **Background work via threads.** No Celery / Temporal yet — orchestrate runs execute synchronously per API call. Heavy work (test running, coverage analysis) runs in-process; may move to worker queue later if needed.
- **LLM call concurrency.** Bounded by `budget_guard` per-run + per-task caps + per-tenant quota (`tenant.py`).

## 14. What this document does not cover

- **Individual service deep-dives.** See `app/services/<name>.py` — each has module docstring.
- **Individual model field semantics.** See `app/models/<name>.py` + [`DATA_MODEL.md`](DATA_MODEL.md).
- **Router endpoint list.** Auto-generated at `/docs` (FastAPI Swagger) + `/redoc` (ReDoc).
- **Deployment runbooks.** Gap tracked in `../README.md`.
- **Incident response.** Planned post Phase G4 Rule Lifecycle.

## 15. Cross-references

- [`WORKFLOW.md`](WORKFLOW.md) — how work executes end-to-end.
- [`DATA_MODEL.md`](DATA_MODEL.md) — 30 entities + relationships + invariants.
- [`ONBOARDING.md`](ONBOARDING.md) — first contribution tutorial.
- [`../FORMAL_PROPERTIES_v2.md`](../FORMAL_PROPERTIES_v2.md) — 25 atomic properties this architecture must satisfy.
- [`../GAP_ANALYSIS_v2.md`](../GAP_ANALYSIS_v2.md) — gaps vs spec per property.
- [`../ROADMAP.md`](../ROADMAP.md) — phases that close gaps.
- [`../FRAMEWORK_MAPPING.md`](../FRAMEWORK_MAPPING.md) — CGAID positioning.
