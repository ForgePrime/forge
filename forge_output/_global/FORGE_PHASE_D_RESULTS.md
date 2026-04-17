# Faza D — Dashboard UI

**Data:** 2026-04-17
**Stack:** Jinja2 + HTMX + Tailwind CDN (zero build pipeline, zero npm)

## Zbudowane

### Templates (`app/templates/`)
- `base.html` — layout z Tailwind CDN + HTMX
- `index.html` — lista projektów z live stats (tasks/cost/findings/decisions) + modal "New project"
- `project.html` — project detail z 6 tabs: Objectives, Tasks, LLM-calls, Findings, Decisions, Knowledge + 4 action buttons (Ingest/Analyze/Plan/Orchestrate)
- `task_report.html` — trustworthy DONE report z pełnym Phase A/B/C breakdown
- `llm_call.html` — pełny prompt + response + parsed delivery + stderr

### Router (`app/api/ui.py`)
- `GET /ui/` — index
- `GET /ui/projects/{slug}?tab=X` — project with tab selector
- `GET /ui/projects/{slug}/tasks/{ext}` — task report
- `GET /ui/llm-calls/{id}` — LLM call detail
- `POST /ui/projects` — create project (HTMX form)
- `POST /ui/projects/{slug}/ingest` — multipart upload
- `POST /ui/projects/{slug}/analyze` — trigger analyze
- `POST /ui/projects/{slug}/plan` — pick objective, trigger plan
- `POST /ui/projects/{slug}/orchestrate` — max_tasks + enable_redis + skip_infra

### Task report renderuje:
- Task header z kosztem i liczbą prób
- **📋 Requirements covered** — linki do SRC-NNN z matchem z Knowledge
- **🎯 Objective + KRs** — z gwiazdką przy KR completed_by_this_task
- **🧪 Tests executed BY FORGE** — aggregate counts + per-AC mapping + expandable per-test
- **⚔️ Cross-model challenge** — verdict badge, claims verified/refuted, expandable per-claim
- **🔍 Findings** — color-coded by severity, badge by source (extractor/challenger)
- **💡 Decisions** — z recommendation + reasoning
- **✔️ Acceptance criteria** — z test_path / command
- **⚠️ Not executed claims**

## Bugs znalezione w trakcie budowy
1. Jinja2 z Python 3.13 cache unhashable → fix: `templates.env.cache = None`
2. Starlette Jinja2Templates nowe API: `TemplateResponse(request, name, context)` zamiast `TemplateResponse(name, {"request": request, ...})`

## Smoke test
Wszystkie 4 główne widoki → HTTP 200:
- `/ui/` (4.4KB)
- `/ui/projects/appointmentbooking` (15KB)
- `/ui/projects/appointmentbooking/tasks/T-004` (28KB) — rendering Phase C (NEEDS_REWORK + F-012..F-017 + Twilio + httpx bugs)
- `/ui/llm-calls/1` (41KB) — pełny prompt + response

## Status całej platformy

| Faza | Status | Dowód |
|------|--------|-------|
| Core pipeline (ingest→analyze→plan→orchestrate) | ✓ | 2 scenariusze E2E |
| Phase A — test_runner + git_verify + kr_measurer | ✓ | 23/28 vs 22/22 testów pass comparison |
| Phase B — auto-extract decisions + findings + DONE report | ✓ | 8 decisions + 8 findings z 2 tasków |
| Phase C1 — cross-model challenge (Opus) | ✓ | NEEDS_REWORK werdykt + 6 findings HIGH/MED |
| Phase C2 — workspace docker-compose bootstrap | ✓ | per-project postgres+redis, deterministic ports |
| Phase D — Dashboard UI | ✓ | 4 widoki × HTTP 200, render pełnego Phase C |

## Co zostaje do dopracowania (post-D)

1. **Live polling IN_PROGRESS** — orchestrate jest sync (blokuje request ~10-30min). Dashboard powinien:
   - Pokazać "Orchestrating..." spinner + ETA
   - HTMX poll endpoint `/ui/projects/{slug}/progress` co 5s
   - Async orchestrate (background worker) żeby UI nie blokowało
2. **Task action: approve finding → triage** — UI button "Create task from F-NNN"
3. **Manual override KR** — edit current_value ręcznie
4. **Workspace file browser** — `tree` view + click → view file
5. **Diff viewer** — dla `changes[]` per task

## Jak używać

1. Uruchom server: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8037`
2. Browser: `http://localhost:8037/ui/`
3. Create project → Upload docs → Analyze → Plan → Orchestrate
4. Klick task → Trustworthy DONE report
5. Klick LLM call → pełny prompt + response audit

Forge platforma jest teraz operacyjnie użyteczna — nie trzeba curl/psql/JSON.
