# Changelog

Release history for Forge. Semver: major.minor.patch.

Conventions:
- `feat`  — user-facing feature
- `fix`   — bugfix
- `ops`   — operational / infra
- `docs`  — documentation-only
- `test`  — test-only additions
- `chore` — tooling, deps, non-feature

## [Unreleased]

### Autonomous session 2026-04-19 — production readiness pass
- feat(cgaid): Handoff Document exporter (CGAID artifact #4)
- feat(provenance): `Assisted-by:` commit trailer (Linux Kernel 2026 precedent)
- ops(dr): backup + restore scripts + docs/DEPLOY.md runbook
- feat(shutdown): graceful SIGTERM cleanup releases IN_PROGRESS task leases
- feat(ops): /ready readiness probe separates liveness from readiness
- feat(obs): JSON structured logging + request-id middleware (zero-dep)
- feat(pii): regex-based PII scanner baseline (standalone, awaiting policy wiring)
- feat(gdpr): Article 20 data portability export (user + organization)
- test+fix(validator): 3 trust gates directly covered; contract_validator
  hardened against TypeError on non-list files_changed
- test(autonomy): 21 unit tests for L1-L5 promotion ladder
- test+docs: enterprise readiness audit (54 attributes), production roadmap
- docs: platform README + DEPLOY runbook
- chore: SQLAlchemy 2.0.30 → 2.0.49 (Python 3.13 compatibility)
- ci: starter `.github/workflows/ci.yml` (pytest + pip-audit + bandit + ruff);
  scheduled weekly security workflow

See `docs/AUTONOMOUS_SESSION_LOG.md` for per-decision rationale.

## [0.1.0] — Initial development (pre-history)

Platform scaffolding, CGAID pipeline (ingest → analyze → plan → orchestrate),
Phase A test_runner, challenger verification, autonomy ladder, cost gating,
multi-tenant org/user model.
