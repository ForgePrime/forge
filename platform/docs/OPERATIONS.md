# OPERATIONS.md — L6 Operations Specification

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-25
**Depends on:** INTEGRATIONS.md (adapter health for `/health`); UX_DESIGN.md (operator-facing pages); PLAN_GOVERNANCE.md G_GOV (audit trail for incident response).
**Source spec:** MASTER_IMPLEMENTATION_PLAN §3 L6; MVP_SCOPE.md §L6 (Docker Compose + Render.com + JSON logs); FORMAL_PROPERTIES_v2.md P5 (reversibility for ops actions); ADR-006 (model pinning impacts ops).
**Scope:** deployment topology, configuration, secrets, observability, backup/restore, disaster recovery, security baseline.

> **Known unverified claim (CONTRACT §A.6):** Operations correctness is empirical — verified by drills, soak tests, and post-incident review, not by structural exit tests alone. This doc specifies the *minimum operational baseline* for MVP (single-tenant local + single hosted). Multi-tenant production-hardening (HA Postgres, blue-green deploy, geographic DR) is explicitly out of MVP scope and deferred to Phase 3 per MVP_SCOPE §3.

---

## 1. Deployment topologies

### 1.1 Local (developer / design partner)

**Stack:** `docker-compose up`

```yaml
services:
  postgres: 16-alpine, port 5432, volume forge_pgdata
  redis: 7-alpine, port 6379, ephemeral
  forge_worker: python:3.13-slim, port 8000, mounts var/repos + var/worktrees
  forge_web: node:20-alpine + Next.js, port 3000
```

**Resource profile (target):**
- RAM: 4 GB total (Postgres 1 GB, worker 2 GB for repo clones + LLM call buffers, web 512 MB, redis 256 MB).
- Disk: 5 GB initial; grows with `var/repos/` (1 git clone per Project, ~50-500 MB each).
- CPU: 4 cores comfortable, 2 cores minimum.

**Bring-up sequence:**
1. `docker-compose up` (60s typical).
2. Health gate: each service must report ready before next dependency starts (compose `depends_on: { service: { condition: service_healthy } }`).
3. Alembic migration auto-runs on worker startup; failure → worker exits non-zero, compose halts.
4. `/health` GET returns 200 within 90s of `docker-compose up` on a fresh clone.

**MVP exit criterion:** `docker-compose up && curl localhost:8000/health` → all green within 2 min on a fresh clone (per MVP_SCOPE §4).

### 1.2 Hosted (Render.com — MVP target)

**Why Render.com:**
- Free tier sufficient for MVP demo (1 web + 1 worker + 1 postgres on free).
- Simple deployment (Git push → auto-deploy).
- Postgres managed (point-in-time restore included).
- No vendor lock-in beyond `render.yaml`.

**`render.yaml` skeleton:**

```yaml
services:
  - type: web
    name: forge-web
    env: docker
    plan: free
    healthCheckPath: /health
  - type: worker
    name: forge-worker
    env: docker
    plan: free
databases:
  - name: forge-pg
    plan: free
```

**Hosted-only differences from local:**
- HTTPS termination at Render's edge.
- Postgres connection via managed connection string injected as env.
- Worktrees on ephemeral disk; lost on deploy. Phase 3 needs persistent volume or S3-backed worktrees.
- Logs streamed to Render's log aggregator; can be exported to Logfire/Datadog (Phase 2).

### 1.3 Phase 2-3 deferred topologies

- Self-hosted (k8s, ECS, Fly.io) — requires Helm chart / Terraform module.
- Multi-tenant SaaS — requires tenant isolation (DB schema per tenant or row-level), per-tenant secrets, billing integration.
- HA Postgres (read replicas, primary/standby) — production-grade only.
- Geographic DR (multi-region replication) — enterprise-grade only.

All are scaffolded via the `12-factor` discipline below; no MVP code prevents them.

---

## 2. Configuration & secrets

### 2.1 12-factor compliance

