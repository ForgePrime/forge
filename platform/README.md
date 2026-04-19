# Forge Platform

Web dashboard + FastAPI backend that governs Forge delivery for multi-tenant teams. Where the root-level Forge (`.claude/CLAUDE.md`) is a CLI discipline for single-developer Claude Code sessions, **Platform** is the orchestrator + UI + audit plane when you want:

- multiple orgs + users + projects in one deployment
- web UI to watch orchestrate runs, review deliverables, dismiss findings
- standardized CGAID artifacts (Evidence / Plan / ADRs / Handoff / …) auto-exported to each project's workspace
- every LLM call audited (cost, tokens, prompt hash, delivery) for compliance

## 5-minute local quickstart

```bash
# from repo root
cd platform
cp .env.example .env           # review; defaults are dev-safe
docker compose up -d postgres redis   # infrastructure deps
uv sync                        # or: pip install -e .
uv run uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/ui/signup → create user → create first project → type `/plan …` in the AI sidebar.

See **docs/DEPLOY.md** for production deployment (IaC, TLS, backup, secret rotation).

## Status (2026-04-19)

- **CGAID compliance:** ~82% (audit: docs/FORGE_PRODUCTION_ROADMAP.md)
- **Enterprise readiness:** RED for production, AMBER for internal pilot (audit: docs/FORGE_ENTERPRISE_AUDIT.md)
- **Tests:** ~420 unit + integration, run via `uv run pytest tests/`

Before any client-facing launch, review **docs/FORGE_ENTERPRISE_AUDIT.md** top-10 fix list.

## Where things live

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI app entry; startup migrations run here |
| `app/api/` | HTTP routers — `pipeline.py` (orchestrate), `execute.py` (per-task claim/deliver), `tier1.py` (UX helpers), `projects.py` (CRUD), `ui.py` (Jinja views) |
| `app/services/` | pure-Python services — `claude_cli.py`, `test_runner.py` (Phase A executable tests), `challenger.py` (independent verification), `coverage_analyzer.py` (source-term coverage gate), `*_exporter.py` (in-repo artifacts) |
| `app/models/` | SQLAlchemy models + `schema_migrations.py` idempotent ALTERs |
| `app/templates/` | Jinja2 + HTMX templates |
| `tests/` | pytest — unit + HTTP integration (`conftest_populated.py` spins up test projects) |

## Key concepts in 30 seconds

- **Objective** = business goal with measurable Key Results
- **Task** = atomic unit of work; feature/bug tasks REQUIRE test-verifiable AC
- **AC (Acceptance Criterion)** = `{text, scenario_type, verification, test_path|command|check}` — mechanical gate
- **Decision** = OPEN questions block planning; CLOSED become ADRs in `.ai/decisions/`
- **Knowledge (SRC-NNN)** = source doc; coverage_analyzer flags terms absent from AC
- **Phase A test_runner** = Forge runs pytest itself after delivery; doesn't trust completion_claims
- **Challenger** = independent LLM verifies delivery; scope limits surfaced on report
- **Autonomy L1–L5** = project-level trust ladder; per-objective watchlist opt-out

## Contribution rules (project CLAUDE.md applies)

- Feature/bug tasks MUST have ≥1 AC with `verification='test'|'command'` + `test_path`
- Every completion: gates must pass (mechanical), AC verified, `[EXECUTED]/[INFERRED]/[ASSUMED]` tags in reasoning
- Commits from orchestrate carry `Assisted-by: Forge orchestrator (<model>)` trailer (Linux Kernel 2026 precedent)
- 3 epistemic tags are a contract violation when missing — `contract_validator.py:158-175`

For CGAID alignment: see `docs/FORGE_PRODUCTION_ROADMAP.md`.
