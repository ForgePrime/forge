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

See [`docs/platform/ARCHITECTURE.md`](docs/platform/ARCHITECTURE.md) for system overview and [`docs/platform/ONBOARDING.md`](docs/platform/ONBOARDING.md) for first-contribution tutorial. (Production deploy doc `docs/DEPLOY.md` pending — tracked as doc gap.)

## Status (2026-04-23)

- **Governance:** v2.1 spec in [`docs/`](docs/) — **DRAFT** pending peer review per [ADR-003](docs/decisions/ADR-003-human-reviewer-normative-transition.md). Start at [`docs/README.md`](docs/README.md).
- **CGAID compliance:** partial — see [`docs/FRAMEWORK_MAPPING.md`](docs/FRAMEWORK_MAPPING.md) for binding to MANIFEST principles / OM layers / 11 artifacts / 7 metrics. Phase G (`docs/CHANGE_PLAN_v2.md §13`) closes remaining gaps.
- **Gaps vs spec:** 4 CRITICAL + 15 HIGH + 15 MEDIUM + 1 LOW per [`docs/GAP_ANALYSIS_v2.md`](docs/GAP_ANALYSIS_v2.md).
- **Known risks (29 enumerated):** see [`docs/DEEP_RISK_REGISTER.md`](docs/DEEP_RISK_REGISTER.md). **2 CRITICAL** (R-FW-02 Stage 0 policy-only; R-GOV-01 solo-authored spec).
- **Enterprise readiness:** NOT ready for Confidential+ processing without deployed DLP (see R-FW-02). Internal pilot acceptable.
- **Tests:** ~420 unit + integration, run via `uv run pytest tests/`. Property-based / metamorphic / adversarial suites planned (Phase D per ROADMAP).

Before any client-facing launch: review [`docs/DEEP_RISK_REGISTER.md`](docs/DEEP_RISK_REGISTER.md) top-10 and complete Phase A (see [`docs/ROADMAP.md`](docs/ROADMAP.md)).

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

For full governance (spec, gaps, change plan, framework mapping, ADRs, deep-risk register): see [`docs/README.md`](docs/README.md).