- **Config in env**: every config value comes from env var; no hardcoded paths/URLs/keys.
- **Strict separation**: code in repo, config in env, secrets in env / secret manager.
- **Stateless processes**: workers can be killed/restarted without data loss (state in DB, not memory).
- **Port binding**: services declare ports via env (`PORT`, `WEB_PORT`).
- **Disposability**: graceful shutdown on SIGTERM (worker drains in-flight Executions to BLOCKED state with `reason='shutdown'` rather than abandoning).

### 2.2 Required env vars (MVP)

```
DATABASE_URL                   # postgresql://...
REDIS_URL                      # redis://...
ANTHROPIC_API_KEY              # sk-ant-...
GITHUB_APP_ID                  # numeric (App preferred)
GITHUB_APP_PRIVATE_KEY         # PEM (App)
GITHUB_PAT                     # ghp_... (PAT fallback for local dev)
GITHUB_WEBHOOK_SECRET          # HMAC secret for webhook signatures
FORGE_BASE_URL                 # https://... or http://localhost:8000
LOG_LEVEL                      # INFO | DEBUG | WARN
LLM_ROUTER_MODE                # sonnet_only (MVP) | full (Phase 2+)
TIMELY_DELIVERY_MODE           # WARN (MVP) | REJECT (Phase 2 after G_{E.1})
VERDICT_ENGINE_MODE            # off (initial) | shadow (A.3) | enforce (A.4)
```

### 2.3 Secret handling

**MVP approach:**
- Local: `.env` file at project root, gitignored. `.env.example` checked into repo with placeholders + comments.
- Render.com: env vars set in dashboard; never logged; never echoed in `/health`.
- CI: secrets via GitHub Actions encrypted secrets.

**Bans (CONTRACT §change-discipline):**
- No secrets in commit messages, log lines, or error messages.
- No secrets in PR descriptions (Forge generates these — secrets must never appear via prompt-injection of envvar values into prompts).
- No secrets in `forge audit <change-id>` JSON output (test asserts no `sk-`, `ghp_`, `Bearer `, etc. patterns).

**Secret rotation (MVP — manual):**
- Document procedure in `docs/runbooks/rotate-secrets.md` (one runbook per secret class: GitHub PAT, GitHub App key, Anthropic key, webhook secret, DB password).
- Rotation cadence: 90 days for API keys; immediate on any suspected leak.
- Phase 2: integrate with Doppler / 1Password / AWS Secrets Manager for automated rotation.

---

## 3. Observability

### 3.1 Logging

**Format:** structured JSON to stdout. One event per line. Fields:

```json
{
  "ts": "2026-04-25T14:30:00.123Z",
  "level": "INFO",
  "service": "forge-worker",
  "execution_id": "uuid",
  "event": "Execution.completed",
  "duration_ms": 4523,
  "status": "DONE",
  "trace_id": "uuid",
  "span_id": "uuid"
}
```

**Levels:**
- `DEBUG` — disabled in production by default; enable via `LOG_LEVEL=DEBUG` for forensic.
- `INFO` — normal operations; lifecycle events (Execution.started/completed); Verdicts.
- `WARN` — non-blocking issues (rate-limit nearing, fallback model used, retry succeeded).
- `ERROR` — Execution failed / BLOCKED with cause.
- `CRITICAL` — system-level emergency (kill-criteria triggered, DB lost, secret leak detected).

**Banned log content (regression test):**
- Secret patterns (`sk-ant-`, `ghp_`, `Bearer `, etc. — see secret patterns in `tests/test_log_safety.py`).
- Full prompt content at INFO level (only at DEBUG for forensic; WARN logs prompt checksum only, per L3.6).
- LLM response content at INFO level (same — checksum only).

### 3.2 Metrics

**MVP metrics (basic):**
- HTTP request count + latency per endpoint (`fastapi-prometheus` or similar).
- Execution lifecycle: count by status, duration P50/P95/P99.
- LLM cost: cumulative per Project, per quarter (per L3.6).
- DB connection pool: active, idle, waiters.

**MVP exposure:**
- `GET /metrics` (Prometheus format) — protected by auth or IP allowlist (not publicly exposed).
- `/health` returns subset for human readability (per INTEGRATIONS.md §8).

**Phase 2 metrics (planned):**
- 7 CGAID metrics (G.3) backend-ready, dashboard UI deferred.
- 5 MASTER §3 L7 outcomes (Quality, Cost, Latency, UX, Reliability) — composed from MVP metrics + benchmark scores from QUALITY_EVALUATION.md.
- Per-capability breakdowns.

