# Forge Platform — Deployment Runbook

**Status:** PILOT-quality (covers what exists). Production-grade deployment (cloud IaC, auto-scaling, multi-region DR) is Roadmap Phase 3.

## Deployment targets matrix

| Target | Status | When to use |
|--------|--------|-------------|
| **Local dev** | GREEN | daily development, unit tests, HTTP integration tests |
| **Single-host docker-compose** | AMBER | internal pilot, single team, ≤ 5 concurrent orgs |
| **Cloud (AWS/GCP/Azure) via IaC** | RED | NOT READY — Roadmap Phase 3 week 9 deliverable |
| **Multi-region HA** | RED | NOT READY — v2 candidate |

This document covers the first two. Production cloud deployment is a separate runbook to be written when IaC lands.

---

## Prerequisites

### Software
- Docker 24+ (or Rancher Desktop)
- Python 3.13 (for local dev without Docker)
- `uv` (recommended) or `pip` for Python deps
- Git 2.40+

### External services
- **Anthropic API key** — required unless using Claude Code CLI auth via Max subscription mount (see docker-compose.yml:25)
- **SMTP** (optional) — only if email alerts are configured
- **Object storage** (optional, production) — for workspace artifact durability

### Secrets you need to set
- `FORGE_JWT_SECRET` — **MANDATORY in prod**. 256-bit random. Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `POSTGRES_PASSWORD` — non-default before exposing beyond localhost
- `ANTHROPIC_API_KEY` — per-org via UI is preferred; global env var is fallback for dev

---

## Local dev (laptop)

```bash
cd platform
cp .env.example .env                    # edit as needed
docker compose up -d postgres redis     # start DB + cache only
uv sync                                  # install Python deps
uv run uvicorn app.main:app --reload --port 8000
```

Sanity:
```bash
curl http://localhost:8000/health        # → {"status":"ok","version":"0.1.0"}
curl http://localhost:8000/docs          # OpenAPI UI
```

First signup at http://localhost:8000/ui/signup.

**Teardown:**
```bash
docker compose down           # keeps data volumes
docker compose down -v        # wipes data volumes (destructive)
```

---

## Single-host docker-compose (internal pilot)

Full stack in one compose file. Suitable for team of ≤10 over a VPN.

```bash
cd platform
# 1. Set secrets
export FORGE_JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export POSTGRES_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(16))")
# 2. Put into .env (committed template, actual values in untracked .env)
# 3. Bring stack up
docker compose up -d
docker compose logs -f forge-api        # watch for schema_migrations success + readiness
```

### TLS termination
docker-compose does NOT terminate TLS. Front with nginx/Caddy/Traefik:

```
# Caddyfile example
forge.internal.example.com {
  reverse_proxy localhost:8000
}
```

### Firewall rules (recommended)
- Only 443 from team network
- 5432 (postgres), 6379 (redis), 8000 (api) — **localhost-only** (compose binds to 127.0.0.1 by default for postgres/redis)

---

## Schema migrations

Forge runs additive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` at every startup via `app.services.schema_migrations:apply()`. This means:

- **Safe:** idempotent; re-running is a no-op
- **Limitation:** the live app instance must be restarted to pick up a new migration entry. Rolling restart is fine.
- **Incident pattern:** if you added a column but forgot to restart and the running app starts querying it, SELECT fails. Remediation: `docker exec platform-db-1 psql -U forge -d forge_platform -c "ALTER TABLE <x> ADD COLUMN IF NOT EXISTS <col> <type>;"` then restart when convenient.

See `platform/app/services/schema_migrations.py` for the PENDING_COLUMNS list.

---

## Backup (pilot-tier)

**Current state:** no automated backup (Enterprise Audit item #5, RED). Before any client-visible deployment, add one of:

### Option A — cron'd pg_dump to S3 (minimum)
```bash
# /etc/cron.d/forge-backup  — nightly at 02:00
0 2 * * * forge docker exec platform-db-1 pg_dump -U forge forge_platform | gzip | aws s3 cp - s3://forge-backups/$(date +\%Y-\%m-\%d).sql.gz
```

### Option B — continuous WAL archiving (recommended for prod)
Configure postgres with `archive_mode=on`, ship WAL segments to object storage. Enables point-in-time recovery. **Not yet scripted in Forge.**

### Restore verification
Any backup is unvalidated until a restore is tested end-to-end. Recommended cadence: monthly in staging.

```bash
# example restore sequence — NOT TESTED in Forge yet
docker exec -i platform-db-1 psql -U forge -d forge_platform < backup.sql
docker compose restart forge-api
# smoke test: GET /health, then GET /api/v1/projects
```

---

## Rollback

### App rollback
The app image is tagged (once CI exists — Roadmap Phase 3). For now, rollback = `git checkout <prev-sha>` + rebuild + restart.

### DB rollback
All migrations are `ADD COLUMN IF NOT EXISTS` (additive). **Rollback = no op**; old app version ignores new columns. The DB never breaks the old app. This is intentional design — see `schema_migrations.py` docstring.

### Data rollback
Requires restore from backup (see above). Has RPO = last backup.

---

## Observability (current state: RED)

Enterprise Audit scored observability RED across 4/6 attributes. Until fixes land (Roadmap Phase 2 week 4), operational visibility is:

- **Logs:** `docker compose logs forge-api` (unstructured stdlib logging)
- **Health:** `GET /health` (liveness only; no readiness probe)
- **Metrics:** none (`/metrics` endpoint is TODO)
- **Tracing:** none
- **Alerts:** none

Incident response today means log-tailing. Plan accordingly: on-call expected to have shell access.

---

## Common failure modes & first response

### `schema migration failed for <table>.<column>`
Startup logs show ALTER failed. Usually column type conflict with existing data. Check live schema, correct the migration entry OR drop the existing column if safe.

### `column tasks.risks does not exist` (or similar)
App has newer model than DB schema. See "Schema migrations" section — apply ALTER via docker exec, then restart app.

### Orchestrate task stuck in IN_PROGRESS after restart
In-process BackgroundTasks lost on restart (Enterprise Audit scale item). Manually reset:
```sql
UPDATE tasks SET status='TODO' WHERE status='IN_PROGRESS' AND agent LIKE 'abandoned-%';
```
Roadmap Phase 2 week 8 replaces with durable job queue.

### Orphaned docker postgres containers (`forge-{slug}-postgres`)
Workspace infra spawns containers per project. Test teardown sweeps most; manual sweep:
```bash
docker ps -aq --filter name=forge- | xargs docker rm -f
```

### Disk full (workspace artifacts accumulate)
`forge_output/{project}/workspace/` grows without cleanup. For pilot: periodic manual archive + delete. Production: scheduled cleanup job (not yet implemented).

---

## Monitoring checklist (weekly manual until observability lands)

- `forge_output/` disk usage — warn at 70% host disk
- Docker `platform-*` container status
- Postgres connection count (`SELECT count(*) FROM pg_stat_activity;` < max_connections threshold)
- Orchestrate runs success rate — UI dashboard or SQL:
  ```sql
  SELECT status, count(*) FROM orchestrate_runs
  WHERE created_at > now() - interval '7 days' GROUP BY status;
  ```
- Org-level monthly LLM cost — `SELECT organization_id, sum(cost_usd) FROM llm_calls JOIN projects ON projects.id = llm_calls.project_id WHERE llm_calls.created_at > date_trunc('month', now()) GROUP BY organization_id;`

---

## Changelog

- **v1.0 (2026-04-19)** — Initial runbook covering local dev + single-host pilot. Explicit AMBER/RED status callouts per category. Production cloud deployment is TBD in Roadmap Phase 3.