### 3.3 Tracing

**MVP:** OpenTelemetry starter already in place (commit `e9f6ad3`). Per-Execution trace ID propagates through worker → LLM call → tool dispatch.

**Phase 2 additions:**
- Span hierarchy (per ADR pending).
- Sampling strategy (10% + 100% on errors per ADR).
- Export to Logfire / Honeycomb / Datadog (per INTEGRATIONS.md §6).

### 3.4 Alerting (Phase 2)

**MVP:** alerts via stdout logs + manual grep. No automated paging.

**Phase 2 alert classes (planned):**
- CRITICAL events (kill-criteria, secret leak) → PagerDuty / Opsgenie.
- HIGH Findings unresolved > 24h → Slack channel.
- Cost overrun (L3.6 post-hoc) → Slack channel.
- /health returning non-200 for > 5 min → PagerDuty.

---

## 4. Backup & restore

### 4.1 Database backup

**MVP (local):**
- `pg_dump` script in `scripts/backup_db.sh` runnable manually.
- Schedule: documented in runbook, not automated for local-dev.

**MVP (hosted on Render):**
- Render.com Postgres includes daily automated backups + point-in-time restore (free tier: 24h retention; paid tier: 7-30 days).
- No additional Forge-side backup logic needed at MVP.

**Phase 2 production:**
- Hourly snapshots to S3 / GCS via `pgbackrest` or equivalent.
- 30-day retention minimum; tiered storage for older.
- Quarterly restore drill (verified runbook).

### 4.2 Worktree / repo state

**MVP:** worktrees and repo clones in `var/` are reproducible from GitHub — not backed up. On data loss, re-clone is automatic on next Execution.

**Phase 2:** worktrees on persistent volume; repos cached in S3 to reduce re-clone cost.

### 4.3 Audit-trail durability

**MVP:** all governance entities (Executions, Decisions, Changes, Findings, EvidenceSets, llm_calls) persist in Postgres → covered by §4.1 backup.

**Phase 2:** append-only audit log mirror to S3 / WORM bucket for compliance retention (regulatory may require 7-year retention even after DB rotation).

### 4.4 Restore drill (MVP exit gate)

```bash
# Drill: simulated DB loss
1. docker-compose down -v        # destroys Postgres volume
2. docker-compose up              # fresh DB, alembic auto-migrates
3. Forge restarts → /health green within 2 min
4. (Phase 2) Restore from backup → governance state recovered
```

For MVP, full state-loss recovery means re-running Executions from GitHub Issues. Acceptable for single-user local; not for multi-user.

---

## 5. Disaster recovery

### 5.1 Failure classes (per OPERATIONS L6 mandate)

| # | Failure class | MVP recovery | Phase 2-3 recovery |
|---|---|---|---|
| 1 | Worker crash mid-Execution | SIGTERM handler drains to BLOCKED; restart resumes from BLOCKED state via `forge resume <execution-id>` | Same + retry budget per L3.5 |
| 2 | Postgres DB lost | Restore from backup (hosted) / manual recovery (local) | Point-in-time restore < 1h |
| 3 | LLM provider down | Fallback chain (L3.4); if all unavailable → BLOCKED with reason | Multi-provider failover (Anthropic + OpenAI + provider TBD) |
| 4 | GitHub API down | Webhook events queued at GitHub side (replayed via delivery_id); local operations continue on cached repos | Same + cached read fallback |
| 5 | Disk full | Worktree cleanup runs aggressively; alert at 80% | Auto-scale storage |
| 6 | Memory leak in worker | Per-Execution memory cap; OOM kill restarts worker | + memory profiling in CI |
| 7 | Network partition | Health check fails → load balancer routes away; retries idempotent ops | Multi-region active-active |
| 8 | Compromised secret | Rotation runbook; revoke at provider; re-deploy with new secret | Auto-rotation per §2.3 Phase 2 |
| 9 | Bad deploy (regression) | Rollback via Render.com previous-deploy button; PR revert | Blue-green deploy with smoke tests |
| 10 | Data corruption | Restore from last known-good backup | Multi-DB state validation |
| 11 | Webhook signature compromise | Rotate webhook secret; replay events with new secret; re-process | Same |
| 12 | Forge prompt-injection compromise | Detect via canary EvidenceSet rows + grep-gate; quarantine Execution; manual incident response | Automated detection per AUTONOMOUS_AGENT_FAILURE_MODES.md §6 |
| 13 | LLM output prompt-injection of Forge | F.10 StructuredTransferGate prevents NL-only paths; F.11 multi-candidate prevents single-source dependence; output schema-validated | Same + detection patterns |
| 14 | Steward unavailability | Per ADR-007 rotation; CRITICAL decisions queue at BLOCKED with `reason='steward_unavailable'` | Multi-Steward quorum |

### 5.2 RTO / RPO targets (MVP)

- **RTO** (recovery time objective): worker / web restart < 5 min; full re-deploy < 30 min.
- **RPO** (recovery point objective): backup cadence determines this. Render.com free tier = 24h RPO; paid tier 1h RPO.

### 5.3 Phase 2-3 RTO / RPO

- RTO target: < 15 min for any single-component failure.
- RPO target: < 1h for governance entity loss.
- Achieved via §4.3 phase-2 hourly backups + §1.3 multi-region.

### 5.4 Drill cadence (Phase 2 ops gate)

- DB restore drill: quarterly.
- Failover drill (multi-provider LLM): quarterly.
- Secret rotation drill: per rotation event (90-day cycle).
- Full DR drill (simulated multi-region failure): annually.

---

## 6. Security baseline

### 6.1 Network

- All public endpoints HTTPS-only (HSTS header enforced).
- Webhook endpoint validates HMAC-SHA256 signature (per INTEGRATIONS.md §2).
- `/metrics` not publicly exposed; behind auth or IP allowlist.
- No outbound network from worker except: GitHub, Anthropic (allowlisted), Postgres, Redis. Egress proxy or firewall rules enforce.

### 6.2 Code

- Dependencies pinned via `uv.lock` / `package-lock.json`; CI verifies no drift.
- `pip-audit` / `npm audit` in CI pipeline; HIGH vulnerabilities block merge.
- No `eval`, `exec`, dynamic import in `app/` (linter rule + grep-gate).
- All shell-out to subprocess uses `shlex.quote` or array form (no string interpolation).

### 6.3 Auth (MVP minimal)

- No login required at MVP (single-user local deployment).
- Cookie-based session scaffolded but disabled by default.
- Phase 2: GitHub OAuth login for hosted multi-user.
- Phase 3: SSO (SAML / OIDC) for enterprise.

### 6.4 Audit logs (security-relevant)

- All adapter operations logged with caller identity (when auth enabled).
- All Steward sign-offs (G.5) logged with `signed_at`, `signer_id`, `decision_id`.
- All resolve-uncertainty (F.4) logged with `accepted_by`, `accepted_role`, `execution_id`.
- All BLOCKED Execution kill-criteria triggers (G.1) logged with `severity=CRITICAL`.

### 6.5 Data classification (forward reference)

Per PLAN_GOVERNANCE.md G.1, the DataClassification gate kicks in pre-ingest for Knowledge / Decision external quotes. MVP minimum: `public` and `internal` tiers acceptable; `confidential` and `secret` BLOCKED until DLP mechanism (ADR-018) closed.

### 6.6 Threat model (MVP — explicit)

| Threat | MVP mitigation | Phase 2-3 strengthening |
|---|---|---|
| Prompt injection from external content | F.10 StructuredTransferGate; content escaping in PromptAssembler | Pattern-detection + quarantine |
| Secret leak via prompt | Test asserts no secret patterns in `forge audit` output; logs sanitized | Auto-redaction + DLP |
| Webhook spoofing | HMAC-SHA256 signature verification | + IP allowlisting at Render edge |
| Compromised provider key | Manual rotation runbook | Auto-rotation per §2.3 Phase 2 |
| Hostile PR closing | GitHub App scopes minimal (no admin) | + branch protection rules |
| Supply-chain attack on dependencies | Dependency pinning + `pip-audit` | + signed releases (sigstore) |
| Forge rogue auto-action | Authority levels (L3.2); Steward sign-off for CRITICAL; F.4 BLOCKED for ambiguity | + per-action whitelist |

---

## 7. Operational runbooks (MVP minimum)

The following runbooks live in `docs/runbooks/` (one Markdown file each):

1. `bring-up-local.md` — `docker-compose up` walkthrough + common errors.
2. `bring-up-render.md` — Render.com deploy walkthrough.
3. `rotate-secrets.md` — per-secret-class rotation procedure.
4. `restore-db.md` — restore from backup (local + hosted).
5. `incident-response.md` — first response template (containment, evidence preservation, postmortem).
6. `unblock-execution.md` — diagnostic flow for BLOCKED Executions.
7. `cost-overrun.md` — diagnostic flow for L3.6 cost overrun Findings.
8. `webhook-debug.md` — debugging GitHub webhook delivery issues.

Each runbook follows the CONTRACT §B.5 evidence-first template. Existence of these 8 runbooks before MVP-ship is a hard exit criterion.

---

## 8. Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | Env vars validated at startup (Pydantic BaseSettings); missing required → exit non-zero with named missing var; empty config files → fail-fast not silent default |
| 2 | timeout_or_dependency_failure | Handled | Per-component health check; service `depends_on` with `condition: service_healthy` in compose; SIGTERM graceful drain; LLM provider unavailability handled per L3.4 fallback |
| 3 | repeated_execution | Handled | Idempotent migration (alembic); idempotent secret rotation (each runbook is idempotent — re-running is safe); webhook event dedup per `delivery_id` |
| 4 | missing_permissions | Handled | GitHub adapter init checks scopes; LLM provider 401 → `/health` reports specific cause; secrets-leak detector grep blocks any leak in audit output |
| 5 | migration_or_old_data_shape | Handled | Alembic round-trip required at every migration (existing tests); `ALTER TABLE` migrations dry-run on prod-like fixture before deploy; rollback via `down_revision` always provided |
| 6 | frontend_not_updated | Handled | `/health` JSON shape stable + versioned; UX_DESIGN.md §10 audit JSON shape versioned per ADR-013 |
| 7 | rollback_or_restore | Handled | Render.com previous-deploy rollback button; backup runbook §4; feature-flag rollback for behaviorally risky changes (every flag pair has WARN→REJECT and reverse path) |
| 8 | monday_morning_user_state | Handled | Stateless processes; restart loses no governance state (DB-backed); local dev survives `docker-compose down && up` because volumes persist; hosted survives deploy because Render preserves DB |
| 9 | warsaw_missing_data | JustifiedNotApplicable | Operations is platform-level; no geographic data dimension (multi-region is Phase 3 deferred per §1.3) |

---

## 9. Open questions

| # | Question | Blocks |
|---|---|---|
| Q1 | Render.com free-tier sleep-on-idle (15 min) — acceptable for MVP demo? Trade-off: free vs $7/mo for always-on | MVP-ship |
| Q2 | Backup retention for hosted: 24h free tier vs 7-day paid — MVP can ride free initially | MVP-ship |
| Q3 | Worktree storage at scale: how big is a typical 10k-LOC repo + worktree? Benchmark before Phase 1 to size disk allocation | Phase 1 capacity planning |
| Q4 | Logfire vs Datadog vs OTel-only for Phase 2 observability — ADR pending | Phase 2 |
| Q5 | Postgres connection pool size — MVP starts at 10 (default); benchmark before Phase 1 to size correctly | Phase 1 capacity planning |
| Q6 | Worker concurrency: 1 Execution at a time per Project (MVP_SCOPE §3) — when does multi-Execution-per-project become safe? Requires CausalEdge cycle invariants under concurrent insert | Phase 2 |
| Q7 | TLS at edge or end-to-end? Render terminates TLS at edge (sufficient for MVP); end-to-end requires service-mesh-like setup (Phase 3) | Phase 3 |

---

## 10. Authorship + versioning

- v1 (2026-04-25) — initial L6 spec; Docker Compose local + Render hosted; 14 failure classes mapped; 8 runbooks declared.
- Updates require explicit version bump + distinct-actor review per ADR-003.
